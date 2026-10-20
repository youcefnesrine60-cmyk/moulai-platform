# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""B1 SQLAlchemy schema contracts, isolated from unmigrated live mappings.

The shared declarative registry is reused; only metadata is staged separately.
Reference tables declare future FK targets, not mapped replacements or tables
to create. No engine, DDL execution, seed or startup registration occurs here.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    event,
    func,
    inspect,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    validates,
)

from app.core.security.tenant_types import (
    TENANT_ROLES,
    permission_ceiling,
    validate_issuer,
    validate_subject,
)
from app.models.base import Base

TENANT_METADATA = MetaData()


# ==============================================
# SQL VALUES
# ==============================================


def _sql_values(*, values: frozenset[str]) -> str:
    """Render trusted catalogue constants, never caller-provided SQL."""
    return ", ".join("'" + value.replace("'", "''") + "'" for value in sorted(values))


class TenantBase(Base):
    """Reuse the project registry without changing its live metadata."""

    __abstract__ = True
    metadata = TENANT_METADATA


class TenantRecord(TenantBase):
    """Provide conventional integer IDs and explicit UTC lifecycle timestamps."""

    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# These FK reference contracts are excluded from E1 CREATE TABLE output.
restaurant_reference = Table(
    "restaurants",
    TENANT_METADATA,
    Column("id", Integer, primary_key=True),
    Column("owner_id", Integer, nullable=False),
    Column(
        "organization_id",
        Integer,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    UniqueConstraint("organization_id", "id", name="uq_restaurants_org_id"),
    info={"external_reference": True},
)
admin_reference = Table(
    "admins",
    TENANT_METADATA,
    Column("id", Integer, primary_key=True),
    info={"external_reference": True},
)

# ==============================================
# IDENTITY, COMPANY AND POLICY
# ==============================================


class Identity(TenantRecord):
    """Store an exact issuer-qualified identity, never credentials."""

    __tablename__ = "identities"
    issuer: Mapped[str] = mapped_column(String(1024, collation="C"), nullable=False)
    subject: Mapped[str] = mapped_column(String(255, collation="C"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="suspended", server_default="suspended"
    )
    revision: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1"
    )
    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="uq_identities_issuer_subject"),
        CheckConstraint(
            "status IN ('active','suspended','retired')", name="ck_identity_status"
        ),
        CheckConstraint("revision > 0", name="ck_identity_revision"),
        CheckConstraint(
            "length(issuer) BETWEEN 1 AND 1024 AND issuer = trim(issuer) AND issuer LIKE 'https://%'",
            name="ck_identity_issuer",
        ),
        CheckConstraint(
            "length(subject) BETWEEN 1 AND 255 AND subject = trim(subject)",
            name="ck_identity_subject",
        ),
        CheckConstraint(
            "octet_length(issuer) = length(issuer) AND octet_length(subject) = length(subject) AND issuer !~ '[[:cntrl:]]' AND subject !~ '[[:cntrl:]]'",
            name="ck_identity_ascii",
        ).ddl_if(dialect="postgresql"),
    )

    # ==============================================
    # VALIDATE KEY
    # ==============================================

    @validates("issuer", "subject")
    def _validate_key(self, key: str, value: str) -> str:
        """Validate without normalization before values reach a database."""
        if key == "issuer":
            validate_issuer(issuer=value)
        else:
            validate_subject(subject=value)
        return value


class Organization(TenantRecord):
    """Represent a stable local business boundary, independent of Keycloak."""

    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )
    revision: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1"
    )
    tenant_enforced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 255 AND name = trim(name)",
            name="ck_org_name",
        ),
        CheckConstraint(
            "status IN ('draft','active','suspended','archived')", name="ck_org_status"
        ),
        CheckConstraint("revision > 0", name="ck_org_revision"),
        CheckConstraint(
            "status != 'active' OR tenant_enforced_at IS NOT NULL",
            name="ck_org_enforcement",
        ),
    )


class TenantRole(TenantBase):
    """Keep tenant role policy disjoint from platform administrators."""

    __tablename__ = "tenant_roles"
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    policy_revision: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1"
    )
    __table_args__ = (
        CheckConstraint(
            "code IN ('owner','manager','employee')", name="ck_tenant_role_code"
        ),
        CheckConstraint("policy_revision > 0", name="ck_tenant_role_revision"),
    )


