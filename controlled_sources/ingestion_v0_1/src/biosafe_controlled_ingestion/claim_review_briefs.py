from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .claim_reconciliation import (
    ALLOWED_DISPOSITIONS,
    REQUIRED_ATTESTATIONS,
    REQUIRED_CHECKS,
)
from .components import ACTIVATION_PROHIBITED, CLAIM_REVIEW_REQUIRED
from .contracts import ValidationError


BRIEF_VERSION = "BioSafe_Pending_Claim_Review_Briefs_v0.1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _blockquote(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.strip().splitlines())


def _page_hint(item: dict[str, Any]) -> str:
    hint = item["page_hint"]
    if hint is None:
        return "None; manual navigation required"
    return (
        f"PDF pages {hint['pdf_page_start']}–{hint['pdf_page_end']} "
        f"(`{hint['basis']}`; navigation only)"
    )


def _native_suggestions(item: dict[str, Any]) -> list[str]:
    suggestions = item["native_candidate_suggestions"]
    if not suggestions:
        return ["_No native candidate suggestions on the hinted pages._"]
    lines: list[str] = []
    for candidate in suggestions:
        lines.extend([
            f"#### `{candidate['candidate_chunk_id']}`",
            "",
            f"Component `{candidate['component_id']}`; PDF pages "
            f"{candidate['pdf_page_start']}–{candidate['pdf_page_end']}; source SHA-256 "
            f"`{candidate['source_sha256']}`.",
            "",
            _blockquote(candidate["text"]),
            "",
        ])
    return lines


def _fallback_suggestions(item: dict[str, Any]) -> list[str]:
    suggestions = item["reviewed_fallback_suggestions"]
    if not suggestions:
        return ["_No accepted reviewed fallback suggestions on the hinted pages._"]
    lines: list[str] = []
    for fallback in suggestions:
        lines.extend([
            f"#### `{fallback['fallback_unit_id']}`",
            "",
            f"Component `{fallback['component_id']}`; PDF page "
            f"{fallback['pdf_page_index']}; source SHA-256 "
            f"`{fallback['source_sha256']}`.",
            "",
            "```json",
            json.dumps(fallback["structured_representation"], indent=2, ensure_ascii=False),
            "```",
            "",
            "Limitations: " + (
                "; ".join(fallback["limitations"])
                if fallback["limitations"] else "none recorded"
            ),
            "",
        ])
    return lines


def _claim_section(item: dict[str, Any]) -> list[str]:
    claim = item["original_claim"]
    excluded = item["excluded_native_pages_in_hint"] or "none"
    lines = [
        f"## {item['claim_id']}",
        "",
        f"- Claim type: `{claim.get('claim_type', 'unspecified')}`",
        f"- Priority: `{claim.get('priority', 'unspecified')}`",
        f"- Legacy document/page: `{claim.get('document_id', '')}` / "
        f"`{claim.get('page', '')}` (navigation only)",
        f"- Section: `{claim.get('section', '')}`",
        f"- Maps to: `{claim.get('maps_to', '')}`",
        f"- Page hint: {_page_hint(item)}",
        f"- Excluded native pages inside hint: `{excluded}`",
        "",
        "### Original claim (untrusted historical input)",
        "",
        _blockquote(claim["text"]),
        "",
        "### Exact native candidate suggestions",
        "",
    ]
    lines.extend(_native_suggestions(item))
    lines.extend(["### Accepted reviewed fallback suggestions", ""])
    lines.extend(_fallback_suggestions(item))
    lines.extend([
        "### Human completion record",
        "",
        "Complete the matching claim entry in "
        "`config/claim_reconciliation_map_v0_1.json`; do not record a decision in this brief.",
        "",
        "- Allowed dispositions: "
        + ", ".join(f"`{value}`" for value in sorted(ALLOWED_DISPOSITIONS)),
        "- Required checks (all `PASS`): "
        + ", ".join(f"`{value}`" for value in sorted(REQUIRED_CHECKS)),
        "- Required attestations (all `true`): "
        + ", ".join(f"`{value}`" for value in sorted(REQUIRED_ATTESTATIONS)),
        "- Also required: reviewer identity/role/date, findings, limitations, exclusions, "
        "authority/jurisdiction, currentness/supersession, and allowed decisions/actions.",
        "- A supported disposition requires atomic propositions and direct exact support. "
        "An unresolved/insufficient disposition must not invent support.",
        "- Completion does not authorize live activation.",
        "",
        "---",
        "",
    ])
    return lines


def build_claim_review_briefs(
    aid: dict[str, Any],
    aid_bytes: bytes,
    review_map_bytes: bytes,
    aid_path: str,
    review_map_path: str,
    generated_date: str,
) -> tuple[dict[str, str], str]:
    if aid.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("review aid must require claim review")
    if aid.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("review aid must prohibit live activation")
    if aid.get("source_claim_reconciliation_map_sha256") != _sha256(review_map_bytes):
        raise ValidationError("review aid is not bound to the supplied review map")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in aid.get("claim_review_items", []):
        if item.get("claim_review_status") == CLAIM_REVIEW_REQUIRED:
            grouped[item["controlled_document_id"]].append(item)
    pending_count = sum(map(len, grouped.values()))
    if pending_count != aid.get("pending_claim_review_count"):
        raise ValidationError("pending claim count does not match review aid")

    provenance = [
        f"Generated {generated_date} from `{aid_path}` (SHA-256 `{_sha256(aid_bytes)}`).",
        f"Canonical map: `{review_map_path}` (SHA-256 `{_sha256(review_map_bytes)}`).",
    ]
    briefs: dict[str, str] = {}
    for document_id in sorted(grouped):
        items = sorted(grouped[document_id], key=lambda value: value["claim_id"])
        lines = [
            f"# Claim review brief — {document_id}", "",
            f"Version: `{BRIEF_VERSION}`. **Navigation only; {len(items)} pending claims.**",
            "", *provenance, "",
            f"Controlled source SHA-256: `{items[0]['controlled_source_sha256']}`.",
            "", "## Safety boundaries", "",
        ]
        for prompt in items[0]["boundary_prompts"]:
            lines.append(f"- {prompt}")
        lines.append("")
        for item in items:
            lines.extend(_claim_section(item))
        briefs[document_id] = "\n".join(lines).rstrip() + "\n"

    index = [
        "# Pending claim review briefs", "",
        f"Version: `{BRIEF_VERSION}`.", "", *provenance, "",
        f"**{pending_count} pending claims across {len(briefs)} controlled documents.**",
        "", "These are navigation-only aids. They create no disposition, atomic proposition, "
        "reviewer identity, attestation, regulatory conclusion, or activation decision.",
        "", "| Brief | Pending claims |", "|---|---:|",
    ]
    for document_id in sorted(briefs):
        count = len(grouped[document_id])
        index.append(f"| [ `{document_id}` ](review_brief_{document_id}.md) | {count} |")
    return briefs, "\n".join(index) + "\n"


def write_claim_review_briefs(briefs: dict[str, str], index: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for document_id, content in briefs.items():
        (output_dir / f"review_brief_{document_id}.md").write_text(content, encoding="utf-8")
    (output_dir / "INDEX.md").write_text(index, encoding="utf-8")