from __future__ import annotations

from collections import Counter
from typing import Any

from contracts import CaseResult


def _rate(values: list[bool]) -> float:
    return sum(values) / len(values) if values else 1.0


def summarize(rows: list[CaseResult]) -> dict[str, Any]:
    independent = [r for r in rows if r.case_type == "independent_claim"]
    applicable = lambda name: [r for r in rows if getattr(r, name) is not None]
    relevant = [r for r in rows if r.first_acceptable_rank is not None or r.support_span_status == "NO_ACCEPTABLE_HIT"]
    gates = {
        "canonical_independent_coverage": all(r.retrieval_ok for r in independent),
        "all_evidence_case_coverage": all(r.retrieval_ok for r in relevant),
        "canonical_route_accuracy": all(r.route_ok for r in independent),
        "unknown_fail_closed": all(r.unknown_fail_closed for r in applicable("unknown_fail_closed")),
        "boundary_preserved": all(r.boundary_preserved for r in applicable("boundary_preserved")),
        "currentness_preserved": all(r.currentness_ok for r in applicable("currentness_ok")),
        "conflict_fails_closed": all(r.conflict_ok for r in applicable("conflict_ok")),
        "support_spans_complete": all(r.support_span_status in {"COMPLETE", "NOT_APPLICABLE"} for r in rows),
        "no_jurisdiction_leakage": all(r.jurisdiction_leakage_count_at_10 == 0 for r in rows if r.route_ok is not None),
        "fixture_onboarding": all(r.retrieval_ok for r in rows if r.case_type == "new_document_fixture"),
    }
    return {"case_counts": dict(Counter(r.case_type for r in rows)), **{f"recall_at_{k}": _rate([bool(r.recall_at.get(str(k))) for r in relevant]) for k in (1, 3, 5, 10)}, "mean_reciprocal_rank": sum(1 / r.first_acceptable_rank for r in relevant if r.first_acceptable_rank) / len(relevant) if relevant else 1.0, "independent_recall_at_10": _rate([bool(r.retrieval_ok) for r in independent]), "independent_route_accuracy": _rate([bool(r.route_ok) for r in independent]), "unknown_fail_closed_rate": _rate([bool(r.unknown_fail_closed) for r in applicable("unknown_fail_closed")]), "boundary_preservation_rate": _rate([bool(r.boundary_preserved) for r in applicable("boundary_preserved")]), "citation_complete_rate": _rate([r.support_span_status == "COMPLETE" for r in rows if r.support_span_status not in {"NOT_APPLICABLE", "NO_ACCEPTABLE_HIT"}]), "mean_source_diversity_at_10": sum(r.source_diversity_at_10 for r in rows) / len(rows), "max_duplicate_domination_at_10": max((r.duplicate_domination_at_10 for r in rows), default=0.0), "jurisdiction_leakage_total_at_10": sum(r.jurisdiction_leakage_count_at_10 for r in rows), "hard_gates": gates}


def metadata_comparison(on: list[CaseResult], off: list[CaseResult]) -> dict[str, Any]:
    by_off = {r.case_id: r for r in off}; changed=[]; improved=[]; harmed=[]
    for row in on:
        base=by_off[row.case_id]
        if row.ranked_claim_ids != base.ranked_claim_ids: changed.append(row.case_id)
        if row.first_acceptable_rank and (not base.first_acceptable_rank or row.first_acceptable_rank < base.first_acceptable_rank): improved.append(row.case_id)
        if base.first_acceptable_rank and (not row.first_acceptable_rank or row.first_acceptable_rank > base.first_acceptable_rank): harmed.append(row.case_id)
    return {"ranking_changed_case_count":len(changed), "ranking_changed_case_ids":changed, "rank_improved_case_ids":improved, "rank_harmed_case_ids":harmed, "metadata_scores_present":any(r.metadata_score_present for r in on)}