"""Deliverable 3: source registry + controlled vocabularies."""

import unittest

from _util import DATA, load_yaml, is_valid, masechot_slugs, sedarim_slugs


class TestSources(unittest.TestCase):
    def test_sources_validate(self):
        self.assertTrue(is_valid("source", load_yaml(DATA / "sources.yaml")))

    def test_sefaria_is_registered(self):
        self.assertIn("sefaria", load_yaml(DATA / "sources.yaml"))


class TestSedarim(unittest.TestCase):
    def test_count_is_63(self):
        self.assertEqual(len(sedarim_slugs()), 63)

    def test_slugs_match_masechot_html_files(self):
        self.assertEqual(sedarim_slugs(), masechot_slugs())

    def test_chapters_are_positive_ints(self):
        data = load_yaml(DATA / "vocab" / "sedarim.yaml")
        for masechtot in data.values():
            for m in masechtot:
                self.assertIsInstance(m["chapters"], int)
                self.assertGreater(m["chapters"], 0)


class TestVocabParse(unittest.TestCase):
    def test_all_vocab_files_parse(self):
        for name in ("generations", "halachic-categories", "regions", "sedarim"):
            with self.subTest(vocab=name):
                self.assertIsInstance(load_yaml(DATA / "vocab" / f"{name}.yaml"), dict)


class TestExemplarVocabRefs(unittest.TestCase):
    """The hand-written exemplars must reference real vocabulary entries."""

    def test_chitah_halachic_in_vocab(self):
        cats = set(load_yaml(DATA / "vocab" / "halachic-categories.yaml"))
        used = set(load_yaml(DATA / "plants" / "chitah.yaml")["usage"]["halachic"])
        self.assertTrue(used <= cats, f"unknown halachic categories: {used - cats}")

    def test_tzippori_region_in_vocab(self):
        regions = set(load_yaml(DATA / "vocab" / "regions.yaml"))
        self.assertIn(load_yaml(DATA / "places" / "tzippori.yaml")["geo"]["region"], regions)

    def test_akiva_generation_in_vocab(self):
        gens = set(load_yaml(DATA / "vocab" / "generations.yaml"))
        self.assertIn(load_yaml(DATA / "people" / "akiva.yaml")["era"]["generation"], gens)


if __name__ == "__main__":
    unittest.main()
