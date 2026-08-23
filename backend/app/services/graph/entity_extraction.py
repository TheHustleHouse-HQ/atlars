import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    from gliner2 import GLiNER2
    # Load model once at module level
    logger.info("Loading GLiNER2 base model...")
    extractor = GLiNER2.from_pretrained("fastino/gliner2-base-v1")
    logger.info("GLiNER2 loaded successfully.")
    
    # Unified ATLARS Schema
    SCHEMA = (extractor.create_schema()
        .entities({
            "person": "A real person mentioned in the user's life, such as a friend, colleague, family member, mentor, or acquaintance",
            "place": "A physical location where the user or another person went, lives, met, worked, or plans to go",
            "project": "A specific project, product, application, business, or long-term work initiative",
            "event": "A specific activity, occurrence, meeting, trip, activity, or significant event",
            "emotion": "An explicitly expressed emotional state or feeling experienced by the user",
            "belief": "A statement expressing something the user believes, values, assumes, or considers true",
            "goal": "A future objective, intention, aspiration, or outcome the user wants to achieve",
            "phase": "A named period or mode of life such as rebuilding, exploring, grinding, or recovery"
        })
        .relations({
            "worked_on": "Person actively worked on or contributed to a project",
            "introduced": "Person introduced one person to another",
            "met_at": "Person met another person at a place or event",
            "lives_in": "Person currently lives in a place",
            "moved_to": "Person moved or plans to move to a place",
            "felt_toward": "Emotion experienced toward a person",
            "felt_about": "Emotion experienced toward a project or goal",
            "felt_during": "Emotion experienced during an event",
            "helps_with": "Person provides help or contribution toward a project",
            "plays_with": "Person participates in an activity with another person"
        })
        .classification(
            "domains", 
            ["Work", "Relationships", "Health", "Creativity", "Social", "Learning", "Finance", "Meaning"],
            multi_label=True,
            cls_threshold=0.3
        )
        .classification(
            "entry_type",
            ["journal", "decision", "reflection", "relationship", "work", "health", "goal", "belief", "event"]
        )
    )
except ImportError:
    logger.warning("gliner2 is not installed. GLiNER extraction will be skipped.")
    extractor = None
    SCHEMA = None


def extract_semantics(text: str) -> Dict[str, Any]:
    """
    Takes raw entry text and returns a unified dictionary containing:
    - entities (with confidence and spans)
    - relations
    - classifications
    """
    if not extractor or not SCHEMA:
        logger.error("GLiNER2 extractor is not initialized.")
        return {}
        
    try:
        results = extractor.extract(
            text, 
            SCHEMA, 
            include_confidence=True, 
            include_spans=True
        )
        return results
    except Exception as e:
        logger.error(f"GLiNER2 extraction failed: {str(e)}")
        return {}
