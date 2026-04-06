from pathlib import Path

from scripts.build_dataset_index import build_index


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


def test_build_index_returns_expected_rows(tmp_path: Path) -> None:
    _create_dataset_pair(tmp_path, "001")
    _create_dataset_pair(tmp_path, "002")

    rows = build_index(tmp_path)

    assert len(rows) == 2
    assert rows[0]["pair_id"] == "001"
    assert rows[0]["has_complete_pdb_pair"] is True
    assert rows[0]["has_complete_svg_pair"] is True
    assert rows[0]["compound_name_a"] == "pair-001-a"
    assert rows[0]["compound_name_b"] == "pair-001-b"
    assert rows[0]["atom_count_a"] == 2
    assert rows[0]["atom_count_b"] == 3
    assert rows[0]["heavy_atom_count_a"] == 1
    assert rows[0]["heavy_atom_count_b"] == 2
    assert rows[0]["atom_count_delta"] == 1
