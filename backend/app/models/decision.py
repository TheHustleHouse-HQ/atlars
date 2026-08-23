from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class DecisionCreate(BaseModel):
    situation: str
    options: List[str]
    choice: str
    reasoning: Optional[str] = None
    outcome: Optional[str] = None

class DecisionUpdate(BaseModel):
    situation: Optional[str] = None
    options: Optional[List[str]] = None
    choice: Optional[str] = None
    reasoning: Optional[str] = None
    outcome: Optional[str] = None

class DecisionDocument(BaseModel):
    decision_id: str
    user_id: str
    situation: str
    options: List[str]
    choice: str
    reasoning: Optional[str] = None
    outcome: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class DecisionResponse(DecisionDocument):
    pass
