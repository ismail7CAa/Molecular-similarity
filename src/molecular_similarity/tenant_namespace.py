from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


COMPANY_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")


def safe_company_id(company_id: object) -> str:
    normalized = COMPANY_ID_PATTERN.sub("_", str(company_id or "").strip())
    normalized = normalized.strip("_").lower()
    if not normalized:
        raise ValueError("company_id must contain at least one alphanumeric character")
    return normalized


def company_namespace_path(root: Path | str, company_id: object) -> Path:
    root_path = Path(root)
    normalized_company_id = safe_company_id(company_id)
    namespace_path = root_path / normalized_company_id
    resolved_root = root_path.resolve()
    resolved_namespace = namespace_path.resolve()
    if resolved_root != resolved_namespace and resolved_root not in resolved_namespace.parents:
        raise ValueError("company namespace path escaped the configured storage root")
    return namespace_path


@dataclass(frozen=True)
class CompanyStorageNamespace:
    company_id: str
    root: Path
    index_dir: Path
    history_dir: Path
    audit_dir: Path


def company_storage_namespace(
    company_id: object,
    *,
    index_root: Path | str = Path("indexes"),
    history_root: Path | str = Path("history"),
    audit_root: Path | str = Path("audit"),
) -> CompanyStorageNamespace:
    normalized_company_id = safe_company_id(company_id)
    return CompanyStorageNamespace(
        company_id=normalized_company_id,
        root=Path("."),
        index_dir=company_namespace_path(index_root, normalized_company_id),
        history_dir=company_namespace_path(history_root, normalized_company_id),
        audit_dir=company_namespace_path(audit_root, normalized_company_id),
    )
