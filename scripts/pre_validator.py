#!/usr/bin/env python3
"""
Pré-validador Semântico — Linter de decisão baseado no knowledge_base.
Consulta o vault antes de ações de I/O ou chamadas de API.

Uso:
  python3 pre_validator.py "fazer POST no upsert do Qdrant"               # deve findar pitfall
  python3 pre_validator.py --json "usar Claude da Anthropic"             # JSON output
  python3 pre_validator.py --domain qdrant,api "modificar docker-compose" # restringe busca

Exit codes:
  0 = pass/warn  (ação pode prosseguir)
  1 = blocked    (ação deve ser abortada)

Fail-open: se OpenRouter ou Qdrant offline, permite execução com alerta.
"""

import os
import sys
import json
import re
import requests
from typing import List, Dict, Optional
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────────────
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.environ.get("QDRANT_COLLECTION", "knowledge_base")
if not OPENROUTER_KEY:
    _env = Path.home() / ".env"
    if _env.exists():
        for ln in _env.read_text().splitlines():
            if ln.startswith("OPENROUTER_API_KEY="):
                OPENROUTER_KEY = ln.split("=", 1)[1].strip().strip('"')
                break
EMBEDDING_MODEL = "qwen/qwen3-embedding-8b"
TOP_K = 5
SCORE_THRESHOLD = 0.60
WARN_THRESHOLD = 0.75          # docs wiki pura precisam de score mais alto para aviso
BLOCK_SEVERITIES = {"critical", "high"}
WARN_SEVERITIES  = {"medium"}
RULE_SOURCES = {"reflection", "decision", "rule", "pitfall", "insight"}
REQUEST_TIMEOUT = 10

# ─── Restriction Patterns in wiki text ─────────────────────────────────────
RESTRICTION_KEYWORDS = [
    "não usar", "não deve", "não pode", "nunca usar", "evitar",
    "proibido", "não recomendado", "anti-padrão", "erro comum",
    "cuidado", "atenção", "importante:", "⚠️", "🚫",
    "deve usar", "deve sempre", "requer", "obrigatório",
    "manter", "não alterar", "não modificar", "congelar",
]

def contains_restriction(text: str) -> bool:
    """Verifica se um texto contém padrões de restrição/decisão."""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in RESTRICTION_KEYWORDS)

# ─── Domain Tag Inference ─────────────────────────────────────────────────
DOMAIN_PATTERNS = {
    "docker"     : ["docker", "compose", "container", "image", "dockerfile"],
    "qdrant"     : ["qdrant", "collection", "points", "upsert", "vector", "vectors", "embedding"],
    "redis"      : ["redis", "arq", "queue", "job", "worker", "broker"],
    "openrouter" : ["openrouter", "embedding", "api_key", "openai", "api_base", "model"],
    "hermes"     : ["hermes", "config.yaml", "skill", "cron", "gateway", "cli"],
    "wiki"       : ["wiki", "raw/", "ingest", "vault", "obsidian", "knowledge_base"],
    "webui"      : ["webui", "open-webui", "frontend", "chat", "rag"],
    "infra"      : ["deploy", "server", "systemd", "service", "port", "host"],
    "security"   : ["password", "secret", "token", "auth", "permission", "sudo"],
    "maas"       : ["maas", "memory", "cognitive", "agent"],
}

def infer_domain_tags(description: str) -> List[str]:
    d = description.lower()
    found = set()
    for domain, pats in DOMAIN_PATTERNS.items():
        if any(p in d for p in pats):
            found.add(domain)
    return sorted(found)

# ─── Core ───────────────────────────────────────────────────────────────────

def embed_text(text: str) -> Optional[List[float]]:
    if not OPENROUTER_KEY:
        return None
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={"model": EMBEDDING_MODEL, "input": text[:8000]},
            timeout=REQUEST_TIMEOUT
        )
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]
    except Exception as e:
        print(f"[PV-ERROR] Embedding failed: {e}", file=sys.stderr)
        return None

def search_knowledge_base(vector: List[float], domain_tags: List[str]) -> List[Dict]:
    try:
        r = requests.post(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
            headers={"Content-Type": "application/json"},
            json={"vector": vector, "limit": TOP_K * 3, "with_payload": True},
            timeout=REQUEST_TIMEOUT
        )
        r.raise_for_status()
        hits = []
        for item in r.json().get("result", []):
            pld = item.get("payload", {})
            src = str(pld.get("source", "")).lower()
            sev = str(pld.get("severity", pld.get("decision_severity", "low"))).lower()
            tags = [str(t).lower() for t in pld.get("tags", [])]
            score = item.get("score", 0)
            
            # Se pediu filtros de domínio, exige overlap
            if domain_tags:
                dom_low = [d.lower() for d in domain_tags]
                if not set(dom_low) & set(tags):
                    continue
            
            hits.append({
                "id"     : str(item.get("id", "")),
                "score"  : score,
                "title"  : pld.get("title", "Sem título"),
                "text"   : (pld.get("text", "") or "")[:400],
                "source" : src,
                "severity": sev,
                "tags"   : tags,
            })
        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits[:TOP_K]
    except Exception as e:
        print(f"[PV-ERROR] Qdrant search failed: {e}", file=sys.stderr)
        return []

