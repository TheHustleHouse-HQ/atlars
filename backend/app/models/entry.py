from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from pydantic import BaseModel


class Modality(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    DECISION = "decision"
    MICRO = "micro"


class EntryCreate(BaseModel):
    raw_text: str
    modality: Modality = Modality.TEXT
    session_id: Optional[str] = None


class EntryUpdate(BaseModel):
    raw_text: str


class EntryResponse(BaseModel):
    entry_id: str
    raw_text: str
    modality: Modality
    timestamp: datetime
    session_id: Optional[str] = None
    embedding_generated_at: Optional[datetime] = None
    audio_url: Optional[str] = None
    word_timestamps: Optional[List[Dict]] = None
    compression_tier: str


class PaginatedEntriesResponse(BaseModel):
    entries: List[EntryResponse]
    next_cursor: Optional[str] = None


class EntryInDB(BaseModel):
    entry_id: str
    user_id: str
    raw_text: str
    timestamp: datetime
    modality: Modality
    session_id: Optional[str] = None
    embedding: Optional[List[float]] = None
    embedding_generated_at: Optional[datetime] = None
    audio_url: Optional[str] = None
    word_timestamps: Optional[List[Dict]] = None
    compression_tier: str
    compression_candidate_id: Optional[str] = None
    maturity_stage_at_capture: str
