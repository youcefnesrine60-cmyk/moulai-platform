# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Synthetic B/W/V admission tests; no engine, credential or database fixtures."""

from __future__ import annotations

import hashlib
import json
import ssl
from copy import deepcopy
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import (
    Any,
    cast,
)
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.engine import (
    Connection,
    make_url,
)

from app.core.rehearsal_admission import (
    DEVELOPMENT_BRANCH_ID,
    DEVELOPMENT_ENDPOINT_ID,
    E1_REVISION,
    PRODUCTION_BRANCH_ID,
    PROJECT_ID,
    START_REVISION,
    BranchEvidence,
    ControlPlaneEvidence,
    EndpointEvidence,
    InitialStateEquivalence,
    Operation,
    Purpose,
    RehearsalManifest,
    RehearsalResource,
    admit_destination,
    inspect_admitted_connection,
    manifest_sha256,
    parse_manifest,
    read_only_connection_arguments,
    validate_manifest,
    verify_initial_equivalence,
)
from app.core.test_database import UnsafeTestDatabaseError

NOW = datetime(2026, 10, 18, 16, tzinfo=timezone.utc)
PURPOSES: tuple[Purpose, ...] = ("baseline", "rehearsal", "recovery-proof")
DIRECT_SUFFIX = "eu-central-1.aws.neon.tech"


# ==============================================
# SYNTHETIC RESOURCE MANIFEST
# ==============================================


@pytest.fixture
def manifest() -> RehearsalManifest:
    """Build explicitly synthetic IDs, including source replica endpoints."""
    branches = [
        BranchEvidence(branch_id=PRODUCTION_BRANCH_ID, parent_id=None, fork_lsn=None),
        BranchEvidence(
            branch_id=DEVELOPMENT_BRANCH_ID,
            parent_id=PRODUCTION_BRANCH_ID,
            fork_lsn="0/A",
        ),
    ]
    endpoints = [
        EndpointEvidence(
            endpoint_id="ep-synthetic-production",
            branch_id=PRODUCTION_BRANCH_ID,
            direct_host=f"ep-synthetic-production.{DIRECT_SUFFIX}",
            primary=True,
        ),
        EndpointEvidence(
            endpoint_id="ep-synthetic-production-replica",
            branch_id=PRODUCTION_BRANCH_ID,
            direct_host=f"ep-synthetic-production-replica.{DIRECT_SUFFIX}",
            primary=False,
        ),
        EndpointEvidence(
            endpoint_id=DEVELOPMENT_ENDPOINT_ID,
            branch_id=DEVELOPMENT_BRANCH_ID,
            direct_host=f"{DEVELOPMENT_ENDPOINT_ID}.{DIRECT_SUFFIX}",
            primary=True,
        ),
        EndpointEvidence(
            endpoint_id="ep-synthetic-development-replica",
            branch_id=DEVELOPMENT_BRANCH_ID,
            direct_host=f"ep-synthetic-development-replica.{DIRECT_SUFFIX}",
            primary=False,
        ),
    ]
    resources = []
    for purpose in PURPOSES:
        parent = (
            DEVELOPMENT_BRANCH_ID if purpose == "baseline" else "br-synthetic-baseline"
        )
        branch_id = f"br-synthetic-{purpose}"
        endpoint_id = f"ep-synthetic-{purpose}"
        branches.append(
            BranchEvidence(branch_id=branch_id, parent_id=parent, fork_lsn="0/B")
        )
        endpoints.append(
            EndpointEvidence(
                endpoint_id=endpoint_id,
                branch_id=branch_id,
                direct_host=f"{endpoint_id}.{DIRECT_SUFFIX}",
                primary=True,
            )
        )
        resources.append(
            RehearsalResource(
                purpose=purpose,
                branch_id=branch_id,
                endpoint_id=endpoint_id,
                parent_id=parent,
                fork_lsn="0/B",
                created_at=NOW - timedelta(minutes=10),
                expires_at=None if purpose == "baseline" else NOW + timedelta(hours=23),
                review_due_at=NOW
                + timedelta(hours=48 if purpose == "baseline" else 20),
            )
        )
    return RehearsalManifest(
        version=1,
        stage="complete",
        project_id=PROJECT_ID,
        production_branch_id=PRODUCTION_BRANCH_ID,
        development_branch_id=DEVELOPMENT_BRANCH_ID,
        database="neondb_test",
        initial_revision=START_REVISION,
        target_revision=E1_REVISION,
        resources=tuple(resources),
        control_plane=ControlPlaneEvidence(
            project_id=PROJECT_ID,
            observed_at=NOW,
            complete=True,
            source_sha256="a" * 64,
            branches=tuple(branches),
            endpoints=tuple(endpoints),
        ),
    )


