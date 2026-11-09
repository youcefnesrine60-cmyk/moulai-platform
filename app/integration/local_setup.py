# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNED LOCAL IDENTITY AND DATABASE BOOTSTRAP
# Initialize a new persistent development instance, never an existing database or provider.
# ==============================================

"""All endpoints and Docker resources are local, labelled, and isolated from other reviews."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Reuse native PostgreSQL, the frozen main bootstrap and the already installed Keycloak image.
# ==============================================

import asyncio
import ipaddress
import json
import os
import secrets
import socket
import subprocess
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path
from uuid import uuid4

import asyncpg
from alembic.config import Config
from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import (
    hashes,
    serialization,
)
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from app.integration.config import (
    INSTANCE_ROOT,
    ROOT,
    IntegrationConfig,
)

PG = Path(r"C:/Program Files/PostgreSQL/18/bin")
DOCKER = ["docker", "-H", "npipe:////./pipe/docker_engine"]
IMAGE = "quay.io/keycloak/keycloak:26.8.0"


# ==============================================
# LOCAL PROCESS
# Run explicit arguments without a shell; expose only nonsensitive failure classes.
# ==============================================


def local_process(
    *, arguments: list[str], cwd: Path | None = None, input_text: str | None = None
) -> str:
    """Run explicit arguments without a shell; expose only nonsensitive failure classes."""
    result = subprocess.run(
        arguments,
        cwd=cwd,
        input=input_text,
        stdout=(
            subprocess.DEVNULL
            if Path(arguments[0]).name.lower() == "pg_ctl.exe"
            else subprocess.PIPE
        ),
        stderr=(
            subprocess.DEVNULL
            if Path(arguments[0]).name.lower() == "pg_ctl.exe"
            else subprocess.PIPE
        ),
        timeout=120,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if result.returncode:
        raise RuntimeError(
            "local_component_failed:"
            + Path(arguments[0]).name
            + ":"
            + str(result.returncode)
        )
    return (result.stdout or "").strip()


# ==============================================
# ISSUE LOCAL CERTIFICATES
# Create one private local CA and a loopback-only leaf, without installing OS trust.
# ==============================================


def issue_local_certificates(*, directory: Path) -> None:
    """Create one private local CA and a loopback-only leaf, without installing OS trust."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "MoulAI isolated development CA")]
    )
    now = datetime.now(timezone.utc)
    ca = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=90))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")]))
        .issuer_name(name)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    tls = directory / "private" / "tls"
    tls.mkdir(exist_ok=True)
    (directory / "private" / "ca.pem").write_bytes(
        ca.public_bytes(serialization.Encoding.PEM)
    )
    (tls / "server.pem").write_bytes(
        leaf.public_bytes(serialization.Encoding.PEM)
        + ca.public_bytes(serialization.Encoding.PEM)
    )
    (tls / "server-key.pem").write_bytes(
        leaf_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


# ==============================================
# INITIALIZE DATABASE
# Apply the frozen historical bootstrap and full principal chain to a new local database.
# ==============================================


async def initialize_database(
    *,
    configuration: IntegrationConfig,
    bootstrap_password: str,
    target: str = "o220261108",
) -> None:
    """Apply the frozen historical bootstrap and full principal chain to a new local database."""
    configuration.process_environment()
    from migration_support.main_bootstrap import load_bootstrap_statements

    bootstrap = await asyncpg.connect(
        host="127.0.0.1",
        port=55433,
        database="postgres",
        user="moulai_bootstrap",
        password=bootstrap_password,
        ssl=False,
    )
    from sqlalchemy.engine import make_url

    password = make_url(configuration.database_url).password
    if (
        not password
        or len(password) != 64
        or any(c not in "0123456789abcdef" for c in password)
    ):
        raise ValueError("generated_password_required")
    try:
        await bootstrap.execute(
            "CREATE ROLE moulai_integrated LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '"
            + password
            + "'"
        )
        await bootstrap.execute(
            "CREATE DATABASE moulai_integrated OWNER moulai_integrated TEMPLATE template0 ENCODING 'UTF8' LOCALE_PROVIDER builtin BUILTIN_LOCALE 'C.UTF-8' LC_COLLATE 'C' LC_CTYPE 'C'"
        )
        await bootstrap.execute(
            "COMMENT ON DATABASE moulai_integrated IS 'moulai-operational-local:"
            + configuration.instance_id
            + "'"
        )
    finally:
        await bootstrap.close()
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with engine.begin() as connection:
            count = await connection.scalar(
                text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
            )
            if count:
                raise RuntimeError("new_operational_database_not_empty")
            for statement in load_bootstrap_statements():
                await connection.exec_driver_sql(statement)

            # ==============================================
            # MIGRATE
            # Let Alembic write its own revision on the same checked transaction.
            # ==============================================

            def migrate(sync: Connection) -> None:
                """Let Alembic write its own revision on the same checked transaction."""
                config = Config()
                config.set_main_option(
                    "script_location", str(ROOT / "alembic_operational_local")
                )
                config.set_main_option(
                    "version_locations", str(ROOT / "alembic/versions")
                )
                config.set_main_option("path_separator", "os")
                config.attributes.update(
                    connection=sync, operational_configuration=configuration
                )
                if target not in {"o220261108", "o420261108"}:
                    raise ValueError("operational_bootstrap_target_not_admitted")
                command.upgrade(config, target)

            await connection.run_sync(migrate)
        async with engine.connect() as connection:
            revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            tables = await connection.scalar(
                text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
            )
            if (
                revision != target
                or tables != {"o220261108": 93, "o420261108": 101}[target]
            ):
                raise RuntimeError("operational_catalogue_not_expected")
        (configuration.directory / "schema.json").write_text(
            json.dumps(
                {
                    "revision": revision,
                    "public_tables": tables,
                    "bootstrap": "main-bootstrap-v1",
                    "database": "moulai_integrated",
                    "host": "127.0.0.1",
                    "port": 55433,
                }
            ),
            encoding="utf-8",
        )
    finally:
        await engine.dispose()


# ==============================================
# INITIALIZE INSTANCE
# Create owned resources only after exact loopback ports and local image are available.
# ==============================================


def initialize_instance() -> Path:
    """Create owned resources only after exact loopback ports and local image are available."""
    for port in (55433, 8444, 5582, 5180):
        with socket.socket() as check:
            check.bind(("127.0.0.1", port))
    local_process(arguments=DOCKER + ["image", "inspect", IMAGE, "--format", "{{.Id}}"])
    identifier = uuid4().hex
    directory = INSTANCE_ROOT / identifier
    (directory / "private").mkdir(parents=True)
    if os.name == "nt":
        account = local_process(arguments=["whoami"])
        local_process(
            arguments=[
                "icacls",
                str(directory / "private"),
                "/inheritance:r",
                "/grant:r",
                account + ":(OI)(CI)F",
                "*S-1-5-18:(OI)(CI)F",
            ]
        )
    (directory / "instance-marker").write_text(identifier, encoding="ascii")
    runtime_password = secrets.token_hex(32)
    data = {
        "instance_id": identifier,
        "database_url": "postgresql+asyncpg://moulai_integrated:"
        + runtime_password
        + "@127.0.0.1:55433/moulai_integrated",
        "client_secret": secrets.token_urlsafe(48),
        "session_key": Fernet.generate_key().decode(),
        "admin_password": secrets.token_urlsafe(32),
    }
    (directory / "private" / "instance.json").write_text(
        json.dumps(data), encoding="utf-8"
    )
    issue_local_certificates(directory=directory)
    configuration = IntegrationConfig.load(directory=directory)
    bootstrap_password = secrets.token_urlsafe(32)
    password_file = directory / "private" / "postgres-password"
    password_file.write_text(bootstrap_password, encoding="utf-8")
    try:
        local_process(
            arguments=[
                str(PG / "initdb.exe"),
                "-D",
                str(directory / "postgres-data"),
                "-U",
                "moulai_bootstrap",
                "--encoding=UTF8",
                "--locale=C",
                "--auth-host=scram-sha-256",
                "--auth-local=trust",
                "--pwfile=" + str(password_file),
            ]
        )
    finally:
        password_file.unlink(missing_ok=True)
    local_process(
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
        ]
    )
    asyncio.run(
        initialize_database(
            configuration=configuration,
            bootstrap_password=bootstrap_password,
            target="o420261108",
        )
    )
    realm = {
        "realm": "moulai-local",
        "enabled": True,
        "sslRequired": "all",
        "registrationAllowed": True,
        "resetPasswordAllowed": False,
        "internationalizationEnabled": True,
        "supportedLocales": ["fr", "en", "ar"],
        "defaultLocale": "fr",
        "accessTokenLifespan": 300,
        "ssoSessionMaxLifespan": 1800,
        "bruteForceProtected": True,
        "clients": [
            {
                "clientId": configuration.client_id,
                "secret": configuration.client_secret,
                "publicClient": False,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": False,
                "redirectUris": [configuration.origin + "/api/web/auth/callback"],
                "webOrigins": [],
                "attributes": {"pkce.code.challenge.method": "S256"},
                "protocolMappers": [
                    {
                        "name": "moulai-api-audience",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-audience-mapper",
                        "config": {
                            "included.custom.audience": configuration.audience,
                            "access.token.claim": "true",
                            "id.token.claim": "false",
                        },
                    },
                    {
                        "name": "moulai-browser-introspection-audience",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-audience-mapper",
                        "config": {
                            "included.client.audience": configuration.client_id,
                            "access.token.claim": "true",
                            "id.token.claim": "false",
                        },
                    },
                ],
            }
        ],
    }
    realms = directory / "private" / "realm"
    realms.mkdir()
    (realms / "moulai-local-realm.json").write_text(json.dumps(realm), encoding="utf-8")
    (directory / "private" / "keycloak-data").mkdir()
    env = directory / "private" / "keycloak.env"
    env.write_text(
        "KC_BOOTSTRAP_ADMIN_USERNAME=bootstrap\nKC_BOOTSTRAP_ADMIN_PASSWORD="
        + configuration.admin_password
        + "\n",
        encoding="utf-8",
    )
    network = "moulai-op-" + identifier[:12]
    local_process(
        arguments=DOCKER
        + [
            "network",
            "create",
            "--opt",
            "com.docker.network.bridge.enable_ip_masquerade=false",
            "--label",
            "moulai.instance=" + identifier,
            network,
        ]
    )
    local_process(
        arguments=DOCKER
        + [
            "create",
            "--pull=never",
            "--name",
            "moulai-keycloak-" + identifier[:12],
            "--network",
            network,
            "--label",
            "moulai.instance=" + identifier,
            "--publish",
            "127.0.0.1:8444:8443",
            "--env-file",
            str(env),
            "--mount",
            "type=bind,source="
            + str(directory / "private" / "tls")
            + ",target=/run/tls,readonly",
            "--mount",
            "type=bind,source="
            + str(realms)
            + ",target=/opt/keycloak/data/import,readonly",
            "--mount",
            "type=bind,source="
            + str(directory / "private" / "keycloak-data")
            + ",target=/opt/keycloak/data/h2",
            IMAGE,
            "start-dev",
            "--http-enabled=false",
            "--hostname=https://127.0.0.1:8444",
            "--https-certificate-file=/run/tls/server.pem",
            "--https-certificate-key-file=/run/tls/server-key.pem",
            "--import-realm",
        ]
    )
    (INSTANCE_ROOT / "active.json").write_text(
        json.dumps({"directory": str(directory)}), encoding="utf-8"
    )
    (directory / "instance.json").write_text(
        json.dumps(
            {
                "instance_id": identifier,
                "origin": configuration.origin,
                "issuer": configuration.issuer,
                "postgres": "127.0.0.1:55433/moulai_integrated",
                "image": IMAGE,
                "external_service": False,
            }
        ),
        encoding="utf-8",
    )
    return directory
