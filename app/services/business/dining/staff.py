# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# GOVERNED PROFESSIONAL RELATIONSHIPS
# Reuse E1 identities, membership states, restaurant grants and transaction locks.
# ==============================================

"""Owner management and personal invitation acceptance; no parallel authentication."""

from __future__ import annotations

# isort: split
# ==============================================
# EXISTING AUTHORITY AND SCOPED RESOURCES
# No provider, connection settings or startup action is imported by this module.
# ==============================================

from uuid import uuid4

from sqlalchemy import (
    delete,
    select,
    text,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_types import (
    TenantAccessDenied,
    TenantConflict,
    validate_identity_key,
)
from app.models.branch import Branch
from app.models.dining import DiningGrant
from app.models.dining_service import (
    DiningStaffAssignment,
    DiningStaffFunction,
    DiningStaffProfile,
)
from app.models.tenant.schema import (
    MembershipRestaurantGrant,
    Organization,
    OrganizationMembership,
    TenantAuditEvent,
    restaurant_reference,
)
from app.repositories.tenant_repo import (
    IdentityRepository,
    TenantRepository,
    _base_membership_select,
)
from app.schemas.dining import JsonObject
from app.schemas.dining_staff import (
    StaffAssignmentInput,
    StaffCommand,
    StaffFunctionInput,
    StaffInviteInput,
    StaffProfileInput,
    StaffStatusInput,
)
from app.services.business.dining.core import DiningCore
from app.services.business.dining.values import (
    DiningError,
    utc_now,
)
from app.services.business.tenant_foundation import (
    IdentityService,
    TenantAuthorizationService,
    TenantContextResolver,
    tenant_unit_of_work,
)
from migration_support.operational_revisions import DINING_SERVICE_REVISIONS

# ==============================================
# EXACT EXTENSION ADMISSION
# Older installations receive a controlled refusal before any new-table query.
# ==============================================


async def require_service_schema(*, session: AsyncSession) -> None:
    """Require a genuinely applied D1d revision; never stamp or repair it here."""
    if (
        await session.scalar(text("SELECT version_num FROM public.alembic_version"))
        not in DINING_SERVICE_REVISIONS
    ):
        raise DiningError(code="dining_service_schema_upgrade_required")


# ==============================================
# SINGLE GOVERNED OWNER TRANSACTION
# Resolve organization-write authority before targeting another member's state.
# ==============================================


class DiningStaffService:
    """Use the existing identity and policy resolver for every administrative write."""

    # ==============================================
    # INITIALIZE EXPLICIT DEPENDENCIES
    # Store a request-owned session without opening a database connection.
    # ==============================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Store a request-owned session without opening a database connection."""
        self.session = session

    # ==============================================
    # OWNER EXECUTION BOUNDARY
    # An employee cannot acquire this unit by adding a role or function in the body.
    # ==============================================

    async def execute(
        self,
        *,
        principal: OIDCPrincipal,
        organization_id: int,
        restaurant_id: int,
        branch_id: int,
        command: StaffCommand,
    ) -> JsonObject:
        """Commit exactly one authorized staff mutation, or roll it back completely."""
        async with tenant_unit_of_work(session=self.session):
            await require_service_schema(session=self.session)
            context = await TenantContextResolver(session=self.session)._resolve(
                principal=principal, organization_id=organization_id, governance=True
            )
            context.require(permission="tenant.memberships.manage")
            if context.role_code != "owner":
                raise TenantAccessDenied("dining_staff_owner_required")
            await TenantAuthorizationService(session=self.session).require_restaurant(
                context=context,
                restaurant_id=restaurant_id,
                permission="tenant.restaurants.read",
            )
            branch = await self.session.scalar(
                select(Branch.id).where(
                    Branch.id == branch_id,
                    Branch.restaurant_id == restaurant_id,
                    Branch.is_active.is_(True),
                )
            )
            if branch is None:
                raise TenantAccessDenied("dining_branch_unavailable")
            unit = DiningCore(
                session=self.session,
                context=context,
                principal=principal,
                restaurant_id=restaurant_id,
                branch_id=branch_id,
                clock=utc_now,
            )
            await unit.guard(capability="configure")
            await unit.policy(lock=True)
            result = await self._execute(unit=unit, command=command)
        logger.info(
            "Dining staff transaction committed",
            extra={
                "organization_id": organization_id,
                "restaurant_id": restaurant_id,
                "branch_id": branch_id,
                "operation": command.operation,
            },
        )
        return result

    # ==============================================
    # SAME-COMPANY NON-OWNER TARGET
    # Descriptive management never promotes a role or edits the last-owner graph.
    # ==============================================

    async def _member(
        self, *, unit: DiningCore, identifier: int
    ) -> OrganizationMembership:
        """Lock a company-qualified employee and reject owner or foreign resources."""
        member = await TenantRepository(session=self.session).lock_membership(
            organization_id=unit.context.organization_id,
            membership_id=identifier,
            exclusive=True,
        )
        if member is None or member.role_code == "owner":
            raise TenantAccessDenied("dining_staff_member_unavailable")
        return member

    # ==============================================
    # DISPATCH CLOSED PROFESSIONAL COMMANDS
    # Each descriptive mutation records evidence but cannot implicitly change grants.
    # ==============================================

    async def _execute(self, *, unit: DiningCore, command: StaffCommand) -> JsonObject:
        """Apply one typed command inside the already verified owner transaction."""
        identifier: int
        if isinstance(command, StaffInviteInput):
            identifier = await self._invite(unit=unit, data=command)
        elif isinstance(command, StaffFunctionInput):
            row = await self.session.scalar(
                unit.repo.statement(model=DiningStaffFunction)
                .where(DiningStaffFunction.code == command.code)
                .with_for_update()
            )
            if row is None:
                row = await unit.repo.persist(
                    record=DiningStaffFunction(
                        **unit.scope(),
                        code=command.code,
                        labels=command.labels,
                        tasks=list(command.tasks),
                        active=command.active,
                    )
                )
            else:
                row.labels, row.tasks, row.active = (
                    command.labels,
                    list(command.tasks),
                    command.active,
                )
            if not row.active:
                await self.session.execute(
                    update(DiningStaffAssignment)
                    .where(
                        DiningStaffAssignment.restaurant_id == unit.repo.restaurant_id,
                        DiningStaffAssignment.branch_id == unit.repo.branch_id,
                        DiningStaffAssignment.function_id == row.id,
                    )
                    .values(active=False)
                )
            identifier = row.id
        elif isinstance(command, StaffProfileInput):
            member = await self._member(unit=unit, identifier=command.membership_id)
            await self._eligible(unit=unit, member=member)
            profile = await self._profile(
                unit=unit,
                member=member,
                code=command.employee_code,
                name=command.display_name,
            )
            identifier = profile.id
        elif isinstance(command, StaffAssignmentInput):
            member = await self._member(unit=unit, identifier=command.membership_id)
            await self._eligible(unit=unit, member=member)
            function = await unit.repo.one(
                model=DiningStaffFunction, identifier=command.function_id, lock=True
            )
            if command.active and (not function.active or member.status != "active"):
                raise DiningError(code="dining_staff_active_assignment_required")
            row = await self.session.scalar(
                unit.repo.statement(model=DiningStaffAssignment)
                .where(
                    DiningStaffAssignment.membership_id == member.id,
                    DiningStaffAssignment.function_id == function.id,
                )
                .with_for_update()
            )
            if row is None:
                row = await unit.repo.persist(
                    record=DiningStaffAssignment(
                        **unit.scope(),
                        membership_id=member.id,
                        function_id=function.id,
                        active=command.active,
                        assigned_by=unit.context.membership_id,
                    )
                )
            else:
                row.active, row.assigned_by = command.active, unit.context.membership_id
            identifier = row.id
        elif isinstance(command, StaffStatusInput):
            identifier = await self._status(unit=unit, data=command)
        else:
            raise DiningError(code="dining_staff_operation_invalid")
        await self.session.flush()
        await unit.event(
            kind="staff." + command.operation,
            details={
                "identifier": identifier,
                "descriptive_functions_do_not_grant_permissions": True,
            },
        )
        return {"identifier": identifier, "operation": command.operation}

    # ==============================================
    # EXPLICIT RESTAURANT ELIGIBILITY
    # A member of another restaurant cannot be assigned through a guessed ID.
    # ==============================================

    async def _eligible(
        self, *, unit: DiningCore, member: OrganizationMembership
    ) -> None:
        """Require the actual company membership's authorized restaurant boundary."""
        grants = await TenantRepository(session=self.session).grants(
            organization_id=unit.context.organization_id, membership_id=member.id
        )
        if (
            member.access_mode == "explicit-grants"
            and unit.repo.restaurant_id not in grants
        ):
            raise TenantAccessDenied("dining_member_restaurant_unavailable")

    # ==============================================
    # RETAIN ONE BRANCH DISPLAY PROFILE
    # Acceptance belongs to an enrollment generation and is never fabricated on invite.
    # ==============================================

    async def _profile(
        self, *, unit: DiningCore, member: OrganizationMembership, code: str, name: str
    ) -> DiningStaffProfile:
        """Create or update professional labels without touching identity credentials."""
        row = await self.session.scalar(
            unit.repo.statement(model=DiningStaffProfile)
            .where(DiningStaffProfile.membership_id == member.id)
            .with_for_update()
        )
        if row is None:
            row = await unit.repo.persist(
                record=DiningStaffProfile(
                    **unit.scope(),
                    membership_id=member.id,
                    employee_code=code.strip(),
                    display_name=name.strip(),
                    enrollment_generation=member.enrollment_generation,
                    accepted_at=(
                        member.accepted_at if member.status == "active" else None
                    ),
                )
            )
        else:
            row.employee_code, row.display_name = code.strip(), name.strip()
            if row.enrollment_generation != member.enrollment_generation:
                row.enrollment_generation, row.accepted_at = (
                    member.enrollment_generation,
                    None,
                )
        return row

    # ==============================================
    # INVITE ONLY AN ALREADY REGISTERED EXACT OIDC IDENTITY
    # A guessed account can receive a pending proposal but cannot be activated without acceptance.
    # ==============================================

    async def _invite(self, *, unit: DiningCore, data: StaffInviteInput) -> int:
        """Keep new relations pending and require a new generation after revocation."""
        validate_identity_key(issuer=data.issuer, subject=data.subject)
        identity_repo = IdentityRepository(session=self.session)
        found = await identity_repo.find(issuer=data.issuer, subject=data.subject)
        identity = (
            await identity_repo.lock(identity_id=found.id)
            if found is not None
            else None
        )
        if identity is None or identity.status != "active":
            raise TenantAccessDenied("dining_staff_account_unavailable")
        member = await self.session.scalar(
            _base_membership_select()
            .where(
                OrganizationMembership.organization_id == unit.context.organization_id,
                OrganizationMembership.identity_id == identity.id,
            )
            .with_for_update()
        )
        if member is not None and member.role_code == "owner":
            raise TenantAccessDenied("dining_staff_member_unavailable")
        if member is None:
            member = OrganizationMembership(
                organization_id=unit.context.organization_id,
                identity_id=identity.id,
                role_code="employee",
                access_mode="explicit-grants",
                status="pending",
                revision=1,
                enrollment_generation=1,
            )
            self.session.add(member)
            await self.session.flush()
        elif member.status == "revoked":
            member.status, member.revision, member.enrollment_generation = (
                "pending",
                member.revision + 1,
                member.enrollment_generation + 1,
            )
            member.access_mode = "explicit-grants"
            member.accepted_at = member.activated_at = member.suspended_at = (
                member.revoked_at
            ) = None
            await self.session.flush()
        if member.access_mode == "explicit-grants":
            grant = await self.session.scalar(
                select(MembershipRestaurantGrant).where(
                    MembershipRestaurantGrant.organization_id
                    == unit.context.organization_id,
                    MembershipRestaurantGrant.membership_id == member.id,
                    MembershipRestaurantGrant.restaurant_id == unit.repo.restaurant_id,
                )
            )
            if grant is None:
                self.session.add(
                    MembershipRestaurantGrant(
                        organization_id=unit.context.organization_id,
                        membership_id=member.id,
                        restaurant_id=unit.repo.restaurant_id,
                        access_mode="explicit-grants",
                    )
                )
                await self.session.flush()
        await self._profile(
            unit=unit, member=member, code=data.employee_code, name=data.display_name
        )
        return member.id

    # ==============================================
    # OWNER LIFECYCLE WITH NO SILENT GRANT RESTORATION
    # Suspension/revocation removes all operational powers across this company relationship.
    # ==============================================

    async def _status(self, *, unit: DiningCore, data: StaffStatusInput) -> int:
        """Retain membership history, personal acceptance and transaction-wide audit."""
        member = await self._member(unit=unit, identifier=data.membership_id)
        if member.status == data.status:
            return member.id
        await self._eligible(unit=unit, member=member)
        if member.revision != data.expected_revision:
            raise TenantConflict("tenant_membership_revision_conflict")
        if member.status == "revoked":
            raise DiningError(code="dining_staff_new_invitation_required")
        previous = member.revision
        before = member.status
        if data.status == "active":
            identity = await IdentityRepository(session=self.session).lock(
                identity_id=member.identity_id
            )
            if identity is None or identity.status != "active":
                raise TenantAccessDenied("dining_staff_account_unavailable")
            profile = await self.session.scalar(
                unit.repo.statement(model=DiningStaffProfile)
                .where(DiningStaffProfile.membership_id == member.id)
                .with_for_update()
            )
            if (
                profile is None
                or profile.enrollment_generation != member.enrollment_generation
                or profile.accepted_at is None
            ):
                raise DiningError(code="dining_staff_personal_acceptance_required")
            member.accepted_at = profile.accepted_at
            member.activated_at = unit.now()
            member.suspended_at = member.revoked_at = None
        else:
            if data.status == "suspended" and member.status != "active":
                raise DiningError(code="dining_staff_active_membership_required")
            if data.status == "suspended":
                member.suspended_at = unit.now()
            else:
                member.revoked_at = unit.now()
            restaurants = select(restaurant_reference.c.id).where(
                restaurant_reference.c.organization_id == unit.context.organization_id
            )
            await self.session.execute(
                update(DiningGrant)
                .where(
                    DiningGrant.membership_id == member.id,
                    DiningGrant.restaurant_id.in_(restaurants),
                )
                .values(active=False)
            )
            await self.session.execute(
                update(DiningStaffAssignment)
                .where(
                    DiningStaffAssignment.membership_id == member.id,
                    DiningStaffAssignment.restaurant_id.in_(restaurants),
                )
                .values(active=False)
            )
            if data.status == "revoked":
                await self.session.execute(
                    delete(MembershipRestaurantGrant).where(
                        MembershipRestaurantGrant.organization_id
                        == unit.context.organization_id,
                        MembershipRestaurantGrant.membership_id == member.id,
                    )
                )
        member.status, member.revision = data.status, previous + 1
        await self.session.flush()
        self._audit(
            member=member,
            actor_member_id=unit.context.membership_id,
            actor_identity_id=unit.context.identity_id,
            previous=previous,
            action="staff." + data.status,
            before=before,
            reason=data.reason,
        )
        return member.id

    # ==============================================
    # RETAIN EXISTING E1 AUDIT EVIDENCE
    # Store only stable IDs, state transitions and revision numbers, never credentials.
    # ==============================================

    def _audit(
        self,
        *,
        member: OrganizationMembership,
        actor_member_id: int,
        actor_identity_id: int,
        previous: int,
        action: str,
        before: str,
        reason: str = "personal_acceptance",
    ) -> None:
        """Stage the immutable audit in the same transaction as its membership mutation."""
        self.session.add(
            TenantAuditEvent(
                organization_id=member.organization_id,
                actor_kind="tenant",
                actor_membership_id=actor_member_id,
                actor_identity_id=actor_identity_id,
                target_membership_id=member.id,
                target_identity_id=member.identity_id,
                action=action,
                previous_revision=previous,
                resulting_revision=member.revision,
                enrollment_generation=member.enrollment_generation,
                reason_code="explicit_staff_lifecycle",
                correlation_id=uuid4().hex,
                policy_before={"status": before},
                policy_after={"status": member.status, "reason": reason},
            )
        )

    # ==============================================
    # PERSONAL ACCEPTANCE WITHOUT ACTIVATION
    # Only the exact signed account may accept its pending professional relationship.
    # ==============================================

    async def accept(
        self, *, principal: OIDCPrincipal, organization_id: int, membership_id: int
    ) -> JsonObject:
        """Record consent as evidence; the owner must still activate and assign rights."""
        async with tenant_unit_of_work(session=self.session):
            await require_service_schema(session=self.session)
            identity_id = await IdentityService(session=self.session).resolve_id(
                principal=principal
            )
            repo = TenantRepository(session=self.session)
            org = await repo.lock_organization(
                organization_id=organization_id, governance=True
            )
            member = await repo.lock_membership(
                organization_id=organization_id,
                membership_id=membership_id,
                exclusive=True,
            )
            if (
                org is None
                or org.status != "active"
                or not await repo.has_active_owner(organization_id=organization_id)
                or member is None
                or member.identity_id != identity_id
                or member.role_code == "owner"
                or member.status != "pending"
            ):
                raise TenantAccessDenied("dining_staff_invitation_unavailable")
            profiles = tuple(
                (
                    await self.session.execute(
                        select(DiningStaffProfile)
                        .where(
                            DiningStaffProfile.membership_id == member.id,
                            DiningStaffProfile.enrollment_generation
                            == member.enrollment_generation,
                        )
                        .with_for_update()
                    )
                ).scalars()
            )
            if not profiles:
                raise TenantAccessDenied("dining_staff_invitation_unavailable")
            if any(row.accepted_at is None for row in profiles):
                for row in profiles:
                    if row.accepted_at is None:
                        row.accepted_at = utc_now()
                previous = member.revision
                member.revision += 1
                await self.session.flush()
                self._audit(
                    member=member,
                    actor_member_id=member.id,
                    actor_identity_id=identity_id,
                    previous=previous,
                    action="staff.invitation.accepted",
                    before=member.status,
                )
        logger.info(
            "Dining staff acceptance committed",
            extra={"organization_id": organization_id, "membership_id": membership_id},
        )
        return {"membership_id": membership_id, "status": "pending_owner_activation"}

    # ==============================================
    # PERSONAL INVITATION DISCOVERY
    # Pending accounts see their own relationship metadata without restaurant business access.
    # ==============================================

    async def invitations(self, *, principal: OIDCPrincipal) -> list[JsonObject]:
        """List at most 100 own professional invitations; this grants no selectable scope."""
        async with tenant_unit_of_work(session=self.session):
            await require_service_schema(session=self.session)
            identity_id = await IdentityService(session=self.session).resolve_id(
                principal=principal
            )
            records = (
                await self.session.execute(
                    _base_membership_select()
                    .add_columns(Organization.name, DiningStaffProfile)
                    .join(
                        Organization,
                        Organization.id == OrganizationMembership.organization_id,
                    )
                    .join(
                        DiningStaffProfile,
                        DiningStaffProfile.membership_id == OrganizationMembership.id,
                    )
                    .where(
                        OrganizationMembership.identity_id == identity_id,
                        OrganizationMembership.status == "pending",
                        Organization.status == "active",
                        DiningStaffProfile.enrollment_generation
                        == OrganizationMembership.enrollment_generation,
                    )
                    .order_by(OrganizationMembership.id, DiningStaffProfile.id)
                    .limit(100)
                )
            ).all()
            return [
                {
                    "organization_id": member.organization_id,
                    "membership_id": member.id,
                    "organization_name": name,
                    "restaurant_id": profile.restaurant_id,
                    "branch_id": profile.branch_id,
                    "employee_code": profile.employee_code,
                    "display_name": profile.display_name,
                    "accepted": profile.accepted_at is not None,
                    "status": member.status,
                }
                for member, name, profile in records
            ]
