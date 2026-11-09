# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNED LOCAL HOST PROCESS LEASE
# Prevent a second launcher from stopping components used by the active local host.
# ==============================================

"""Windows development coordination; the OS releases the lease on process exit."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Local file locking never changes database or provider configuration.
# ==============================================

import msvcrt
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# ==============================================
# NONBLOCKING HOST OWNERSHIP
# One lock byte serializes launchers without trusting a reusable process identifier.
# ==============================================


@contextmanager
def local_host_lease(*, directory: Path) -> Iterator[None]:
    """Refuse a competing host before startup and release only this acquired lease."""
    with (directory / "host.lock").open("a+b") as lease:
        if lease.seek(0, 2) == 0:
            lease.write(b"0")
            lease.flush()
        lease.seek(0)
        try:
            msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError("operational_instance_already_running") from error
        try:
            yield
        finally:
            lease.seek(0)
            msvcrt.locking(lease.fileno(), msvcrt.LK_UNLCK, 1)