# ==============================================
# EFFECTIVE ISOLATED-PROCESS VALUES
# ==============================================


def environment(*, purpose: Purpose = "rehearsal") -> dict[str, str]:
    """Supply only synthetic process values, without reading the real .env."""
    return {
        "APP_ENV": "development",
        "DATABASE_TARGET": "development",
        "DEBUG": "false",
        "DB_ECHO": "false",
        "OIDC_DIAGNOSTICS_ENABLED": "false",
        "OIDC_ALLOW_LOCAL_HTTP": "false",
        "TEST_DATABASE_PROJECT_ID": PROJECT_ID,
        "TEST_DATABASE_BRANCH_ID": f"br-synthetic-{purpose}",
        "TEST_DATABASE_ENDPOINT_ID": f"ep-synthetic-{purpose}",
        "PROTECTED_DATABASE_BRANCH_ID": PRODUCTION_BRANCH_ID,
        "PROTECTED_DATABASE_ENDPOINT_ID": "ep-synthetic-production",
    }


# ==============================================
# SECRET-FREE SYNTHETIC URL
# ==============================================


def url(*, purpose: Purpose = "rehearsal", pooler: bool = False) -> str:
    """Return a nonconnecting fake target with no real credentials."""
    alias = "-pooler" if pooler else ""
    return f"postgresql+asyncpg://ep-synthetic-{purpose}{alias}.{DIRECT_SUFFIX}/neondb_test"


# ==============================================
# POSITIVE PURPOSE AND ENDPOINT ADMISSION
# ==============================================


@pytest.mark.parametrize(
    "purpose,operation",
    [(item, "inventory") for item in PURPOSES] + [("rehearsal", "e1")],
)
@pytest.mark.parametrize("pooler", [False, True])
def test_correct_destination(
    manifest: RehearsalManifest, purpose: Purpose, operation: Operation, pooler: bool
) -> None:
    """Accept B/W/V read-only admission and only W's future E1 destination."""
    result = admit_destination(
        manifest=manifest,
        approved_sha256=manifest_sha256(manifest=manifest),
        purpose=purpose,
        operation=operation,
        database_url=url(purpose=purpose, pooler=pooler),
        environment=environment(purpose=purpose),
        now=NOW,
        equivalence=equivalence(manifest=manifest) if operation == "e1" else None,
    )
    assert result.branch_id == f"br-synthetic-{purpose}"
    assert result.initial_revision == START_REVISION
    assert "database_url" not in result.model_dump()


# ==============================================
# BASELINE AND RECOVERY-PROOF WRITE EXCLUSION
# ==============================================


@pytest.mark.parametrize("purpose", ["baseline", "recovery-proof"])
def test_b_and_v_cannot_receive_e1(
    manifest: RehearsalManifest, purpose: Purpose
) -> None:
    """A valid reference manifest and URL never authorize E1 on B or V."""
    with pytest.raises(UnsafeTestDatabaseError, match="purpose_operation_denied"):
        admit_destination(
            manifest=manifest,
            approved_sha256=manifest_sha256(manifest=manifest),
            purpose=purpose,
            operation="e1",
            database_url=url(purpose=purpose),
            environment=environment(purpose=purpose),
            now=NOW,
        )


# ==============================================
# SOURCE AND UNKNOWN ENDPOINT EXCLUSION
# ==============================================


@pytest.mark.parametrize(
    "endpoint",
    [
        "ep-synthetic-production",
        "ep-synthetic-production-replica",
        DEVELOPMENT_ENDPOINT_ID,
        "ep-synthetic-development-replica",
        "ep-synthetic-baseline",
        "ep-synthetic-recovery-proof",
        "ep-unknown",
    ],
)
@pytest.mark.parametrize("pooler", [False, True])
def test_forbidden_endpoint_url(
    manifest: RehearsalManifest, endpoint: str, pooler: bool
) -> None:
    """Reject both source branches' primary/replica/pooler and unapproved endpoints."""
    alias = "-pooler" if pooler else ""
    with pytest.raises(UnsafeTestDatabaseError):
        admit_destination(
            manifest=manifest,
            approved_sha256=manifest_sha256(manifest=manifest),
            purpose="rehearsal",
            operation="e1",
            database_url=f"postgresql+asyncpg://{endpoint}{alias}.{DIRECT_SUFFIX}/neondb_test",
            environment=environment(),
            now=NOW,
        )


