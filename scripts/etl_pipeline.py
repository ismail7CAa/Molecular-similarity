"""
SQL ETL pipeline for molecular similarity and ChEMBL imports.

Flows supported:
1. Pair files -> dataset index -> local modeling DB
2. Official ChEMBL SQLite -> local analysis DB
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = "./data/chembl.db"
DEFAULT_INDEX_PATH = "./exploration/reports/dataset_index.json"
DEFAULT_COMPACT_CHEMBL_DIR = "./data/chembl_small"
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
OPTIONAL_PAIR_COLUMNS = {
    "target_chembl_id": "TEXT",
    "target_name": "TEXT",
    "standard_type": "TEXT",
    "activity_value_a": "REAL",
    "activity_value_b": "REAL",
    "activity_unit": "TEXT",
    "activity_delta": "REAL",
}
PAIRABLE_STANDARD_TYPES = {"Ki", "IC50", "EC50"}
UNIT_TO_NM_SCALE = {"nM": 1.0, "uM": 1000.0}


def _chembl_numeric_id(chembl_id: str) -> int:
    normalized = str(chembl_id).strip()
    if not normalized.startswith("CHEMBL"):
        raise ValueError(f"Unsupported ChEMBL identifier: {chembl_id}")
    return int(normalized.removeprefix("CHEMBL"))


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
        self._ensure_pair_columns()
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

    def _ensure_pair_columns(self) -> None:
        """Backfill newer pair metadata columns in older local databases."""
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized")

        existing_columns = {
            row[1]
            for row in self.conn.execute("PRAGMA table_info(molecule_pairs)")
        }
        for column_name, column_type in OPTIONAL_PAIR_COLUMNS.items():
            if column_name in existing_columns:
                continue
            self.conn.execute(
                f"ALTER TABLE molecule_pairs ADD COLUMN {column_name} {column_type}"
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
        self._ensure_pair_columns()
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

    def import_compact_chembl_json(self, dataset_dir: str) -> dict[str, int]:
        """Import compact ChEMBL API JSON payloads into the local database."""
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized")

        self._ensure_activity_columns()
        self._ensure_pair_columns()
        dataset_path = Path(dataset_dir)
        if not dataset_path.exists():
            raise FileNotFoundError(f"Compact ChEMBL dataset directory not found: {dataset_dir}")

        activity_files = sorted(dataset_path.glob("*_activities.json"))
        if not activity_files:
            raise FileNotFoundError(
                f"No *_activities.json files found in compact dataset directory: {dataset_dir}"
            )

        molecules_by_chembl_id: dict[str, dict[str, object]] = {}
        activities: list[dict[str, object]] = []

        for activity_file in activity_files:
            payload = json.loads(activity_file.read_text())
            for activity in payload.get("activities", []):
                molecule_chembl_id = str(activity.get("molecule_chembl_id") or "").strip()
                if not molecule_chembl_id:
                    continue

                molecules_by_chembl_id.setdefault(
                    molecule_chembl_id,
                    {
                        "molecule_id": _chembl_numeric_id(molecule_chembl_id),
                        "chembl_id": molecule_chembl_id,
                        "compound_name": activity.get("molecule_pref_name")
                        or activity.get("parent_molecule_chembl_id")
                        or molecule_chembl_id,
                        "smiles": activity.get("canonical_smiles") or "",
                        "inchi": "",
                        "molecular_weight": None,
                        "heavy_atom_count": None,
                    },
                )
                activities.append(
                    {
                        "activity_id": int(activity["activity_id"]),
                        "molecule_id": _chembl_numeric_id(molecule_chembl_id),
                        "assay_type": activity.get("assay_type"),
                        "activity_value": float(activity["standard_value"])
                        if activity.get("standard_value") not in {None, ""}
                        else None,
                        "unit": activity.get("standard_units"),
                        "standard_type": activity.get("standard_type"),
                        "target_chembl_id": activity.get("target_chembl_id"),
                        "target_name": activity.get("target_pref_name"),
                        "source_assay_id": None,
                    }
                )

        molecules = sorted(
            molecules_by_chembl_id.values(),
            key=lambda row: int(row["molecule_id"]),
        )
        self._upsert_molecules(molecules)
        imported_activity_count = self._insert_activities(activities)
        self.conn.commit()

        summary = {
            "molecules": len(molecules),
            "activities": imported_activity_count,
            "source_files": len(activity_files),
        }
        print(
            "Imported {molecules} molecules and {activities} activities from "
            "{source_files} compact JSON files".format(**summary)
        )
        return summary

    def generate_activity_pairs(
        self,
        similarity_threshold: float = 1.0,
        max_pairs_per_group: int = 2000,
    ) -> dict[str, int]:
        """Build pair candidates from comparable activity records."""
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized")

        self._ensure_pair_columns()
        aggregated_rows = self._build_activity_pairing_rows()
        total_groups = len(aggregated_rows)
        inserted_pairs = 0

        for group_key, rows in aggregated_rows.items():
            pair_candidates = 0
            for left_index, left_row in enumerate(rows):
                for right_row in rows[left_index + 1 :]:
                    if pair_candidates >= max_pairs_per_group:
                        break

                    delta = abs(
                        float(left_row["pchembl_value"]) - float(right_row["pchembl_value"])
                    )
                    similarity_score = round(1.0 / (1.0 + delta), 4)
                    left_molecule_id = int(left_row["molecule_id"])
                    right_molecule_id = int(right_row["molecule_id"])
                    if left_molecule_id <= right_molecule_id:
                        molecule_a_id = left_molecule_id
                        molecule_b_id = right_molecule_id
                        activity_value_a = round(float(left_row["pchembl_value"]), 4)
                        activity_value_b = round(float(right_row["pchembl_value"]), 4)
                    else:
                        molecule_a_id = right_molecule_id
                        molecule_b_id = left_molecule_id
                        activity_value_a = round(float(right_row["pchembl_value"]), 4)
                        activity_value_b = round(float(left_row["pchembl_value"]), 4)
                    pair_id = (
                        f"ACT_{left_row['target_chembl_id']}_{left_row['standard_type']}_"
                        f"{molecule_a_id}_{molecule_b_id}"
                    )
                    self.conn.execute(
                        """
                        INSERT OR REPLACE INTO molecule_pairs
                        (
                            pair_id,
                            molecule_a_id,
                            molecule_b_id,
                            has_conformer_pair,
                            has_image_pair,
                            similarity_score,
                            is_similar,
                            target_chembl_id,
                            target_name,
                            standard_type,
                            activity_value_a,
                            activity_value_b,
                            activity_unit,
                            activity_delta
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            pair_id,
                            molecule_a_id,
                            molecule_b_id,
                            False,
                            False,
                            similarity_score,
                            delta <= similarity_threshold,
                            left_row["target_chembl_id"],
                            left_row["target_name"],
                            left_row["standard_type"],
                            activity_value_a,
                            activity_value_b,
                            "pchembl",
                            round(delta, 4),
                        ),
                    )
                    inserted_pairs += 1
                    pair_candidates += 1

        self.conn.commit()
        summary = {
            "groups": total_groups,
            "pairs": inserted_pairs,
        }
        print("Generated {pairs} activity-derived pairs across {groups} groups".format(**summary))
        return summary

    def _build_activity_pairing_rows(self) -> dict[tuple[str, str], list[dict[str, object]]]:
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized")

        rows = self.conn.execute(
            """
            SELECT
                molecule_id,
                target_chembl_id,
                target_name,
                standard_type,
                unit,
                activity_value
            FROM activities
            WHERE activity_value IS NOT NULL
              AND target_chembl_id IS NOT NULL
              AND standard_type IS NOT NULL
            ORDER BY target_chembl_id, standard_type, molecule_id
            """
        ).fetchall()

        grouped_values: dict[tuple[int, str, str], list[float]] = {}
        grouped_metadata: dict[tuple[int, str, str], tuple[str, str]] = {}
        for molecule_id, target_chembl_id, target_name, standard_type, unit, activity_value in rows:
            if standard_type not in PAIRABLE_STANDARD_TYPES:
                continue
            if unit not in UNIT_TO_NM_SCALE:
                continue
            if activity_value is None or float(activity_value) <= 0:
                continue

            value_nm = float(activity_value) * UNIT_TO_NM_SCALE[unit]
            pchembl_value = 9.0 - math.log10(value_nm)
            row_key = (int(molecule_id), str(target_chembl_id), str(standard_type))
            grouped_values.setdefault(row_key, []).append(pchembl_value)
            grouped_metadata[row_key] = (str(target_name), "pchembl")

        pairing_groups: dict[tuple[str, str], list[dict[str, object]]] = {}
        for row_key, values in grouped_values.items():
            molecule_id, target_chembl_id, standard_type = row_key
            target_name, _ = grouped_metadata[row_key]
            median_value = sorted(values)[len(values) // 2]
            pairing_groups.setdefault((target_chembl_id, standard_type), []).append(
                {
                    "molecule_id": molecule_id,
                    "target_chembl_id": target_chembl_id,
                    "target_name": target_name,
                    "standard_type": standard_type,
                    "pchembl_value": median_value,
                }
            )

        return {
            group_key: sorted(
                group_rows,
                key=lambda row: (float(row["pchembl_value"]), int(row["molecule_id"])),
            )
            for group_key, group_rows in pairing_groups.items()
            if len(group_rows) >= 2
        }

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
                mp.pair_id,
                mp.molecule_a_id,
                mp.molecule_b_id,
                mp.has_conformer_pair,
                mp.has_image_pair,
                mp.similarity_score,
                mp.is_similar,
                mp.target_chembl_id,
                mp.target_name,
                mp.standard_type,
                mp.activity_value_a,
                mp.activity_value_b,
                mp.activity_unit,
                mp.activity_delta,
                ma.chembl_id,
                mb.chembl_id,
                ma.compound_name,
                mb.compound_name,
                ma.smiles,
                mb.smiles,
                ma.molecular_weight,
                mb.molecular_weight,
                ma.heavy_atom_count,
                mb.heavy_atom_count
            FROM molecule_pairs
            AS mp
            LEFT JOIN molecules AS ma ON ma.molecule_id = mp.molecule_a_id
            LEFT JOIN molecules AS mb ON mb.molecule_id = mp.molecule_b_id
            WHERE mp.is_similar IS NOT NULL
            """
        ).fetchall()

        fieldnames = [
            "pair_id",
            "split",
            "molecule_a_id",
            "molecule_b_id",
            "molecule_a_chembl_id",
            "molecule_b_chembl_id",
            "compound_name_a",
            "compound_name_b",
            "target_chembl_id",
            "target_name",
            "standard_type",
            "has_conformer_pair",
            "has_image_pair",
            "similarity_score",
            "is_similar",
            "activity_value_a",
            "activity_value_b",
            "activity_unit",
            "activity_delta",
            "activity_value_mean",
            "smiles_a",
            "smiles_b",
            "smiles_length_a",
            "smiles_length_b",
            "smiles_length_abs_delta",
            "molecular_weight_a",
            "molecular_weight_b",
            "molecular_weight_abs_delta",
            "heavy_atom_count_a",
            "heavy_atom_count_b",
            "heavy_atom_count_abs_delta",
        ]
        with open(output_path, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                (
                    pair_id,
                    molecule_a_id,
                    molecule_b_id,
                    has_conformer_pair,
                    has_image_pair,
                    similarity_score,
                    is_similar,
                    target_chembl_id,
                    target_name,
                    standard_type,
                    activity_value_a,
                    activity_value_b,
                    activity_unit,
                    activity_delta,
                    chembl_id_a,
                    chembl_id_b,
                    compound_name_a,
                    compound_name_b,
                    smiles_a,
                    smiles_b,
                    molecular_weight_a,
                    molecular_weight_b,
                    heavy_atom_count_a,
                    heavy_atom_count_b,
                ) = row
                smiles_a = smiles_a or ""
                smiles_b = smiles_b or ""
                weight_a = float(molecular_weight_a) if molecular_weight_a is not None else 0.0
                weight_b = float(molecular_weight_b) if molecular_weight_b is not None else 0.0
                heavy_a = int(heavy_atom_count_a) if heavy_atom_count_a is not None else 0
                heavy_b = int(heavy_atom_count_b) if heavy_atom_count_b is not None else 0
                activity_a = float(activity_value_a) if activity_value_a is not None else 0.0
                activity_b = float(activity_value_b) if activity_value_b is not None else 0.0
                writer.writerow(
                    {
                        "pair_id": pair_id,
                        "split": self._deterministic_split(str(pair_id)),
                        "molecule_a_id": molecule_a_id,
                        "molecule_b_id": molecule_b_id,
                        "molecule_a_chembl_id": chembl_id_a,
                        "molecule_b_chembl_id": chembl_id_b,
                        "compound_name_a": compound_name_a or "",
                        "compound_name_b": compound_name_b or "",
                        "target_chembl_id": target_chembl_id or "",
                        "target_name": target_name or "",
                        "standard_type": standard_type or "",
                        "has_conformer_pair": int(bool(has_conformer_pair)),
                        "has_image_pair": int(bool(has_image_pair)),
                        "similarity_score": float(similarity_score) if similarity_score is not None else 0.0,
                        "is_similar": int(bool(is_similar)),
                        "activity_value_a": activity_a,
                        "activity_value_b": activity_b,
                        "activity_unit": activity_unit or "",
                        "activity_delta": float(activity_delta) if activity_delta is not None else 0.0,
                        "activity_value_mean": round((activity_a + activity_b) / 2.0, 4),
                        "smiles_a": smiles_a,
                        "smiles_b": smiles_b,
                        "smiles_length_a": len(smiles_a),
                        "smiles_length_b": len(smiles_b),
                        "smiles_length_abs_delta": abs(len(smiles_a) - len(smiles_b)),
                        "molecular_weight_a": weight_a,
                        "molecular_weight_b": weight_b,
                        "molecular_weight_abs_delta": round(abs(weight_a - weight_b), 4),
                        "heavy_atom_count_a": heavy_a,
                        "heavy_atom_count_b": heavy_b,
                        "heavy_atom_count_abs_delta": abs(heavy_a - heavy_b),
                    }
                )

        print(f"Exported {len(rows)} records")

    @staticmethod
    def _deterministic_split(pair_id: str) -> str:
        bucket = sum(pair_id.encode("utf-8")) % 10
        if bucket < 8:
            return "train"
        if bucket == 8:
            return "val"
        return "test"

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
        "--compact-chembl-dir",
        type=str,
        default=DEFAULT_COMPACT_CHEMBL_DIR,
        help=(
            "Path to the compact ChEMBL JSON directory "
            f"(default: {DEFAULT_COMPACT_CHEMBL_DIR})"
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
        "--import-compact-chembl",
        action="store_true",
        help="Import molecules and activities from compact ChEMBL API JSON files",
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
        "--generate-activity-pairs",
        action="store_true",
        help="Generate molecule pairs from imported activity records",
    )
    parser.add_argument(
        "--pair-threshold",
        type=float,
        default=1.0,
        help="Maximum pChEMBL delta to mark an activity-derived pair as similar",
    )
    parser.add_argument(
        "--max-pairs-per-group",
        type=int,
        default=2000,
        help="Maximum number of generated pairs per target/activity-type group",
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

        if args.import_compact_chembl:
            pipeline.import_compact_chembl_json(args.compact_chembl_dir)

        if args.generate_activity_pairs:
            pipeline.generate_activity_pairs(
                similarity_threshold=args.pair_threshold,
                max_pairs_per_group=args.max_pairs_per_group,
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
