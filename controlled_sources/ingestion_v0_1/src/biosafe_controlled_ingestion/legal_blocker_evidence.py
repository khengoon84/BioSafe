from __future__ import annotations

import hashlib
from typing import Any

from .components import ACTIVATION_PROHIBITED, CLAIM_REVIEW_REQUIRED
from .contracts import ValidationError


BUNDLE_VERSION = "BioSafe_Legal_Blocker_Evidence_Bundle_v0.1"
TARGET_CLAIMS = {"CLM-006", "CLM-007", "CLM-030"}
EXTRA_CHUNKS = {
    "CLM-030": {"KB-MY-SW2005:AMENDMENT_LIST:PDF_PAGE_34"},
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _quote(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.strip().splitlines())


def build_legal_blocker_evidence(
    legal_draft: dict[str, Any],
    legal_draft_bytes: bytes,
    review_map: dict[str, Any],
    review_map_bytes: bytes,
    components: dict[str, Any],
    component_bytes: bytes,
    source_policy: dict[str, Any],
    source_policy_bytes: bytes,
    source_register: list[dict[str, str]],
    source_register_bytes: bytes,
    generated_date: str,
) -> tuple[dict[str, str], str]:
    for name, artifact in (("legal draft", legal_draft), ("components", components)):
        if artifact.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
            raise ValidationError(f"{name} must require claim review")
        if artifact.get("live_activation_status") != ACTIVATION_PROHIBITED:
            raise ValidationError(f"{name} must prohibit live activation")
    if legal_draft.get("source_component_artifact_sha256") != _sha256(component_bytes):
        raise ValidationError("legal draft is not bound to supplied components")
    if legal_draft.get("source_policy_sha256") != _sha256(source_policy_bytes):
        raise ValidationError("legal draft is not bound to supplied source policy")

    drafts = {
        item["claim_id"]: item for item in legal_draft.get("legal_claim_drafts", [])
        if item.get("claim_id") in TARGET_CLAIMS
    }
    if set(drafts) != TARGET_CLAIMS:
        raise ValidationError("legal draft must contain the exact blocker claim set")
    reviews = {
        item["claim_id"]: item for item in review_map.get("claim_reviews", [])
        if item.get("claim_id") in TARGET_CLAIMS
    }
    if set(reviews) != TARGET_CLAIMS:
        raise ValidationError("review map must contain the exact blocker claim set")
    for claim_id, review in reviews.items():
        if (
            review.get("review_status") != "CLAIM_REVIEW_COMPLETE"
            or review.get("disposition") != "CURRENTNESS_UNRESOLVED"
            or review.get("support_spans") != []
        ):
            raise ValidationError(f"canonical blocker disposition is invalid for {claim_id}")
    chunks = {item["candidate_chunk_id"]: item for item in components["candidate_chunks"]}
    component_records = {item["component_id"]: item for item in components["components"]}
    register = {item["candidate_id"]: item for item in source_register}
    policies = source_policy.get("sources", {})
    for record in source_register:
        searchable = " ".join(
            record.get(field, "")
            for field in ("candidate_id", "staged_filename", "title", "instrument_identifier")
        ).lower()
        if "2019" in searchable and ("amend" in searchable or "pindaan" in searchable):
            raise ValidationError(
                "2019 amendment is now present; controlled-corpus gap logic must be reviewed"
            )

    provenance = [
        f"Generated: {generated_date}",
        f"Legal draft SHA-256: `{_sha256(legal_draft_bytes)}`",
        f"Canonical review map SHA-256: `{_sha256(review_map_bytes)}`",
        f"Component artifact SHA-256: `{_sha256(component_bytes)}`",
        f"Source policy SHA-256: `{_sha256(source_policy_bytes)}`",
        f"Source register SHA-256: `{_sha256(source_register_bytes)}`",
    ]
    outputs: dict[str, str] = {}
    for claim_id in sorted(TARGET_CLAIMS):
        draft = drafts[claim_id]
        document_id = draft["controlled_document_id"]
        if document_id not in register or document_id not in policies:
            raise ValidationError(f"source metadata missing for {claim_id}")
        selected = {item["candidate_chunk_id"] for item in draft["candidate_evidence"]}
        selected |= EXTRA_CHUNKS.get(claim_id, set())
        evidence = []
        for chunk_id in sorted(selected):
            if chunk_id not in chunks:
                raise ValidationError(f"required evidence chunk missing: {chunk_id}")
            chunk = chunks[chunk_id]
            if chunk["document_id"] != document_id:
                raise ValidationError(f"evidence document mismatch for {claim_id}")
            if chunk["source_sha256"] != draft["controlled_source_sha256"]:
                raise ValidationError(f"evidence source hash mismatch for {claim_id}")
            evidence.append(chunk)

        record = register[document_id]
        if record.get("sha256") != draft["controlled_source_sha256"]:
            raise ValidationError(f"register source hash mismatch for {claim_id}")
        policy = policies[document_id]
        if policy.get("supersession_status") != draft["controlled_supersession_status"]:
            raise ValidationError(f"supersession status mismatch for {claim_id}")

        lines = [
            f"# Legal blocker evidence — {claim_id}", "",
            f"Version: `{BUNDLE_VERSION}`. **Evidence-only human review aid.**", "",
            *[f"- {value}" for value in provenance], "",
            "This bundle does not establish current law, applicability, exemption, approval, "
            "notification, classification, compliance, non-compliance, or a prescribed pathway. "
            "It does not change the claim disposition or authorize curation or activation.", "",
            "## Claim under review", "", _quote(draft["original_claim"]["text"]), "",
            f"- Controlled document: `{document_id}`",
            f"- Controlled source SHA-256: `{draft['controlled_source_sha256']}`",
            f"- Currentness status: `{draft['controlled_currentness_status']}`",
            f"- Supersession status: `{draft['controlled_supersession_status']}`",
            f"- Current review status: `{reviews[claim_id]['review_status']}`",
            f"- Current disposition in canonical map: `{reviews[claim_id]['disposition']}`",
            "- Current support spans: none", "",
            "## Recorded review issues", "",
        ]
        lines.extend(f"- {issue}" for issue in draft["review_issues"])
        lines.extend(["", "## Controlled source metadata", ""])
        for field in (
            "staged_filename", "instrument_identifier", "status", "official_landing_page",
            "direct_download_url", "currentness_status", "supersession_status",
            "live_activation_status",
        ):
            if record.get(field):
                lines.append(f"- Register `{field}`: `{record[field]}`")
        lines.extend(["", "## Exact controlled candidate passages", ""])
        for chunk in sorted(evidence, key=lambda value: value["pdf_page_start"]):
            component = component_records[chunk["component_id"]]
            lines.extend([
                f"### `{chunk['candidate_chunk_id']}`", "",
                f"PDF pages {chunk['pdf_page_start']}–{chunk['pdf_page_end']}; "
                f"source SHA-256 `{chunk['source_sha256']}`.", "", _quote(chunk["text"]), "",
                f"Component review status: `{component['review_status']}`.", "",
            ])
        lines.extend([
            "## Human review boundary", "",
            "Compare these passages with the immutable staged PDF and authoritative amendment "
            "evidence. Unknown or missing amendment information must remain unresolved. Record any "
            "future decision through the claim-reconciliation contract, not in this bundle.", "",
        ])
        outputs[claim_id] = "\n".join(lines)

    index = [
        "# Legal blocker evidence bundles", "",
        f"Version: `{BUNDLE_VERSION}`. Generated {generated_date}.", "",
        "Evidence-only aids for three claims already dispositioned `CURRENTNESS_UNRESOLVED`.",
        "No bundle resolves currentness or changes any claim record.", "",
        "| Claim | Controlled document | Blocker |", "|---|---|---|",
    ]
    for claim_id in sorted(outputs):
        draft = drafts[claim_id]
        blockers = ", ".join(f"`{value}`" for value in draft["currentness_blockers"])
        index.append(
            f"| [{claim_id}](legal_blocker_{claim_id}.md) | "
            f"`{draft['controlled_document_id']}` | {blockers} |"
        )
    index.extend([
        "", "## Controlled-corpus gap", "",
        "The staged collection contains the Regulations 2010 base instrument but does not contain "
        "the separately listed 2019 First/Third Schedule amending instrument. CLM-007 therefore "
        "remains unresolved from the controlled collection. No source was downloaded by this step.",
        "",
    ])
    return outputs, "\n".join(index)