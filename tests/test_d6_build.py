"""Deliverable 6: kb-build.py (YAML -> knowledge.db)."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from _util import DATA, load_script, sedarim_slugs

kb_build = load_script("kb_build", "kb-build.py")


class BuildCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.db_path = cls.tmp / "knowledge.db"
        cls.counts = kb_build.build(DATA, cls.db_path)
        cls.db = sqlite3.connect(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def q(self, sql, *a):
        return self.db.execute(sql, a).fetchall()


class TestStructure(BuildCase):
    def test_entity_row_per_yaml_file(self):
        n_files = sum(len(list((DATA / f).glob("*.yaml")))
                      for f in ("people", "places", "plants"))
        self.assertEqual(self.counts["entity"], n_files)

    def test_source_table_matches_registry(self):
        import yaml
        with open(DATA / "sources.yaml") as f:
            self.assertEqual(self.counts["source"], len(yaml.safe_load(f)))

    def test_every_claim_source_is_registered(self):
        bad = self.q("SELECT field FROM claim WHERE source NOT IN (SELECT key FROM source)")
        self.assertEqual(bad, [])

    def test_mishnah_appearances_parse_to_canonical_masechet(self):
        slugs = sedarim_slugs()
        for ref, masechet in self.q("SELECT ref, masechet FROM appearance WHERE work='mishnah'"):
            self.assertEqual(masechet, ref.rsplit(" ", 1)[0])
            self.assertIn(masechet, slugs)

    def test_other_appearances_have_no_masechet(self):
        rows = self.q("SELECT masechet FROM appearance WHERE work='other'")
        self.assertTrue(all(m is None for (m,) in rows))

    def test_external_ids_have_no_nulls(self):
        self.assertEqual(self.q("SELECT * FROM external_id WHERE id IS NULL"), [])


class TestFlattening(BuildCase):
    def test_candidate_ids_preserved_in_extra_json(self):
        (extra,) = self.q(
            "SELECT extra_json FROM claim WHERE entity_slug='chitah' AND source='feliks'")[0]
        self.assertIn("wikidata_qid", json.loads(extra)["ids"])

    def test_coordinate_value_is_lat_lon(self):
        (vj,) = self.q(
            "SELECT value_json FROM claim WHERE entity_slug='tzippori' "
            "AND field='geo.coordinates'")[0]
        self.assertEqual(set(json.loads(vj)), {"lat", "lon"})

    def test_region_rollup(self):
        rows = dict(self.q("SELECT region, place_count FROM region_rollup"))
        self.assertEqual(rows.get("galilee"), 1)


class TestDeterminism(unittest.TestCase):
    def test_build_is_byte_identical_across_runs(self):
        tmp = Path(tempfile.mkdtemp())
        a, b = tmp / "a.db", tmp / "b.db"
        kb_build.build(DATA, a)
        kb_build.build(DATA, b)
        self.assertEqual(a.read_bytes(), b.read_bytes())


if __name__ == "__main__":
    unittest.main()