class TenantRolePermission(TenantBase):
    """Store explicit permission rows with no inheritance or wildcard."""

    __tablename__ = "tenant_role_permissions"
    role_code: Mapped[str] = mapped_column(
        ForeignKey("tenant_roles.code", ondelete="RESTRICT"), primary_key=True
    )
    permission_code: Mapped[str] = mapped_column(String(80), primary_key=True)
    __table_args__ = (
        CheckConstraint(
            " OR ".join(
                f"(role_code = '{role}' AND permission_code IN ({_sql_values(values=permission_ceiling(role_code=role))}))"
                for role in sorted(TENANT_ROLES)
            ),
            name="ck_tenant_role_permission",
        ),
    )


# ==============================================
# MEMBERSHIP AND RESTAURANT GRANTS
# ==============================================


class OrganizationMembership(TenantRecord):
    """Preserve one stable identity/company association and enrollment history."""

    __tablename__ = "organization_memberships"
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    identity_id: Mapped[int] = mapped_column(
        ForeignKey("identities.id", ondelete="RESTRICT"), nullable=False
    )
    role_code: Mapped[str] = mapped_column(
        ForeignKey("tenant_roles.code", ondelete="RESTRICT"), nullable=False
    )
    access_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="explicit-grants",
        server_default="explicit-grants",
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    revision: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1"
    )
    enrollment_generation: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "identity_id", name="uq_membership_identity"
        ),
        UniqueConstraint(
            "organization_id", "id", "access_mode", name="uq_membership_mode"
        ),
        UniqueConstraint(
            "organization_id", "id", "identity_id", name="uq_membership_actor"
        ),
        CheckConstraint(
            "status IN ('pending','active','suspended','revoked')",
            name="ck_membership_status",
        ),
        CheckConstraint(
            "access_mode IN ('company-wide','explicit-grants')",
            name="ck_membership_mode",
        ),
        CheckConstraint(
            "role_code != 'owner' OR access_mode = 'company-wide'",
            name="ck_membership_owner_scope",
        ),
        CheckConstraint(
            "revision > 0 AND enrollment_generation > 0", name="ck_membership_revision"
        ),
        CheckConstraint(
            "status != 'active' OR (accepted_at IS NOT NULL AND activated_at IS NOT NULL)",
            name="ck_membership_acceptance",
        ),
        CheckConstraint(
            "status != 'suspended' OR suspended_at IS NOT NULL",
            name="ck_membership_suspension",
        ),
        CheckConstraint(
            "status != 'revoked' OR revoked_at IS NOT NULL",
            name="ck_membership_revocation",
        ),
        CheckConstraint(
            "status != 'pending' OR (accepted_at IS NULL AND activated_at IS NULL)",
            name="ck_membership_pending",
        ),
        Index(
            "ix_membership_identity_state", "identity_id", "status", "organization_id"
        ),
        Index("ix_membership_org_role", "organization_id", "status", "role_code"),
        Index("ix_membership_role", "role_code"),
    )


class MembershipRestaurantGrant(TenantRecord):
    """Enforce company and access-mode consistency through composite FKs."""

    __tablename__ = "membership_restaurant_grants"
    organization_id: Mapped[int] = mapped_column(Integer, nullable=False)
    membership_id: Mapped[int] = mapped_column(Integer, nullable=False)
    restaurant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    access_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="explicit-grants",
        server_default="explicit-grants",
    )
    __table_args__ = (
        UniqueConstraint(
            "membership_id", "restaurant_id", name="uq_membership_restaurant"
        ),
        CheckConstraint("access_mode = 'explicit-grants'", name="ck_grant_mode"),
        ForeignKeyConstraint(
            ["organization_id", "membership_id", "access_mode"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.id",
                "organization_memberships.access_mode",
            ],
            ondelete="RESTRICT",
            name="fk_grant_membership",
        ),
        ForeignKeyConstraint(
            ["organization_id", "restaurant_id"],
            ["restaurants.organization_id", "restaurants.id"],
            ondelete="RESTRICT",
            name="fk_grant_restaurant",
        ),
        Index("ix_grant_restaurant", "organization_id", "restaurant_id"),
        Index("ix_grant_membership", "organization_id", "membership_id", "access_mode"),
    )


