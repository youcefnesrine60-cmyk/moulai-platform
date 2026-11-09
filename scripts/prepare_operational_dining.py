# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT INTEGRATED DINING DEVELOPMENT DATA
# Prepare a small real catalogue and unprivileged local accounts for the positive client/staff rehearsal.
# ==============================================

"""No SaaS feature price, subscription, paid entitlement, grant or remote customer data is created."""

from __future__ import annotations

# isort: split
# ==============================================
# LOCAL DEVELOPMENT DEPENDENCIES
# Private account passwords stay outside the repository and never appear in command arguments or output.
# ==============================================

import argparse
import asyncio
import json
import secrets
import sys
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from scripts.run_operational_local import (
    IntegrationNetworkGuard,
    resolve_instance,
)

# ==============================================
# DEVELOPMENT PREPARATION CONTRACTS
# Keep identifiers and counts typed without weakening the result to an arbitrary object dictionary.
# ==============================================


class PreparedProduct(TypedDict):
    """An actual locally inserted catalogue row and its explicit development price."""

    id: int
    name: str
    exact_public_price: str


class FeatureReference(TypedDict):
    """A compatibility reference that grants no commercial entitlement or feature price."""

    id: int
    code: str
    source: str
    grants: bool
    feature_prices: bool


class PreparedCatalogue(TypedDict):
    """Nonsecret preparation evidence; passwords remain in the private account store."""

    organization_id: int
    restaurant_id: int
    branch_id: int
    category_id: int
    products: list[PreparedProduct]
    accounts: list[str]
    feature_reference: FeatureReference
    data: str


# ==============================================
# MARKED CATALOGUE PREPARATION
# Scope each insert to the supplied organization/restaurant/branch and refuse conflicting existing fixture names.
# ==============================================


async def prepare(
    *, organization: int, restaurant: int, branch: int
) -> PreparedCatalogue:
    """Prepare explicit development inputs; real permissions must still be granted separately through owner routes."""
    configuration = resolve_instance(supplied=None)
    configuration.process_environment()
    from app.integration.provision import create_account
    from app.integration.web import attest_database

    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with async_sessionmaker(engine)() as session:
            await attest_database(session=session, configuration=configuration)
            await session.rollback()
            async with session.begin():
                selected = await session.scalar(
                    text(
                        "SELECT b.id FROM branches b JOIN restaurants r ON r.id=b.restaurant_id WHERE b.id=:b AND r.id=:r AND r.organization_id=:o AND b.is_active AND r.is_active"
                    ),
                    {"b": branch, "r": restaurant, "o": organization},
                )
                if selected is None:
                    raise RuntimeError("explicit_development_scope_not_found")
                feature = await session.scalar(
                    text("SELECT code FROM features WHERE id=6")
                )
                if feature not in {None, "orders"}:
                    raise RuntimeError("legacy_orders_feature_reference_conflict")
                if feature is None:
                    await session.execute(
                        text(
                            "INSERT INTO features(id,code,name) VALUES(6,'orders','Orders reference — no paid entitlement')"
                        )
                    )
                    await session.execute(
                        text(
                            "SELECT setval(pg_get_serial_sequence('features','id'),greatest((SELECT max(id) FROM features),6))"
                        )
                    )
                existing = await session.scalar(
                    text(
                        "SELECT id FROM categories WHERE restaurant_id=:r AND name='LOCAL DEV — Menu'"
                    ),
                    {"r": restaurant},
                )
                if existing is not None:
                    raise RuntimeError("development_catalogue_already_prepared")
                category = await session.scalar(
                    text(
                        "INSERT INTO categories(restaurant_id,name) VALUES(:r,'LOCAL DEV — Menu') RETURNING id"
                    ),
                    {"r": restaurant},
                )
                products: list[PreparedProduct] = []
                for name, price in [
                    ("LOCAL DEV — Plat", 600),
                    ("LOCAL DEV — Boisson", 150),
                ]:
                    identifier = await session.scalar(
                        text(
                            "INSERT INTO products(restaurant_id,category_id,name,description,price,is_available) VALUES(:r,:c,:name,'Synthetic development item, not a commercial SaaS price',:price,true) RETURNING id"
                        ),
                        {"r": restaurant, "c": category, "name": name, "price": price},
                    )
                    products.append(
                        {
                            "id": identifier,
                            "name": name,
                            "exact_public_price": str(price),
                        }
                    )
        account_path = configuration.directory / "private/acceptance-accounts.json"
        accounts = json.loads(account_path.read_text(encoding="utf-8"))
        prepared = []
        for username in ["d1-service", "d1-kitchen", "d1-collector", "d1-cleaner"]:
            if username not in accounts:
                password = secrets.token_urlsafe(24)
                record = await create_account(
                    configuration=configuration, username=username, password=password
                )
                accounts[username] = {**record, "password": password}
                account_path.write_text(
                    json.dumps(accounts, indent=2), encoding="utf-8"
                )
            prepared.append(username)
        result: PreparedCatalogue = {
            "organization_id": organization,
            "restaurant_id": restaurant,
            "branch_id": branch,
            "category_id": category,
            "products": products,
            "accounts": prepared,
            "feature_reference": {
                "id": 6,
                "code": "orders",
                "source": "existing ORDERS_FEATURE_ID constant; usage counter FK only",
                "grants": False,
                "feature_prices": False,
            },
            "data": "explicit local development only",
        }
        (ROOT / "artifacts/operational-milestone-20261108/catalogue.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result
    finally:
        await engine.dispose()


# ==============================================
# EXPLICIT OPT-IN COMMAND
# A fresh attested local target is mandatory; this is technical test setup, not autonomous enrollment.
# ==============================================


def main() -> int:
    """Refuse missing acknowledgement or invalid IDs before configuring any development resource."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-development-data", action="store_true", required=True
    )
    parser.add_argument("--organization", type=int, required=True)
    parser.add_argument("--restaurant", type=int, required=True)
    parser.add_argument("--branch", type=int, required=True)
    options = parser.parse_args()
    if min(options.organization, options.restaurant, options.branch) < 1:
        raise ValueError("positive_scope_required")
    sys.addaudithook(IntegrationNetworkGuard())
    result = asyncio.run(
        prepare(
            organization=options.organization,
            restaurant=options.restaurant,
            branch=options.branch,
        )
    )
    print(
        json.dumps(
            {
                "prepared": True,
                "products": len(result["products"]),
                "accounts": len(result["accounts"]),
                "grants_created": False,
                "saas_prices_created": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        ValueError,
        RuntimeError,
        SQLAlchemyError,
        httpx.HTTPError,
    ) as error:
        print(
            json.dumps({"status": "STOPPED", "type": type(error).__name__}),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