# ==============================================
# BAD DATABASE, ROUTING, HOST AND DRIVER
# ==============================================


@pytest.mark.parametrize(
    "bad_url",
    [
        url().replace("neondb_test", "neondb"),
        url().replace("postgresql+asyncpg", "postgresql"),
        url().replace(DIRECT_SUFFIX, "different.neon.tech"),
        url().replace(DIRECT_SUFFIX, "example.invalid"),
        url().replace("/neondb_test", ":6543/neondb_test"),
        *[
            url() + f"?{key}=forbidden"
            for key in (
                "host",
                "options",
                "endpoint",
                "ssl",
                "sslmode",
                "application_name",
            )
        ],
        "not a URL",
    ],
)
def test_invalid_url(manifest: RehearsalManifest, bad_url: str) -> None:
    """Reject alternate database/driver/host/port and every query override."""
    with pytest.raises(UnsafeTestDatabaseError):
        admit_destination(
            manifest=manifest,
            approved_sha256=manifest_sha256(manifest=manifest),
            purpose="rehearsal",
            operation="e1",
            database_url=bad_url,
            environment=environment(),
            now=NOW,
        )


# ==============================================
# MISSING AND INHERITED PROCESS CONFIGURATION
# ==============================================


@pytest.mark.parametrize("key", list(environment()))
@pytest.mark.parametrize("missing", [False, True])
def test_incomplete_or_stale_environment(
    manifest: RehearsalManifest, key: str, missing: bool
) -> None:
    """Reject every missing setting and inherited mismatching terminal value."""
    values = environment()
    if missing:
        values.pop(key)
    else:
        values[key] = "release" if key == "DEBUG" else "incorrect"
    with pytest.raises(
        UnsafeTestDatabaseError, match="effective_process_configuration_mismatch"
    ):
        admit_destination(
            manifest=manifest,
            approved_sha256=manifest_sha256(manifest=manifest),
            purpose="rehearsal",
            operation="e1",
            database_url=url(),
            environment=values,
            now=NOW,
        )


# ==============================================
# PRODUCTION AND DEVELOPMENT BRANCH EXCLUSION
# ==============================================


@pytest.mark.parametrize(
    "branch", [PRODUCTION_BRANCH_ID, DEVELOPMENT_BRANCH_ID, "br-unknown"]
)
def test_source_branch_cannot_be_w(manifest: RehearsalManifest, branch: str) -> None:
    """Reject a manifest assigning W to an excluded or unknown branch."""
    data = manifest.model_dump(mode="json")
    data["resources"][1]["branch_id"] = branch
    altered = RehearsalManifest.model_validate_json(json.dumps(data))
    with pytest.raises(UnsafeTestDatabaseError):
        validate_manifest(
            manifest=altered, approved_sha256=manifest_sha256(manifest=altered), now=NOW
        )


# ==============================================
# MALFORMED AND DRIFTED MANIFESTS
# ==============================================


