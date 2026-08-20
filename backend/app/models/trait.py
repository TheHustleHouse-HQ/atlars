from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum
from pydantic import BaseModel, Field

class OceanDimension(str, Enum):
    O = "O"
    C = "C"
    E = "E"
    A = "A"
    N = "N"

class SignalDirection(str, Enum):
    HIGH = "high"
    LOW = "low"

class TraitSignal(BaseModel):
    user_id: str
    ocean_dimension: OceanDimension
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    evidence_type: str = Field(description="The specific category of behavior this evidence represents (e.g., novelty_seeking, planning)")
    entry_id: str
    trait_extraction_version: str = Field(default="1.0", description="The version of the extraction prompt used")
    model: str = Field(default="unknown", description="The LLM model used for extraction")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class TraitCategoryStats(BaseModel):
    high_signals_count: int = 0
    low_signals_count: int = 0
    overall_confidence: float = 0.0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

class TraitDocument(BaseModel):
    user_id: str
    categories: Dict[OceanDimension, TraitCategoryStats] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TraitResponse(BaseModel):
    label: str
    ocean_dimension: str
    direction: str
    confidence: float
    signal_count: int

class TraitListResponse(BaseModel):
    traits: List[TraitResponse]
    is_early_estimate: bool
