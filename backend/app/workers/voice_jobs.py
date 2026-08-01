from datetime import datetime
from app.workers.celery_app import celery_app
from app.core.database import get_entries_collection, connect_db, close_db
from app.models.entry import EntryStatus
from app.services.capture.transcription import get_transcription_provider
from app.services.capture.audio_storage import audio_storage
from app.workers.daily_jobs import embed_entry
import asyncio

@celery_app.task(name="transcribe_audio", queue="voice", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def transcribe_audio(entry_id: str):
    """
    Event-driven worker task to transcribe an audio entry.
    """
    # We must run DB calls synchronously inside celery, or use async event loops.
    # Assuming `get_entries_collection()` returns a Motor collection, we need asyncio.run
    # Let's write an async helper to handle this since Motor is async.
    asyncio.run(_process_transcription(entry_id))

async def _process_transcription(entry_id: str):
    await connect_db()
    try:
        entries_collection = get_entries_collection()
        
        # Fetch entry
        entry = await entries_collection.find_one({"entry_id": entry_id})
        if not entry:
            return
        
        # Idempotency check
        if entry.get("status") == EntryStatus.COMPLETED.value:
            return

        # Update to TRANSCRIBING
        now = datetime.utcnow()
        await entries_collection.update_one(
            {"entry_id": entry_id},
            {"$set": {
                "status": EntryStatus.TRANSCRIBING.value,
                "transcription_started_at": now
            }}
        )

        audio_url = entry.get("audio_url")
        provider = get_transcription_provider()

        try:
            # Transcribe
            result = provider.transcribe(audio_url)
            
            # Update on success
            await entries_collection.update_one(
                {"entry_id": entry_id},
                {"$set": {
                    "raw_text": result["text"],
                    "word_timestamps": result.get("words", []),
                    "status": EntryStatus.COMPLETED.value,
                    "transcription_completed_at": datetime.utcnow()
                }}
            )
            
            # Enqueue next pipeline step
            embed_entry.delay(entry_id)

        except Exception as e:
            # Update on permanent failure
            await entries_collection.update_one(
                {"entry_id": entry_id},
                {"$set": {
                    "status": EntryStatus.FAILED.value,
                    "transcription_error": str(e)
                }}
            )
            # Cleanup orphaned file
            if audio_url:
                audio_storage.delete(audio_url)
            raise e  # Reraise so Celery knows it failed and can retry if applicable
    finally:
        await close_db()