@pytest.mark.parametrize(
    "case",
    [
        "project",
        "protected_typo",
        "development",
        "initial",
        "target",
        "incomplete",
        "future",
        "stale",
        "source_hash",
        "missing_source",
        "missing_primary",
        "duplicate_branch",
        "duplicate_endpoint",
        "duplicate_resource",
        "missing_resource",
        "wrong_parent",
        "wrong_endpoint_branch",
        "missing_endpoint",
        "wrong_fork",
        "expired",
        "near_expiry",
        "long_expiry",
        "baseline_expiry",
        "missing_expiry",
        "expired_review",
        "naive_time",
        "noncanonical_host",
        "purpose_swap",
        "extra_compute",
        "review_after_expiry",
    ],
)
def test_bad_manifest(manifest: RehearsalManifest, case: str) -> None:
    """Reject self-consistent rehashed unsafe declarations as well as hash drift."""
    data = manifest.model_dump(mode="json")
    evidence = data["control_plane"]
    resources = data["resources"]
    if case == "project":
        data["project_id"] = "wrong-project"
    elif case == "protected_typo":
        data["production_branch_id"] = "br-plain-firefly-as17li6w"
    elif case == "development":
        data["development_branch_id"] = "br-other-development"
    elif case == "initial":
        data["initial_revision"] = E1_REVISION
    elif case == "target":
        data["target_revision"] = "head"
    elif case == "incomplete":
        evidence["complete"] = False
    elif case == "future":
        evidence["observed_at"] = (NOW + timedelta(seconds=1)).isoformat()
    elif case == "stale":
        evidence["observed_at"] = (NOW - timedelta(hours=2)).isoformat()
    elif case == "source_hash":
        evidence["source_sha256"] = ""
    elif case == "missing_source":
        evidence["branches"].pop(0)
    elif case == "missing_primary":
        evidence["endpoints"][0]["primary"] = False
    elif case == "duplicate_branch":
        evidence["branches"].append(evidence["branches"][0])
    elif case == "duplicate_endpoint":
        evidence["endpoints"].append(evidence["endpoints"][0])
    elif case == "duplicate_resource":
        resources[1]["purpose"] = "baseline"
    elif case == "missing_resource":
        resources.pop()
    elif case == "wrong_parent":
        resources[1]["parent_id"] = DEVELOPMENT_BRANCH_ID
    elif case == "wrong_endpoint_branch":
        evidence["endpoints"][-2]["branch_id"] = PRODUCTION_BRANCH_ID
    elif case == "missing_endpoint":
        evidence["endpoints"].pop(-2)
    elif case == "wrong_fork":
        resources[1]["fork_lsn"] = "0/C"
    elif case == "expired":
        resources[1]["expires_at"] = NOW.isoformat()
    elif case == "near_expiry":
        resources[1]["expires_at"] = (NOW + timedelta(hours=2)).isoformat()
    elif case == "long_expiry":
        resources[1]["expires_at"] = (NOW + timedelta(hours=48)).isoformat()
    elif case == "baseline_expiry":
        resources[0]["expires_at"] = (NOW + timedelta(hours=24)).isoformat()
    elif case == "missing_expiry":
        resources[1]["expires_at"] = None
    elif case == "expired_review":
        resources[0]["review_due_at"] = NOW.isoformat()
    elif case == "naive_time":
        evidence["observed_at"] = NOW.replace(tzinfo=None).isoformat()
    elif case == "noncanonical_host":
        evidence["endpoints"][-2]["direct_host"] = "alias.example.invalid"
    elif case == "purpose_swap":
        resources[0]["purpose"], resources[1]["purpose"] = "rehearsal", "baseline"
    elif case == "extra_compute":
        replica = dict(evidence["endpoints"][-2])
        replica["endpoint_id"] = "ep-extra-rehearsal-replica"
        replica["direct_host"] = f"ep-extra-rehearsal-replica.{DIRECT_SUFFIX}"
        replica["primary"] = False
        evidence["endpoints"].append(replica)
    elif case == "review_after_expiry":
        resources[1]["review_due_at"] = resources[1]["expires_at"]
    altered = RehearsalManifest.model_validate_json(json.dumps(data))
    with pytest.raises(UnsafeTestDatabaseError):
        validate_manifest(
            manifest=altered, approved_sha256=manifest_sha256(manifest=altered), now=NOW
        )


# ==============================================
# IMMUTABILITY, SCHEMA AND APPROVAL SEPARATION
# ==============================================


def test_manifest_freeze_and_approval(manifest: RehearsalManifest) -> None:
    """Require separate hash approval and frozen nested secret-free structures."""
    with pytest.raises(ValidationError):
        manifest.resources[0].branch_id = "br-other"
    with pytest.raises(UnsafeTestDatabaseError, match="manifest_approval_mismatch"):
        validate_manifest(manifest=manifest, approved_sha256="b" * 64, now=NOW)
    data = manifest.model_dump(mode="json")
    data["database_url"] = "forbidden"
    with pytest.raises(ValidationError):
        RehearsalManifest.model_validate_json(json.dumps(data))
    del data["database_url"]
    del data["resources"][0]["branch_id"]
    with pytest.raises(ValidationError):
        RehearsalManifest.model_validate_json(json.dumps(data))


# ==============================================
# FAKE PINNED DATABASE CONNECTION
# ==============================================


