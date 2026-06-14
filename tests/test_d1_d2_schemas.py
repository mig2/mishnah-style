"""Deliverables 1–2: the five JSON schemas (claim, source, person, place, plant)."""

import json
import unittest

from _util import SCHEMA, load_registry, is_valid, validator_for


class TestSchemasWellFormed(unittest.TestCase):
    def test_all_schema_files_are_valid_json_schema(self):
        from jsonschema import Draft202012Validator
        files = sorted(SCHEMA.glob("*.schema.json"))
        self.assertEqual(len(files), 5, "expected 5 schema files")
        for p in files:
            with self.subTest(schema=p.name):
                Draft202012Validator.check_schema(json.loads(p.read_text()))

    def test_cross_file_ref_resolves(self):
        # person.bio items $ref "claim.schema.json"; building a validator must not raise
        validator_for("person")


class TestClaim(unittest.TestCase):
    def test_minimal_valid(self):
        self.assertTrue(is_valid("claim", {"value": "x", "source": "wikidata"}))

    def test_source_required(self):
        self.assertFalse(is_valid("claim", {"value": "x"}))

    def test_bad_confidence_rejected(self):
        self.assertFalse(is_valid("claim", {"value": 1, "source": "s", "confidence": "maybe"}))

    def test_bad_date_rejected(self):
        self.assertFalse(is_valid("claim", {"value": 1, "source": "s", "date": "2026/01/01"}))

    def test_extra_keys_allowed(self):
        # candidates carry `ids`, medicinal carries `provenance`
        self.assertTrue(is_valid("claim", {"value": 1, "source": "s", "ids": {"wikidata_qid": "Q1"}}))


class TestSource(unittest.TestCase):
    def good(self):
        return {"k": {"citation": "c", "type": "structured", "license": "CC0", "trust_tier": 1}}

    def test_valid(self):
        self.assertTrue(is_valid("source", self.good()))

    def test_missing_required_rejected(self):
        bad = self.good()
        del bad["k"]["trust_tier"]
        self.assertFalse(is_valid("source", bad))

    def test_bad_type_enum_rejected(self):
        bad = self.good()
        bad["k"]["type"] = "blog"
        self.assertFalse(is_valid("source", bad))

    def test_negative_trust_tier_rejected(self):
        bad = self.good()
        bad["k"]["trust_tier"] = -1
        self.assertFalse(is_valid("source", bad))


class TestPerson(unittest.TestCase):
    def base(self):
        return {"slug": "x", "status": "stub", "type": "tanna", "names": {"he": "פ"}}

    def test_minimal_valid(self):
        self.assertTrue(is_valid("person", self.base()))

    def test_missing_names_rejected(self):
        d = self.base()
        del d["names"]
        self.assertFalse(is_valid("person", d))

    def test_bad_type_enum_rejected(self):
        d = self.base()
        d["type"] = "robot"
        self.assertFalse(is_valid("person", d))

    def test_additional_properties_rejected(self):
        d = self.base()
        d["surprise"] = 1
        self.assertFalse(is_valid("person", d))

    def test_uppercase_slug_rejected(self):
        d = self.base()
        d["slug"] = "Rabbi_Akiva"
        self.assertFalse(is_valid("person", d))

    def test_generation_range_enforced(self):
        d = self.base()
        d["era"] = {"generation": 9}
        self.assertFalse(is_valid("person", d))

    def test_bio_claim_requires_source(self):
        d = self.base()
        d["bio"] = [{"value": "leading tanna"}]   # no source
        self.assertFalse(is_valid("person", d))

    def test_appearance_ref_pattern(self):
        ok = self.base()
        ok["appearances"] = {"mishnah": ["shekalim 4:2"]}
        self.assertTrue(is_valid("person", ok))
        bad = self.base()
        bad["appearances"] = {"mishnah": ["Shekalim chapter 4"]}
        self.assertFalse(is_valid("person", bad))


class TestPlace(unittest.TestCase):
    def base(self):
        return {"slug": "x", "status": "stub", "type": "settlement", "names": {"he": "פ"}}

    def test_minimal_valid(self):
        self.assertTrue(is_valid("place", self.base()))

    def test_geo_null_allowed(self):
        d = self.base()
        d["geo"] = None  # temple_structure / legal_domain
        self.assertTrue(is_valid("place", d))

    def test_coordinate_claim_requires_source(self):
        d = self.base()
        d["geo"] = {"coordinates": [{"value": {"lat": 1, "lon": 2}}]}
        self.assertFalse(is_valid("place", d))

    def test_geo_consensus_enum(self):
        d = self.base()
        d["geo"] = {"consensus": "definitely"}
        self.assertFalse(is_valid("place", d))


class TestPlant(unittest.TestCase):
    def base(self):
        return {"slug": "x", "status": "stub", "term": {"he": "פ"}, "term_type": "species"}

    def test_minimal_valid(self):
        self.assertTrue(is_valid("plant", self.base()))

    def test_term_type_enum(self):
        d = self.base()
        d["term_type"] = "weed"
        self.assertFalse(is_valid("plant", d))

    def test_candidate_requires_source(self):
        d = self.base()
        d["identification"] = {"candidates": [{"value": {"taxon": "T", "rank": "species"}}]}
        self.assertFalse(is_valid("plant", d))

    def test_candidate_valid_with_source_and_ids(self):
        d = self.base()
        d["identification"] = {"candidates": [
            {"value": {"taxon": "T", "rank": "species"}, "source": "feliks",
             "ids": {"wikidata_qid": "Q1"}}]}
        self.assertTrue(is_valid("plant", d))


if __name__ == "__main__":
    unittest.main()
