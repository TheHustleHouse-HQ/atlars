from typing import Optional
from fastapi import APIRouter, Depends, Query, status, UploadFile, File, Form

from app.api.deps import get_current_user
from app.models.entry import (
    EntryCreate, 
    EntryUpdate, 
    EntryResponse, 
    PaginatedEntriesResponse, 
    VoiceEntryResponse,
    Modality
)
from app.services.capture import entry_service
from app.services.capture import voice_transcription


router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("/", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    entry_in: EntryCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit a text entry.
    """
    return await entry_service.create_entry(user=current_user, entry_data=entry_in)


@router.post("/voice", response_model=VoiceEntryResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_voice_entry(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a voice note.
    """
    return await voice_transcription.process_voice_upload(
        user=current_user, 
        audio=audio, 
        session_id=session_id
    )


@router.get("/", response_model=PaginatedEntriesResponse)
async def list_entries(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = None,
    modality: Optional[Modality] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Returns paginated list of user's entries.
    """
    entries, next_cursor = await entry_service.list_entries(
        user=current_user,
        limit=limit,
        cursor=cursor,
        modality=modality
    )
    return PaginatedEntriesResponse(
        entries=[EntryResponse(**entry) for entry in entries],
        next_cursor=next_cursor
    )


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Returns a single entry with all fields including embedding status.
    """
    return await entry_service.get_entry(user=current_user, entry_id=entry_id)


@router.patch("/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: str,
    entry_in: EntryUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Edit an entry's raw_text. Re-triggers embedding generation.
    """
    return await entry_service.update_entry(
        user=current_user,
        entry_id=entry_id,
        entry_update=entry_in
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Permanently deletes the entry and its embedding.
    """
    await entry_service.delete_entry(user=current_user, entry_id=entry_id)
    # 204 requires no response body
    return None
