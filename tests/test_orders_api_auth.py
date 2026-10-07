from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.api import auth
from app.api.v1 import orders
from app.api.v1 import order_item as order_items
from app.core.config import settings


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, result):
        self.result = result
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return ScalarResult(self.result)


def owner_auth_settings(monkeypatch):
    monkeypatch.setattr(settings, "OIDC_ISSUER", "https://identity.example.com/")
    monkeypatch.setattr(settings, "OIDC_AUDIENCE", "moulai-api")
    monkeypatch.setattr(
        settings,
        "OIDC_JWKS_URL",
        "https://identity.example.com/.well-known/jwks.json",
    )


@pytest.mark.asyncio
async def test_orders_authentication_fails_closed_without_bearer_token():
    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_owner(credentials=None, session=FakeSession(None))

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_orders_authentication_fails_closed_without_oidc_configuration(monkeypatch):
    monkeypatch.setattr(settings, "OIDC_ISSUER", None)
    monkeypatch.setattr(settings, "OIDC_AUDIENCE", None)
    monkeypatch.setattr(settings, "OIDC_JWKS_URL", None)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_owner(credentials=credentials, session=FakeSession(None))

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_current_owner_requires_verified_oidc_claims_and_maps_subject(
    monkeypatch,
):
    owner_auth_settings(monkeypatch)
    session = FakeSession(result=314)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks = SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(
            key=private_key.public_key(),
        ),
    )
    monkeypatch.setattr(auth, "_get_jwks_client", lambda _: jwks)
    token = jwt.encode(
        {
            "iss": "https://identity.example.com/",
            "aud": "moulai-api",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "sub": "idp|owner-314",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    principal = await auth.get_current_owner(
        credentials=credentials,
        session=session,
    )

    assert principal == auth.OwnerPrincipal(owner_id=314)
    assert "owners.auth_subject" in str(session.statements[0])
    assert "idp|owner-314" in session.statements[0].compile().params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["signature", "issuer", "audience", "expiry"])
async def test_current_owner_rejects_invalid_token(monkeypatch, failure):
    owner_auth_settings(monkeypatch)
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(
        key=signing_key.public_key(),
    ))
    monkeypatch.setattr(auth, "_get_jwks_client", lambda _: jwks)
    claims = {
        "iss": "https://identity.example.com/",
        "aud": "moulai-api",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "sub": "idp|owner-314",
    }
    signing_token_key = signing_key
    if failure == "signature":
        signing_token_key = other_key
    elif failure == "issuer":
        claims["iss"] = "https://attacker.example.com/"
    elif failure == "audience":
        claims["aud"] = "different-api"
    elif failure == "expiry":
        claims["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = jwt.encode(
        claims,
        signing_token_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_owner(
            credentials=credentials,
            session=FakeSession(None),
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_current_owner_rejects_subject_without_owner_mapping(monkeypatch):
    owner_auth_settings(monkeypatch)
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks = SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(
            key=signing_key.public_key(),
        ),
    )
    monkeypatch.setattr(auth, "_get_jwks_client", lambda _: jwks)
    token = jwt.encode(
        {
            "iss": "https://identity.example.com/",
            "aud": "moulai-api",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "sub": "unlinked",
        },
        signing_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_owner(
            credentials=credentials,
            session=FakeSession(None),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_owned_restaurant_query_is_bound_to_owner():
    session = FakeSession(result=18)
    await auth.require_owned_restaurant(
        restaurant_id=18,
        owner=auth.OwnerPrincipal(owner_id=314),
        session=session,
    )

    statement = session.statements[0]
    compiled = statement.compile()
    assert "restaurants.owner_id" in str(compiled)
    assert {18, 314}.issubset(set(compiled.params.values()))


@pytest.mark.asyncio
async def test_other_owners_restaurant_is_not_found():
    session = FakeSession(result=None)

    with pytest.raises(HTTPException) as exc_info:
        await auth.require_owned_restaurant(
            restaurant_id=18,
            owner=auth.OwnerPrincipal(owner_id=314),
            session=session,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_owned_order_query_joins_through_restaurant_owner():
    session = FakeSession(result=91)
    await auth.require_owned_order(
        order_id=91,
        owner=auth.OwnerPrincipal(owner_id=314),
        session=session,
    )

    statement = session.statements[0]
    compiled = statement.compile()
    assert "orders.restaurant_id = restaurants.id" in str(compiled)
    assert "restaurants.owner_id" in str(compiled)
    assert {91, 314}.issubset(set(compiled.params.values()))


@pytest.mark.asyncio
async def test_owned_order_item_query_joins_through_order_and_restaurant():
    session = FakeSession(result=72)
    await auth.require_owned_order_item(
        order_item_id=72,
        owner=auth.OwnerPrincipal(owner_id=314),
        session=session,
    )

    statement = session.statements[0]
    compiled = statement.compile()
    assert "order_items.order_id = orders.id" in str(compiled)
    assert "orders.restaurant_id = restaurants.id" in str(compiled)
    assert "restaurants.owner_id" in str(compiled)
    assert {72, 314}.issubset(set(compiled.params.values()))


def test_every_orders_route_requires_authenticated_owner():
    routes = []
    for router in (orders.router, order_items.router):
        routes.extend(
            route
            for route in router.routes
            if isinstance(route, APIRoute)
        )

    assert routes
    for route in routes:
        assert any(
            dependency.call is auth.get_current_owner
            for dependency in route.dependant.dependencies
        ), route.path


def test_orders_http_endpoint_rejects_requests_without_bearer_token():
    app = FastAPI()
    app.include_router(orders.router)

    response = TestClient(app).get("/orders/", params={"restaurant_id": 18})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
