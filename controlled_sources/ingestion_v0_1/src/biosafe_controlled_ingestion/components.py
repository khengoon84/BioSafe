from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .contracts import ValidationError


ACTIVATION_PROHIBITED = "PROHIBITED_PENDING_PHASE_C_GATES"
CLAIM_REVIEW_REQUIRED = "REVIEW_REQUIRED_BEFORE_CLAIM_USE"


@dataclass(frozen=True)
class ComponentSpan:
    pdf_page_start: int
    pdf_page_end: int
    start_at: str = ""
    end_before: str = ""

    def validate(self) -> None:
        if self.pdf_page_start < 1 or self.pdf_page_end < self.pdf_page_start:
            raise ValidationError("component span page range is invalid")
        if self.start_at and self.end_before and self.start_at == self.end_before:
            raise ValidationError("component span markers must differ")


@dataclass(frozen=True)
class ComponentPolicy:
    component_id: str
    document_id: str
    source_sha256: str
    title: str
    component_type: str
    spans: tuple[ComponentSpan, ...]
    allowed_domains: tuple[str, ...]
    excluded_domains: tuple[str, ...]
    review_status: str
    candidate_excluded_pages: tuple[int, ...] = ()

    def validate(self, expected_page_count: int) -> None:
        required = (self.component_id, self.document_id, self.title, self.component_type, self.review_status)
        if any(not isinstance(value, str) or not value.strip() for value in required):
            raise ValidationError("component required strings must be non-empty")
        if not self.component_id.startswith(f"{self.document_id}:"):
            raise ValidationError("component_id must be namespaced by document_id")
        if len(self.source_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_sha256):
            raise ValidationError("component source_sha256 must be a lowercase SHA-256 digest")
        if not self.spans or not self.allowed_domains:
            raise ValidationError("component spans and allowed_domains must not be empty")
        if set(self.allowed_domains) & set(self.excluded_domains):
            raise ValidationError("component allowed_domains and excluded_domains must not overlap")
        for span in self.spans:
            span.validate()
            if span.pdf_page_end > expected_page_count:
                raise ValidationError(f"{self.component_id} exceeds the configured PDF page count")
        included_pages = {
            page for span in self.spans
            for page in range(span.pdf_page_start, span.pdf_page_end + 1)
        }
        invalid_exclusions = set(self.candidate_excluded_pages) - included_pages
        if invalid_exclusions:
            raise ValidationError(
                f"{self.component_id} candidate exclusions are outside its spans: "
                f"{sorted(invalid_exclusions)}"
            )