# ==============================================
# ACCEPTANCE PROPOSALS AND APPEND-ONLY AUDIT
# ==============================================


class MembershipChangeProposal(TenantRecord):
    """Store immutable reviewed intent; storing a proposal grants no authority."""

    __tablename__ = "membership_change_proposals"
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    target_membership_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_identity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_membership_id: Mapped[int | None] = mapped_column(Integer)
    actor_identity_id: Mapped[int | None] = mapped_column(Integer)
    actor_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id", ondelete="RESTRICT")
    )
    proposed_role_code: Mapped[str] = mapped_column(
        ForeignKey("tenant_roles.code", ondelete="RESTRICT"), nullable=False
    )
    proposed_access_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_actor_revision: Mapped[int | None] = mapped_column(BigInteger)
    expected_target_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    enrollment_generation: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "id", "proposed_access_mode", name="uq_proposal_mode"
        ),
        CheckConstraint(
            "proposed_access_mode IN ('company-wide','explicit-grants')",
            name="ck_proposal_mode",
        ),
        CheckConstraint(
            "proposed_role_code != 'owner' OR proposed_access_mode = 'company-wide'",
            name="ck_proposal_owner_scope",
        ),
        CheckConstraint(
            "status IN ('pending','applied','cancelled','expired')",
            name="ck_proposal_status",
        ),
        CheckConstraint(
            "expected_target_revision > 0 AND enrollment_generation > 0",
            name="ck_proposal_revision",
        ),
        CheckConstraint(
            "(actor_kind = 'tenant' AND actor_membership_id IS NOT NULL AND actor_identity_id IS NOT NULL AND actor_admin_id IS NULL AND expected_actor_revision IS NOT NULL AND expected_actor_revision > 0) OR (actor_kind = 'platform' AND actor_membership_id IS NULL AND actor_identity_id IS NULL AND actor_admin_id IS NOT NULL AND expected_actor_revision IS NULL)",
            name="ck_proposal_actor",
        ),
        CheckConstraint(
            "(status = 'applied' AND applied_at IS NOT NULL) OR (status != 'applied' AND applied_at IS NULL)",
            name="ck_proposal_application",
        ),
        ForeignKeyConstraint(
            ["organization_id", "target_membership_id", "target_identity_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.id",
                "organization_memberships.identity_id",
            ],
            ondelete="RESTRICT",
            name="fk_proposal_target",
        ),
        ForeignKeyConstraint(
            ["organization_id", "actor_membership_id", "actor_identity_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.id",
                "organization_memberships.identity_id",
            ],
            ondelete="RESTRICT",
            name="fk_proposal_actor",
        ),
        Index(
            "ix_proposal_target",
            "organization_id",
            "target_membership_id",
            "target_identity_id",
        ),
        Index(
            "ix_proposal_actor",
            "organization_id",
            "actor_membership_id",
            "actor_identity_id",
        ),
    )


class MembershipProposalRestaurant(TenantRecord):
    """Normalize the exact proposed restaurant set without JSON authority."""

    __tablename__ = "membership_proposal_restaurants"
    organization_id: Mapped[int] = mapped_column(Integer, nullable=False)
    proposal_id: Mapped[int] = mapped_column(Integer, nullable=False)
    restaurant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_access_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="explicit-grants",
        server_default="explicit-grants",
    )
    __table_args__ = (
        UniqueConstraint("proposal_id", "restaurant_id", name="uq_proposal_restaurant"),
        CheckConstraint(
            "proposed_access_mode = 'explicit-grants'",
            name="ck_proposal_restaurant_mode",
        ),
        ForeignKeyConstraint(
            ["organization_id", "proposal_id", "proposed_access_mode"],
            [
                "membership_change_proposals.organization_id",
                "membership_change_proposals.id",
                "membership_change_proposals.proposed_access_mode",
            ],
            ondelete="RESTRICT",
            name="fk_proposal_restaurant_intent",
        ),
        ForeignKeyConstraint(
            ["organization_id", "restaurant_id"],
            ["restaurants.organization_id", "restaurants.id"],
            ondelete="RESTRICT",
            name="fk_proposal_restaurant_resource",
        ),
        Index("ix_proposal_restaurant", "organization_id", "restaurant_id"),
        Index(
            "ix_proposal_restaurant_parent",
            "organization_id",
            "proposal_id",
            "proposed_access_mode",
        ),
    )


