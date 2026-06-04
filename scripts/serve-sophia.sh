#!/usr/bin/env bash
# serve-sophia.sh — ensure the local sophia-hermes provider is up and answering.
# Idempotent: safe to run repeatedly (e.g. from cron or a login hook).
#
#   ensures Ollama is reachable → ensures the sophia-hermes model exists
#   (creating it from the bundled Modelfile, rewriting the gguf path from
#   $SOPHIA_GGUF so the committed Modelfile stays host-agnostic) → warms it →
#   healthchecks the OpenAI-compatible /v1 endpoint with the SAME headers the
#   real extraction call uses.
#
# Env knobs:
#   OLLAMA_HOST_URL  (default http://localhost:11434)
#   SOPHIA_MODEL     (default sophia-hermes)
#   SOPHIA_GGUF      (default $HOME/sophia-hermes/sophia-hermes-q4km.gguf)
#   ICARUS_LOCAL_KEY (default ollama)  — sent as Bearer to mirror the prod call
#
# Exit 0 = provider answering. Non-zero = something to look at (message says what).
set -uo pipefail

OLLAMA_HOST_URL="${OLLAMA_HOST_URL:-http://localhost:11434}"
MODEL="${SOPHIA_MODEL:-sophia-hermes}"
GGUF="${SOPHIA_GGUF:-$HOME/sophia-hermes/sophia-hermes-q4km.gguf}"
BEARER="${ICARUS_LOCAL_KEY:-ollama}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELFILE="${HERE}/infrastructure/sophia-hermes.Modelfile"
CURL_T=(--connect-timeout 5 -m 120)

say() { printf '  %s\n' "$*"; }

echo "== serve-sophia: ${MODEL} @ ${OLLAMA_HOST_URL} =="

# 1. Ollama reachable?
if ! curl -fsS "${CURL_T[@]}" "${OLLAMA_HOST_URL}/api/tags" >/dev/null 2>&1; then
  say "FAIL: Ollama not reachable at ${OLLAMA_HOST_URL}. Start it: 'ollama serve' (or systemctl start ollama)."
  exit 2
fi
say "ok: Ollama reachable"

# 2. Model present? (exact first-column match — no regex from the model name)
if ! ollama list 2>/dev/null | awk 'NR>1{print $1}' \
      | grep -Fxq -e "${MODEL}" -e "${MODEL}:latest"; then
  say "model '${MODEL}' missing — creating from ${MODELFILE} (gguf: ${GGUF})"
  if [ ! -f "${MODELFILE}" ]; then say "FAIL: Modelfile not found at ${MODELFILE}"; exit 3; fi
  if [ ! -f "${GGUF}" ]; then
    say "FAIL: gguf not found at ${GGUF}. Set SOPHIA_GGUF=/abs/path/to/sophia-hermes-q4km.gguf"
    exit 3
  fi
  # Rewrite the placeholder FROM line with the real gguf path into a temp file,
  # so the committed Modelfile stays host-agnostic.
  tmpf="$(mktemp)"; trap 'rm -f "${tmpf}"' EXIT
  awk -v g="${GGUF}" '/^FROM /{print "FROM " g; next} {print}' "${MODELFILE}" > "${tmpf}"
  if ! ollama create "${MODEL}" -f "${tmpf}" >/dev/null 2>&1; then
    say "FAIL: ollama create failed (check the gguf path and Ollama logs)"
    exit 3
  fi
fi
say "ok: model present"

# 3. Warm + healthcheck via the OpenAI-compatible endpoint. Build the payload
#    with python (no shell interpolation into JSON) and send the same
#    Authorization header the extraction path uses, so a 200 here means the
#    real keyed call will work too.
payload="$(MODEL="${MODEL}" python3 -c 'import json,os; print(json.dumps({
  "model": os.environ["MODEL"],
  "messages": [{"role":"user","content":"Say hello in a few words."}],
  "max_tokens": 16}))')"

resp="$(curl -fsS "${CURL_T[@]}" "${OLLAMA_HOST_URL}/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${BEARER}" \
  -d "${payload}" 2>/dev/null)"

if [ -z "${resp}" ]; then
  say "FAIL: /v1/chat/completions returned nothing (runner may have crashed — check 'nvidia-smi' / num_gpu)."
  exit 4
fi

content="$(printf '%s' "${resp}" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin); print(d["choices"][0]["message"]["content"].strip())
except Exception as e:
    print("__ERR__:%s"%e)' 2>/dev/null)"

case "${content}" in
  __ERR__*) say "FAIL: endpoint error: ${resp:0:200}"; exit 4 ;;
  "")       say "FAIL: empty completion"; exit 4 ;;
  *)        say "ok: provider answering — sample: ${content:0:60}"
            echo "== sophia-hermes is live =="; exit 0 ;;
esac