def load_component_map(path: Path) -> tuple[dict[str, Any], tuple[ComponentPolicy, ...]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("component map must prohibit live activation")
    policies: list[ComponentPolicy] = []
    component_ids: set[str] = set()
    for document_id, document in raw.get("documents", {}).items():
        source_sha256 = document["source_sha256"]
        expected_page_count = int(document["expected_pdf_page_count"])
        allow_disjoint_within_page = bool(document.get("allow_disjoint_within_page_components", False))
        occupied_pages: set[int] = set()
        for item in document.get("components", []):
            spans = tuple(ComponentSpan(**span) for span in item["spans"])
            policy = ComponentPolicy(
                component_id=item["component_id"], document_id=document_id,
                source_sha256=source_sha256, title=item["title"],
                component_type=item["component_type"], spans=spans,
                allowed_domains=tuple(item["allowed_domains"]),
                excluded_domains=tuple(item["excluded_domains"]),
                review_status=item["review_status"],
                candidate_excluded_pages=tuple(item.get("candidate_excluded_pages", ())),
            )
            policy.validate(expected_page_count)
            if policy.component_id in component_ids:
                raise ValidationError(f"duplicate component_id: {policy.component_id}")
            component_ids.add(policy.component_id)
            pages = {page for span in spans for page in range(span.pdf_page_start, span.pdf_page_end + 1)}
            overlap = occupied_pages & pages
            if overlap and not allow_disjoint_within_page:
                raise ValidationError(f"overlapping component pages for {document_id}: {sorted(overlap)}")
            occupied_pages.update(pages)
            policies.append(policy)
    return raw, tuple(policies)


def _bounded_text(text: str, span: ComponentSpan, component_id: str) -> tuple[str, dict[str, int]]:
    start = 0
    end = len(text)
    marker_positions: dict[str, int] = {}
    if span.start_at:
        count = text.count(span.start_at)
        if count != 1:
            raise ValidationError(f"{component_id} start marker count is {count}, expected 1")
        start = text.index(span.start_at)
        marker_positions["start_at_character"] = start
    if span.end_before:
        count = text.count(span.end_before)
        if count != 1:
            raise ValidationError(f"{component_id} end marker count is {count}, expected 1")
        end = text.index(span.end_before)
        marker_positions["end_before_character"] = end
    if (span.start_at or span.end_before) and start >= end:
        raise ValidationError(f"{component_id} markers produce an empty or reversed span")
    return text[start:end].rstrip(), marker_positions


def build_component_artifact(
    extraction_report: dict[str, Any], policies: Iterable[ComponentPolicy]
) -> dict[str, Any]:
    documents = {item["document_id"]: item for item in extraction_report["documents"]}
    components: list[dict[str, Any]] = []
    candidate_chunks: list[dict[str, Any]] = []
    citation_pages: list[dict[str, Any]] = []
    selected_intervals: dict[tuple[str, int], list[tuple[int, int, str]]] = {}
    for policy in policies:
        if policy.document_id not in documents:
            raise ValidationError(f"missing extraction document: {policy.document_id}")
        document = documents[policy.document_id]
        if document["source_sha256"] != policy.source_sha256:
            raise ValidationError(f"source hash mismatch for {policy.document_id}")
        pages_by_index = {int(page["pdf_page_index"]): page for page in document["pages"]}
        component_pages: list[dict[str, Any]] = []
        for span in policy.spans:
            for page_index in range(span.pdf_page_start, span.pdf_page_end + 1):
                if page_index not in pages_by_index:
                    raise ValidationError(f"missing page {page_index} for {policy.document_id}")
                source_page = pages_by_index[page_index]
                text, marker_positions = _bounded_text(source_page["text"], span, policy.component_id)
                selected_start = marker_positions.get("start_at_character", 0)
                selected_end = marker_positions.get("end_before_character", len(source_page["text"]))
                key = (policy.document_id, page_index)
                for prior_start, prior_end, prior_component in selected_intervals.get(key, []):
                    if max(selected_start, prior_start) < min(selected_end, prior_end):
                        raise ValidationError(
                            f"overlapping text spans on {policy.document_id} page {page_index}: "
                            f"{prior_component} and {policy.component_id}"
                        )
                selected_intervals.setdefault(key, []).append(
                    (selected_start, selected_end, policy.component_id)
                )
                marker_positions["selected_character_start"] = selected_start
                marker_positions["selected_character_end"] = selected_end
                page_record = {
                    "pdf_page_index": page_index,
                    "pdf_page_label": source_page["pdf_page_label"],
                    "printed_page_label": source_page["printed_page_label"],
                    "printed_page_verification_status": (
                        "VERIFIED" if source_page["printed_page_label"] else "UNVERIFIED"
                    ),
                    "text": text,
                    "extraction_method": source_page["extraction_method"],
                    "extraction_warnings": source_page["extraction_warnings"],
                    "boundary_positions": marker_positions,
                }
                component_pages.append(page_record)
                citation_pages.append({
                    "component_id": policy.component_id,
                    "document_id": policy.document_id,
                    "source_sha256": policy.source_sha256,
                    "pdf_page_index": page_index,
                    "pdf_page_label": source_page["pdf_page_label"],
                    "printed_page_label": source_page["printed_page_label"],
                    "printed_page_verification_status": page_record["printed_page_verification_status"],
                    "component_local_page": len(component_pages),
                })
                if text.strip() and page_index not in policy.candidate_excluded_pages:
                    candidate_chunks.append({
                        "candidate_chunk_id": f"{policy.component_id}:PDF_PAGE_{page_index}",
                        "component_id": policy.component_id,
                        "document_id": policy.document_id,
                        "source_sha256": policy.source_sha256,
                        "title": policy.title,
                        "component_type": policy.component_type,
                        "pdf_page_start": page_index,
                        "pdf_page_end": page_index,
                        "pdf_page_label": source_page["pdf_page_label"],
                        "printed_page_label": source_page["printed_page_label"],
                        "text": text,
                        "scope_domains": list(policy.allowed_domains),
                        "excluded_domains": list(policy.excluded_domains),
                        "extraction_method": source_page["extraction_method"],
                        "extraction_warnings": source_page["extraction_warnings"],
                        "claim_use_status": CLAIM_REVIEW_REQUIRED,
                        "live_activation_status": ACTIVATION_PROHIBITED,
                    })
        components.append({
            "component_id": policy.component_id,
            "document_id": policy.document_id,
            "source_sha256": policy.source_sha256,
            "title": policy.title,
            "component_type": policy.component_type,
            "spans": [asdict(span) for span in policy.spans],
            "allowed_domains": list(policy.allowed_domains),
            "excluded_domains": list(policy.excluded_domains),
            "review_status": policy.review_status,
            "candidate_excluded_pages": list(policy.candidate_excluded_pages),
            "page_record_count": len(component_pages),
            "nonempty_page_count": sum(bool(page["text"].strip()) for page in component_pages),
            "total_characters": sum(len(page["text"]) for page in component_pages),
            "pages": component_pages,
            "live_activation_status": ACTIVATION_PROHIBITED,
        })
    return {
        "artifact_version": "BioSafe_Component_Candidates_v0.1",
        "source_extraction_report_version": extraction_report.get("report_version", ""),
        "live_activation_status": ACTIVATION_PROHIBITED,
        "claim_use_status": CLAIM_REVIEW_REQUIRED,
        "components": components,
        "candidate_chunks": candidate_chunks,
        "citation_page_map": citation_pages,
    }


def build_review_ledger(
    extraction_report: dict[str, Any], component_map: dict[str, Any]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    fixed_pages: set[tuple[str, int]] = set()
    excluded_pages: set[tuple[str, int]] = set()
    for item in component_map.get("fixed_review_dispositions", []):
        for page in range(int(item["pdf_page_start"]), int(item["pdf_page_end"]) + 1):
            fixed_pages.add((item["document_id"], page))
            if item["disposition"].startswith("EXCLUDE_"):
                excluded_pages.add((item["document_id"], page))
            rows.append({
                "document_id": item["document_id"], "pdf_page_index": str(page),
                "warning": "", "disposition": item["disposition"],
                "review_basis": item["review_basis"], "notes": item["notes"],
            })
    warning_dispositions: dict[tuple[str, int, str], dict[str, Any]] = {}
    for item in component_map.get("warning_dispositions", []):
        for page in item["pdf_pages"]:
            warning_dispositions[(item["document_id"], int(page), item["warning"])] = item
    for document in extraction_report["documents"]:
        for page in document["pages"]:
            key = (document["document_id"], int(page["pdf_page_index"]))
            for warning in page["extraction_warnings"]:
                if key in excluded_pages or (key in fixed_pages and "EMPTY" in warning):
                    continue
                reviewed = warning_dispositions.get((key[0], key[1], warning))
                rows.append({
                    "document_id": document["document_id"],
                    "pdf_page_index": str(page["pdf_page_index"]),
                    "warning": warning,
                    "disposition": reviewed["disposition"] if reviewed else "REVIEW_PENDING",
                    "review_basis": reviewed["review_basis"] if reviewed else "EXTRACTION_WARNING",
                    "notes": reviewed["notes"] if reviewed else "Must be dispositioned before consequential claim use.",
                })
    return sorted(rows, key=lambda row: (row["document_id"], int(row["pdf_page_index"]), row["warning"]))


def write_json_atomic(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_review_ledger(rows: Iterable[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ("document_id", "pdf_page_index", "warning", "disposition", "review_basis", "notes")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)