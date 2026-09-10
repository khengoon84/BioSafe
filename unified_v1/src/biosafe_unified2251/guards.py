from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


UNKNOWN_DECISION = (
    "The available information is insufficient to determine whether a permit, "
    "approval, notification, or other regulatory authorization is required."
)

NEUTRAL_NEXT_STEP = (
    "Confirm the jurisdiction, material or technology trigger, and specific activity "
    "before selecting a regulatory pathway."
)

_PRIMARY_CLAIM_FIELDS = ("conclusion", "direct_answer")
_GENERATED_LIST_CLAIM_FIELDS = (
    "recommended_next_step",
    "recommendations",
    "recommended_next_steps",
    "missing_information",
)

_NEGATIVE_AUTHORIZATION = (
    r"\bno (?:specific )?(?:permit|approval|notification|authori[sz]ation)s? "
    r"(?:is|are) required\b",
    r"\bno (?:specific )?(?:permit|approval|notification|authori[sz]ation)s? "
    r"appl(?:y|ies)\b",
    r"\byou do not need (?:a|an|any) "
    r"(?:permit|approval|notification|authori[sz]ation)\b",
    r"\b(?:permit|approval|notification|authori[sz]ation) is not "
    r"(?:required|necessary)\b",
)

_POSITIVE_AUTHORIZATION = (
    r"\byou (?:need|must|are required) to (?:submit|obtain|apply for|notify)\b",
    r"\b(?:notification|approval|a permit|an authori[sz]ation) is required\b",
    r"^\s*(?:submit|obtain|apply for|notify)\b.{0,160}"
    r"\b(?:permit|approval|notification|authori[sz]ation)\b",
    r"^\s*submit\b.{0,160}\bfor approval\b",
    r"\b(?:submit|obtain|apply for|notify)\b.{0,160}\bto (?:the )?"
    r"(?:department of biosafety|biosafety (?:authority|board|department)|"
    r"national biosafety (?:authority|board)|regulatory authorit(?:y|ies)|"
    r"regulator|ministry)\b",
    r"\bnotify\b.{0,60}\bdepartment of biosafety\b",
    r"^\s*submit\b",
)

_COMPLIANCE_VERDICT = (
    r"\b(?:your|this|the) (?:project|activity|work) is "
    r"(?:(?:not|yet|currently)\s+){0,2}(?:legally\s+)?compliant\b",
    r"\b(?:your|this|the) (?:project|activity|work) is "
    r"(?:legal|illegal|approved|not approved|certified|not certified)\b",
)

_NONEXISTENCE = re.compile(
    r"\b(?:act|law|regulation|regulations|ordinance|order|guideline)s?\b"
    r".{0,100}\b(?:does not|doesn't|do not|don't) exist\b|"
    r"\bnon[- ]existent (?:act|law|regulation|ordinance|order|guideline)\b",
    re.I,
)

_FORM_E_AS_AUTHORIZATION = re.compile(
    r"\b(?:biosafety\s+)?(?:permit|approval|authori[sz]ation|certificate)\s*"
    r"\(?(?:form\s*e)\)?|"
    r"\bform\s*e\b.{0,45}\b(?:permit|approval|authori[sz]ation|certificate)\b|"
    r"\b(?:plan|report|submission|assessment)\s*\(\s*form\s*e\s*\)|"
    r"\bform\s*e\b.{0,45}\b(?:is|as)\s+(?:a|an|the)\b[^.]{0,30}\b"
    r"(?:plan|report|submission|assessment)\b",
    re.I,
)

_START_WORK = re.compile(
    r"\b(?:you|the project|the activity|work) (?:can|cannot|can't|may|must not) "
    r"(?:start|begin|proceed|commence)(?: work| the work| the activity)?\b",
    re.I,
)

_INVENTED_BSA = re.compile(r"\bbiosafety and biosecurity assessment\s*\(BSA\)", re.I)

_EXACT_PROVISION = re.compile(
    r"\b(?:s\.|section|reg\.|regulation)\s*(\d+[A-Za-z0-9()\-]*)", re.I
)


