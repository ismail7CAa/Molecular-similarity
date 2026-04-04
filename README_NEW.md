# Molecular Similarity

A cheminformatics project focused on computing, analyzing, and visualizing molecular similarity using structured molecular representations and reproducible data pipelines. This repository is designed as a foundation for similarity-based virtual screening and AI-driven drug discovery workflows.

## Overview
Molecular similarity is a central concept in computational chemistry and drug discovery. Structurally similar molecules often exhibit similar physicochemical or biological properties. This project provides a modular pipeline for transforming molecular structures into comparable representations and computing similarity metrics in a reproducible manner.

## Objectives
- preprocess molecular datasets
- compute molecular representations (e.g., descriptors, fingerprints)
- evaluate similarity between compounds
- visualize similarity distributions
- prepare integration with machine learning and deep learning models

## Project Structure
```
Molecular-similarity/
│── scripts/                 # data processing and exploration scripts
│── exploration/            # reports and dataset summaries
│── .github/workflows/      # CI/CD pipelines
│── README.md
```

## Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage
```bash
python scripts/explore_dataset.py "/path/to/dataset"
```

## Future Work
- integration of graph neural networks
- 3D molecular similarity using geometric deep learning
- pharmacophore-based similarity scoring

## Author
Ismail Cherkaoui Aadil
