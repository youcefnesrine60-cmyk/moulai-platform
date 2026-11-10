# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# STAGING OUTBOUND NETWORK ALLOWLIST
# Permit only the pinned staging database and isolated OIDC provider.
# ==============================================

"""Defense in depth in Python; hosting firewall policy remains a deployment check."""

from __future__ import annotations

# isort: split
# ==============================================
# EXPLICIT DESTINATION RESOLUTION
# Resolve approved endpoints before installing the irreversible process audit hook.
# ==============================================

import socket
import sys
from urllib.parse import urlsplit

from app.staging.config import StagingConfig

# ==============================================
# DENY UNRELATED PROVIDER CALLS
# No AI, Telegram, Redis, email or discovered remote hostname is admitted.
# ==============================================


class StagingNetworkGuard:
    """Admit one listener and two TLS destinations, with no DNS expansion at runtime."""

    # ==============================================
    # CONSTRUCTOR
    # Public TLS verification still protects both destinations after DNS resolution.
    # ==============================================

    def __init__(self, *, configuration: StagingConfig, port: int) -> None:
        """Prepare allowed addresses without retaining a connection credential."""
        issuer = urlsplit(configuration.issuer)
        self.hosts = {
            (configuration.target.host, 5432),
            (issuer.hostname, issuer.port or 443),
        }
        self.addresses: set[tuple[str, int]] = set()
        self.port = port
        for hostname, destination_port in self.hosts:
            for record in socket.getaddrinfo(
                hostname, destination_port, type=socket.SOCK_STREAM
            ):
                self.addresses.add((record[4][0], destination_port))

    # ==============================================
    # AUDIT CALLBACK
    # Preserve Python's callback signature and allow only its internal socketpair helper.
    # ==============================================

    def __call__(self, event: str, arguments: tuple[object, ...]) -> None:
        """Reject unknown DNS, outbound traffic, datagrams and unrelated binds."""
        if not event.startswith("socket."):
            return
        if event in {"socket.__new__", "socket.gethostname"}:
            return
        frame = sys._getframe(1)
        while frame is not None:
            if (
                frame.f_code.co_filename == socket.__file__
                and frame.f_code.co_name in {"socketpair", "_fallback_socketpair"}
            ):
                return
            frame = frame.f_back
        if event == "socket.getaddrinfo":
            if (arguments[0], int(arguments[1] or 0)) in self.hosts:
                return
        elif event == "socket.connect":
            destination = arguments[1]
            if isinstance(destination, tuple) and destination[:2] in self.addresses:
                return
        elif event == "socket.bind":
            destination = arguments[1]
            if isinstance(destination, tuple) and destination[:2] == (
                "0.0.0.0",
                self.port,
            ):
                return
        else:
            # Accept ordinary socket lifecycle operations; reject address-discovery and datagrams.
            if event not in {
                "socket.sendto",
                "socket.sendmsg",
                "socket.gethostbyname",
                "socket.gethostbyaddr",
                "socket.getnameinfo",
            }:
                return
        raise RuntimeError("staging_network_destination_denied")
