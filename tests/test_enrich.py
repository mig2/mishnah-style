"""Display phase 3: kb-enrich.py (entity overlay woven into masechot copies)."""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _util import DATA, REPO, SCRIPTS

MASECHOT = REPO / "masechot"


def mishna_text(path, mid):
    html = Path(path).read_text(encoding="utf-8")
    a = re.search(rf'id="{mid}"', html)
    b = re.search(r'<p class="mishna-text">(.*?)</p>', html[a.end():], re.S)
    return b.group(1)


def words(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


class EnrichCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(tempfile.mkdtemp()) / "read"
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "kb-enrich.py"),
             "--data", str(DATA), "--masechot", str(MASECHOT), "--out", str(cls.out)],
            capture_output=True, text=True)
        assert r.returncode == 0, r.stderr

    def read(self, slug):
        return (self.out / f"{slug}.html").read_text(encoding="utf-8")

    def test_plant_mention_wrapped_with_prefix_tolerance(self):
        # kilayim 1:1 has הַחִטִּים (definite-article prefix) -> matched to chitah
        page = self.read("kilayim")
        self.assertIn('<a class="ent ent-plant" href="../plants/chitah.html">הַחִטִּים</a>', page)

    def test_person_mention_wrapped_and_nested_in_bold(self):
        page = self.read("makkot")  # makkot 1:10
        self.assertIn('<b><a class="ent ent-person" href="../people/akiva.html">'
                      'רַבִּי עֲקִיבָא</a></b>', page)

    def test_overlay_scaffolding_present(self):
        page = self.read("kilayim")
        for needle in ('id="kb-plant"', 'class="kb-bar"', 'class="kb-content"',
                       "#kb-person:checked", "ent-plant"):
            self.assertIn(needle, page)

    def test_text_is_preserved(self):
        # enrichment only inserts <a> tags; the mishna text must be byte-for-byte the same
        for slug, mid in (("kilayim", "m1-1"), ("makkot", "m1-10"), ("challah", "m1-1")):
            with self.subTest(slug=slug):
                canon = words(mishna_text(MASECHOT / f"{slug}.html", mid))
                enr = words(mishna_text(self.out / f"{slug}.html", mid))
                self.assertEqual(canon, enr)

    def test_no_false_positive_when_form_absent(self):
        # akiva is indexed for brachot 9:5 but the form isn't in that mishna -> no mark
        page = self.read("brachot")
        self.assertNotIn('class="ent ent-person"', page)

    def test_canonical_masechot_untouched(self):
        # the canonical files never gain entity markup
        self.assertNotIn('class="ent ', (MASECHOT / "kilayim.html").read_text(encoding="utf-8"))
        self.assertNotIn("kb-bar", (MASECHOT / "makkot.html").read_text(encoding="utf-8"))

    def test_links_point_to_phase2_entity_pages(self):
        # ../plants/chitah.html is reachable from site/read/<slug>.html -> site/plants/
        self.assertIn("../plants/chitah.html", self.read("pesachim"))


if __name__ == "__main__":
    unittest.main()