class TenantAuditEvent(TenantRecord):
    """Retain local actor/target and policy revisions without token material."""

    __tablename__ = "tenant_audit_events"
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    actor_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_membership_id: Mapped[int | None] = mapped_column(Integer)
    actor_identity_id: Mapped[int | None] = mapped_column(Integer)
    actor_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id", ondelete="RESTRICT")
    )
    target_membership_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_identity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    resulting_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    enrollment_generation: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_before: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    policy_after: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    __table_args__ = (
        CheckConstraint("length(trim(action)) > 0", name="ck_audit_action"),
        CheckConstraint(
            "length(trim(reason_code)) > 0 AND length(trim(correlation_id)) > 0",
            name="ck_audit_reason",
        ),
        CheckConstraint(
            "previous_revision > 0 AND resulting_revision > previous_revision AND enrollment_generation > 0",
            name="ck_audit_revisions",
        ),
        CheckConstraint(
            "(actor_kind = 'tenant' AND actor_membership_id IS NOT NULL AND actor_identity_id IS NOT NULL AND actor_admin_id IS NULL) OR (actor_kind = 'platform' AND actor_membership_id IS NULL AND actor_identity_id IS NULL AND actor_admin_id IS NOT NULL)",
            name="ck_audit_actor",
        ),
        ForeignKeyConstraint(
            ["organization_id", "target_membership_id", "target_identity_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.id",
                "organization_memberships.identity_id",
            ],
            ondelete="RESTRICT",
            name="fk_audit_target",
        ),
        ForeignKeyConstraint(
            ["organization_id", "actor_membership_id", "actor_identity_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.id",
                "organization_memberships.identity_id",
            ],
            ondelete="RESTRICT",
            name="fk_audit_actor",
        ),
        Index(
            "ix_audit_target",
            "organization_id",
            "target_membership_id",
            "target_identity_id",
        ),
        Index(
            "ix_audit_actor",
            "organization_id",
            "actor_membership_id",
            "actor_identity_id",
        ),
    )


# ==============================================
# REJECT KEY CHANGES
# ==============================================


@event.listens_for(Identity, "before_update")
@event.listens_for(OrganizationMembership, "before_update")
@event.listens_for(Organization, "before_update")
@event.listens_for(MembershipChangeProposal, "before_update")
def _reject_key_changes(mapper: object, connection: object, target: object) -> None:
    """Protect ORM immutable keys; SQL-level guards belong to reviewed E1 DDL."""
    if isinstance(target, Identity):
        keys = ("issuer", "subject")
    elif isinstance(target, OrganizationMembership):
        keys = ("organization_id", "identity_id")
    elif isinstance(target, Organization):
        history = inspect(target).attrs.tenant_enforced_at.history
        if history.deleted and history.deleted[0] is not None and history.has_changes():
            raise ValueError("tenant_enforcement_is_immutable")
        return
    else:
        keys = tuple(
            column.key
            for column in MembershipChangeProposal.__table__.columns
            if column.key not in {"status", "applied_at", "updated_at"}
        )
    if any(inspect(target).attrs[key].history.has_changes() for key in keys):
        raise ValueError("tenant_identity_or_intent_is_immutable")


# ==============================================
# REJECT AUDIT MUTATION
# ==============================================


@event.listens_for(TenantAuditEvent, "before_update")
@event.listens_for(TenantAuditEvent, "before_delete")
def _reject_audit_mutation(mapper: object, connection: object, target: object) -> None:
    """Reject ordinary ORM audit edits; database privileges remain an E1 gate."""
    raise ValueError("tenant_audit_is_append_only")


# ==============================================
# REJECT HISTORY DELETION
# ==============================================


@event.listens_for(Identity, "before_delete")
@event.listens_for(Organization, "before_delete")
@event.listens_for(OrganizationMembership, "before_delete")
def _reject_history_deletion(
    mapper: object, connection: object, target: object
) -> None:
    """Use lifecycle states; never hard-delete authorization history via ORM."""
    raise ValueError("tenant_history_requires_retention")
