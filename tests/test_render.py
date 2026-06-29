"""Display phase 2: kb-render.py (static views on the KB)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _util import DATA, SCRIPTS


class RenderCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(tempfile.mkdtemp()) / "site"
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "kb-render.py"),
             "--data", str(DATA), "--out", str(cls.out)],
            capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        cls.r = r

    def read(self, rel):
        return (self.out / rel).read_text(encoding="utf-8")

    def test_all_pages_written(self):
        for rel in ("index.html", "people.html", "places.html", "plants.html",
                    "people/akiva.html", "places/tzippori.html", "plants/chitah.html"):
            with self.subTest(page=rel):
                self.assertTrue((self.out / rel).exists(), rel)

    def test_home_links_to_aggregates(self):
        home = self.read("index.html")
        for agg in ("people.html", "places.html", "plants.html"):
            self.assertIn(f"href='{agg}'", home)

    def test_person_page_has_name_and_deep_link(self):
        page = self.read("people/akiva.html")
        self.assertIn("רבי עקיבא", page)
        # appearance resolves to the canonical masechet anchor, correct relative depth
        self.assertIn("../../../masechot/brachot.html#mishna-9-5", page)

    def test_plant_page_shows_candidate_with_source(self):
        page = self.read("plants/chitah.html")
        self.assertIn("Triticum aestivum", page)
        self.assertIn("feliks", page)          # candidate source visible (dissent stays visible)
        self.assertIn("../../../masechot/kilayim.html#mishna-1-1", page)

    def test_place_page_has_coordinate_and_osm(self):
        page = self.read("places/tzippori.html")
        self.assertIn("openstreetmap.org", page)
        self.assertIn("pleiades", page)

    def test_aggregate_links_to_entity_pages(self):
        self.assertIn("people/akiva.html", self.read("people.html"))
        self.assertIn("plants/chitah.html", self.read("plants.html"))

    def test_nonentity_relationship_falls_back_to_slug(self):
        # akiva's teachers aren't entities yet -> rendered as bare slug, not a broken link
        page = self.read("people/akiva.html")
        self.assertIn("eliezer-b-hyrcanus", page)
        self.assertNotIn("people/eliezer-b-hyrcanus.html", page)


if __name__ == "__main__":
    unittest.main()
