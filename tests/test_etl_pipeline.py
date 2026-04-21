import sqlite3
from pathlib import Path
import json

from scripts.etl_pipeline import MolecularETLPipeline


def _create_source_chembl_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE molecule_dictionary (
            molregno INTEGER PRIMARY KEY,
            pref_name TEXT,
            chembl_id TEXT NOT NULL
        );
        CREATE TABLE compound_structures (
            molregno INTEGER PRIMARY KEY,
            standard_inchi TEXT,
            canonical_smiles TEXT
        );
        CREATE TABLE compound_properties (
            molregno INTEGER PRIMARY KEY,
            full_mwt REAL,
            heavy_atoms INTEGER
        );
        CREATE TABLE assays (
            assay_id INTEGER PRIMARY KEY,
            assay_type TEXT,
            tid INTEGER
        );
        CREATE TABLE target_dictionary (
            tid INTEGER PRIMARY KEY,
            chembl_id TEXT NOT NULL,
            pref_name TEXT NOT NULL
        );
        CREATE TABLE activities (
            activity_id INTEGER PRIMARY KEY,
            assay_id INTEGER NOT NULL,
            molregno INTEGER,
            standard_value REAL,
            standard_units TEXT,
            standard_type TEXT
        );
        """
    )
    conn.executemany(
        """
        INSERT INTO molecule_dictionary (molregno, pref_name, chembl_id)
        VALUES (?, ?, ?)
        """,
        [
            (1, "Example A", "CHEMBL1"),
            (2, "Example B", "CHEMBL2"),
        ],
    )
    conn.executemany(
        """
        INSERT INTO compound_structures (molregno, standard_inchi, canonical_smiles)
        VALUES (?, ?, ?)
        """,
        [
            (1, "InChI=1S/exampleA", "CCO"),
            (2, "InChI=1S/exampleB", "CCN"),
        ],
    )
    conn.executemany(
        """
        INSERT INTO compound_properties (molregno, full_mwt, heavy_atoms)
        VALUES (?, ?, ?)
        """,
        [
            (1, 46.07, 3),
            (2, 45.08, 3),
        ],
    )
    conn.execute(
        """
        INSERT INTO target_dictionary (tid, chembl_id, pref_name)
        VALUES (10, 'CHEMBLT1', 'Target One')
        """
    )
    conn.execute(
        """
        INSERT INTO assays (assay_id, assay_type, tid)
        VALUES (100, 'B', 10)
        """
    )
    conn.executemany(
        """
        INSERT INTO activities
        (activity_id, assay_id, molregno, standard_value, standard_units, standard_type)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (1000, 100, 1, 12.5, "nM", "IC50"),
            (1001, 100, 2, 33.0, "nM", "Ki"),
        ],
    )
    conn.commit()
    conn.close()


def test_import_chembl_sqlite_loads_molecules_and_activities(tmp_path: Path) -> None:
    source_db = tmp_path / "chembl_source.db"
    target_db = tmp_path / "target.db"
    _create_source_chembl_db(source_db)

    pipeline = MolecularETLPipeline(str(target_db))
    pipeline.connect()
    try:
        pipeline.create_schema()
        summary = pipeline.import_chembl_sqlite(
            str(source_db),
            include_activities=True,
        )

        assert summary == {"molecules": 2, "activities": 2}
        molecule_rows = pipeline.conn.execute(
            """
            SELECT molecule_id, chembl_id, compound_name, smiles, inchi, molecular_weight, heavy_atom_count
            FROM molecules
            ORDER BY molecule_id
            """
        ).fetchall()
        activity_rows = pipeline.conn.execute(
            """
            SELECT activity_id, molecule_id, assay_type, activity_value, unit, standard_type,
                   target_chembl_id, target_name, source_assay_id
            FROM activities
            ORDER BY activity_id
            """
        ).fetchall()
    finally:
        pipeline.close()

    assert molecule_rows == [
        (1, "CHEMBL1", "Example A", "CCO", "InChI=1S/exampleA", 46.07, 3),
        (2, "CHEMBL2", "Example B", "CCN", "InChI=1S/exampleB", 45.08, 3),
    ]
    assert activity_rows == [
        (1000, 1, "B", 12.5, "nM", "IC50", "CHEMBLT1", "Target One", 100),
        (1001, 2, "B", 33.0, "nM", "Ki", "CHEMBLT1", "Target One", 100),
    ]


