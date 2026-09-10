from pathlib import Path
import sys
ROOT=Path("/home/khengoon/biosafe")
for p in (ROOT/"src",ROOT/"unified_v1/src"):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from biosafe_unified223.service import Unified223Service
from biosafe_unified224 import ResponseTypeContractEnforcer,SemanticRepairLayer
class Unified224Service(Unified223Service):
    def __init__(self):
        super().__init__();self.contract=ResponseTypeContractEnforcer();self.repairer=SemanticRepairLayer()
    def infer(self,prep,documents=None):
        out=super().infer(prep,documents=documents)
        if not isinstance(out,dict):return out
        intent=self.intent(prep)
        flags=((out.get("_semantic_verifier") or {}).get("unsupported") or [])
        out,ra=self.repairer.repair(out,flags,out.get("evidence",[]) or [],prep["query"])
        out,ca=self.contract.apply(out,intent)
        out["_response_contract"]={"intent":intent,"audit":ca}
        out["_semantic_repair"]={"audit":ra}
        return out
