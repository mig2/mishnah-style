"""Deliverable 4: kb-validate.py (schema + semantic cross-checks, exit codes)."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _util import DATA, SCHEMA, SCRIPTS


def run_validate(data_dir):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "kb-validate.py"),
         "--data", str(data_dir), "--schema", str(SCHEMA)],
        capture_output=True, text=True)


class TestValidatorOnRealData(unittest.TestCase):
    def test_real_data_passes(self):
        r = run_validate(DATA)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class TestValidatorCatchesFailures(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.data = self.tmp / "data"
        shutil.copytree(DATA, self.data)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _edit(self, rel, old, new):
        p = self.data / rel
        p.write_text(p.read_text().replace(old, new))

    def assert_fails_with(self, needle):
        r = run_validate(self.data)
        self.assertEqual(r.returncode, 1, "expected failure exit")
        self.assertIn(needle, r.stdout)

    def test_schema_violation(self):
        self._edit("people/akiva.yaml", "status: enriched", "status: bogus")
        self.assert_fails_with("is not one of")

    def test_unknown_source(self):
        self._edit("plants/chitah.yaml", "source: feliks", "source: nonesuch")
        self.assert_fails_with("is not in sources.yaml")

    def test_noncanonical_appearance_slug(self):
        self._edit("places/tzippori.yaml", "  mishnah: []", '  mishnah: ["notamasechet 1:1"]')
        self.assert_fails_with("is not a canonical masechet slug")

    def test_filename_slug_mismatch(self):
        shutil.move(self.data / "people" / "akiva.yaml",
                    self.data / "people" / "rabbi-akiva.yaml")
        self.assert_fails_with("does not match filename")


if __name__ == "__main__":
    unittest.main()
