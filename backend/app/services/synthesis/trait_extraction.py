import json
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from pymongo import UpdateOne

from app.services.routing.openrouter import openrouter_client
from app.models.trait import OceanDimension, SignalDirection, TraitSignal
from app.core.database import get_entries_collection, get_traits_collection, get_trait_signals_collection
from app.core.config import settings
from app.services.synthesis.prompts import get_trait_extraction_prompt

logger = logging.getLogger(__name__)

async def extract_traits_for_entries(entries: List[dict]) -> Tuple[List[TraitSignal], Dict[str, int]]:
    if not entries:
        return [], {"signals_extracted": 0, "signals_rejected_validation": 0}
        
    prompt_version = settings.trait_extraction_prompt_version
    system_prompt = get_trait_extraction_prompt(prompt_version)
    
    entries_text = "\n\n".join([f"Entry ID: {e['entry_id']}\nText: {e.get('raw_text', '')}" for e in entries])
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please extract OCEAN signals from these entries:\n\n{entries_text}"}
    ]
    
    try:
        response = await openrouter_client.create_chat_completion(
            messages=messages,
            model="openai/gpt-oss-20b:free",
            response_format={"type": "json_object"},
            reasoning={"enabled": True}
        )
        
        if not response or "choices" not in response:
            raise Exception("Invalid or empty response from OpenRouter")
            
        content = response["choices"][0]["message"]["content"]
        print(f"RAW LLM RESPONSE: {content}")
        
        try:
            data = json.loads(content)
            if isinstance(data, list):
                signals_data = data
            else:
                signals_data = data.get("signals", [])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {content}")
            raise ValueError(f"LLM returned malformed JSON: {e}")
            
        extracted_signals = []
        entry_dict = {e["entry_id"]: e for e in entries}
        
        metrics = {
            "signals_rejected_validation": 0,
            "signals_extracted": 0,
        }
        
        for s in signals_data:
            try:
                e_id = s.get("entry_id")
                if e_id not in entry_dict:
                    logger.warning(f"Rejected signal with unknown entry_id: {e_id}")
                    metrics["signals_rejected_validation"] += 1
                    continue
                    
                evidence = s.get("evidence", "")
                raw_text = entry_dict[e_id].get("raw_text", "")
                if evidence not in raw_text:
                    logger.warning(f"Rejected signal due to hallucinated evidence: '{evidence}' not in '{raw_text}'")
                    metrics["signals_rejected_validation"] += 1
                    continue

                # Use original entry timestamp for longitudinal accuracy
                entry_timestamp = entry_dict[e_id].get("timestamp", datetime.utcnow())
                user_id = str(entry_dict[e_id].get("user_id", "unknown"))

                signal = TraitSignal(
                    user_id=user_id,
                    ocean_dimension=OceanDimension(s["ocean_dimension"]),
                    direction=SignalDirection(s["direction"]),
                    confidence=float(s["confidence"]),
                    evidence=evidence,
                    evidence_type=s.get("evidence_type", "unknown"),
                    entry_id=e_id,
                    trait_extraction_version=prompt_version,
                    model="openai/gpt-oss-20b:free",
                    timestamp=entry_timestamp
                )
                extracted_signals.append(signal)
                metrics["signals_extracted"] += 1
            except Exception as e:
                logger.warning(f"Failed to validate signal {s}: {e}")
                metrics["signals_rejected_validation"] += 1
                
        return extracted_signals, metrics
        
    except Exception as e:
        logger.error(f"Error during trait extraction: {e}")
        raise e


