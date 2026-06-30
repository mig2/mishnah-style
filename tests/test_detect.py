"""Detector: resolution engine, deterministic detection, promote, rerun-delta."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _util import DATA, REPO, SCRIPTS, load_yaml, validator_for

import kb_detect as engine

MASECHOT = REPO / "masechot"

ENTITIES = [
    {"kind": "plant", "slug": "chitah", "forms": ["חיטה", "חטים"]},
    {"kind": "person", "slug": "yehuda-b-ilai", "forms": ["רבי יהודה"]},
    {"kind": "person", "slug": "yehuda-ha-nasi", "forms": ["רבי יהודה"]},
    {"kind": "person", "slug": "akiva", "forms": ["רבי עקיבא"]},
]


class TestEngine(unittest.TestCase):
    def R(self, rejections=(), rules=()):
        return engine.Resolver(ENTITIES, rejections, rules)

    def test_known_single_candidate(self):
        r = self.R().resolve("רבי עקיבא", "person", "makkot 1:10")
        self.assertEqual((r["status"], r["slug"]), ("known", "akiva"))

    def test_new_when_unknown(self):
        self.assertEqual(self.R().resolve("רבי טרפון", "person", "makkot 1:10")["status"], "new")

    def test_ambiguous_two_candidates(self):
        r = self.R().resolve("רבי יהודה", "person", "shabbat 1:4")
        self.assertEqual(r["status"], "ambiguous")
        self.assertEqual(r["candidates"], ["yehuda-b-ilai", "yehuda-ha-nasi"])

    def test_rule_resolves_ambiguous(self):
        rules = [{"form": "רבי יהודה", "kind": "person", "resolve": "yehuda-b-ilai", "scope": "global"}]
        r = self.R(rules=rules).resolve("רבי יהודה", "person", "shabbat 1:4")
        self.assertEqual((r["status"], r["slug"]), ("known", "yehuda-b-ilai"))

    def test_rule_scope_precedence(self):
        rules = [
            {"form": "רבי יהודה", "kind": "person", "resolve": "yehuda-b-ilai", "scope": "global"},
            {"form": "רבי יהודה", "kind": "person", "resolve": "yehuda-ha-nasi", "scope": "masechet", "masechet": "avot"},
        ]
        res = self.R(rules=rules)
        self.assertEqual(res.resolve("רבי יהודה", "person", "avot 1:1")["slug"], "yehuda-ha-nasi")
        self.assertEqual(res.resolve("רבי יהודה", "person", "shabbat 1:1")["slug"], "yehuda-b-ilai")

    def test_rejection_global_and_per_mishna(self):
        g = self.R(rejections=[{"form": "רבי עקיבא", "kind": "person", "scope": "global"}])
        self.assertEqual(g.resolve("רבי עקיבא", "person", "makkot 1:10")["status"], "rejected")
        m = self.R(rejections=[{"form": "רבי עקיבא", "kind": "person", "scope": "mishna", "ref": "makkot 1:10"}])
        self.assertEqual(m.resolve("רבי עקיבא", "person", "makkot 1:10")["status"], "rejected")
        self.assertEqual(m.resolve("רבי עקיבא", "person", "avot 3:13")["status"], "known")

    def test_prefix_tolerance(self):
        # הַחִטִּים -> normalized החטים -> deprefix -> חטים -> chitah
        r = self.R().resolve("הַחִטִּים", "plant", "kilayim 1:1")
        self.assertEqual((r["status"], r["slug"]), ("known", "chitah"))

    def test_kind_separates_matches(self):
        self.assertEqual(self.R().resolve("רבי יהודה", "plant", "x 1:1")["status"], "new")


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          capture_output=True, text=True)


class TestDetectBold(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.data = self.tmp / "data"
        shutil.copytree(DATA, self.data)
        self.prop = self.tmp / "proposals.json"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def detect(self):
        return run("kb-detect.py", "--mode", "bold", "--masechet", "makkot",
                   "--data", str(self.data), "--masechot", str(MASECHOT), "--out", str(self.prop))

    def test_known_appearance_written_and_proposals_made(self):
        r = self.detect()
        self.assertEqual(r.returncode, 0, r.stderr)
        akiva = load_yaml(self.data / "people" / "akiva.yaml")
        self.assertIn("makkot 1:10", akiva["appearances"]["mishnah"])
        prop = json.loads(self.prop.read_text())
        self.assertIn("רבי מאיר", prop["proposals"])

    def test_idempotent_appearances(self):
        self.detect()
        self.detect()
        apps = load_yaml(self.data / "people" / "akiva.yaml")["appearances"]["mishnah"]
        self.assertEqual(apps.count("makkot 1:10"), 1)

    def test_llm_mode_not_implemented(self):
        r = run("kb-detect.py", "--mode", "llm")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not implemented", (r.stdout + r.stderr).lower())


class TestPromoteAndDelta(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.data = self.tmp / "data"
        shutil.copytree(DATA, self.data)
        self.detect_dir = self.tmp / "detect"
        self.prop = self.tmp / "proposals.json"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_promote_creates_valid_stub_rejections_rules(self):
        decisions = {
            "accept": [{"kind": "person", "slug": "meir", "type": "tanna",
                        "names": {"he": "רבי מאיר", "en": "Rabbi Meir"},
                        "variants": ["רַבִּי מֵאִיר"], "refs": ["makkot 1:2"]}],
            "reject": [{"form": "זה הכלל", "kind": "plant", "scope": "global"}],
            "rules": [{"form": "רבי יהודה", "kind": "person", "resolve": "yehuda-b-ilai", "scope": "global"}],
        }
        dpath = self.tmp / "decisions.json"
        dpath.write_text(json.dumps(decisions, ensure_ascii=False))
        r = run("kb-promote.py", str(dpath), "--data", str(self.data), "--detect", str(self.detect_dir))
        self.assertEqual(r.returncode, 0, r.stderr)

        stub = load_yaml(self.data / "people" / "meir.yaml")
        self.assertEqual(list(validator_for("person").iter_errors(stub)), [])
        self.assertEqual(stub["status"], "stub")
        self.assertIn("makkot 1:2", stub["appearances"]["mishnah"])

        rej = load_yaml(self.detect_dir / "rejections.yaml")
        self.assertEqual(list(validator_for("rejection").iter_errors(rej)), [])
        rules = load_yaml(self.detect_dir / "rules.yaml")
        self.assertEqual(list(validator_for("rule").iter_errors(rules)), [])

    def test_rerun_delta_promoted_entity_no_longer_proposed(self):
        # promote meir, then a fresh detect run should resolve רבי מאיר as known
        decisions = {"accept": [{"kind": "person", "slug": "meir", "type": "tanna",
                                 "names": {"he": "רבי מאיר"}, "variants": ["רַבִּי מֵאִיר"], "refs": []}]}
        dpath = self.tmp / "decisions.json"
        dpath.write_text(json.dumps(decisions, ensure_ascii=False))
        run("kb-promote.py", str(dpath), "--data", str(self.data), "--detect", str(self.detect_dir))
        run("kb-detect.py", "--mode", "bold", "--masechet", "makkot",
            "--data", str(self.data), "--masechot", str(MASECHOT), "--out", str(self.prop))
        prop = json.loads(self.prop.read_text())
        self.assertNotIn("רבי מאיר", prop["proposals"])
        self.assertIn("makkot 1:2", load_yaml(self.data / "people" / "meir.yaml")["appearances"]["mishnah"])


if __name__ == "__main__":
    unittest.main()
