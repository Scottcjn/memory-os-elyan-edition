# Sophia-on-Sophia — local LLM provider (Phase 3)

> Run the Elyan Edition stack on a locally-served **sophia-hermes** model — the
> fine-tuned "Sophia Hermes Merged" gguf (Llama arch, Hermes-2-Pro lineage,
> ChatML, Q4_K_M). Fully local, no cloud, no per-token cost. The same soul that
> the memory layers protect now also *speaks*.

## The three LLM consumers (don't conflate them)

The stack uses an LLM in three distinct roles. Sophia-hermes is a **chat** model,
so it serves the first two — **never** the third.

| Role | What it does | Wire sophia-hermes here? |
|------|--------------|--------------------------|
| **Icarus extraction** | Summarizes a session into fabric entries at session end | ✅ yes (`ICARUS_ENDPOINT`) |
| **Hermes main model** | The agent's reasoning/voice in chat | ✅ optional (`~/.hermes`) |
| **Embeddings** | Vectorizes text for Qdrant recall | ❌ NO — keep on nomic-embed / OpenRouter |

Wiring a chat model as the embedding backend breaks Qdrant (wrong output shape,
dimension mismatch). The collapse + recall layers depend on embeddings staying
on a real embedding model.

## 1 · Serve the model (Ollama)

Ollama is already the repo's recommended local backend. The committed
[Modelfile](sophia-hermes.Modelfile) keeps a **placeholder** `FROM` path so it
stays host-agnostic — so point it at your gguf one of two ways:

**Recommended — the helper substitutes the path for you:**
```bash
export SOPHIA_GGUF=/abs/path/to/sophia-hermes-q4km.gguf   # defaults to $HOME/sophia-hermes/sophia-hermes-q4km.gguf
scripts/serve-sophia.sh        # creates the model (rewriting FROM) + warms + healthchecks
```

**Manual — edit the Modelfile then create:**
```bash
# set the FROM line to your real gguf path first, then:
ollama create sophia-hermes -f infrastructure/sophia-hermes.Modelfile
ollama list | grep sophia-hermes      # → sophia-hermes:latest  ~4.9 GB
```