def connection(*, versions: list[str] | None = None) -> MagicMock:
    """Mock SELECT results without instantiating an engine or SQL backend."""
    conn = MagicMock(spec=Connection)
    conn.dialect = MagicMock()
    conn.engine = MagicMock()
    conn.dialect.name = "postgresql"
    conn.in_transaction.return_value = True
    conn.get_execution_options.return_value = {}
    conn.engine.url = make_url(url())
    readonly, database, identity, revision = (MagicMock() for _ in range(4))
    readonly.scalar_one.return_value = "on"
    database.scalar_one.return_value = "neondb_test"
    identity.mappings.return_value.all.return_value = [
        {
            "name": name,
            "setting": value,
            "context": "postmaster",
            "vartype": "string",
            "source": "configuration file",
            "reset_val": value,
            "pending_restart": False,
        }
        for name, value in {
            "neon.endpoint_id": "ep-synthetic-rehearsal",
            "neon.branch_id": "br-synthetic-rehearsal",
            "neon.project_id": PROJECT_ID,
        }.items()
    ]
    revision.scalars.return_value.all.return_value = (
        [START_REVISION] if versions is None else versions
    )
    conn.execute.side_effect = [readonly, database, identity, revision]
    return conn


# ==============================================
# SAME-CONNECTION IDENTITY AND EXACT PARENT
# ==============================================


@pytest.mark.parametrize(
    "versions",
    [
        [START_REVISION],
        [],
        [START_REVISION, START_REVISION],
        [E1_REVISION],
        ["c413b7918a20"],
    ],
)
def test_live_parent_observation(
    manifest: RehearsalManifest, versions: list[str]
) -> None:
    """Exercise the real identity helper using fake read-only result rows."""
    conn = connection(versions=versions)
    arguments = {
        "manifest": manifest,
        "approved_sha256": manifest_sha256(manifest=manifest),
        "purpose": "rehearsal",
        "operation": "e1",
        "environment": environment(),
        "now": NOW,
        "equivalence": equivalence(manifest=manifest),
    }
    if versions == [START_REVISION]:
        result = inspect_admitted_connection(cast(Connection, conn), **arguments)
        assert result.branch_id == "br-synthetic-rehearsal"
    else:
        with pytest.raises(
            UnsafeTestDatabaseError, match="exact_initial_revision_required"
        ):
            inspect_admitted_connection(cast(Connection, conn), **arguments)
    assert all(
        str(call.args[0]).startswith("SELECT ") for call in conn.execute.call_args_list
    )
    conn.commit.assert_not_called()
    conn.rollback.assert_not_called()


# ==============================================
# READ-ONLY IDENTITY FAILURE PATHS
# ==============================================


@pytest.mark.parametrize(
    "case",
    [
        "dialect",
        "transaction",
        "autocommit",
        "readonly",
        "database",
        "branch",
        "endpoint",
        "project",
        "session_override",
        "restart",
        "connection_url",
    ],
)
def test_connection_refusal(manifest: RehearsalManifest, case: str) -> None:
    """Refuse substituted connections and identity settings before any mutation."""
    conn = connection()
    results = list(conn.execute.side_effect)
    if case == "dialect":
        conn.dialect.name = "sqlite"
    elif case == "transaction":
        conn.in_transaction.return_value = False
    elif case == "autocommit":
        conn.get_execution_options.return_value = {"isolation_level": "AUTOCOMMIT"}
    elif case == "readonly":
        results[0].scalar_one.return_value = "off"
    elif case == "database":
        results[1].scalar_one.return_value = "neondb"
    elif case == "connection_url":
        conn.engine.url = make_url(url(purpose="baseline"))
    else:
        rows = results[2].mappings.return_value.all.return_value
        if case in {"branch", "endpoint", "project"}:
            row = next(item for item in rows if item["name"] == f"neon.{case}_id")
            row["setting"] = PRODUCTION_BRANCH_ID if case == "branch" else "wrong"
        elif case == "session_override":
            rows[1]["source"] = "session"
        elif case == "restart":
            rows[1]["pending_restart"] = True
    conn.execute.side_effect = results
    with pytest.raises(UnsafeTestDatabaseError):
        inspect_admitted_connection(
            cast(Connection, conn),
            manifest=manifest,
            approved_sha256=manifest_sha256(manifest=manifest),
            purpose="rehearsal",
            operation="e1",
            environment=environment(),
            now=NOW,
            equivalence=equivalence(manifest=manifest),
        )
    assert all(
        str(call.args[0]).startswith("SELECT ") for call in conn.execute.call_args_list
    )


