# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TEST MODULE - TESTS / TEST ORDER ARCHITECTURE BOUNDARIES
# Automated test coverage for the MoulAI platform.
# ==============================================

"""Boundary tests that protect responsibilities and monetary validation."""

import ast
from pathlib import Path
import pytest
from app.core.exceptions import ValidationError
from app.services.business.orders.pricing import item_total

# ==============================================
# TEST ORDER ACTION DELEGATES WITHOUT PRICING OR TRANSACTION RULES
# ==============================================


def test_order_action_delegates_without_pricing_or_transaction_rules():
    tree = ast.parse(
        Path("app/agent/executor/actions.py").read_text(encoding="utf-8-sig")
    )
    action = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "OrderFoodAction"
    )
    calls = [node for node in ast.walk(action) if isinstance(node, ast.Call)]
    assert not any(
        isinstance(node.func, ast.Attribute)
        and node.func.attr in {"commit", "rollback", "get_by_id", "search"}
        for node in calls
    )
    assert not any(
        isinstance(node, ast.BinOp)
        and isinstance(node.op, (ast.Mult, ast.Add, ast.Sub))
        for node in ast.walk(action)
    )


# ==============================================
# TEST INVALID PRICES AND QUANTITIES CANNOT ENTER ORDER CALCULATION
# ==============================================


@pytest.mark.parametrize(
    "price,quantity",
    [
        (float("nan"), 1),
        (float("inf"), 1),
        (-1, 1),
        (1, True),
        (1, 0),
        (1, 101),
        (1, 1.5),
    ],
)
def test_invalid_prices_and_quantities_cannot_enter_order_calculation(price, quantity):
    with pytest.raises(ValidationError):
        item_total(price, quantity)