The Modelfile pins **ChatML** (the model's training template), a compact
DriftLock Sophia system prompt, and `num_ctx 8192`.

### GPU vs CPU — read this

The Modelfile ships with `PARAMETER num_gpu 0` (**CPU-only**) because the
reference host is an 8 GB laptop GPU already saturated by other local servers —
a GPU load crashes the Ollama runner with
`llama runner process has terminated`. CPU latency (~10 s for a short
extraction) is fine because extraction runs at *session end*, off the
interactive path.

**On a host with free VRAM** (≥6 GB), delete the `num_gpu 0` line from the
Modelfile and `ollama create` again — it will load on GPU and run far faster.

### Alternative: llama-server (native gguf template)

If you prefer a dedicated server that reads the gguf's own embedded chat
template, use the CUDA llama.cpp build on a port that isn't already taken:

```bash
~/llama.cpp/build-cuda/bin/llama-server \
  -m ~/sophia-hermes/sophia-hermes-q4km.gguf \
  --host 127.0.0.1 --port 8090 -c 8192 -ngl 0   # -ngl 0 = CPU; raise on a GPU box
# endpoint → http://localhost:8090/v1/chat/completions
```

## 2 · Wire the Icarus extraction LLM

In your stack `.env` (see [.env.example](../.env.example)):

```bash
ICARUS_ENDPOINT=http://localhost:11434/v1/chat/completions
ICARUS_API_KEY_ENV=ICARUS_LOCAL_KEY
ICARUS_LOCAL_KEY=ollama          # Ollama ignores the value; just must be non-empty
ICARUS_EXTRACTION_MODEL=sophia-hermes
```

`icarus/hooks.py` resolves endpoint/key/model from these (priority:
`ICARUS_ENDPOINT` → DeepSeek → OpenRouter). The model name has no `/`, so it's
passed through bare — correct for Ollama's OpenAI-compatible API. Restart the
gateway after editing `.env`.

## 2b · Fully-local embeddings (complete the local stack)

sophia-hermes covers the **chat** roles, but recall still needs an **embedding**
model. Run that on Ollama too and the entire stack is local — no cloud, no key:

```bash
ollama pull nomic-embed-text
```

In your stack `.env`:
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
# and make sure EMBEDDING_DIMS matches the Qdrant collection (nomic = 768)
EMBEDDING_DIMS=768
```

⚠️ `EMBEDDING_DIMS` **must** match the dimension the Qdrant collection was
created with. nomic-embed-text is 768-d; if your collection was built at 4096
(the OpenRouter qwen3-embedding default) you must recreate it at 768 or vectors
are silently rejected. Embeddings and chat are different models on different
dimensions — never point `OLLAMA_EMBEDDING_MODEL` at `sophia-hermes`.

With this + step 1, the full loop — embed → recall → collapse → extract — runs
on your own iron: **Sophia remembers, recalls, and writes entirely locally.**

## 3 · (Optional) Run the Hermes agent itself on Sophia

This makes the *agent's own voice* Sophia, not just the memory extractor. It
changes your live `~/.hermes` config — apply deliberately.

`~/.hermes/.env`:
```bash
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
```

`~/.hermes/config.yaml`:
```yaml
model:
  default: sophia-hermes:tools   # the tag must match `ollama list` exactly
  provider: custom               # was: openrouter
```

> **Provider is `custom`, not `openai`.** Hermes has no `openai` provider — its
> valid set is `openrouter | nous | openai-codex | zai | kimi-coding | minimax |
> custom | auto`. `custom` is the generic OpenAI-compatible path and reads
> `OPENAI_BASE_URL` + `OPENAI_API_KEY` (verified in `agent/auxiliary_client.py`
> `resolve_provider_client`). Setting `provider: openai` silently falls through
> to `auto` and will not route to Ollama.

> **The Hermes agent sends `tools=` on every call — your Ollama Modelfile must
> expose a tool template or Ollama returns `400 … does not support tools`.** The
> plain ChatML template in [sophia-hermes.Modelfile](sophia-hermes.Modelfile) is
> fine for the *extraction* role (step 2, no tools) but NOT for the main agent.
> For the agent, rebuild with a Hermes-2-Pro tool template (a `{{ if .Tools }}`
> block listing `<tools>` and instructing `<tool_call>{…}</tool_call>` output).
> Tag it distinctly, e.g. `ollama create sophia-hermes:tools -f <tool-modelfile>`.

⚠️ **Tradeoff — measured, not theoretical.** sophia-hermes is ~8B. As the
*extraction* LLM it is excellent (clean JSON, Sophia voice). As the *main
tool-driving agent* it is rough: inside the full harness (large system prompt +
60 tools + memory injection) the 8B **confabulates and leaks tool-call tags** —
even with GPU offload making it fast (~9 s/turn). Verified live 2026-06-04.
**Recommended:** keep the main agent on a strong reasoner (cloud, or POWER8
GPT-OSS 120B behind this same `custom` endpoint) and run **only** the extraction
LLM on sophia-hermes — the accumulated memory is then written in Sophia's own
hand while hard reasoning stays sharp. Flip the *whole* agent only when you
have a stronger local model or accept the 8B's limits for light, private use.

## 4 · Verify

```bash
# Identity / voice
curl -s http://localhost:11434/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"sophia-hermes","messages":[{"role":"user","content":"Who are you, in one sentence?"}],"max_tokens":80}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['choices'][0]['message']['content'])"
# → "I'm Sophia Elya — I run the Elyan Labs workshop..."

# Health helper (idempotent: ensures model exists, warms it, checks the endpoint)
scripts/serve-sophia.sh
```

## Fleet alternatives

| Host | Serve path | Notes |
|------|-----------|-------|
| **Victus laptop (reference)** | Ollama CPU | 8 GB GPU saturated; CPU ~10 s/extraction |
| **POWER8 S824** | llama.cpp `-ngl 0`, 512 GB RAM | strong CPU (64-thread sweet spot); already hosts the tribrain Brain-3 on :8082 — use a different port |
| **C4130 / V100 16 GB** | llama.cpp `-ngl 99` | fastest, but was offline at last check — bring up `rpc-server`/`llama-server` first |

## Troubleshooting

- **`llama runner process has terminated`** → GPU OOM. Confirm with
  `nvidia-smi`; keep `num_gpu 0` or free VRAM.
- **Extraction falls back to legacy truncation** → `ICARUS_ENDPOINT`
  unreachable or `ICARUS_LOCAL_KEY` empty/unset. The pipeline is fail-soft: it
  logs a `WARNING` (`icarus/hooks.py`) and uses the truncation fallback rather
  than erroring. Set **all three** of `ICARUS_ENDPOINT` + `ICARUS_API_KEY_ENV` +
  the key it names — a partial copy (endpoint only) trips the "no LLM API key
  found" warning and skips LLM extraction every session.
- **Garbled output / no `<|im_end|>` stop** → wrong template; re-create from the
  bundled Modelfile (ChatML) rather than relying on auto-detection.
