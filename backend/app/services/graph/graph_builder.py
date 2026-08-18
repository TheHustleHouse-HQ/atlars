import logging
import uuid
from typing import Dict, Any
from datetime import datetime
from pymongo import UpdateOne
from app.core.database import get_graph_nodes_collection, get_graph_edges_collection, get_entries_collection

logger = logging.getLogger(__name__)

async def build_graph_from_semantics(
    user_id: str,
    entry_id: str,
    filtered_extractions: Dict[str, Any],
    node_id_map: Dict[str, str]
) -> None:
    """
    Takes the resolved and filtered extractions and builds the graph by upserting
    nodes and edges into the database.
    """
    now = datetime.utcnow()
    nodes_col = get_graph_nodes_collection()
    edges_col = get_graph_edges_collection()
    entries_col = get_entries_collection()
    
    # 1. Update Entry Classifications
    classifications = filtered_extractions.get("classifications", {})
    if classifications:
        await entries_col.update_one(
            {"entry_id": entry_id},
            {"$set": {"classifications": classifications}}
        )

    # 2. Upsert Nodes
    node_operations = []
    processed_texts = set()
    
    entities = filtered_extractions.get("entities", {})
    for ent_type, ent_list in entities.items():
        for ent in ent_list:
            text = ent.get("text", "")
            if not text or text in processed_texts:
                continue
            processed_texts.add(text)
            
            normalized_label = text.lower().strip()
            node_id = node_id_map.get(normalized_label)
            if not node_id:
                continue
                
            node_operations.append(
                UpdateOne(
                    {"node_id": node_id},
                    {
                        "$setOnInsert": {
                            "node_id": node_id,
                            "user_id": user_id,
                            "type": ent_type,
                            "label": text,
                            "normalized_label": normalized_label,
                            "first_mentioned": now,
                            "created_at": now,
                            "metadata": {}
                        },
                        "$set": {
                            "last_mentioned": now
                        },
                        "$inc": {
                            "mention_count": 1
                        }
                    },
                    upsert=True
                )
            )
            
    if node_operations:
        await nodes_col.bulk_write(node_operations)
        logger.info(f"Upserted {len(node_operations)} graph nodes for user {user_id}")

    # 3. Upsert Edges
    edge_operations = []
    processed_edges = set()
    
    relations = filtered_extractions.get("relations", {})
    for rel_type, rel_list in relations.items():
        for rel in rel_list:
            head_text = ""
            tail_text = ""
            
            if isinstance(rel, tuple) and len(rel) == 2:
                head_text, tail_text = rel
            elif isinstance(rel, dict):
                head_text = rel.get("head", {}).get("text", "")
                tail_text = rel.get("tail", {}).get("text", "")
                
            head_id = node_id_map.get(head_text.lower().strip())
            tail_id = node_id_map.get(tail_text.lower().strip())
            
            if not head_id or not tail_id:
                continue
                
            # Prevent duplicate edge upserts in the same batch
            edge_key = f"{head_id}:{rel_type}:{tail_id}"
            if edge_key in processed_edges:
                continue
            processed_edges.add(edge_key)
            
            # Create a deterministic edge ID
            edge_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{user_id}_{edge_key}"))
            
            edge_operations.append(
                UpdateOne(
                    {"edge_id": edge_id},
                    {
                        "$setOnInsert": {
                            "edge_id": edge_id,
                            "user_id": user_id,
                            "from_id": head_id,
                            "to_id": tail_id,
                            "type": rel_type,
                            "date": now,
                            "source_entry_id": entry_id
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
        logger.info(f"Upserted {len(edge_operations)} graph edges for user {user_id}")
