# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Guard canonical registration signatures and product option group boundaries."""

from datetime import (
    UTC,
    datetime,
)
from types import SimpleNamespace
from typing import Any
from unittest.mock import (
    AsyncMock,
    MagicMock,
    call,
    create_autospec,
)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.product import Product
from app.repositories.option_groups_repo import OptionGroupsRepository
from app.repositories.product_option_repo import ProductOptionRepository
from app.repositories.products_repo import ProductRepository
from app.repositories.registration_request_repo import RegistrationRequestRepository
from app.schemas.option_group import (
    OptionGroupCreate,
    OptionGroupResponse,
)
from app.schemas.owner import OwnerCreate
from app.schemas.registration_request import (
    RegistrationRequestResponse,
    RegistrationRequestStatusUpdate,
    RegistrationRequestUpdate,
)
from app.services.business.option_groups_service import OptionGroupsService
from app.services.business.registration_request_service import RegistrationRequestService  # fmt: skip
from tests.test_owner_statistics_contracts import owner_record

# ==============================================
# VALID BUSINESS RECORDS
# ==============================================


def registration_record() -> RegistrationRequestResponse:
    """Return a pending request with the same Telegram identity as its owner."""
    return RegistrationRequestResponse(
        id=41,
        chat_id=425,
        full_name="Owner Example",
        owner_phone="0555123456",
        email=None,
        restaurant_name="Restaurant Example",
        restaurant_type="restaurant",
        restaurant_phone="0555123456",
        wilaya="Alger",
        lat=None,
        lng=None,
        status="pending",
        owner_id=None,
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )


def registration_service() -> RegistrationRequestService:
    """Create a real service with strict repository method specifications."""
    service = RegistrationRequestService(session=MagicMock(spec=AsyncSession))
    service.repo = create_autospec(RegistrationRequestRepository, instance=True)
    service.repo.get_by_id.return_value = registration_record()
    service.repo.update.return_value = registration_record()
    service.repo.approve.return_value = registration_record().model_copy(
        update={"status": "approved", "owner_id": 17},
    )
    service.owner_service = MagicMock()
    service.owner_service.get_owner_by_id = AsyncMock(return_value=owner_record())
    service.owner_service.get_owner_by_chat_id = AsyncMock(return_value=None)
    service.owner_service.create_owner = AsyncMock(return_value=owner_record())
    service.owner_service.approve_owner = AsyncMock()
    service.restaurant_repo = MagicMock()
    service.restaurant_repo.create = AsyncMock(return_value=SimpleNamespace(id=99))
    service.subscription_service = MagicMock()
    service.subscription_service.create_trial_subscription = AsyncMock(
        return_value=SimpleNamespace(id=101),
    )
    return service


def option_group_record() -> OptionGroupResponse:
    """Build a persisted option group DTO for product 17."""
    return OptionGroupResponse(
        id=8,
        product_id=17,
        name="Size",
        required=False,
        multiple_choice=False,
        sort_order=0,
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )


# ==============================================
# REGISTRATION CANONICAL SIGNATURES
# ==============================================


@pytest.mark.asyncio
async def test_registration_lookup_uses_the_base_primary_key_contract() -> None:
    """A removed request_id repository wrapper is unnecessary for lookups."""
    service = registration_service()

    result = await service.get_by_id(request_id=41)

    assert result.id == 41
    service.repo.get_by_id.assert_awaited_once_with(id=41)


@pytest.mark.asyncio
async def test_registration_update_uses_the_base_primary_key_contract() -> None:
    """Nullable optional profile values do not reintroduce a wrapper dependency."""
    service = registration_service()

    await service.update(
        request_id=41,
        update_data=RegistrationRequestUpdate(full_name="Changed Owner", email=None),
    )

    service.repo.update.assert_awaited_once_with(
        id=41,
        data={"full_name": "Changed Owner", "email": None},
    )


