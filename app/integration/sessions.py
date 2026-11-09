# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ENCRYPTED LOCAL BROWSER SESSIONS
# Persist opaque cookie associations without exposing provider tokens to JavaScript.
# ==============================================

"""SQLite belongs to the isolated host; business data remains in PostgreSQL."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Use parameterized SQLite and authenticated encryption for local session custody.
# ==============================================

import asyncio
import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from cryptography.fernet import (
    Fernet,
    InvalidToken,
)

# ==============================================
# BROWSERSESSIONS
# Store encrypted provider tokens behind random, hashed HttpOnly cookie IDs.
# ==============================================


class BrowserSessions:
    """Store encrypted provider tokens behind random, hashed HttpOnly cookie IDs."""

    # ==============================================
    # INIT
    # Require an already owned private directory; create no business schema.
    # ==============================================

    def __init__(self, *, path: Path, key: str) -> None:
        """Require an already owned private directory; create no business schema."""
        self.path = path
        self.cipher = Fernet(key.encode("ascii"))
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS browser_sessions (digest TEXT PRIMARY KEY, payload BLOB NOT NULL, expires INTEGER NOT NULL)"
            )
            columns = connection.execute(
                "PRAGMA table_info(browser_sessions)"
            ).fetchall()
            if [(row[1], row[2]) for row in columns] != [
                ("digest", "TEXT"),
                ("payload", "BLOB"),
                ("expires", "INTEGER"),
            ]:
                raise RuntimeError("browser_session_schema_mismatch")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS enrollment_drafts (owner TEXT PRIMARY KEY, payload BLOB NOT NULL, expires INTEGER NOT NULL)"
            )

    # ==============================================
    # PRIVATE ACCOUNT-SCOPED FORM RECOVERY
    # Store only validated enrollment text for thirty minutes, separately from credentials.
    # ==============================================

    def _draft(
        self, *, owner: str, payload: str | None, delete: bool
    ) -> dict[str, object] | None:
        """Purge expired drafts on access; encrypt content and hash issuer/subject ownership.

        The route validates the closed enrollment contract and the current account
        before calling this private store. No binary, password, consent or command
        is accepted; restoring a draft never submits any business operation.
        """
        digest = hashlib.sha256(owner.encode()).hexdigest()
        now = int(time.time())
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "DELETE FROM enrollment_drafts WHERE expires <= ?", (now,)
            )
            if delete:
                connection.execute(
                    "DELETE FROM enrollment_drafts WHERE owner=?", (digest,)
                )
                return None
            if payload is not None:
                connection.execute(
                    "INSERT INTO enrollment_drafts VALUES (?,?,?) ON CONFLICT(owner) DO UPDATE SET payload=excluded.payload,expires=excluded.expires",
                    (digest, self.cipher.encrypt(payload.encode()), now + 1800),
                )
            row = connection.execute(
                "SELECT payload,expires FROM enrollment_drafts WHERE owner=?", (digest,)
            ).fetchone()
        if row is None:
            return None
        try:
            return {
                "fields": json.loads(self.cipher.decrypt(row[0])),
                "expires_at": row[1],
            }
        except (InvalidToken, ValueError, UnicodeError):
            return None

    # ==============================================
    # NONBLOCKING DRAFT CUSTODY
    # Keep SQLite out of the event loop and expose no token or session identifier.
    # ==============================================

    async def draft(
        self, *, owner: str, payload: str | None = None, delete: bool = False
    ) -> dict[str, object] | None:
        """Read, explicitly save or explicitly delete the authenticated account's draft."""
        return await asyncio.to_thread(
            self._draft, owner=owner, payload=payload, delete=delete
        )

    # ==============================================
    # WRITE
    # Atomically retain one encrypted session and discard only expired sessions.
    # ==============================================

    def _write(self, *, identifier: str, payload: str, expires: int) -> None:
        """Atomically retain one encrypted session and discard only expired sessions."""
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "DELETE FROM browser_sessions WHERE expires <= ?", (int(time.time()),)
            )
            connection.execute(
                "INSERT INTO browser_sessions VALUES (?,?,?)",
                (
                    hashlib.sha256(identifier.encode()).hexdigest(),
                    self.cipher.encrypt(payload.encode()),
                    expires,
                ),
            )

    # ==============================================
    # CREATE
    # Persist before issuing a browser cookie; a failure grants no session.
    # ==============================================

    async def create(self, *, tokens: dict[str, object], expires: int) -> str:
        """Persist before issuing a browser cookie; a failure grants no session."""
        if (
            set(tokens) != {"access_token", "refresh_token"}
            or not isinstance(tokens["access_token"], str)
            or not tokens["access_token"]
            or not isinstance(tokens["refresh_token"], str)
            or type(expires) is not int
            or expires <= int(time.time())
        ):
            raise ValueError("invalid_browser_session_record")
        identifier = secrets.token_urlsafe(32)
        await asyncio.to_thread(
            self._write,
            identifier=identifier,
            payload=json.dumps(tokens),
            expires=expires,
        )
        return identifier

    # ==============================================
    # READ
    # Return only a live decrypted record identified by its opaque digest.
    # ==============================================

    def _read(self, *, identifier: str) -> dict[str, object] | None:
        """Return only a live decrypted record identified by its opaque digest."""
        if len(identifier) != 43:
            return None
        with closing(sqlite3.connect(self.path)) as connection, connection:
            row = connection.execute(
                "SELECT payload FROM browser_sessions WHERE digest=? AND expires>?",
                (hashlib.sha256(identifier.encode()).hexdigest(), int(time.time())),
            ).fetchone()
        if row is None:
            return None
        try:
            data = json.loads(self.cipher.decrypt(row[0]))
        except (InvalidToken, ValueError, UnicodeError):
            return None
        if (
            not isinstance(data, dict)
            or set(data) != {"access_token", "refresh_token"}
            or not all(isinstance(value, str) for value in data.values())
        ):
            return None
        return data

    # ==============================================
    # READ
    # Keep filesystem IO out of the event loop and never return expired tokens.
    # ==============================================

    async def read(self, *, identifier: str) -> dict[str, object] | None:
        """Keep filesystem IO out of the event loop and never return expired tokens."""
        return await asyncio.to_thread(self._read, identifier=identifier)

    # ==============================================
    # DELETE
    # Invalidate one browser session, retaining all business and identity data.
    # ==============================================

    def _delete(self, *, identifier: str) -> None:
        """Invalidate one browser session, retaining all business and identity data."""
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "DELETE FROM browser_sessions WHERE digest=?",
                (hashlib.sha256(identifier.encode()).hexdigest(),),
            )

    # ==============================================
    # DELETE
    # Commit local logout independently of provider availability.
    # ==============================================

    async def delete(self, *, identifier: str) -> None:
        """Commit local logout independently of provider availability."""
        await asyncio.to_thread(self._delete, identifier=identifier)
