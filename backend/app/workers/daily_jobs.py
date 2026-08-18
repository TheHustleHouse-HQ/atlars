import asyncio
from datetime import datetime
import logging
from app.workers.celery_app import celery_app
from app.core.database import get_entries_collection, connect_db, close_db
from app.services.synthesis.embedding import generate_embedding

logger = logging.getLogger(__name__)

@celery_app.task(name="embed_entry", queue="daily", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def embed_entry(entry_id: str) -> None:
    """
    Event-driven worker task to generate embeddings for an entry.
    """
    logger.info(f"🚀 Started embedding background task for entry {entry_id}")
    asyncio.run(_process_embedding(entry_id))

async def _process_embedding(entry_id: str):
    await connect_db()
    try:
        entries_collection = get_entries_collection()
        
        # Fetch entry
        entry = await entries_collection.find_one({"entry_id": entry_id})
        if not entry:
            logger.warning(f"Entry {entry_id} not found. Skipping embedding.")
            return
            
        raw_text = entry.get("raw_text")
        if not raw_text or not raw_text.strip():
            logger.info(f"Entry {entry_id} has no text. Skipping embedding.")
            return

        # Generate embedding
        logger.info(f"🧠 Generating embedding via OpenRouter for entry {entry_id}...")
        embedding = await generate_embedding(raw_text)
        
        if not embedding:
            logger.warning(f"Failed to generate embedding for entry {entry_id}. Retrying...")
            raise Exception("Failed to generate embedding")
            
        # Update MongoDB
        now = datetime.utcnow()
        await entries_collection.update_one(
            {"entry_id": entry_id},
            {"$set": {
                "embedding": embedding,
                "embedding_generated_at": now
            }}
        )
        logger.info(f"✅ Successfully updated MongoDB with new embedding for entry {entry_id}")
        
    finally:
        await close_db()


@celery_app.task(name="extract_graph_entities", queue="daily")
def extract_graph_entities() -> None:
    """
    Daily cron job to extract entities, relations, and classifications
    from recent entries using GLiNER2, building the Life Graph.
    """
    logger.info("🚀 Starting daily GLiNER2 entity extraction...")
    asyncio.run(_process_graph_entities())

async def _process_graph_entities():
    from app.services.graph.entity_extraction import extract_semantics
    from app.services.graph.entity_resolution import resolve_entities
    from app.services.graph.graph_builder import build_graph_from_semantics
    
    await connect_db()
    try:
        entries_col = get_entries_collection()
        now = datetime.utcnow()
        # Find entries that haven't been processed for graph extraction yet
        cursor = entries_col.find({"synthesis.graph_extracted_at": None})
        
        processed_count = 0
        async for entry in cursor:
            raw_text = entry.get("raw_text")
            if not raw_text:
                continue
                
            user_id = entry["user_id"]
            entry_id = entry["entry_id"]
            
            # 1. Extract Semantics using GLiNER2 Unified Schema
            extractions = extract_semantics(raw_text)
            
            if not extractions:
                continue
                
            # 2. Entity Resolution & Confidence Gates
            filtered, node_id_map = await resolve_entities(user_id, extractions)
            
            # 3. Graph Builder
            await build_graph_from_semantics(user_id, entry_id, filtered, node_id_map)
            
            # Mark entry as processed
            await entries_col.update_one(
                {"entry_id": entry_id},
                {"$set": {"synthesis.graph_extracted_at": now}}
            )
            processed_count += 1
            
        logger.info(f"✅ Graph extraction complete. Processed {processed_count} entries.")
    finally:
        await close_db()


@celery_app.task(queue="daily")
def extract_traits(user_id: str) -> None:
    # Phase 2 — placeholder
    pass


@celery_app.task(queue="daily")
def extract_beliefs(user_id: str) -> None:
    # Phase 2 — placeholder
    pass


@celery_app.task(queue="daily")
def detect_contradictions(user_id: str) -> None:
    # Phase 2 — placeholder
    pass


@celery_app.task(name="update_user_maturity_stages", queue="daily")
def update_user_maturity_stages() -> None:
    """
    Daily cron job to passively upgrade users to 'scoring' or 'inference' stages
    based on the time elapsed since their first entry.
    """
    logger.info("🕒 Starting daily maturity stage updates...")
    asyncio.run(_process_maturity_stages())


async def _process_maturity_stages():
    from app.core.database import get_users_collection
    
    await connect_db()
    try:
        users_collection = get_users_collection()
        now = datetime.utcnow()
        
        # We only need to check users in 'extraction' or 'scoring' who have submitted at least one entry
        cursor = users_collection.find({
            "maturity_stage": {"$in": ["extraction", "scoring"]},
            "first_entry_at": {"$ne": None}
        })
        
        upgraded_to_scoring = 0
        upgraded_to_inference = 0
        
        async for user in cursor:
            first_entry_at = user.get("first_entry_at")
            if not first_entry_at:
                continue
                
            days_elapsed = (now - first_entry_at).days
            
            new_stage = None
            if user["maturity_stage"] == "extraction" and days_elapsed >= 30:
                new_stage = "scoring"
                upgraded_to_scoring += 1
            elif user["maturity_stage"] == "scoring" and days_elapsed >= 90:
                new_stage = "inference"
                upgraded_to_inference += 1
                
            if new_stage:
                await users_collection.update_one(
                    {"user_id": user["user_id"]},
                    {"$set": {"maturity_stage": new_stage}}
                )
                logger.info(f"🚀 Upgraded user {user['user_id']} to {new_stage} (Days elapsed: {days_elapsed})")
                
        logger.info(f"✅ Maturity updates complete. Upgraded to scoring: {upgraded_to_scoring}, to inference: {upgraded_to_inference}")
    finally:
        await close_db()