@pytest.mark.asyncio
async def test_registration_status_lookup_uses_the_base_primary_key_contract() -> None:
    """Administrative status changes resolve the canonical primary key first."""
    service = registration_service()

    await service.update_status(
        request_id=41,
        status_data=RegistrationRequestStatusUpdate(status="approved"),
    )

    service.repo.get_by_id.assert_awaited_once_with(id=41)
    service.repo.approve.assert_awaited_once_with(request_id=41, owner_id=None)


@pytest.mark.asyncio
async def test_registration_delete_uses_the_base_primary_key_contract() -> None:
    """Deleting an unapproved request uses BaseRepository.delete's id argument."""
    service = registration_service()
    service.repo.delete.return_value = True

    await service.delete(request_id=41)

    service.repo.delete.assert_awaited_once_with(id=41)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "arguments", "expected_data"),
    [
        ("update_status", {"status": "pending"}, {"status": "pending"}),
        ("approve", {"owner_id": 17}, {"status": "approved", "owner_id": 17}),
        ("reject", {}, {"status": "rejected"}),
    ],
)
async def test_registration_repository_mutations_keep_base_update_signature(
    method_name: str,
    arguments: dict[str, Any],
    expected_data: dict[str, Any],
) -> None:
    """Specialized decisions use the same BaseRepository.update contract."""
    repository = RegistrationRequestRepository(session=MagicMock(spec=AsyncSession))
    repository.update = create_autospec(repository.update)

    await getattr(repository, method_name)(request_id=41, **arguments)

    repository.update.assert_awaited_once_with(id=41, data=expected_data)


# ==============================================
# REGISTRATION OWNER IDENTITY
# ==============================================


@pytest.mark.asyncio
async def test_registration_approval_supplies_an_owner_create_schema() -> None:
    """Approval passes a validated schema rather than an incompatible dictionary."""
    service = registration_service()

    result = await service.approve(request_id=41)

    payload = service.owner_service.create_owner.await_args.kwargs["owner_data"]
    assert isinstance(payload, OwnerCreate)
    assert payload.chat_id == 425
    assert payload.email is None
    assert result.owner_id == 17
    service.repo.get_by_id.assert_awaited_once_with(id=41)
    service.restaurant_repo.create.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("linked_owner", [False, True], ids=["explicit", "persisted"])
async def test_registration_cannot_assign_another_telegram_users_owner(
    linked_owner: bool,
) -> None:
    """A foreign owner is rejected before creating restaurants or subscriptions."""
    service = registration_service()
    service.owner_service.get_owner_by_id.return_value = owner_record().model_copy(
        update={"id": 18, "chat_id": 999},
    )
    if linked_owner:
        service.repo.get_by_id.return_value = registration_record().model_copy(
            update={"owner_id": 18},
        )

    with pytest.raises(ValidationError, match="does not match"):
        await service.approve(request_id=41, owner_id=None if linked_owner else 18)

    service.owner_service.get_owner_by_id.assert_awaited_once_with(owner_id=18)
    service.owner_service.create_owner.assert_not_awaited()
    service.restaurant_repo.create.assert_not_awaited()
    service.subscription_service.create_trial_subscription.assert_not_awaited()
    service.repo.approve.assert_not_awaited()


@pytest.mark.asyncio
async def test_registration_reuses_the_owner_bound_to_the_request_chat() -> None:
    """Another request from an existing chat does not create a duplicate owner."""
    service = registration_service()
    service.owner_service.get_owner_by_chat_id.return_value = owner_record()

    await service.approve(request_id=41)

    service.owner_service.get_owner_by_chat_id.assert_awaited_once_with(chat_id=425)
    service.owner_service.create_owner.assert_not_awaited()
    assert service.restaurant_repo.create.await_args.kwargs["data"]["owner_id"] == 17


# ==============================================
# OPTION GROUP PRODUCT BOUNDARY
# ==============================================


