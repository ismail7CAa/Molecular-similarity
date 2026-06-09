import json
from pathlib import Path

import faiss
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rdkit import Chem

from molecular_similarity.company_onboarding import (
    build_company_faiss_index,
    create_onboarding_router,
    parse_ra_history_csv,
    parse_sdf,
    parse_smiles_csv,
    write_company_ra_history,
)


def test_parse_smiles_csv_standardizes_valid_compounds() -> None:
    compounds = parse_smiles_csv(
        b"compound_id,name,smiles\nCMPD1,Ethanol,C(C)O\nCMPD2,Bad,not-a-smiles\n"
    )

    assert len(compounds) == 1
    assert compounds[0].compound_id == "CMPD1"
    assert compounds[0].canonical_smiles == "CCO"


def test_parse_sdf_standardizes_valid_compounds() -> None:
    molecule = Chem.MolFromSmiles("CCO")
    molecule.SetProp("_Name", "Ethanol")
    sdf_content = f"{Chem.MolToMolBlock(molecule)}\n$$$$\n".encode()

    compounds = parse_sdf(sdf_content)

    assert len(compounds) == 1
    assert compounds[0].compound_id == "Ethanol"
    assert compounds[0].canonical_smiles == "CCO"


def test_build_company_faiss_index_writes_index_and_metadata(tmp_path: Path) -> None:
    compounds = parse_smiles_csv(b"compound_id,smiles\nCMPD1,CCO\nCMPD2,CCN\n")

    result = build_company_faiss_index(
        company_id="Example Pharma",
        compounds=compounds,
        index_root=tmp_path / "indexes",
    )

    index_path = Path(str(result["index_path"]))
    metadata_path = Path(str(result["metadata_path"]))
    index = faiss.read_index(str(index_path))
    metadata = json.loads(metadata_path.read_text())

    assert index_path == tmp_path / "indexes" / "example_pharma" / "faiss.index"
    assert index.ntotal == 2
    assert metadata["company_id"] == "example_pharma"
    assert metadata["compound_count"] == 2
    assert metadata["compounds"][0]["canonical_smiles"] == "CCO"


def test_onboarding_endpoint_accepts_smiles_csv_upload(tmp_path: Path) -> None:
    app = FastAPI()
    app.include_router(create_onboarding_router(index_root=tmp_path / "indexes"))
    client = TestClient(app)

    response = client.post(
        "/onboarding/library",
        data={"company_id": "Example Pharma"},
        files={
            "file": (
                "library.csv",
                b"compound_id,name,smiles\nCMPD1,Ethanol,CCO\nCMPD2,Ethylamine,CCN\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] == "example_pharma"
    assert payload["compound_count"] == 2
    assert Path(payload["index_path"]).exists()
    assert faiss.read_index(payload["index_path"]).ntotal == 2


def test_onboarding_endpoint_rejects_invalid_library(tmp_path: Path) -> None:
    app = FastAPI()
    app.include_router(create_onboarding_router(index_root=tmp_path / "indexes"))
    client = TestClient(app)

    response = client.post(
        "/onboarding/library",
        data={"company_id": "Example Pharma"},
        files={"file": ("library.csv", b"compound_id,smiles\nCMPD1,not-a-smiles\n")},
    )

    assert response.status_code == 400
    assert "No valid compounds" in response.json()["detail"]


def test_parse_ra_history_csv_maps_compounds_and_outcomes() -> None:
    rows = parse_ra_history_csv(
        (
            "compound_id,chembl_id,name,smiles,ra_outcome,decision_date,jurisdiction,notes\n"
            "CMPD1,CHEMBL1,Ethanol,C(C)O,approved,2025-01-02,FDA,Internal precedent\n"
            "CMPD2,,Bad,not-a-smiles,rejected,2025-01-03,EMA,Bad structure\n"
        ).encode()
    )

    assert len(rows) == 1
    assert rows[0].compound_id == "CMPD1"
    assert rows[0].chembl_id == "CHEMBL1"
    assert rows[0].canonical_smiles == "CCO"
    assert rows[0].ra_outcome == "approved"
    assert rows[0].jurisdiction == "FDA"


def test_write_company_ra_history_writes_parquet(tmp_path: Path) -> None:
    rows = parse_ra_history_csv(
        b"compound_id,smiles,ra_outcome\nCMPD1,CCO,approved\nCMPD2,CCN,review_required\n"
    )

    result = write_company_ra_history(
        company_id="Example Pharma",
        history_rows=rows,
        history_root=tmp_path / "history",
    )

    history_path = Path(str(result["history_path"]))
    import pyarrow.parquet as pq

    table = pq.read_table(history_path)
    records = table.to_pylist()
    assert history_path == tmp_path / "history" / "example_pharma" / "ra_decisions.parquet"
    assert result["history_count"] == 2
    assert records[0]["compound_id"] == "CMPD1"
    assert records[0]["ra_outcome"] == "approved"


def test_onboarding_endpoint_accepts_ra_history_upload(tmp_path: Path) -> None:
    app = FastAPI()
    app.include_router(
        create_onboarding_router(
            index_root=tmp_path / "indexes",
            history_root=tmp_path / "history",
        )
    )
    client = TestClient(app)

    response = client.post(
        "/onboarding/ra-history",
        data={"company_id": "Example Pharma"},
        files={
            "file": (
                "ra_history.csv",
                b"compound_id,smiles,ra_outcome\nCMPD1,CCO,approved\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] == "example_pharma"
    assert payload["history_count"] == 1
    assert Path(payload["history_path"]).exists()


def test_onboarding_endpoint_rejects_ra_history_without_outcome(
    tmp_path: Path,
) -> None:
    app = FastAPI()
    app.include_router(create_onboarding_router(history_root=tmp_path / "history"))
    client = TestClient(app)

    response = client.post(
        "/onboarding/ra-history",
        data={"company_id": "Example Pharma"},
        files={"file": ("ra_history.csv", b"compound_id,smiles\nCMPD1,CCO\n")},
    )

    assert response.status_code == 400
    assert "ra_outcome" in response.json()["detail"]
