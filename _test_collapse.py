"""Test non-bijunctive recall collapse (Elyan Edition)."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from icarus.collapse import tokenize, salience, collapse, DEFAULTS

all_ok = True


def check(name, cond):
    global all_ok
    if not cond:
        print(f"FAIL: {name}")
        all_ok = False


# ── tokenize ──
check("tokenize strips stopwords", tokenize("the quick brown fox") == {"quick", "brown", "fox"})
check("tokenize empty -> empty set", tokenize("") == set())
check("tokenize lowercases", tokenize("RustChain POWER8") == {"rustchain", "power8"})

# ── salience monotonic with overlap ──
q = tokenize("rustchain ed25519 attestation signature")
hi = salience({"text": "rustchain ed25519 attestation signature node", "source": "facts"}, q)
lo = salience({"text": "unrelated gardening tomatoes weather", "source": "facts"}, q)
check("salience rewards overlap", hi > lo)

# qdrant score lifts a candidate with no overlap above a zero-score one
sc_hi = salience({"text": "zzz none", "source": "qdrant", "score": 0.9}, q)
sc_lo = salience({"text": "zzz none", "source": "qdrant", "score": 0.1}, q)
check("salience rewards score", sc_hi > sc_lo)

# rank decay: later rank => lower salience, all else equal
r0 = salience({"text": "rustchain ed25519", "source": "fabric", "rank": 0}, q)
r3 = salience({"text": "rustchain ed25519", "source": "fabric", "rank": 3}, q)
check("rank decay lowers later ranks", r0 > r3)

# ── collapse: prune weak relative to strong ──
cands = [
    {"key": "strong", "source": "facts", "text": "rustchain ed25519 attestation signature verified node", "rank": 0},
    {"key": "mid", "source": "sessions", "text": "rustchain notes about something", "rank": 0},
    {"key": "weak", "source": "qdrant", "text": "completely unrelated gardening tomatoes", "score": 0.0, "rank": 0},
]
out = collapse(cands, q, budget=6, prune_ratio=0.35)
keys = [c["key"] for c in out]
check("strong survives", "strong" in keys)
check("weak pruned relative to strong", "weak" not in keys)
check("survivors carry _salience", all("_salience" in c for c in out))
check("survivors sorted strongest-first", out == sorted(out, key=lambda c: c["_salience"], reverse=True))

# ── collapse: budget cap ──
many = [
    {"key": f"k{i}", "source": "facts", "text": f"rustchain ed25519 attestation node {i}", "rank": 0}
    for i in range(20)
]
out2 = collapse(many, q, budget=4)
check("budget caps survivors", len(out2) <= 4)

# ── collapse: near-duplicate suppression ──
dups = [
    {"key": "a", "source": "facts", "text": "rustchain ed25519 attestation signature verified", "rank": 0},
    {"key": "b", "source": "qdrant", "text": "rustchain ed25519 attestation signature verified", "score": 0.9, "rank": 0},
    {"key": "c", "source": "sessions", "text": "totally different power8 numa coffer topic entirely", "rank": 0},
]
out3 = collapse(dups, tokenize("rustchain ed25519 attestation signature power8 numa"), budget=6, dup_overlap=0.82)
ids = [c["key"] for c in out3]
check("near-duplicate suppressed (a or b, not both)", not ("a" in ids and "b" in ids))

# ── edge cases ──
check("empty input -> []", collapse([], q) == [])
check("zero budget -> []", collapse(cands, q, budget=0) == [])
mixed = collapse([None, "x", 42, {"key": "ok", "source": "facts", "text": "rustchain ed25519 attestation"}], q)
check("non-dict items ignored (only the dict survives)", [c["key"] for c in mixed] == ["ok"])

# no query tokens: must NOT collapse to empty when there was real signal
out4 = collapse(cands, set(), budget=2)
check("empty query still returns survivors (no firehose, no blackout)", 0 < len(out4) <= 2)

# DEFAULTS sanity
check("DEFAULTS present", {"budget", "prune_ratio", "dup_overlap"} <= set(DEFAULTS))

# ── adapter tests: hooks._apply_collapse (the hot-path wiring) ──
# Silence the fail-open WARNING+traceback that the intentional malformed-input
# test below triggers by design — keeps test output clean.
import logging as _logging
_logging.disable(_logging.CRITICAL)
from icarus import hooks as _hooks

# strong fabric + relevant session survive; irrelevant zero-score qdrant pruned
af, aq, asn, afc = _hooks._apply_collapse(
    "rustchain ed25519 attestation signature",
    [{"id": "f1", "summary": "rustchain ed25519 attestation signature verified"}],
    [{"id": "q1", "title": "gardening", "content_preview": "tomatoes weather unrelated", "score": 0.0}],
    [{"session_id": "s1", "title": "rustchain", "snippet": "ed25519 attestation work"}],
    ["power8 numa coffer unrelated topic"],
)
check("adapter: strong fabric survives", [e["id"] for e in af] == ["f1"])
check("adapter: weak zero-score qdrant pruned", aq == [])
check("adapter: returns four lists", all(isinstance(x, list) for x in (af, aq, asn, afc)))

# qdrant text now reads `content`/`body`, not just title+preview (Codex fix)
qtxt = _hooks._qdrant_text({"content": "rustchain ed25519 attestation node verified"})
check("adapter: _qdrant_text reads content field", "ed25519" in qtxt)

# fail-open: malformed inputs must return unchanged tuple, never raise
bad = _hooks._apply_collapse("q", [{"no": "text"}], [None], [], [])
check("adapter: fail-open returns 4-tuple", len(bad) == 4)

# safe env parser: garbage value falls back to default, never raises
check("adapter: _env_num bad value -> default", _hooks._env_num("X_NOPE_BAD", 6, int) == 6)

if all_ok:
    print("=== ALL COLLAPSE TESTS PASS ===")
    sys.exit(0)
else:
    print("=== COLLAPSE TESTS FAILED ===")
    sys.exit(1)
