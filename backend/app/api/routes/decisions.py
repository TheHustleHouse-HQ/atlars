import uuid
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks

from app.api.deps import require_maturity_stage
from app.core.database import get_decisions_collection, get_graph_nodes_collection
from app.models.decision import DecisionCreate, DecisionResponse, DecisionDocument

router = APIRouter(prefix="/decisions", tags=["decisions"])

async def extract_and_map_decision_beliefs(user_id: str, decision_id: str, situation: str, choice: str):
    """
    Background task to extract relationships between a new decision and existing confirmed beliefs.
    """
    from app.core.database import get_beliefs_collection, get_graph_edges_collection
    from app.services.routing.openrouter import generate_json
    import json
    
    beliefs_col = get_beliefs_collection()
    edges_col = get_graph_edges_collection()
    
    # 1. Fetch all confirmed beliefs for the user
    cursor = beliefs_col.find({"user_id": user_id, "confirmed_by_user": True})
    beliefs = await cursor.to_list(length=None)
    
    if not beliefs:
        return
        
    beliefs_text = "\n".join([f"- ID: {b['belief_id']} | Belief: {b['statement']}" for b in beliefs])
    
    # 2. Use LLM to find which beliefs influenced this decision
    prompt = f"""
    You are an AI assistant analyzing a user's decisions against their confirmed core beliefs.
    
    USER'S DECISION:
    Situation: {situation}
    Choice: {choice}
    
    USER'S CONFIRMED BELIEFS:
    {beliefs_text}
    
    Which of the user's beliefs likely influenced or drove this decision?
    Select only the explicitly relevant beliefs. It is okay if no beliefs apply.
    
    Return a JSON object with a list of influenced_belief_ids.
    Example: {{"influenced_belief_ids": ["uuid-1", "uuid-2"]}}
    """
    
    schema = {
        "type": "object",
        "properties": {
            "influenced_belief_ids": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["influenced_belief_ids"]
    }
    
    response = await generate_json(
        messages=[{"role": "user", "content": prompt}],
        schema=schema,
        model="gpt-4o-mini", # cheap/fast model for simple mapping
        temperature=0.1
    )
    
    if not response or "influenced_belief_ids" not in response:
        return
        
    influenced_ids = response["influenced_belief_ids"]
    
    # 3. Create edges in the graph
    now = datetime.utcnow()
    edge_operations = []
    from pymongo import UpdateOne
    
    for b_id in influenced_ids:
        # Verify the belief ID is valid
        if any(b["belief_id"] == b_id for b in beliefs):
            edge_key = f"{b_id}:influenced:{decision_id}"
            edge_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{user_id}_{edge_key}"))
            
            edge_operations.append(
                UpdateOne(
                    {"edge_id": edge_id},
                    {
                        "$setOnInsert": {
                            "edge_id": edge_id,
                            "user_id": user_id,
                            "from_id": b_id,
                            "to_id": decision_id,
                            "type": "influenced",
                            "date": now,
                            "source_entry_id": decision_id
                        },
                        "$inc": {
                            "weight": 1
                        }
                    },
                    upsert=True
                )
            )
            
    if edge_operations:
        await edges_col.bulk_write(edge_operations)

@router.post("/", response_model=DecisionResponse)
async def create_decision(
    decision_create: DecisionCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_maturity_stage("extraction"))
):
    user_id = current_user["user_id"]
    decisions_col = get_decisions_collection()
    nodes_col = get_graph_nodes_collection()
    
    decision_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    doc = DecisionDocument(
        decision_id=decision_id,
        user_id=user_id,
        situation=decision_create.situation,
        options=decision_create.options,
        choice=decision_create.choice,
        reasoning=decision_create.reasoning,
        outcome=decision_create.outcome,
        timestamp=now
    )
    
    await decisions_col.insert_one(doc.model_dump())
    
    # Create Graph Node for the Decision
    await nodes_col.update_one(
        {"node_id": decision_id},
        {
            "$setOnInsert": {
                "node_id": decision_id,
                "user_id": user_id,
                "type": "decision",
                "first_mentioned": now,
                "created_at": now
            },
            "$set": {
                "label": doc.choice[:50] + ("..." if len(doc.choice) > 50 else ""),
                "normalized_label": doc.choice.lower()[:50],
                "last_mentioned": now,
                "metadata": {"situation": doc.situation, "reasoning": doc.reasoning}
            },
            "$inc": {
                "mention_count": 1
            }
        },
        upsert=True
    )
    
    # Map beliefs to this decision in background
    background_tasks.add_task(
        extract_and_map_decision_beliefs, 
        user_id, 
        decision_id, 
        doc.situation, 
        doc.choice
    )
    
    return doc

@router.get("/", response_model=List[DecisionResponse])
async def get_decisions(current_user: dict = Depends(require_maturity_stage("extraction"))):
    user_id = current_user["user_id"]
    decisions_col = get_decisions_collection()
    
    cursor = decisions_col.find({"user_id": user_id}).sort("timestamp", -1)
    decisions = await cursor.to_list(length=None)
    
    return decisions
