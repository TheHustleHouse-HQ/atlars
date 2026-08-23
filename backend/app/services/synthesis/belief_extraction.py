import json
import logging
import uuid
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from pymongo import UpdateOne

from app.services.routing.openrouter import openrouter_client
from app.models.belief import BeliefDocument, BeliefType, BeliefEvidence
from app.core.database import get_entries_collection, get_beliefs_collection
from app.core.config import settings
from app.services.synthesis.prompts import get_belief_extraction_prompt
from app.services.synthesis.embedding import generate_embedding
import math

logger = logging.getLogger(__name__)

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

async def extract_beliefs_for_entries(entries: List[dict]) -> Tuple[List[BeliefDocument], Dict[str, int]]:
    if not entries:
        return [], {"beliefs_extracted": 0, "beliefs_rejected_validation": 0}
        
    prompt_version = settings.belief_extraction_prompt_version
    system_prompt = get_belief_extraction_prompt(prompt_version)
    
    entries_text = "\n\n".join([f"Entry ID: {e['entry_id']}\nText: {e.get('raw_text', '')}" for e in entries])
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please extract beliefs and values from these entries:\n\n{entries_text}"}
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
                beliefs_data = data
            else:
                beliefs_data = data.get("beliefs", [])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {content}")
            raise ValueError(f"LLM returned malformed JSON: {e}")
            
        extracted_beliefs = []
        entry_dict = {e["entry_id"]: e for e in entries}
        
        metrics = {
            "beliefs_rejected_validation": 0,
            "beliefs_extracted": 0,
        }
        
        for b in beliefs_data:
            try:
                e_id = b.get("entry_id")
                if e_id not in entry_dict:
                    logger.warning(f"Rejected belief with unknown entry_id: {e_id}")
                    metrics["beliefs_rejected_validation"] += 1
                    continue
                    
                evidence_text = b.get("evidence", "")
                raw_text = entry_dict[e_id].get("raw_text", "")
                if evidence_text not in raw_text:
                    logger.warning(f"Rejected belief due to hallucinated evidence: '{evidence_text}' not in '{raw_text}'")
                    metrics["beliefs_rejected_validation"] += 1
                    continue

                user_id = str(entry_dict[e_id].get("user_id", "unknown"))

                belief_id = f"bel-{uuid.uuid4()}"
                
                evidence = BeliefEvidence(
                    entry_id=e_id,
                    quote=evidence_text
                )

                belief = BeliefDocument(
                    belief_id=belief_id,
                    user_id=user_id,
                    statement=b["statement"],
                    belief_type=BeliefType(b["belief_type"]),
                    domain=b.get("domain", "General"),
                    confidence=float(b.get("confidence", 0.0)),
                    confirmed_by_user=None,
                    evidence=[evidence],
                    extraction_version=prompt_version,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                extracted_beliefs.append(belief)
                metrics["beliefs_extracted"] += 1
            except Exception as e:
                logger.warning(f"Failed to validate belief {b}: {e}")
                metrics["beliefs_rejected_validation"] += 1
                
        return extracted_beliefs, metrics
        
    except Exception as e:
        logger.error(f"Error during belief extraction: {e}")
        raise e

async def process_belief_extractions(user_id: Optional[str] = None, limit: Optional[int] = None):
    """
    Finds unextracted entries, extracts beliefs, and upserts the beliefs collection.
    If user_id is provided, only processes entries for that specific user.
    """
    entries_col = get_entries_collection()
    beliefs_col = get_beliefs_collection()
    
    query = {"synthesis.beliefs_extracted_at": None}
    if user_id:
        query["user_id"] = user_id
        
    cursor = entries_col.find(query)
    if limit is not None:
        cursor = cursor.limit(limit)
    
    entries_by_user = {}
    async for entry in cursor:
        if not entry.get("raw_text") or not entry.get("user_id") or not entry.get("entry_id"):
            continue
        u_id = entry["user_id"]
        if u_id not in entries_by_user:
            entries_by_user[u_id] = []
        entries_by_user[u_id].append(entry)
        
    processed_count = 0
    now = datetime.utcnow()
    
    global_metrics = {
        "entries_processed": 0,
        "beliefs_extracted": 0,
        "entries_with_no_beliefs": 0,
        "beliefs_rejected_validation": 0,
        "beliefs_inserted": 0,
        "beliefs_clustered": 0,
        "api_failures": 0,
        "validation_failures": 0
    }
    
    for u_id, user_entries in entries_by_user.items():
        chunk_size = 10
        # Fetch existing beliefs once per user to cluster against
        existing_beliefs = await beliefs_col.find({"user_id": u_id}).to_list(length=None)
        
        for i in range(0, len(user_entries), chunk_size):
            batch = user_entries[i:i+chunk_size]
            
            try:
                beliefs, batch_metrics = await extract_beliefs_for_entries(batch)
                global_metrics["beliefs_extracted"] += batch_metrics["beliefs_extracted"]
                global_metrics["beliefs_rejected_validation"] += batch_metrics["beliefs_rejected_validation"]
                if not beliefs:
                    global_metrics["entries_with_no_beliefs"] += len(batch)
            except ValueError as e:
                logger.error(f"Validation/Client error processing batch for user {u_id}: {e}")
                global_metrics["validation_failures"] += 1
                beliefs = [] 
            except Exception as e:
                logger.error(f"API/Server error processing batch for user {u_id}: {e}")
                global_metrics["api_failures"] += 1
                continue
                
            if beliefs:
                operations = []
                for belief in beliefs:
                    embedding = await generate_embedding(belief.statement)
                    belief.embedding = embedding
                    
                    best_match = None
                    best_score = 0.0
                    
                    for existing in existing_beliefs:
                        if not existing.get("embedding"):
                            continue
                        score = cosine_similarity(embedding, existing["embedding"])
                        if score > best_score:
                            best_score = score
                            best_match = existing
                            
                    SIMILARITY_THRESHOLD = 0.85
                    
                    if best_match and best_score >= SIMILARITY_THRESHOLD:
                        # Cluster with existing belief
                        evidence_dict = belief.evidence[0].model_dump()
                        existing_entry_ids = [e["entry_id"] for e in best_match.get("evidence", [])]
                        
                        if evidence_dict["entry_id"] not in existing_entry_ids:
                            best_match.setdefault("evidence", []).append(evidence_dict)
                            operations.append(
                                UpdateOne(
                                    {"belief_id": best_match["belief_id"]},
                                    {
                                        "$push": {"evidence": evidence_dict},
                                        "$set": {"updated_at": now}
                                    }
                                )
                            )
                            global_metrics["beliefs_clustered"] += 1
                    else:
                        # Insert new belief
                        belief_dict = belief.model_dump()
                        belief_dict["belief_type"] = belief.belief_type.value
                        existing_beliefs.append(belief_dict)
                        
                        operations.append(
                            UpdateOne(
                                {
                                    "user_id": belief.user_id, 
                                    "statement": belief.statement,
                                    "domain": belief.domain
                                },
                                {"$setOnInsert": belief_dict},
                                upsert=True
                            )
                        )
                
                if operations:
                    # ordered=True ensures $setOnInsert happens before a potential $push to the same belief in this batch
                    res = await beliefs_col.bulk_write(operations, ordered=True)
                    if res.upserted_count:
                        global_metrics["beliefs_inserted"] += res.upserted_count
                    
            entry_ids = [e["entry_id"] for e in batch]
            await entries_col.update_many(
                {"entry_id": {"$in": entry_ids}},
                {"$set": {"synthesis.beliefs_extracted_at": now}}
            )
            processed_count += len(batch)
            global_metrics["entries_processed"] += len(batch)
            
    if processed_count > 0:
        logger.info(f"✅ Belief extraction complete. Processed {processed_count} entries.")
        logger.info(f"📊 Metrics: {json.dumps(global_metrics)}")
