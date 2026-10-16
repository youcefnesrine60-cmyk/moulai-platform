# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""add normalized RBAC roles and permissions

Revision ID: a91e7c2b4d10
Revises: 6bf21d4a8c30
Create Date: 2026-10-11 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a91e7c2b4d10"
down_revision: Union[str, Sequence[str], None] = "6bf21d4a8c30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create or complete the RBAC schema for tracked and metadata-created databases."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "roles" not in tables:
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
        )
        op.create_index("ix_roles_code", "roles", ["code"], unique=True)

    if "permissions" not in tables:
        op.create_table(
            "permissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("code", sa.String(length=128), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
        )
        op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)

    if "role_permissions" not in tables:
        op.create_table(
            "role_permissions",
            sa.Column(
                "role_id",
                sa.Integer(),
                sa.ForeignKey("roles.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "permission_id",
                sa.Integer(),
                sa.ForeignKey("permissions.id", ondelete="CASCADE"),
                primary_key=True,
            ),
        )

    admin_columns = {column["name"] for column in inspector.get_columns("admins")}
    if "role_id" not in admin_columns:
        op.add_column("admins", sa.Column("role_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_admins_role_id_roles",
            "admins",
            "roles",
            ["role_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_admins_role_id", "admins", ["role_id"])

    op.execute(
        "INSERT INTO roles (code, name, description, is_active) VALUES ('super_admin', 'Super administrator', 'Full platform authority', true), ('admin', 'Administrator', 'Restaurant and operations management', true), ('support', 'Support', 'Read and complaint support', true) ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, is_active = EXCLUDED.is_active"
    )
    op.execute(
        "INSERT INTO permissions (code, name, description) SELECT code, code, code FROM unnest(ARRAY['*','restaurants.read','restaurants.manage','branches.manage','catalog.manage','orders.read','orders.manage','subscriptions.read','subscriptions.manage','reports.read','complaints.manage','admins.manage','rbac.manage']::text[]) AS code ON CONFLICT (code) DO NOTHING"
    )
    op.execute(
        "UPDATE admins SET role_id = roles.id FROM roles WHERE admins.role = roles.code AND admins.role_id IS NULL"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) SELECT r.id, p.id FROM roles r CROSS JOIN permissions p WHERE r.code = 'super_admin' ON CONFLICT DO NOTHING"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code IN ('restaurants.read','restaurants.manage','branches.manage','catalog.manage','orders.read','orders.manage','subscriptions.read','subscriptions.manage','reports.read','complaints.manage') WHERE r.code = 'admin' ON CONFLICT DO NOTHING"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code IN ('restaurants.read','orders.read','subscriptions.read','reports.read','complaints.manage') WHERE r.code = 'support' ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_index("ix_admins_role_id", table_name="admins")
    op.drop_constraint("fk_admins_role_id_roles", "admins", type_="foreignkey")
    op.drop_column("admins", "role_id")
    op.drop_table("role_permissions")
    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_code", table_name="roles")
    op.drop_table("roles")
