#!/usr/bin/env python3
"""Offline self-test for the §8 merge rules in kb_lib. No network, no fixtures.
Run in CI to guarantee the upsert engine keeps its invariants.

Requires: ruamel.yaml.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kb_lib as kb
from ruamel.yaml.comments import CommentedMap


def entity(slug="x"):
    d = CommentedMap()
    d["slug"] = slug
    return d


_failed = []


def check(name, cond):
    print(("\033[32m✓\033[0m " if cond else "\033[31m✗\033[0m ") + name)
    if not cond:
        _failed.append(name)


# 1. single: re-adding the same value is a no-op (idempotent, no churn)
d, conf = entity(), []
kb.upsert_claim(d, "bio", "A", "wikidata", mode="single", conflicts=conf)
r = kb.upsert_claim(d, "bio", "A", "wikidata", mode="single", conflicts=conf)
check("single: re-add same value -> unchanged, no duplicate",
      r == "unchanged" and len(d["bio"]) == 1)

# 2. single: a changed value updates in place (one claim per source)
r = kb.upsert_claim(d, "bio", "B", "wikidata", mode="single", conflicts=conf)
check("single: changed value -> updated in place",
      r == "updated" and len(d["bio"]) == 1 and d["bio"][0]["value"] == "B")

# 3. single: a confirmed claim is never auto-overwritten; conflict is recorded
d2, conf2 = entity(), []
kb.upsert_claim(d2, "bio", "keep", "manual", mode="single", conflicts=conf2, confirmed=True)
r = kb.upsert_claim(d2, "bio", "overwrite", "manual", mode="single", conflicts=conf2)
check("single: confirmed claim protected -> conflict, value kept, logged",
      r == "conflict" and d2["bio"][0]["value"] == "keep" and len(conf2) == 1)

# 4. multi: dedup on (value, source); a new value from any source is retained dissent
d3, conf3 = entity(), []
kb.upsert_claim(d3, "geo.coordinates", {"lat": 1, "lon": 2}, "pleiades", mode="multi", conflicts=conf3)
r1 = kb.upsert_claim(d3, "geo.coordinates", {"lat": 1, "lon": 2}, "pleiades", mode="multi", conflicts=conf3)
r2 = kb.upsert_claim(d3, "geo.coordinates", {"lat": 9, "lon": 9}, "wikidata", mode="multi", conflicts=conf3)
check("multi: identical (value, source) -> unchanged", r1 == "unchanged")
check("multi: new value -> appended (dissent retained)",
      r2 == "added" and len(d3["geo"]["coordinates"]) == 2)

# 5. appearances dedupe by ref
d4 = entity()
a1 = kb.add_appearance(d4, "mishnah", "shekalim 4:2")
a2 = kb.add_appearance(d4, "mishnah", "shekalim 4:2")
check("appearance: deduped by ref",
      a1 is True and a2 is False and len(d4["appearances"]["mishnah"]) == 1)

# 6. external ids are idempotent
d5 = entity()
s1 = kb.set_external_id(d5, "wikidata_qid", "Q1")
s2 = kb.set_external_id(d5, "wikidata_qid", "Q1")
check("external_id: idempotent", s1 is True and s2 is False)

print()
if _failed:
    print(f"\033[31m✗ {len(_failed)} check(s) failed.\033[0m")
    sys.exit(1)
print("\033[32m✓ all checks passed.\033[0m")