# ==============================================
# CREDENTIAL REDACTION BOUNDARY
# ==============================================


def test_url_values_are_never_reported(manifest: RehearsalManifest) -> None:
    """Ensure a synthetic sensitive value never appears in refusal messages."""
    secret = "synthetic-sensitive-test-value"
    with pytest.raises(UnsafeTestDatabaseError) as error:
        admit_destination(
            manifest=manifest,
            approved_sha256=manifest_sha256(manifest=manifest),
            purpose="rehearsal",
            operation="e1",
            database_url=f"postgresql+asyncpg://user:{secret}@ep-unknown.{DIRECT_SUFFIX}/neondb_test",
            environment=environment(),
            now=NOW,
        )
    assert secret not in str(error.value)
    assert secret not in manifest.model_dump_json()


# ==============================================
# STRICT PARSING AND SECRET-SAFE FAILURE
# ==============================================


def test_manifest_parser(manifest: RehearsalManifest) -> None:
    """Round-trip the contract and refuse malformed, incomplete or secret fields."""
    assert parse_manifest(payload=manifest.model_dump_json()) == manifest
    secret = "synthetic-sensitive-test-value"
    for payload in ("{}", "invalid", json.dumps({"secret": secret}), " " * 262145):
        with pytest.raises(UnsafeTestDatabaseError) as error:
            parse_manifest(payload=payload)
        assert secret not in str(error.value)


# ==============================================
# VERIFIED TLS AND BOUNDED READ-ONLY DEFAULTS
# ==============================================


def test_read_only_connection_arguments() -> None:
    """Require certificate/hostname validation and retain the central safeguards."""
    arguments = read_only_connection_arguments()
    assert arguments["ssl"].verify_mode == ssl.CERT_REQUIRED
    assert arguments["ssl"].check_hostname is True
    assert arguments["server_settings"]["default_transaction_read_only"] == "on"
    assert arguments["server_settings"]["lock_timeout"] == "5000"
    assert arguments["server_settings"]["statement_timeout"] == "60000"
    assert arguments["server_settings"]["timezone"] == "UTC"
    assert arguments["prepared_statement_cache_size"] == 0


# ==============================================
# FIRST-BASELINE ADMISSION BEFORE CHILD CREATION
# ==============================================


def test_baseline_only_stage(manifest: RehearsalManifest) -> None:
    """Permit B inventory before W/V exist, without fabricating future IDs."""
    data = manifest.model_dump(mode="json")
    data["stage"] = "baseline-only"
    data["resources"] = data["resources"][:1]
    data["control_plane"]["branches"] = data["control_plane"]["branches"][:3]
    data["control_plane"]["endpoints"] = data["control_plane"]["endpoints"][:5]
    initial = parse_manifest(payload=json.dumps(data))
    digest = manifest_sha256(manifest=initial)
    observed = admit_destination(
        manifest=initial,
        approved_sha256=digest,
        purpose="baseline",
        operation="inventory",
        database_url=url(purpose="baseline"),
        environment=environment(purpose="baseline"),
        now=NOW,
    )
    assert observed.purpose == "baseline"
    for purpose in PURPOSES:
        with pytest.raises(UnsafeTestDatabaseError, match="purpose_operation_denied"):
            admit_destination(
                manifest=initial,
                approved_sha256=digest,
                purpose=purpose,
                operation="e1",
                database_url=url(purpose=purpose),
                environment=environment(purpose=purpose),
                now=NOW,
            )
    data["stage"] = "complete"
    incomplete = parse_manifest(payload=json.dumps(data))
    with pytest.raises(
        UnsafeTestDatabaseError, match="distinct_stage_resources_required"
    ):
        validate_manifest(
            manifest=incomplete,
            approved_sha256=manifest_sha256(manifest=incomplete),
            now=NOW,
        )


# ==============================================
# COMPLETE SYNTHETIC READ-ONLY OBSERVATIONS
# ==============================================


