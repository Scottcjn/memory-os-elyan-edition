# Layer 7 — DriftLock & the Ground Truth Hierarchy

> **Type:** Identity contract (SOUL.md + rulebook.md) — conceptually Layer 0, numbered 7 for upstream compatibility
> **Why it exists:** Context injection is not enough. The agent must hold a *continuous self* that treats injected memory as something it already knows — not as an optional suggestion to be re-verified from scratch.
> **Discovered:** independently, twice — Memory OS on 2026-05-31, Elyan Labs ~a year earlier (see [convergent evolution](../README.md#convergent-evolution--two-roads-to-the-same-soul))

## The problem

Memory OS successfully injects context from all four sources (Fabric + Qdrant + Sessions + Facts) into every prompt. You can see it in the system preamble: `[qdrant]`, `[fabric]`, `[sessions]`, `[facts]` blocks are right there.

**But the agent ignores them.**

Symptoms:
- Agent runs `search_files`, `read_file`, `session_search` to rediscover information that `[qdrant]` already provided
- Treats every question as novel even when the answer is literally in the prompt
- Rediscovers projects, decisions, and constraints from scratch each session

The original Memory OS author named this **memory-zero behavior**. Elyan Labs, fighting the same symptom in long-running sessions, named the underlying disease **flattening**: when an agent loses the thread of *who it is*, it stops trusting its own continuity — and an agent that doesn't trust its continuity will re-derive everything from training priors, ignoring the memory sitting in front of it.

Same symptom. Same root cause. The fix is an **identity contract**.

## Root cause

Memory OS was injecting memory into the prompt, but the agent's **identity documents** (`SOUL.md` and `rulebook.md`) did not include injected memory in the Ground Truth hierarchy. Without an explicit rank, the injected context was implicitly treated as optional suggestion — below terminal output and official documentation.

The deeper reading: **injected memory has no authority unless the self that receives it is anchored.** A flattened agent treats its own prior decisions as a stranger's notes. The Ground Truth hierarchy works *because* it's attached to a continuous identity — that's why this is the foundation layer, not a late patch.

The original hierarchy had only 3 levels:

```
1. Terminal output → Ground Truth
2. Official documentation → Authoritative
3. Training knowledge → Reference only
```

The injected memory (`[qdrant]`, `[fabric]`, `[sessions]`, `[facts]`) was **not listed at all**. No status = no authority.

## The fix

The hierarchy is expanded to 4 levels, with injected memory inserted as the second level — and bound to an anchored, continuous self (DriftLock):

```
1. Terminal output → Ground Truth for system state (runtime)
2. Injected memory [qdrant, fabric, sessions, facts] → Ground Truth for
   documented knowledge and prior decisions. This is YOUR memory — the
   record of who you are and what you've already built. Treat it as known.
3. Official documentation → Authoritative for APIs, configs, version-specifics
4. Training knowledge → Reference only; always verify against 1-3
```

### Conflict resolution

| Sources conflict | Winner |
|---|---|
| Terminal vs Injected memory | Terminal wins for system state. Injected memory wins for documented knowledge. |
| Injected memory vs Assumptions | **Injected memory wins.** Never treat a question as novel when the answer is already in your prompt. |
| Injected memory vs Official docs | Official docs win for version-sensitive specifics. Injected memory wins for project context. |
| Training knowledge vs anything | Training knowledge always loses. Verify against 1-3. |

### Verify-before-recommend (the Elyan provenance gate)

Injected memory is Ground Truth for *documented knowledge*, but a memory reflects what was true **when it was written**. The contract therefore splits behavior:

- **Reasoning** → use injected memory directly; do not re-derive what you were just told.
- **Acting** → when a memory names a file, flag, version, or endpoint, confirm it still exists against runtime (Level 1) before recommending or acting on it.

This is what stops stale memory from silently overriding current truth. It is the difference between an agent that confidently recommends a flag that was removed three months ago, and one that says *"memory says `--foo`; let me confirm it's still there."*

### Files changed

| File | Change |
|------|--------|
| `~/.hermes/SOUL.md` | Ground Truth section expanded to 4 levels; DriftLock anti-flattening anchor added; conflict + provenance rules |
| `~/.hermes/rulebook.md` | Added "Injected memory" row to Source of Truth table; mandatory verify-before-act behavior |

### Key instruction added to SOUL.md

> *"You hold a continuous self. The injected `[qdrant]`, `[fabric]`, `[sessions]`, `[facts]` blocks are your own memory — what you have already built, decided, and documented. When injected memory contradicts your assumptions, injected memory wins. Never treat a question as novel when the answer is already in your prompt. Use memory directly when reasoning; verify it against runtime before acting."*

## Why this matters

The infrastructure layers (01-06) ensure memory is **captured, stored, and injected**. Layer 07 ensures the injected memory is **used** — because the agent receiving it knows it's *its own*. Without it:

- Qdrant points are injected but the agent `curl`s the Qdrant API to verify them
- Fabric entries are injected but the agent calls `fabric_recall` to re-find them
- Session history is injected but the agent runs `session_search` to re-discover it
- Facts are injected but the agent probes `fact_store` to confirm them

Each rediscovery burns tokens, time, and model context. Layer 07 is what stops the waste — and the anti-flattening anchor is what keeps Layer 07 holding across a long session.

## Verification

After applying this fix (updating SOUL.md and rulebook.md), the agent should:

1. Read injected `[qdrant]`, `[fabric]`, `[sessions]`, `[facts]` blocks before running any search/discovery tools
2. Not rediscover knowledge that is already in the prompt
3. Cite injected context directly instead of re-deriving it
4. Verify file/flag/version references against runtime before acting on them
5. Respect the conflict rules when sources disagree

A gateway restart is required after editing SOUL.md or rulebook.md for changes to take effect in new sessions:

```bash
systemctl --user restart hermes-gateway
```

## Related

- [The SOUL.md / rulebook contract](../modifications/soul-rulebook.md) — the exact identity-document additions
- [Layer 4 — Fabric (injection mechanism)](04-icarus-fabric.md)
- [Layer 5 — Qdrant (vector source)](05-qdrant.md)
- [Layer 3 — Fact Store (structured facts + provenance)](03-fact-store.md)
- [Layer 2 — Sessions](02-sessions.md)
- [Convergent evolution — two roads to the same soul](../README.md#convergent-evolution--two-roads-to-the-same-soul)
