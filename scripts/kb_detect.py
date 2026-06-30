"""Detection engine for the entities KB: the resolution logic that classifies a
detected mention as known / rejected / ambiguous / new, against the existing
entities + the durable rejections and disambiguation rules.

This module is pure and importable (no I/O, no network). The CLI kb-detect.py
walks the corpus and feeds mentions through a Resolver; kb-promote.py applies the
human's decisions. See docs/entities-detection.md.
"""

import re

# --- Hebrew normalization (mirrors verify.py / kb-enrich) -------------------
_FINAL_TO_REGULAR = str.maketrans("ךםןףץ", "כמנפצ")
_REGULAR_TO_FINAL = str.maketrans("כמנפצ", "ךםןףץ")
_PREFIXES = set("הובכלמש")


def strip_nikkud(text):
    return re.sub(r"[֑-ׇ]", "", text)


def _normalize_final(word):
    if len(word) <= 1:
        return word
    return word[:-1].translate(_FINAL_TO_REGULAR) + word[-1].translate(_REGULAR_TO_FINAL)


def normalize_word(word):
    word = strip_nikkud(word).strip(".:,;?!-–—'\"״׳*")
    word = word.replace("וו", "ו").replace("יי", "ה")
    return _normalize_final(word)


def normalize_form(text):
    """Normalize a possibly multi-word surface form to a canonical key."""
    return " ".join(w for w in (normalize_word(x) for x in text.split()) if w)


def _deprefix(norm):
    """Drop a single attached prefix letter from the first word (definite article
    etc.), so הַחִטִּים resolves to חטים. Returns the alternative or None."""
    if not norm:
        return None
    head, sep, rest = norm.partition(" ")
    if len(head) > 1 and head[0] in _PREFIXES:
        return (head[1:] + sep + rest) if sep else head[1:]
    return None


_SCOPE_RANK = {"mishna": 2, "masechet": 1, "global": 0}


def masechet_of(ref):
    return ref.split(" ", 1)[0] if ref else None


class Resolver:
    """Classifies mentions against the KB, rejections, and rules. Stateless per
    call; the run-level 'seen this entity earlier' accumulation lives in the CLI.
    """

    def __init__(self, entities, rejections=(), rules=()):
        # entities: iterable of {"kind","slug","forms":[raw,...]}
        self.index = {}  # (kind, norm_form) -> set(slug)
        for e in entities:
            for f in e.get("forms", []):
                nf = normalize_form(f)
                if nf:
                    self.index.setdefault((e["kind"], nf), set()).add(e["slug"])
        self.rejections = list(rejections)
        self.rules = list(rules)

    # -- lookups ------------------------------------------------------------
    def _candidates(self, kind, norm):
        for key in (norm, _deprefix(norm)):
            if key and (kind, key) in self.index:
                return sorted(self.index[(kind, key)])
        return []

    def _rejected(self, kind, norm, ref):
        for r in self.rejections:
            if normalize_form(r["form"]) != norm or r.get("kind", kind) != kind:
                continue
            scope = r.get("scope", "mishna")
            if scope == "global":
                return True
            if scope == "mishna" and r.get("ref") == ref:
                return True
        return False

    def _rule(self, kind, norm, ref):
        masechet = masechet_of(ref)
        best, best_rank = None, -1
        for ru in self.rules:
            if normalize_form(ru["form"]) != norm or ru.get("kind", kind) != kind:
                continue
            scope = ru.get("scope", "global")
            if scope == "mishna" and ru.get("ref") != ref:
                continue
            if scope == "masechet" and ru.get("masechet") != masechet:
                continue
            if _SCOPE_RANK[scope] > best_rank:
                best, best_rank = ru["resolve"], _SCOPE_RANK[scope]
        return best

    # -- the one entry point ------------------------------------------------
    def resolve(self, form, kind, ref):
        """Return a dict with 'status' in known|rejected|ambiguous|new."""
        norm = normalize_form(form)
        if not norm:
            return {"status": "new", "norm": norm}
        if self._rejected(kind, norm, ref):
            return {"status": "rejected", "norm": norm}
        cands = self._candidates(kind, norm)
        if len(cands) == 1:
            return {"status": "known", "slug": cands[0], "norm": norm}
        if len(cands) > 1:
            ruled = self._rule(kind, norm, ref)
            if ruled:
                return {"status": "known", "slug": ruled, "norm": norm, "via": "rule"}
            return {"status": "ambiguous", "candidates": cands, "norm": norm}
        return {"status": "new", "norm": norm}
