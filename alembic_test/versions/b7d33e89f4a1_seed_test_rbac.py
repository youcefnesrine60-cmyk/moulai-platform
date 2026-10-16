# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - TEST RBAC SEED DATA
# Seed normalized roles and permissions for isolated tests.
# ==============================================

"""Seed the normalized RBAC records required by isolated integration tests.

Revision ID: b7d33e89f4a1
Revises: ae6a266365fb
Create Date: 2026-10-11 19:15:00
"""

from typing import Sequence

from alembic import op


revision: str = "b7d33e89f4a1"
down_revision: str | None = "ae6a266365fb"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


# ==============================================
# RBAC SEED MIGRATION
# ==============================================


def upgrade() -> None:
    """Insert the canonical roles, permissions, and role assignments."""
    op.execute(
        "INSERT INTO roles (code, name, description, is_active) VALUES "
        "('super_admin', 'Super administrator', 'Full platform authority', true), "
        "('admin', 'Administrator', 'Restaurant and operations management', true), "
        "('support', 'Support', 'Read and complaint support', true) "
        "ON CONFLICT (code) DO UPDATE SET "
        "name = EXCLUDED.name, "
        "description = EXCLUDED.description, "
        "is_active = EXCLUDED.is_active"
    )
    op.execute(
        "INSERT INTO permissions (code, name, description) "
        "SELECT code, code, code FROM unnest(ARRAY["
        "'*', 'restaurants.read', 'restaurants.manage', 'branches.manage', "
        "'catalog.manage', 'orders.read', 'orders.manage', "
        "'subscriptions.read', 'subscriptions.manage', 'reports.read', "
        "'complaints.manage', 'admins.manage', 'rbac.manage'"
        "]::text[]) AS code ON CONFLICT (code) DO NOTHING"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT role.id, permission.id FROM roles AS role "
        "CROSS JOIN permissions AS permission "
        "WHERE role.code = 'super_admin' ON CONFLICT DO NOTHING"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT role.id, permission.id FROM roles AS role "
        "JOIN permissions AS permission ON permission.code IN ("
        "'restaurants.read', 'restaurants.manage', 'branches.manage', "
        "'catalog.manage', 'orders.read', 'orders.manage', "
        "'subscriptions.read', 'subscriptions.manage', 'reports.read', "
        "'complaints.manage') WHERE role.code = 'admin' "
        "ON CONFLICT DO NOTHING"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT role.id, permission.id FROM roles AS role "
        "JOIN permissions AS permission ON permission.code IN ("
        "'restaurants.read', 'orders.read', 'subscriptions.read', "
        "'reports.read', 'complaints.manage') WHERE role.code = 'support' "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    """Remove only the canonical RBAC seed records from the test schema."""
    op.execute(
        "DELETE FROM role_permissions WHERE role_id IN "
        "(SELECT id FROM roles WHERE code IN ('super_admin', 'admin', 'support'))"
    )
    op.execute(
        "DELETE FROM permissions WHERE code IN ("
        "'*', 'restaurants.read', 'restaurants.manage', 'branches.manage', "
        "'catalog.manage', 'orders.read', 'orders.manage', "
        "'subscriptions.read', 'subscriptions.manage', 'reports.read', "
        "'complaints.manage', 'admins.manage', 'rbac.manage')"
    )
    op.execute(
        "DELETE FROM roles WHERE code IN ('super_admin', 'admin', 'support')"
    )
