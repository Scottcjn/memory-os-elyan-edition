# Memory OS — rulebook.md additions

> **Version 1** — append these sections to `~/.hermes/rulebook.md`.

The marker `## Memory OS Additions — v1 (do not duplicate)` at the top of
each block is an idempotency guard. Before appending, check whether this
exact line already exists in your rulebook. If it does, skip that block.

---

## Memory OS Additions — v1 (do not duplicate)

## Memory Architecture

The agent has 6 layers of persistent memory, each with a distinct purpose:

| Layer | Tool | What it stores |
|---|---|---|
| Session | `session_search` | Past conversations (FTS5 over SQLite) |
| Persistent | `memory` | MEMORY.md (volatile learnings) + USER.md (who the user is) |
| Structured | `fact_store` | Durable facts with entity resolution (SQLite + HRR) |
| Cross-agent | `fabric_*` | Session archive with structured summaries |
| Procedural | `skill_view` / `skill_manage` | Reusable workflows |
| Vector | Qdrant `knowledge_base` (4096d / Cosine) | Semantic search over sessions and wiki content |

**Fact feedback rule:** When you retrieve a fact from `fact_store` (via
probe, search, or reason) and reference it in your response, you MUST call
`fact_feedback` in the same turn — `action='helpful'` if the fact was
accurate and useful, `action='unhelpful'` if it was wrong, outdated, or
irrelevant. This is not optional. The trust scoring system depends on it.
Without feedback, `trust_score` is ornamental and fact quality degrades
silently.

## Memory OS Additions — v1 (do not duplicate)

## Memory Operating System (Memory OS)

Your memory infrastructure runs locally via Docker:
- **Qdrant** (vector database, hybrid search: dense 4096d + BM25 sparse)
- **Redis** (ARQ job queue for async embedding/indexing)
- **ARQ Worker** (embedding pipeline, ingestion, decay scanning)

These services are defined in the Memory OS docker-compose stack.

## Memory OS Additions — v1 (do not duplicate)

## Mandatory Verifications

Before reporting a fact as true, verify against:
1. **Runtime evidence** — terminal output, file existence, process status
2. **Injected memory** — `[qdrant]`, `[fabric]`, `[sessions]`, `[facts]` in your prompt
3. **Documentation** — man pages, official docs for installed version
4. **Training knowledge** — never cite without verifying against 1-3