@pytest.mark.asyncio
async def test_option_group_create_looks_up_the_product_by_primary_key() -> None:
    """A product identifier is never mislabelled as a restaurant identifier."""
    service = OptionGroupsService(session=AsyncSession(), owner_id=7)
    service.product_repo = create_autospec(ProductRepository, instance=True)
    service.product_repo.get_by_id.return_value = SimpleNamespace(
        id=17, restaurant_id=5
    )
    service.repo = create_autospec(OptionGroupsRepository, instance=True)
    service.repo.count_by_product.return_value = 0
    service.repo.get_by_name.return_value = None
    service.repo.create.return_value = option_group_record()

    result = await service.create_group(
        group_data=OptionGroupCreate(product_id=17, name="Size")
    )

    assert result.product_id == 17
    service.product_repo.get_by_id.assert_awaited_once_with(id=17)


@pytest.mark.asyncio
async def test_option_groups_delete_by_product_uses_primary_key_lookup() -> None:
    """Product deletion scope is resolved with the canonical product ID."""
    service = OptionGroupsService(session=AsyncSession(), owner_id=7)
    service.product_repo = create_autospec(ProductRepository, instance=True)
    service.product_repo.get_by_id.return_value = SimpleNamespace(
        id=17, restaurant_id=5
    )
    service.repo = create_autospec(OptionGroupsRepository, instance=True)
    service.repo.delete_by_product.return_value = 2

    assert await service.delete_by_product(product_id=17) == 2
    service.product_repo.get_by_id.assert_awaited_once_with(id=17)
    service.repo.delete_by_product.assert_awaited_once_with(product_id=17)


@pytest.mark.asyncio
async def test_reorder_validates_all_product_membership_before_any_write() -> None:
    """A foreign product group late in the batch cannot leave partial changes."""
    service = OptionGroupsService(session=AsyncSession(), owner_id=7)
    service.repo = create_autospec(OptionGroupsRepository, instance=True)
    service.repo.get_by_id.side_effect = [
        SimpleNamespace(id=8, product_id=17),
        SimpleNamespace(id=9, product_id=18),
    ]

    with pytest.raises(ValidationError):
        await service.reorder_groups(product_id=17, group_order=[8, 9])

    service.repo.get_by_id.assert_has_awaits([call(id=8), call(id=9)])
    service.repo.update_sort_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_group_deletion_counts_hidden_options_through_canonical_repository() -> (
    None
):
    """An unavailable option still prevents destructive group deletion."""
    service = OptionGroupsService(session=AsyncSession(), owner_id=7)
    service.repo = create_autospec(OptionGroupsRepository, instance=True)
    service.repo.get_by_id.return_value = option_group_record()
    service.option_repo = create_autospec(ProductOptionRepository, instance=True)
    service.option_repo.count_by_group.return_value = 1

    with pytest.raises(ValidationError):
        await service.delete_group(group_id=8)

    service.option_repo.count_by_group.assert_awaited_once_with(
        group_id=8,
        only_available=False,
    )
    service.repo.delete.assert_not_awaited()


# ==============================================
# PRODUCT DOMAIN UPDATE SIGNATURES
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "parameters", "expected_data"),
    [
        ("update_availability", {"is_available": False}, {"is_available": False}),
        ("update_price", {"price": 21.5}, {"price": 21.5}),
        ("update_sort_order", {"sort_order": 3}, {"sort_order": 3}),
    ],
    ids=["availability", "price", "sort-order"],
)
async def test_product_domain_update_helpers_keep_canonical_base_signature(
    method_name: str,
    parameters: dict[str, Any],
    expected_data: dict[str, Any],
) -> None:
    """Domain helpers retain product_id inputs while calling the strict base method."""
    repository = ProductRepository(session=MagicMock(spec=AsyncSession))
    expected = Product(id=17, restaurant_id=4, category_id=2, name="Product Example")
    repository.update = create_autospec(repository.update, return_value=expected)

    result = await getattr(repository, method_name)(product_id=17, **parameters)

    assert result is expected
    repository.update.assert_awaited_once_with(id=17, data=expected_data)
