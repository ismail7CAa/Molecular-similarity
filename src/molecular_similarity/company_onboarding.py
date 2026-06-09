from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import Annotated

import faiss
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator

from molecular_similarity.tenant_namespace import company_namespace_path, safe_company_id


DEFAULT_INDEX_ROOT = Path("indexes")
DEFAULT_HISTORY_ROOT = Path("history")
FINGERPRINT_SIZE = 2048
MORGAN_GENERATOR = rdFingerprintGenerator.GetMorganGenerator(
    radius=2,
    fpSize=FINGERPRINT_SIZE,
)
RDLogger.DisableLog("rdApp.warning")


@dataclass(frozen=True)
class StandardizedCompound:
    compound_id: str
    name: str
    canonical_smiles: str


@dataclass(frozen=True)
class RADecisionHistoryRow:
    compound_id: str
    chembl_id: str
    name: str
    canonical_smiles: str
    ra_outcome: str
    decision_date: str
    jurisdiction: str
    notes: str


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


def parse_ra_history_csv(content: bytes) -> list[RADecisionHistoryRow]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("RA history CSV must include a header row")

    field_map = {field.lower().strip(): field for field in reader.fieldnames}
    outcome_field = (
        field_map.get("ra_outcome")
        or field_map.get("outcome")
        or field_map.get("decision")
        or field_map.get("ra_decision")
    )
    if outcome_field is None:
        raise ValueError("RA history CSV must include an ra_outcome, outcome, or decision column")

    smiles_field = field_map.get("smiles") or field_map.get("canonical_smiles")
    compound_id_field = (
        field_map.get("compound_id")
        or field_map.get("molecule_id")
        or field_map.get("id")
    )
    chembl_id_field = field_map.get("chembl_id")
    name_field = field_map.get("name") or field_map.get("compound_name")
    date_field = field_map.get("decision_date") or field_map.get("date")
    jurisdiction_field = field_map.get("jurisdiction")
    notes_field = field_map.get("notes") or field_map.get("rationale")

    history_rows: list[RADecisionHistoryRow] = []
    for row_number, row in enumerate(reader, start=1):
        ra_outcome = (row.get(outcome_field) or "").strip()
        if not ra_outcome:
            continue

        raw_smiles = (row.get(smiles_field) or "").strip() if smiles_field else ""
        compound_id = (
            (row.get(compound_id_field) or "").strip()
            if compound_id_field
            else f"row_{row_number}"
        )
        chembl_id = (row.get(chembl_id_field) or "").strip() if chembl_id_field else ""
        name = (row.get(name_field) or "").strip() if name_field else ""
        canonical_smiles = ""
        if raw_smiles:
            compound = standardize_molecule(
                Chem.MolFromSmiles(raw_smiles),
                compound_id=compound_id or chembl_id or f"row_{row_number}",
                name=name,
            )
            if compound is None:
                continue
            canonical_smiles = compound.canonical_smiles
            compound_id = compound_id or compound.compound_id

        if not any([compound_id, chembl_id, canonical_smiles]):
            continue

        history_rows.append(
            RADecisionHistoryRow(
                compound_id=compound_id or chembl_id or canonical_smiles,
                chembl_id=chembl_id,
                name=name,
                canonical_smiles=canonical_smiles,
                ra_outcome=ra_outcome,
                decision_date=(row.get(date_field) or "").strip() if date_field else "",
                jurisdiction=(
                    (row.get(jurisdiction_field) or "").strip()
                    if jurisdiction_field
                    else ""
                ),
                notes=(row.get(notes_field) or "").strip() if notes_field else "",
            )
        )

    return history_rows


def write_company_ra_history(
    company_id: str,
    history_rows: list[RADecisionHistoryRow],
    history_root: Path = DEFAULT_HISTORY_ROOT,
) -> dict[str, object]:
    if not history_rows:
        raise ValueError("No valid RA history rows found in uploaded CSV")

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError(
            "Writing RA history parquet requires pyarrow. "
            "Install project dependencies with: pip install -e .[dev]"
        ) from error

    normalized_company_id = safe_company_id(company_id)
    company_history_dir = company_namespace_path(history_root, normalized_company_id)
    company_history_dir.mkdir(parents=True, exist_ok=True)
    history_path = company_history_dir / "ra_decisions.parquet"
    rows = [
        {
            "compound_id": row.compound_id,
            "chembl_id": row.chembl_id,
            "name": row.name,
            "canonical_smiles": row.canonical_smiles,
            "ra_outcome": row.ra_outcome,
            "decision_date": row.decision_date,
            "jurisdiction": row.jurisdiction,
            "notes": row.notes,
        }
        for row in history_rows
    ]
    pq.write_table(pa.Table.from_pylist(rows), history_path)
    return {
        "company_id": normalized_company_id,
        "history_count": len(rows),
        "history_path": str(history_path),
    }


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
    company_index_dir = company_namespace_path(index_root, normalized_company_id)
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


def create_onboarding_router(
    index_root: Path = DEFAULT_INDEX_ROOT,
    history_root: Path = DEFAULT_HISTORY_ROOT,
) -> APIRouter:
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

    @router.post("/onboarding/ra-history")
    async def upload_ra_history(
        company_id: Annotated[str, Form(...)],
        file: Annotated[UploadFile, File(...)],
    ) -> dict[str, object]:
        try:
            if Path(file.filename or "").suffix.lower() != ".csv":
                raise ValueError("RA history upload must be a CSV file")
            content = await file.read()
            history_rows = parse_ra_history_csv(content)
            return write_company_ra_history(
                company_id=company_id,
                history_rows=history_rows,
                history_root=history_root,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    return router
