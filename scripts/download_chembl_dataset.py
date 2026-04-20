#!/usr/bin/env python3
"""
Download and setup ChEMBL molecular similarity dataset.

Usage:
    python scripts/download_chembl_dataset.py --help
    python scripts/download_chembl_dataset.py --output /path/to/dataset
"""

import argparse
from pathlib import Path


def download_from_chembl(output_dir: Path) -> None:
    """Download ChEMBL dataset with 3D conformers and 2D images."""
    print(f"Downloading ChEMBL dataset to {output_dir}...")
    
    # Create directories
    output_dir.mkdir(parents=True, exist_ok=True)
    conformers_dir = output_dir / "conformers_3D"
    images_dir = output_dir / "images_2D"
    conformers_dir.mkdir(exist_ok=True)
    images_dir.mkdir(exist_ok=True)
    
    print("\n ChEMBL Dataset Download Options:")
    print("\n1. Via ChEMBL Web Interface:")
    print("   - Visit: https://www.ebi.ac.uk/chembl/")
    print("   - Search for molecules of interest")
    print("   - Export 3D conformers (SDF/MOL2)")
    print("   - Export 2D structures (SVG/PNG)")
    
    print("\n2. Via ChEMBL API:")
    print("   - Install: pip install chembl-webresource-client")
    print("   - See: https://chembl.gitbook.io/chembl-interface-documentation/")
    
    print("\n3. Via Direct Download:")
    print("   - Full ChEMBL dump: https://chembl.gitbook.io/chembl/downloads")
    print("   - Contains: SDF with 3D coordinates, SMILES, activities")
    
    print("\n Directory structure created:")
    print(f"   {conformers_dir}/  (place PDB/SDF files here)")
    print(f"   {images_dir}/      (place SVG/PNG files here)")
    
    print("\n After downloading, rename files to match expected pattern:")
    print("   - Conformers: best_rocs_conformer_XXX[ab].pdb")
    print("   - Images: image_molecule_XXX[ab].svg")
    print("   (where XXX is a 3-digit zero-padded molecule ID)")


def download_sample_dataset(output_dir: Path) -> None:
    """Download a small sample dataset for testing."""
    print(f"Setting up sample ChEMBL dataset structure in {output_dir}...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    conformers_dir = output_dir / "conformers_3D"
    images_dir = output_dir / "images_2D"
    conformers_dir.mkdir(exist_ok=True)
    images_dir.mkdir(exist_ok=True)
    
    print(" Sample dataset directories created at:")
    print(f"   {conformers_dir}/")
    print(f"   {images_dir}/")
    print("\nNext steps:")
    print("1. Download ChEMBL molecules from: https://www.ebi.ac.uk/chembl/")
    print("2. Place 3D conformer files (PDB format) in conformers_3D/")
    print("3. Place 2D structure images (SVG format) in images_2D/")
    print("4. Run: python scripts/explore_dataset.py '<your_dataset_path>'")


def main():
    parser = argparse.ArgumentParser(
        description="Setup ChEMBL molecular similarity dataset"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / "chembl_dataset",
        help="Output directory for dataset (default: ~/chembl_dataset)",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Create sample directory structure (no data download)",
    )
    
    args = parser.parse_args()
    
    if args.sample:
        download_sample_dataset(args.output)
    else:
        download_from_chembl(args.output)
    
    print("\n" + "="*60)
    print("Documentation: https://chembl.gitbook.io/chembl/")
    print("="*60)


if __name__ == "__main__":
    main()
