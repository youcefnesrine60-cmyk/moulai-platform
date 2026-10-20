# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Opt-in B/W/V admission contracts; no engine, migration or API client.

An independently approved manifest pins operator-verified control-plane evidence.
Its hash detects changes, but is not an authorization signature. Admission never
grants G1 creation or G2 SQL execution authority. Existing guards remain mandatory.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import (
    Mapping,
    Sequence,
)
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Literal,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
)
from sqlalchemy import text
from sqlalchemy.engine import (
    Connection,
    make_url,
)

from app.core.test_database import (
    UnsafeTestDatabaseError,
    isolated_connection_arguments,
    read_test_database_identity,
    validate_test_branch_configuration,
    validated_test_database_url,
)

PROJECT_ID = "shiny-lab-60817779"
PRODUCTION_BRANCH_ID = "br-plain-firefly-as17il6w"
DEVELOPMENT_BRANCH_ID = "br-lively-truth-asga1dtk"
DEVELOPMENT_ENDPOINT_ID = "ep-quiet-rain-assrs0gv"
START_REVISION = "dce91870b4a2"
E1_REVISION = "e1b92b200001"
Purpose = Literal["baseline", "rehearsal", "recovery-proof"]
Operation = Literal["inventory", "e1"]
_BRANCH = re.compile(r"br-[a-z0-9]+(?:-[a-z0-9]+)*")
_ENDPOINT = re.compile(r"ep-[a-z0-9]+(?:-[a-z0-9]+)*")
_HOST = re.compile(r"ep-[a-z0-9-]+\.[a-z0-9.-]+\.neon\.tech")
_SHA256 = re.compile(r"[a-f0-9]{64}")
_LSN = re.compile(r"[0-9A-F]+/[0-9A-F]+")
_CATALOG_CATEGORIES = frozenset(
    {
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
    }
)


# ==============================================
# IMMUTABLE SECRET-FREE RESOURCE CONTRACTS
# ==============================================