def test_import_compact_chembl_json_loads_molecules_and_activities(
    tmp_path: Path,
) -> None:
    dataset_dir = tmp_path / "chembl_small"
    dataset_dir.mkdir()
    (dataset_dir / "cyp2d6_activities.json").write_text(
        json.dumps(
            {
                "activities": [
                    {
                        "activity_id": 45777,
                        "molecule_chembl_id": "CHEMBL292759",
                        "molecule_pref_name": None,
                        "parent_molecule_chembl_id": "CHEMBL292759",
                        "canonical_smiles": "CCO",
                        "standard_value": "11000.0",
                        "standard_units": "nM",
                        "standard_type": "IC50",
                        "assay_type": "A",
                        "target_chembl_id": "CHEMBL289",
                        "target_pref_name": "Cytochrome P450 2D6",
                    },
                    {
                        "activity_id": 62461,
                        "molecule_chembl_id": "CHEMBL542139",
                        "molecule_pref_name": "Example Compound",
                        "parent_molecule_chembl_id": "CHEMBL431298",
                        "canonical_smiles": "CCN",
                        "standard_value": "32000.0",
                        "standard_units": "nM",
                        "standard_type": "IC50",
                        "assay_type": "A",
                        "target_chembl_id": "CHEMBL289",
                        "target_pref_name": "Cytochrome P450 2D6",
                    },
                ]
            }
        )
    )

    target_db = tmp_path / "target.db"
    pipeline = MolecularETLPipeline(str(target_db))
    pipeline.connect()
    try:
        pipeline.create_schema()
        summary = pipeline.import_compact_chembl_json(str(dataset_dir))

        assert summary == {"molecules": 2, "activities": 2, "source_files": 1}
        molecule_rows = pipeline.conn.execute(
            """
            SELECT molecule_id, chembl_id, compound_name, smiles
            FROM molecules
            ORDER BY molecule_id
            """
        ).fetchall()
        activity_rows = pipeline.conn.execute(
            """
            SELECT activity_id, molecule_id, assay_type, activity_value, unit, standard_type,
                   target_chembl_id, target_name, source_assay_id
            FROM activities
            ORDER BY activity_id
            """
        ).fetchall()
    finally:
        pipeline.close()

    assert molecule_rows == [
        (292759, "CHEMBL292759", "CHEMBL292759", "CCO"),
        (542139, "CHEMBL542139", "Example Compound", "CCN"),
    ]
    assert activity_rows == [
        (45777, 292759, "A", 11000.0, "nM", "IC50", "CHEMBL289", "Cytochrome P450 2D6", None),
        (62461, 542139, "A", 32000.0, "nM", "IC50", "CHEMBL289", "Cytochrome P450 2D6", None),
    ]


def test_generate_activity_pairs_builds_pair_candidates(tmp_path: Path) -> None:
    target_db = tmp_path / "target.db"
    pipeline = MolecularETLPipeline(str(target_db))
    pipeline.connect()
    try:
        pipeline.create_schema()
        pipeline.conn.executemany(
            """
            INSERT INTO molecules (molecule_id, chembl_id, compound_name, smiles)
            VALUES (?, ?, ?, ?)
            """,
            [
                (1, "CHEMBL1", "Mol A", "CCO"),
                (2, "CHEMBL2", "Mol B", "CCN"),
                (3, "CHEMBL3", "Mol C", "CCC"),
            ],
        )
        pipeline.conn.executemany(
            """
            INSERT INTO activities
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
                (10, 1, "B", 10.0, "nM", "Ki", "CHEMBLT1", "Target One", None),
                (11, 2, "B", 12.0, "nM", "Ki", "CHEMBLT1", "Target One", None),
                (12, 3, "B", 1000.0, "nM", "Ki", "CHEMBLT1", "Target One", None),
            ],
        )
        pipeline.conn.commit()

        summary = pipeline.generate_activity_pairs(similarity_threshold=1.0)
        pair_rows = pipeline.conn.execute(
            """
            SELECT
                pair_id,
                molecule_a_id,
                molecule_b_id,
                similarity_score,
                is_similar,
                target_chembl_id,
                standard_type,
                activity_unit,
                activity_delta
            FROM molecule_pairs
            ORDER BY pair_id
            """
        ).fetchall()
    finally:
        pipeline.close()

    assert summary == {"groups": 1, "pairs": 3}
    assert pair_rows == [
        ("ACT_CHEMBLT1_Ki_1_2", 1, 2, 0.9266, 1, "CHEMBLT1", "Ki", "pchembl", 0.0792),
        ("ACT_CHEMBLT1_Ki_1_3", 1, 3, 0.3333, 0, "CHEMBLT1", "Ki", "pchembl", 2.0),
        ("ACT_CHEMBLT1_Ki_2_3", 2, 3, 0.3424, 0, "CHEMBLT1", "Ki", "pchembl", 1.9208),
    ]
