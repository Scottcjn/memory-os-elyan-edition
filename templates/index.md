# Memory Indexes

This file documents two indexes:

- **`MEMORY.md`** — the workspace fact index (Elyan taxonomy). One line per
  durable fact, loaded into context every session. The index is small; the
  facts it points to hold the detail.
- **Knowledge Wiki** — the Map of Content for the auto-curated wiki layer.

---

## `MEMORY.md` — workspace fact index template

`MEMORY.md` is the lightweight index of the [memory fact store](SCHEMA.md#memory-fact-schema-elyan-taxonomy).
Keep each entry to **one line under ~200 chars** — a title, a link, and a hook.
Put detail in the fact file, never here. Group by type so recall stays scannable.

```markdown
# Memory — Concise Index

## User Profile
- [Operator Background](user-background.md) — SCADA + IT tech; wants explicit, grounded answers.

## Feedback (Behavioral Directives)
- [Careful Engineering](feedback-careful-engineering.md) — re-read before/after edits; phases ≤5 files.
- [Verify Before Recommend](feedback-verify-before-recommend.md) — memory is a timestamp, not a live probe.

## Projects
- [Auth → Ed25519](project-auth-ed25519.md) — node verifies pipe-string, not JSON; OPEN.

## Reference
- [Dashboards & Tickets](reference-links.md) — explorer, bounty queue, status board.
```

**Maintenance rules:**
- One line per fact. If `MEMORY.md` grows past a few hundred lines, the entries
  are too long — move detail into the fact files.
- Before adding a fact, check for an existing file that already covers it;
  update rather than duplicate. Delete facts that turn out to be wrong.
- A `[[wikilink]]` in a fact body that doesn't resolve yet is fine — it marks a
  fact worth writing later, not an error.

---

# Knowledge Wiki

> Map of Content — curated knowledge base for the Memory OS agent.

```yaml
---
title: "Wiki Index"
type: meta
last_updated: YYYY-MM-DD
total_pages: 0
---
```

## Concepts

Abstract patterns, ideas, and recurring themes.

- _Add wiki links here as concepts are created_

## Entities

Concrete things: tools, models, projects, people.

- _Add wiki links here as entities are created_

## Comparisons

Side-by-side analyses of alternatives.

- _Add wiki links here as comparisons are created_

## Recent Additions

| Date | Title | Type |
|------|-------|------|
| | | |

---

## Raw Sources

Source documents that feed the wiki pipeline:

```
raw/
├── external/    # Third-party articles, docs, specs
├── notes/       # Personal notes and observations
└── research/    # Research papers and investigations
```
