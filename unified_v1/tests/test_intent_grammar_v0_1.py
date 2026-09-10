"""Deterministic tests for the structural intent grammar (no model, no network)."""

import sys
import unittest
from pathlib import Path

ROOT = Path("/home/khengoon/biosafe")
for p in (ROOT / "unified_v1/src",):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from biosafe_unified226 import canonicalize, parse_act  # noqa: E402


class CanonicalizeTests(unittest.TestCase):
    def test_contractions(self):
        self.assertEqual(canonicalize("What's biosafety?"), "what is biosafety")
        self.assertEqual(canonicalize("I'm new here"), "i am new here")

    def test_punctuation_and_case(self):
        self.assertEqual(canonicalize("  BIOSAFETY!!!  "), "biosafety")

    def test_filler_strip(self):
        self.assertEqual(canonicalize("Please tell me more"), "please tell me more")


class ParseActTests(unittest.TestCase):
    def test_greeting(self):
        r = parse_act("hi biosafe")
        self.assertEqual(r["act"], "greeting")
        r = parse_act("hello there")
        self.assertEqual(r["act"], "greeting")
        r = parse_act("hey biosafe")
        self.assertEqual(r["act"], "greeting")
        r = parse_act("good morning")
        self.assertEqual(r["act"], "greeting")

    def test_greeting_with_content(self):
        r = parse_act("hi, what can you do")
        self.assertEqual(r["act"], "product_help")

    def test_definition(self):
        r = parse_act("what is biosafety")
        self.assertEqual(r["act"], "definition")
        self.assertEqual(r["concept"], "biosafety")

    def test_difference(self):
        r = parse_act("what is the difference between biosafety and biosecurity")
        self.assertEqual(r["act"], "difference")
        self.assertEqual(r["concept"], "biosafety_vs_biosecurity")

    def test_continuation_binds_previous(self):
        r = parse_act("I just want to understand the difference",
                      previous_subject="biosafety and biosecurity")
        self.assertEqual(r["act"], "definition")
        self.assertEqual(r["concept"], "biosafety_vs_biosecurity")

    def test_elaboration_binds_previous(self):
        r = parse_act("please elaborate more using case studies",
                      previous_subject="biosafety and biosecurity")
        self.assertEqual(r["act"], "elaboration")
        self.assertEqual(r["concept"], "biosafety_vs_biosecurity")
        self.assertEqual(r["bound_subject"], "biosafety and biosecurity")

    def test_general_case_request_binds_previous(self):
        r = parse_act(
            "can you create it or use some general case for explanation",
            previous_subject="biosafety and biosecurity",
        )
        self.assertEqual(r["act"], "elaboration")
        self.assertEqual(r["concept"], "biosafety_vs_biosecurity")

    def test_unknown_falls_through(self):
        r = parse_act("i made 12 ml of the complex media sample")
        self.assertEqual(r["act"], "simple_answer")

    def test_regulatory(self):
        r = parse_act("does this need a transport permit")
        self.assertEqual(r["act"], "regulatory_assessment")


if __name__ == "__main__":
    unittest.main(verbosity=2)