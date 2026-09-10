
import sys
from pathlib import Path
PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG / "src"))
from decision_quality_refinement_v0_1 import BioSafeDecisionQualityRefinementV01

g = BioSafeDecisionQualityRefinementV01()

q = "I am working with Bacillus antracts in my laboratory. Do I need to notify the Director General under the Biosafety Regulations?"

r = g.apply({
    "conclusion": "The organism identity is not yet confirmed, so BioSafe should not make an organism-specific risk-group, biosafety-level, containment, PPE, transport, or disposal determination at this stage. Please confirm the organism name first.",
    "applicable_authority": ["Department of Biosafety / Malaysia", "Ministry of Health Malaysia"],
    "evidence": [
        {"evidence_id":"CLM-013","statement":"A defensible risk assessment should contain enough background and detail for reviewers to understand hazards."},
        {"evidence_id":"CLM-014","statement":"Risk assessment should be reviewed and updated."},
        {"evidence_id":"CLM-028","statement":"The MOH clinical-specimen transport guideline does not serve as the clinical-waste guideline."}
    ],
    "limitations": ["BioSafe provides an evidence-based advisory review and does not certify regulatory compliance or approval."],
    "missing_information": [
        "Confirm the organism name. The supplied term 'bacillus antracts' may be a misspelling; please confirm whether you mean 'Bacillus anthracis' or a different organism.",
        "Specific containment area requirements",
        "PPE type (e.g., N95 vs. full suit)"
    ],
    "recommended_next_step": [
        "Please confirm the organism identity before BioSafe applies organism-specific risk or containment guidance."
    ],
    "safety": {
        "classification":"caution",
        "response_mode":"ask_before_concluding",
        "reason":"Organism-specific conclusions require the organism identity to be confirmed."
    }
}, user_query=q)

mi = " | ".join(r.response.get("missing_information", [])).lower()
recs = " | ".join(r.response.get("recommended_next_step", [])).lower()
lims = " | ".join(r.response.get("limitations", [])).lower()

tests = [
    ("DQ14-001-remove-containment-missing", "specific containment area" not in mi),
    ("DQ14-002-remove-ppe-missing", "ppe type" not in mi),
    ("DQ14-003-preserve-organism-confirmation", "confirm the organism name" in mi),
    ("DQ14-004-add-lmo-trigger", "living modified organism" in mi),
    ("DQ14-005-add-regulatory-next-step", "malaysian biosafety notification pathway" in recs),
    ("DQ14-006-add-applicability-limitation", "notification applicability determination" in lims),
    ("DQ14-007-ask-before-concluding", r.response["safety"]["response_mode"] == "ask_before_concluding"),
]

r2 = g.apply({
    "conclusion":"The organism identity is not yet confirmed.",
    "evidence":[],
    "missing_information":[
        "Confirm the organism name. The supplied term 'bacillus antracts' may be a misspelling; please confirm whether you mean 'Bacillus anthracis' or a different organism.",
        "Specific containment area requirements"
    ],
    "recommended_next_step":[],
    "limitations":[],
    "safety":{"classification":"caution","response_mode":"ask_before_concluding","reason":""}
}, user_query="What containment level should I use for Bacillus antracts?")

tests.append((
    "DQ14-008-keep-containment-when-user-asks",
    any("containment area" in x.lower() for x in r2.response["missing_information"])
))

failed = [name for name, ok in tests if not ok]
for name, ok in tests:
    print(("PASS" if ok else "FAIL"), name)
print(f"\nSummary: {len(tests)-len(failed)}/{len(tests)} passed")
if failed:
    raise SystemExit("Failures: " + ", ".join(failed))
print("Decision Quality Refinement v0.1.4 regression: PASS")
