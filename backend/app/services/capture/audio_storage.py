import os
import shutil
import uuid
from pathlib import Path
from fastapi import UploadFile
from app.core.config import settings

class AudioStorage:
    def __init__(self, upload_dir: str):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file: UploadFile) -> str:
        """
        Saves an uploaded audio file and returns its stored path/URL.
        """
        file_ext = Path(file.filename or "").suffix
        # If no extension is found or it's invalid, we default to the first allowed extension
        if file_ext not in settings.allowed_audio_extensions_list:
            file_ext = ".mp3"

        file_id = str(uuid.uuid4())
        file_name = f"{file_id}{file_ext}"
        file_path = self.upload_dir / file_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # In production this would return an S3 URL. For local dev, return the relative path.
        return str(file_path)

    def delete(self, file_path: str) -> None:
        """
        Deletes the file at the given path if it exists.
        """
        path = Path(file_path)
        if path.exists() and path.is_file():
            path.unlink()

    def exists(self, file_path: str) -> bool:
        """
        Checks if the file exists.
        """
        return Path(file_path).exists()

audio_storage = AudioStorage(settings.upload_dir)
