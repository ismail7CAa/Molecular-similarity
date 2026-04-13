"""
SQL ETL pipeline for molecular similarity and ChEMBL imports.

Flows supported:
1. Pair files -> dataset index -> local modeling DB
2. Official ChEMBL SQLite -> local analysis DB
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = "./data/chembl.db"
DEFAULT_INDEX_PATH = "./exploration/reports/dataset_index.json"
DEFAULT_CHEMBL_SQLITE_PATH = (
    "./data/chembl/raw/chembl_36_sqlite/chembl_36/chembl_36_sqlite/chembl_36.db"
)
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"
OPTIONAL_ACTIVITY_COLUMNS = {
    "standard_type": "TEXT",
    "target_chembl_id": "TEXT",
    "target_name": "TEXT",
    "source_assay_id": "INTEGER",
}


class MolecularETLPipeline:
    """ETL pipeline for loading molecular data into a local SQLite database."""

    def __init__(self, db_path: str, db_type: str = "sqlite"):
        self.db_path = db_path
        self.db_type = db_type
        self.conn: sqlite3.Connection | None = None
        self.cursor: sqlite3.Cursor | None = None

    def connect(self) -> None:
        """Establish the destination database connection."""
        if self.db_type != "sqlite":
            raise NotImplementedError(f"Database type {self.db_type} not yet implemented")

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"Connected to SQLite: {self.db_path}")

    def create_schema(self) -> None:
        """Create the local schema used by the modeling pipeline."""
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized")

        print(f"Creating database schema from {SCHEMA_PATH}...")
        self.conn.executescript(SCHEMA_PATH.read_text())
        self._ensure_activity_columns()
        self.conn.commit()
        print("Schema created successfully")

    def _ensure_activity_columns(self) -> None:
        """Backfill newer activity columns in older local databases."""
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized")

        existing_columns = {
            row[1]
            for row in self.conn.execute("PRAGMA table_info(activities)")
        }
        for column_name, column_type in OPTIONAL_ACTIVITY_COLUMNS.items():
            if column_name in existing_columns:
                continue
            self.conn.execute(
                f"ALTER TABLE activities ADD COLUMN {column_name} {column_type}"
            )

    def load_from_index(self, index_json_path: str) -> None:
        """Load pair completeness data from dataset_index.json."""
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized")

        print(f"Loading pair data from {index_json_path}...")

        with open(index_json_path, "r") as handle:
            data = json.load(handle)

        if isinstance(data, list):
            pairs = data
        else:
            pairs = data.get("pairs", [])

        for pair in pairs:
            pair_id = str(pair.get("pair_id"))
            has_pdb = bool(pair.get("has_complete_pdb_pair"))
            has_svg = bool(pair.get("has_complete_svg_pair"))
            molecule_a_id = int(pair_id) * 2 - 1
            molecule_b_id = int(pair_id) * 2

            self.conn.execute(
                """
                INSERT OR IGNORE INTO molecule_pairs
                (pair_id, molecule_a_id, molecule_b_id, has_conformer_pair, has_image_pair)
                VALUES (?, ?, ?, ?, ?)
                """,
                (pair_id, molecule_a_id, molecule_b_id, has_pdb, has_svg),
            )

        self.conn.commit()
        print(f"Loaded {len(pairs)} molecule pairs")

    def import_chembl_sqlite(
        self,
        source_db_path: str,
        limit: int | None = None,
        include_activities: bool = False,
        activity_limit: int | None = None,
    ) -> dict[str, int]:
        """Import molecules and optional activities from the official ChEMBL SQLite DB."""
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized")

        self._ensure_activity_columns()
        source_path = Path(source_db_path)
        if not source_path.exists():
            raise FileNotFoundError(f"ChEMBL SQLite database not found: {source_db_path}")

        print(f"Importing ChEMBL SQLite data from {source_db_path}...")
        molecules = self._fetch_chembl_molecules(source_path, limit=limit)
        self._upsert_molecules(molecules)

        imported_activity_count = 0
        if include_activities and molecules:
            molecule_ids = [row["molecule_id"] for row in molecules]
            activities = self._fetch_chembl_activities(
                source_path,
                molecule_ids=molecule_ids,
                limit=activity_limit,
            )
            imported_activity_count = self._insert_activities(activities)

        self.conn.commit()
        summary = {
            "molecules": len(molecules),
            "activities": imported_activity_count,
        }
        print(
            "Imported {molecules} molecules and {activities} activities".format(
                **summary
            )
        )
        return summary

    def _fetch_chembl_molecules(
        self,
        source_path: Path,
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        source_conn = sqlite3.connect(source_path)
        source_conn.row_factory = sqlite3.Row
        try:
            query = """
                SELECT
                    md.molregno AS molecule_id,
                    md.chembl_id,
                    COALESCE(md.pref_name, '') AS compound_name,
                    COALESCE(cs.canonical_smiles, '') AS smiles,
                    COALESCE(cs.standard_inchi, '') AS inchi,
                    cp.full_mwt AS molecular_weight,
                    cp.heavy_atoms AS heavy_atom_count
                FROM molecule_dictionary md
                JOIN compound_structures cs ON cs.molregno = md.molregno
                LEFT JOIN compound_properties cp ON cp.molregno = md.molregno
                WHERE cs.canonical_smiles IS NOT NULL
                ORDER BY md.molregno
            """
            parameters: tuple[object, ...] = ()
            if limit is not None:
                query += " LIMIT ?"
                parameters = (limit,)

            return [
                dict(row)
                for row in source_conn.execute(query, parameters).fetchall()
            ]
        finally:
            source_conn.close()

    def _upsert_molecules(self, molecules: list[dict[str, object]]) -> None:
        if self.conn is None or not molecules:
            return

        self.conn.executemany(
            """
            INSERT OR REPLACE INTO molecules
            (molecule_id, chembl_id, compound_name, smiles, inchi, molecular_weight, heavy_atom_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["molecule_id"],
                    row["chembl_id"],
                    row["compound_name"],
                    row["smiles"],
                    row["inchi"],
                    row["molecular_weight"],
                    row["heavy_atom_count"],
                )
                for row in molecules
            ],
        )

    def _fetch_chembl_activities(
        self,
        source_path: Path,
        molecule_ids: list[int],
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        if not molecule_ids:
            return []

        placeholders = ",".join("?" for _ in molecule_ids)
        query = f"""
            SELECT
                a.activity_id,
                a.molregno AS molecule_id,
                assays.assay_type,
                a.standard_value AS activity_value,
                a.standard_units AS unit,
                a.standard_type,
                td.chembl_id AS target_chembl_id,
                td.pref_name AS target_name,
                a.assay_id AS source_assay_id
            FROM activities a
            LEFT JOIN assays ON assays.assay_id = a.assay_id
            LEFT JOIN target_dictionary td ON td.tid = assays.tid
            WHERE a.molregno IN ({placeholders})
              AND a.standard_value IS NOT NULL
        """
        parameters: list[object] = list(molecule_ids)
        if limit is not None:
            query += " ORDER BY a.activity_id LIMIT ?"
            parameters.append(limit)
        else:
            query += " ORDER BY a.activity_id"

        source_conn = sqlite3.connect(source_path)
        source_conn.row_factory = sqlite3.Row
        try:
            return [
                dict(row)
                for row in source_conn.execute(query, tuple(parameters)).fetchall()
            ]
        finally:
            source_conn.close()

    def _insert_activities(self, activities: list[dict[str, object]]) -> int:
        if self.conn is None or not activities:
            return 0

        self.conn.executemany(
            """
            INSERT OR REPLACE INTO activities
            (
                activity_id,
                molecule_id,
                assay_type,
                activity_value,
                unit,
                standard_type,
                target_chembl_id,
                target_name,
                source_assay_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["activity_id"],
                    row["molecule_id"],
                    row["assay_type"],
                    row["activity_value"],
                    row["unit"],
                    row["standard_type"],
                    row["target_chembl_id"],
                    row["target_name"],
                    row["source_assay_id"],
                )
                for row in activities
            ],
        )
        return len(activities)

    def export_for_modeling(self, output_path: str) -> None:
        """Export pair completeness records for downstream modeling."""
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized")

        print(f"Exporting data to {output_path}...")
        rows = self.conn.execute(
            """
            SELECT
                pair_id,
                has_conformer_pair,
                has_image_pair,
                similarity_score,
                is_similar
            FROM molecule_pairs
            WHERE has_conformer_pair AND has_image_pair
            """
        ).fetchall()

        with open(output_path, "w") as handle:
            handle.write("pair_id,has_conformer,has_image,similarity_score,is_similar\n")
            for row in rows:
                handle.write(",".join(str(value) for value in row) + "\n")

        print(f"Exported {len(rows)} records")

    def get_statistics(self) -> dict[str, object]:
        """Summarize the destination database contents."""
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized")

        molecule_count = self.conn.execute("SELECT COUNT(*) FROM molecules").fetchone()[0]
        pair_count = self.conn.execute("SELECT COUNT(*) FROM molecule_pairs").fetchone()[0]
        complete_pair_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM molecule_pairs
            WHERE has_conformer_pair AND has_image_pair
            """
        ).fetchone()[0]
        activity_count = self.conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]

        return {
            "total_molecules": molecule_count,
            "total_pairs": pair_count,
            "complete_pairs": complete_pair_count,
            "total_activities": activity_count,
            "completeness_pct": round(
                (complete_pair_count / pair_count * 100) if pair_count > 0 else 0,
                2,
            ),
        }

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            print("Database connection closed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SQL ETL pipeline for ChEMBL molecular similarity data"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=DEFAULT_DB_PATH,
        help=f"Destination database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--index",
        type=str,
        default=DEFAULT_INDEX_PATH,
        help=f"Path to dataset_index.json (default: {DEFAULT_INDEX_PATH})",
    )
    parser.add_argument(
        "--chembl-sqlite",
        type=str,
        default=DEFAULT_CHEMBL_SQLITE_PATH,
        help=(
            "Path to the official ChEMBL SQLite database "
            f"(default: {DEFAULT_CHEMBL_SQLITE_PATH})"
        ),
    )
    parser.add_argument(
        "--create-schema",
        action="store_true",
        help="Create the destination schema",
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="Load pair completeness data from dataset_index.json",
    )
    parser.add_argument(
        "--import-chembl-sqlite",
        action="store_true",
        help="Import molecules from the official ChEMBL SQLite database",
    )
    parser.add_argument(
        "--include-activities",
        action="store_true",
        help="Also import ChEMBL activities for imported molecules",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of imported ChEMBL molecules",
    )
    parser.add_argument(
        "--activity-limit",
        type=int,
        help="Limit the number of imported ChEMBL activities",
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export pair data to CSV",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show destination database statistics",
    )
    args = parser.parse_args()

    pipeline = MolecularETLPipeline(args.db)
    pipeline.connect()

    try:
        if args.create_schema:
            pipeline.create_schema()

        if args.load:
            if not Path(args.index).exists():
                print(f"Index file not found: {args.index}")
                print("Run: python scripts/build_dataset_index.py ./data/chembl")
                return 1
            pipeline.load_from_index(args.index)

        if args.import_chembl_sqlite:
            pipeline.import_chembl_sqlite(
                args.chembl_sqlite,
                limit=args.limit,
                include_activities=args.include_activities,
                activity_limit=args.activity_limit,
            )

        if args.stats:
            stats = pipeline.get_statistics()
            print("\nPipeline Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        if args.export:
            pipeline.export_for_modeling(args.export)
    finally:
        pipeline.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
