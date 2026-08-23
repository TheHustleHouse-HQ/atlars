from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field

class BeliefType(str, Enum):
    VALUE = "value"
    BELIEF = "belief"
    PRINCIPLE = "principle"

class BeliefEvidence(BaseModel):
    entry_id: str
    quote: str

class BeliefCreate(BaseModel):
    statement: str
    belief_type: BeliefType
    domain: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[BeliefEvidence]
    extraction_version: str = Field(default="1.0")

class BeliefUpdate(BaseModel):
    statement: Optional[str] = None
    confirmed_by_user: Optional[bool] = None

class BeliefDocument(BaseModel):
    belief_id: str
    user_id: str
    statement: str
    belief_type: BeliefType
    domain: str
    confidence: float = Field(ge=0.0, le=1.0)
    confirmed_by_user: Optional[bool] = None
    evidence: List[BeliefEvidence]
    extraction_version: str
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BeliefResponse(BeliefDocument):
    pass

class ExtractedBelief(BaseModel):
    statement: str
    belief_type: BeliefType
    domain: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    entry_id: str

class BeliefExtractionResponse(BaseModel):
    beliefs: List[ExtractedBelief]