def reports(*, manifest: RehearsalManifest) -> list[dict[str, Any]]:
    """Provide three isolated synthetic inventories, never real database rows."""
    digest = hashlib.sha256(b"synthetic-state").hexdigest()
    tables = {
        **{
            f"synthetic_{number:02}": {
                "rows": 0,
                "sha256": digest,
                "columns": ["id"],
                "primary_key": ["id"],
            }
            for number in range(46)
        },
        "alembic_version": {
            "rows": 1,
            "sha256": digest,
            "columns": ["version_num"],
            "primary_key": ["version_num"],
        },
    }
    categories = (
        "columns",
        "constraints",
        "indexes",
        "triggers",
        "routines",
        "relations",
        "schemas",
        "database_privileges",
        "roles",
        "role_memberships",
        "default_privileges",
        "rls",
        "sequence_definitions",
    )
    catalogs = {
        name: {
            "count": (
                47 if name == "columns" else 43 if name == "sequence_definitions" else 0
            ),
            "sha256": digest,
        }
        for name in categories
    }
    sequences = {
        f"synthetic_{number:02}_seq": {
            "relname": f"synthetic_{number:02}_seq",
            "last_value": 1,
            "is_called": False,
        }
        for number in range(43)
    }
    return [
        {
            "purpose": resource.purpose,
            "branch_id": resource.branch_id,
            "endpoint_id": resource.endpoint_id,
            "manifest_sha256": manifest_sha256(manifest=manifest),
            "revision": START_REVISION,
            "finished_at": NOW.isoformat(),
            "read_only": True,
            "transaction_rolled_back": True,
            "tables": deepcopy(tables),
            "catalogs": deepcopy(catalogs),
            "sequences": deepcopy(sequences),
            "server_version": "18.6",
        }
        for resource in manifest.resources
    ]


# ==============================================
# VERIFIED SYNTHETIC EQUIVALENCE FOR POSITIVE E1 ADMISSION
# ==============================================


def equivalence(*, manifest: RehearsalManifest) -> InitialStateEquivalence:
    """Generate an actual comparison result from the complete synthetic fixtures."""
    return verify_initial_equivalence(
        manifest=manifest,
        approved_sha256=manifest_sha256(manifest=manifest),
        reports=reports(manifest=manifest),
        now=NOW,
    )


# ==============================================
# DIFFERENT HEAD LSNS DO NOT SUBSTITUTE FOR STATE COMPARISON
# ==============================================


def test_different_lsns_require_logical_equivalence(
    manifest: RehearsalManifest,
) -> None:
    """Accept distinct documented forks only with exact lineage and real evidence."""
    data = manifest.model_dump(mode="json")
    data["resources"][2]["fork_lsn"] = "0/C"
    data["control_plane"]["branches"][-1]["fork_lsn"] = "0/C"
    revised = parse_manifest(payload=json.dumps(data))
    digest = manifest_sha256(manifest=revised)
    assert validate_manifest(manifest=revised, approved_sha256=digest, now=NOW)
    with pytest.raises(
        UnsafeTestDatabaseError, match="initial_state_equivalence_required"
    ):
        admit_destination(
            manifest=revised,
            approved_sha256=digest,
            purpose="rehearsal",
            operation="e1",
            database_url=url(),
            environment=environment(),
            now=NOW,
        )
    proof = equivalence(manifest=revised)
    assert (
        proof.baseline.logical_state_sha256 == proof.recovery_proof.logical_state_sha256
    )
    assert admit_destination(
        manifest=revised,
        approved_sha256=digest,
        purpose="rehearsal",
        operation="e1",
        database_url=url(),
        environment=environment(),
        now=NOW,
        equivalence=proof,
    )


# ==============================================
# ANY UNEXPLAINED LOGICAL OR AUTHORIZATION DIVERGENCE DENIES G1
# ==============================================


