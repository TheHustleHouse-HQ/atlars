import uuid
from datetime import datetime
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings
from app.core.database import get_entries_collection, get_users_collection
from app.models.entry import EntryInDB, Modality, EntryStatus, VoiceEntryResponse
from app.services.capture.audio_storage import audio_storage
from app.workers.voice_jobs import transcribe_audio

async def process_voice_upload(user: dict, audio: UploadFile, session_id: Optional[str] = None) -> dict:
    """
    Validates audio file, saves it, creates DB entry, and enqueues transcription task.
    """
    # 1. Validate MIME/Extension
    file_ext = (f".{audio.filename.split('.')[-1]}" if "." in (audio.filename or "") else "").lower()
    if file_ext not in settings.allowed_audio_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: {settings.allowed_audio_extensions}"
        )
    
    # 2. Validate File Size
    if audio.size is not None and audio.size > settings.max_audio_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size allowed is {settings.max_audio_size_bytes / (1024 * 1024):.0f} MB."
        )
    # 2. Save Audio
    try:
        audio_url = audio_storage.save(audio)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save audio: {str(e)}")

    # 3. Create MongoDB Entry
    entries_collection = get_entries_collection()
    users_collection = get_users_collection()
    now = datetime.utcnow()

    # Update user metadata
    update_ops = {"$inc": {"entry_count": 1}, "$set": {"last_active_at": now}}
    if not user.get("first_entry_at"):
        update_ops["$set"]["first_entry_at"] = now

    await users_collection.update_one(
        {"user_id": user["user_id"]},
        update_ops
    )

    entry_id = str(uuid.uuid4())
    maturity_stage = user.get("maturity_stage", "baseline")

    entry_in_db = EntryInDB(
        entry_id=entry_id,
        user_id=user["user_id"],
        raw_text="",
        timestamp=now,
        modality=Modality.VOICE,
        status=EntryStatus.PENDING,
        session_id=session_id,
        compression_tier="hot",
        maturity_stage_at_capture=maturity_stage,
        audio_url=audio_url,
    )

    entry_dict = entry_in_db.model_dump()
    await entries_collection.insert_one(entry_dict)

    # 4. Enqueue Job
    transcribe_audio.delay(entry_id)

    # 5. Return Response
    return VoiceEntryResponse(
        entry_id=entry_id,
        modality=entry_in_db.modality,
        status=entry_in_db.status,
        timestamp=entry_in_db.timestamp,
    ).model_dump()