class Contract(BaseModel):
    """Forbid unknown/coerced fields and freeze every nested contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class BranchEvidence(Contract):
    """One entry from a complete approved project branch inventory."""

    branch_id: str
    parent_id: str | None
    fork_lsn: str | None


class EndpointEvidence(Contract):
    """Bind an exact direct host to its project-local branch and compute type."""

    endpoint_id: str
    branch_id: str
    direct_host: str
    primary: bool


class ControlPlaneEvidence(Contract):
    """Operator-reviewed complete inventory, including replica endpoints.

    Completeness and provenance must be checked against Neon before approval.
    Offline validation cannot authenticate an operator's claimed API evidence.
    """

    project_id: str
    observed_at: datetime
    complete: bool
    source_sha256: str
    branches: tuple[BranchEvidence, ...]
    endpoints: tuple[EndpointEvidence, ...]


class RehearsalResource(Contract):
    """An actual created resource; planned labels cannot substitute for IDs."""

    purpose: Purpose
    branch_id: str
    endpoint_id: str
    parent_id: str
    fork_lsn: str
    created_at: datetime
    expires_at: datetime | None
    review_due_at: datetime


class RehearsalManifest(Contract):
    """Exact post-creation topology and evidence submitted for approval."""

    version: Literal[1]
    stage: Literal["baseline-only", "complete"]
    project_id: str
    production_branch_id: str
    development_branch_id: str
    database: Literal["neondb_test"]
    initial_revision: str
    target_revision: str
    resources: tuple[RehearsalResource, ...]
    control_plane: ControlPlaneEvidence


class AdmissionObservation(Contract):
    """Secret-free observation, never a reusable migration execution permit."""

    manifest_sha256: str
    purpose: Purpose
    operation: Operation
    branch_id: str
    endpoint_id: str
    initial_revision: str


class InitialStateDigest(Contract):
    """Immutable attested inventory fingerprint, without business row values."""

    purpose: Purpose
    branch_id: str
    endpoint_id: str
    manifest_sha256: str
    revision: str
    observed_at: datetime
    logical_state_sha256: str


class InitialStateEquivalence(Contract):
    """Compared initial states; not incident recovery or G2 write authorization."""

    manifest_sha256: str
    verified_at: datetime
    baseline: InitialStateDigest
    rehearsal: InitialStateDigest
    recovery_proof: InitialStateDigest


# ==============================================
# SAFE REFUSALS AND MANIFEST FINGERPRINT
# ==============================================


def require(*, condition: bool, code: str) -> None:
    """Expose only fixed error codes, never supplied URLs or field values."""
    if not condition:
        raise UnsafeTestDatabaseError(code)


# ==============================================
# CANONICAL APPROVAL HASH
# ==============================================


def manifest_sha256(*, manifest: RehearsalManifest) -> str:
    """Fingerprint a validated immutable structure; do not auto-approve it."""
    payload = json.dumps(
        manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ==============================================
# BOUNDED SECRET-SAFE MANIFEST PARSING
# ==============================================


def parse_manifest(*, payload: str) -> RehearsalManifest:
    """Parse the strict contract without echoing untrusted fields on failure."""
    require(condition=len(payload) <= 262144, code="manifest_size_limit")
    try:
        return RehearsalManifest.model_validate_json(payload)
    except ValidationError:
        raise UnsafeTestDatabaseError("invalid_resource_manifest") from None


# ==============================================
# VERIFIED TLS FOR FUTURE READ-ONLY COLLECTION
# ==============================================


def read_only_connection_arguments() -> dict[str, Any]:
    """Reuse verified TLS and bound future inventory sessions; open nothing."""
    arguments = isolated_connection_arguments()
    arguments["server_settings"].update(
        {
            "default_transaction_read_only": "on",
            "lock_timeout": "5000",
            "statement_timeout": "60000",
        }
    )
    return arguments


# ==============================================
# UTC TIME ADMISSION
# ==============================================


def require_utc(*, value: datetime) -> None:
    """Reject naive and non-UTC timestamps before temporal comparisons."""
    require(condition=value.utcoffset() == timedelta(0), code="utc_time_required")


# ==============================================
# COMPLETE TOPOLOGY AND EXPIRATION ADMISSION
# ==============================================


def validate_manifest(
    *, manifest: RehearsalManifest, approved_sha256: str, now: datetime
) -> dict[Purpose, RehearsalResource]:
    """Validate exact sources, complete endpoint inventory and bounded lifetimes.

    B has no automatic expiration: its review deadline is not a deletion job.
    W/V expire within 24 hours; an expired review or two-hour safety margin
    closes admission. Fresh reviewed evidence is required at least hourly.
    """
    require_utc(value=now)
    require(
        condition=bool(_SHA256.fullmatch(approved_sha256))
        and hmac.compare_digest(manifest_sha256(manifest=manifest), approved_sha256),
        code="manifest_approval_mismatch",
    )
    evidence = manifest.control_plane
    require_utc(value=evidence.observed_at)
    require(
        condition=manifest.project_id == evidence.project_id == PROJECT_ID
        and manifest.production_branch_id == PRODUCTION_BRANCH_ID
        and manifest.development_branch_id == DEVELOPMENT_BRANCH_ID
        and manifest.initial_revision == START_REVISION
        and manifest.target_revision == E1_REVISION,
        code="project_source_or_revision_mismatch",
    )
    require(
        condition=evidence.complete
        and bool(_SHA256.fullmatch(evidence.source_sha256))
        and timedelta(0) <= now - evidence.observed_at <= timedelta(hours=1),
        code="incomplete_or_stale_control_plane_evidence",
    )
    branches = {item.branch_id: item for item in evidence.branches}
    endpoints = {item.endpoint_id: item for item in evidence.endpoints}
    require(
        condition=len(branches) == len(evidence.branches)
        and len(endpoints) == len(evidence.endpoints)
        and len({item.direct_host for item in evidence.endpoints}) == len(endpoints)
        and {PRODUCTION_BRANCH_ID, DEVELOPMENT_BRANCH_ID}.issubset(branches),
        code="ambiguous_or_missing_inventory",
    )
    for branch in branches.values():
        require(
            condition=bool(_BRANCH.fullmatch(branch.branch_id))
            and (branch.parent_id is None or branch.parent_id in branches),
            code="invalid_branch_inventory",
        )
    require(
        condition=branches[DEVELOPMENT_BRANCH_ID].parent_id == PRODUCTION_BRANCH_ID,
        code="source_parent_mismatch",
    )
    for endpoint in endpoints.values():
        require(
            condition=bool(_ENDPOINT.fullmatch(endpoint.endpoint_id))
            and not endpoint.endpoint_id.endswith("-pooler")
            and endpoint.branch_id in branches
            and bool(_HOST.fullmatch(endpoint.direct_host))
            and endpoint.direct_host.split(".", 1)[0] == endpoint.endpoint_id,
            code="invalid_endpoint_inventory",
        )
    for source in (PRODUCTION_BRANCH_ID, DEVELOPMENT_BRANCH_ID):
        require(
            condition=sum(
                endpoint.primary and endpoint.branch_id == source
                for endpoint in endpoints.values()
            )
            == 1,
            code="source_primary_inventory_required",
        )
    require(
        condition=DEVELOPMENT_ENDPOINT_ID in endpoints
        and endpoints[DEVELOPMENT_ENDPOINT_ID].branch_id == DEVELOPMENT_BRANCH_ID
        and endpoints[DEVELOPMENT_ENDPOINT_ID].primary,
        code="development_endpoint_mismatch",
    )
    resources = {item.purpose: item for item in manifest.resources}
    expected_purposes = (
        {"baseline"}
        if manifest.stage == "baseline-only"
        else {"baseline", "rehearsal", "recovery-proof"}
    )
    require(
        condition=len(manifest.resources) == len(resources) == len(expected_purposes)
        and set(resources) == expected_purposes
        and len({item.branch_id for item in resources.values()}) == len(resources)
        and len({item.endpoint_id for item in resources.values()}) == len(resources),
        code="distinct_stage_resources_required",
    )
    for purpose, resource in resources.items():
        require_utc(value=resource.created_at)
        require_utc(value=resource.review_due_at)
        parent = (
            DEVELOPMENT_BRANCH_ID
            if purpose == "baseline"
            else resources["baseline"].branch_id
        )
        branch = branches.get(resource.branch_id)
        endpoint = endpoints.get(resource.endpoint_id)
        require(
            condition=resource.branch_id
            not in {PRODUCTION_BRANCH_ID, DEVELOPMENT_BRANCH_ID}
            and branch is not None
            and endpoint is not None
            and resource.parent_id == parent == branch.parent_id
            and bool(_LSN.fullmatch(resource.fork_lsn))
            and resource.fork_lsn == branch.fork_lsn
            and endpoint.branch_id == resource.branch_id
            and endpoint.primary
            and sum(item.branch_id == resource.branch_id for item in endpoints.values())
            == 1,
            code="resource_identity_or_lineage_mismatch",
        )
        require(
            condition=resource.created_at
            <= evidence.observed_at
            <= now
            < resource.review_due_at
            <= resource.created_at + timedelta(hours=72),
            code="resource_review_expired",
        )
        if purpose == "baseline":
            require(
                condition=resource.expires_at is None, code="baseline_must_be_retained"
            )
        else:
            require(condition=resource.expires_at is not None, code="expiry_required")
            assert resource.expires_at is not None
            require_utc(value=resource.expires_at)
            require(
                condition=now + timedelta(hours=2)
                < resource.expires_at
                <= resource.created_at + timedelta(hours=24)
                and resource.review_due_at <= resource.expires_at - timedelta(hours=2),
                code="unsafe_resource_expiration",
            )
    if manifest.stage == "complete":
        require(
            # Each fork remains pinned to its own verified control-plane LSN.
            # HEAD forks may differ; actual logical equivalence is checked below.
            condition=all(
                resources["baseline"].created_at <= resources[purpose].created_at
                for purpose in ("rehearsal", "recovery-proof")
            ),
            code="reference_creation_order_mismatch",
        )
    return resources


# ==============================================
# COMPLETE READ-ONLY INVENTORY FINGERPRINT
# ==============================================


def initial_state_digest(*, report: Mapping[str, Any]) -> InitialStateDigest:
    """Require complete counted data/catalog/sequence evidence before hashing.

    Reports come from the trusted read-only collector, not HTTP claims. No raw
    rows are accepted or exported. This validates completeness and consistency,
    not the authenticity of an arbitrary supplied file or its source process.
    """
    tables = report.get("tables")
    catalogs = report.get("catalogs")
    sequences = report.get("sequences")
    require(
        condition=isinstance(tables, dict)
        and len(tables) == 47
        and "alembic_version" in tables
        and isinstance(catalogs, dict)
        and set(catalogs) == _CATALOG_CATEGORIES
        and isinstance(sequences, dict)
        and len(sequences) == 43
        and report.get("revision") == START_REVISION
        and report.get("read_only") is True
        and report.get("transaction_rolled_back") is True,
        code="incomplete_initial_state_evidence",
    )
    for table, item in tables.items():
        require(
            condition=isinstance(table, str)
            and bool(table)
            and isinstance(item, dict)
            and type(item.get("rows")) is int
            and item["rows"] >= 0
            and isinstance(item.get("sha256"), str)
            and bool(_SHA256.fullmatch(item["sha256"]))
            and isinstance(item.get("primary_key"), list)
            and bool(item["primary_key"])
            and isinstance(item.get("columns"), list)
            and bool(item["columns"])
            and all(
                isinstance(name, str) and bool(name)
                for name in [*item["primary_key"], *item["columns"]]
            )
            and len(set(item["columns"])) == len(item["columns"])
            and set(item["primary_key"]).issubset(item["columns"]),
            code="invalid_table_fingerprint",
        )
    require(
        condition=tables["alembic_version"]["rows"] == 1,
        code="exact_initial_revision_required",
    )
    for item in catalogs.values():
        require(
            condition=isinstance(item, dict)
            and type(item.get("count")) is int
            and item["count"] >= 0
            and isinstance(item.get("sha256"), str)
            and bool(_SHA256.fullmatch(item["sha256"])),
            code="invalid_catalog_fingerprint",
        )
    require(
        condition=catalogs["sequence_definitions"]["count"] == 43
        and catalogs["columns"]["count"]
        == sum(len(item["columns"]) for item in tables.values()),
        code="inconsistent_inventory_counts",
    )
    for name, item in sequences.items():
        require(
            condition=isinstance(item, dict)
            and item.get("relname") == name
            and type(item.get("last_value")) is int
            and type(item.get("is_called")) is bool,
            code="invalid_sequence_fingerprint",
        )
    state = {
        "revision": report["revision"],
        "tables": tables,
        "catalogs": catalogs,
        "sequences": sequences,
        "server_version": report.get("server_version"),
    }
    digest = hashlib.sha256(
        json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    try:
        result = InitialStateDigest(
            purpose=report.get("purpose"),
            branch_id=report.get("branch_id"),
            endpoint_id=report.get("endpoint_id"),
            manifest_sha256=report.get("manifest_sha256"),
            revision=report["revision"],
            observed_at=datetime.fromisoformat(report.get("finished_at", "")),
            logical_state_sha256=digest,
        )
    except (ValidationError, TypeError, ValueError):
        raise UnsafeTestDatabaseError("invalid_initial_state_identity") from None
    require_utc(value=result.observed_at)
    return result


# ==============================================
# G1 LOGICAL STATE EQUIVALENCE, INDEPENDENT OF FORK LSN
# ==============================================


def verify_initial_equivalence(
    *,
    manifest: RehearsalManifest,
    approved_sha256: str,
    reports: Sequence[Mapping[str, Any]],
    now: datetime,
) -> InitialStateEquivalence:
    """Require real fresh observations on each exact B/W/V resource and equality.

    Different provenance LSNs are allowed. Missing/duplicate observations or any
    unexplained catalog, permissions, row, revision or sequence difference deny
    G1. Equal empty tables prove only the measured empty reference state.
    """
    resources = validate_manifest(
        manifest=manifest, approved_sha256=approved_sha256, now=now
    )
    require(
        condition=manifest.stage == "complete" and len(reports) == 3,
        code="three_initial_observations_required",
    )
    observations = [initial_state_digest(report=report) for report in reports]
    by_purpose = {item.purpose: item for item in observations}
    require(
        condition=set(by_purpose) == set(resources),
        code="three_initial_observations_required",
    )
    for purpose, observation in by_purpose.items():
        resource = resources[purpose]
        require(
            condition=observation.branch_id == resource.branch_id
            and observation.endpoint_id == resource.endpoint_id
            and observation.manifest_sha256 == approved_sha256
            and manifest.control_plane.observed_at <= observation.observed_at <= now
            and now - observation.observed_at <= timedelta(hours=1),
            code="initial_observation_identity_or_freshness_mismatch",
        )
    require(
        condition=len({item.logical_state_sha256 for item in observations}) == 1,
        code="initial_state_divergence",
    )
    return InitialStateEquivalence(
        manifest_sha256=approved_sha256,
        verified_at=now,
        baseline=by_purpose["baseline"],
        rehearsal=by_purpose["rehearsal"],
        recovery_proof=by_purpose["recovery-proof"],
    )


# ==============================================
# PRE-CONNECTION DESTINATION ADMISSION
# ==============================================


def admit_destination(
    *,
    manifest: RehearsalManifest,
    approved_sha256: str,
    purpose: Purpose,
    operation: Operation,
    database_url: str,
    environment: Mapping[str, str],
    now: datetime,
    equivalence: InitialStateEquivalence | None = None,
) -> AdmissionObservation:
    """Reuse existing guards, then require the exact purpose-bound destination.

    Callers supply effective fresh-process Settings as strings. No environment
    is loaded, changed or silently corrected here. Credential URLs stay outside
    manifests/observations. Only W can be admitted for a future E1 operation.
    """
    resources = validate_manifest(
        manifest=manifest, approved_sha256=approved_sha256, now=now
    )
    require(
        condition=purpose in resources
        and operation in {"inventory", "e1"}
        and (
            operation != "e1"
            or (purpose == "rehearsal" and manifest.stage == "complete")
        ),
        code="purpose_operation_denied",
    )
    resource = resources[purpose]
    endpoints = manifest.control_plane.endpoints
    endpoint = next(
        item for item in endpoints if item.endpoint_id == resource.endpoint_id
    )
    protected = next(
        item
        for item in endpoints
        if item.branch_id == PRODUCTION_BRANCH_ID and item.primary
    )
    expected = {
        "APP_ENV": "development",
        "DATABASE_TARGET": "development",
        "DEBUG": "false",
        "DB_ECHO": "false",
        "OIDC_DIAGNOSTICS_ENABLED": "false",
        "OIDC_ALLOW_LOCAL_HTTP": "false",
        "TEST_DATABASE_PROJECT_ID": PROJECT_ID,
        "TEST_DATABASE_BRANCH_ID": resource.branch_id,
        "TEST_DATABASE_ENDPOINT_ID": resource.endpoint_id,
        "PROTECTED_DATABASE_BRANCH_ID": PRODUCTION_BRANCH_ID,
        "PROTECTED_DATABASE_ENDPOINT_ID": protected.endpoint_id,
    }
    require(
        condition=all(environment.get(key) == value for key, value in expected.items()),
        code="effective_process_configuration_mismatch",
    )
    validate_test_branch_configuration(
        branch_id=resource.branch_id,
        project_id=manifest.project_id,
        protected_branch_id=PRODUCTION_BRANCH_ID,
    )
    validated_test_database_url(
        test_database_url=database_url,
        test_endpoint_id=resource.endpoint_id,
        protected_endpoint_id=protected.endpoint_id,
    )
    url = make_url(database_url)
    host_prefix, suffix = endpoint.direct_host.split(".", 1)
    require(
        condition=url.host in {endpoint.direct_host, f"{host_prefix}-pooler.{suffix}"}
        and url.port in {None, 5432}
        and not url.query,
        code="exact_host_port_or_query_mismatch",
    )
    if operation == "e1":
        require(
            condition=equivalence is not None, code="initial_state_equivalence_required"
        )
        assert equivalence is not None
        require_utc(value=equivalence.verified_at)
        require(
            condition=equivalence.manifest_sha256 == approved_sha256
            and manifest.control_plane.observed_at <= equivalence.verified_at <= now
            and now - equivalence.verified_at <= timedelta(hours=1),
            code="equivalence_manifest_or_freshness_mismatch",
        )
        observed = (
            equivalence.baseline,
            equivalence.rehearsal,
            equivalence.recovery_proof,
        )
        require(
            condition={item.purpose for item in observed} == set(resources)
            and len({item.logical_state_sha256 for item in observed}) == 1
            and all(
                item.manifest_sha256 == approved_sha256
                and item.branch_id == resources[item.purpose].branch_id
                and item.endpoint_id == resources[item.purpose].endpoint_id
                and item.revision == START_REVISION
                and manifest.control_plane.observed_at
                <= item.observed_at
                <= equivalence.verified_at
                for item in observed
            ),
            code="equivalence_resource_or_state_mismatch",
        )
    return AdmissionObservation(
        manifest_sha256=approved_sha256,
        purpose=purpose,
        operation=operation,
        branch_id=resource.branch_id,
        endpoint_id=resource.endpoint_id,
        initial_revision=START_REVISION,
    )


# ==============================================
# PINNED READ-ONLY CONNECTION OBSERVATION (DB HELPER)
# ==============================================


def inspect_admitted_connection(
    connection: Connection,
    *,
    manifest: RehearsalManifest,
    approved_sha256: str,
    purpose: Purpose,
    operation: Operation,
    environment: Mapping[str, str],
    now: datetime,
    equivalence: InitialStateEquivalence | None = None,
) -> AdmissionObservation:
    """Re-admit the actual connection, then SELECT identity and exact parent.

    This function neither opens nor starts/commits a transaction. It accepts an
    existing explicit read-only PostgreSQL transaction only. The returned value
    is evidence, not transferable authorization for a later write connection.
    """
    require(
        condition=connection.dialect.name == "postgresql"
        and connection.in_transaction()
        and connection.get_execution_options().get("isolation_level") != "AUTOCOMMIT",
        code="explicit_postgresql_transaction_required",
    )
    observation = admit_destination(
        manifest=manifest,
        approved_sha256=approved_sha256,
        purpose=purpose,
        operation=operation,
        database_url=connection.engine.url.render_as_string(hide_password=False),
        environment=environment,
        now=now,
        equivalence=equivalence,
    )
    require(
        condition=connection.execute(
            text("SELECT current_setting('transaction_read_only')")
        ).scalar_one()
        == "on",
        code="read_only_transaction_required",
    )
    read_test_database_identity(
        connection,
        endpoint_id=observation.endpoint_id,
        branch_id=observation.branch_id,
        project_id=PROJECT_ID,
        protected_branch_id=PRODUCTION_BRANCH_ID,
    )
    versions = (
        connection.execute(
            text("SELECT version_num FROM public.alembic_version LIMIT 2")
        )
        .scalars()
        .all()
    )
    require(
        condition=versions == [START_REVISION], code="exact_initial_revision_required"
    )
    return observation
