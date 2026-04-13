-- ChEMBL Molecular Similarity ETL Pipeline Schema
-- Database: SQLite / PostgreSQL compatible

-- Core molecules table
CREATE TABLE IF NOT EXISTS molecules (
    molecule_id INTEGER PRIMARY KEY,
    chembl_id TEXT UNIQUE,
    compound_name TEXT,
    smiles TEXT,
    inchi TEXT,
    molecular_weight REAL,
    heavy_atom_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3D conformer details
CREATE TABLE IF NOT EXISTS conformers (
    conformer_id INTEGER PRIMARY KEY,
    molecule_id INTEGER NOT NULL,
    conformer_file TEXT,
    atom_count INTEGER,
    heavy_atom_count INTEGER,
    element_composition TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (molecule_id) REFERENCES molecules(molecule_id)
);

-- 2D structure images
CREATE TABLE IF NOT EXISTS images (
    image_id INTEGER PRIMARY KEY,
    molecule_id INTEGER NOT NULL,
    image_file TEXT,
    format TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (molecule_id) REFERENCES molecules(molecule_id)
);

-- Molecular pairs for similarity prediction
CREATE TABLE IF NOT EXISTS molecule_pairs (
    pair_id TEXT PRIMARY KEY,
    molecule_a_id INTEGER NOT NULL,
    molecule_b_id INTEGER NOT NULL,
    has_conformer_pair BOOLEAN,
    has_image_pair BOOLEAN,
    similarity_score REAL,
    is_similar BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (molecule_a_id) REFERENCES molecules(molecule_id),
    FOREIGN KEY (molecule_b_id) REFERENCES molecules(molecule_id)
);

-- Bioactivity data
CREATE TABLE IF NOT EXISTS activities (
    activity_id INTEGER PRIMARY KEY,
    molecule_id INTEGER NOT NULL,
    assay_type TEXT,
    activity_value REAL,
    unit TEXT,
    standard_type TEXT,
    target_chembl_id TEXT,
    target_name TEXT,
    source_assay_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (molecule_id) REFERENCES molecules(molecule_id)
);

-- Create indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_molecules_chembl ON molecules(chembl_id);
CREATE INDEX IF NOT EXISTS idx_conformers_molecule ON conformers(molecule_id);
CREATE INDEX IF NOT EXISTS idx_images_molecule ON images(molecule_id);
CREATE INDEX IF NOT EXISTS idx_pairs_has_complete ON molecule_pairs(has_conformer_pair, has_image_pair);
CREATE INDEX IF NOT EXISTS idx_activities_molecule ON activities(molecule_id);
