"""
Cognitive Worker ARQ — Memory-as-a-Service (MaaS)
Main entry point for the processing worker.
"""
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ─── Load .env ──────────────────────────────────────────────────────────────
ENV_PATH = Path(__file__).parent.parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# ─── Logging configuration ──────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cognitive-worker")

# ─── Import ARQ worker ──────────────────────────────────────────────────────
from arq import create_pool, cron
from arq.connections import RedisSettings

from tasks.ingestion import ingest_memory
from tasks.reflection import reflect_on_memories, micro_reflection
from tasks.file_ingestion import ingest_file

# ─── Redis configuration ────────────────────────────────────────────────────
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-maas")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")

redis_settings = RedisSettings(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD or None,
)

# ─── Startup/shutdown functions ────────────────────────────────────────────
async def startup(ctx):
    """Connect to Qdrant and validate the collection."""
    from services.local_qdrant import get_qdrant_client, ensure_collection

    logger.info("Worker starting...")
    ctx["qdrant"] = get_qdrant_client()
    await ensure_collection(ctx["qdrant"])
    logger.info("Qdrant connection validated")


async def process_wiki_file(ctx, file_path: str):
    """ARQ job: ingests a .md file from the vault."""
    return await ingest_file(ctx["qdrant"], file_path)


async def shutdown(ctx):
    """Clean up connections."""
    logger.info("Worker shutting down...")
    if "qdrant" in ctx:
        await ctx["qdrant"].close()


# ─── ARQ function definitions ────────────────────────────────────────────
async def process_ingestion(ctx, memory_text: str, source: str, tags: list = None):
    """ARQ job: ingests a memory into the vector store."""
    return await ingest_memory(ctx["qdrant"], memory_text, source, tags)


async def process_reflection(ctx):
    """ARQ job: runs periodic reflection."""
    return await reflect_on_memories(ctx["qdrant"])


async def process_micro_reflection(ctx):
    """ARQ job: runs on-demand micro-reflection (Phase 3)."""
    return await micro_reflection(ctx["qdrant"])


# ─── ARQ Worker Settings ─────────────────────────────────────────────────
class WorkerSettings:
    """ARQ worker settings."""
    redis_settings = redis_settings
    functions = [process_ingestion, process_reflection, process_micro_reflection, process_wiki_file]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = int(os.environ.get("ARQ_MAX_JOBS", "10"))
    job_timeout = int(os.environ.get("ARQ_JOB_TIMEOUT", "300"))
    keep_result = int(os.environ.get("ARQ_KEEP_RESULT", "3600"))
    cron_jobs = [
        # Reflection every 2 hours (minute 0 of even hours)
        cron(process_reflection, hour={0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22}, minute=0),
        # Micro-reflection now triggered via reflection_trigger.py (idle + budget)
    ]


# ─── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--run-worker":
        from arq.worker import run_worker
        logger.info("Starting ARQ worker (programmatic)...")
        run_worker(WorkerSettings)
    else:
        print("Usage: python main.py --run-worker")
        print("")
        print("To enqueue jobs via Redis, use the enqueue functions")
        print("or the Hermes cron scripts in the scripts/ directory.")
