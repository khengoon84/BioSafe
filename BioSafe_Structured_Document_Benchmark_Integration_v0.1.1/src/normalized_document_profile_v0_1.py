from __future__ import annotations
import re
from typing import Any

PROFILE_FIELDS = [
    'project_title','principal_investigator','institution','project_duration','proposed_start',
    'objectives','host_organism','construct_identity','facility','culture_scale','containment',
    'waste','transport','emergency_response'
]

CORE_EXACT_FIELDS = {
    'project_title','principal_investigator','institution','project_duration','proposed_start',
    'host_organism','construct_identity','culture_scale','containment'
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = ' '.join(value.strip().split())
    return value or None


def _inline(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text, flags=re.I | re.M)
    return _clean(m.group(1)) if m else None


def _section_body(text: str, heading_regex: str) -> str | None:
    m = re.search(
        rf'(?ims)^(?:\d+\.|A\d)\s*{heading_regex}\s*:?\s*\n(.*?)(?=^(?:\d+\.|A\d)\s+|\Z)',
        text,
    )
    return _clean(m.group(1)) if m else None


def _norm(v: Any) -> str | None:
    if v is None:
        return None
    s = ' '.join(str(v).lower().split())
    s = re.sub(r'[.;:,]+$', '', s).strip()
    return s or None


def _explicitly_missing(text: str, concepts: list[str]) -> bool:
    low = text.lower()
    markers = ['not fully described', 'not specified', 'not provided', 'not known', 'to be confirmed']
    return any(c.lower() in low for c in concepts) and any(m in low for m in markers)


def extract_normalized_profile(text: str, doc_type: str) -> dict[str, Any]:
    out: dict[str, Any] = {k: None for k in PROFILE_FIELDS}
    status: dict[str, str] = {k: 'missing' for k in PROFILE_FIELDS}

    def setv(field: str, value: str | None, state: str = 'present'):
        if value is not None:
            out[field] = value
            status[field] = state

    setv('principal_investigator', _inline(text, r'^Principal Investigator:\s*([^\n]+)'))
    setv('institution', _inline(text, r'^Institution:\s*([^\n]+)'))
    setv('project_duration', _inline(text, r'^Project duration:\s*([^\n]+)'))
    setv('proposed_start', _inline(text, r'^Proposed start:\s*([^\n]+)'))

    setv('project_title', _section_body(text, r'Project Title') or _section_body(text, r'Project\s*/\s*activity title'))
    setv('objectives', _section_body(text, r'Objectives') or _section_body(text, r'Objectives\s*/\s*purpose of the contained-use activity'))

    setv('host_organism', _inline(text, r'^Host:\s*([^\n.]+)') or _inline(text, r'^Host organism:\s*([^\n.]+)'))
    setv('construct_identity', _inline(text, r'^Inserted construct:\s*([^\n.]+)') or _inline(text, r'^Construct:\s*([^\n.]+)'))

    facility = _inline(text, r'Work will be conducted in the ([^\n.]+)')
    if facility:
        # Normalize institution suffix so 'Molecular Biology Laboratory at Example University'
        # can be compared conservatively with 'Molecular Biology Laboratory'.
        facility = re.sub(r'\s+at\s+[^,.;]+$', '', facility, flags=re.I)
    setv('facility', facility)

    setv('culture_scale', _inline(text, r'^Culture scale:\s*([^\n.]+)'))
    setv('containment', _inline(text, r'^Containment:\s*([^\n.]+)'))

    setv('waste', _section_body(text, r'Waste Management') or _section_body(text, r'Waste'))
    setv('transport', _section_body(text, r'Transport and Storage') or _section_body(text, r'Transport'))
    setv('emergency_response', _section_body(text, r'Emergency Response') or _section_body(text, r'Incident Management') or _section_body(text, r'Spill or Exposure Incident') or _section_body(text, r'Incidents'))

    if doc_type == 'form_e_completed':
        a2 = _section_body(text, r'Applicant\s*/\s*principal investigator and institution')
        if a2:
            if out['principal_investigator'] is None:
                setv('principal_investigator', _inline(a2, r'^Principal Investigator:\s*([^\n]+)'))
            if out['institution'] is None:
                setv('institution', _inline(a2, r'^Institution:\s*([^\n]+)'))
        a4 = _section_body(text, r'LMO\s*/\s*GMM identity and characteristics')
        if a4:
            setv('host_organism', _inline(a4, r'^Host:\s*([^\n.]+)') or out['host_organism'])
            setv('construct_identity', _inline(a4, r'^Inserted construct:\s*([^\n.]+)') or out['construct_identity'])
        a5 = _section_body(text, r'Activities\s*/\s*facility\s*/\s*containment')
        if a5:
            setv('facility', _inline(a5, r'conducted in the ([^\n.]+)') or out['facility'])
            setv('culture_scale', _inline(a5, r'^Culture scale:\s*([^\n.]+)') or out['culture_scale'])
            setv('containment', _inline(a5, r'^Containment:\s*([^\n.]+)') or out['containment'])
        a6 = _section_body(text, r'Dates\s*/\s*waste\s*/\s*transport\s*/\s*emergency response')
        if a6:
            setv('project_duration', _inline(a6, r'^Project duration:\s*([^\n.]+)') or out['project_duration'])
            setv('proposed_start', _inline(a6, r'^Proposed start:\s*([^\n.]+)') or out['proposed_start'])
            if 'waste' in a6.lower(): setv('waste', a6)
            if 'transfer' in a6.lower() or 'transport' in a6.lower(): setv('transport', a6)
            if 'spill' in a6.lower() or 'incident' in a6.lower(): setv('emergency_response', a6)

    # Preserve explicit absence/uncertainty instead of silently treating it as no data.
    if out['host_organism'] is None and _explicitly_missing(text, ['host species','host organism']):
        status['host_organism'] = 'explicitly_unclear'
    if out['construct_identity'] is None and _explicitly_missing(text, ['inserted construct','inserted sequence']):
        status['construct_identity'] = 'explicitly_unclear'
    if out['culture_scale'] is None and ('exact culture scale' in text.lower() or 'culture scale' in text.lower()):
        if any(x in text.lower() for x in ['depend on preliminary results','not specified','not provided']):
            status['culture_scale'] = 'explicitly_unclear'
    if out['containment'] is None and any(x in text.lower() for x in ['appropriate biosafety level','contained conditions']):
        status['containment'] = 'explicitly_unclear'

    out['_status'] = status
    return out


def compare_profiles(document_a: str, profile_a: dict[str, Any], document_b: str, profile_b: dict[str, Any]) -> list[dict]:
    findings = []
    status_a = profile_a.get('_status', {})
    status_b = profile_b.get('_status', {})

    for field in PROFILE_FIELDS:
        va, vb = profile_a.get(field), profile_b.get(field)
        sa, sb = status_a.get(field, 'missing'), status_b.get(field, 'missing')

        if va is not None and vb is not None:
            if field in CORE_EXACT_FIELDS and _norm(va) != _norm(vb):
                findings.append({
                    'field': field,
                    'document_a': document_a, 'value_a': va,
                    'document_b': document_b, 'value_b': vb,
                    'status': 'possible_value_conflict',
                    'review_rule': 'Verify against source documents; do not silently choose one version.'
                })
            elif field == 'transport':
                a_no = bool(re.search(r'\bwill not be transferred\b|\bno transfer\b', str(va), flags=re.I))
                b_no = bool(re.search(r'\bwill not be transferred\b|\bno transfer\b', str(vb), flags=re.I))
                a_may = bool(re.search(r'\bmay be transferred\b|\bwill be transferred\b', str(va), flags=re.I))
                b_may = bool(re.search(r'\bmay be transferred\b|\bwill be transferred\b', str(vb), flags=re.I))
                if (a_no and b_may) or (b_no and a_may):
                    findings.append({
                        'field': field,
                        'document_a': document_a, 'value_a': va,
                        'document_b': document_b, 'value_b': vb,
                        'status': 'possible_operational_conflict',
                        'review_rule': 'Verify transfer scope and permitted movement.'
                    })
        elif sa == 'explicitly_unclear' and vb is not None:
            findings.append({
                'field': field,
                'document_a': document_a, 'value_a': '[explicitly unclear / not fully described]',
                'document_b': document_b, 'value_b': vb,
                'status': 'unsupported_secondary_detail',
                'review_rule': 'The second document contains a specific value not supported by the first document.'
            })
        elif sb == 'explicitly_unclear' and va is not None:
            findings.append({
                'field': field,
                'document_a': document_a, 'value_a': va,
                'document_b': document_b, 'value_b': '[explicitly unclear / not fully described]',
                'status': 'unsupported_primary_detail',
                'review_rule': 'The first document contains a specific value not supported by the second document.'
            })

    return findings
