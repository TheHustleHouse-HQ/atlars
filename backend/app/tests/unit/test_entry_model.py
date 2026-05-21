import pytest
from pydantic import ValidationError

from app.models.entry import EntryCreate


def test_entry_create_rejects_empty_raw_text():
    with pytest.raises(ValidationError):
        EntryCreate(raw_text="   ", modality="text")
