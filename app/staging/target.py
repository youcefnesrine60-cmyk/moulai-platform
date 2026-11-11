# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ATTESTED STAGING DATABASE IDENTITY
# Admit the newly created empty Neon project and reject every historical database.
# ==============================================

"""Public target metadata contains no credential and cannot authorize production."""

from __future__ import annotations

# isort: split
# ==============================================
# STRICT TARGET CONTRACT
# Validate both the connection destination and server-reported Neon identity.
# ==============================================

import json
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import (
    Connection,
    make_url,
)

# ==============================================
# CLOSED REMOTE TARGET
# No default DATABASE_URL, branch discovery or production-compatible name is accepted.
# ==============================================


@dataclass(frozen=True, kw_only=True)
class StagingTarget:
    """Bind migration and runtime connections to one synthetic-only project."""

    project_id: str
    branch_id: str
    endpoint_id: str
    host: str
    database: str
    migrator_role: str
    runtime_role: str
    instance_id: str

    # ==============================================
    # CONSTRUCTION ADMISSION
    # The first staging target is intentionally pinned separately from development.
    # ==============================================

    def __post_init__(self) -> None:
        """Reject foreign projects, legacy databases and malformed public markers."""
        if (
            self.project_id != "sparkling-rice-23028300"
            or self.branch_id != "br-lucky-smoke-b9edyxoe"
            or self.endpoint_id != "ep-odd-wildflower-b9wacgg0"
            or self.host != "ep-odd-wildflower-b9wacgg0.c-7.eu-central-1.aws.neon.tech"
            or self.database != "moulai_staging_rehearsal"
            or self.migrator_role != "moulai_staging_migrator"
            or self.runtime_role != "moulai_staging_app"
            or re.fullmatch(r"[0-9a-f]{32}", self.instance_id) is None
        ):
            raise ValueError("staging_target_not_approved")

    # ==============================================
    # PUBLIC MANIFEST LOADING
    # Reject extra fields rather than interpreting unknown deployment instructions.
    # ==============================================

    @classmethod
    def load(cls, *, path: Path) -> StagingTarget:
        """Load the exact public target fields; no credential is read from this file."""
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    # ==============================================
    # URL ADMISSION
    # Role, host, port and database must agree before a driver may connect.
    # ==============================================

    def check_url(self, *, value: str, migration: bool) -> str:
        """Return an asyncpg URL with TLS configured separately, never log it."""
        url = make_url(value)
        role = self.migrator_role if migration else self.runtime_role
        if (
            url.drivername not in {"postgresql", "postgresql+asyncpg"}
            or url.host != self.host
            or url.port not in {None, 5432}
            or url.database != self.database
            or url.username != role
            or not url.password
            or set(url.query) - {"sslmode", "channel_binding"}
            or url.query.get("sslmode", "verify-full") not in {"require", "verify-full"}
        ):
            raise ValueError("staging_connection_target_mismatch")
        return url.set(drivername="postgresql+asyncpg", query={}).render_as_string(
            hide_password=False
        )

    # ==============================================
    # LIVE SERVER IDENTITY
    # A correct URL alone does not prove which project accepted the connection.
    # ==============================================

    def attest(
        self,
        *,
        connection: Connection,
        migration: bool,
        require_marker: bool = True,
        require_revision: bool = False,
    ) -> None:
        """Fail before business IO on a wrong role, branch, endpoint, marker or schema."""
        row = connection.execute(
            text(
                "SELECT current_database(),current_user,"
                "current_setting('neon.project_id',true),"
                "current_setting('neon.branch_id',true),"
                "current_setting('neon.endpoint_id',true),"
                "shobj_description(oid,'pg_database') "
                "FROM pg_database WHERE datname=current_database()"
            )
        ).one()
        if tuple(row[:5]) != (
            self.database,
            self.migrator_role if migration else self.runtime_role,
            self.project_id,
            self.branch_id,
            self.endpoint_id,
        ) or (require_marker and row[5] != "moulai-staging:" + self.instance_id):
            raise RuntimeError("staging_live_database_identity_mismatch")
        if (
            require_revision
            and connection.scalar(
                text("SELECT version_num FROM public.alembic_version")
            )
            != "o520261111"
        ):
            raise RuntimeError("staging_schema_revision_mismatch")
