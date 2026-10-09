# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TEST MODULE - TESTS / TEST SUBSCRIPTION COMPAT
# Automated test coverage for the MoulAI platform.
# ==============================================

"""Automated tests for test subscription compat.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.repositories.subscription_feature_requests_repo import (
    SubscriptionFeatureRequestRepository,
)
from app.repositories.subscription_features_repo import (
    SubscriptionFeatureRepository,
)

# ==============================================
# TEST SUBSCRIPTION REPOSITORY API EXISTS
# ==============================================


def test_subscription_repository_api_exists():
    assert hasattr(SubscriptionFeatureRepository, "create_subscription_feature")
    assert hasattr(SubscriptionFeatureRepository, "get_by_subscription")
    assert hasattr(SubscriptionFeatureRequestRepository, "get_by_subscription")
    assert hasattr(SubscriptionFeatureRequestRepository, "delete_by_subscription")
