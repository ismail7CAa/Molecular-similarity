import sqlite3
from pathlib import Path

from scripts.build_enriched_molecules import build_enriched_molecule_rows


def _create_enriched_source_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE molecules (
            molecule_id INTEGER PRIMARY KEY,
            chembl_id TEXT,
            compound_name TEXT,
            smiles TEXT,
            inchi TEXT,
            molecular_weight REAL,
            heavy_atom_count INTEGER,
            max_phase REAL,
            therapeutic_area TEXT,
            indication_count INTEGER,
            first_approval INTEGER,
            black_box_warning INTEGER,
            molecule_type TEXT,
            oral INTEGER,
            parenteral INTEGER,
            topical INTEGER,
            regulatory_alert_count INTEGER,
            regulatory_alerts TEXT,
            alerts_nitrosamine INTEGER,
            alerts_epoxide INTEGER,
            alerts_aziridine INTEGER,
            alerts_alkyl_halide INTEGER,
            alerts_aldehyde INTEGER,
            alerts_hydrazine INTEGER,
            alerts_aromatic_amine INTEGER,
            alerts_michael_acceptor INTEGER,
            alerts_acyl_halide INTEGER,
            alerts_sulfonate_ester INTEGER,
            alerts_azo INTEGER,
            alerts_nitro_aromatic INTEGER,
            alerts_polycyclic_aromatic INTEGER,
            alerts_pains INTEGER
        );
        """
    )
    conn.executemany(
        """
        INSERT INTO molecules
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        [
            (
                1,
                "CHEMBL1",
                "Example A",
                "CCO",
                "InChI=1S/example",
                46.07,
                3,
                4,
                "Oncology",
                2,
                2001,
                1,
                "Small molecule",
                1,
                0,
                0,
                1,
                "Target liability",
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ),
            (
                2,
                "CHEMBL2",
                "Invalid",
                "not-a-smiles",
                "",
                None,
                None,
                0,
                None,
                0,
                None,
                0,
                "",
                0,
                0,
                0,
                0,
                "",
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ),
        ],
    )
    conn.commit()
    conn.close()


def test_build_enriched_molecule_rows_adds_fingerprints_and_ra_metadata(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "chembl.db"
    _create_enriched_source_db(db_path)

    rows = build_enriched_molecule_rows(db_path)

    assert len(rows) == 1
    row = rows[0]
    assert row["chembl_id"] == "CHEMBL1"
    assert len(str(row["morgan_fp_radius2"])) == 2048
    assert len(str(row["morgan_fp_radius3"])) == 2048
    assert len(str(row["maccs_fp"])) == 167
    assert row["max_phase"] == 4.0
    assert row["first_approval"] == 2001
    assert row["therapeutic_area"] == "Oncology"
    assert row["therapeutic_flag"] == 1
    assert row["black_box_warning"] == 1
    assert row["alerts_nitrosamine"] == 0