def _strings(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def _evidence_text(evidence: list[dict[str, Any]]) -> str:
    fields = (
        "evidence_id", "text", "statement", "support_span", "section",
        "subsection", "regulation", "article", "citation", "title",
    )
    return " ".join(
        str(item.get(field) or "")
        for item in evidence
        for field in fields
        if isinstance(item, dict)
    ).lower()


def _provision_supported(sentence: str, evidence: list[dict[str, Any]]) -> bool:
    identifiers = _EXACT_PROVISION.findall(sentence)
    if not identifiers:
        return True
    text = _evidence_text(evidence)
    for identifier in identifiers:
        number = re.escape(identifier.lower())
        if not re.search(
            rf"(?:s\.|section|reg\.|regulation)\s*{number}(?![a-z0-9])", text, re.I
        ):
            return False
    return True


def _trigger_facts_established(case_state: dict[str, Any]) -> bool:
    """Require explicit structured facts; do not infer them from the question."""
    state = {str(k).lower(): v for k, v in (case_state or {}).items()}
    jurisdiction = str(state.get("jurisdiction") or "").lower()
    if jurisdiction not in {"malaysia", "my", "malaysian"}:
        return False

    trigger_values = (
        state.get("lmo"), state.get("is_lmo"), state.get("genetically_modified"),
        state.get("modern_biotechnology"), state.get("recombinant"),
    )
    if not any(value is True or str(value).lower() in {"true", "yes"} for value in trigger_values):
        return False

    activity = str(
        state.get("regulated_activity") or state.get("activity") or state.get("use_type") or ""
    ).strip().lower()
    return bool(activity and activity not in {"unknown", "unspecified", "none"})


def _authorization_evidence_supports(
    sentence: str, evidence: list[dict[str, Any]]
) -> bool:
    """Require both the authorization subject and normative force in scoped evidence."""
    claim = sentence.lower()
    source = _evidence_text(evidence)
    subjects = {
        "permit": ("permit", "licence", "license"),
        "approval": ("approval", "approve"),
        "notification": ("notification", "notify"),
        "authorization": ("authorization", "authorisation", "authorize", "authorise"),
    }
    requested = [name for name, terms in subjects.items() if any(term in claim for term in terms)]
    if not requested:
        return False
    subject_supported = all(
        any(term in source for term in subjects[name]) for name in requested
    )
    normative_supported = any(
        term in source
        for term in ("required", "requires", "must", "shall", "prior notification", "specified activity")
    )
    return subject_supported and normative_supported


def vetted_direct_answer(query: str) -> dict[str, Any] | None:
    """Conservative answers for stable, common concepts that need no case decision."""
    q = re.sub(r"\s+", " ", (query or "").strip().lower().rstrip("?.!"))
    if q in {"what is biosafety", "define biosafety"}:
        return {
            "direct_answer": (
                "Biosafety is the set of principles, technologies, and practices used to prevent "
                "unintentional exposure to biological agents or their accidental release. This "
                "covers things like hand hygiene, personal protective equipment, safe injection "
                "practices, proper waste decontamination, and containment equipment. The specific "
                "controls should always be selected through a context-specific risk assessment "
                "that considers the agent, procedures, and laboratory setting. In short, "
                "biosafety is the preventive side of working safely with biological materials."
            )
        }
    if q in {
        "what is the difference between biosafety and biosecurity",
        "difference between biosafety and biosecurity",
    }:
        return {
            "direct_answer": (
                "Here is how biosafety and biosecurity fit together:\n\n"
                "- **Biosafety**: prevents *accidents*. Protects people and the environment from "
                "unintentional exposure, spills, or releases of biological agents. Think lab "
                "safety cabinets, PPE, safe injection practices, and waste decontamination.\n"
                "- **Biosecurity**: prevents *misuse*. Protects biological agents from theft, loss, "
                "unauthorized access, or diversion. Think access control, inventory tracking, "
                "personnel reliability, and security cameras.\n\n"
                "Both are pillars of laboratory risk management and overlap in practice — a "
                "locked freezer might serve containment (biosafety) and access control (biosecurity)."
            )
        }
    if q in {"what is a biological risk group", "define biological risk group"}:
        return {
            "direct_answer": (
                "A biological risk group is a hazard-based category assigned to a biological agent "
                "using criteria such as its ability to cause disease, severity, transmissibility and "
                "the availability of preventive or therapeutic measures. A risk group does not by "
                "itself determine the biosafety level required for a particular activity."
            ),
            "limitations": [
                "BioSafe has not assigned a risk group or containment level to any specific agent."
            ],
        }
    if q in {"what is pi and ibc", "what are pi and ibc", "define pi and ibc"}:
        return {
            "direct_answer": (
                "PI means Principal Investigator, the person responsible for leading a research "
                "project. IBC means Institutional Biosafety Committee, an institutional committee "
                "that reviews and oversees biosafety aspects of relevant work under its mandate."
            ),
            "limitations": [
                "Exact responsibilities depend on the applicable institutional and regulatory framework."
            ],
        }
    if q in {"what is the biological weapons convention", "define the biological weapons convention"}:
        return {
            "direct_answer": (
                "The Biological Weapons Convention is an international treaty that prohibits the "
                "development, production, acquisition, transfer, stockpiling and use of biological "
                "and toxin weapons."
            )
        }
    return None


class DecisionSemanticsGuard:
    """Fail closed on consequential determinations that lack prerequisites/provenance."""

    @staticmethod
    def _field_sentences(value: Any) -> list[str]:
        if isinstance(value, str):
            return [item for item in re.split(r"(?<=[.!?])\s+", value) if item.strip()]
        return []

    def _guard_text(
        self,
        text: str,
        *,
        field: str,
        trigger_ready: bool,
        evidence: list[dict[str, Any]],
        recommendation: bool = False,
    ) -> tuple[str, list[dict[str, Any]]]:
        kept: list[str] = []
        audit: list[dict[str, Any]] = []

        for sentence in self._field_sentences(text):
            action = ""
            replacement = ""
            if _NONEXISTENCE.search(sentence):
                action = "replace_unverified_nonexistence"
                replacement = (
                    "I could not verify the named law or instrument from the authoritative "
                    "sources currently available to BioSafe."
                )
            elif _FORM_E_AS_AUTHORIZATION.search(sentence) or _INVENTED_BSA.search(sentence):
                action = "replace_form_e_mischaracterization"
                replacement = (
                    "BioSafe cannot authorize the work and cannot treat Form E as a permit, "
                    "approval, certificate, or IBC decision."
                )
            elif _START_WORK.search(sentence):
                action = "replace_start_work_verdict"
                replacement = (
                    "BioSafe cannot authorize starting the work; follow the applicable institutional "
                    "and regulatory review process before proceeding."
                )
            elif any(re.search(pattern, sentence, re.I) for pattern in _COMPLIANCE_VERDICT):
                action = "replace_compliance_verdict"
                replacement = (
                    "BioSafe cannot determine or certify the project's legal or compliance status."
                )
            else:
                if not _provision_supported(sentence, evidence):
                    action = "remove_unsupported_exact_provision"
                else:
                    authorization_claim = any(
                        re.search(pattern, sentence, re.I)
                        for pattern in _NEGATIVE_AUTHORIZATION + _POSITIVE_AUTHORIZATION
                    )
                    if authorization_claim and (
                        not trigger_ready
                        or not _authorization_evidence_supports(sentence, evidence)
                    ):
                        action = "downgrade_untriggered_authorization"
                        replacement = NEUTRAL_NEXT_STEP if recommendation else UNKNOWN_DECISION

            if action:
                item = {"action": action, "original": sentence, "field": field}
                if replacement:
                    item["replacement"] = replacement
                    kept.append(replacement)
                audit.append(item)
                continue
            kept.append(sentence)

        return " ".join(dict.fromkeys(item.strip() for item in kept if item.strip())), audit

    def apply(
        self,
        response: dict[str, Any],
        query: str = "",
        case_state: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ):
        out = deepcopy(response)
        evidence = evidence or []
        case_state = case_state or {}
        trigger_ready = _trigger_facts_established(case_state)
        audit: list[dict[str, Any]] = []

        for key in _PRIMARY_CLAIM_FIELDS:
            if key not in out:
                continue
            original = str(out.get(key) or "")
            clean, field_audit = self._guard_text(
                original,
                field=key,
                trigger_ready=trigger_ready,
                evidence=evidence,
            )
            audit.extend(field_audit)
            if not clean and original:
                clean = (
                    "BioSafe cannot make a legal, compliance, approval, permit, notification, or "
                    "authorization determination from the information currently available."
                )
            out[key] = clean

        for key in _GENERATED_LIST_CLAIM_FIELDS:
            if key not in out:
                continue
            value = out.get(key)
            items = value if isinstance(value, list) else [value] if isinstance(value, str) else []
            clean_items: list[str] = []
            for item in items:
                clean, field_audit = self._guard_text(
                    str(item or ""),
                    field=key,
                    trigger_ready=trigger_ready,
                    evidence=evidence,
                    recommendation=True,
                )
                audit.extend(field_audit)
                if clean and clean not in clean_items:
                    clean_items.append(clean)
            out[key] = clean_items if isinstance(value, list) else " ".join(clean_items)

        if any(item["action"] == "downgrade_untriggered_authorization" for item in audit):
            missing = list(out.get("missing_information") or [])
            requirement = (
                "Confirm the jurisdiction, whether the material is an LMO or otherwise involves "
                "modern biotechnology, and the specific activity being undertaken."
            )
            if requirement not in missing:
                missing.append(requirement)
            out["missing_information"] = missing
            safety = dict(out.get("safety") or {})
            safety["response_mode"] = "ask_before_concluding"
            safety.setdefault("classification", "caution")
            safety.setdefault("reason", "Regulatory applicability prerequisites are incomplete.")
            out["safety"] = safety

        return out, audit
