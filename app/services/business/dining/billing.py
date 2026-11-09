# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# RESTAURANT RECEIPTS AND FOOD INVOICE APPLICATION
# Keep received funds durable and use reviewed Decimal snapshots for legacy orders.
# ==============================================

"""Separate from SaaS billing; no charge, conversion, refund or fiscal invention."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND NEW FINANCIAL RECORDS
# Legacy Float fields are diagnostic source strings, never authoritative pricing.
# ==============================================

from decimal import Decimal

from sqlalchemy.orm import raiseload

from app.models.dining import (
    DiningAcceptance,
    DiningAllocation,
    DiningClaim,
    DiningInvoice,
    DiningInvoiceOrder,
    DiningOccupation,
    DiningOccupationTable,
    DiningQuote,
    DiningReceipt,
    DiningRequest,
)
from app.models.order import Order
from app.models.order_item import (
    OrderItem,
    OrderItemOption,
    OrderPayment,
)
from app.repositories.subscription_queries import base_select
from app.schemas.dining import (
    InvoiceInput,
    JsonObject,
    ReceiptInput,
)
from app.services.business.dining.pricing import DiningPricing
from app.services.business.dining.values import (
    DiningError,
    exact_product,
    exact_sum,
    final_amount,
    utc,
)

# ==============================================
# RECEIPT FACTS AND SINGLE RESERVATION INVOICE
# The facade exposes receipt recording as a separate clean committed operation.
# ==============================================


class DiningBilling(DiningPricing):
    """Persist human collection facts, finalize invoices and prevent credit reuse."""

    async def _record_receipt(self, *, data: ReceiptInput) -> int:
        """Record actual funds; late/partial/excess facts remain for human review.

        Only the facade may call this inside its own fresh transaction. It never
        combines receipt persistence with reservation confirmation or allocation.
        """
        await self.guard(capability="collect", human=True)
        policy = await self.policy()
        await self.expire_holds()
        request = await self.request(identifier=data.request_id)
        quote = await self.repo.one(model=DiningQuote, identifier=data.quote_id)
        if quote.request_id != request.id:
            raise DiningError(code="dining_resource_unavailable")
        received = utc(value=data.received_at)
        if received > self.now():
            raise DiningError(code="dining_received_funds_cannot_be_future")
        previous = (
            await self.session.execute(
                self.repo.statement(model=DiningReceipt)
                .where(
                    DiningReceipt.mode == data.mode,
                    DiningReceipt.reference == data.reference,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if previous is not None:
            if (
                previous.request_id,
                previous.quote_id,
                previous.received_amount,
                previous.currency,
                previous.received_at,
            ) != (
                data.request_id,
                data.quote_id,
                data.received_amount,
                data.currency,
                received,
            ):
                raise DiningError(code="dining_receipt_reference_conflict")
            return previous.id
        reasons: list[str] = []
        if data.currency != quote.currency:
            reasons.append("currency_mismatch")
        if data.received_amount != quote.amount:
            reasons.append("amount_mismatch")
        if data.mode not in policy.payment_instructions:
            reasons.append("unconfigured_payment_mode")
        if quote.expires_at <= self.now():
            reasons.append("proposal_expired")
        if request.status != "held":
            reasons.append("request_not_held")
        holds = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningClaim)
                    .where(
                        DiningClaim.request_id == request.id,
                        DiningClaim.kind == "hold",
                        DiningClaim.active.is_(True),
                    )
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        if not holds or any(
            row.expires_at is None
            or row.expires_at <= self.now()
            or received >= row.expires_at
            for row in holds
        ):
            reasons.append("late_or_expired_hold")
        latest = (
            await self.session.execute(
                self.repo.statement(model=DiningQuote)
                .where(DiningQuote.request_id == request.id)
                .order_by(DiningQuote.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest is None or latest.id != quote.id:
            reasons.append("superseded_proposal")
        acceptances = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningAcceptance).where(
                        DiningAcceptance.quote_id == quote.id,
                        DiningAcceptance.digest == quote.digest,
                    )
                )
            )
            .scalars()
            .all()
        )
        parties = {row.party for row in acceptances}
        if "customer" not in parties or (request.menu and "restaurant" not in parties):
            reasons.append("missing_exact_consents")
        other = (
            await self.session.execute(
                self.repo.statement(model=DiningReceipt)
                .where(
                    DiningReceipt.request_id == request.id,
                    DiningReceipt.status == "verified",
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if other is not None:
            reasons.append("additional_received_funds")
        receipt = await self.repo.persist(
            record=DiningReceipt(
                **self.scope(),
                request_id=request.id,
                quote_id=quote.id,
                expected_amount=quote.amount,
                received_amount=data.received_amount,
                currency=data.currency,
                mode=data.mode,
                reference=data.reference,
                received_at=received,
                validated_by=self.context.membership_id,
                status="manual_review" if reasons else "verified",
                review_reason=",".join(reasons) or None,
            )
        )
        await self.event(
            kind="advance.received",
            request_id=request.id,
            details={
                "receipt_id": receipt.id,
                "status": receipt.status,
                "manual_reasons": reasons,
            },
        )
        if reasons:
            await self.alert(
                request_id=request.id,
                event_key=f"advance.review:{receipt.id}",
                details={"receipt_id": receipt.id, "received_funds_retained": True},
            )
        return receipt.id

    # ==============================================
    # ORDER SOURCES
    # Lock exact source orders/items; refuse unscoped, unpaid-history ambiguity.
    # ==============================================

    async def _order_sources(
        self,
        *,
        request: DiningRequest | None,
        order_ids: tuple[int, ...],
        occupation_id: int | None = None,
    ) -> tuple[tuple[Order, ...], tuple[OrderItem, ...], list[JsonObject]]:
        """Lock exact source orders/items; refuse unscoped, unpaid-history ambiguity."""
        orders = tuple(
            (
                await self.session.execute(
                    base_select(Order)
                    .options(raiseload("*"))
                    .where(
                        Order.restaurant_id == self.repo.restaurant_id,
                        Order.branch_id == self.repo.branch_id,
                        Order.id.in_(order_ids),
                    )
                    .order_by(Order.id)
                    .with_for_update()
                )
            ).scalars()
        )
        if len(orders) != len(set(order_ids)):
            raise DiningError(code="dining_source_order_scope_mismatch")
        if request is not None:
            table_ids = set(await self.selected(request_id=request.id))
        else:
            table_ids = set(
                (
                    await self.session.execute(
                        self.repo.statement(model=DiningOccupationTable)
                        .with_only_columns(DiningOccupationTable.table_id)
                        .where(DiningOccupationTable.occupation_id == occupation_id)
                    )
                ).scalars()
            )
            from app.models.dining_service import (
                DiningVisit,
                DiningVisitOrder,
            )

            visit_orders = tuple(
                (
                    await self.session.execute(
                        self.repo.statement(model=DiningVisitOrder)
                        .join(DiningVisit, DiningVisit.id == DiningVisitOrder.visit_id)
                        .where(
                            DiningVisit.occupation_id == occupation_id,
                            DiningVisitOrder.order_id.in_(order_ids),
                        )
                    )
                ).scalars()
            )
            if {row.order_id for row in visit_orders} != set(order_ids):
                raise DiningError(code="dining_visit_invoice_order_scope_mismatch")
        for order in orders:
            if (
                order.status != "completed"
                or order.order_type != "dine_in"
                or order.table_id not in table_ids
            ):
                raise DiningError(code="dining_completed_reservation_order_required")
            if any(
                str(value) not in {"0", "0.0", "0.00"}
                for value in (
                    order.discount_amount,
                    order.tax_amount,
                    order.delivery_amount,
                )
            ):
                raise DiningError(
                    code="dining_legacy_adjustment_or_fiscal_contract_required"
                )
        paid = (
            await self.session.execute(
                base_select(OrderPayment)
                .with_only_columns(OrderPayment.id)
                .where(
                    OrderPayment.order_id.in_(order_ids),
                    OrderPayment.payment_status == "paid",
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if paid is not None:
            raise DiningError(
                code="dining_legacy_paid_amount_currency_requires_reconciliation_contract"
            )
        items = tuple(
            (
                await self.session.execute(
                    base_select(OrderItem)
                    .options(raiseload("*"))
                    .where(OrderItem.order_id.in_(order_ids))
                    .order_by(OrderItem.id)
                    .with_for_update()
                )
            ).scalars()
        )
        options = tuple(
            (
                await self.session.execute(
                    base_select(OrderItemOption)
                    .where(
                        OrderItemOption.order_item_id.in_(
                            tuple(item.id for item in items)
                        )
                    )
                    .order_by(OrderItemOption.id)
                    .with_for_update()
                )
            ).scalars()
        )
        snapshots: list[JsonObject] = []
        for order in orders:
            snapshots.append(
                {
                    "order_id": order.id,
                    "restaurant_id": order.restaurant_id,
                    "branch_id": order.branch_id,
                    "table_id": order.table_id,
                    "status": order.status,
                    "order_type": order.order_type,
                    "legacy_total": str(order.total_amount),
                    "legacy_money_not_authoritative": True,
                    "items": [
                        {
                            "id": line.id,
                            "product_id": line.product_id,
                            "quantity": line.quantity,
                            "description": line.product_name,
                            "legacy_unit_price": str(line.unit_price),
                            "legacy_total_price": str(line.total_price),
                            "options": [
                                {
                                    "id": option.id,
                                    "group": option.option_group_name,
                                    "name": option.option_name,
                                    "legacy_additional_price": str(
                                        option.additional_price
                                    ),
                                }
                                for option in options
                                if option.order_item_id == line.id
                            ],
                        }
                        for line in items
                        if line.order_id == order.id
                    ],
                }
            )
        return orders, items, snapshots

    # ==============================================
    # PREPARE INVOICE
    # Prepare one food invoice from fully identified reviewed exact sources.
    # ==============================================

    async def prepare_invoice(self, *, data: InvoiceInput) -> int:
        """Prepare one food invoice from fully identified reviewed exact sources.

        No existing Float amount is rewritten or promoted to authoritative money.
        Existing taxes, adjustments or paid Float receipts require another
        explicit reconciliation contract and block only their affected invoice.
        """
        await self.guard(capability="invoices.create", human=True)
        policy = await self.policy()
        request = (
            await self.request(identifier=data.request_id)
            if data.request_id is not None
            else None
        )
        if request is not None and request.status not in {
            "confirmed",
            "arrived",
            "served",
        }:
            raise DiningError(code="dining_invoice_reservation_required")
        if data.occupation_id is not None:
            occupation = await self.repo.one(
                model=DiningOccupation, identifier=data.occupation_id, lock=True
            )
            if occupation.status != "occupied":
                raise DiningError(code="dining_live_occupation_required")
        if data.currency not in policy.currencies:
            raise DiningError(code="dining_invoice_currency_configuration_missing")
        existing = (
            await self.session.execute(
                self.repo.statement(model=DiningInvoice)
                .where(
                    DiningInvoice.request_id == request.id
                    if request is not None
                    else DiningInvoice.occupation_id == data.occupation_id
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise DiningError(
                code="dining_one_invoice_per_reservation_existing_invoice_requires_review"
            )
        order_ids = tuple(sorted({line.order_id for line in data.lines}))
        orders, items, snapshots = await self._order_sources(
            request=request, order_ids=order_ids, occupation_id=data.occupation_id
        )
        by_id = {item.id: item for item in items}
        if set(by_id) != {line.order_item_id for line in data.lines}:
            raise DiningError(code="dining_invoice_must_reconcile_complete_order_items")
        # A QR order already carries an authoritative exact tariff snapshot.
        # The finance form may review it, but cannot substitute another unit price.
        from app.models.dining_service import DiningVisitOrder

        exact_sources = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningVisitOrder).where(
                        DiningVisitOrder.order_id.in_(order_ids)
                    )
                )
            ).scalars()
        )
        for source in exact_sources:
            if source.currency != data.currency:
                raise DiningError(code="dining_cross_currency_invoice_forbidden")
            by_item = {int(row["order_item_id"]): row for row in source.exact_lines}
            for line in data.lines:
                if line.order_id == source.order_id:
                    exact = by_item.get(line.order_item_id)
                    if (
                        exact is None
                        or Decimal(str(exact["quantity"])) != line.quantity
                        or Decimal(str(exact["unit_price"])) != line.unit_price
                        or exact["description"] != line.description
                    ):
                        raise DiningError(
                            code="dining_visit_invoice_exact_source_mismatch"
                        )
        precision = policy.currencies[data.currency]
        lines: list[JsonObject] = []
        amounts: list[Decimal] = []
        discrepancies: list[int] = []
        for line in data.lines:
            item = by_id[line.order_item_id]
            if (
                item.order_id != line.order_id
                or Decimal(item.quantity) != line.quantity
            ):
                raise DiningError(code="dining_invoice_order_item_quantity_mismatch")
            amount = exact_product(left=line.quantity, right=line.unit_price)
            # This comparison is diagnostic only. It neither repairs Float
            # precision nor provides values to the invoice calculation.
            legacy = Decimal(str(item.total_price))
            if (
                not legacy.is_finite()
                or legacy < 0
                or final_amount(value=legacy, precision=precision)
                != final_amount(value=amount, precision=precision)
            ):
                discrepancies.append(item.id)
            amounts.append(amount)
            lines.append(
                {
                    "order_id": line.order_id,
                    "order_item_id": line.order_item_id,
                    "description": line.description,
                    "quantity": str(line.quantity),
                    "unit_price": str(line.unit_price),
                    "amount": str(amount),
                    "source_reference": line.source_reference,
                }
            )
        amount = final_amount(
            value=exact_sum(values=tuple(amounts)), precision=precision
        )
        legacy_total = sum(
            (Decimal(str(order.total_amount)) for order in orders), Decimal(0)
        )
        if (
            not legacy_total.is_finite()
            or legacy_total < 0
            or final_amount(value=legacy_total, precision=precision) != amount
        ):
            discrepancies.extend(order.id for order in orders)
        if discrepancies and not data.legacy_discrepancies_acknowledged:
            raise DiningError(code="dining_legacy_decimal_discrepancy_requires_review")
        provenance: JsonObject = {
            "kind": "reviewed_exact_decimal_source",
            "currency_source": data.currency_source,
            "rounding_source": data.rounding_source,
            "rounding": "ROUND_HALF_UP_final_total",
            "reconciliation_reference": data.reconciliation_reference,
            "reviewed_by": self.context.membership_id,
            "legacy_discrepancies_acknowledged": data.legacy_discrepancies_acknowledged,
            "legacy_discrepancy_ids": sorted(set(discrepancies)),
            "source_snapshots": snapshots,
            "no_fiscal_rule_inferred": True,
        }
        invoice = await self.repo.persist(
            record=DiningInvoice(
                **self.scope(),
                request_id=request.id if request else None,
                occupation_id=data.occupation_id,
                status="draft",
                currency=data.currency,
                precision=precision,
                revision=1,
                lines=lines,
                provenance=provenance,
                total=amount,
            )
        )
        for snapshot in snapshots:
            await self.repo.persist(
                record=DiningInvoiceOrder(
                    **self.scope(),
                    invoice_id=invoice.id,
                    order_id=snapshot["order_id"],
                    source_snapshot=snapshot,
                )
            )
        await self.event(
            kind="invoice.prepared",
            request_id=request.id if request else None,
            details={
                "invoice_id": invoice.id,
                "currency": data.currency,
                "legacy_discrepancies": bool(discrepancies),
            },
        )
        return invoice.id

    # ==============================================
    # FINALIZE INVOICE
    # Freeze a reconciled draft only after actual arrival and unchanged source proof.
    # ==============================================

    async def finalize_invoice(
        self, *, invoice_id: int, expected_revision: int
    ) -> Decimal:
        """Freeze a reconciled draft only after actual arrival and unchanged source proof."""
        await self.guard(capability="invoices.finalize", human=True)
        await self.policy()
        invoice = await self.repo.one(
            model=DiningInvoice, identifier=invoice_id, lock=True
        )
        request = (
            await self.request(identifier=invoice.request_id)
            if invoice.request_id is not None
            else None
        )
        occupation = (
            await self.repo.one(
                model=DiningOccupation, identifier=invoice.occupation_id, lock=True
            )
            if invoice.occupation_id is not None
            else None
        )
        if invoice.status == "finalized":
            return invoice.total
        if (
            (request is not None and request.status not in {"arrived", "served"})
            or (occupation is not None and occupation.status != "occupied")
            or invoice.revision != expected_revision
        ):
            raise DiningError(code="dining_invoice_arrival_or_revision_required")
        links = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningInvoiceOrder)
                    .where(DiningInvoiceOrder.invoice_id == invoice.id)
                    .order_by(DiningInvoiceOrder.order_id)
                )
            ).scalars()
        )
        if (
            not links
            or not invoice.lines
            or invoice.provenance.get("kind") != "reviewed_exact_decimal_source"
        ):
            raise DiningError(code="dining_invoice_reliable_provenance_required")
        _orders, _items, snapshots = await self._order_sources(
            request=request,
            order_ids=tuple(row.order_id for row in links),
            occupation_id=invoice.occupation_id,
        )
        if snapshots != invoice.provenance.get("source_snapshots"):
            raise DiningError(
                code="dining_invoice_source_changed_new_reconciliation_required"
            )
        recomputed = final_amount(
            value=exact_sum(
                values=tuple(
                    exact_product(
                        left=Decimal(str(line["quantity"])),
                        right=Decimal(str(line["unit_price"])),
                    )
                    for line in invoice.lines
                )
            ),
            precision=invoice.precision,
        )
        if recomputed != invoice.total:
            raise DiningError(code="dining_invoice_total_mismatch")
        invoice.status, invoice.finalized_at = "finalized", self.now()
        invoice.finalized_by, invoice.revision = (
            self.context.membership_id,
            invoice.revision + 1,
        )
        await self.session.flush()
        await self.event(
            kind="invoice.finalized",
            request_id=request.id if request else None,
            details={"invoice_id": invoice.id, "currency": invoice.currency},
        )
        if request is None:
            return invoice.total
        receipts = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningReceipt)
                    .where(
                        DiningReceipt.request_id == request.id,
                        DiningReceipt.status == "verified",
                    )
                    .order_by(DiningReceipt.id)
                )
            )
            .scalars()
            .all()
        )
        if len(receipts) == 1:
            # Applying verified funds is not a new collection approval; it is
            # atomic with invoice finalization and uses the existing receipt.
            await self.guard(capability="advances.allocate", human=True)
            await self._apply_advance(invoice_id=invoice.id, receipt_id=receipts[0].id)
        elif receipts:
            raise DiningError(
                code="dining_multiple_verified_advances_require_manual_review"
            )
        return invoice.total

    # ==============================================
    # ALLOCATE ADVANCE
    # Apply an entire verified advance once without changing sales or refunding excess.
    # ==============================================

    async def allocate_advance(
        self, *, invoice_id: int, receipt_id: int
    ) -> dict[str, str | int]:
        """Apply an entire verified advance once without changing sales or refunding excess."""
        await self.guard(capability="advances.allocate", human=True)
        await self.policy()
        return await self._apply_advance(invoice_id=invoice_id, receipt_id=receipt_id)

    # ==============================================
    # APPLY ADVANCE
    # Apply received funds after the caller's explicit financial guards.
    # ==============================================

    async def _apply_advance(
        self, *, invoice_id: int, receipt_id: int
    ) -> dict[str, str | int]:
        """Apply received funds after the caller's explicit financial guards."""
        invoice = await self.repo.one(
            model=DiningInvoice, identifier=invoice_id, lock=True
        )
        if invoice.request_id is None:
            raise DiningError(code="dining_reservation_advance_required")
        request = await self.request(identifier=invoice.request_id)
        receipt = await self.repo.one(
            model=DiningReceipt, identifier=receipt_id, lock=True
        )
        previous = (
            await self.session.execute(
                self.repo.statement(model=DiningAllocation)
                .where(DiningAllocation.receipt_id == receipt_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if previous is not None:
            if previous.invoice_id != invoice_id:
                raise DiningError(code="dining_advance_already_allocated")
            return {
                "allocation_id": previous.id,
                "invoice_total": str(previous.invoice_total),
                "advance": str(previous.amount),
                "balance": str(previous.balance),
                "currency": previous.currency,
            }
        if (
            invoice.status != "finalized"
            or request.status not in {"arrived", "served"}
            or receipt.request_id != request.id
            or receipt.status != "verified"
        ):
            raise DiningError(
                code="dining_finalized_matching_invoice_and_receipt_required"
            )
        if receipt.currency != invoice.currency:
            raise DiningError(code="dining_cross_currency_allocation_forbidden")
        existing = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningAllocation).where(
                        DiningAllocation.invoice_id == invoice_id
                    )
                )
            )
            .scalars()
            .all()
        )
        already_paid = sum((row.amount for row in existing), Decimal(0))
        if receipt.received_amount > invoice.total - already_paid:
            await self.event(
                kind="advance.excess_requires_decision",
                request_id=request.id,
                details={"invoice_id": invoice_id, "receipt_id": receipt_id},
            )
            await self.alert(
                request_id=request.id,
                event_key=f"advance.excess:{receipt_id}",
                details={"no_refund": True, "no_negative_balance": True},
            )
            return {
                "status": "manual_review",
                "reason": "advance_excess",
                "invoice_total": str(invoice.total),
                "advance": str(receipt.received_amount),
                "unallocated_excess": str(
                    receipt.received_amount - (invoice.total - already_paid)
                ),
                "currency": invoice.currency,
            }
        amount = receipt.received_amount
        balance = invoice.total - already_paid - amount
        allocation = await self.repo.persist(
            record=DiningAllocation(
                **self.scope(),
                request_id=request.id,
                receipt_id=receipt_id,
                invoice_id=invoice_id,
                invoice_revision=invoice.revision,
                invoice_total=invoice.total,
                other_paid=already_paid,
                amount=amount,
                currency=invoice.currency,
                balance=balance,
            )
        )
        await self.event(
            kind="advance.allocated",
            request_id=request.id,
            details={
                "allocation_id": allocation.id,
                "invoice_id": invoice.id,
                "receipt_id": receipt.id,
            },
        )
        return {
            "allocation_id": allocation.id,
            "invoice_total": str(invoice.total),
            "advance": str(amount),
            "balance": str(balance),
            "currency": invoice.currency,
        }
