"""Non-bijunctive recall collapse — Elyan Edition.

Stock recall pulls a fixed quota from each memory source (fabric, qdrant,
sessions, facts) and injects all of it. A *strong* session memory and a *weak*
vector hit both survive because they live in separate per-source buckets.

This module unifies every candidate into one salience-ranked pool and applies a
Hebbian-style collapse borrowed (in structure only) from the PSE doctrine:

  - PRUNE   weak paths *relative to the strongest* (not an absolute floor) —
            noise doesn't vote.
  - AMPLIFY strong paths — the highest-salience candidates fill the budget,
            and near-duplicates of a survivor are suppressed.
  - BUDGET  spend ONE cross-source budget — the best N things get injected,
            regardless of which layer produced them.

The function is pure (no I/O, no globals) and fail-open by contract at the call
site: callers should treat any exception as "inject everything, unchanged."

Tunables are passed explicitly so the caller can wire them to env vars and so
the behavior is fully deterministic for tests.
"""

from __future__ import annotations

import re
from typing import Iterable

__all__ = ["tokenize", "salience", "collapse", "DEFAULTS"]

# Mild per-source priors. Curated/durable sources get a small nudge; this only
# breaks ties between candidates of otherwise-equal salience. Kept close to 1.0
# on purpose — query relevance should dominate, not source identity.
_SOURCE_PRIOR = {
    "facts": 1.10,     # durable, hand-curated facts about the world
    "fabric": 1.05,    # cross-session decisions/resolutions
    "sessions": 1.00,  # prior conversation snippets
    "qdrant": 1.00,    # vector knowledge base
}

DEFAULTS = {
    "budget": 6,           # max candidates injected across ALL sources
    "prune_ratio": 0.35,   # keep candidates with salience >= ratio * max_salience
    "dup_overlap": 0.82,   # token-overlap above this vs a kept survivor => drop
    "overlap_weight": 0.55,  # weight of query-overlap vs base score in salience
    "rank_decay": 0.85,    # geometric decay applied per within-source rank
}

_STOPWORDS = frozenset(
    "the a an is was are to of in for on with it and or not i you can do this "
    "that what how please help me my your we our they them then than over such "
    "be been being have has had will would could should about into only also "
    "just like very from at as by if".split()
)


def tokenize(text: str) -> set:
    """Lowercase alphanumeric tokens, minus stopwords. Pure and deterministic."""
    if not text:
        return set()
    words = set(re.findall(r"[a-z0-9]+", str(text).lower()))
    return words - _STOPWORDS


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def salience(candidate: dict, query_tokens: set, *,
             overlap_weight: float = DEFAULTS["overlap_weight"],
             rank_decay: float = DEFAULTS["rank_decay"]) -> float:
    """Unified salience for one candidate, in [0, ~1.2].

    Combines:
      - query-token overlap (universal — every source has text)
      - base score (qdrant cosine when present; neutral prior otherwise)
      - within-source rank decay (earlier == stronger)
      - a mild per-source prior (tie-breaker only)

    A candidate dict may carry: ``text`` (str), ``score`` (float|None),
    ``rank`` (int, 0-based within its source), ``source`` (str).
    """
    text_tokens = tokenize(candidate.get("text", ""))
    if query_tokens:
        overlap = len(query_tokens & text_tokens) / len(query_tokens)
    else:
        overlap = 0.0

    score = candidate.get("score")
    base = _clamp01(float(score)) if score is not None else 0.6

    sw = _clamp01(overlap_weight)
    blended = sw * overlap + (1.0 - sw) * base

    rank = int(candidate.get("rank", 0) or 0)
    decay = rank_decay ** max(rank, 0)

    prior = _SOURCE_PRIOR.get(candidate.get("source", ""), 1.0)
    return blended * decay * prior


def collapse(candidates: Iterable[dict], query_tokens: set, *,
             budget: int = DEFAULTS["budget"],
             prune_ratio: float = DEFAULTS["prune_ratio"],
             dup_overlap: float = DEFAULTS["dup_overlap"],
             overlap_weight: float = DEFAULTS["overlap_weight"],
             rank_decay: float = DEFAULTS["rank_decay"]) -> list:
    """Collapse a unified candidate pool to a salience-ranked survivor list.

    Returns the surviving candidate dicts, strongest first, each annotated with
    a ``_salience`` float. Length <= ``budget``.

    Non-bijunctive: weak paths are pruned relative to the strongest survivor,
    not against an absolute threshold — so a session with three mediocre hits
    and one excellent one keeps only the excellent one, while a session of four
    strong hits keeps all four (up to budget).

    Empty input or non-positive budget returns ``[]``. Pure function.
    """
    pool = [c for c in candidates if isinstance(c, dict)]
    if not pool or budget <= 0:
        return []

    scored = []
    for c in pool:
        s = salience(c, query_tokens,
                     overlap_weight=overlap_weight, rank_decay=rank_decay)
        scored.append((s, c))

    max_s = max((s for s, _ in scored), default=0.0)

    # PRUNE: relative floor. When max_s is 0 (no overlap, no scores) the floor is
    # 0 and nothing is pruned here — budget + rank ordering still bound the output
    # so we never inject a firehose, and we never collapse to empty when there
    # was real signal.
    floor = max_s * prune_ratio
    kept = [(s, c) for s, c in scored if s >= floor]

    # AMPLIFY: strongest first. Stable on insertion order for equal salience.
    kept.sort(key=lambda sc: sc[0], reverse=True)

    # Near-duplicate suppression: if a candidate's text overlaps an already-kept
    # survivor above dup_overlap, the weaker one is redundant — drop it. This is
    # the cross-source version of "don't say the same thing twice."
    survivors: list = []
    survivor_tokens: list = []
    for s, c in kept:
        if len(survivors) >= budget:
            break
        ctoks = tokenize(c.get("text", ""))
        is_dup = False
        for stoks in survivor_tokens:
            denom = min(len(ctoks), len(stoks)) or 1
            if ctoks and len(ctoks & stoks) / denom >= dup_overlap:
                is_dup = True
                break
        if is_dup:
            continue
        annotated = dict(c)
        annotated["_salience"] = round(s, 4)
        survivors.append(annotated)
        survivor_tokens.append(ctoks)

    return survivors
