from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from pydantic import BaseModel, Field


class Modality(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    DECISION = "decision"
    MICRO = "micro"


class EntryStatus(str, Enum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    COMPLETED = "completed"
    FAILED = "failed"


class SynthesisStatus(BaseModel):
    graph_extracted_at: Optional[datetime] = None
    traits_extracted_at: Optional[datetime] = None
    beliefs_extracted_at: Optional[datetime] = None


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


class VoiceEntryResponse(BaseModel):
    entry_id: str
    modality: Modality
    status: EntryStatus
    timestamp: datetime


class EntryInDB(BaseModel):
    entry_id: str
    user_id: str
    raw_text: str
    timestamp: datetime
    modality: Modality
    status: EntryStatus = EntryStatus.COMPLETED
    session_id: Optional[str] = None
    embedding: Optional[List[float]] = None
    embedding_generated_at: Optional[datetime] = None
    audio_url: Optional[str] = None
    word_timestamps: Optional[List[Dict]] = None
    compression_tier: str
    compression_candidate_id: Optional[str] = None
    maturity_stage_at_capture: str
    transcription_started_at: Optional[datetime] = None
    transcription_completed_at: Optional[datetime] = None
    transcription_error: Optional[str] = None
    synthesis: SynthesisStatus = Field(default_factory=SynthesisStatus)
