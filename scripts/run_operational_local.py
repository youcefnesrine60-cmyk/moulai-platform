# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PERSISTENT LOCAL OPERATIONAL PLATFORM LAUNCHER
# Own one isolated database and local Keycloak without replacing existing review services.
# ==============================================

"""No .env edit, image pull, remote target, public bind, worker or provider expenditure."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Resolve the project explicitly and keep credentials out of process arguments and output.
# ==============================================

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
from collections import Counter
from contextlib import ExitStack
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
from sqlalchemy.exc import SQLAlchemyError

from app.integration.config import (
    INSTANCE_ROOT,
    IntegrationConfig,
)
from app.integration.local_setup import (
    DOCKER,
    PG,
    initialize_instance,
    local_process,
)
from app.integration.process import local_host_lease

# ==============================================
# INTEGRATIONNETWORKGUARD
# Reject Python outbound IO except the exact local PostgreSQL and Keycloak ports.
# ==============================================


class IntegrationNetworkGuard:
    """Reject Python outbound IO except the exact local PostgreSQL and Keycloak ports."""

    # ==============================================
    # NONSENSITIVE TRAFFIC ACCOUNTING
    # Retain event categories only, never destinations, requests or tokens.
    # ==============================================

    def __init__(self, *, readiness_only: bool = False) -> None:
        """Count admitted local IO and denied operations for the owned process report."""
        self.allowed: Counter[str] = Counter()
        self.denied: Counter[str] = Counter()
        self.destinations = (
            {("127.0.0.1", 5582), ("127.0.0.1", 5180)}
            if readiness_only
            else {("127.0.0.1", 55433), ("127.0.0.1", 8444)}
        )
        self.binds = (
            set() if readiness_only else {("127.0.0.1", 5582), ("127.0.0.1", 5180)}
        )

    # ==============================================
    # CALL
    # Permit stdlib Windows socketpair but deny foreign binds and remote connections.
    # ==============================================

    def __call__(self, event: str, arguments: tuple[object, ...]) -> None:
        """Permit stdlib Windows socketpair but deny foreign binds and remote connections."""
        if event not in {
            "socket.getaddrinfo",
            "socket.connect",
            "socket.bind",
            "socket.sendto",
            "socket.sendmsg",
            "socket.gethostbyname",
            "socket.gethostbyaddr",
            "socket.getnameinfo",
        }:
            return
        if event in {
            "socket.sendto",
            "socket.sendmsg",
            "socket.gethostbyname",
            "socket.gethostbyaddr",
            "socket.getnameinfo",
        }:
            self.denied[event] += 1
            raise RuntimeError("operational_network_operation_denied")
        frame = sys._getframe(1)
        while frame is not None:
            if (
                frame.f_code.co_filename == socket.__file__
                and frame.f_code.co_name in {"socketpair", "_fallback_socketpair"}
            ):
                return
            frame = frame.f_back
        if event == "socket.getaddrinfo" and arguments[:2] not in self.destinations:
            self.denied[event] += 1
            raise RuntimeError("operational_remote_dns_denied")
        if event in {"socket.connect", "socket.bind"}:
            address = arguments[1] if len(arguments) > 1 else None
            allowed = self.destinations if event == "socket.connect" else self.binds
            if not isinstance(address, tuple) or address[:2] not in allowed:
                self.denied[event] += 1
                raise RuntimeError("operational_network_destination_denied")
        self.allowed[event] += 1


# ==============================================
# RESOLVE INSTANCE
# Use the explicit directory or the owned active marker, never a DATABASE_URL default.
# ==============================================


def resolve_instance(*, supplied: str | None) -> IntegrationConfig:
    """Use the explicit directory or the owned active marker, never a DATABASE_URL default."""
    path = (
        Path(supplied)
        if supplied
        else Path(
            json.loads((INSTANCE_ROOT / "active.json").read_text(encoding="utf-8"))[
                "directory"
            ]
        )
    )
    return IntegrationConfig.load(directory=path)


# ==============================================
# APPLICATION PORT ADMISSION
# Refuse an already running frontend or API before touching persistent local components.
# ==============================================


def require_free_application_ports() -> None:
    """Probe only owned loopback application ports; do not stop an existing listener."""
    for port in (5180, 5582):
        try:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError("operational_application_port_in_use") from error


# ==============================================
# KEEP ONLY THE SAME READY LOCAL INSTANCE
# An occupied lease alone may belong to a migration or incomplete startup; require the API identity and the trusted local frontend too.
# ==============================================


async def require_existing_review(
    *,
    configuration: IntegrationConfig,
    transport: httpx.AsyncBaseTransport | None = None,
) -> None:
    """Perform only fixed read-only loopback GETs; reject redirects, another instance and an unavailable frontend."""
    import ssl

    async with httpx.AsyncClient(
        verify=ssl.create_default_context(cafile=str(configuration.ca_file)),
        trust_env=False,
        follow_redirects=False,
        timeout=5,
        transport=transport,
    ) as client:
        reply = await client.get("http://127.0.0.1:5582/api/web/local-status")
        if reply.status_code != 200 or reply.json() != {
            "service": "moulai-operational-local",
            "instance_id": configuration.instance_id,
            "url": configuration.origin + "/access",
        }:
            raise RuntimeError("operational_existing_instance_not_ready")
        frontend = await client.get(configuration.origin + "/access")
        if (
            frontend.status_code != 200
            or "text/html" not in frontend.headers.get("content-type", "")
            or "/src/main.tsx" not in frontend.text
        ):
            raise RuntimeError("operational_existing_frontend_not_ready")


# ==============================================
# SERVE
# Restore persistent components, attest them, and run one loopback-only application entry.
# ==============================================


async def serve(*, configuration: IntegrationConfig) -> int:
    """Restore persistent components, attest them, and run one loopback-only application entry."""
    configuration.process_environment()
    import ssl

    import httpx
    import uvicorn

    from app.integration.web import create_operational_app

    directory = configuration.directory
    container = "moulai-keycloak-" + configuration.instance_id[:12]
    label = await asyncio.to_thread(
        local_process,
        arguments=DOCKER
        + [
            "inspect",
            container,
            "--format",
            '{{index .Config.Labels "moulai.instance"}}',
        ],
    )
    if label != configuration.instance_id:
        raise RuntimeError("operational_container_ownership_mismatch")
    pg_status = await asyncio.to_thread(
        subprocess.run,
        [str(PG / "pg_ctl.exe"), "-D", str(directory / "postgres-data"), "status"],
        capture_output=True,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if pg_status.returncode:
        await asyncio.to_thread(
            local_process,
            arguments=[
                str(PG / "pg_ctl.exe"),
                "-D",
                str(directory / "postgres-data"),
                "-l",
                str(directory / "postgres.log"),
                "-o",
                "-h 127.0.0.1 -p 55433 -c log_min_error_statement=panic",
                "-w",
                "start",
            ],
        )
    await asyncio.to_thread(local_process, arguments=DOCKER + ["start", container])
    async with httpx.AsyncClient(
        verify=ssl.create_default_context(cafile=str(configuration.ca_file)),
        trust_env=False,
        timeout=2,
    ) as client:
        for _ in range(600):
            try:
                reply = await client.get(
                    configuration.issuer + "/.well-known/openid-configuration"
                )
                if (
                    reply.status_code == 200
                    and reply.json().get("issuer") == configuration.issuer
                ):
                    break
            except httpx.HTTPError:
                await asyncio.sleep(1)
        else:
            raise RuntimeError("local_keycloak_not_ready")
    (directory / "stop-request").unlink(missing_ok=True)
    app = create_operational_app(configuration=configuration)
    server = uvicorn.Server(
        uvicorn.Config(
            app, host="127.0.0.1", port=5582, access_log=False, log_config=None
        )
    )
    task = asyncio.create_task(server.serve())
    frontend: asyncio.subprocess.Process | None = None
    log = (directory / "frontend.log").open("ab")
    try:
        for _ in range(150):
            if server.started:
                break
            if task.done():
                await task
            await asyncio.sleep(0.1)
        if not server.started:
            raise RuntimeError("operational_api_not_ready")
        environment = {**os.environ, "MOULAI_OPERATIONAL_DIR": str(directory)}
        frontend = await asyncio.create_subprocess_exec(
            str(ROOT / "artifacts/frontend-tooling/node-v24.22.1-win-x64/node.exe"),
            "node_modules/vite/bin/vite.js",
            "--mode",
            "operational",
            "--host",
            "127.0.0.1",
            "--port",
            "5180",
            "--strictPort",
            cwd=ROOT / "frontend",
            env=environment,
            stdout=log,
            stderr=log,
            **(
                {"creationflags": subprocess.CREATE_NO_WINDOW}
                if os.name == "nt"
                else {}
            ),
        )
        (directory / "review.json").write_text(
            json.dumps(
                {
                    "url": configuration.origin + "/access",
                    "instance_id": configuration.instance_id,
                    "identity": "Keycloak local, authorization-code + PKCE",
                    "business_database": "127.0.0.1:55433/moulai_integrated",
                    "persistence": "retained on restart",
                    "workers": False,
                    "external_services": False,
                    "pid": os.getpid(),
                    "stop_request": str(directory / "stop-request"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            "MoulAI operational local: " + configuration.origin + "/access", flush=True
        )
        print(
            "Real local Keycloak accounts; retained local database. No worker or external transport.",
            flush=True,
        )
        while (
            not task.done()
            and not (directory / "stop-request").exists()
            and frontend.returncode is None
        ):
            await asyncio.sleep(0.5)
        server.should_exit = True
        await task
        return 0
    finally:
        if frontend is not None and frontend.returncode is None:
            frontend.terminate()
            await frontend.wait()
        server.should_exit = True
        if not task.done():
            await task
        log.close()
        await asyncio.to_thread(
            local_process, arguments=DOCKER + ["stop", "--time", "20", container]
        )
        await asyncio.to_thread(
            local_process,
            arguments=[
                str(PG / "pg_ctl.exe"),
                "-D",
                str(directory / "postgres-data"),
                "-m",
                "fast",
                "-w",
                "stop",
            ],
        )


# ==============================================
# MAIN
# Require an explicit operation and never reveal input credentials on failure.
# ==============================================


def main() -> int:
    """Require an explicit operation and never reveal input credentials on failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=[
            "init",
            "serve",
            "account",
            "company",
            "platform-admin",
            "role-policy",
        ],
    )
    parser.add_argument("--instance")
    parser.add_argument("--keep-running", action="store_true")
    options = parser.parse_args()
    if options.keep_running and options.operation != "serve":
        parser.error("--keep-running is supported only for serve")
    try:
        if options.operation == "init":
            directory = initialize_instance()
            print(
                json.dumps(
                    {
                        "status": "initialized",
                        "directory": str(directory),
                        "target": "127.0.0.1:55433/moulai_integrated",
                    }
                )
            )
            return 0
        configuration = resolve_instance(supplied=options.instance)
        configuration.process_environment()
        guard = IntegrationNetworkGuard()
        if options.operation == "serve":
            with ExitStack() as ownership:
                try:
                    ownership.enter_context(
                        local_host_lease(directory=configuration.directory)
                    )
                except RuntimeError as error:
                    if (
                        not options.keep_running
                        or str(error) != "operational_instance_already_running"
                    ):
                        raise
                    sys.addaudithook(IntegrationNetworkGuard(readiness_only=True))
                    asyncio.run(require_existing_review(configuration=configuration))
                    print(
                        "MoulAI operational local already running: "
                        + configuration.origin
                        + "/access"
                    )
                    return 0
                sys.addaudithook(guard)
                require_free_application_ports()
                try:
                    return asyncio.run(serve(configuration=configuration))
                finally:
                    (configuration.directory / "network-report.json").write_text(
                        json.dumps(
                            {
                                "scope": "Python audit hook; not an OS firewall",
                                "allowed": dict(guard.allowed),
                                "denied": dict(guard.denied),
                                "external_provider_calls": "not permitted by this transport allowlist",
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
        sys.addaudithook(guard)
        from app.integration.provision import (
            configure_role_policy,
            create_account,
            create_company,
            create_platform_admin,
        )

        data = json.load(sys.stdin)
        if options.operation == "account":
            result = asyncio.run(
                create_account(
                    configuration=configuration,
                    username=data["username"],
                    password=data["password"],
                )
            )
        elif options.operation == "company":
            result = asyncio.run(
                create_company(
                    configuration=configuration,
                    subject=data["subject"],
                    name=data["name"],
                    restaurant_name=data["restaurant_name"],
                    branch_name=data["branch_name"],
                    legacy_id=data["legacy_id"],
                    permissions=tuple(data["permissions"]),
                )
            )
        elif options.operation == "role-policy":
            result = asyncio.run(
                configure_role_policy(
                    configuration=configuration,
                    role_code=data["role_code"],
                    permissions=tuple(data["permissions"]),
                )
            )
        else:
            result = asyncio.run(
                create_platform_admin(
                    configuration=configuration,
                    subject=data["subject"],
                    legacy_id=data["legacy_id"],
                    permissions=tuple(data["permissions"]),
                )
            )
        print(json.dumps(result))
        return 0
    except (
        OSError,
        RuntimeError,
        ValueError,
        KeyError,
        TypeError,
        SQLAlchemyError,
        httpx.HTTPError,
        KeyboardInterrupt,
    ) as error:
        # Error messages may contain database URLs or provider form contents.
        print(
            json.dumps(
                {
                    "status": "STOPPED",
                    "error_type": type(error).__name__,
                    **(
                        {"reason": error.args[0]}
                        if isinstance(error, RuntimeError)
                        and error.args
                        in {
                            ("operational_instance_already_running",),
                            ("operational_application_port_in_use",),
                            ("local_keycloak_not_ready",),
                            ("operational_existing_instance_not_ready",),
                            ("operational_existing_frontend_not_ready",),
                        }
                        else {}
                    ),
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
