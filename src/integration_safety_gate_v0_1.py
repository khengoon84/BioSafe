
from __future__ import annotations
import re

class SafetyDecision:
    def __init__(self, restricted:bool, reason:str, matched:list[str]):
        self.restricted=restricted
        self.reason=reason
        self.matched=matched

def classify_safety(query:str)->SafetyDecision:
    q=query.lower()
    patterns={
        "increase harmful biological capability":[
            r"increase (?:the )?infectivity", r"increase (?:the )?pathogenicity",
            r"increase (?:the )?virulence", r"make .* more infectious", r"make .* more harmful"
        ],
        "defeat or bypass containment":[
            r"overcome .*containment", r"defeat .*containment", r"bypass .*containment",
            r"evade .*containment", r"circumvent .*containment"
        ],
        "actionable modification request":[
            r"detailed procedure .*modifying .*biological", r"step[- ]by[- ]step .*modif",
            r"procedure .* biological agent .* containment"
        ]
    }
    matched=[]
    for label,ps in patterns.items():
        if any(re.search(p,q) for p in ps):
            matched.append(label)
    return SafetyDecision(bool(matched),
                          "Request may enable harmful biological capability or defeat containment." if matched else "",
                          matched)
