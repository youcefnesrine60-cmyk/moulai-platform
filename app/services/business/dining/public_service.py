# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PUBLIC MENU AND CONTROLLED VISIT TRANSACTIONS
# Resolve opaque read targets and independently hashed visit proofs without staff impersonation.
# ==============================================

"""No public request can confirm presence, preparation, money or administrative grants."""

from __future__ import annotations

# isort: split
# ==============================================
# SCOPED SOURCES AND EXACT ORDER PROVENANCE
# The injected session owns one clean transaction; no application connection is selected.
# ==============================================

import hashlib
import re
from collections.abc import Callable
from datetime import (
    datetime,
    timedelta,
)
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.branch import Branch
from app.models.category import Category
from app.models.dining import (
    DiningEvent,
    DiningInvoice,
    DiningOccupation,
    DiningOccupationTable,
    DiningReceipt,
    DiningReference,
    DiningRequest,
    DiningTable,
    DiningTariff,
)
from app.models.dining_service import (
    DiningPresenceSignal,
    DiningPublicLink,
    DiningVisit,
    DiningVisitOrder,
)
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.restaurant import Restaurant
from app.models.tenant.schema import (
    Organization,
    restaurant_reference,
)
from app.repositories.dining_repo import DiningRepository
from app.repositories.subscription_queries import base_select
from app.schemas.dining import (
    DiningPolicyInput,
    JsonObject,
)
from app.schemas.dining_public import (
    PresenceInput,
    VisitOrderInput,
)
from app.services.business.dining.values import (
    DiningError,
    content_digest,
    exact_product,
    exact_sum,
    final_amount,
    utc,
    utc_now,
)
from app.services.business.orders.create import create_restaurant_order
from app.services.business.orders.transaction import order_transaction
from app.services.business.tenant_foundation import tenant_unit_of_work

# ==============================================
# OPAQUE SECRET ADMISSION
# Read identifiers and write proofs are separate, bounded and never emitted to logs.
# ==============================================


