from pathlib import Path

from molecular_similarity.tenant_namespace import (
    company_namespace_path,
    company_storage_namespace,
    safe_company_id,
)


def test_safe_company_id_normalizes_untrusted_values() -> None:
    assert safe_company_id(" Example Pharma ") == "example_pharma"
    assert safe_company_id("../Other Company") == "other_company"
    assert safe_company_id("ACME/../../Secrets") == "acme_secrets"


def test_company_namespace_path_stays_under_configured_root(tmp_path: Path) -> None:
    root = tmp_path / "indexes"
    namespace_path = company_namespace_path(root, "../Other Company")

    assert namespace_path == root / "other_company"
    assert namespace_path.resolve().is_relative_to(root.resolve())


def test_company_storage_namespace_uses_same_company_prefix_for_all_roots(
    tmp_path: Path,
) -> None:
    namespace = company_storage_namespace(
        "Example Pharma",
        index_root=tmp_path / "indexes",
        history_root=tmp_path / "history",
        audit_root=tmp_path / "audit",
    )

    assert namespace.company_id == "example_pharma"
    assert namespace.index_dir == tmp_path / "indexes" / "example_pharma"
    assert namespace.history_dir == tmp_path / "history" / "example_pharma"
    assert namespace.audit_dir == tmp_path / "audit" / "example_pharma"
