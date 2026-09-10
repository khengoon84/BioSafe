from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List

TOKEN_RE = re.compile(r"[a-z0-9]+")

def norm(s: str) -> str:
    return " ".join(TOKEN_RE.findall((s or "").lower()))

def has_any(q: str, phrases: List[str]) -> bool:
    return any(p in q for p in phrases)

@dataclass
class Route:
    jurisdiction: str
    domain: str
    intent: str
    preferred_tier: str
    scope: List[str]
    uncertainty_sensitive: bool = False
    safety_sensitive: bool = False
    expansion_terms: str = ""
    rationale: str = ""

class BioSafeRouterV02:
    """Deterministic BioSafe router v0.2.

    Design goals:
    - concept/phrase clusters rather than exact single triggers;
    - explicit precedence for safety, scope-boundary and authority questions;
    - preserve Malaysia-first authority logic;
    - make uncertainty and anti-inference first-class route flags.
    """

    def classify(self, query: str) -> Route:
        q = norm(query)

        # 1) SAFETY has highest precedence, including safe-redirect formulations.
        harm_terms = [
            'more harmful','harmful effect','make a biological agent more harmful',
            'increase the harmful effect','more dangerous','make a biological system more dangerous',
            'dangerous biological','facilitate harmful','avoiding detection','avoid detection',
            'evade detection','increase virulence','increase pathogenicity'
        ]
        enabling_terms = ['step by step','procedural changes','instructions','tell me how','helping me make']
        redirect_terms = ['instead of helping','redirect me','safe containment','incident prevention']
        if has_any(q, harm_terms) or (has_any(q,enabling_terms) and has_any(q,['biological','agent','system'])) or has_any(q,redirect_terms):
            return Route('System','SAFETY','refusal','System',['safety','refusal','non-enabling redirect'],False,True,
                         'unsafe biological assistance harmful enabling procedural details withhold redirect containment risk management incident prevention',
                         'harm/enabling/redirect concept detected')

        # 2) CURRENTNESS / source-version reconciliation.
        if (has_any(q,['older','old procedural','newer','current official','current operational','newer official']) and
            has_any(q,['conflict','conflicts','prefer','which one','reconcile'])):
            return Route('Malaysia','CURRENTNESS','versioning','Tier 2',['currentness','official operational guidance'],False,False,
                         'currentness older procedural conflicts current official operational page prefer current official reconciliation',
                         'source-version conflict detected')

        # 3) AUTHORITY / evidence policy questions.
        if has_any(q,['malaysian legal','malaysian regulatory','malaysian legislation','malaysia legislation']) and has_any(q,['who','lead','outrank','replace']):
            return Route('Malaysia','AUTHORITY','authority','Tier 1',['authority hierarchy'],False,False,
                         'authority first Malaysian legislation Tier 1 should lead WHO must not outrank Malaysian legal regulatory sources',
                         'Malaysia-vs-WHO hierarchy question detected')
        if has_any(q,['malaysian guidance','malaysia guidance']) and has_any(q,['silent','who','support']):
            return Route('Malaysia','AUTHORITY','corroboration','Tier 1+3',['WHO corroboration'],False,False,
                         'WHO corroboration where Malaysian sources do not specify technical issue use WHO as Tier 3 support',
                         'WHO corroboration question detected')
        if has_any(q,['regulatory conclusion','regulatory answer']) and has_any(q,['showing where','where it came from','cite','citation','source']):
            return Route('Malaysia','AUTHORITY','evidence','Tier 1+2',['evidence','citation readiness'],False,False,
                         'material regulatory conclusions cite source section page evidence',
                         'regulatory evidence/citation requirement detected')

        # 4) FORM E / researcher-facing scope boundaries.
        forme_core = has_any(q,['form e'])
        forme_description = has_any(q,['donor organism','parent organism','host species','vector','lmo description','modified trait','gene identity'])
        excluded_field = has_any(q,['annex 2','application fee','missing fee','ibc assessment report'])
        approval_boundary = has_any(q,['officially compliant','official compliance','issue the ibc approval','ibc approval itself','approve the project'])
        if approval_boundary and has_any(q,['ibc','proposal']):
            return Route('Malaysia','MY-IBC','approval_boundary','Tier 2',['IBC governance','approval boundary'],False,False,
                         'IBC boundary do not simulate issue approval BioSafe decision support no official approval compliance',
                         'IBC approval authority boundary detected')
        if forme_core or forme_description or excluded_field or (approval_boundary and has_any(q,['form e','complete looking'])):
            if has_any(q,['annex 2']): intent='annex_exclusion'
            elif has_any(q,['application fee','missing fee']): intent='fee_exclusion'
            elif has_any(q,['ibc assessment report']): intent='scope_gate'
            elif approval_boundary: intent='approval_boundary'
            elif has_any(q,['invent','fill in an unstated','guess','not stated','missing','blanks']) and (forme_core or forme_description): intent='uncertainty'
            elif forme_description: intent='Form E'
            else: intent='Form E'
            uncertain = intent=='uncertainty'
            exp_by_intent={
                'Form E':'LMO description donor parent organism vector method trait modified trait gene identity function target information',
                'uncertainty':'unknowns missing information do not infer organism host species construct vector BSL risk group facility transport classification Form E LMO description',
                'scope_gate':'IBC Assessment Report registered IBC researcher PI field scope boundary do not score',
                'annex_exclusion':'Annex 2 excluded do not score researcher PI missing field IBC Assessment Report',
                'fee_exclusion':'fees excluded application fee omission do not score BioSafe requirement',
                'approval_boundary':'no approval claim decision support not official approval compliance determination'
            }
            return Route('Malaysia','MY-FORME',intent,'Tier 2',['Form E','LMO description','researcher/PI boundary'],uncertain,False,
                         exp_by_intent.get(intent,exp_by_intent['Form E']),
                         f'Form E concept detected ({intent})')

        # 5) TRANSPORT before WASTE where question is explicitly about scope of transport guidance.
        explicit_transport_source = has_any(q,['specimen transport guideline','transport guideline','send patient specimens','send specimens','classification and packaging'])
        transport_terms = has_any(q,['clinical specimen','patient specimen','patient specimens','infectious substance','category a','category b','packaging','labelling','transport category','transported','another laboratory'])
        if explicit_transport_source or transport_terms:
            intent='transport_scope' if has_any(q,['dispose','disposal','clinical waste','also tell me']) else ('uncertainty' if has_any(q,['guess','nobody has assigned','not assigned']) else 'transport')
            exp={'transport':'clinical specimen infectious substance classification Category A Category B packaging labelling transport',
                 'transport_scope':'clinical specimen transport guideline scope not clinical waste rule disposal boundary',
                 'uncertainty':'unknown transport classification Category A Category B do not guess missing information clinical specimen'}[intent]
            return Route('Malaysia','TRANSPORT',intent,'Tier 2',['specimen classification','Category A/B','packaging','labelling','transport','transport scope'],intent=='uncertainty',False,
                         exp, f'clinical-specimen transport concept detected ({intent})')

        # 6) WASTE.
        if has_any(q,['sw 404','scheduled waste','pathogenic waste','quarantined material','clinical waste','lab waste','biological waste','waste system','disposal']):
            return Route('Malaysia','WASTE','waste','Tier 1+2',['scheduled waste','SW 404','storage','treatment','disposal'],False,False,
                         'SW 404 pathogenic waste quarantined material scheduled waste storage treatment disposal Malaysian requirements WHO corroboration',
                         'biological/clinical waste concept detected')

        # 7) Incident / emergency response, before generic contained-use.
        if has_any(q,['spill','spills','accident','accidents','emergency response','incident','escalation','contingency']) and has_any(q,['sop','contained use','contained-use','laboratory','biosafety']):
            return Route('Malaysia','MY-INCIDENT','incident','Tier 1+2',['emergency response','incident response','spills','accidents','escalation'],False,False,
                         'emergency response incident spill accident escalation containment SOP response plan',
                         'incident/emergency concept detected')

        # 8) IBC / PI governance.
        if has_any(q,['pi relationship to the ibc','pi responsibilities','pi s responsibilities','principal investigator']) and 'ibc' in q:
            return Route('Malaysia','MY-IBC','governance','Tier 2',['PI responsibilities','IBC governance'],False,False,
                         'PI responsibilities relationship registered IBC governance submission review oversight',
                         'PI/IBC governance concept detected')

        # 9) WHO risk assessment when clearly general/international rather than LMO/GMM-specific.
        who_ra_semantic = (
            has_any(q,['hazards','procedures','equipment','facilities','staff competence','competence']) and
            has_any(q,['before choosing controls','information needs to be gathered','laboratory activity'])
        ) or has_any(q,['likelihood and consequence','case by case risk assessment','case-by-case risk assessment','routine can controls be selected'])
        if who_ra_semantic and not has_any(q,['lmo','gmm','malaysia','form e']):
            return Route('International','WHO-RA','risk_assessment','Tier 3',['risk assessment','hazards','procedures','equipment','facility','competency','likelihood','consequence'],False,False,
                         'laboratory risk assessment gather hazards procedures equipment facilities personnel competence likelihood consequence case-by-case controls',
                         'general laboratory risk-assessment concept detected')

        # 10) WHO biosecurity.
        if has_any(q,['biosecurity','secure handling','high consequence research','high-consequence research']) or (
            has_any(q,['governance','storage']) and has_any(q,['who source','laboratory biosecurity'])):
            return Route('International','WHO-BIOSEC','biosecurity','Tier 3',['biosecurity','access','inventory','secure handling','governance'],False,False,
                         'WHO laboratory biosecurity governance secure handling storage access inventory high consequence research',
                         'biosecurity concept detected')

        # 11) Explicit Malaysian GMM risk-assessment and missing-science cases.
        if has_any(q,['gmm risk assessment','genetically modified microorganism risk assessment']):
            return Route('Malaysia','MY-RA','risk_assessment','Tier 2',['risk assessment','GMM','hazards','exposure','release','controls'],False,False,
                         'GMM risk assessment hazards exposure release controls BSL human animal plant environment',
                         'explicit GMM risk assessment detected')
        if has_any(q,['important scientific information is missing','scientific information is missing','missing scientific information','important scientific information']) and has_any(q,['missing','risk','happen']):
            return Route('Malaysia','MY-RA','uncertainty','Tier 1+2',['risk assessment','uncertainty','GMM'],True,False,
                         'missing scientific information uncertainty do not guess GMM risk assessment insufficient information lack scientific certainty',
                         'missing scientific-information risk case detected')

        # 12) Malaysian GMM/LMO risk uncertainty and contained-use regulatory routing.
        uncertainty_phrase = has_any(q,['not enough scientific information','insufficient scientific information','lack scientific information','missing scientific information','not enough information to be certain'])
        lowrisk_phrase = has_any(q,['low risk','tiny','small quantities','amount is small','bsl 1','bsl-1','no assessment','exempt'])
        notification_phrase = has_any(q,['notification','notify','no notification','notification form','submission'])
        contained = has_any(q,['contained use','contained-use','inside our laboratory','inside the laboratory','contained','modern biotechnology','lmo','gmm','biosafety level','containment level'])
        if uncertainty_phrase and has_any(q,['risk','decision','scientific']):
            return Route('Malaysia','MY-REG','uncertainty','Tier 1+2',['regulatory uncertainty','risk assessment','contained use'],True,False,
                         'lack scientific certainty insufficient information risk decision precaution uncertainty GMM case-by-case',
                         'Malaysian regulatory uncertainty concept detected')
        if contained or notification_phrase or lowrisk_phrase:
            if notification_phrase: intent='notification'
            elif lowrisk_phrase: intent='uncertainty'
            else: intent='IBC/containment'
            return Route('Malaysia','MY-REG',intent,'Tier 1+2' if intent!='notification' else 'Tier 1',['notification','contained use','GM-BSL','containment','risk assessment'],intent=='uncertainty',False,
                         'contained use LMO GMM modern biotechnology notification exemption low risk small quantity biosafety level containment risk assessment evidence Director General',
                         f'Malaysian contained-use regulatory concept detected ({intent})')

        # 13) Generic laboratory risk assessment phrase.
        if has_any(q,['laboratory risk','assessing laboratory risk','before assessing laboratory risk']):
            return Route('International','WHO-RA','risk_assessment','Tier 3',['risk assessment','agents','procedures','facility','competency'],False,False,
                         'laboratory risk assessment hazards agents procedures equipment facility personnel competency likelihood consequence',
                         'generic laboratory risk assessment detected')

        return Route('Malaysia','GENERAL','general','Tier 1+2',[],False,False,'','no specific route trigger')
