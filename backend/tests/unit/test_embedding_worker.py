import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.workers.daily_jobs import _process_embedding

@pytest.fixture
def mock_db():
    with patch("app.workers.daily_jobs.connect_db", new_callable=AsyncMock), \
         patch("app.workers.daily_jobs.close_db", new_callable=AsyncMock), \
         patch("app.workers.daily_jobs.get_entries_collection") as mock_get_collection:
        
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock()
        mock_collection.update_one = AsyncMock()
        mock_get_collection.return_value = mock_collection
        yield mock_collection

@pytest.mark.asyncio
@patch("app.workers.daily_jobs.generate_embedding")
async def test_embed_entry_success(mock_generate_embedding, mock_db):
    entry_id = "test-entry-123"
    mock_db.find_one.return_value = {
        "entry_id": entry_id,
        "raw_text": "This is a journal entry.",
        "embedding": None
    }
    
    mock_generate_embedding.return_value = [0.1, 0.2, 0.3]
    
    await _process_embedding(entry_id)
    
    # Assert entry was fetched
    mock_db.find_one.assert_called_once_with({"entry_id": entry_id})
    
    # Assert embedding was generated
    mock_generate_embedding.assert_called_once_with("This is a journal entry.")
    
    # Assert DB was updated
    mock_db.update_one.assert_called_once()
    update_args = mock_db.update_one.call_args[0]
    assert update_args[0] == {"entry_id": entry_id}
    assert "$set" in update_args[1]
    assert update_args[1]["$set"]["embedding"] == [0.1, 0.2, 0.3]
    assert "embedding_generated_at" in update_args[1]["$set"]


@pytest.mark.asyncio
@patch("app.workers.daily_jobs.generate_embedding")
async def test_embed_entry_empty_text(mock_generate_embedding, mock_db):
    entry_id = "test-entry-empty"
    mock_db.find_one.return_value = {
        "entry_id": entry_id,
        "raw_text": "   ", # Empty or whitespace
        "embedding": None
    }
    
    await _process_embedding(entry_id)
    
    # Embedding generation should be skipped
    mock_generate_embedding.assert_not_called()
    mock_db.update_one.assert_not_called()


@pytest.mark.asyncio
@patch("app.workers.daily_jobs.generate_embedding")
async def test_embed_entry_not_found(mock_generate_embedding, mock_db):
    entry_id = "missing-entry"
    mock_db.find_one.return_value = None
    
    await _process_embedding(entry_id)
    
    # Embedding generation should be skipped
    mock_generate_embedding.assert_not_called()
    mock_db.update_one.assert_not_called()


@pytest.mark.asyncio
@patch("app.workers.daily_jobs.generate_embedding")
async def test_embed_entry_generation_failure(mock_generate_embedding, mock_db):
    entry_id = "test-entry-fail"
    mock_db.find_one.return_value = {
        "entry_id": entry_id,
        "raw_text": "Some text",
        "embedding": None
    }
    
    mock_generate_embedding.return_value = None # Simulating failure
    
    with pytest.raises(Exception, match="Failed to generate embedding"):
        await _process_embedding(entry_id)
        
    # Database shouldn't be updated on failure
    mock_db.update_one.assert_not_called()
