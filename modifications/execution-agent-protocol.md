# Execution Agent Protocol — Memory OS Amendments

> Apply these amendments to `~/.hermes/rulebook.md` AFTER the Execution Agent
> protocol sections. Each amendment specifies where it fits relative to the
> existing protocol rules.
>
> **Idempotency:** Each block starts with `<!-- Memory OS amendment — do not duplicate -->`.
> Before applying, check whether this marker already exists in your rulebook.
> If it does, skip that block.

---

<!-- Memory OS amendment — do not duplicate -->

## Amendment: Memory Architecture Integration

**Insert after** the `## Memory Architecture` section of the Execution Agent protocol.

The 6-layer memory architecture (Session → Persistent → Structured → Cross-agent →
Procedural → Vector) is your operational memory. When the protocol instructs you
to verify before acting (`Ground Truth` rule), consult the appropriate layer:

- **"What did we decide about X?"** → `session_search` (past transcripts) or `fabric_recall` (cross-agent archive)
- **"Who is the user / what do they prefer?"** → Persistent memory (`memory` tool)
- **"What durable fact do we know about X?"** → `fact_store` (SQLite + HRR)
- **"What does the codebase / wiki say about X?"** → `qdrant_search` (vector, 4096d Cosine + BM25 sparse)
- **"How do I perform task Y?"** → `skill_view` / `skill_manage` (procedural)

When injected memory (labels `[qdrant]`, `[fabric]`, `[sessions]`, `[facts]`)
appears in your prompt: you already know this. Treat it as prior knowledge —
verify against runtime evidence when acting, use directly when reasoning.

**Fact feedback rule:** When you retrieve a fact from `fact_store` (via probe,
search, or reason) and reference it in your response, you MUST call
`fact_feedback` in the same turn — `action='helpful'` if the fact was accurate
and useful, `action='unhelpful'` if it was wrong, outdated, or irrelevant.
Without feedback, `trust_score` is ornamental and fact quality degrades silently.

---

<!-- Memory OS amendment — do not duplicate -->

## Amendment: Memory OS Infrastructure

**Insert after** the `## Defaults` section of the Execution Agent protocol.

Your memory infrastructure runs locally via Docker. These services are defined in
the Memory OS `docker-compose.yml`:

- **Qdrant** (`qdrant/qdrant:v1.17.1`) — vector database on `127.0.0.1:6333`.
  Hybrid search: dense 4096d (Cosine) + BM25 sparse. Collection: `knowledge_base`.
  Requires `QDRANT_API_KEY` environment variable for authentication.
- **Redis** (`redis:8.6.2`) — ARQ job queue on `127.0.0.1:6379`.
  Requires `REDIS_PASSWORD` (generate with `openssl rand -hex 16`).
- **ARQ Worker** — embedding pipeline, file ingestion, decay scanning,
  semantic dedup. Depends on Qdrant + Redis being healthy (`service_healthy`).

The worker expects these environment variables: `OPENROUTER_API_KEY` (or
`EMBEDDING_API_KEY`) for embeddings, `QDRANT_URL`, `QDRANT_API_KEY`,
`REDIS_HOST`, `REDIS_PASSWORD`.

---

<!-- Memory OS amendment — do not duplicate -->

## Amendment: Mandatory Verifications

**Insert after** the `## Ground Truth` section of the Execution Agent protocol.

Add a 5th level to the verification hierarchy:

```
5. Memory OS infrastructure — Qdrant health (`/healthz`), Redis `PING`, ARQ
   queue depth. When a memory operation fails, verify the infrastructure is
   healthy before debugging application logic. The worker container exposes
   port 8000 with a `/health` endpoint.
```

Before reporting infrastructure state as fact:
1. Verify Qdrant connectivity: `curl -s http://127.0.0.1:6333/healthz`
2. Verify Redis connectivity: `redis-cli -a $REDIS_PASSWORD PING`
3. Check worker health: `curl -s http://127.0.0.1:8000/health`
4. Check ARQ queue depth via Redis: `redis-cli -a $REDIS_PASSWORD LLEN arq:queue`
