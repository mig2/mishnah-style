"""Deliverable 5: the hand-written exemplars (akiva, tzippori, chitah)."""

import unittest

from _util import DATA, load_yaml, validator_for, sedarim_slugs

EXEMPLARS = {"person": "people/akiva.yaml",
             "place": "places/tzippori.yaml",
             "plant": "plants/chitah.yaml"}


class TestExemplars(unittest.TestCase):
    def test_each_validates_against_its_schema(self):
        for kind, rel in EXEMPLARS.items():
            with self.subTest(kind=kind):
                errs = list(validator_for(kind).iter_errors(load_yaml(DATA / rel)))
                self.assertEqual(errs, [], [e.message for e in errs])

    def test_filename_matches_slug(self):
        for rel in EXEMPLARS.values():
            with self.subTest(file=rel):
                doc = load_yaml(DATA / rel)
                self.assertEqual(doc["slug"], (DATA / rel).stem)

    def test_appearances_use_canonical_slugs(self):
        slugs = sedarim_slugs()
        for rel in EXEMPLARS.values():
            doc = load_yaml(DATA / rel)
            for ref in (doc.get("appearances") or {}).get("mishnah") or []:
                with self.subTest(ref=ref):
                    self.assertIn(ref.rsplit(" ", 1)[0], slugs)

    def test_one_exemplar_per_kind_exists(self):
        for rel in EXEMPLARS.values():
            self.assertTrue((DATA / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
