# Schema Templates

This document defines two complementary structures:

1. **Memory Fact Schema** (Elyan taxonomy) — for durable, hand-written facts in
   the workspace memory store. One file = one fact, typed and linked.
2. **Wiki Schema** — for auto-curated knowledge pages under
   `wiki/{concepts,entities,comparisons}/`.

The fact store is *what the agent knows about its world*; the wiki is *what the
agent has researched and organized*. Both feed recall. Both use frontmatter and
`[[wikilink]]` associations so the memory store is a **graph, not a pile**.

---

## Memory Fact Schema (Elyan taxonomy)

Each durable memory is **one file holding one fact**, with frontmatter:

```yaml
---
name: short-kebab-case-slug
description: one-line summary — used to decide relevance during recall
metadata:
  type: user | feedback | project | reference
---
```

The body is the fact itself. For `feedback` and `project` types, follow the
fact with **`Why:`** and **`How to apply:`** lines. Link related memories with
`[[their-name]]` (the other memory's `name:` slug) — link liberally; a
`[[name]]` that doesn't resolve yet marks something worth writing later.

**The four types — choose by what the fact *is*, not where it came from:**

| Type | What it captures | Example |
|------|------------------|---------|
| `user` | Who the operator is — role, expertise, durable preferences | "Operator is a SCADA + IT tech; prefers explicit, grounded answers." |
| `feedback` | Corrections and confirmed approaches, **with the why** | "Re-read files before editing. **Why:** context decays mid-session." |
| `project` | Ongoing work, goals, constraints not derivable from the code | "Migrating auth to Ed25519; node verifies pipe-string, not JSON." |
| `reference` | Pointers to external resources (URLs, dashboards, tickets) | "Block explorer: https://… · Bounty queue: repo#12458" |

**What NOT to store as a fact:** anything the repo already records (code
structure, git history, past fixes, CONTRIBUTING docs) or anything that only
matters to the current conversation. If asked to remember one of those, ask what
was *non-obvious* about it and store that instead.

**The index.** Every fact gets a one-line pointer in `MEMORY.md`
(`- [Title](slug.md) — hook`). `MEMORY.md` is the lightweight index loaded each
session; the fact files hold the detail. See [index.md](index.md).

**Recall hygiene.** A recalled fact reflects what was true *when written*. If it
names a file, flag, or version, verify it still exists before recommending it —
see the [verify-before-recommend gate](../modifications/soul-rulebook.md).

---

## Wiki Schema Template

The rest of this document defines the structure for wiki pages in the knowledge
base. Each page under `wiki/{concepts,entities,comparisons}/` should follow this
structure.

## Frontmatter

```yaml
---
title: "Page Title"
type: concept          # concept | entity | comparison
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: raw/filename.md # link to source document
status: seedling       # seedling | growing | evergreen
aliases: [alt-name-1, alt-name-2]
---
```

**Field descriptions:**
- `type` — one of: `concept` (abstract pattern/idea), `entity` (concrete tool/project/person), `comparison` (side-by-side analysis)
- `status` — maturity indicator: `seedling` (new), `growing` (being refined), `evergreen` (stable reference)
- `source` — relative path to the raw source document that generated this page
- `aliases` — alternative names for cross-linking and search

## Body Structure

### For `concept` pages

```markdown
# Concept Name

## Summary

One-paragraph high-level overview of the concept.

## Description

Detailed explanation. Include:
- What problem this concept solves
- How it works at a high level
- Key principles or rules

## Examples

### Example 1: Descriptive title
```
code or configuration block
```
Brief explanation of what the example demonstrates.

### Example 2: Another example

## Related

- [[Related Concept 1]] — relationship description
- [[Related Concept 2]] — relationship description
```

### For `entity` pages

```markdown
# Entity Name

## Summary

What this thing is — one paragraph.

## Purpose

Why this entity exists in the system.

## Configuration

```yaml
# Example configuration block
key: value
option: setting
```

## Dependencies

- Dependency 1: what it provides
- Dependency 2: what it provides

## Usage Notes

Practical considerations, edge cases, known issues.

## Related

- [[Related Concept]] — relationship
```

### For `comparison` pages

```markdown
# Comparison: A vs B

## Summary

One-paragraph overview of what is being compared.

## Comparison Table

| Aspect | Option A | Option B |
|--------|----------|----------|
| Strengths | ... | ... |
| Weaknesses | ... | ... |
| Best for | ... | ... |

## Decision Factors

Considerations that favour one option over the other.

## Recommendation

Final recommendation with reasoning.

## Related

- [[Option A detail page]]
- [[Option B detail page]]
```
