# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# INTEGRATION TEST - RBAC AND BRANCH FEATURE GUARD
# Verify persisted authorization and subscription fixtures on PostgreSQL.
# ==============================================

"""Database integration coverage for normalized RBAC and branch feature access."""

from datetime import datetime
from datetime import timedelta

import pytest
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.core.exceptions import UnauthorizedError
from app.models.admin import Admin
from app.models.branch import Branch
from app.models.feature_pricing import FeatureUsageCounter
from app.models.feature_pricing import FeatureUsageLimit
from app.models.owner import Owner
from app.models.rbac import Permission
from app.models.rbac import Role
from app.models.restaurant import Restaurant
from app.models.subscription import Feature
from app.models.subscription import PlanFeature
from app.models.subscription import Subscription
from app.models.subscription import SubscriptionFeature
from app.models.subscription import SubscriptionPlan
from app.schemas.branch import BranchCreate
from app.services.business.admin.admin_service import AdminService
from app.services.business.branch_service import BRANCH_FEATURE_ID
from app.services.business.branch_service import BranchService


async def create_restaurant(*, session: AsyncSession, suffix: str) -> Restaurant:
    """Persist one owner and restaurant for an isolated feature-guard scenario."""
    owner = Owner(
        chat_id=900_000 + len(suffix),
        full_name=f"Integration owner {suffix}",
        phone="0555000000",
        email=f"integration-{suffix}@example.test",
        registration_status="approved",
    )
    session.add(owner)
    await session.flush()
    restaurant = Restaurant(
        owner_id=owner.id,
        name=f"Integration restaurant {suffix}",
        type="restaurant",
        phone="0555111111",
        wilaya="Alger",
        lat=36.75,
        lng=3.05,
        is_active=True,
    )
    session.add(restaurant)
    await session.flush()
    return restaurant


async def create_branch_feature_context(
    *,
    session: AsyncSession,
    suffix: str,
    include_subscription: bool = True,
    include_feature: bool = True,
    monthly_limit: int = 2,
    usage_count: int = 0,
) -> Restaurant:
    """Persist an explicit plan, subscription, feature, limit, and usage counter."""
    restaurant = await create_restaurant(session=session, suffix=suffix)
    feature = Feature(id=BRANCH_FEATURE_ID, code="branches", name="Branches")
    plan = SubscriptionPlan(
        code=f"integration-{suffix}",
        name=f"Integration {suffix}",
        base_price=0,
        plan_discount_percent=0,
        active=True,
    )
    session.add_all([feature, plan])
    await session.flush()
    session.add(PlanFeature(plan_id=plan.id, feature_id=feature.id, included=True))

    if include_subscription:
        subscription = Subscription(
            owner_id=restaurant.owner_id,
            restaurant_id=restaurant.id,
            plan_id=plan.id,
            billing_cycle="monthly",
            amount=0,
            starts_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=30),
            status="active",
        )
        session.add(subscription)
        await session.flush()
        if include_feature:
            session.add(
                SubscriptionFeature(
                    subscription_id=subscription.id,
                    feature_id=feature.id,
                ),
            )

    session.add(
        FeatureUsageLimit(
            plan_id=plan.id,
            feature_id=feature.id,
            monthly_limit=monthly_limit,
            limit_type="hard",
        ),
    )
    now = datetime.now()
    session.add(
        FeatureUsageCounter(
            restaurant_id=restaurant.id,
            feature_id=feature.id,
            usage_count=usage_count,
            period_year=now.year,
            period_month=now.month,
        ),
    )
    await session.commit()
    return restaurant


@pytest.mark.asyncio
async def test_rbac_permission_is_resolved_from_persisted_role(
    db_session: AsyncSession,
) -> None:
    """An AdminService permission check uses persisted normalized RBAC records."""
    permission = Permission(code="orders.manage", name="Manage orders")
    role = Role(code="integration_admin", name="Integration administrator")
    role.permissions.append(permission)
    db_session.add(role)
    await db_session.flush()
    admin = Admin(
        chat_id=990_001,
        username="integration-admin",
        full_name="Integration Admin",
        role="admin",
        role_id=role.id,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    service = AdminService(db_session)
    assert await service.check_admin_permission(
        admin_id=admin.id,
        required_permission="orders.manage",
    )
    with pytest.raises(UnauthorizedError):
        await service.check_admin_permission(
            admin_id=admin.id,
            required_permission="branches.manage",
        )


@pytest.mark.asyncio
async def test_branch_creation_persists_branch_and_increments_usage(
    db_session: AsyncSession,
) -> None:
    """A valid persisted subscription setup creates one branch and increments usage."""
    restaurant = await create_branch_feature_context(
        session=db_session,
        suffix="allow",
    )

    response = await BranchService(
        session=db_session, owner_id=restaurant.owner_id
    ).create_branch(
        restaurant_id=restaurant.id,
        branch_data=BranchCreate(name="Integration branch"),
    )
    usage_count = await db_session.scalar(
        select(FeatureUsageCounter.usage_count).where(
            FeatureUsageCounter.restaurant_id == restaurant.id,
            FeatureUsageCounter.feature_id == BRANCH_FEATURE_ID,
        ),
    )
    branch_count = await db_session.scalar(
        select(func.count()).select_from(Branch).where(Branch.id == response.id),
    )

    assert usage_count == 1
    assert branch_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "include_subscription",
        "include_feature",
        "monthly_limit",
        "usage_count",
        "error_code",
    ),
    [
        (False, True, 2, 0, "no_active_subscription"),
        (True, False, 2, 0, "feature_not_available"),
        (True, True, 1, 1, "feature_limit_reached"),
    ],
)
async def test_branch_feature_guard_rejects_persisted_invalid_states(
    db_session: AsyncSession,
    include_subscription: bool,
    include_feature: bool,
    monthly_limit: int,
    usage_count: int,
    error_code: str,
) -> None:
    """Each documented denial is enforced from persisted database state."""
    restaurant = await create_branch_feature_context(
        session=db_session,
        suffix=error_code,
        include_subscription=include_subscription,
        include_feature=include_feature,
        monthly_limit=monthly_limit,
        usage_count=usage_count,
    )

    with pytest.raises(ForbiddenError) as captured:
        await BranchService(
            session=db_session, owner_id=restaurant.owner_id
        ).create_branch(
            restaurant_id=restaurant.id,
            branch_data=BranchCreate(name=f"Denied {error_code}"),
        )

    assert captured.value.error_code == error_code
