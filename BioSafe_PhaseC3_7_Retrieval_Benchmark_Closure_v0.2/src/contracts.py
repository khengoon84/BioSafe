from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

VALID_METRICS = frozenset({"retrieval", "route", "unknown", "boundary", "support_span", "currentness", "conflict", "leakage", "diversity", "duplicates"})


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    case_type: str
    query: str
    acceptable_claim_ids: tuple[str, ...]
    acceptable_document_ids: tuple[str, ...]
    expected_jurisdiction: str
    expected_source_record_ids: tuple[str, ...]
    forbidden_document_ids: tuple[str, ...]
    required_boundary: str | None
    retrieval_must_be_empty: bool
    metrics: frozenset[str]
    partition: str = "development"

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "BenchmarkCase":
        return cls(row["case_id"], row["case_type"], row["query"], tuple(row.get("acceptable_claim_ids", [])), tuple(row.get("acceptable_document_ids", [])), row.get("expected_jurisdiction", "Unspecified"), tuple(row.get("expected_source_record_ids", [])), tuple(row.get("forbidden_document_ids", [])), row.get("required_boundary"), bool(row.get("retrieval_must_be_empty", False)), frozenset(row.get("metrics", [])), row.get("partition", "development"))


@dataclass
class CaseResult:
    case_id: str
    case_type: str
    partition: str
    ranked_claim_ids: list[str]
    ranked_document_ids: list[str]
    query_profile: dict[str, Any]
    route_ok: bool | None
    retrieval_ok: bool | None
    unknown_fail_closed: bool | None
    boundary_preserved: bool | None
    currentness_ok: bool | None
    conflict_ok: bool | None
    support_span_status: str
    first_acceptable_rank: int | None
    recall_at: dict[str, int] = field(default_factory=dict)
    citation_completeness_at_10: float | None = None
    jurisdiction_leakage_count_at_10: int = 0
    source_diversity_at_10: int = 0
    duplicate_domination_at_10: float = 0.0
    metadata_score_present: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)