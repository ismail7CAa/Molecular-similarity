import sqlite3
from pathlib import Path

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
