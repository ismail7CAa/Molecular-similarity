from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import MACCSkeys, rdFingerprintGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.etl_pipeline import STRUCTURAL_ALERT_COLUMNS  # noqa: E402


DEFAULT_DB_PATH = Path("data/chembl.db")
DEFAULT_OUTPUT_PATH = Path("data/enriched_molecules.parquet")
MORGAN_RADIUS2 = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
MORGAN_RADIUS3 = rdFingerprintGenerator.GetMorganGenerator(radius=3, fpSize=2048)
RDLogger.DisableLog("rdApp.warning")

RA_METADATA_COLUMNS = [
    "max_phase",
    "therapeutic_area",
    "indication_count",
    "first_approval",
    "black_box_warning",
    "molecule_type",
    "oral",
    "parenteral",
    "topical",
    "regulatory_alert_count",
    "regulatory_alerts",
]


def _fingerprint_bitstring(fingerprint: Any) -> str:
    return DataStructs.BitVectToText(fingerprint)


def build_enriched_molecule_rows(db_path: Path) -> list[dict[str, object]]:
    """Build one enriched inference-lookup row per ChEMBL molecule."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        select_columns = [
            "molecule_id",
            "chembl_id",
            "compound_name",
            "smiles",
            "inchi",
            "molecular_weight",
            "heavy_atom_count",
            *RA_METADATA_COLUMNS,
            *STRUCTURAL_ALERT_COLUMNS,
        ]
        rows = conn.execute(
            f"""
            SELECT {", ".join(select_columns)}
            FROM molecules
            WHERE smiles IS NOT NULL
              AND smiles != ''
            ORDER BY molecule_id
            """
        ).fetchall()
    finally:
        conn.close()

    enriched_rows: list[dict[str, object]] = []
    for row in rows:
        molecule = Chem.MolFromSmiles(str(row["smiles"]))
        if molecule is None:
            continue

        enriched_rows.append(
            {
                "molecule_id": int(row["molecule_id"]),
                "chembl_id": row["chembl_id"] or "",
                "compound_name": row["compound_name"] or "",
                "smiles": row["smiles"] or "",
                "inchi": row["inchi"] or "",
                "molecular_weight": (
                    float(row["molecular_weight"])
                    if row["molecular_weight"] is not None
                    else 0.0
                ),
                "heavy_atom_count": (
                    int(row["heavy_atom_count"])
                    if row["heavy_atom_count"] is not None
                    else 0
                ),
                "morgan_fp_radius2": _fingerprint_bitstring(
                    MORGAN_RADIUS2.GetFingerprint(molecule)
                ),
                "morgan_fp_radius3": _fingerprint_bitstring(
                    MORGAN_RADIUS3.GetFingerprint(molecule)
                ),
                "maccs_fp": _fingerprint_bitstring(MACCSkeys.GenMACCSKeys(molecule)),
                "max_phase": float(row["max_phase"] or 0.0),
                "first_approval": row["first_approval"] or None,
                "therapeutic_area": row["therapeutic_area"] or "Unassigned",
                "therapeutic_flag": int(bool(row["max_phase"] or row["first_approval"])),
                "black_box_warning": int(bool(row["black_box_warning"])),
                "indication_count": int(row["indication_count"] or 0),
                "molecule_type": row["molecule_type"] or "",
                "oral": int(bool(row["oral"])),
                "parenteral": int(bool(row["parenteral"])),
                "topical": int(bool(row["topical"])),
                "regulatory_alert_count": int(row["regulatory_alert_count"] or 0),
                "regulatory_alerts": row["regulatory_alerts"] or "",
                **{
                    alert_column: int(bool(row[alert_column]))
                    for alert_column in STRUCTURAL_ALERT_COLUMNS
                },
            }
        )

    return enriched_rows


def write_parquet(rows: list[dict[str, object]], output_path: Path) -> None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError(
            "Writing enriched_molecules.parquet requires pyarrow. "
            "Install project dependencies with: pip install -e .[dev]"
        ) from error

    output_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, output_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build molecule-level enriched Parquet for inference lookup"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Input SQLite DB path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output Parquet path (default: {DEFAULT_OUTPUT_PATH})",
    )
    args = parser.parse_args()

    rows = build_enriched_molecule_rows(args.db)
    write_parquet(rows, args.output)
    print(f"Wrote {len(rows)} enriched molecule rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
