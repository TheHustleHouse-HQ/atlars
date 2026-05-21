from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


Modality = Literal["text", "voice", "decision", "micro"]
CompressionTier = Literal["hot", "warm", "cold", "permanent"]


class EntryCreate(BaseModel):
    raw_text: str
    modality: Modality
    session_id: str | None = None

    @field_validator("raw_text")
    @classmethod
    def raw_text_not_empty(cls, v: str) -> str:
        text = v.strip()
        if not text:
            raise ValueError("raw_text cannot be empty")
        return text


class EntryResponse(BaseModel):
    entry_id: str
    raw_text: str
    modality: Modality
    timestamp: datetime
    embedding_generated_at: datetime | None = None
    compression_tier: CompressionTier = "hot"


class EntryInDB(BaseModel):
    entry_id: str
    user_id: str
    raw_text: str
    timestamp: datetime
    modality: Modality
    session_id: str | None = None
    embedding: list[float] | None = None
    embedding_generated_at: datetime | None = None
    audio_url: str | None = None
    word_timestamps: list[dict] | None = None
    compression_tier: CompressionTier = "hot"
    compression_candidate_id: str | None = None
    maturity_stage_at_capture: str
