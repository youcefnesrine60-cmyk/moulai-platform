# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNED LOCAL DINING REVIEW LIFECYCLE
# Rebuild the real principal migration chain on a fresh local cluster and host only loopback.
# ==============================================

"""No .env target, permanent database, external provider, channel or deployed app."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT LOCAL CONTRACTS
# Reuse typed module dependencies without creating a connection or enabling a transport.
# ==============================================

import argparse
import asyncio
import contextlib
import json
import os
import secrets
import socket
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_local_postgres_tests import (
    provision_database,
    run_process,
)
from test_support.local_postgres import (
    LOCAL_PORT,
    LocalPostgresNetworkGuard,
    LocalPostgresSettings,
)

# ==============================================
# LOCALDININGNETWORKGUARD
# The server may listen on its exact loopback port; outbound traffic remains PG-only.
# ==============================================


class LocalDiningNetworkGuard(LocalPostgresNetworkGuard):
    """The server may listen on its exact loopback port; outbound traffic remains PG-only."""

    # ==============================================
    # CALL
    # Reject public binds and all remote DNS/provider traffic before the operation.
    # ==============================================

    def __call__(self, event: str, arguments: tuple[object, ...]) -> None:
        """Reject public binds and all remote DNS/provider traffic before the operation."""
        if event == "socket.bind" and len(arguments) > 1:
            address = arguments[1]
            if not self._is_socket_pair() and (
                not isinstance(address, tuple)
                or address[:2]
                not in {
                    ("127.0.0.1", LOCAL_PORT),
                    ("127.0.0.1", 5581),
                    ("127.0.0.1", 5574),
                }
            ):
                self.denied[event] += 1
                raise RuntimeError("dining_public_bind_denied")
        if event == "socket.getaddrinfo" and arguments[:2] == ("127.0.0.1", 5581):
            return
        super().__call__(event, arguments)


# ==============================================
# HOST
# Keep this owned cluster alive for genuine HTTP operations; never start workers.
# ==============================================


async def host(
    *,
    configuration: LocalPostgresSettings,
    output: Path,
    browser_tests: bool,
    nominal_only: bool = False,
    visual_fixtures: bool = False,
) -> int:
    """Keep this owned cluster alive for genuine HTTP operations; never start workers."""
    import uvicorn
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.services.business.dining.values import utc_now
    from test_support.dining_http import create_local_dining_app
    from test_support.dining_seed import prepare_dining_rehearsal

    engine = create_async_engine(
        configuration.URL.get_secret_value(),
        hide_parameters=True,
        connect_args={"ssl": False},
    )
    frontend: asyncio.subprocess.Process | None = None
    server: uvicorn.Server | None = None
    task: asyncio.Task[None] | None = None
    monitor: asyncio.Task[None] | None = None
    try:
        graph = await prepare_dining_rehearsal(
            engine=engine, configuration=configuration, now=utc_now()
        )
        if visual_fixtures:
            from test_support.dining_visual_seed import prepare_visual_states

            await prepare_visual_states(
                graph=graph, engine=engine, configuration=configuration
            )
        app, _issuer = await create_local_dining_app(
            configuration=configuration, graph=graph, clock=utc_now
        )
        server = uvicorn.Server(
            uvicorn.Config(
                app, host="127.0.0.1", port=5581, access_log=False, log_config=None
            )
        )
        task = asyncio.create_task(server.serve())
        for _ in range(200):
            if server.started:
                break
            if task.done():
                await task
            await asyncio.sleep(0.05)
        if not server.started:
            raise RuntimeError("local_dining_http_start_failed")
        node = ROOT / "artifacts/frontend-tooling/node-v24.22.1-win-x64/node.exe"
        process_options = (
            {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        )
        if browser_tests:
            process = await asyncio.create_subprocess_exec(
                str(node),
                "node_modules/@playwright/test/cli.js",
                "test",
                "-c",
                "playwright.dining-live.config.ts",
                *(["--grep", "real UI nominal"] if nominal_only else []),
                cwd=ROOT / "frontend",
                **process_options,
            )
            result = await process.wait()
            return result
        frontend_log = (output / "frontend.log").open("wb")
        try:
            frontend = await asyncio.create_subprocess_exec(
                str(node),
                "node_modules/vite/bin/vite.js",
                "--mode",
                "dining",
                "--host",
                "127.0.0.1",
                "--port",
                "5574",
                "--strictPort",
                cwd=ROOT / "frontend",
                stdout=frontend_log,
                stderr=frontend_log,
                **process_options,
            )
            # ==============================================
            # OWNED REVIEW SHUTDOWN MONITOR
            # A per-run stop request closes HTTP/Node before the owned cluster stops.
            # ==============================================

            async def observe_stop() -> None:
                """Watch only this run's lifecycle file; never dispatch business work."""
                while not server.should_exit:
                    if (
                        output / "stop-request"
                    ).is_file() or frontend.returncode is not None:
                        server.should_exit = True
                        return
                    await asyncio.sleep(0.5)

            monitor = asyncio.create_task(observe_stop())
            print(
                "Local persisted D1 review: http://127.0.0.1:5574/dining-local",
                flush=True,
            )
            print(
                "Fictional identities and food sources; real disposable PostgreSQL writes; no real notifications.",
                flush=True,
            )
            (output / "review.json").write_text(
                json.dumps(
                    {
                        "url": "http://127.0.0.1:5574/dining-local",
                        "instance_id": configuration.INSTANCE_ID,
                        "base": graph.base,
                        "revision": "d1d20261105",
                        "identity_provider": "simulated-local-RS256",
                        "business_clock": "real-UTC",
                        "workers_started": False,
                        "visual_fixtures": visual_fixtures,
                        "process_pid": os.getpid(),
                        "stop_request": str(output / "stop-request"),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            await task
        finally:
            frontend_log.close()
        return 0
    finally:
        if monitor is not None:
            monitor.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor
        if frontend is not None and frontend.returncode is None:
            frontend.terminate()
            await frontend.wait()
        if server is not None:
            server.should_exit = True
        if task is not None:
            await task
        await engine.dispose()


# ==============================================
# MAIN
# Create a fresh owned target, apply actual migrations, serve, and stop in finally.
# ==============================================


def main() -> int:
    """Create a fresh owned target, apply actual migrations, serve, and stop in finally."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-tests", action="store_true")
    parser.add_argument("--browser-nominal-only", action="store_true")
    parser.add_argument(
        "--visual-fixtures",
        action="store_true",
        help="Add labeled fictional state observations to the owned disposable target",
    )
    options = parser.parse_args()
    os.chdir(ROOT)
    run_id = uuid4().hex
    output = ROOT / "artifacts/dining-local-runs" / run_id
    output.mkdir(parents=True)
    runtime_password = secrets.token_hex(32)
    bootstrap_password = secrets.token_hex(32)
    configuration = LocalPostgresSettings(
        URL=f"postgresql+asyncpg://moulai_pytest:{runtime_password}@127.0.0.1:55432/moulai_pytest",
        INSTANCE_ID=run_id,
        PROFILE="dining",
        SERVER_PORT=LOCAL_PORT,
    )
    os.environ.update(
        {
            "DEBUG": "false",
            "DB_ECHO": "false",
            "APP_ENV": "test",
            "DATABASE_TARGET": "primary",
            "DATABASE_URL": configuration.URL.get_secret_value(),
            "TEST_DATABASE_URL": configuration.URL.get_secret_value(),
            "REDIS_URL": "",
            "OPENAI_API_KEY": "local-rehearsal-no-provider-access",
            "OPENAI_BASE_URL": "http://127.0.0.1:1",
            "BOT_TOKEN": "000000000:LOCAL_REHEARSAL_NOT_A_REAL_BOT_TOKEN",
            "LOG_FILE_PATH": str(output / "application.log"),
        }
    )
    guard = LocalDiningNetworkGuard()
    sys.addaudithook(guard)
    for port in (LOCAL_PORT, 5581, 5574):
        with socket.socket() as reservation:
            try:
                reservation.bind(("127.0.0.1", port))
            except OSError as error:
                raise RuntimeError(
                    f"local_review_port_unavailable:127.0.0.1:{port}"
                ) from error
    data = output / "server-data"
    binaries = Path(r"C:\Program Files\PostgreSQL\18\bin")
    pg_ctl = str(binaries / "pg_ctl.exe")
    password = output / "bootstrap-password"
    attempted = False
    try:
        password.write_text(bootstrap_password + "\n", encoding="utf-8")
        try:
            run_process(
                arguments=[
                    str(binaries / "initdb.exe"),
                    "-D",
                    str(data),
                    "-U",
                    "moulai_test_bootstrap",
                    "--encoding=UTF8",
                    "--locale=C",
                    "--auth-host=scram-sha-256",
                    "--auth-local=trust",
                    f"--pwfile={password}",
                ]
            )
        finally:
            password.unlink(missing_ok=True)
        attempted = True
        run_process(
            arguments=[
                pg_ctl,
                "-D",
                str(data),
                "-l",
                str(output / "server.log"),
                "-o",
                "-h 127.0.0.1 -p 55432 -c log_min_error_statement=panic",
                "-w",
                "-t",
                "30",
                "start",
            ]
        )
        schema = asyncio.run(
            provision_database(
                bootstrap_password=bootstrap_password,
                configuration=configuration,
                runtime_password=runtime_password,
            )
        )
        (output / "schema.json").write_text(
            json.dumps(schema, indent=2), encoding="utf-8"
        )
        return asyncio.run(
            host(
                configuration=configuration,
                output=output,
                browser_tests=options.browser_tests or options.browser_nominal_only,
                nominal_only=options.browser_nominal_only,
                visual_fixtures=options.visual_fixtures,
            )
        )
    finally:
        if attempted and (data / "postmaster.pid").exists():
            if not data.resolve().is_relative_to(output.resolve()):
                raise RuntimeError("local_cleanup_scope_invalid")
            run_process(arguments=[pg_ctl, "-D", str(data), "-m", "fast", "-w", "stop"])
        (output / "safety.json").write_text(
            json.dumps(
                {
                    "network_denied_categories": dict(guard.denied),
                    "permanent_database_used": False,
                    "server_stopped": True,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    raise SystemExit(main())
