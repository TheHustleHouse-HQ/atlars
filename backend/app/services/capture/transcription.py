import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class TranscriptionProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_url: str) -> Dict[str, Any]:
        """
        Transcribes the audio at the given URL/path.
        Returns a dictionary containing 'text' and 'words' timestamps.
        """
        pass

class MockProvider(TranscriptionProvider):
    def transcribe(self, audio_url: str) -> Dict[str, Any]:
        """
        Returns a realistic WhisperX-like dictionary payload.
        """
        return {
            "text": "Today I worked on ATLARS.",
            "words": [
                {"word": "Today", "start": 0.12, "end": 0.44},
                {"word": "I", "start": 0.45, "end": 0.51},
                {"word": "worked", "start": 0.52, "end": 0.70},
                {"word": "on", "start": 0.71, "end": 0.85},
                {"word": "ATLARS.", "start": 0.86, "end": 1.20}
            ]
        }

class WhisperXProvider(TranscriptionProvider):
    _model = None
    _align_model = None
    _align_metadata = None
    _device = None

    @classmethod
    def load_models(cls):
        if cls._model is not None:
            return

        import torch
        import whisperx
        
        # Determine device
        if settings.whisper_device == "auto":
            cls._device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            cls._device = settings.whisper_device
            
        compute_type = "float16" if cls._device == "cuda" else "int8"
        
        logger.info(f"Loading WhisperX model: {settings.whisper_model} on {cls._device} (compute_type={compute_type})")
        # Load whisperx model
        cls._model = whisperx.load_model(
            settings.whisper_model, 
            cls._device, 
            compute_type=compute_type
        )
        logger.info("WhisperX model loaded successfully.")

    def transcribe(self, audio_url: str) -> Dict[str, Any]:
        if not os.path.exists(audio_url):
            raise FileNotFoundError(f"Audio file not found at path: {audio_url}")

        if WhisperXProvider._model is None:
            WhisperXProvider.load_models()

        import whisperx
        
        start_time = time.time()
        
        # 1. Transcribe
        audio = whisperx.load_audio(audio_url)
        language = settings.whisper_language if settings.whisper_language != "auto" else None
        
        result = WhisperXProvider._model.transcribe(
            audio, 
            batch_size=16, 
            language=language
        )
        
        detected_language = result.get("language", "en")
        
        # 2. Align (load alignment model if needed for this language)
        if WhisperXProvider._align_model is None or getattr(WhisperXProvider, '_last_lang', None) != detected_language:
            logger.info(f"Loading alignment model for language: {detected_language}")
            model_a, metadata = whisperx.load_align_model(
                language_code=detected_language, 
                device=WhisperXProvider._device
            )
            WhisperXProvider._align_model = model_a
            WhisperXProvider._align_metadata = metadata
            WhisperXProvider._last_lang = detected_language
            logger.info("Alignment model loaded successfully.")

        result = whisperx.align(
            result["segments"], 
            WhisperXProvider._align_model, 
            WhisperXProvider._align_metadata, 
            audio, 
            WhisperXProvider._device, 
            return_char_alignments=False
        )

        elapsed = time.time() - start_time
        logger.info(f"Transcribed {len(audio)/16000:.1f}-second audio in {elapsed:.1f} seconds")

        # Map to expected output
        full_text = " ".join([seg["text"].strip() for seg in result["segments"]])
        
        words_out = []
        for segment in result["segments"]:
            for w in segment.get("words", []):
                if "start" in w and "end" in w:
                    words_out.append({
                        "word": w["word"],
                        "start": w["start"],
                        "end": w["end"]
                    })

        return {
            "text": full_text.strip(),
            "words": words_out
        }

def get_transcription_provider() -> TranscriptionProvider:
    if settings.transcription_provider.lower() == "whisperx":
        return WhisperXProvider()
    return MockProvider()
