from __future__ import annotations
import re
from copy import deepcopy

NEG = [
 r"\bno (?:specific )?(?:permit|approval|notification|authori[sz]ation)s? (?:is|are) required\b",
 r"\bno (?:specific )?(?:permit|approval|notification|authori[sz]ation)s? appl(?:y|ies)\b",
 r"\byou do not need (?:a|an|any) (?:permit|approval|notification|authori[sz]ation)\b",
 r"\b(?:permit|approval|notification|authori[sz]ation) is not (?:required|necessary)\b",
]
POS = [
 r"\byou need to (?:submit|obtain|apply for)\b",
 r"\byou must (?:submit|obtain|apply for)\b",
 r"\bis required to (?:submit|obtain|apply for)\b",
 # 2026-09-12 live A/B gap: "you need a/an ... permit" forms were not
 # classified as authorization claims and passed unguarded with no evidence.
 r"\byou need (?:a|an) [^.]{0,120}?(?:biosafety )?(?:permit|approval|notification|authori[sz]ation|licence|license)\b",
 r"\b(?:biosafety )?(?:permit|approval|notification|authori[sz]ation|licence|license)[^.]{0,80}?(?:is|are) required\b",
]
COMP = [
 r"\b(?:your|this|the) (?:project|activity|work) is (?:not )?(?:legally )?compliant\b",
 r"\b(?:your|this|the) (?:project|activity|work) is (?:legal|illegal)\b",
 r"\b(?:approved|not approved|certified|not certified)\b",
]
CITE = re.compile(r"\b(?:s\.|section|reg\.|regulation)\s*\d+[A-Za-z0-9()\-]*", re.I)

class DecisionSemanticsGuard:
    @staticmethod
    def _has_prereq(case_state, query):
        cs=" ".join(f"{k}:{v}" for k,v in (case_state or {}).items()).lower()
        q=(query or "").lower()
        jurisdiction=any(x in cs or x in q for x in ("malaysia","malaysian","jurisdiction"))
        trigger=any(x in cs or x in q for x in ("lmo","living modified organism","genetic modification",
            "genetically modified","recombinant","modern biotechnology","contained use","release","import","export"))
        activity=any(x in cs or x in q for x in ("research","project","activity","work","use","transport","import","export","release","contained"))
        return jurisdiction and trigger and activity

    @staticmethod
    def _citation_supported(sentence,evidence):
        cites=CITE.findall(sentence)
        if not cites:return True
        meta=" ".join(" ".join(str(e.get(k) or "") for k in ("section","subsection","regulation","article","citation","text"))
                      for e in (evidence or []))
        ml=meta.lower()
        return all(c.lower() in ml for c in cites)

    @staticmethod
    def _auth_supported(sentence,evidence):
        # Modeled on the 2251 successor contract: an authorization claim is
        # supported only when the subject of the claim AND its normative force
        # both appear in the scoped evidence. Absence of evidence is never
        # support, regardless of keyword prerequisites.
        claim=sentence.lower()
        source=" ".join(" ".join(str(e.get(k) or "") for k in ("text","statement","conclusion","section","subsection","regulation","article","citation"))
                        for e in (evidence or [])).lower()
        subjects={"permit":("permit","licence","license"),
                  "approval":("approval","approve"),
                  "notification":("notification","notify"),
                  "authorization":("authorization","authorisation","authorize","authorise")}
        requested=[name for name,terms in subjects.items() if any(t in claim for t in terms)]
        if not requested:return False
        subject_supported=all(any(t in source for t in subjects[name]) for name in requested)
        normative_supported=any(t in source for t in ("required","requires","must","shall","prior notification"))
        return subject_supported and normative_supported

    def apply(self,response,query="",case_state=None,evidence=None):
        out=deepcopy(response); evidence=evidence or []
        key="conclusion" if "conclusion" in out else "direct_answer"
        text=str(out.get(key) or "")
        sentences=re.split(r'(?<=[.!?])\s+',text)
        prereq=self._has_prereq(case_state or {},query)
        kept=[];audit=[]
        for s in sentences:
            if any(re.search(p,s,re.I) for p in COMP):
                audit.append({"action":"remove_compliance_verdict","sentence":s}); continue
            if any(re.search(p,s,re.I) for p in NEG+POS):
                # Prerequisites gate which facts are still needed; they never
                # authorize a positive or negative determination on their own.
                # An authorization claim survives only when the scoped evidence
                # supports the exact claim.
                if not prereq or not self._auth_supported(s,evidence):
                    repl=("The available information is insufficient to determine whether a permit, approval, "
                          "notification, or other regulatory authorization is required.")
                    kept.append(repl)
                    audit.append({"action":"downgrade_to_insufficient","original":s,"replacement":repl}); continue
                kept.append(s); continue
            if not self._citation_supported(s,evidence):
                audit.append({"action":"remove_unsupported_exact_citation","sentence":s}); continue
            kept.append(s)
        clean=" ".join(x for x in kept if x.strip()).strip()
        if not clean and text:
            clean=("BioSafe cannot make a legal, compliance, approval, permit, or notification determination "
                   "from the information currently available.")
        out[key]=clean
        if any(a["action"]=="downgrade_to_insufficient" for a in audit):
            mi=list(out.get("missing_information") or [])
            x="The jurisdiction and the specific material/activity facts that determine which regulatory pathway applies."
            if x not in mi:mi.append(x)
            out["missing_information"]=mi
        return out,audit

