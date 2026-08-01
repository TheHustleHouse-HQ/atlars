import pytest
from unittest.mock import patch, AsyncMock
from fastapi import UploadFile, HTTPException
import io

from app.services.capture.voice_transcription import process_voice_upload
from app.models.entry import EntryStatus, Modality

@pytest.fixture
def user():
    return {"user_id": "test_user_id", "maturity_stage": "baseline"}

@pytest.fixture
def valid_audio():
    file = UploadFile(filename="test.mp3", file=io.BytesIO(b"dummy audio"))
    return file

@pytest.fixture
def invalid_audio():
    file = UploadFile(filename="test.txt", file=io.BytesIO(b"dummy text"))
    return file

@pytest.mark.asyncio
@patch("app.services.capture.voice_transcription.audio_storage")
@patch("app.services.capture.voice_transcription.get_entries_collection")
@patch("app.services.capture.voice_transcription.get_users_collection")
@patch("app.services.capture.voice_transcription.transcribe_audio")
async def test_process_voice_upload_success(mock_transcribe, mock_users, mock_entries, mock_storage, user, valid_audio):
    mock_storage.save.return_value = "uploads/test.mp3"
    
    mock_users_collection = AsyncMock()
    mock_users.return_value = mock_users_collection
    
    mock_entries_collection = AsyncMock()
    mock_entries.return_value = mock_entries_collection

    response = await process_voice_upload(user, valid_audio)

    assert response["status"] == EntryStatus.PENDING
    assert response["modality"] == Modality.VOICE
    
    mock_storage.save.assert_called_once_with(valid_audio)
    mock_transcribe.delay.assert_called_once_with(response["entry_id"])

@pytest.mark.asyncio
async def test_process_voice_upload_invalid_type(user, invalid_audio):
    with pytest.raises(HTTPException) as exc:
        await process_voice_upload(user, invalid_audio)
    assert exc.value.status_code == 415
