# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OPT-IN DINING HTTP BOUNDARY
# Bind injected local sessions to verified OIDC identities without mounting in main.
# ==============================================

"""Explicit integration router; imports neither create a server nor send a message."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND CLOSED FINANCIAL CONTRACTS
# Current database grants remain authoritative; request bodies cannot set actors.
# ==============================================

from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
)
from datetime import (
    date,
    datetime,
    time,
)
from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
)
from fastapi.responses import HTMLResponse
from pydantic import Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dining_public import dining_public_router
from app.api.dining_staff import dining_staff_router
from app.api.tenant_dependencies import get_business_oidc_principal
from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_types import (
    TenantAccessDenied,
    TenantConflict,
)
from app.models.dining import (
    DiningReference,
    DiningTable,
)
from app.schemas.dining import (
    DiningInput,
    InvoiceInput,
    JsonObject,
    ReceiptInput,
)
from app.schemas.dining_operations import DiningOperation
from app.schemas.dining_public import (
    PresenceInstallationInput,
    PublicLinkInput,
    VisitOrderTransition,
)
from app.services.business.dining.calendar import local_instant
from app.services.business.dining.customer import (
    accept_customer_quote,
    customer_confirmation,
    customer_signal,
    customer_workspace,
)
from app.services.business.dining.event_history import read_event_history
from app.services.business.dining.operations import execute_operation
from app.services.business.dining.public_print import print_public_document
from app.services.business.dining.service import (
    DiningService,
    DiningUnit,
)
from app.services.business.dining.tickets import (
    TicketStatus,
    printable_confirmation,
    verification_viewer,
    verify_ticket,
)
from app.services.business.dining.values import (
    DiningError,
    Period,
    utc_now,
)
from app.services.business.document_qr import (
    public_read_url,
    svg_for_public_url,
)

# ==============================================
# FINALIZEINVOICEINPUT
# Require the draft revision actually reviewed by the service responsible.
# ==============================================


class FinalizeInvoiceInput(DiningInput):
    """Require the draft revision actually reviewed by the service responsible."""

    expected_revision: int = Field(strict=True, gt=0)


# ==============================================
# ACCEPTQUOTEINPUT
# Bind customer consent to the immutable exact proposal digest.
# ==============================================


class AcceptQuoteInput(DiningInput):
    """Bind customer consent to the immutable exact proposal digest."""

    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


# ==============================================
# CUSTOMERSIGNALINPUT
# A customer may request cancellation, never authorize its execution.
# ==============================================


class CustomerSignalInput(DiningInput):
    """A customer may request cancellation, never authorize its execution."""

    reason: str = Field(min_length=1, max_length=1000)


# ==============================================
# VERIFYTICKETINPUT
# Keep the opaque read token outside request URL logs.
# ==============================================


class VerifyTicketInput(DiningInput):
    """Keep the opaque read token outside request URL logs."""

    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


# ==============================================
# DINING ROUTER
# Build opt-in routes with explicit sessions; never fall back to DATABASE_URL.
# ==============================================


def dining_router(
    *,
    session_dependency: Callable[[], AsyncIterator[AsyncSession]],
    verification_origin: str | None = None,
    principal_dependency: Callable[
        ..., Awaitable[OIDCPrincipal]
    ] = get_business_oidc_principal,
    customer_dependency: Callable[..., Awaitable[OIDCPrincipal | None]] | None = None,
    clock: Callable[[], datetime] = utc_now,
) -> APIRouter:
    """Build opt-in routes with explicit sessions; never fall back to DATABASE_URL.

    The host must separately enable D1 schema, OIDC and rate limiting before
    mounting. No router is installed in app.main by this module.
    """
    router = APIRouter(tags=["dining"])
    router.include_router(
        dining_public_router(session_dependency=session_dependency, clock=clock)
    )
    router.include_router(
        dining_staff_router(
            session_dependency=session_dependency,
            principal_dependency=principal_dependency,
        )
    )
    session_dep = Depends(session_dependency)
    principal_dep = Depends(principal_dependency)
    prefix = "/organizations/{organization_id}/restaurants/{restaurant_id}/branches/{branch_id}/dining"

    # ==============================================
    # UNIT DEPENDENCY
    # Translate bounded domain errors, never SQL details or foreign resource IDs.
    # ==============================================

    async def unit_dependency(
        *,
        organization_id: int,
        restaurant_id: int,
        branch_id: int,
        session: AsyncSession = session_dep,
        principal: OIDCPrincipal = principal_dep,
    ) -> AsyncIterator[DiningUnit]:
        """Translate bounded domain errors, never SQL details or foreign resource IDs."""
        if min(organization_id, restaurant_id, branch_id) <= 0:
            raise HTTPException(status_code=404, detail="Resource unavailable")
        try:
            async with DiningService(session=session, clock=clock).authorized(
                principal=principal,
                organization_id=organization_id,
                restaurant_id=restaurant_id,
                branch_id=branch_id,
            ) as unit:
                yield unit
        except TenantAccessDenied as error:
            raise HTTPException(
                status_code=403, detail="Dining access denied"
            ) from error
        except DiningError as error:
            raise HTTPException(
                status_code=409,
                detail={"code": error.code, "conflicts": list(error.conflicts)},
            ) from error
        except TenantConflict as error:
            raise HTTPException(
                status_code=409, detail="Dining operation refused"
            ) from error
        except IntegrityError as error:
            raise HTTPException(
                status_code=409, detail="Dining integrity conflict"
            ) from error

    unit_dep = Depends(unit_dependency, scope="function")

    # ==============================================
    # EXPLICIT STAFF PUBLIC-LINK AND VISIT OPERATIONS
    # Existing unit authorization applies to every direct request and current capability.
    # ==============================================

    @router.post(prefix + "/public-links")
    async def public_link(
        *, data: PublicLinkInput, unit: DiningUnit = unit_dep
    ) -> JsonObject:
        """Issue, rotate or disable an owned read link without exposing its private snapshot."""
        return await unit.manage_public_link(data=data)

    # ==============================================
    # HUMAN INSTALLATION OF A SIGNALLED PARTY
    # Customer presence never substitutes for observation and existing D1 availability rules.
    # ==============================================

    @router.post(prefix + "/presence/install")
    async def install_presence(
        *, data: PresenceInstallationInput, unit: DiningUnit = unit_dep
    ) -> JsonObject:
        """Create the visit and actual occupation in one service-owned commit."""
        return {"identifier": await unit.install_presence(data=data)}

    # ==============================================
    # DISTINCT KITCHEN AND SERVICE ACTIONS
    # Role descriptions cannot invoke preparation or service without explicit current grants.
    # ==============================================

    @router.post(prefix + "/visit-orders/transition")
    async def visit_order_transition(
        *, data: VisitOrderTransition, unit: DiningUnit = unit_dep
    ) -> JsonObject:
        """Apply one observed transition to an owned active visit's food order."""
        await unit.transition_visit_order(data=data)
        return {"status": "recorded"}

    # ==============================================
    # REPRINT THE SAME ISSUED VERSION
    # Consultation never emits a new document or silently replaces an old reference.
    # ==============================================

    @router.get(prefix + "/public-links/{link_id}/print", response_class=HTMLResponse)
    async def print_link(
        *, link_id: int, locale: str = "fr", unit: DiningUnit = unit_dep
    ) -> HTMLResponse:
        """Render one authorized retained snapshot with a real read-only QR and manual URL."""
        if verification_origin is None:
            raise HTTPException(
                status_code=409, detail="Document origin not configured"
            )
        link = await unit.issued_print(link_id=link_id)
        document = dict(link.snapshot)
        if link.kind == "table":
            table = await unit.repo.one(model=DiningTable, identifier=link.table_id)
            zone = await unit.repo.one(model=DiningReference, identifier=table.zone_id)
            location = await unit.repo.one(
                model=DiningReference, identifier=table.location_id
            )
            document.update(
                {
                    "table": table.code,
                    "floor": table.floor_label,
                    "room": table.room_label,
                    "zone": zone.labels.get(locale),
                    "location": location.labels.get(locale),
                }
            )
        return HTMLResponse(
            print_public_document(
                link=link, document=document, origin=verification_origin, locale=locale
            ),
            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
        )

    # ==============================================
    # DOWNLOAD A TABLE OR DOCUMENT QR
    # Downloading is the same read permission as printing and grants no new authority.
    # ==============================================

    @router.get(prefix + "/public-links/{link_id}/qr")
    async def download_link(
        *, link_id: int, locale: str = "fr", unit: DiningUnit = unit_dep
    ) -> Response:
        """Return local SVG encoding of the approved origin and opaque read reference."""
        if verification_origin is None:
            raise HTTPException(
                status_code=409, detail="Document origin not configured"
            )
        link = await unit.issued_print(link_id=link_id)
        url = public_read_url(
            origin=verification_origin,
            page="menu" if link.kind == "table" else "verify-document",
            public_id=link.public_id,
            locale=locale,
        )
        return Response(
            svg_for_public_url(value=url),
            media_type="image/svg+xml",
            headers={
                "Content-Disposition": f'attachment; filename="{link.reference}.svg"',
                "Cache-Control": "no-store",
            },
        )

    # ==============================================
    # NO CUSTOMER PROOF
    # A host without a trusted customer verifier cannot create on-behalf demands.
    # ==============================================

    async def no_customer_proof() -> OIDCPrincipal | None:
        """A host without a trusted customer verifier cannot create on-behalf demands."""
        return None

    customer_dep = Depends(customer_dependency or no_customer_proof)

    # ==============================================
    # RESOLVE INSTANT
    # Resolve branch wall time on the server, without using the workstation timezone.
    # ==============================================

    @router.get(prefix + "/instant")
    async def resolve_instant(
        *,
        day: date,
        wall_time: time,
        fold: int | None = None,
        unit: DiningUnit = unit_dep,
    ) -> dict[str, str]:
        """Resolve branch wall time on the server, without using the workstation timezone."""
        await unit.guard(capability="read")
        policy = await unit.policy(lock=False)
        if wall_time.tzinfo is not None or fold not in {None, 0, 1}:
            raise DiningError(code="dining_wall_clock_input_invalid")
        instant = local_instant(
            day=day, clock=wall_time, zone=ZoneInfo(policy.timezone), fold=fold
        )
        return {"instant": instant.isoformat(), "timezone": policy.timezone}

    # ==============================================
    # MATCHES
    # Expose descriptive candidates only, without assignment or availability consent.
    # ==============================================

    @router.get(prefix + "/requests/{request_id}/matches")
    async def matches(*, request_id: int, unit: DiningUnit = unit_dep) -> JsonObject:
        """Expose descriptive candidates only, without assignment or availability consent."""
        return {
            "table_ids": list(await unit.matching_tables(request_id=request_id)),
            "availability_confirmed": False,
        }

    # ==============================================
    # WORKSPACE
    # Read persisted role-filtered form data and never silently substitute fixtures.
    # ==============================================

    @router.get(prefix + "/workspace")
    async def workspace(*, unit: DiningUnit = unit_dep) -> JsonObject:
        """Read persisted role-filtered form data and never silently substitute fixtures."""
        return await unit.workspace()

    # ==============================================
    # READ-ONLY EVENT PAGES
    # Reuse journal authority and branch-local civil days without changing historical records.
    # ==============================================

    @router.get(prefix + "/events")
    async def event_history(
        *,
        response: Response,
        unit: DiningUnit = unit_dep,
        from_day: date | None = None,
        until_day: date | None = None,
        kind: str | None = None,
        author: str | None = None,
        page: int = 1,
        page_size: int = 20,
        snapshot_id: int | None = None,
    ) -> JsonObject:
        """Return a bounded, scoped page; malformed filters never relax authorization."""
        response.headers["Cache-Control"] = "no-store"
        return await read_event_history(
            unit=unit,
            from_day=from_day,
            until_day=until_day,
            kind=kind,
            author=author,
            page=page,
            page_size=page_size,
            snapshot_id=snapshot_id,
        )

    # ==============================================
    # COMMAND
    # Dispatch a single closed operation; business methods still check every grant.
    # ==============================================

    @router.post(prefix + "/commands")
    async def command(
        *,
        data: DiningOperation,
        unit: DiningUnit = unit_dep,
        customer: OIDCPrincipal | None = customer_dep,
    ) -> JsonObject:
        """Dispatch a single closed operation; business methods still check every grant."""
        return await execute_operation(unit=unit, data=data, customer=customer)

    # ==============================================
    # OWN WORKSPACE
    # Keep customer reads outside staff permissions and bound to the actual token.
    # ==============================================

    @router.get(
        "/dining/restaurants/{restaurant_id}/branches/{branch_id}/customer-workspace"
    )
    async def own_workspace(
        *,
        restaurant_id: int,
        branch_id: int,
        session: AsyncSession = session_dep,
        principal: OIDCPrincipal = principal_dep,
    ) -> JsonObject:
        """Keep customer reads outside staff permissions and bound to the actual token."""
        try:
            return await customer_workspace(
                session=session,
                principal=principal,
                restaurant_id=restaurant_id,
                branch_id=branch_id,
            )
        except DiningError as error:
            raise HTTPException(status_code=409, detail={"code": error.code}) from error

    # ==============================================
    # OWN CANCELLATION REQUEST
    # Forward only the verified owning customer's request to dedicated human grants.
    # ==============================================

    @router.post(
        "/dining/restaurants/{restaurant_id}/branches/{branch_id}/requests/{request_id}/cancellation-request"
    )
    async def own_cancellation_request(
        *,
        restaurant_id: int,
        branch_id: int,
        request_id: int,
        data: CustomerSignalInput,
        session: AsyncSession = session_dep,
        principal: OIDCPrincipal = principal_dep,
    ) -> JsonObject:
        """Forward only the verified owning customer's request to dedicated human grants."""
        try:
            return await customer_signal(
                session=session,
                principal=principal,
                restaurant_id=restaurant_id,
                branch_id=branch_id,
                request_id=request_id,
                reason=data.reason,
                clock=clock,
            )
        except DiningError as error:
            raise HTTPException(status_code=409, detail={"code": error.code}) from error

    # ==============================================
    # OWN CONFIRMATION
    # Print only the verified customer's own confirmation, in the selected language.
    # ==============================================

    @router.get(
        "/dining/restaurants/{restaurant_id}/branches/{branch_id}/requests/{request_id}/confirmation",
        response_class=HTMLResponse,
    )
    async def own_confirmation(
        *,
        restaurant_id: int,
        branch_id: int,
        request_id: int,
        locale: str = "fr",
        session: AsyncSession = session_dep,
        principal: OIDCPrincipal = principal_dep,
    ) -> HTMLResponse:
        """Print only the verified customer's own confirmation, in the selected language."""
        if verification_origin is None:
            raise HTTPException(
                status_code=409, detail="Verification origin unavailable"
            )
        try:
            document = await customer_confirmation(
                session=session,
                principal=principal,
                restaurant_id=restaurant_id,
                branch_id=branch_id,
                request_id=request_id,
            )
            return HTMLResponse(
                printable_confirmation(
                    document=document,
                    verification_origin=verification_origin,
                    locale=locale,
                ),
                headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
            )
        except DiningError as error:
            raise HTTPException(status_code=409, detail={"code": error.code}) from error

    # ==============================================
    # PLANNING
    # Read one bounded calendar period without receipt or customer contact data.
    # ==============================================

    @router.get(prefix + "/planning")
    async def planning(
        *, starts_at: datetime, ends_at: datetime, unit: DiningUnit = unit_dep
    ) -> object:
        """Read one bounded calendar period without receipt or customer contact data."""
        return await unit.planning(period=Period(start=starts_at, end=ends_at))

    # ==============================================
    # PREPARE INVOICE
    # Prepare a draft from explicitly reconciled exact food sources.
    # ==============================================

    @router.post(prefix + "/invoices")
    async def prepare_invoice(
        *, data: InvoiceInput, unit: DiningUnit = unit_dep
    ) -> dict[str, int]:
        """Prepare a draft from explicitly reconciled exact food sources."""
        return {"invoice_id": await unit.prepare_invoice(data=data)}

    # ==============================================
    # FINALIZE INVOICE
    # Atomically freeze sales and apply the already-verified advance once.
    # ==============================================

    @router.post(prefix + "/invoices/{invoice_id}/finalize")
    async def finalize_invoice(
        *, invoice_id: int, data: FinalizeInvoiceInput, unit: DiningUnit = unit_dep
    ) -> dict[str, str]:
        """Atomically freeze sales and apply the already-verified advance once."""
        amount = await unit.finalize_invoice(
            invoice_id=invoice_id, expected_revision=data.expected_revision
        )
        return {"total": str(amount)}

    # ==============================================
    # RECEIVE
    # Commit collection in its own transaction, distinct from any later booking.
    # ==============================================

    @router.post(prefix + "/receipts")
    async def receive(
        *,
        organization_id: int,
        restaurant_id: int,
        branch_id: int,
        data: ReceiptInput,
        session: AsyncSession = session_dep,
        principal: OIDCPrincipal = principal_dep,
    ) -> dict[str, int]:
        """Commit collection in its own transaction, distinct from any later booking."""
        try:
            identifier = await DiningService(
                session=session, clock=clock
            ).record_receipt(
                principal=principal,
                organization_id=organization_id,
                restaurant_id=restaurant_id,
                branch_id=branch_id,
                data=data,
            )
        except TenantAccessDenied as error:
            raise HTTPException(
                status_code=403, detail="Dining access denied"
            ) from error
        except (TenantConflict, DiningError, IntegrityError) as error:
            raise HTTPException(
                status_code=409, detail="Dining receipt refused"
            ) from error
        return {"receipt_id": identifier}

    # ==============================================
    # ACCEPT QUOTE
    # Verify the actual customer principal; staff cannot consent in their name.
    # ==============================================

    @router.post(
        "/dining/restaurants/{restaurant_id}/branches/{branch_id}/quotes/{quote_id}/accept"
    )
    async def accept_quote(
        *,
        restaurant_id: int,
        branch_id: int,
        quote_id: int,
        data: AcceptQuoteInput,
        session: AsyncSession = session_dep,
        principal: OIDCPrincipal = principal_dep,
    ) -> dict[str, str]:
        """Verify the actual customer principal; staff cannot consent in their name."""
        try:
            await accept_customer_quote(
                session=session,
                principal=principal,
                restaurant_id=restaurant_id,
                branch_id=branch_id,
                quote_id=quote_id,
                expected_digest=data.digest,
                clock=clock,
            )
        except (DiningError, IntegrityError) as error:
            raise HTTPException(
                status_code=409, detail="Dining consent refused"
            ) from error
        return {"status": "accepted"}

    # ==============================================
    # PRINT CONFIRMATION
    # Create a printable authorized document only with an explicit trusted origin.
    # ==============================================

    @router.get(
        prefix + "/requests/{request_id}/confirmation", response_class=HTMLResponse
    )
    async def print_confirmation(
        *, request_id: int, locale: str = "fr", unit: DiningUnit = unit_dep
    ) -> HTMLResponse:
        """Create a printable authorized document only with an explicit trusted origin."""
        if verification_origin is None:
            raise DiningError(code="dining_verification_origin_configuration_required")
        document = await unit.confirmation_document(request_id=request_id)
        return HTMLResponse(
            content=printable_confirmation(
                document=document,
                verification_origin=verification_origin,
                locale=locale,
            ),
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
            },
        )

    # ==============================================
    # VERIFICATION PAGE
    # Serve a read-only same-origin viewer; token remains outside the HTTP URL.
    # ==============================================

    @router.get("/verify-reservation", response_class=HTMLResponse)
    async def verification_page(*, locale: str = "fr") -> HTMLResponse:
        """Serve the localized viewer without embedding customer data or a write power."""
        try:
            content, policy = verification_viewer(locale=locale)
        except DiningError as error:
            raise HTTPException(status_code=422, detail={"code": error.code}) from error
        return HTMLResponse(
            content,
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": policy,
            },
        )

    # ==============================================
    # VERIFY
    # Public read capability only; return no names, contacts, money or write token.
    # ==============================================

    @router.post("/dining/verify-reservation")
    async def verify(
        *,
        data: VerifyTicketInput,
        response: Response,
        session: AsyncSession = session_dep,
    ) -> TicketStatus:
        """Public read capability only; return no names, contacts, money or write token."""
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        try:
            return await verify_ticket(session=session, token=data.token)
        except DiningError as error:
            raise HTTPException(
                status_code=404, detail="Reservation unavailable"
            ) from error

    return router