async def process_trait_extractions(user_id: Optional[str] = None):
    """
    Finds unextracted entries, extracts traits, and upserts the traits collection.
    If user_id is provided, only processes entries for that specific user.
    """
    entries_col = get_entries_collection()
    traits_col = get_traits_collection()
    signals_col = get_trait_signals_collection()
    
    query = {"synthesis.traits_extracted_at": None}
    if user_id:
        query["user_id"] = user_id
        
    cursor = entries_col.find(query)
    
    entries_by_user = {}
    async for entry in cursor:
        if not entry.get("raw_text") or not entry.get("user_id") or not entry.get("entry_id"):
            continue
        user_id = entry["user_id"]
        if user_id not in entries_by_user:
            entries_by_user[user_id] = []
        entries_by_user[user_id].append(entry)
        
    processed_count = 0
    now = datetime.utcnow()
    
    global_metrics = {
        "entries_processed": 0,
        "signals_extracted": 0,
        "entries_with_no_signal": 0,
        "signals_rejected_validation": 0,
        "signals_replaced": 0,
        "api_failures": 0,
        "validation_failures": 0
    }
    
    for user_id, user_entries in entries_by_user.items():
        chunk_size = 15
        for i in range(0, len(user_entries), chunk_size):
            batch = user_entries[i:i+chunk_size]
            
            try:
                signals, batch_metrics = await extract_traits_for_entries(batch)
                global_metrics["signals_extracted"] += batch_metrics["signals_extracted"]
                global_metrics["signals_rejected_validation"] += batch_metrics["signals_rejected_validation"]
                if not signals:
                    global_metrics["entries_with_no_signal"] += len(batch)
            except ValueError as e:
                logger.error(f"Validation/Client error processing batch for user {user_id}: {e}")
                global_metrics["validation_failures"] += 1
                # Mark as extracted so we don't retry bad json/requests forever
                signals = [] 
            except Exception as e:
                logger.error(f"API/Server error processing batch for user {user_id}: {e}")
                global_metrics["api_failures"] += 1
                # Skip to next batch, do NOT mark as extracted so it retries later
                continue
                
            if signals:
                # 1. Bulk Upsert Event Logs (Idempotency)
                operations = []
                for signal in signals:
                    signal_dict = signal.model_dump()
                    signal_dict["ocean_dimension"] = signal.ocean_dimension.value
                    signal_dict["direction"] = signal.direction.value
                    
                    operations.append(
                        UpdateOne(
                            {
                                "user_id": signal.user_id, 
                                "entry_id": signal.entry_id, 
                                "ocean_dimension": signal_dict["ocean_dimension"]
                            },
                            {"$set": signal_dict},
                            upsert=True
                        )
                    )
                
                if operations:
                    res = await signals_col.bulk_write(operations, ordered=False)
                    global_metrics["signals_replaced"] += res.modified_count
                    
                # 2. Re-aggregate traits for this user
                all_user_signals = await signals_col.find({"user_id": user_id}).to_list(length=None)
                
                categories = {}
                for s in all_user_signals:
                    dim = s["ocean_dimension"]
                    if dim not in categories:
                        categories[dim] = {
                            "high_signals_count": 0,
                            "low_signals_count": 0,
                            "overall_confidence": 0.0,
                            "first_seen": None,
                            "last_seen": None
                        }
                        
                    cat = categories[dim]
                    if s["direction"] == "high":
                        cat["high_signals_count"] += 1
                    else:
                        cat["low_signals_count"] += 1
                        
                    s_time = s["timestamp"]
                    if not cat["first_seen"] or s_time < cat["first_seen"]:
                        cat["first_seen"] = s_time
                    if not cat["last_seen"] or s_time > cat["last_seen"]:
                        cat["last_seen"] = s_time
                        
                # Compute average confidence per dimension
                for dim, cat in categories.items():
                    dim_signals = [s["confidence"] for s in all_user_signals if s["ocean_dimension"] == dim]
                    cat["overall_confidence"] = sum(dim_signals) / len(dim_signals) if dim_signals else 0.0
                    
                await traits_col.update_one(
                    {"user_id": user_id},
                    {"$set": {"categories": categories, "updated_at": now}},
                    upsert=True
                )
                
            # Only mark batch as extracted if the LLM call succeeded (even if signals were empty)
            entry_ids = [e["entry_id"] for e in batch]
            await entries_col.update_many(
                {"entry_id": {"$in": entry_ids}},
                {"$set": {"synthesis.traits_extracted_at": now}}
            )
            processed_count += len(batch)
            global_metrics["entries_processed"] += len(batch)
            
    if processed_count > 0:
        logger.info(f"✅ Trait extraction complete. Processed {processed_count} entries.")
        logger.info(f"📊 Metrics: {json.dumps(global_metrics)}")
        
        signals_per_entry = global_metrics['signals_extracted'] / global_metrics['entries_processed']
        logger.info(f"📈 Signals per entry ratio: {signals_per_entry:.2f}")
