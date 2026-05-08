import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from freezegun import freeze_time

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from jose import JWTError


# ── Password hashing ──────────────────────────────────────────────────────────

def test_hash_and_verify_password():
    hashed = hash_password("mysecretpassword")
    assert verify_password("mysecretpassword", hashed)


def test_wrong_password_fails():
    hashed = hash_password("mysecretpassword")
    assert not verify_password("wrongpassword", hashed)


# ── Access token ──────────────────────────────────────────────────────────────

def test_access_token_contains_user_id():
    token = create_access_token("user-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_access_token_valid_within_expiry():
    with freeze_time("2025-01-01 12:00:00"):
        token = create_access_token("user-123")
    with freeze_time("2025-01-01 12:14:00"):  # 14 minutes later
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"


def test_access_token_expired_after_15_minutes():
    with freeze_time("2025-01-01 12:00:00"):
        token = create_access_token("user-123")
    with freeze_time("2025-01-01 12:16:00"):  # 16 minutes later
        with pytest.raises(JWTError):
            decode_access_token(token)


def test_refresh_token_rejected_as_access_token():
    refresh_token, _ = create_refresh_token("user-123")
    with pytest.raises(JWTError):
        decode_access_token(refresh_token)


# ── Refresh token ─────────────────────────────────────────────────────────────

def test_refresh_token_contains_user_id_and_jti():
    token, token_id = create_refresh_token("user-123")
    payload = decode_refresh_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "refresh"
    assert payload["jti"] == token_id


def test_refresh_token_valid_within_7_days():
    with freeze_time("2025-01-01 12:00:00"):
        token, _ = create_refresh_token("user-123")
    with freeze_time("2025-01-07 11:59:00"):  # just under 7 days
        payload = decode_refresh_token(token)
        assert payload["sub"] == "user-123"


def test_refresh_token_expired_after_7_days():
    with freeze_time("2025-01-01 12:00:00"):
        token, _ = create_refresh_token("user-123")
    with freeze_time("2025-01-09 12:00:00"):  # 8 days later
        with pytest.raises(JWTError):
            decode_refresh_token(token)


def test_access_token_rejected_as_refresh_token():
    token = create_access_token("user-123")
    with pytest.raises(JWTError):
        decode_refresh_token(token)


def test_each_refresh_token_has_unique_jti():
    _, token_id_1 = create_refresh_token("user-123")
    _, token_id_2 = create_refresh_token("user-123")
    assert token_id_1 != token_id_2
