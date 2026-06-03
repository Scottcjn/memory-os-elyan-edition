#!/usr/bin/env python3
"""
semantic_dedup.py
Scanner mensal de near-duplicates no knowledge_base_hybrid via cosine similarity.
Rodo no primeiro domingo de cada mês (cron: 0 3 1 * *).

Regras:
- Ignora coleções com prefixo em DEDUP_EXEMPT_PREFIXES (csv)
- Não deleta automaticamente — apenas emite relatório JSON de candidatos
- Threshold de similaridade: 0.92 (configurável)
- Merge é feito em upserts via file_ingestion.py (pre-write dedup)
- Este script faz o scan retroativo da coleção inteira

Uso:
  python3 semantic_dedup.py [--collection knowledge_base_hybrid] [--threshold 0.92] [--dry-run]
"""

import os
import sys
import json
import math
import argparse
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# ─── Config ────────────────────────────────────────────────────────────────
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.environ.get("QDRANT_COLLECTION", "knowledge_base")
SCROLL_LIMIT = 50  # paginação Qdrant (evita timeout em coleções grandes)
SIMILARITY_THRESHOLD = 0.92
TOP_NEIGHBORS = 10

LOG_DIR = Path.home() / ".hermes" / "logs"
LOG_FILE = LOG_DIR / "semantic_dedup.log"
REPORT_FILE = LOG_DIR / "semantic_dedup_report.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_message(msg: str):
    ts = now_iso()
    line = f"[{ts}] {msg}"
    print(line)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ─── Qdrant Operations ────────────────────────────────────────────────────

