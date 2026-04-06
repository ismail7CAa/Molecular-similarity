from pathlib import Path

from scripts.prepare_dataset import (
    allocate_split_counts,
    assign_splits,
    build_prepared_rows,
)


def _write_pdb(path: Path, compound_name: str, atom_lines: list[str]) -> None:
    content = [f"COMPND {compound_name}\n", *atom_lines, "END\n"]
    path.write_text("".join(content))


def _pdb_atom_line(serial: int, atom_name: str, element: str) -> str:
    return (
        f"HETATM{serial:5d} {atom_name:<4} MOL A   1      "
        f"{0.0:8.3f}{0.0:8.3f}{0.0:8.3f}{1.00:6.2f}{0.00:6.2f}"
        f"          {element:>2}\n"
    )


def _create_dataset_pair(dataset_root: Path, pair_id: str) -> None:
    conformers_dir = dataset_root / "conformers_3D"
    images_dir = dataset_root / "images_2D"
    conformers_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    _write_pdb(
        conformers_dir / f"best_rocs_conformer_{pair_id}a.pdb",
        compound_name=f"pair-{pair_id}-a",
        atom_lines=[
            _pdb_atom_line(1, "C1", "C"),
            _pdb_atom_line(2, "H1", "H"),
        ],
    )
    _write_pdb(
        conformers_dir / f"best_rocs_conformer_{pair_id}b.pdb",
        compound_name=f"pair-{pair_id}-b",
        atom_lines=[
            _pdb_atom_line(1, "C1", "C"),
            _pdb_atom_line(2, "N1", "N"),
            _pdb_atom_line(3, "H1", "H"),
        ],
    )
    (images_dir / f"image_molecule_{pair_id}a.svg").write_text("<svg></svg>\n")
    (images_dir / f"image_molecule_{pair_id}b.svg").write_text("<svg></svg>\n")


def test_allocate_split_counts_uses_full_dataset() -> None:
    counts = allocate_split_counts(10, {"train": 0.8, "val": 0.1, "test": 0.1})

    assert counts == {"train": 8, "val": 1, "test": 1}


def test_assign_splits_is_deterministic() -> None:
    pair_ids = [f"{index:03d}" for index in range(1, 11)]

    first = assign_splits(pair_ids, {"train": 0.8, "val": 0.1, "test": 0.1}, seed=7)
    second = assign_splits(pair_ids, {"train": 0.8, "val": 0.1, "test": 0.1}, seed=7)

    assert first == second
    assert sorted(first.values()).count("train") == 8
    assert sorted(first.values()).count("val") == 1
    assert sorted(first.values()).count("test") == 1


def test_build_prepared_rows_filters_incomplete_pairs(tmp_path: Path) -> None:
    for index in range(1, 11):
        _create_dataset_pair(tmp_path, f"{index:03d}")

    incomplete_svg = tmp_path / "images_2D" / "image_molecule_010b.svg"
    incomplete_svg.unlink()

    rows, metadata = build_prepared_rows(tmp_path, seed=11)

    assert len(rows) == 9
    assert metadata["pair_count"] == 9
    assert sum(metadata["split_counts"].values()) == 9
    assert all(row["is_complete_pair"] is True for row in rows)
    assert all(row["pair_id"] != "010" for row in rows)
