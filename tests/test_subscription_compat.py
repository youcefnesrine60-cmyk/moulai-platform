from app.repositories.subscription_feature_requests_repo import (
    SubscriptionFeatureRequestRepository,
)
from app.repositories.subscription_features_repo import (
    SubscriptionFeatureRepository,
)


def test_subscription_repository_api_exists():
    assert hasattr(SubscriptionFeatureRepository, "create_subscription_feature")
    assert hasattr(SubscriptionFeatureRepository, "get_by_subscription")
    assert hasattr(SubscriptionFeatureRequestRepository, "get_by_subscription")
    assert hasattr(SubscriptionFeatureRequestRepository, "delete_by_subscription")
