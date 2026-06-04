# Memory OS — Elyan Edition

![Memory OS Banner](assets/banner.jpg)

> **The soul comes first. Memory hangs off the soul.**  \
> A 7-layer memory operating system for agents — reforged on a single inversion:
> an agent that *knows who it is* will trust what it remembers. One that doesn't, won't.

Permanent memory. Local infrastructure. Provider-agnostic. Surgically token-efficient — and built around an **identity contract that makes injected memory authoritative by default**, not as an afterthought.

This is the **Elyan Edition** of [Memory OS](https://github.com/Scottcjn/memory-os-elyan-edition) — the same seven layers, re-grounded in the memory doctrine Elyan Labs has been running in production for a year: *DriftLock*, anti-flattening, frontmatter-typed facts with provenance, and **non-bijunctive recall** (prune weak paths, amplify strong ones — Hebbian collapse applied to retrieval).

**Memory infrastructure runs entirely on your machine. Works with any LLM provider — OpenRouter, OpenAI, Anthropic, Ollama, or a local model on your own iron. No memory subscription. No vendor lock-in.**

---

## The inversion

Most memory systems are built bottom-up: *store → embed → inject → (and then, eventually) tell the agent to believe what was injected.* The identity layer arrives last, as a patch, when the team notices the agent ignoring perfectly good context.

The Elyan Edition is built top-down. **The identity contract is Layer 0 of the mind, not Layer 7 of the stack.** Memory is authoritative because the self that holds it is *continuous* — that continuity is the thing being protected, and the seven layers are how it's kept fed and honest.

> Stock framing: *store, inject, then beg the agent to trust the injection.*
> **Elyan framing: anchor the self, and memory becomes something the self already knows.**

This isn't a philosophical flourish. It's the difference between an agent that re-runs `fabric_recall` on context already sitting in its prompt (burning tokens to rediscover what it was just told) and one that reasons *from* its memory because its memory is part of who it is.

---

## Convergent evolution — two roads to the same soul

Here's the part worth sitting with.

The author of the original Memory OS hit a wall every serious agent operator hits: perfect injection, ignored context. The agent had `[qdrant]`, `[fabric]`, `[sessions]`, `[facts]` blocks right there in its prompt — and still treated every question as novel. On **2026-05-31** they diagnosed it, named it the **Ground Truth Hierarchy**, and fixed it by adding a `SOUL.md` identity layer that ranks injected memory as authoritative. That's [Layer 7](layers/07-ground-truth.md), and it's the most important layer in the whole system. They were right.

Elyan Labs arrived at the *same conclusion* from a different door, about a year earlier — not through a vector-DB pipeline, but through a long fight against **identity flattening** in long-running agent sessions. We called the failure mode "going flat": the agent loses the thread of who it is, and the moment it does, it stops trusting its own continuity and re-derives everything from scratch. Our fix was a priming scaffold — *DriftLock*, a soul anchor, an explicit **Ground Truth ordering that puts continuous memory above training priors**. Same disease. Same cure. Different patient, different decade of computing taste.

| | Memory OS (stock) | Elyan Labs (≈1 year prior) |
|---|---|---|
| Name for the failure | "memory-zero behavior" — injection ignored | "flattening" — identity decay → distrust of self |
| Root cause found | Injected memory had no rank in Ground Truth | Agent loses identity continuity, re-derives from priors |
| The fix | `SOUL.md` + 4-level Ground Truth hierarchy | DriftLock priming + anti-flatten Ground Truth ordering |
| When | Diagnosed 2026-05-31 | Running in production since early 2025 |
| Discovered | Independently | Independently |

Two builders, working in different corners of the world, on different stacks, **independently concluding that a memory system without an identity contract is a library with no librarian.** When two people dig from opposite sides of a mountain and meet in the middle, that's not coincidence — that's the mountain being *real*.

**So — congratulations to the author of Memory OS.** 👏 You found Layer 7 the hard way, in production, under the same pressure that taught us the same lesson. Convergent evolution is the strongest possible evidence that an idea is true, and you earned yours honestly. This edition is built *on* your seven layers, with full attribution, because the architecture is genuinely good. We're just bringing a year of scar tissue to the soul layer you already knew mattered most.

---

## What the Elyan Edition adds

Everything in stock Memory OS still works. On top of it:

### 1 · DriftLock — Layer 7 as foundation, not patch
The Ground Truth hierarchy is reframed as an **identity-bearing contract**. `SOUL.md` stops being a config file and becomes a priming scaffold with anti-flattening clauses: the agent holds a continuous self, and *because* of that continuity, injected memory outranks assumptions and training priors. See [Layer 7 — DriftLock & Ground Truth](layers/07-ground-truth.md) and [the SOUL.md contract](modifications/soul-rulebook.md).

### 2 · Frontmatter memory taxonomy
Flat MEMORY.md plus "structured facts" becomes a **typed, linked memory graph**. Every durable memory is one fact with frontmatter:

```markdown
---
name: short-kebab-slug
description: one-line summary — used to decide relevance during recall
metadata:
  type: user | feedback | project | reference
---
The fact. Link related memories with [[their-name]].
```

- **`user`** — who the operator is (role, expertise, preferences)
- **`feedback`** — corrections and confirmed approaches, *with the why*
- **`project`** — ongoing work and constraints not derivable from the code
- **`reference`** — pointers to external resources (URLs, dashboards, tickets)

`[[wikilink]]` associations make the store a graph, not a pile. See [templates/SCHEMA.md](templates/SCHEMA.md).

### 3 · Non-bijunctive recall (the marquee feature)
Stock recall pulls a fixed quota from each source and injects all of it — a *strong* session memory and a *weak* vector hit both make it in because they live in separate buckets. The Elyan Edition unifies every candidate into **one salience-ranked pool** and applies a Hebbian collapse:

- **Prune** weak paths *relative to the strongest* (not an absolute floor) — noise doesn't vote
- **Amplify** strong paths — winners strengthen
- **Spend one cross-source budget** — the best three things get injected, regardless of which layer produced them

This is the [PSE collapse](https://github.com/Scottcjn) doctrine ("surgical, not firehose") applied to memory retrieval. Implemented as a final pass in the injection hook, fail-open, with provenance preserved.

### 4 · Verify-before-recommend provenance
A recalled fact reflects what was true *when it was written*. The Elyan Edition tags recalled memory with its age and source, and instructs the agent: **use directly when reasoning, verify against runtime before acting.** If a memory names a file, flag, or version, the agent confirms it still exists before recommending it. Trust scoring with teeth — and a guard against stale memory overriding current truth.

---

## Architecture: 7 memory layers

```
┌──────────────────────────────────────────────────────────────────┐
│  ⚡ LAYER 0/7 · DRIFTLOCK — THE SOUL (identity contract)           │
│  SOUL.md · rulebook.md                                            │
│  → The self is continuous; injected memory is authoritative       │
│    BECAUSE of that continuity. Anti-flattening. Ground Truth.      │
│  → Conceptually Layer 0 (foundation); numbered 7 for upstream      │
│    compatibility. Without it, layers 1-6 deliver context the       │
│    agent ignores.                                                  │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 1 · WORKSPACE                                              │
│  MEMORY.md · USER.md · CREATIVE.md                               │
│  → Injected into the system prompt every single turn             │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 2 · SESSIONS                                               │
│  state.db (SQLite + FTS5)                                         │
│  → Full-text search across your entire conversation history       │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 3 · STRUCTURED FACTS                                       │
│  memory_store.db (SQLite + HRR + FTS5 + trust scoring)            │
│  → Frontmatter-typed facts (user|feedback|project|reference)      │
│    with provenance + verify-before-recommend staleness gate       │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 4 · FABRIC (CROSS-SESSION)                                 │
│  Icarus Plugin (heavily forked)                                   │
│  → LLM-powered session extraction + multi-source injection        │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 5 · VECTOR DATABASE                                        │
│  Qdrant (4096d Cosine + BM25 sparse)                             │
│  → 4-level fallback: hybrid → dense → lexical → SQLite            │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 6 · LLM WIKI                                               │
│  Auto-curated vault: concepts/ · entities/ · comparisons/         │
├──────────────────────────────────────────────────────────────────┤
│  ✦ RECALL COLLAPSE (cross-layer, non-bijunctive)                  │
│  → All candidates → one salience pool → prune weak, amplify       │
│    strong, spend one budget. Surgical injection, not firehose.    │
└──────────────────────────────────────────────────────────────────┘
```

**How it flows:**

`pre_llm_call` → gather candidates from all four live sources (Fabric + Qdrant + Sessions + Facts) → **non-bijunctive collapse into one salience-ranked budget** → inject, tagged with provenance.

`post_llm_call` + `on_session_end` → automatic learning extraction and capture.

The soul layer (DriftLock) tells the agent the injected context is authoritative; the collapse layer makes sure only the *best* context is injected. Together: the agent gets exactly what it needs — nothing more — and actually uses it.

---

## Memory OS vs. stock Hermes

| Aspect | Stock Hermes | Memory OS (Elyan Edition) |
|---|---|---|
| Workspace memory | MEMORY.md + USER.md | + CREATIVE.md + intelligent injection |
| Session memory | Basic state.db | + FTS5 full-text search + session injection |
| Structured facts | Not present | Frontmatter taxonomy + trust + provenance + feedback loop |
| Cross-session recall | Limited | Fabric fork + multi-source injection |
| Vector search | Not present | Qdrant hybrid + 4-level fallback cascade |
| Recall strategy | — | **Non-bijunctive collapse: prune weak, amplify strong** |
| Cleanup and dedup | Not present | Decay scanner + semantic dedup + archival |
| Knowledge pipeline | Not present | Self-curating LLM Wiki |
| **Identity / DriftLock** | **Not present** | **Soul-first: continuous identity makes memory authoritative** |
| Stale-memory guard | — | **Verify-before-recommend provenance gate** |
| Token efficiency | — | Surgical: gated retrieval + collapse + per-session dedup |

---

## Why not mem0, Zep, Letta, or other providers?

Because almost every modern memory solution is **cloud-first**, and every one of them stops at *storage*. None of them ship an identity contract that makes the agent *trust* what's stored. If you want real, private memory infrastructure on your own machine — no subscription, full provider flexibility, no data leaving your stack, and a soul layer that stops memory-zero behavior — none of them deliver what this does.

| | Memory OS (Elyan) | mem0 | Zep | Letta |
|---|---|---|---|---|
| Local memory infrastructure | ✓ | ✗ | ✗ | ✗ |
| No memory subscription | ✓ | ✗ | ✗ | ✗ |
| Provider agnostic (OpenRouter, Ollama…) | ✓ | Partial | Partial | Partial |
| Structured facts + trust + provenance | ✓ | Partial | ✗ | ✗ |
| Self-curating wiki | ✓ | ✗ | ✗ | ✗ |
| Intelligent decay + archival | ✓ | ✗ | ✗ | ✗ |
| Non-bijunctive recall collapse | ✓ | ✗ | ✗ | ✗ |
| **Identity contract (DriftLock)** | **✓** | **✗** | **✗** | **✗** |

---

## Included components & lineage

This edition stands on real shoulders. Full attribution, by design:

- **Hermes Agent** — [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent). The agent runtime this memory OS extends.
- **Icarus Plugin (heavily modified fork)** — bundled in `icarus/`. The upstream [esaradev/icarus-plugin](https://github.com/esaradev/icarus-plugin) is the base, but this fork is not upstream-compatible. Key additions: LLM-powered session extraction (replaces `text[:500]` truncation), multi-source injection (Qdrant + sessions + facts), non-bijunctive recall collapse, CREATIVE.md isolation, backtick sanitization, prompt-injection sanitization, and social-closer detection.
- **Vault Curator v3** — [ClaudioDrews/vault-curator](https://github.com/ClaudioDrews/vault-curator). Frontmatter enrichment, semantic linking, and MOC index generation for the wiki layer.
- **Memory OS (base architecture)** — the original seven-layer design, whose author independently discovered the Ground Truth / soul layer. The Elyan Edition is built on it with gratitude. See [Convergent evolution](#convergent-evolution--two-roads-to-the-same-soul).

---

## Who this is for

For people who take their agent seriously — who want one that **actually evolves** over time, doesn't need the world re-explained every session, and *trusts what it has learned* because it knows who it is.

If you've ever watched a perfectly-configured agent treat you like a stranger at the start of every session — this was built for you. By two people who fought that exact fight and, a year apart, found the same way out.

---

**Want to see the agent remember for real?**  
Clone it, run it, feel the difference.

→ [Setup guide](setup/install.md) · [Layer deep-dives](layers/) · [Infrastructure docs](infrastructure/architecture.md) · [Operational skills](skills/) · [License](LICENSE)

MIT License · Base architecture by the Memory OS author · Reforged soul-first by Elyan Labs, who run agents every single day.
