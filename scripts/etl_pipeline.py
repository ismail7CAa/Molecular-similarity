"""
SQL ETL Pipeline for ChEMBL Molecular Similarity Data

Flow: Extract (PDB/SDF files) → Transform (parse, normalize) → Load (PostgreSQL/SQLite)
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Optional
import sys


class MolecularETLPipeline:
    """ETL pipeline for loading molecular data into SQL database."""
    
    def __init__(self, db_path: str, db_type: str = "sqlite"):
        """Initialize pipeline with database connection."""
        self.db_path = db_path
        self.db_type = db_type
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection."""
        if self.db_type == "sqlite":
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            print(f"✅ Connected to SQLite: {self.db_path}")
        else:
            raise NotImplementedError(f"Database type {self.db_type} not yet implemented")
    
    def create_schema(self):
        """Create database schema for molecular data."""
        print("📊 Creating database schema...")
        
        # Molecules table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS molecules (
                molecule_id INTEGER PRIMARY KEY,
                chembl_id TEXT UNIQUE,
                compound_name TEXT,
                smiles TEXT,
                inchi TEXT,
                molecular_weight REAL,
                heavy_atom_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Conformers table (3D structures)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS conformers (
                conformer_id INTEGER PRIMARY KEY,
                molecule_id INTEGER NOT NULL,
                conformer_file TEXT,
                atom_count INTEGER,
                heavy_atom_count INTEGER,
                element_composition TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (molecule_id) REFERENCES molecules(molecule_id)
            )
        """)
        
        # Images table (2D structures)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                image_id INTEGER PRIMARY KEY,
                molecule_id INTEGER NOT NULL,
                image_file TEXT,
                format TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (molecule_id) REFERENCES molecules(molecule_id)
            )
        """)
        
        # Molecular pairs (for similarity prediction)
        self.cursor.execute("""
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
            )
        """)
        
        # Activity/Property table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                activity_id INTEGER PRIMARY KEY,
                molecule_id INTEGER NOT NULL,
                assay_type TEXT,
                activity_value REAL,
                unit TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (molecule_id) REFERENCES molecules(molecule_id)
            )
        """)
        
        self.conn.commit()
        print("✅ Schema created successfully")
    
    def load_from_index(self, index_json_path: str):
        """Load molecule pair data from dataset_index.json."""
        print(f"📥 Loading data from {index_json_path}...")
        
        with open(index_json_path, 'r') as f:
            data = json.load(f)
        
        # Ensure we have the pairs data
        pairs = data.get('pairs', [])
        
        for idx, pair in enumerate(pairs):
            pair_id = pair.get('pair_id')
            has_pdb = pair.get('has_complete_pdb_pair')
            has_svg = pair.get('has_complete_svg_pair')
            
            # Insert pair record
            self.cursor.execute("""
                INSERT OR IGNORE INTO molecule_pairs 
                (pair_id, molecule_a_id, molecule_b_id, has_conformer_pair, has_image_pair)
                VALUES (?, ?, ?, ?, ?)
            """, (
                pair_id,
                int(pair_id) * 2 - 1,  # molecule A
                int(pair_id) * 2,      # molecule B
                has_pdb,
                has_svg
            ))
        
        self.conn.commit()
        print(f"✅ Loaded {len(pairs)} molecule pairs")
    
    def export_for_modeling(self, output_path: str):
        """Export processed data as CSV for modeling."""
        print(f"💾 Exporting data to {output_path}...")
        
        query = """
            SELECT 
                pair_id,
                has_conformer_pair,
                has_image_pair,
                similarity_score,
                is_similar
            FROM molecule_pairs
            WHERE has_conformer_pair AND has_image_pair
        """
        
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        
        # Write to CSV
        with open(output_path, 'w') as f:
            f.write("pair_id,has_conformer,has_image,similarity_score,is_similar\n")
            for row in rows:
                f.write(",".join(str(x) for x in row) + "\n")
        
        print(f"✅ Exported {len(rows)} records")
    
    def get_statistics(self):
        """Get pipeline statistics."""
        self.cursor.execute("SELECT COUNT(*) FROM molecules")
        mol_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM molecule_pairs")
        pair_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM molecule_pairs WHERE has_conformer_pair AND has_image_pair")
        complete_count = self.cursor.fetchone()[0]
        
        return {
            "total_molecules": mol_count,
            "total_pairs": pair_count,
            "complete_pairs": complete_count,
            "completeness_pct": round((complete_count / pair_count * 100) if pair_count > 0 else 0, 2)
        }
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("✅ Database connection closed")


def main():
    parser = argparse.ArgumentParser(
        description="SQL ETL Pipeline for ChEMBL Molecular Similarity Data"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="./data/chembl.db",
        help="Database path (default: ./data/chembl.db)"
    )
    parser.add_argument(
        "--index",
        type=str,
        default="./exploration/reports/dataset_index.json",
        help="Path to dataset_index.json file"
    )
    parser.add_argument(
        "--create-schema",
        action="store_true",
        help="Create database schema"
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="Load data from index file"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export data to CSV file"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show pipeline statistics"
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = MolecularETLPipeline(args.db)
    pipeline.connect()
    
    try:
        if args.create_schema:
            pipeline.create_schema()
        
        if args.load:
            if not Path(args.index).exists():
                print(f"⚠️ Index file not found: {args.index}")
                print("Run: python scripts/build_dataset_index.py ./data/chembl")
                return
            pipeline.load_from_index(args.index)
        
        if args.stats:
            stats = pipeline.get_statistics()
            print("\n📈 Pipeline Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        if args.export:
            pipeline.export_for_modeling(args.export)
    
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
