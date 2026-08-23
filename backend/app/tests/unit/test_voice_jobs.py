import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.workers.voice_jobs import _process_transcription
from app.models.entry import EntryStatus

@pytest.mark.asyncio
@patch("app.workers.voice_jobs.get_entries_collection")
@patch("app.workers.voice_jobs.embed_entry")
@patch("app.workers.voice_jobs.get_transcription_provider")
@patch("app.workers.voice_jobs.connect_db")
@patch("app.workers.voice_jobs.close_db")
async def test_transcription_success(mock_close_db, mock_connect_db, mock_get_provider, mock_embed, mock_get_entries):
    mock_entries_collection = AsyncMock()
    mock_get_entries.return_value = mock_entries_collection
    
    # Mock entry found
    mock_entries_collection.find_one.return_value = {
        "entry_id": "test_id",
        "status": EntryStatus.PENDING.value,
        "audio_url": "test.mp3"
    }
    
    # Mock provider
    mock_provider = MagicMock()
    mock_provider.transcribe.return_value = {"text": "hello", "words": []}
    mock_get_provider.return_value = mock_provider
    
    await _process_transcription("test_id")
    
    # Should be updated twice (TRANSCRIBING, then COMPLETED)
    assert mock_entries_collection.update_one.call_count == 2
    
    # Enqueued embedding
    mock_embed.delay.assert_called_once_with("test_id")

@pytest.mark.asyncio
@patch("app.workers.voice_jobs.get_entries_collection")
@patch("app.workers.voice_jobs.audio_storage")
@patch("app.workers.voice_jobs.get_transcription_provider")
@patch("app.workers.voice_jobs.connect_db")
@patch("app.workers.voice_jobs.close_db")
async def test_transcription_failure(mock_close_db, mock_connect_db, mock_get_provider, mock_audio_storage, mock_get_entries):
    mock_entries_collection = AsyncMock()
    mock_get_entries.return_value = mock_entries_collection
    
    # Mock entry found
    mock_entries_collection.find_one.return_value = {
        "entry_id": "test_id",
        "status": EntryStatus.PENDING.value,
        "audio_url": "test.mp3"
    }
    
    # Mock provider throws error
    mock_provider = MagicMock()
    mock_provider.transcribe.side_effect = Exception("Whisper failed")
    mock_get_provider.return_value = mock_provider
    
    with pytest.raises(Exception):
        await _process_transcription("test_id")
        
    mock_audio_storage.delete.assert_called_once_with("test.mp3")

@pytest.mark.asyncio
@patch("app.workers.voice_jobs.get_entries_collection")
@patch("app.workers.voice_jobs.connect_db")
@patch("app.workers.voice_jobs.close_db")
async def test_transcription_idempotency(mock_close_db, mock_connect_db, mock_get_entries):
    mock_entries_collection = AsyncMock()
    mock_get_entries.return_value = mock_entries_collection
    
    # Mock entry already COMPLETED
    mock_entries_collection.find_one.return_value = {
        "entry_id": "test_id",
        "status": EntryStatus.COMPLETED.value
    }
    
    await _process_transcription("test_id")
    
    # Should not update anything
    assert mock_entries_collection.update_one.call_count == 0
