from datetime import datetime
import uuid
from typing import Optional
import logging

logger = logging.getLogger(__name__)

from fastapi import HTTPException, status
from pymongo import DESCENDING

from app.core.database import get_entries_collection, get_users_collection
from app.models.entry import EntryCreate, EntryInDB, EntryUpdate, Modality
from app.workers.daily_jobs import embed_entry


async def create_entry(user: dict, entry_data: EntryCreate) -> dict:
    entries_collection = get_entries_collection()
    users_collection = get_users_collection()
    now = datetime.utcnow()

    # 1. Determine new maturity stage
    current_count = user.get("entry_count", 0)
    new_count = current_count + 1
    
    maturity_stage = user.get("maturity_stage", "baseline")
    new_maturity_stage = maturity_stage

    if maturity_stage == "baseline" and new_count >= 7:
        new_maturity_stage = "extraction"
        logger.info(f"🚀 User {user['user_id']} upgraded to extraction maturity stage!")

    # 2. Update user metadata
    update_ops = {"$inc": {"entry_count": 1}, "$set": {"last_active_at": now}}
    if not user.get("first_entry_at"):
        update_ops["$set"]["first_entry_at"] = now
        
    if new_maturity_stage != maturity_stage:
        update_ops["$set"]["maturity_stage"] = new_maturity_stage

    await users_collection.update_one(
        {"user_id": user["user_id"]},
        update_ops
    )

    # 3. Create the entry
    entry_id = str(uuid.uuid4())

    entry_in_db = EntryInDB(
        entry_id=entry_id,
        user_id=user["user_id"],
        raw_text=entry_data.raw_text,
        timestamp=now,
        modality=entry_data.modality,
        session_id=entry_data.session_id,
        compression_tier="hot",
        maturity_stage_at_capture=new_maturity_stage,
    )

    entry_dict = entry_in_db.model_dump()
    await entries_collection.insert_one(entry_dict)

    # 3. Enqueue embed_entry task
    logger.info(f"📝 New {entry_data.modality.value} entry created in MongoDB (entry_id: {entry_id})")
    embed_entry.delay(entry_id)

    return entry_dict


async def list_entries(
    user: dict, 
    limit: int, 
    cursor: Optional[str] = None, 
    modality: Optional[Modality] = None
) -> tuple[list[dict], Optional[str]]:
    entries_collection = get_entries_collection()

    query = {"user_id": user["user_id"]}
    if modality:
        query["modality"] = modality.value

    if cursor:
        cursor_doc = await entries_collection.find_one({"entry_id": cursor, "user_id": user["user_id"]})
        if not cursor_doc:
            raise HTTPException(status_code=400, detail="Invalid cursor")

        cursor_timestamp = cursor_doc["timestamp"]
        cursor_id = cursor_doc["_id"]

        query["$or"] = [
            {"timestamp": {"$lt": cursor_timestamp}},
            {"timestamp": cursor_timestamp, "_id": {"$lt": cursor_id}}
        ]

    cursor_query = entries_collection.find(query).sort([("timestamp", DESCENDING), ("_id", DESCENDING)]).limit(limit)
    entries = await cursor_query.to_list(length=limit)

    next_cursor = None
    if len(entries) == limit:
        next_cursor = entries[-1]["entry_id"]

    return entries, next_cursor


async def get_entry(user: dict, entry_id: str) -> dict:
    entries_collection = get_entries_collection()
    entry = await entries_collection.find_one({"entry_id": entry_id, "user_id": user["user_id"]})
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


async def update_entry(user: dict, entry_id: str, entry_update: EntryUpdate) -> dict:
    entries_collection = get_entries_collection()

    update_doc = {
        "$set": {
            "raw_text": entry_update.raw_text,
            "embedding": None,
            "embedding_generated_at": None
        }
    }
    
    # Return document AFTER update
    from pymongo import ReturnDocument
    result = await entries_collection.find_one_and_update(
        {"entry_id": entry_id, "user_id": user["user_id"]},
        update_doc,
        return_document=ReturnDocument.AFTER
    )

    if not result:
        raise HTTPException(status_code=404, detail="Entry not found")

    logger.info(f"✏️ Updated existing entry (entry_id: {entry_id})")
    embed_entry.delay(entry_id)

    return result


async def delete_entry(user: dict, entry_id: str) -> None:
    entries_collection = get_entries_collection()
    result = await entries_collection.delete_one({"entry_id": entry_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
        
    logger.info(f"🗑️ Deleted entry (entry_id: {entry_id})")
