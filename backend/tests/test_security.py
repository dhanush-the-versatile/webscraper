"""Unit tests: password hashing and JWT lifecycle."""

from __future__ import annotations

import pytest

from app.core.security import (
    JWTError,
    create_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_verify_password_handles_malformed_hash():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_token_pair_claims():
    pair = create_token_pair("user-42", extra_claims={"role": "recruiter"})
    access = decode_token(pair["access_token"])
    refresh = decode_token(pair["refresh_token"])
    assert access["sub"] == "user-42" and access["type"] == "access"
    assert refresh["type"] == "refresh"
    assert access["role"] == "recruiter"
    assert access["jti"] != refresh["jti"]


def test_tampered_token_rejected():
    token = create_token("user-1")
    with pytest.raises(JWTError):
        decode_token(token[:-2] + "xx")
