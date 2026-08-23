import logging
import uuid
from typing import Dict, Any, Tuple
from app.core.database import get_graph_nodes_collection

logger = logging.getLogger(__name__)

async def _find_canonical_node_id(user_id: str, ent_type: str, normalized_text: str) -> str | None:
    """
    Placeholder for future advanced Entity Resolution (e.g. mapping 'Dave' to 'David', alias resolution).
    Currently performs an exact lookup on the normalized label.
    """
    nodes_col = get_graph_nodes_collection()
    existing_node = await nodes_col.find_one({
        "user_id": user_id,
        "type": ent_type,
        "normalized_label": normalized_text
    })
    
    if existing_node:
        return existing_node["node_id"]
    return None


async def resolve_entities(
    user_id: str, 
    extraction_results: Dict[str, Any], 
    confidence_threshold: float = 0.60
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Takes raw GLiNER2 extraction results, filters out low confidence entities,
    and maps the remaining strings to canonical graph node IDs in the DB.
    
    Returns:
    - filtered_extractions: The same dictionary structure but without low-confidence items.
    - node_id_map: A dictionary mapping NORMALIZED extracted string -> canonical UUID.
    """
    filtered_extractions = {
        "entities": {},
        "relations": {},
        "classifications": extraction_results.get("classifications", {})
    }
    
    # Maps normalized_text -> canonical node_id
    node_id_map = {}
    
    raw_entities = extraction_results.get("entities", {})
    
    # 1. Resolve Entities & Apply Confidence Gates
    for ent_type, ent_list in raw_entities.items():
        filtered_list = []
        for ent in ent_list:
            text = ent.get("text", "")
            confidence = ent.get("confidence", 1.0)
            
            if not text or confidence < confidence_threshold:
                if text:
                    logger.debug(f"Discarding '{text}' due to low confidence ({confidence})")
                continue
                
            filtered_list.append(ent)
            normalized_text = text.lower().strip()
            
            if normalized_text in node_id_map:
                continue
                
            # Entity Resolution
            node_id = await _find_canonical_node_id(user_id, ent_type, normalized_text)
            
            if not node_id:
                node_id = str(uuid.uuid4())
                
            node_id_map[normalized_text] = node_id
                
        if filtered_list:
            filtered_extractions["entities"][ent_type] = filtered_list

    # 2. Filter Relations (Ensure both head and tail passed the confidence gate)
    # GLiNER2 outputs relations under the key 'relation_extraction'
    raw_relations = extraction_results.get("relation_extraction", extraction_results.get("relations", {})) or {}
    for rel_type, rel_list in raw_relations.items():
        filtered_rels = []
        for rel in rel_list:
            if isinstance(rel, tuple) and len(rel) == 2:
                head, tail = rel
                head_norm = head.lower().strip()
                tail_norm = tail.lower().strip()
                if head_norm in node_id_map and tail_norm in node_id_map:
                    filtered_rels.append(rel)
            elif isinstance(rel, dict):
                head_text = rel.get("head", {}).get("text", "")
                tail_text = rel.get("tail", {}).get("text", "")
                head_norm = head_text.lower().strip()
                tail_norm = tail_text.lower().strip()
                if head_norm in node_id_map and tail_norm in node_id_map:
                    filtered_rels.append(rel)
                    
        if filtered_rels:
            filtered_extractions["relations"][rel_type] = filtered_rels

    return filtered_extractions, node_id_map