@pytest.mark.parametrize(
    "case",
    [
        "data",
        "rows",
        "sequence",
        "sequence_called",
        "constraints",
        "indexes",
        "schemas",
        "roles",
        "role_memberships",
        "default_privileges",
        "rls",
        "columns",
        "table_columns",
        "revision",
        "table_missing",
        "sequence_missing",
        "catalog_missing",
        "hash_missing",
        "duplicate_purpose",
        "branch",
        "endpoint",
        "manifest",
        "read_only",
        "rollback",
        "stale",
        "future",
    ],
)
def test_initial_state_divergence(manifest: RehearsalManifest, case: str) -> None:
    """Refuse incomplete, stale, substituted or unequal observations by default."""
    observed = reports(manifest=manifest)
    target = observed[2]
    if case == "data":
        target["tables"]["synthetic_00"]["sha256"] = "b" * 64
    elif case == "rows":
        target["tables"]["synthetic_00"]["rows"] = 1
    elif case == "sequence":
        target["sequences"]["synthetic_00_seq"]["last_value"] = 2
    elif case == "sequence_called":
        target["sequences"]["synthetic_00_seq"]["is_called"] = True
    elif case in {
        "constraints",
        "indexes",
        "schemas",
        "roles",
        "role_memberships",
        "default_privileges",
        "rls",
        "columns",
    }:
        target["catalogs"][case]["sha256"] = "b" * 64
    elif case == "table_columns":
        target["tables"]["synthetic_00"]["columns"] = ["id", "extra"]
    elif case == "revision":
        target["revision"] = E1_REVISION
    elif case == "table_missing":
        target["tables"].pop("synthetic_00")
    elif case == "sequence_missing":
        target["sequences"].pop("synthetic_00_seq")
    elif case == "catalog_missing":
        target["catalogs"].pop("indexes")
    elif case == "hash_missing":
        target["tables"]["synthetic_00"]["sha256"] = ""
    elif case == "duplicate_purpose":
        target["purpose"] = "baseline"
    elif case == "branch":
        target["branch_id"] = PRODUCTION_BRANCH_ID
    elif case == "endpoint":
        target["endpoint_id"] = DEVELOPMENT_ENDPOINT_ID
    elif case == "manifest":
        target["manifest_sha256"] = "b" * 64
    elif case == "read_only":
        target["read_only"] = False
    elif case == "rollback":
        target["transaction_rolled_back"] = False
    elif case == "stale":
        target["finished_at"] = (NOW - timedelta(hours=2)).isoformat()
    elif case == "future":
        target["finished_at"] = (NOW + timedelta(seconds=1)).isoformat()
    with pytest.raises(UnsafeTestDatabaseError):
        verify_initial_equivalence(
            manifest=manifest,
            approved_sha256=manifest_sha256(manifest=manifest),
            reports=observed,
            now=NOW,
        )


# ==============================================
# WRONG DIRECT PARENT REFUSAL WITH CONSISTENT REHASHED EVIDENCE
# ==============================================


@pytest.mark.parametrize(
    "parent",
    [PRODUCTION_BRANCH_ID, DEVELOPMENT_BRANCH_ID, "br-synthetic-recovery-proof"],
)
def test_wrong_direct_parent(manifest: RehearsalManifest, parent: str) -> None:
    """Reject a W parent other than B even if the declaration matches the catalog."""
    data = manifest.model_dump(mode="json")
    data["resources"][1]["parent_id"] = parent
    data["control_plane"]["branches"][-2]["parent_id"] = parent
    revised = parse_manifest(payload=json.dumps(data))
    with pytest.raises(
        UnsafeTestDatabaseError, match="resource_identity_or_lineage_mismatch"
    ):
        validate_manifest(
            manifest=revised, approved_sha256=manifest_sha256(manifest=revised), now=NOW
        )


# ==============================================
# PROOF REUSE AND TAMPERING REFUSAL
# ==============================================


@pytest.mark.parametrize("case", ["manifest", "time", "state", "endpoint"])
def test_equivalence_cannot_be_reused_or_changed(
    manifest: RehearsalManifest, case: str
) -> None:
    """Bind E1 destination admission to fresh compared identities and state."""
    data = equivalence(manifest=manifest).model_dump(mode="json")
    if case == "manifest":
        data["manifest_sha256"] = "b" * 64
    elif case == "time":
        data["verified_at"] = (NOW - timedelta(hours=2)).isoformat()
    elif case == "state":
        data["recovery_proof"]["logical_state_sha256"] = "b" * 64
    elif case == "endpoint":
        data["recovery_proof"]["endpoint_id"] = DEVELOPMENT_ENDPOINT_ID
    proof = InitialStateEquivalence.model_validate_json(json.dumps(data))
    with pytest.raises(UnsafeTestDatabaseError):
        admit_destination(
            manifest=manifest,
            approved_sha256=manifest_sha256(manifest=manifest),
            purpose="rehearsal",
            operation="e1",
            database_url=url(),
            environment=environment(),
            now=NOW,
            equivalence=proof,
        )
