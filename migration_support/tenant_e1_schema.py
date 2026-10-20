# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Frozen E1 table/policy contract shared by the two independent histories.

Do not import live models here or modify this contract after application.
The nine explicit tables never include the legacy FK reference contracts.
"""

import sqlalchemy as sa

TENANT_TABLE_NAMES: tuple[str, ...] = (
    "identities",
    "organizations",
    "tenant_roles",
    "organization_memberships",
    "tenant_role_permissions",
    "membership_restaurant_grants",
    "membership_change_proposals",
    "membership_proposal_restaurants",
    "tenant_audit_events",
)

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "owner": (
        "tenant.agents.manage",
        "tenant.agents.read",
        "tenant.billing.checkout",
        "tenant.billing.read",
        "tenant.branches.manage",
        "tenant.branches.read",
        "tenant.catalog.manage",
        "tenant.catalog.read",
        "tenant.conversations.read",
        "tenant.conversations.respond",
        "tenant.groups.manage",
        "tenant.groups.read",
        "tenant.membership.self.leave",
        "tenant.membership.self.read",
        "tenant.memberships.manage",
        "tenant.memberships.read",
        "tenant.orders.manage",
        "tenant.orders.read",
        "tenant.organization.read",
        "tenant.organization.suspend",
        "tenant.organization.update",
        "tenant.ownership.manage",
        "tenant.receipts.submit",
        "tenant.reports.read",
        "tenant.restaurants.read",
        "tenant.restaurants.update",
    ),
    "manager": (
        "tenant.agents.manage",
        "tenant.agents.read",
        "tenant.branches.manage",
        "tenant.branches.read",
        "tenant.catalog.manage",
        "tenant.catalog.read",
        "tenant.conversations.read",
        "tenant.conversations.respond",
        "tenant.groups.read",
        "tenant.membership.self.leave",
        "tenant.membership.self.read",
        "tenant.orders.manage",
        "tenant.orders.read",
        "tenant.organization.read",
        "tenant.reports.read",
        "tenant.restaurants.read",
        "tenant.restaurants.update",
    ),
    "employee": (
        "tenant.branches.read",
        "tenant.catalog.read",
        "tenant.membership.self.leave",
        "tenant.membership.self.read",
        "tenant.orders.read",
        "tenant.restaurants.read",
    ),
}


# ==============================================
# DEFINE TENANT TABLES
# ==============================================


def define_tenant_tables(*, metadata: sa.MetaData) -> None:
    """Attach exactly nine frozen new tables to prepared legacy metadata."""
    sa.Table(
        "identities",
        metadata,
        sa.Column("issuer", sa.String(length=1024, collation="C"), nullable=False),
        sa.Column("subject", sa.String(length=255, collation="C"), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="suspended"
        ),
        sa.Column("revision", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_identities"),
        sa.CheckConstraint(
            "octet_length(issuer) = length(issuer) AND octet_length(subject) = length(subject) AND issuer !~ '[[:cntrl:]]' AND subject !~ '[[:cntrl:]]'",
            name="ck_identity_ascii",
        ),
        sa.CheckConstraint(
            "length(issuer) BETWEEN 1 AND 1024 AND issuer = trim(issuer) AND issuer LIKE 'https://%'",
            name="ck_identity_issuer",
        ),
        sa.CheckConstraint("revision > 0", name="ck_identity_revision"),
        sa.CheckConstraint(
            "status IN ('active','suspended','retired')", name="ck_identity_status"
        ),
        sa.CheckConstraint(
            "length(subject) BETWEEN 1 AND 255 AND subject = trim(subject)",
            name="ck_identity_subject",
        ),
        sa.UniqueConstraint("issuer", "subject", name="uq_identities_issuer_subject"),
    )
    sa.Table(
        "organizations",
        metadata,
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="draft"
        ),
        sa.Column("revision", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("tenant_enforced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.CheckConstraint(
            "status != 'active' OR tenant_enforced_at IS NOT NULL",
            name="ck_org_enforcement",
        ),
        sa.CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 255 AND name = trim(name)",
            name="ck_org_name",
        ),
        sa.CheckConstraint("revision > 0", name="ck_org_revision"),
        sa.CheckConstraint(
            "status IN ('draft','active','suspended','archived')", name="ck_org_status"
        ),
    )
    sa.Table(
        "tenant_roles",
        metadata,
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column(
            "policy_revision", sa.BigInteger(), nullable=False, server_default="1"
        ),
        sa.PrimaryKeyConstraint("code", name="pk_tenant_roles"),
        sa.CheckConstraint(
            "code IN ('owner','manager','employee')", name="ck_tenant_role_code"
        ),
        sa.CheckConstraint("policy_revision > 0", name="ck_tenant_role_revision"),
    )
    sa.Table(
        "organization_memberships",
        metadata,
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("identity_id", sa.Integer(), nullable=False),
        sa.Column("role_code", sa.String(length=16), nullable=False),
        sa.Column(
            "access_mode",
            sa.String(length=20),
            nullable=False,
            server_default="explicit-grants",
        ),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="pending"
        ),
        sa.Column("revision", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("enrollment_generation", sa.BigInteger(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_memberships"),
        sa.CheckConstraint(
            "status != 'active' OR (accepted_at IS NOT NULL AND activated_at IS NOT NULL)",
            name="ck_membership_acceptance",
        ),
        sa.CheckConstraint(
            "access_mode IN ('company-wide','explicit-grants')",
            name="ck_membership_mode",
        ),
        sa.CheckConstraint(
            "role_code != 'owner' OR access_mode = 'company-wide'",
            name="ck_membership_owner_scope",
        ),
        sa.CheckConstraint(
            "status != 'pending' OR (accepted_at IS NULL AND activated_at IS NULL)",
            name="ck_membership_pending",
        ),
        sa.CheckConstraint(
            "revision > 0 AND enrollment_generation > 0", name="ck_membership_revision"
        ),
        sa.CheckConstraint(
            "status != 'revoked' OR revoked_at IS NOT NULL",
            name="ck_membership_revocation",
        ),
        sa.CheckConstraint(
            "status IN ('pending','active','suspended','revoked')",
            name="ck_membership_status",
        ),
        sa.CheckConstraint(
            "status != 'suspended' OR suspended_at IS NOT NULL",
            name="ck_membership_suspension",
        ),
        sa.ForeignKeyConstraint(
            ["identity_id"],
            ["identities.id"],
            name="fk_organization_memberships_identity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_memberships_organization_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["role_code"],
            ["tenant_roles.code"],
            name="fk_organization_memberships_role_code",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "organization_id", "id", "identity_id", name="uq_membership_actor"
        ),
        sa.UniqueConstraint(
            "organization_id", "identity_id", name="uq_membership_identity"
        ),
        sa.UniqueConstraint(
            "organization_id", "id", "access_mode", name="uq_membership_mode"
        ),
        sa.Index(
            "ix_membership_identity_state", "identity_id", "status", "organization_id"
        ),
        sa.Index("ix_membership_org_role", "organization_id", "status", "role_code"),
        sa.Index("ix_membership_role", "role_code"),
    )
    sa.Table(
        "tenant_role_permissions",
        metadata,
        sa.Column("role_code", sa.String(length=16), nullable=False),
        sa.Column("permission_code", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint(
            "role_code", "permission_code", name="pk_tenant_role_permissions"
        ),
        sa.CheckConstraint(
            "(role_code = 'employee' AND permission_code IN ('tenant.branches.read', 'tenant.catalog.read', 'tenant.membership.self.leave', 'tenant.membership.self.read', 'tenant.orders.fulfill', 'tenant.orders.read', 'tenant.restaurants.read')) OR (role_code = 'manager' AND permission_code IN ('tenant.agents.manage', 'tenant.agents.read', 'tenant.branches.manage', 'tenant.branches.read', 'tenant.catalog.manage', 'tenant.catalog.read', 'tenant.conversations.read', 'tenant.conversations.respond', 'tenant.groups.read', 'tenant.membership.self.leave', 'tenant.membership.self.read', 'tenant.orders.fulfill', 'tenant.orders.manage', 'tenant.orders.read', 'tenant.organization.read', 'tenant.reports.read', 'tenant.restaurants.read', 'tenant.restaurants.update')) OR (role_code = 'owner' AND permission_code IN ('tenant.agents.manage', 'tenant.agents.read', 'tenant.billing.checkout', 'tenant.billing.read', 'tenant.branches.manage', 'tenant.branches.read', 'tenant.catalog.manage', 'tenant.catalog.read', 'tenant.conversations.read', 'tenant.conversations.respond', 'tenant.groups.manage', 'tenant.groups.read', 'tenant.membership.self.leave', 'tenant.membership.self.read', 'tenant.memberships.manage', 'tenant.memberships.read', 'tenant.orders.fulfill', 'tenant.orders.manage', 'tenant.orders.read', 'tenant.organization.read', 'tenant.organization.suspend', 'tenant.organization.update', 'tenant.ownership.manage', 'tenant.receipts.submit', 'tenant.reports.read', 'tenant.restaurants.read', 'tenant.restaurants.update'))",
            name="ck_tenant_role_permission",
        ),
        sa.ForeignKeyConstraint(
            ["role_code"],
            ["tenant_roles.code"],
            name="fk_tenant_role_permissions_role_code",
            ondelete="RESTRICT",
        ),
    )
    sa.Table(
        "membership_restaurant_grants",
        metadata,
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column(
            "access_mode",
            sa.String(length=20),
            nullable=False,
            server_default="explicit-grants",
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_membership_restaurant_grants"),
        sa.CheckConstraint("access_mode = 'explicit-grants'", name="ck_grant_mode"),
        sa.ForeignKeyConstraint(
            ["organization_id", "membership_id", "access_mode"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.id",
                "organization_memberships.access_mode",
            ],
            name="fk_grant_membership",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "restaurant_id"],
            ["restaurants.organization_id", "restaurants.id"],
            name="fk_grant_restaurant",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "membership_id", "restaurant_id", name="uq_membership_restaurant"
        ),
        sa.Index(
            "ix_grant_membership", "organization_id", "membership_id", "access_mode"
        ),
        sa.Index("ix_grant_restaurant", "organization_id", "restaurant_id"),
    )
    sa.Table(
        "membership_change_proposals",
        metadata,
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("target_membership_id", sa.Integer(), nullable=False),
        sa.Column("target_identity_id", sa.Integer(), nullable=False),
        sa.Column("actor_kind", sa.String(length=16), nullable=False),
        sa.Column("actor_membership_id", sa.Integer(), nullable=True),
        sa.Column("actor_identity_id", sa.Integer(), nullable=True),
        sa.Column("actor_admin_id", sa.Integer(), nullable=True),
        sa.Column("proposed_role_code", sa.String(length=16), nullable=False),
        sa.Column("proposed_access_mode", sa.String(length=20), nullable=False),
        sa.Column("expected_actor_revision", sa.BigInteger(), nullable=True),
        sa.Column("expected_target_revision", sa.BigInteger(), nullable=False),
        sa.Column("enrollment_generation", sa.BigInteger(), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="pending"
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_membership_change_proposals"),
        sa.CheckConstraint(
            "(actor_kind = 'tenant' AND actor_membership_id IS NOT NULL AND actor_identity_id IS NOT NULL AND actor_admin_id IS NULL AND expected_actor_revision IS NOT NULL AND expected_actor_revision > 0) OR (actor_kind = 'platform' AND actor_membership_id IS NULL AND actor_identity_id IS NULL AND actor_admin_id IS NOT NULL AND expected_actor_revision IS NULL)",
            name="ck_proposal_actor",
        ),
        sa.CheckConstraint(
            "(status = 'applied' AND applied_at IS NOT NULL) OR (status != 'applied' AND applied_at IS NULL)",
            name="ck_proposal_application",
        ),
        sa.CheckConstraint(
            "proposed_access_mode IN ('company-wide','explicit-grants')",
            name="ck_proposal_mode",
        ),
        sa.CheckConstraint(
            "proposed_role_code != 'owner' OR proposed_access_mode = 'company-wide'",
            name="ck_proposal_owner_scope",
        ),
        sa.CheckConstraint(
            "expected_target_revision > 0 AND enrollment_generation > 0",
            name="ck_proposal_revision",
        ),
        sa.CheckConstraint(
            "status IN ('pending','applied','cancelled','expired')",
            name="ck_proposal_status",
        ),
        sa.ForeignKeyConstraint(
            ["actor_admin_id"],
            ["admins.id"],
            name="fk_membership_change_proposals_actor_admin_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_membership_id", "actor_identity_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.id",
                "organization_memberships.identity_id",
            ],
            name="fk_proposal_actor",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "target_membership_id", "target_identity_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.id",
                "organization_memberships.identity_id",
            ],
            name="fk_proposal_target",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_membership_change_proposals_organization_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["proposed_role_code"],
            ["tenant_roles.code"],
            name="fk_membership_change_proposals_proposed_role_code",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "organization_id", "id", "proposed_access_mode", name="uq_proposal_mode"
        ),
        sa.Index(
            "ix_proposal_actor",
            "organization_id",
            "actor_membership_id",
            "actor_identity_id",
        ),
        sa.Index(
            "ix_proposal_target",
            "organization_id",
            "target_membership_id",
            "target_identity_id",
        ),
    )
    sa.Table(
        "membership_proposal_restaurants",
        metadata,
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("proposal_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column(
            "proposed_access_mode",
            sa.String(length=20),
            nullable=False,
            server_default="explicit-grants",
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_membership_proposal_restaurants"),
        sa.CheckConstraint(
            "proposed_access_mode = 'explicit-grants'",
            name="ck_proposal_restaurant_mode",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "proposal_id", "proposed_access_mode"],
            [
                "membership_change_proposals.organization_id",
                "membership_change_proposals.id",
                "membership_change_proposals.proposed_access_mode",
            ],
            name="fk_proposal_restaurant_intent",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "restaurant_id"],
            ["restaurants.organization_id", "restaurants.id"],
            name="fk_proposal_restaurant_resource",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "proposal_id", "restaurant_id", name="uq_proposal_restaurant"
        ),
        sa.Index("ix_proposal_restaurant", "organization_id", "restaurant_id"),
        sa.Index(
            "ix_proposal_restaurant_parent",
            "organization_id",
            "proposal_id",
            "proposed_access_mode",
        ),
    )
    sa.Table(
        "tenant_audit_events",
        metadata,
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("actor_kind", sa.String(length=16), nullable=False),
        sa.Column("actor_membership_id", sa.Integer(), nullable=True),
        sa.Column("actor_identity_id", sa.Integer(), nullable=True),
        sa.Column("actor_admin_id", sa.Integer(), nullable=True),
        sa.Column("target_membership_id", sa.Integer(), nullable=False),
        sa.Column("target_identity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("previous_revision", sa.BigInteger(), nullable=False),
        sa.Column("resulting_revision", sa.BigInteger(), nullable=False),
        sa.Column("enrollment_generation", sa.BigInteger(), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("policy_before", sa.JSON(), nullable=False),
        sa.Column("policy_after", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tenant_audit_events"),
        sa.CheckConstraint("length(trim(action)) > 0", name="ck_audit_action"),
        sa.CheckConstraint(
            "(actor_kind = 'tenant' AND actor_membership_id IS NOT NULL AND actor_identity_id IS NOT NULL AND actor_admin_id IS NULL) OR (actor_kind = 'platform' AND actor_membership_id IS NULL AND actor_identity_id IS NULL AND actor_admin_id IS NOT NULL)",
            name="ck_audit_actor",
        ),
        sa.CheckConstraint(
            "length(trim(reason_code)) > 0 AND length(trim(correlation_id)) > 0",
            name="ck_audit_reason",
        ),
        sa.CheckConstraint(
            "previous_revision > 0 AND resulting_revision > previous_revision AND enrollment_generation > 0",
            name="ck_audit_revisions",
        ),
        sa.ForeignKeyConstraint(
            ["actor_admin_id"],
            ["admins.id"],
            name="fk_tenant_audit_events_actor_admin_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_membership_id", "actor_identity_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.id",
                "organization_memberships.identity_id",
            ],
            name="fk_audit_actor",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "target_membership_id", "target_identity_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.id",
                "organization_memberships.identity_id",
            ],
            name="fk_audit_target",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_tenant_audit_events_organization_id",
            ondelete="RESTRICT",
        ),
        sa.Index(
            "ix_audit_actor",
            "organization_id",
            "actor_membership_id",
            "actor_identity_id",
        ),
        sa.Index(
            "ix_audit_target",
            "organization_id",
            "target_membership_id",
            "target_identity_id",
        ),
    )
