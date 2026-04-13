from __future__ import annotations

import csv
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path


def _load_build_index():
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from scripts.build_dataset_index import build_index

    return build_index


DEFAULT_SPLITS = {
    "train": 0.8,
    "val": 0.1,
    "test": 0.1,
}


def allocate_split_counts(total: int, split_ratios: dict[str, float]) -> dict[str, int]:
    if total < 0:
        raise ValueError("total must be non-negative")
    if not split_ratios:
        raise ValueError("split_ratios must not be empty")

    ratio_sum = sum(split_ratios.values())
    if not math.isclose(ratio_sum, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("split ratios must sum to 1.0")
    if any(ratio < 0 for ratio in split_ratios.values()):
        raise ValueError("split ratios must be non-negative")

    raw_counts = {
        split_name: total * ratio for split_name, ratio in split_ratios.items()
    }
    split_counts = {
        split_name: int(math.floor(raw_count)) for split_name, raw_count in raw_counts.items()
    }

    remaining = total - sum(split_counts.values())
    ordered_remainders = sorted(
        split_ratios,
        key=lambda split_name: (
            -1 * (raw_counts[split_name] - split_counts[split_name]),
            split_name,
        ),
    )

    for split_name in ordered_remainders[:remaining]:
        split_counts[split_name] += 1

    return split_counts


def assign_splits(
    pair_ids: list[str], split_ratios: dict[str, float], seed: int = 42
) -> dict[str, str]:
    shuffled_pair_ids = list(pair_ids)
    random.Random(seed).shuffle(shuffled_pair_ids)
    split_counts = allocate_split_counts(len(shuffled_pair_ids), split_ratios)

    assignments: dict[str, str] = {}
    start_index = 0

    for split_name in split_ratios:
        end_index = start_index + split_counts[split_name]
        for pair_id in shuffled_pair_ids[start_index:end_index]:
            assignments[pair_id] = split_name
        start_index = end_index

    return assignments


def build_prepared_rows(
    dataset_root: Path,
    split_ratios: dict[str, float] | None = None,
    seed: int = 42,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    split_ratios = split_ratios or DEFAULT_SPLITS
    build_index = _load_build_index()
    rows = build_index(dataset_root)
    prepared_rows = [
        dict(row)
        for row in rows
        if bool(row["has_complete_pdb_pair"]) and bool(row["has_complete_svg_pair"])
    ]

    split_assignments = assign_splits(
        pair_ids=[str(row["pair_id"]) for row in prepared_rows],
        split_ratios=split_ratios,
        seed=seed,
    )

    for row in prepared_rows:
        pair_id = str(row["pair_id"])
        row["split"] = split_assignments[pair_id]
        row["is_complete_pair"] = True

    prepared_rows.sort(key=lambda row: (str(row["split"]), str(row["pair_id"])))

    split_counts = Counter(str(row["split"]) for row in prepared_rows)
    metadata = {
        "dataset_root": str(dataset_root),
        "seed": seed,
        "split_ratios": split_ratios,
        "pair_count": len(prepared_rows),
        "split_counts": dict(split_counts),
    }

    return prepared_rows, metadata


def render_markdown(metadata: dict[str, object], rows: list[dict[str, object]]) -> str:
    preview_rows = rows[:12]
    lines = [
        "# Prepared Dataset",
        "",
        f"- Dataset root: `{metadata['dataset_root']}`",
        f"- Pair count: {metadata['pair_count']}",
        f"- Seed: {metadata['seed']}",
        (
            "- Split counts: "
            + ", ".join(
                f"{split_name}={count}"
                for split_name, count in dict(metadata["split_counts"]).items()
            )
        ),
        "",
        "## Preview",
        "",
        "| pair_id | split | atoms_a | atoms_b | heavy_a | heavy_b |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]

    for row in preview_rows:
        lines.append(
            "| {pair_id} | {split} | {atom_count_a} | {atom_count_b} | "
            "{heavy_atom_count_a} | {heavy_atom_count_b} |".format(
                pair_id=row["pair_id"],
                split=row["split"],
                atom_count_a=row["atom_count_a"],
                atom_count_b=row["atom_count_b"],
                heavy_atom_count_a=row["heavy_atom_count_a"],
                heavy_atom_count_b=row["heavy_atom_count_b"],
            )
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("Usage: python scripts/prepare_dataset.py /path/to/dataset [seed]")
        return 1

    dataset_root = Path(sys.argv[1]).expanduser().resolve()
    if not dataset_root.exists():
        print(f"Dataset directory not found: {dataset_root}")
        return 1

    seed = int(sys.argv[2]) if len(sys.argv) == 3 else 42
    rows, metadata = build_prepared_rows(dataset_root, seed=seed)

    reports_dir = Path("exploration/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_path = reports_dir / "prepared_dataset.csv"
    json_path = reports_dir / "prepared_dataset.json"
    markdown_path = reports_dir / "prepared_dataset.md"

    fieldnames = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps({"metadata": metadata, "rows": rows}, indent=2))
    markdown_path.write_text(render_markdown(metadata, rows))

    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
