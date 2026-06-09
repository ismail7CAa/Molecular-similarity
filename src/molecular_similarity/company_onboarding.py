from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import Annotated

import faiss
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator


DEFAULT_INDEX_ROOT = Path("indexes")
FINGERPRINT_SIZE = 2048
MORGAN_GENERATOR = rdFingerprintGenerator.GetMorganGenerator(
    radius=2,
    fpSize=FINGERPRINT_SIZE,
)
COMPANY_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")
RDLogger.DisableLog("rdApp.warning")


@dataclass(frozen=True)
class StandardizedCompound:
    compound_id: str
    name: str
    canonical_smiles: str


def safe_company_id(company_id: str) -> str:
    normalized = COMPANY_ID_PATTERN.sub("_", company_id.strip())
    normalized = normalized.strip("_").lower()
    if not normalized:
        raise ValueError("company_id must contain at least one alphanumeric character")
    return normalized


def standardize_molecule(
    molecule: Chem.Mol | None,
    compound_id: str,
    name: str = "",
) -> StandardizedCompound | None:
    if molecule is None:
        return None

    try:
        Chem.SanitizeMol(molecule)
    except Exception:
        return None

    canonical_smiles = Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)
    if not canonical_smiles:
        return None

    return StandardizedCompound(
        compound_id=compound_id or canonical_smiles,
        name=name,
        canonical_smiles=canonical_smiles,
    )


def parse_smiles_csv(content: bytes) -> list[StandardizedCompound]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("SMILES CSV must include a header row")

    field_map = {field.lower().strip(): field for field in reader.fieldnames}
    smiles_field = field_map.get("smiles") or field_map.get("canonical_smiles")
    if smiles_field is None:
        raise ValueError("SMILES CSV must include a smiles or canonical_smiles column")

    id_field = (
        field_map.get("compound_id")
        or field_map.get("molecule_id")
        or field_map.get("chembl_id")
        or field_map.get("id")
    )
    name_field = field_map.get("name") or field_map.get("compound_name")

    compounds: list[StandardizedCompound] = []
    for row_number, row in enumerate(reader, start=1):
        raw_smiles = (row.get(smiles_field) or "").strip()
        if not raw_smiles:
            continue
        compound_id = (row.get(id_field) or f"row_{row_number}") if id_field else f"row_{row_number}"
        name = (row.get(name_field) or "") if name_field else ""
        compound = standardize_molecule(
            Chem.MolFromSmiles(raw_smiles),
            compound_id=compound_id,
            name=name,
        )
        if compound is not None:
            compounds.append(compound)

    return compounds


def parse_sdf(content: bytes) -> list[StandardizedCompound]:
    supplier = Chem.ForwardSDMolSupplier(BytesIO(content))
    compounds: list[StandardizedCompound] = []
    for index, molecule in enumerate(supplier, start=1):
        if molecule is None:
            continue
        compound_id = (
            molecule.GetProp("compound_id")
            if molecule.HasProp("compound_id")
            else molecule.GetProp("_Name")
            if molecule.HasProp("_Name")
            else f"sdf_{index}"
        )
        name = molecule.GetProp("_Name") if molecule.HasProp("_Name") else ""
        compound = standardize_molecule(molecule, compound_id=compound_id, name=name)
        if compound is not None:
            compounds.append(compound)
    return compounds


def parse_library_upload(filename: str, content: bytes) -> list[StandardizedCompound]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".sdf":
        return parse_sdf(content)
    if suffix in {".csv", ".smi", ".smiles", ".txt"}:
        return parse_smiles_csv(content)
    raise ValueError("Unsupported library format. Upload SDF or SMILES CSV.")


def fingerprint_matrix(compounds: list[StandardizedCompound]) -> np.ndarray:
    matrix = np.zeros((len(compounds), FINGERPRINT_SIZE), dtype=np.float32)
    for row_index, compound in enumerate(compounds):
        molecule = Chem.MolFromSmiles(compound.canonical_smiles)
        fingerprint = MORGAN_GENERATOR.GetFingerprint(molecule)
        bit_array = np.zeros((FINGERPRINT_SIZE,), dtype=np.int8)
        DataStructs.ConvertToNumpyArray(fingerprint, bit_array)
        matrix[row_index] = bit_array.astype(np.float32)
    faiss.normalize_L2(matrix)
    return matrix


def build_company_faiss_index(
    company_id: str,
    compounds: list[StandardizedCompound],
    index_root: Path = DEFAULT_INDEX_ROOT,
) -> dict[str, object]:
    if not compounds:
        raise ValueError("No valid compounds found in uploaded library")

    normalized_company_id = safe_company_id(company_id)
    company_index_dir = index_root / normalized_company_id
    company_index_dir.mkdir(parents=True, exist_ok=True)

    vectors = fingerprint_matrix(compounds)
    index = faiss.IndexFlatIP(FINGERPRINT_SIZE)
    index.add(vectors)

    index_path = company_index_dir / "faiss.index"
    metadata_path = company_index_dir / "metadata.json"
    faiss.write_index(index, str(index_path))
    metadata = {
        "company_id": normalized_company_id,
        "index_type": "IndexFlatIP",
        "metric": "cosine_similarity_on_l2_normalized_morgan_radius2",
        "fingerprint_size": FINGERPRINT_SIZE,
        "compound_count": len(compounds),
        "compounds": [
            {
                "row_id": row_id,
                "compound_id": compound.compound_id,
                "name": compound.name,
                "canonical_smiles": compound.canonical_smiles,
            }
            for row_id, compound in enumerate(compounds)
        ],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return {
        "company_id": normalized_company_id,
        "compound_count": len(compounds),
        "index_path": str(index_path),
        "metadata_path": str(metadata_path),
    }


def create_onboarding_router(index_root: Path = DEFAULT_INDEX_ROOT) -> APIRouter:
    router = APIRouter()

    @router.post("/onboarding/library")
    async def upload_company_library(
        company_id: Annotated[str, Form(...)],
        file: Annotated[UploadFile, File(...)],
    ) -> dict[str, object]:
        try:
            content = await file.read()
            compounds = parse_library_upload(file.filename or "", content)
            return build_company_faiss_index(
                company_id=company_id,
                compounds=compounds,
                index_root=index_root,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    return router
