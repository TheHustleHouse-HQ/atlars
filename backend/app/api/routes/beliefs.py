from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from app.api.deps import require_maturity_stage
from app.core.database import get_beliefs_collection
from app.models.belief import BeliefResponse, BeliefUpdate

router = APIRouter(prefix="/beliefs", tags=["beliefs"])

@router.get("/", response_model=List[BeliefResponse])
async def get_beliefs(
    status: Optional[str] = Query(None, description="Filter by status: 'confirmed', 'rejected', 'pending'"),
    current_user: dict = Depends(require_maturity_stage("extraction"))
):
    """
    Returns the user's beliefs. 
    If no status is provided, returns all beliefs.
    Use status='pending' for the review queue.
    """
    user_id = current_user["user_id"]
    beliefs_col = get_beliefs_collection()
    
    query = {"user_id": user_id}
    if status == "confirmed":
        query["confirmed_by_user"] = True
    elif status == "rejected":
        query["confirmed_by_user"] = False
    elif status == "pending":
        query["confirmed_by_user"] = None
        
    cursor = beliefs_col.find(query).sort("updated_at", -1)
    beliefs = await cursor.to_list(length=None)
    
    return beliefs

@router.patch("/{belief_id}", response_model=BeliefResponse)
async def update_belief(
    belief_id: str,
    belief_update: BeliefUpdate,
    current_user: dict = Depends(require_maturity_stage("extraction"))
):
    """
    Updates a belief. 
    Use this for confirmation (confirmed_by_user=True), rejection (confirmed_by_user=False), 
    or editing the statement (statement="New statement").
    """
    user_id = current_user["user_id"]
    beliefs_col = get_beliefs_collection()
    
    # Verify belief exists and belongs to user
    belief = await beliefs_col.find_one({"belief_id": belief_id, "user_id": user_id})
    if not belief:
        raise HTTPException(status_code=404, detail="Belief not found")
        
    update_data = {}
    if belief_update.statement is not None:
        update_data["statement"] = belief_update.statement
    if belief_update.confirmed_by_user is not None:
        update_data["confirmed_by_user"] = belief_update.confirmed_by_user
        
    if not update_data:
        return belief
        
    update_data["updated_at"] = datetime.utcnow()
    
    await beliefs_col.update_one(
        {"belief_id": belief_id},
        {"$set": update_data}
    )
    
    # If confirming the belief, create/update a graph node
    if update_data.get("confirmed_by_user") is True:
        from app.core.database import get_graph_nodes_collection
        from pymongo import UpdateOne
        nodes_col = get_graph_nodes_collection()
        statement = update_data.get("statement", belief.get("statement", ""))
        domain = belief.get("domain", "general")
        now = datetime.utcnow()
        
        await nodes_col.update_one(
            {"node_id": belief_id},
            {
                "$setOnInsert": {
                    "node_id": belief_id,
                    "user_id": user_id,
                    "type": "belief",
                    "first_mentioned": now,
                    "created_at": now
                },
                "$set": {
                    "label": statement,
                    "normalized_label": statement.lower(),
                    "last_mentioned": now,
                    "metadata": {"belief_id": belief_id, "domain": domain}
                },
                "$inc": {
                    "mention_count": 1
                }
            },
            upsert=True
        )
    # If rejecting, we might want to remove the node, but for now we'll just leave it or maybe it's better to remove it.
    elif update_data.get("confirmed_by_user") is False:
        from app.core.database import get_graph_nodes_collection
        nodes_col = get_graph_nodes_collection()
        await nodes_col.delete_one({"node_id": belief_id, "user_id": user_id})
    
    # Fetch and return the updated belief
    updated_belief = await beliefs_col.find_one({"belief_id": belief_id})
    return updated_belief
@router.post("/extract")
async def run_belief_extractor(current_user: dict = Depends(require_maturity_stage("extraction"))):
    """
    Manually triggers the belief extraction pipeline for the current user's unextracted entries.
    Extracts up to 15 entries in one request for testing purposes.
    """
    user_id = current_user["user_id"]
    from app.services.synthesis.belief_extraction import process_belief_extractions
    
    # Run the extraction specifically for this user with a limit of 15
    await process_belief_extractions(user_id=user_id, limit=15)
    
    return {"message": f"Belief extraction triggered successfully for up to 15 entries for user {user_id}"}