def is_rule_hit(hit: Dict) -> bool:
    """Retorna True se o hit contém regra explícita (reflection/decision/rule/insight/pitfall)."""
    return any(s in hit["source"] for s in RULE_SOURCES)

def classify_hit(hit: Dict, action_desc: str) -> str:
    """
    Retorna categoria do hit: 'block', 'warn', 'info', ou 'none'.
    Considera tanto source=reflection/decision/rule quanto padrões de restrição
    embutidos no texto de documentos wiki.
    """
    sev = hit.get("severity", "low")
    is_rule = is_rule_hit(hit) or contains_restriction(hit.get("text", ""))
    score = hit.get("score", 0)
    
    # Se contém restrição no texto, dá mais peso
    restriction_bonus = 0.08 if contains_restriction(hit.get("text", "")) else 0
    effective_score = score + restriction_bonus
    
    # Proximidade: se a ação (ex: "POST") aparece no texto próximo a uma keyword
    action_terms = set(action_desc.lower().split())
    text_lower = (hit.get("text", "") or "").lower()
    text_words = set(text_lower.split())
    proximity_match = len(action_terms & text_words) > 0
    
    # Se tem restrição + proximidade → eleva severidade
    has_restriction = contains_restriction(hit.get("text", "")) and proximity_match
    
    if is_rule or has_restriction:
        if sev in BLOCK_SEVERITIES or (has_restriction and effective_score >= 0.65):
            return "block"
        elif sev in WARN_SEVERITIES or (has_restriction and effective_score >= SCORE_THRESHOLD):
            return "warn"
    
    # Para documentos wiki normais, só avisa se score muito alto
    if effective_score >= WARN_THRESHOLD:
        return "warn"
    if effective_score >= SCORE_THRESHOLD:
        return "info"
    return "none"

def validate_action(action_description: str, domain_tags: Optional[List[str]] = None) -> Dict:
    try:
        dom = domain_tags or infer_domain_tags(action_description)
        vec = embed_text(action_description)
        if vec is None:
            return {"status": "pass", "blocked": False, "message": "⚠️  Validador offline. Executando com cautela.", "action": action_description}
        
        hits = search_knowledge_base(vec, dom)
        blockers = []
        warnings = []
        infos = []
        
        for h in hits:
            cat = classify_hit(h)
            if cat == "block":
                blockers.append(h)
            elif cat == "warn":
                warnings.append(h)
            elif cat == "info":
                infos.append(h)
        
        if blockers:
            lines = [f"🚫 AÇÃO BLOQUEADA — {len(blockers)} regra(s) crítica(s) no vault:"]
            for b in blockers:
                lines.append(f"  • [{b['severity'].upper()}] {b['title']} (score: {b['score']:.2f})")
                lines.append(f"    {b['text'][:200]}...")
            lines.append("")
            lines.append("Ignorar? Digite 'forçar' (não recomendado).")
            return {
                "status": "blocked", "blocked": True,
                "blockers": blockers, "warnings": warnings,
                "message": "\n".join(lines), "action": action_description, "domain": dom,
            }
        
        if warnings:
            lines = [f"⚠️  {len(warnings)} aviso(s) encontrado(s) no vault:"]
            for w in warnings:
                lines.append(f"  • [{w['severity'].upper()}] {w['title']} (score: {w['score']:.2f})")
                lines.append(f"    {w['text'][:200]}...")
            return {
                "status": "warn", "blocked": False,
                "warnings": warnings, "infos": infos,
                "message": "\n".join(lines), "action": action_description, "domain": dom,
            }
        
        if infos:
            return {
                "status": "info", "blocked": False,
                "infos": infos,
                "message": f"ℹ️  {len(infos)} documento(s) relevante(s), nenhum crítico.",
                "action": action_description, "domain": dom,
            }
        
        return {
            "status": "pass", "blocked": False,
            "message": "Nenhum insight relevante encontrado. Execução autorizada.",
            "action": action_description, "domain": dom,
        }
    except Exception as e:
        return {
            "status": "pass", "blocked": False,
            "message": f"Validador falhou ({e}). Executando com cautela.",
            "action": action_description, "domain": [],
        }

# ─── Main ───────────────────────────────────────────────────────────────────
def main():
    import argparse
    p = argparse.ArgumentParser(description="Pré-validador Semântico")
    p.add_argument("action", nargs="?", help="Descrição da ação")
    p.add_argument("--domain", help="Tags de domínio separadas por vírgula")
    p.add_argument("--json", action="store_true", help="Saída JSON")
    p.add_argument("--silent", action="store_true", help="Silencioso — só exit code")
    p.add_argument("--force-block", action="store_true", help="Forçar bloqueio (teste)")
    args = p.parse_args()
    
    action = args.action or sys.stdin.read().strip() or "fazer POST no endpoint de upsert do Qdrant"
    dom = [x.strip() for x in args.domain.split(",")] if args.domain else None
    
    res = validate_action(action, dom)
    if args.force_block:
        res["blocked"] = True
        res["status"] = "blocked"
    
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    elif not args.silent:
        print(res["message"])
        if res["blocked"]:
            print("\n(Use --force-block para testar bypass de validador)")
    
    sys.exit(1 if res["blocked"] else 0)

if __name__ == "__main__":
    main()
