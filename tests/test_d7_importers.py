"""Deliverable 7: the §8 upsert engine (kb_lib) and the importers."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _util import DATA, FIXTURES, SCRIPTS, load_script  # puts scripts/ on sys.path

import kb_lib as kb
from ruamel.yaml.comments import CommentedMap

wd_import = load_script("kb_import_wikidata", "kb-import-wikidata.py")
pl_import = load_script("kb_import_pleiades", "kb-import-pleiades.py")


def entity(**kw):
    d = CommentedMap()
    d.update(kw)
    return d


def load_fixture(rel):
    return json.loads((FIXTURES / rel).read_text())


# --------------------------------------------------------------------------- #
# §8 merge rules
# --------------------------------------------------------------------------- #
class TestEngine(unittest.TestCase):
    def test_single_reupsert_same_value_unchanged(self):
        d, c = entity(slug="x"), []
        kb.upsert_claim(d, "bio", "A", "wikidata", mode="single", conflicts=c)
        r = kb.upsert_claim(d, "bio", "A", "wikidata", mode="single", conflicts=c)
        self.assertEqual(r, "unchanged")
        self.assertEqual(len(d["bio"]), 1)

    def test_single_changed_value_updates_in_place(self):
        d, c = entity(slug="x"), []
        kb.upsert_claim(d, "bio", "A", "wikidata", mode="single", conflicts=c)
        r = kb.upsert_claim(d, "bio", "B", "wikidata", mode="single", conflicts=c)
        self.assertEqual(r, "updated")
        self.assertEqual(len(d["bio"]), 1)
        self.assertEqual(d["bio"][0]["value"], "B")

    def test_confirmed_claim_is_protected(self):
        d, c = entity(slug="x"), []
        kb.upsert_claim(d, "bio", "keep", "manual", mode="single", conflicts=c, confirmed=True)
        r = kb.upsert_claim(d, "bio", "overwrite", "manual", mode="single", conflicts=c)
        self.assertEqual(r, "conflict")
        self.assertEqual(d["bio"][0]["value"], "keep")
        self.assertEqual(len(c), 1)

    def test_multi_dedups_and_retains_dissent(self):
        d, c = entity(slug="x"), []
        kb.upsert_claim(d, "geo.coordinates", {"lat": 1, "lon": 2}, "pleiades", mode="multi", conflicts=c)
        same = kb.upsert_claim(d, "geo.coordinates", {"lat": 1, "lon": 2}, "pleiades", mode="multi", conflicts=c)
        other = kb.upsert_claim(d, "geo.coordinates", {"lat": 9, "lon": 9}, "wikidata", mode="multi", conflicts=c)
        self.assertEqual(same, "unchanged")
        self.assertEqual(other, "added")
        self.assertEqual(len(d["geo"]["coordinates"]), 2)

    def test_appearance_dedupe(self):
        d = entity(slug="x")
        self.assertTrue(kb.add_appearance(d, "mishnah", "shekalim 4:2"))
        self.assertFalse(kb.add_appearance(d, "mishnah", "shekalim 4:2"))

    def test_external_id_idempotent(self):
        d = entity(slug="x")
        self.assertTrue(kb.set_external_id(d, "wikidata_qid", "Q1"))
        self.assertFalse(kb.set_external_id(d, "wikidata_qid", "Q1"))

    def test_flow_map_renders_inline(self):
        d = entity(slug="x")
        kb.upsert_claim(d, "geo.coordinates", kb.flow_map({"lat": 1, "lon": 2}),
                        "pleiades", mode="multi", conflicts=[])
        import io
        buf = io.StringIO()
        kb.make_yaml().dump(d, buf)
        self.assertIn("{lat: 1, lon: 2}", buf.getvalue())

    def test_roundtrip_preserves_comments(self):
        data = kb.load_entity(DATA / "people" / "akiva.yaml")
        kb.upsert_claim(data, "bio", "new note", "manual", mode="multi", conflicts=[])
        import io
        buf = io.StringIO()
        kb.make_yaml().dump(data, buf)
        self.assertIn("tannaitic generation", buf.getvalue())


# --------------------------------------------------------------------------- #
# Wikidata importer transforms
# --------------------------------------------------------------------------- #
class TestWikidataTransform(unittest.TestCase):
    def test_person_bio_and_variants(self):
        d, c = entity(slug="akiva", names=CommentedMap({"he": "רבי עקיבא"})), []
        wd = load_fixture("wikidata/Q310357.json")
        wd_import.transform("person", "Q310357", wd, d, c)
        self.assertEqual(d["bio"][0]["source"], "wikidata")
        self.assertIn("tanna", d["bio"][0]["value"])
        self.assertIn("Akiva ben Joseph", d["names"]["variants"])

    def test_person_is_idempotent(self):
        d, c = entity(slug="akiva", names=CommentedMap({"he": "רבי עקיבא"})), []
        wd = load_fixture("wikidata/Q310357.json")
        wd_import.transform("person", "Q310357", wd, d, c)
        log = wd_import.transform("person", "Q310357", wd, d, c)
        self.assertTrue(all(s in ("unchanged", "0") for _, s in log), log)
        self.assertEqual(len(d["bio"]), 1)

    def test_place_coord_and_photo(self):
        d, c = entity(slug="tzippori", geo=CommentedMap({"region": "galilee"})), []
        wd = load_fixture("wikidata/Q745966.json")
        wd_import.transform("place", "Q745966", wd, d, c)
        coord = d["geo"]["coordinates"][0]["value"]
        self.assertEqual((coord["lat"], coord["lon"]), (32.7522, 35.2797))
        self.assertIn("commons.wikimedia.org", d["media"]["photo"])

    def test_plant_candidate_via_qid(self):
        d, c = entity(slug="chitah", term=CommentedMap({"he": "חיטה"})), []
        wd = load_fixture("wikidata/Q12100.json")
        wd_import.transform("plant", "Q12100", wd, d, c)
        cand = d["identification"]["candidates"][0]
        self.assertEqual(cand["value"]["taxon"], "Triticum aestivum")
        self.assertEqual(cand["value"]["rank"], "species")  # P105 Q7432 -> species
        self.assertEqual(cand["ids"]["wikidata_qid"], "Q12100")

    def test_confirmed_bio_protected_through_importer(self):
        d, c = entity(slug="akiva", names=CommentedMap({"he": "x"})), []
        kb.upsert_claim(d, "bio", "hand-written", "wikidata", mode="single",
                        conflicts=c, confirmed=True)
        wd = load_fixture("wikidata/Q310357.json")
        wd_import.transform("person", "Q310357", wd, d, c)
        self.assertEqual(d["bio"][0]["value"], "hand-written")
        self.assertEqual(len(c), 1)


# --------------------------------------------------------------------------- #
# Pleiades importer transform
# --------------------------------------------------------------------------- #
class TestPleiadesTransform(unittest.TestCase):
    def test_coord_from_repr_point(self):
        d, c = entity(slug="tzippori", geo=CommentedMap({})), []
        pl = load_fixture("pleiades/678378.json")
        pl_import.transform(pl, d, c)
        coord = d["geo"]["coordinates"][0]["value"]
        self.assertEqual((coord["lat"], coord["lon"]), (32.7522, 35.2797))  # reprPoint is [lon, lat]


# --------------------------------------------------------------------------- #
# CLI integration: writes valid YAML, flow style, idempotent
# --------------------------------------------------------------------------- #
class TestImporterCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.data = self.tmp / "data"
        shutil.copytree(DATA, self.data)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_wd(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "kb-import-wikidata.py"),
             "--data", str(self.data), *args],
            capture_output=True, text=True)

    def test_place_import_writes_flow_coord_and_is_idempotent(self):
        first = self.run_wd("--kind", "places", "--slug", "tzippori",
                            "--input", str(FIXTURES / "wikidata/Q745966.json"))
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("geo.coordinates=added", first.stdout)
        text = (self.data / "places" / "tzippori.yaml").read_text()
        self.assertIn("{lat: 32.7522, lon: 35.2797}", text)  # flow style preserved
        # re-run -> no change
        second = self.run_wd("--kind", "places", "--slug", "tzippori",
                             "--input", str(FIXTURES / "wikidata/Q745966.json"))
        self.assertIn("no change", second.stdout)


if __name__ == "__main__":
    unittest.main()
