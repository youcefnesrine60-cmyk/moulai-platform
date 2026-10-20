# Functional tenant reads

Date: 2026-10-19. Delivery: **transaction-bound tenant reads and opt-in FastAPI
dependencies**, tested locally without altering existing application routes.

## Available behavior

[TenantAccessService](../app/services/business/tenant_access.py) composes the
existing `IdentityService`, `TenantContextResolver`, `TenantAuthorizationService`,
`restaurant_scope` and owned transaction boundary. PostgreSQL remains the only
membership/permission authority. No realm-role mapping or permission catalogue
fallback was added.

- `own_memberships(...)` returns only the authenticated local identity's minimal
  association metadata, with an ID cursor and a maximum of 100 entries. Inactive
  history may appear; it cannot authorize entry into a company. No company
  business records, external identity keys or resource grants are returned.
  Discovery also requires the role's explicit stored
  `tenant.membership.self.read` permission; there is no catalogue fallback.
- `authorized(...)` requires an explicit positive company ID and an explicit
  tenant permission. The existing resolver verifies and locks the active local
  identity, selected active/enforced company, accepted membership, current policy
  and exact grants. It never selects a first company or unions memberships.
- The yielded `TenantReadUnit` provides `membership()`, `restaurants(...)` and
  `restaurant(...)`. Every call revalidates current database authority and its
  own permission. Empty explicit grants return zero restaurants and deny direct
  access; minimal own-membership metadata remains available.
- Outputs are frozen/slotted scalar records. The read unit closes with its
  transaction and cannot be reused afterward. A session cannot change companies
  or mix the legacy owner guard with tenant authorization.

Example for an internal caller that already holds a verifier-issued principal:

```python
service = TenantAccessService(session=session)
memberships = await service.own_memberships(principal=principal, limit=50)

async with service.authorized(
    principal=principal,
    organization_id=selected_organization_id,
    permission="tenant.restaurants.read",
) as unit:
    restaurants = await unit.restaurants(limit=50)
```

Use a dedicated clean session for a request/selected company. Return only the
detached outputs; do not store the context, session or facade for later work.
The read transaction must remain bounded and must not span provider/network IO.

## Opt-in HTTP integration

[Tenant dependencies](../app/api/tenant_dependencies.py) reuse the existing
strict HTTPS RS256/JWKS verifier. The diagnostic principal dependency is not
used: it is deliberately gated by the disabled K8 flags and permits a different
local diagnostic policy. The new business dependency cannot relax issuer/JWKS
validation through those flags.

Future reviewed routes can use:

```python
access = tenant_read_access(permission="tenant.restaurants.read")

@router.get("/organizations/{organization_id}/restaurants")
async def restaurants(
    unit: Annotated[TenantReadUnit, Depends(access, scope="function")],
) -> tuple[RestaurantSummary, ...]:
    return await unit.restaurants()
```

This is an integration example, not a registered route. No router imports this
dependency in the running application. The future handler must validate its
other path/query parameters and return outputs before streaming or external IO.

The dependency returns existing authentication 401/503 responses, generic 404
for unknown memberships/resources, 403 for unavailable identity/authority or
permission, and 409 for incompatible session/transaction use. No internal
identity, foreign resource details, token or provider exception enters responses.
Platform permissions and `tenant.orders.fulfill` are rejected when constructing
the tenant dependency. No identity linking, tenant enrollment or policy mutation
is provided by this read delivery.

## Targeted validation

```powershell
.venv\Scripts\python.exe scripts/run_tenant_access_tests.py
```

Observed: **41 tests passed**, zero warnings or network attempts, no shared
database conftest loaded. Tests execute real SQL in disposable memory SQLite and
real RS256 token verification with a simulated JWKS. Temporary HTTP routes exist
only inside the disposable test app. Assertions cover 200/401/403/404/409/422,
same-owner A/B isolation, exact/empty grants, missing issuer-qualified identity,
no automatic `owner-test` association, stored suspension/policy changes, bounded
pagination, stale revisions, transaction cleanup and rejected owner-scope mixing.

The suite does not connect to Neon or Keycloak, run Alembic, repeat the accepted
G2 suite or measure PostgreSQL locking again. SQLite results add functional SQL
and HTTP integration evidence; they do not replace G2's PostgreSQL observations.
No new claim about whole-application coverage is made.

Local ignored results, targeted coverage and
[complete copyable Python sources](../artifacts/tenant-functional/complete-python-sources.md)
are in [artifacts/tenant-functional](../artifacts/tenant-functional).

## Exact delivery inventory

Added:

- `app/api/tenant_dependencies.py`.
- `app/schemas/tenant_access.py`.
- `app/services/business/tenant_access.py`.
- `tests/test_tenant_access.py` and `tests/test_tenant_access_http.py`.
- `scripts/run_tenant_access_tests.py`.
- This usage document.

Modified:

- `app/repositories/tenant_repo.py`: bounded personal-membership and explicitly
  company-qualified restaurant projections using the existing base-select style.
- `docs/keycloak-k9-g2-postgres-validation.md`: user acceptance and temporary
  resource custody, retaining the original comparator incident and correction.
- `docs/README.md`: index this functional delivery.

The G2 foundation services, TenantContext issuance, JWT verifier, existing
routes/models, migration contracts and `.env` remain unchanged. OIDC diagnostic
flags remain false. No production/development/W/B/V data was written, no resource
was deleted or extended, and no deployment or Git push occurred.
