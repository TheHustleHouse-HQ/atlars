from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import get_current_user, require_maturity_stage
from app.core.database import get_graph_nodes_collection, get_graph_edges_collection

router = APIRouter(prefix="/graph", tags=["graph"])

class NodeResponse(BaseModel):
    node_id: str
    type: str
    label: str
    normalized_label: str
    mention_count: int  
    first_mentioned: datetime
    last_mentioned: datetime
    created_at: datetime
    metadata: Optional[dict] = None

class EdgeResponse(BaseModel):
    edge_id: str
    from_id: str
    to_id: str
    type: str
    weight: int
    date: datetime
    source_entry_id: str

@router.get("/nodes", response_model=List[NodeResponse])
async def get_nodes(
    type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(require_maturity_stage("extraction"))
):
    nodes_col = get_graph_nodes_collection()
    query = {"user_id": current_user["user_id"]}
    if type:
        query["type"] = type
        
    cursor = nodes_col.find(query).sort("mention_count", -1).limit(limit)
    nodes = await cursor.to_list(length=limit)
    return nodes

@router.get("/edges", response_model=List[EdgeResponse])
async def get_edges(
    type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    from_id: Optional[str] = None,
    to_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(require_maturity_stage("extraction"))
):
    edges_col = get_graph_edges_collection()
    query = {"user_id": current_user["user_id"]}
    if type:
        query["type"] = type
    if from_id:
        query["from_id"] = from_id
    if to_id:
        query["to_id"] = to_id
        
    if from_date or to_date:
        date_query = {}
        if from_date:
            date_query["$gte"] = from_date
        if to_date:
            date_query["$lte"] = to_date
        query["date"] = date_query
        
    cursor = edges_col.find(query).sort("weight", -1).limit(limit)
    edges = await cursor.to_list(length=limit)
    return edges

@router.post("/run-extraction")
async def run_extraction(
    current_user: dict = Depends(get_current_user)
):
    """
    Manually triggers the graph extraction pipeline for testing purposes.
    Processes all entries for the current user that haven't been extracted yet.
    """
    from app.services.graph.entity_extraction import extract_semantics
    from app.services.graph.entity_resolution import resolve_entities
    from app.services.graph.graph_builder import build_graph_from_semantics
    from app.core.database import get_entries_collection
    import logging
    
    logger = logging.getLogger(__name__)
    entries_col = get_entries_collection()
    now = datetime.utcnow()
    user_id = current_user["user_id"]
    
    # Find entries for this user that haven't been processed yet
    cursor = entries_col.find({
        "user_id": user_id, 
        "synthesis.graph_extracted_at": None
    })
    
    processed_count = 0
    async for entry in cursor:
        raw_text = entry.get("raw_text")
        if not raw_text:
            continue
            
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
        
    logger.info(f"✅ Manual graph extraction complete. Processed {processed_count} entries for user {user_id}.")
    return {"message": "Manual extraction complete", "processed_count": processed_count}


@router.post("/query")
async def query_graph(
    query: str,
    current_user: dict = Depends(get_current_user)
):
    # Phase 2.1 placeholder for natural language graph queries
    return {"message": "Natural language graph querying coming soon", "query": query}
