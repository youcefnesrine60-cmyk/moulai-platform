# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TEST MODULE - TESTS / TEST AGENT ORDER ENTITY EXTRACTION
# Automated test coverage for the MoulAI platform.
# ==============================================

"""Automated tests for test agent order entity extraction.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import pytest

from app.agent.nlu.entity_extractor import EntityExtractor

# ==============================================
# TEST ORDER REFERENCE AND QUANTITY ARE EXTRACTED WITHOUT CONFUSION
# ==============================================


@pytest.mark.parametrize(
    ("message", "expected_order_id", "expected_quantity"),
    [
        ("Track order RST1-000017", "RST1-000017", None),
        (
            "Change quantity of Pizza in order RST1-000017 to 4",
            "RST1-000017",
            4,
        ),
        (
            "Modifier la quantité de Pizza de la commande RST1-000017 à 3",
            "RST1-000017",
            3,
        ),
    ],
)
def test_order_reference_and_quantity_are_extracted_without_confusion(
    message,
    expected_order_id,
    expected_quantity,
):
    entities = EntityExtractor()._extract_with_patterns(
        text=message,
        language="fr" if message.startswith("Modifier") else "en",
    )
    extracted = {entity["type"]: entity["value"] for entity in entities}

    assert extracted.get("order_id") == expected_order_id
    assert extracted.get("quantity") == expected_quantity
