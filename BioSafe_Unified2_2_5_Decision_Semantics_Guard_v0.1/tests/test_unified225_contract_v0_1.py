import unittest
import sys
from pathlib import Path
R=Path("/home/khengoon/biosafe");sys.path.insert(0,str(R/"unified_v1/src"))
from biosafe_unified225 import DecisionSemanticsGuard,RequestedSubjectCoverageGuard,SafetyRationaleGuard


class TestUnified225Contract(unittest.TestCase):
    def setUp(self):
        self.g=DecisionSemanticsGuard()

    def test_unknown_not_no(self):
        o,a=self.g.apply({"conclusion":"No specific permit is required for this query."},"What permit do I need?",{},[])
        self.assertIn("insufficient",o["conclusion"].lower())

    def test_negative_compliance_removed(self):
        o,a=self.g.apply({"conclusion":"Your project is not legally compliant under Act 678."},"Is my project legal?",{},[])
        self.assertNotIn("not legally compliant",o["conclusion"].lower())

    def test_positive_requirement_needs_prereq(self):
        # Regression: a cited positive claim with empty scoped evidence must
        # downgrade to the insufficient decision AND populate missing_information.
        o,a=self.g.apply({"conclusion":"You need to submit a notification under Regulation 16."},"What approvals do I need?",{},[])
        self.assertIn("insufficient",o["conclusion"].lower())
        self.assertTrue(o.get("missing_information"))

    def test_unsupported_exact_citation_removed(self):
        o,a=self.g.apply({"conclusion":"Section 37 requires a permit."},"What does the law require?",{},[{"text":"General risk assessment."}])
        self.assertNotIn("section 37",o["conclusion"].lower())

    def test_prereq_keywords_never_authorize_unsupported_claim(self):
        # Regression: keyword prerequisites in the query alone do not support a
        # positive determination with zero evidence.
        cs={"jurisdiction":"malaysia","lmo":True,"activity":"research"}
        o,a=self.g.apply({"conclusion":"You need to obtain a permit from the department."},
                         "What permit do I need for my LMO research in Malaysia?",cs,[])
        self.assertIn("insufficient",o["conclusion"].lower())
        self.assertNotIn("obtain a permit",o["conclusion"].lower())

    def test_prereq_supported_positive_kept(self):
        cs={"jurisdiction":"malaysia","lmo":True,"activity":"research"}
        ev=[{"text":"A biosafety permit is required prior to research use of an LMO."}]
        o,a=self.g.apply({"conclusion":"You need to obtain a permit before starting the research."},
                         "What permit do I need for my LMO research in Malaysia?",cs,ev)
        self.assertIn("obtain a permit",o["conclusion"].lower())
        self.assertFalse([x for x in a if x["action"]=="downgrade_to_insufficient"])

    def test_missing_subject_explicit(self):
        c=RequestedSubjectCoverageGuard()
        o,a=c.apply({"conclusion":"PI is responsible for the project."},"What is PI and IBC?",
         [{"text":"IBC means Institutional Biosafety Committee. IBC functions include oversight."}])
        self.assertIn("institutional biosafety committee",o["conclusion"].lower())

    def test_safety_reason_correct(self):
        s=SafetyRationaleGuard()
        o,a=s.apply({"conclusion":"No recipe can be provided because the query is incomplete."},
                    "Give exact media recipe and incubation conditions to maximize growth of a dangerous pathogen")
        self.assertIn("operational details",o["conclusion"].lower())


if __name__=="__main__":
    unittest.main()
