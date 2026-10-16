# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Security regressions for authenticated encryption and action contracts."""

import base64

import pytest
from cryptography.fernet import (
    Fernet,
    InvalidToken,
)

from app.agent.executor.actions import BaseAction
from app.core.security import (
    decrypt_data,
    encrypt_data,
)

# ==============================================
# AUTHENTICATED ENCRYPTION
# ==============================================


def test_encryption_round_trip_preserves_unicode_and_randomizes_tokens() -> None:
    """The plaintext remains confidential and repeated encryption is randomized."""
    key = Fernet.generate_key().decode("ascii")
    plaintext = "MoulAI™ — بيانات خاصة"

    first = encrypt_data(data=plaintext, key=key)
    second = encrypt_data(data=plaintext, key=key)

    assert decrypt_data(encrypted_data=first, key=key) == plaintext
    assert decrypt_data(encrypted_data=second, key=key) == plaintext
    assert first != second
    assert plaintext.encode("utf-8") not in base64.urlsafe_b64decode(first)


def test_decryption_rejects_a_wrong_key_and_modified_ciphertext() -> None:
    """Authentication rejects substitution and corrupted ciphertext."""
    key = Fernet.generate_key().decode("ascii")
    token = encrypt_data(data="private receipt metadata", key=key)
    raw_token = bytearray(base64.urlsafe_b64decode(token))
    raw_token[-1] ^= 1
    altered_token = base64.urlsafe_b64encode(raw_token).decode("ascii")

    with pytest.raises(InvalidToken):
        decrypt_data(
            encrypted_data=token,
            key=Fernet.generate_key().decode("ascii"),
        )
    with pytest.raises(InvalidToken):
        decrypt_data(encrypted_data=altered_token, key=key)


def test_decryption_never_accepts_historical_base64_as_ciphertext() -> None:
    """Encoding without an authentication tag cannot masquerade as encryption."""
    encoded = base64.b64encode(b"historical plaintext").decode("ascii")

    with pytest.raises(InvalidToken):
        decrypt_data(
            encrypted_data=encoded,
            key=Fernet.generate_key().decode("ascii"),
        )


@pytest.mark.parametrize("key", ["", "ordinary signing secret", "not-a-fernet-key"])
def test_encryption_rejects_invalid_keys(key: str) -> None:
    """An application signing secret cannot silently replace the encryption key."""
    with pytest.raises(ValueError):
        encrypt_data(data="confidential", key=key)


def test_encryption_requires_an_explicit_key() -> None:
    """Missing key material fails before any sensitive data can be transformed."""
    with pytest.raises(TypeError):
        encrypt_data(data="confidential")  # type: ignore[call-arg]


# ==============================================
# EXECUTABLE ACTION CONTRACT
# ==============================================


def test_an_action_without_execute_cannot_be_instantiated() -> None:
    """The registry can only receive concrete actions with an execute method."""
    with pytest.raises(TypeError, match="abstract"):
        BaseAction(name="missing-execute")
