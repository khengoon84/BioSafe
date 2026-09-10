
from retrievers_router02 import BioSafeCFG01Router02, BioSafeCFG02Router02

class ScopeGateV021Mixin:
    """BioSafe Scope Gate v0.2.1.

    Changes candidate eligibility only. Router v0.2 and CFG-01/CFG-02 ranking formulas remain unchanged.
    """

    def _eligible(self, r, p):
        # Cross-cutting system controls must be retrievable for IBC approval/authority boundaries.
        if r['record_type'] == 'control_rule':
            if p.domain == 'MY-IBC' and p.intent == 'approval_boundary':
                return True
            return super()._eligible(r, p)

        # For MY-REG uncertainty claims, restrict the candidate set to evidence that can actually
        # establish/qualify exemption, regulatory uncertainty, or GMM risk assessment.
        # This avoids generic IBC/notification claims crowding out risk-assessment evidence.
        if p.domain == 'MY-REG' and p.intent == 'uncertainty':
            did = r['document_id']
            if did == 'KB-MY-GMMRA':
                return True
            if did == 'KB-MY-ACT678':
                return r.get('claim_type') == 'regulatory_uncertainty'
            if did == 'KB-MY-REG2010':
                return r.get('claim_type') == 'exemption'
            return False

        return super()._eligible(r, p)

class BioSafeCFG01ScopeV021(ScopeGateV021Mixin, BioSafeCFG01Router02):
    pass

class BioSafeCFG02ScopeV021(ScopeGateV021Mixin, BioSafeCFG02Router02):
    pass