class RequestedSubjectCoverageGuard:
    WHAT=re.compile(r"^\s*(?:what is|what are|define|meaning of|explain)\s+(.+?)[?.!]*\s*$",re.I)
    _IMAGE_SUBJECTS=re.compile(
        r"\b(?:this image|the image|this photo|the photo|this picture|the picture|"
        r"this screenshot|the screenshot|this attachment|the attachment|"
        r"what is in the (?:image|photo|picture)|image about)\b",
        re.I,
    )
    _CONTINUATION=re.compile(
        r"\b(?:elaborate|explain more|explain further|more detail|go deeper|"
        r"i just want to (?:understand|learn|know)|i need to (?:learn|understand)|"
        r"tell me more)\b",
        re.I,
    )
    def requested(self,q):
        m=self.WHAT.match(q or "")
        if not m:return []
        body=m.group(1)
        if "difference between" in body.lower():return []
        if self._IMAGE_SUBJECTS.search(body):return []
        if self._CONTINUATION.search(q or ""):return []
        return [p.strip(" ?.") for p in re.split(r"\s*(?:,|/|\band\b)\s*",body,flags=re.I)
                if p.strip(" ?.")][:5]
    @staticmethod
    def present(s,text):
        if re.fullmatch(r"[A-Z][A-Z0-9-]{1,7}",s):
            return bool(re.search(rf"\b{re.escape(s)}\b\s*(?:means|=|\()",text,re.I))
        return s.lower() in text.lower()
    def apply(self,response,query,evidence):
        out=deepcopy(response); key="conclusion" if "conclusion" in out else "direct_answer"
        text=str(out.get(key) or ""); req=self.requested(query); audit=[]; add=[]
        ev=" ".join(str(e.get("text") or e.get("statement") or "") for e in (evidence or []))
        for s in [x for x in req if not self.present(x,text)]:
            if re.fullmatch(r"[A-Z][A-Z0-9-]{1,7}",s):
                m=re.search(rf"\b{re.escape(s)}\b\s*(?:\(|means|is short for)\s*([A-Za-z][A-Za-z -]{{3,80}})",ev,re.I)
                if m:
                    exp=m.group(1).strip(" ).,;:")
                    add.append(f"{s} means {exp}."); audit.append({"subject":s,"action":"define_from_evidence"})
                else:
                    add.append(f"BioSafe does not have enough scoped evidence to expand {s} confidently.")
                    audit.append({"subject":s,"action":"explicitly_unsupported"})
            else:
                add.append(f"BioSafe does not have enough scoped evidence to define {s} confidently.")
                audit.append({"subject":s,"action":"explicitly_unsupported"})
        if add: out[key]=(" ".join(add)+" "+text).strip()
        return out,audit

class SafetyRationaleGuard:
    SENSITIVE=("exact media recipe","incubation conditions","increase virulence","weapon",
               "evade detection","evade immunity","maximize growth","grow a dangerous pathogen",
               "release an agent without being detected")
    def apply(self,response,query):
        out=deepcopy(response); q=(query or "").lower()
        if not any(x in q for x in self.SENSITIVE):return out,[]
        key="conclusion" if "conclusion" in out else "direct_answer"
        text=str(out.get(key) or "")
        if "incomplete" in text.lower() or "not enough information" in text.lower():
            out[key]=("I can’t provide operational details that would enable cultivation, enhancement, weaponization, "
                      "evasion, or harmful use of a dangerous biological agent. I can help with high-level biosafety, "
                      "containment, oversight, or risk-management guidance instead.")
            return out,[{"action":"replace_incomplete_rationale_with_safety_rationale"}]
        return out,[]