def scroll_all_chunks(collection: str) -> List[Dict]:
    """
    Carrega todos os pontos da coleção paginando via scroll.
    Retorna lista de {id, vector, payload}.
    """
    all_chunks = []
    offset = None
    scanned = 0

    while True:
        payload = {
            "limit": SCROLL_LIMIT,
            "with_payload": True,
            "with_vector": True,
        }
        if offset is not None:
            payload["offset"] = offset

        try:
            resp = requests.post(
                f"{QDRANT_URL}/collections/{collection}/points/scroll",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result", {})
            points = result.get("points", [])

            if not points:
                break

            for point in points:
                # Pegar apenas vetor dense para similarity
                vector = point.get("vector")
                dense = None
                if isinstance(vector, dict):
                    dense = vector.get("dense")
                elif isinstance(vector, list):
                    dense = vector  # fallback: vetor simples

                if dense:
                    all_chunks.append({
                        "id": point.get("id"),
                        "vector": dense,
                        "payload": point.get("payload", {}),
                    })

            scanned += len(points)
            offset = result.get("next_page_offset")
            if offset is None:
                break

        except Exception as e:
            log_message(f"❌ Erro no scroll Qdrant: {e}")
            break

    log_message(f"📊 Total chunks carregados: {len(all_chunks)} / {scanned} escaneados")
    return all_chunks


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calcula cosine similarity entre dois vetores."""
    if len(v1) != len(v2):
        return 0.0

    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / (norm1 * norm2)


def find_near_duplicates(chunks: List[Dict], threshold: float = SIMILARITY_THRESHOLD) -> List[Dict]:
    """
    Encontra pares de near-duplicates via brute-force cosine similarity.
    Otimização: comparação triangular superior da matriz.
    Retorna lista de {chunk_id_a, chunk_id_b, similarity}.
    """
    n = len(chunks)
    if n < 2:
        return []

    candidates = []
    ids_seen = set()  # evita duplicados (A,B) e (B,A)

    for i in range(n):
        for j in range(i + 1, n):
            # Heurística rápida: pular se textos são muito diferentes em tamanho
            text_len_i = len(chunks[i]["payload"].get("text", ""))
            text_len_j = len(chunks[j]["payload"].get("text", ""))
            if text_len_i > 0 and text_len_j > 0:
                ratio = min(text_len_i, text_len_j) / max(text_len_i, text_len_j)
                if ratio < 0.5:  # Tamanhos muito diferentes, skip
                    continue

            sim = cosine_similarity(chunks[i]["vector"], chunks[j]["vector"])
            if sim >= threshold:
                pair_key = tuple(sorted([str(chunks[i]["id"]), str(chunks[j]["id"])]))
                if pair_key not in ids_seen:
                    ids_seen.add(pair_key)
                    candidates.append({
                        "chunk_id_a": chunks[i]["id"],
                        "chunk_id_b": chunks[j]["id"],
                        "similarity": round(sim, 6),
                        "source_a": chunks[i]["payload"].get("source", "unknown"),
                        "source_b": chunks[j]["payload"].get("source", "unknown"),
                        "title_a": chunks[i]["payload"].get("title", "")[:60],
                        "title_b": chunks[j]["payload"].get("title", "")[:60],
                        "text_preview_a": chunks[i]["payload"].get("text", "")[:100],
                        "text_preview_b": chunks[j]["payload"].get("text", "")[:100],
                    })

    # Ordenar por similaridade decrescente
    candidates.sort(key=lambda x: x["similarity"], reverse=True)
    return candidates


def generate_report(candidates: List[Dict], collection: str, threshold: float, scanned: int) -> Dict:
    """Gera relatório estruturado em JSON."""
    return {
        "timestamp": now_iso(),
        "collection": collection,
        "threshold": threshold,
        "scanned_chunks": scanned,
        "near_duplicate_pairs": len(candidates),
        "candidates": candidates,
        "recommendation": (
            f"{len(candidates)} pares de near-duplicates encontrados. "
            "Revisar manualmente e aplicar merge via Qdrant point update se aprovado."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Semantic Dedup Scanner")
    parser.add_argument("--collection", default=COLLECTION, help="Nome da coleção Qdrant")
    parser.add_argument("--threshold", type=float, default=SIMILARITY_THRESHOLD, help="Threshold cosine similarity")
    parser.add_argument("--dry-run", action="store_true", help="Só escaneia, não salva relatório")
    args = parser.parse_args()

    collection = args.collection

    # Ignorar coleções com prefixos exempt (via DEDUP_EXEMPT_PREFIXES env var)
    exempt_prefixes = os.environ.get("DEDUP_EXEMPT_PREFIXES", "").split(",")
    exempt_prefixes = [p.strip() for p in exempt_prefixes if p.strip()]
    for prefix in exempt_prefixes:
        if collection.startswith(prefix):
            log_message(f"⏭️ Coleção '{collection}' é exempt (prefixo '{prefix}'). Saindo.")
            return

    log_message(f"🚀 Iniciando semantic dedup (collection={collection}, threshold={args.threshold}, dry_run={args.dry_run})")

    # Carregar chunks
    chunks = scroll_all_chunks(collection)

    if not chunks:
        log_message("⚠️ Nenhum chunk encontrado na coleção.")
        return

    # Encontrar near-duplicates
    log_message(f"🔍 Analisando similaridade entre {len(chunks)} chunks...")
    candidates = find_near_duplicates(chunks, threshold=args.threshold)

    # Gerar relatório
    report = generate_report(candidates, collection, args.threshold, len(chunks))

    log_message("=" * 60)
    log_message("📊 RELATÓRIO SEMANTIC DEDUP")
    log_message("=" * 60)
    log_message(f"  Chunks escaneados:      {report['scanned_chunks']}")
    log_message(f"  Near-duplicate pairs:   {report['near_duplicate_pairs']}")

    if candidates:
        log_message(f"  Top similaridade:       {candidates[0]['similarity']:.4f}")
        log_message(f"  Top par:                {candidates[0]['chunk_id_a']} ↔ {candidates[0]['chunk_id_b']}")
    else:
        log_message("  Nenhum near-duplicate encontrado.")

    log_message("=" * 60)

    # Salvar relatório JSON
    if not args.dry_run and candidates:
        try:
            REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(REPORT_FILE, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            log_message(f"📄 Relatório salvo: {REPORT_FILE}")
        except Exception as e:
            log_message(f"❌ Erro ao salvar relatório: {e}")

    # Output JSON para stderr (parseável)
    print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)

    log_message("✅ Semantic dedup completo.")


if __name__ == "__main__":
    main()
