from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


PDB_PATTERN = re.compile(r"best_rocs_conformer_(\d{3})([ab])\.pdb$")
SVG_PATTERN = re.compile(r"image_molecule_(\d{3})([ab])\.svg$")


def parse_element(line: str) -> str:
    element = line[76:78].strip()
    if element:
        return element

    atom_name = line[12:16].strip()
    letters = "".join(character for character in atom_name if character.isalpha())
    return letters[:2] if letters else "?"


def parse_pdb_file(path: Path) -> dict[str, object]:
    atom_count = 0
    heavy_atom_count = 0
    element_counts: Counter[str] = Counter()
    compound_name = None

    with path.open() as handle:
        for line in handle:
            if line.startswith("COMPND") and compound_name is None:
                compound_name = line.split(maxsplit=1)[1].strip()
            if line.startswith(("ATOM", "HETATM")):
                atom_count += 1
                element = parse_element(line)
                element_counts[element] += 1
                if element.upper() != "H":
                    heavy_atom_count += 1

    return {
        "compound_name": compound_name,
        "atom_count": atom_count,
        "heavy_atom_count": heavy_atom_count,
        "element_counts": dict(sorted(element_counts.items())),
    }


def collect_files(directory: Path, pattern: re.Pattern[str]) -> dict[str, dict[str, Path]]:
    grouped: dict[str, dict[str, Path]] = {}

    for path in sorted(directory.glob("*")):
        match = pattern.match(path.name)
        if not match:
            continue
        identifier, variant = match.groups()
        grouped.setdefault(identifier, {})[variant] = path

    return grouped


def build_index(dataset_root: Path) -> list[dict[str, object]]:
    conformer_dir = dataset_root / "conformers_3D"
    image_dir = dataset_root / "images_2D"

    conformers = collect_files(conformer_dir, PDB_PATTERN)
    images = collect_files(image_dir, SVG_PATTERN)

    pair_ids = sorted(set(conformers) | set(images))
    rows: list[dict[str, object]] = []

    for pair_id in pair_ids:
        conformer_variants = conformers.get(pair_id, {})
        image_variants = images.get(pair_id, {})
        row: dict[str, object] = {
            "pair_id": pair_id,
            "has_complete_pdb_pair": {"a", "b"} <= set(conformer_variants),
            "has_complete_svg_pair": {"a", "b"} <= set(image_variants),
        }

        for variant in ("a", "b"):
            pdb_path = conformer_variants.get(variant)
            svg_path = image_variants.get(variant)
            pdb_data = parse_pdb_file(pdb_path) if pdb_path else None

            row[f"pdb_path_{variant}"] = str(pdb_path) if pdb_path else ""
            row[f"svg_path_{variant}"] = str(svg_path) if svg_path else ""
            row[f"compound_name_{variant}"] = (
                str(pdb_data["compound_name"]) if pdb_data and pdb_data["compound_name"] else ""
            )
            row[f"atom_count_{variant}"] = int(pdb_data["atom_count"]) if pdb_data else ""
            row[f"heavy_atom_count_{variant}"] = (
                int(pdb_data["heavy_atom_count"]) if pdb_data else ""
            )
            row[f"element_counts_{variant}"] = (
                json.dumps(pdb_data["element_counts"], sort_keys=True) if pdb_data else ""
            )

        if row["atom_count_a"] != "" and row["atom_count_b"] != "":
            row["atom_count_delta"] = int(row["atom_count_b"]) - int(row["atom_count_a"])
        else:
            row["atom_count_delta"] = ""

        if row["heavy_atom_count_a"] != "" and row["heavy_atom_count_b"] != "":
            row["heavy_atom_count_delta"] = int(row["heavy_atom_count_b"]) - int(
                row["heavy_atom_count_a"]
            )
        else:
            row["heavy_atom_count_delta"] = ""

        rows.append(row)

    return rows


def render_markdown(rows: list[dict[str, object]], dataset_root: Path) -> str:
    preview_rows = rows[:10]
    lines = [
        "# Dataset Index",
        "",
        f"- Dataset root: `{dataset_root}`",
        f"- Pair rows: {len(rows)}",
        "",
        "## Columns",
        "",
        "- `pair_id`: shared pair identifier",
        "- `pdb_path_a` / `pdb_path_b`: 3D conformer paths",
        "- `svg_path_a` / `svg_path_b`: 2D image paths",
        "- `compound_name_a` / `compound_name_b`: names extracted from PDB `COMPND` records",
        "- `atom_count_*` and `heavy_atom_count_*`: per-variant structural size",
        "- `*_delta`: simple `b - a` difference for pair comparison",
        "",
        "## Preview",
        "",
        "| pair_id | atoms_a | atoms_b | heavy_a | heavy_b | delta_atoms | complete |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for row in preview_rows:
        lines.append(
            "| {pair_id} | {atom_count_a} | {atom_count_b} | {heavy_atom_count_a} | "
            "{heavy_atom_count_b} | {atom_count_delta} | {complete} |".format(
                pair_id=row["pair_id"],
                atom_count_a=row["atom_count_a"],
                atom_count_b=row["atom_count_b"],
                heavy_atom_count_a=row["heavy_atom_count_a"],
                heavy_atom_count_b=row["heavy_atom_count_b"],
                atom_count_delta=row["atom_count_delta"],
                complete=bool(row["has_complete_pdb_pair"]) and bool(row["has_complete_svg_pair"]),
            )
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/build_dataset_index.py /path/to/dataset")
        return 1

    dataset_root = Path(sys.argv[1]).expanduser().resolve()
    if not dataset_root.exists():
        print(f"Dataset directory not found: {dataset_root}")
        return 1

    rows = build_index(dataset_root)
    reports_dir = Path("exploration/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_path = reports_dir / "dataset_index.csv"
    json_path = reports_dir / "dataset_index.json"
    markdown_path = reports_dir / "dataset_index.md"

    fieldnames = list(rows[0].keys()) if rows else []

    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps(rows, indent=2))
    markdown_path.write_text(render_markdown(rows, dataset_root))

    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