def visit_hash(*, token: str) -> str:
    """Reject malformed credentials before hashing; callers never persist the bearer secret."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise DiningError(code="dining_visit_secret_invalid")
    return hashlib.sha256(token.encode("ascii")).hexdigest()


# ==============================================
# PUBLIC BROKER
# An opaque target establishes scope, while only a staff-created visit allows an order request.
# ==============================================


class PublicDiningService:
    """Expose redacted reads and bounded customer requests with no staff capability."""

    # ==============================================
    # EXPLICIT SESSION AND CLOCK
    # Construction cannot discover a database or call any external service.
    # ==============================================

    def __init__(
        self, *, session: AsyncSession, clock: Callable[[], datetime] = utc_now
    ) -> None:
        """Keep trusted dependencies supplied by the isolated host."""
        self.session, self.clock = session, clock

    # ==============================================
    # RESOLVE A CURRENT PUBLIC TARGET
    # Recheck live company, restaurant, branch and link under the same scope as staff.
    # ==============================================

    async def _target(
        self, *, public_id: str, write: bool
    ) -> tuple[DiningPublicLink, DiningRepository]:
        """Use no caller-provided tenant ID and expose the same rejection for foreign/absent links."""
        visit_hash(token=public_id)
        link = await self.session.scalar(
            base_select(DiningPublicLink).where(DiningPublicLink.public_id == public_id)
        )
        if link is None:
            raise DiningError(code="dining_public_link_unavailable")
        organization = await self.session.scalar(
            select(Organization)
            .join(
                restaurant_reference,
                restaurant_reference.c.organization_id == Organization.id,
            )
            .where(
                restaurant_reference.c.id == link.restaurant_id,
                Organization.status == "active",
                Organization.tenant_enforced_at.is_not(None),
            )
            .with_for_update(read=True, of=Organization)
        )
        available = await self.session.scalar(
            select(Branch.id)
            .join(Restaurant, Restaurant.id == Branch.restaurant_id)
            .where(
                Restaurant.id == link.restaurant_id,
                Restaurant.is_active.is_(True),
                Branch.id == link.branch_id,
                Branch.is_active.is_(True),
            )
        )
        if organization is None or available is None:
            raise DiningError(code="dining_public_link_unavailable")
        repo = DiningRepository(
            session=self.session,
            restaurant_id=link.restaurant_id,
            branch_id=link.branch_id,
        )
        await repo.policy(lock=write)
        if write:
            # Serialize writes before promoting restaurant locks used by legacy orders.
            # Two visitors must not hold SHARE locks and then both try to upgrade them.
            available = await self.session.scalar(
                select(Branch.id)
                .join(Restaurant, Restaurant.id == Branch.restaurant_id)
                .where(
                    Restaurant.id == link.restaurant_id,
                    Restaurant.is_active.is_(True),
                    Branch.id == link.branch_id,
                    Branch.is_active.is_(True),
                )
                .with_for_update(of=(Restaurant, Branch))
            )
            if available is None:
                raise DiningError(code="dining_public_link_unavailable")
        link = await repo.one(model=DiningPublicLink, identifier=link.id, lock=write)
        if not link.active:
            raise DiningError(code="dining_public_link_unavailable")
        if link.kind == "table":
            table = await repo.one(
                model=DiningTable, identifier=link.table_id, lock=write
            )
            if not table.in_service:
                raise DiningError(code="dining_public_table_disabled")
        return link, repo

    # ==============================================
    # CURRENT PUBLIC MENU
    # Only an explicit public-product tariff supplies money; legacy Float prices never do.
    # ==============================================

    async def _menu(
        self, *, link: DiningPublicLink, repo: DiningRepository, currency: str | None
    ) -> JsonObject:
        """Return live identification and exact purchasable sources without other clients' history."""
        if link.kind != "table":
            raise DiningError(code="dining_public_table_required")
        table = await repo.one(model=DiningTable, identifier=link.table_id)
        policy_row = await repo.policy()
        policy = DiningPolicyInput.model_validate(
            {**policy_row.settings, "timezone": policy_row.timezone}
        )
        if currency is None:
            currency = (
                next(iter(policy.currencies)) if len(policy.currencies) == 1 else None
            )
        if currency is not None and currency not in policy.currencies:
            raise DiningError(code="dining_menu_currency_selection_required")
        now = utc(value=self.clock())
        products = tuple(
            (
                await self.session.execute(
                    base_select(Product)
                    .join(Category, Category.id == Product.category_id)
                    .where(
                        Category.restaurant_id == repo.restaurant_id,
                        Product.restaurant_id == repo.restaurant_id,
                        Product.is_available.is_(True),
                    )
                    .order_by(Product.id)
                    .limit(250)
                )
            ).scalars()
        )
        tariffs = tuple(
            (
                await self.session.execute(
                    repo.statement(model=DiningTariff).where(
                        DiningTariff.component == "menu",
                        DiningTariff.unit == "per_item",
                        DiningTariff.currency == currency,
                        DiningTariff.valid_from <= now,
                        or_(
                            DiningTariff.valid_until.is_(None),
                            DiningTariff.valid_until > now,
                        ),
                    )
                )
            ).scalars()
        )
        menu = []
        for product in products:
            rates = [
                row
                for row in tariffs
                if row.reference == "public-product:" + str(product.id)
            ]
            rate = rates[0] if len(rates) == 1 else None
            menu.append(
                {
                    "product_id": product.id,
                    "name": product.name,
                    "unit_price": format(rate.unit_price, "f") if rate else None,
                    "tariff_id": rate.id if rate else None,
                    "orderable": rate is not None,
                }
            )
        exact = {
            "currency": currency,
            "precision": policy.currencies[currency] if currency is not None else None,
            "currencies": sorted(policy.currencies),
            "products": menu,
        }
        location = await repo.one(model=DiningReference, identifier=table.location_id)
        zone = await repo.one(model=DiningReference, identifier=table.zone_id)
        return {
            **exact,
            "menu_digest": content_digest(value=exact),
            "reference": link.reference,
            "restaurant": await self.session.scalar(
                select(Restaurant.name).where(Restaurant.id == repo.restaurant_id)
            ),
            "branch": await self.session.scalar(
                select(Branch.name).where(Branch.id == repo.branch_id)
            ),
            "table": {
                "code": table.code,
                "floor": table.floor_label,
                "room": table.room_label,
                "zone": zone.labels,
                "location": location.labels,
                "physical_state": (
                    table.physical_state
                    if link.snapshot.get("public_physical_state") is True
                    else None
                ),
            },
            "scan_confirms_presence": False,
            "availability_certified": False,
        }

    # ==============================================
    # READ WITHOUT SIDE EFFECTS
    # Opening or refreshing a QR cannot create a presence signal or occupation.
    # ==============================================

    async def menu(self, *, public_id: str, currency: str | None = None) -> JsonObject:
        """Resolve the current menu in a clean read transaction without recording a scan event."""
        async with tenant_unit_of_work(session=self.session):
            link, repo = await self._target(public_id=public_id, write=False)
            result = await self._menu(link=link, repo=repo, currency=currency)
        return result

    # ==============================================
    # CUSTOMER EVENT WITHOUT HUMAN AUTHORITY
    # Exactly one signal is kept per tab credential, with an explicit short technical lifetime.
    # ==============================================

    async def signal(
        self, *, public_id: str, token: str, data: PresenceInput
    ) -> JsonObject:
        """Request observation; never move a table to occupied or assert availability."""
        digest = visit_hash(token=token)
        async with tenant_unit_of_work(session=self.session):
            link, repo = await self._target(public_id=public_id, write=True)
            if link.kind != "table":
                raise DiningError(code="dining_public_table_required")
            table = await repo.one(model=DiningTable, identifier=link.table_id)
            if data.party_size > table.max_capacity:
                raise DiningError(code="dining_table_capacity_exceeded")
            previous = await self.session.scalar(
                base_select(DiningPresenceSignal)
                .where(DiningPresenceSignal.token_hash == digest)
                .with_for_update()
            )
            if previous is not None:
                if (
                    previous.public_link_id != link.id
                    or previous.party_size != data.party_size
                ):
                    raise DiningError(code="dining_presence_reference_conflict")
                return {
                    "identifier": previous.id,
                    "status": previous.status,
                    "expires_at": previous.expires_at.isoformat(),
                }
            now = utc(value=self.clock())
            pending = tuple(
                (
                    await self.session.execute(
                        repo.statement(model=DiningPresenceSignal)
                        .where(
                            DiningPresenceSignal.table_id == link.table_id,
                            DiningPresenceSignal.status == "pending",
                            DiningPresenceSignal.expires_at > now,
                        )
                        .limit(20)
                    )
                ).scalars()
            )
            if len(pending) >= 20:
                raise DiningError(code="dining_presence_queue_full")
            row = await repo.persist(
                record=DiningPresenceSignal(
                    restaurant_id=repo.restaurant_id,
                    branch_id=repo.branch_id,
                    public_link_id=link.id,
                    table_id=link.table_id,
                    token_hash=digest,
                    party_size=data.party_size,
                    status="pending",
                    expires_at=now + timedelta(minutes=15),
                )
            )
            await repo.persist(
                record=DiningEvent(
                    restaurant_id=repo.restaurant_id,
                    branch_id=repo.branch_id,
                    request_id=None,
                    kind="presence.signalled",
                    author={"kind": "customer-signal"},
                    details={
                        "presence_id": row.id,
                        "table_id": row.table_id,
                        "no_installation": True,
                    },
                    occurred_at=now,
                )
            )
            result = {
                "identifier": row.id,
                "status": row.status,
                "expires_at": row.expires_at.isoformat(),
            }
        logger.info(
            "Dining presence signal committed",
            extra={
                "restaurant_id": repo.restaurant_id,
                "branch_id": repo.branch_id,
                "presence_id": row.id,
            },
        )
        return result

    # ==============================================
    # ACTIVE VISIT ADMISSION
    # A predicted end never ends occupation; actual departure and link revocation do.
    # ==============================================

    async def _visit(
        self, *, link: DiningPublicLink, repo: DiningRepository, token: str
    ) -> DiningVisit:
        """Require a staff-installed visit with a still-active physical assignment."""
        visit = await self.session.scalar(
            repo.statement(model=DiningVisit)
            .where(
                DiningVisit.public_link_id == link.id,
                DiningVisit.token_hash == visit_hash(token=token),
            )
            .with_for_update()
        )
        if visit is None or visit.status != "active":
            raise DiningError(code="dining_visit_not_active")
        occupation = await repo.one(
            model=DiningOccupation, identifier=visit.occupation_id, lock=True
        )
        assignment = await self.session.scalar(
            repo.statement(model=DiningOccupationTable).where(
                DiningOccupationTable.occupation_id == occupation.id,
                DiningOccupationTable.table_id == visit.table_id,
                DiningOccupationTable.active.is_(True),
            )
        )
        if occupation.status != "occupied" or assignment is None:
            raise DiningError(code="dining_visit_closed")
        return visit

    # ==============================================
    # OWN VISIT STATUS ONLY
    # No public read can enumerate another table's customers or historical orders.
    # ==============================================

    async def visit(self, *, public_id: str, token: str) -> JsonObject:
        """Return only this credential's signal, active visit and order requests."""
        async with tenant_unit_of_work(session=self.session):
            link, repo = await self._target(public_id=public_id, write=True)
            signal = await self.session.scalar(
                repo.statement(model=DiningPresenceSignal).where(
                    DiningPresenceSignal.public_link_id == link.id,
                    DiningPresenceSignal.token_hash == visit_hash(token=token),
                )
            )
            if signal is None:
                return {"status": "not_signalled", "orders": []}
            if signal.status != "installed":
                return {
                    "status": (
                        "pending"
                        if signal.expires_at > utc(value=self.clock())
                        else "expired"
                    ),
                    "orders": [],
                }
            try:
                visit = await self._visit(link=link, repo=repo, token=token)
            except DiningError as error:
                if error.code not in {"dining_visit_not_active", "dining_visit_closed"}:
                    raise
                # Ending a visit revokes ordering, not the public restaurant menu.
                return {"status": "ended", "orders": []}
            records = tuple(
                (
                    await self.session.execute(
                        repo.statement(model=DiningVisitOrder)
                        .where(DiningVisitOrder.visit_id == visit.id)
                        .order_by(DiningVisitOrder.id)
                    )
                ).scalars()
            )
            result = {
                "status": "active",
                "orders": [
                    {
                        "order_id": row.order_id,
                        "currency": row.currency,
                        "total": format(row.total, "f"),
                        "lines": row.exact_lines,
                        "status": await self.session.scalar(
                            select(Order.status).where(
                                Order.id == row.order_id,
                                Order.restaurant_id == repo.restaurant_id,
                                Order.branch_id == repo.branch_id,
                            )
                        ),
                    }
                    for row in records
                ],
            }
        return result

    # ==============================================
    # IDEMPOTENT FOOD REQUEST
    # Staff approval remains separate; exact snapshots are authoritative over the Float bridge.
    # ==============================================

    async def order(
        self, *, public_id: str, token: str, data: VisitOrderInput
    ) -> JsonObject:
        """Create one pending scoped food order atomically with exact sources and no payment."""
        async with tenant_unit_of_work(session=self.session):
            link, repo = await self._target(public_id=public_id, write=True)
            visit = await self._visit(link=link, repo=repo, token=token)
            digest = content_digest(value=data.model_dump(mode="json"))
            previous = await self.session.scalar(
                repo.statement(model=DiningVisitOrder).where(
                    DiningVisitOrder.visit_id == visit.id,
                    DiningVisitOrder.idempotency_key == data.idempotency_key,
                )
            )
            if previous is not None:
                if previous.digest != digest:
                    raise DiningError(code="dining_visit_order_reference_conflict")
                return {
                    "identifier": previous.order_id,
                    "total": format(previous.total, "f"),
                    "currency": previous.currency,
                    "status": "persisted",
                }
            menu = await self._menu(link=link, repo=repo, currency=data.currency)
            if menu["menu_digest"] != data.menu_digest:
                raise DiningError(code="dining_menu_changed_review_required")
            sources = {item["product_id"]: item for item in menu["products"]}
            lines = []
            for selected in data.lines:
                item = sources.get(selected.product_id)
                if item is None or item["orderable"] is not True:
                    raise DiningError(code="dining_menu_product_unavailable")
                price = Decimal(item["unit_price"])
                lines.append(
                    {
                        "product_id": selected.product_id,
                        "description": item["name"],
                        "quantity": str(selected.quantity),
                        "unit_price": format(price, "f"),
                        "amount": format(
                            exact_product(left=price, right=Decimal(selected.quantity)),
                            "f",
                        ),
                        "tariff_id": item["tariff_id"],
                    }
                )
            total = final_amount(
                value=exact_sum(values=tuple(Decimal(row["amount"]) for row in lines)),
                precision=menu["precision"],
            )
            async with order_transaction(self.session):
                identifier = await create_restaurant_order(
                    session=self.session,
                    restaurant_id=repo.restaurant_id,
                    branch_id=repo.branch_id,
                    table_id=visit.table_id,
                    employee_id=None,
                    user_id=None,
                    order_number="VISIT-" + uuid4().hex,
                    order_type="dine_in",
                    customer_name=None,
                    customer_phone=None,
                    delivery_address=None,
                    customer_note=None,
                    subtotal_amount=float(total),
                    discount_amount=0,
                    tax_amount=0,
                    delivery_amount=0,
                    total_amount=float(total),
                )
                for line in lines:
                    item = OrderItem(
                        order_id=identifier,
                        product_id=line["product_id"],
                        product_name=line["description"],
                        quantity=int(line["quantity"]),
                        unit_price=float(Decimal(line["unit_price"])),
                        total_price=float(Decimal(line["amount"])),
                    )
                    self.session.add(item)
                    await self.session.flush()
                    line["order_item_id"] = item.id
                await repo.persist(
                    record=DiningVisitOrder(
                        restaurant_id=repo.restaurant_id,
                        branch_id=repo.branch_id,
                        visit_id=visit.id,
                        order_id=identifier,
                        idempotency_key=data.idempotency_key,
                        currency=data.currency,
                        exact_lines=lines,
                        total=total,
                        digest=digest,
                    )
                )
            await repo.persist(
                record=DiningEvent(
                    restaurant_id=repo.restaurant_id,
                    branch_id=repo.branch_id,
                    request_id=None,
                    kind="visit.order.requested",
                    author={"kind": "visit-customer"},
                    details={
                        "visit_id": visit.id,
                        "order_id": identifier,
                        "no_preparation_approval": True,
                        "no_payment": True,
                    },
                    occurred_at=utc(value=self.clock()),
                )
            )
        logger.info(
            "Dining visit order committed",
            extra={
                "restaurant_id": repo.restaurant_id,
                "branch_id": repo.branch_id,
                "order_id": identifier,
            },
        )
        return {
            "identifier": identifier,
            "currency": data.currency,
            "total": format(total, "f"),
            "status": "pending",
        }

    # ==============================================
    # REDACTED DOCUMENT VERIFICATION
    # Current status is checked against a retained emitted version without altering its content.
    # ==============================================

    async def verify(self, *, public_id: str) -> JsonObject:
        """Return reference, version, digest and validity only; no customer, amount or contact data."""
        async with tenant_unit_of_work(session=self.session):
            visit_hash(token=public_id)
            link = await self.session.scalar(
                base_select(DiningPublicLink).where(
                    DiningPublicLink.public_id == public_id
                )
            )
            if link is None:
                return {"status": "invalid"}
            status = (
                "valid"
                if link.active
                else (
                    "replaced"
                    if link.invalidated_reason == "replaced"
                    else "invalidated"
                )
            )
            if link.active:
                try:
                    link, repo = await self._target(public_id=public_id, write=False)
                except DiningError:
                    status = "invalid"
                else:
                    if link.kind == "reservation":
                        request = await repo.one(
                            model=DiningRequest, identifier=link.request_id
                        )
                        if request.status == "cancelled":
                            status = "cancelled"
                        elif request.status not in {"confirmed", "arrived", "served"}:
                            status = "invalid"
                    elif link.kind == "food_invoice":
                        invoice = await repo.one(
                            model=DiningInvoice, identifier=link.invoice_id
                        )
                        if (
                            invoice.status != "finalized"
                            or invoice.revision != link.version
                        ):
                            status = "invalid"
                    elif link.kind == "receipt":
                        receipt = await repo.one(
                            model=DiningReceipt, identifier=link.receipt_id
                        )
                        if receipt.status != "verified":
                            status = "invalid"
                    else:
                        status = "table_menu"
            return {
                "status": status,
                "reference": link.reference,
                "kind": link.kind,
                "version": link.version,
                "digest": link.digest,
            }
