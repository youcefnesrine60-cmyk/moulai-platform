# A2 + A5 — Catalog security and isolation validation

Date: **2026-10-22**. Branch: `feature/keycloak-k10-complete`.
Current conclusion: **PASS for the focused, corrected and tested A2 + A5 scope**.
The initial audit concluded FAIL: four batch-atomicity cases and two legitimate
summaries failed. Those findings and their original results are retained below.
The user subsequently authorized their correction; final implementation and
verification are recorded in the authorized-correction section.

This targeted control follows the accepted frontend delivery. It does not reopen
K9/K10, activate their routes or introduce a roadmap phase.

## Scope and existing protections

The [2026-10-16 remediation](catalog-options-isolation-finding.md) was reviewed
first. Its authentication and owner-filtering fixes are present; the old public
catalog finding is **not** treated as an open vulnerability.

| Boundary                            | Inspected implementation and observed evidence                                                                                                                                                                                                                                                           |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Trusted identity                    | `get_current_owner` in [auth.py](../app/api/auth.py#L313) obtains a verified JWT subject and resolves `Owner.auth_subject`. RS256, issuer, audience, expiry and subject checks use the existing verifier. Existing simulated-key tests cover valid mapping and invalid signature/issuer/audience/expiry. |
| Every catalog operation             | All four routers declare `Depends(get_current_owner)` and their service factories use `get_owner_tenant_db`. The added matrix derives **46 operations from the actual routers** and obtains 401 for both absent and malformed Bearer credentials: **92 HTTP cases**, without database execution.         |
| Client-supplied owner               | Four real-SQL list/detail tests confirm that `owner_id=8` cannot replace verified fixture Owner 7. A forged owner header also cannot bypass missing/invalid authentication.                                                                                                                              |
| SQL session                         | [tenant_scope.py](../app/core/security/tenant_scope.py) binds one session permanently to one positive owner, scopes ORM entities/scalars/counts/aliases/relationship loads and bulk mutations, and rejects raw/Core escape paths. Its listeners are session-local.                                       |
| Ownership chain                     | `OptionGroup → Product → Restaurant → Owner`; `ProductOption → OptionGroup → Product → Restaurant → Owner`. Foreign detail/update/delete/creation-parent paths return 404 in the relational tests and emit no mutation.                                                                                  |
| Flush and identity map              | The guard validates the complete pending batch, immutable parents and same-restaurant product/category relations before SQL. Tests also cover cached foreign identities, dirty first binding and attempted owner rebinding.                                                                              |
| Common owner, different restaurants | Five added real-SQL cases reject product/category reassignment or mixed reorder parents across two restaurants of the **same owner**, with no INSERT/UPDATE/DELETE. Product/category mismatch returns 404; valid owned resources mixed under the wrong parent return 422.                                |
| Legitimate access                   | Existing real-SQL tests preserve authorized option/group creation, updates and owner-filtered list/search results. Their passing results do not certify every response contract: the two summary failures below are explicit counterexamples.                                                            |

No cross-owner disclosure or mutation was demonstrated in these scenarios.
This is evidence for the tested application boundaries, not a database RLS
certification or a proof against every possible concurrent operation.

## Exact implementation inventory

| Layer                                          | Files inspected                                                                                                                                                                                                                                                                                           |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Registration and dependencies                  | [main.py](../app/main.py), [auth.py](../app/api/auth.py), [database.py](../app/core/database.py), [tenant_scope.py](../app/core/security/tenant_scope.py).                                                                                                                                                |
| Routers                                        | [option_group.py](../app/api/v1/option_group.py), [product_option.py](../app/api/v1/product_option.py), [products.py](../app/api/v1/products.py), [categories.py](../app/api/v1/categories.py).                                                                                                           |
| Services                                       | [option_groups_service.py](../app/services/business/option_groups_service.py), [product_option_service.py](../app/services/business/product_option_service.py), [product_service.py](../app/services/business/product_service.py), [category_service.py](../app/services/business/category_service.py).   |
| Repositories                                   | [base.py](../app/repositories/base.py), [option_groups_repo.py](../app/repositories/option_groups_repo.py), [product_option_repo.py](../app/repositories/product_option_repo.py), [products_repo.py](../app/repositories/products_repo.py), [categories_repo.py](../app/repositories/categories_repo.py). |
| Relationship models                            | [owner.py](../app/models/owner.py), [restaurant.py](../app/models/restaurant.py), [category.py](../app/models/category.py), [product.py](../app/models/product.py), [option_group.py](../app/models/option_group.py), [product_option.py](../app/models/product_option.py).                               |
| Option request/response contracts              | [option_group.py](../app/schemas/option_group.py), [product_option.py](../app/schemas/product_option.py). Product/category request paths were followed through their actual router/service calls.                                                                                                         |
| Transaction conventions, for the proposal only | [orders/transaction.py](../app/services/business/orders/transaction.py), [payment_transaction.py](../app/services/business/payment_transaction.py). Neither was modified or exercised as a catalog boundary.                                                                                              |
| Test infrastructure                            | [offline runner](../scripts/run_offline_api_tests.py), [HTTP support](../tests/api/unit/business/_support.py), [local PostgreSQL runner](../scripts/run_local_postgres_tests.py), [local admission](../test_support/local_postgres.py). PostgreSQL tooling was inspected only, not launched.              |

The exact HTTP inventory appears at the end. These routes are registered under
`/api/v1` by the existing application. Tests mount their real routers in private
FastAPI applications, without startup, the production application or K10 routes.

## Initial reproduced findings — before correction

### A2-A5-01 — Medium: a rejected bulk creation persists a partial batch

Affected path: `POST /api/v1/product-options/bulk`.

The disposable fixture supplies Owner 7, group 41 and an existing option named
`Cheese`. Submit this authorized request through the real router:

```json
{
  "group_id": 41,
  "options": [
    { "name": "Audit first item", "extra_price": 10 },
    { "name": "Cheese", "extra_price": 50 }
  ]
}
```

Observed: **409 Conflict**, but `Audit first item` remains in group 41 after an
explicit session rollback and a fresh connection read. The second name conflict
is natural; this reproduction injects no storage failure.

Cause: [create_product_options_bulk](../app/api/v1/product_option.py#L504) loops
over [create_option](../app/services/business/product_option_service.py#L422).
Each call reaches [BaseRepository.create](../app/repositories/base.py#L161),
which commits unless `defer_repository_commit` is set. No outer catalog batch
transaction sets it here. A later rollback cannot undo the first commit.

Impact: an error response can leave incomplete catalog changes, leading to
inconsistent retries and unexpected options. The reproduced writes remain in
the authenticated owner's group; no cross-owner escalation or financial-table
write is demonstrated.

Acceptance reproduction:
`test_bulk_conflict_must_not_leave_a_committed_first_option` in the added
[test file](../tests/api/unit/business/test_catalog_a2_a5.py).

### A2-A5-02 — Medium: late reorder failure preserves an earlier update

Affected operations:

- `POST /api/v1/categories/reorder` → `CategoryService.reorder_categories`.
- `POST /api/v1/option-groups/reorder` → `OptionGroupsService.reorder_groups`.
- `POST /api/v1/product-options/reorder` → `ProductOptionService.reorder_options`.

Each test adds a second valid resource under the same authorized parent with
`sort_order=9`, then orders it before the original resource. A local SQLAlchemy
event raises a synthetic error before the second UPDATE. This is deterministic
fault injection, **not an observed PostgreSQL outage or race**.

All three routes return **500**. After rollback, an independent read finds the
first resource at **0 instead of its original 9**. Validation of every ID occurs
before updates, so foreign/mixed-parent refusals remain protected; the defect
concerns failure after valid updates have begun.

Cause: each service loop delegates to repository updates that individually
commit through [BaseRepository.update](../app/repositories/base.py#L463).
There is no enclosing batch transaction. The request database dependency rolls
back exceptions but cannot reverse a completed earlier commit.

Impact: partial display-order changes despite an error response. Three acceptance
cases in `test_second_update_failure_must_rollback_complete_reorder` fail.
Late-failure atomicity of the separately inspected parent-delete loops has not
been certified by this campaign and must not be inferred from foreign-ID denial.

### A2-A5-03 — Low, functional: legitimate summaries return 500

Two real-SQL requests for the authenticated owner's existing resources return
500 instead of the declared 200 response:

| Route                                          | Demonstrated contract mismatch                                                                                                                                                          |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/v1/option-groups/product/31/summary` | `get_option_group_summary` constructs `OptionGroupSummary` without required `product_id` and `total_options`.                                                                           |
| `GET /api/v1/product-options/group/41/summary` | `get_option_summary` omits required `group_id`, `total_extra_price`, `avg_extra_price`, `min_extra_price` and `max_extra_price`; it supplies the undeclared name `average_extra_price`. |

The actual Pydantic validation failures are retained in local test evidence.
HTTP responses contain generic error messages; no foreign record or validation
trace is returned to the caller in these reproductions. This is an availability
and response-contract defect, **not evidence of an authentication bypass**.
The two `test_owned_option_summary_must_return_its_declared_contract` cases fail.
Existing HTTP-contract mocks returned already-valid summaries and therefore did
not exercise these real service constructors.

## Reviewed correction proposal — historical record

1. Reuse the existing `defer_repository_commit` convention for one transaction
   covering each catalog batch. Repositories should flush within that boundary,
   with one final commit and complete rollback on failure. Preserve explicit
   caller-owned transactions and account for authentication/read AUTOBEGIN;
   adding a bare `session.begin()` after a read is insufficient.
2. Move the bulk-creation orchestration into `ProductOptionService`; retain the
   existing endpoint and response contract. Apply the same transaction boundary
   to the three reorder methods, preserving their complete prevalidation.
3. Populate the existing summary schemas with the required scoped counts and
   amounts. Keep their declared field names, owner boundary and HTTP policy.
4. Before acceptance, validate legitimate batches, late business/storage errors,
   explicit outer-transaction ownership and rollback. Include deletion-loop
   coverage where the same per-item commit pattern is used.

Expected application scope: `app/api/v1/product_option.py`, the existing
`product_option_service.py`, `option_groups_service.py` and `category_service.py`,
and a narrowly scoped transaction adapter only if needed to reuse the established
convention safely. **Do not change global BaseRepository commit defaults**, JWT
verification, owner binding, platform RBAC, payment/order transaction code or the
database schema for this correction.

Risks to check: returning rows after commit/expiration, transaction ownership
when services are composed, duplicate/limit checks, rollback of cascaded deletes,
and unchanged successful HTTP contracts. These are correction acceptance checks,
not claims that the proposed implementation has already passed.

## Initial audit tests — before correction

| Final selection                 | Executed | Passed  | Failed | Skipped |
| ------------------------------- | -------- | ------- | ------ | ------- |
| Six existing test files         | 303      | 303     | 0      | 0       |
| Added targeted acceptance file  | 107      | 101     | 6      | 0       |
| Total distinct final test cases | **410**  | **404** | **6**  | **0**   |

The first selection reused:

- `tests/api/unit/business/test_catalog_authorization.py`.
- `tests/api/unit/business/test_catalog_membership.py`.
- `tests/api/unit/business/test_catalog_sqlite_authorization.py`.
- `tests/api/unit/business/test_catalog_http.py`.
- `tests/test_owner_tenant_scope.py`.
- `tests/test_orders_api_auth.py` — the existing shared legacy owner/JWT contracts;
  no K8/K9/K10 campaign was restarted.

The added [test_catalog_a2_a5.py](../tests/api/unit/business/test_catalog_a2_a5.py)
contains 92 route-authentication cases, four forged-owner cases, five same-owner
restaurant-consistency cases and the six failing acceptance reproductions above.
It reuses the original relational fixture, routers, services and repositories.
The six failures were left visible at that checkpoint, without skip, xfail,
mocked commits or weakened assertions. The same assertions now pass after the
authorized application correction; the initial failing evidence is retained.

Both final selections produced zero warnings, zero denied network attempts and
`shared_conftest_loaded=false`. The existing runner enforced its Python socket
guard and disabled shared integration fixtures and plugin autoload. Black and
Ruff pass for the new Python file. The threshold of zero below is only for this
focused run's coverage denominator; no global coverage result is claimed.

Commands executed during the initial audit, retained as a historical record:

```powershell
$env:DEBUG = 'false'
$env:DB_ECHO = 'false'
$env:OIDC_DIAGNOSTICS_ENABLED = 'false'
$env:OIDC_ALLOW_LOCAL_HTTP = 'false'

.venv\Scripts\python.exe scripts/run_offline_api_tests.py --name a2-a5-existing --minimum 0 tests/api/unit/business/test_catalog_authorization.py tests/api/unit/business/test_catalog_membership.py tests/api/unit/business/test_catalog_sqlite_authorization.py tests/api/unit/business/test_catalog_http.py tests/test_owner_tenant_scope.py tests/test_orders_api_auth.py
.venv\Scripts\python.exe scripts/run_offline_api_tests.py --name a2-a5-final --minimum 0 tests/api/unit/business/test_catalog_a2_a5.py
```

The second command exited **1** on the original audited implementation, with six
failures. On the corrected implementation it is expected to pass; use a new
report name if reproducing it so the historical evidence is retained. An
intermediate 26-case investigation preceded the initial expanded matrix and is
not added to the distinct-case totals.

Ignored local evidence: `artifacts/api-test-review/a2-a5-existing-results.json`,
`a2-a5-final-results.json` and their coverage reports; console logs and the
sanitized inventory/scope record are under `artifacts/catalog-a2-a5/`. These
artifacts are not publication inputs. The source test and this report provide
reproduction without forcing ignored or potentially sensitive artifacts into Git.

## Validation limits and initial stop point

- SQLite tests run actual SQLAlchemy guards and commits in private in-memory
  databases. They demonstrate these application-level failures, but not asyncpg,
  PostgreSQL FK enforcement, locks, isolation levels or live concurrency.
- No PostgreSQL test or migration was executed during the initial audit. The
  authorized correction was subsequently verified on disposable local PostgreSQL
  only, as recorded below. No Neon SQL or remote migration was executed.
- JWT tests use simulated signing keys; HTTP relational tests explicitly supply
  a trusted fixture principal. No real Keycloak user or identity binding changed.
- Historical catalog authorization remains Owner/Restaurant based. It does not
  yet consume K9 Organization memberships or K10 tenant permissions. Issuer is
  verified by the JWT configuration; the legacy Owner mapping uses its stored
  subject. Multi-issuer identity linking, explicit company selection and
  Owner/Manager/Staff integration remain **Business Integration** work, without
  duplicate authorization logic or automatic grants from Keycloak roles.
- The initial audit changed no backend application, migration, existing test,
  frontend asset, configuration or external resource. Its two source-hash
  inventories match. The later correction's exact source scope is listed below.
  Frontend source hashes still match the accepted logo-delivery manifest.

The initial audit stopped before application correction for review. The user's
subsequent request to correct these errors authorized the targeted work below.
K9/K10 remain closed in their accepted scope. The roadmap remains
**Frontend → Business Integration → K11 Production Security → Pilot**.

## Authorized correction and final verification — 2026-10-22

### Exact implementation changes

| File                                                                                            | Change                                                                                                                                                                                                                              |
| ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [catalog_transaction.py](../app/services/business/catalog_transaction.py) — added               | Scoped context manager using the existing `defer_repository_commit` convention; owns fresh/read-AUTOBEGIN transactions, preserves explicit/managed callers with savepoints, restores the flag and rejects unrelated unflushed work. |
| [product_option_service.py](../app/services/business/product_option_service.py)                 | Atomic bulk creation reuses single-option validation. Reordering and parent-wide option deletion share the batch context. Summaries populate the existing declared fields from SQL statistics.                                      |
| [option_groups_service.py](../app/services/business/option_groups_service.py)                   | Atomic reordering and parent-wide group deletion; summary now includes product ID and the scoped option count.                                                                                                                      |
| [category_service.py](../app/services/business/category_service.py)                             | Transaction boundary around the already-prevalidated reorder updates; no ownership-policy change.                                                                                                                                   |
| [product_option_repo.py](../app/repositories/product_option_repo.py)                            | Typed SQL statistics and product-wide option count using mapped BASE SELECTs. Aggregation has no 1,000-row pagination truncation. Empty aggregates return zeroes.                                                                   |
| [product_option.py](../app/api/v1/product_option.py)                                            | Existing `/bulk` endpoint delegates orchestration to the service; URL, payload, HTTP/error policy and response shape are unchanged.                                                                                                 |
| [test_catalog_http.py](../tests/api/unit/business/test_catalog_http.py)                         | Bulk service double now targets the actual batch method; existing public HTTP assertions are retained.                                                                                                                              |
| [test_catalog_postgres_transactions.py](../tests/test_catalog_postgres_transactions.py) — added | Twenty-one real local PostgreSQL cases covering HTTP outcomes, rollback, parent-delete failures/cascades, caller ownership, nested failure, pending-work refusal and complete scoped statistics.                                    |
| [run_local_postgres_tests.py](../scripts/run_local_postgres_tests.py)                           | Adds only `--suite catalog`, pinned to the existing local legacy profile and its identity checks.                                                                                                                                   |
| [run_offline_api_tests.py](../scripts/run_offline_api_tests.py)                                 | Excludes the new PostgreSQL file from offline selection, preserving the network-denied execution boundary.                                                                                                                          |

The six original acceptance assertions are unchanged and pass. Global repository
commit defaults, JWT verification, owner/session binding, platform permissions,
payment/order transaction code, K9/K10 components and all migrations are unchanged.
No new endpoint, business role or dependency was added. New code has the standard
header, typed signatures, function headings and docstrings. Black passes for all
ten correction Python files. Ruff passes for eight files; the two historical
router/category modules introduce no new diagnostics relative to HEAD, while
retaining their unrelated legacy lint findings outside this correction.

### Observed final results

| Final campaign                                                                 | Passed  | Failed | Skipped | Warnings |
| ------------------------------------------------------------------------------ | ------- | ------ | ------- | -------- |
| Targeted catalog, owner/JWT, repository contracts and launcher safety, offline | **505** | 0      | 0       | 0        |
| Native PostgreSQL catalog suite, actual asyncpg                                | **21**  | 0      | 0       | 0        |
| Total distinct final cases                                                     | **526** | **0**  | **0**   | **0**    |

The offline run uses the original runner with shared conftest disabled and its
socket guard active. No denied network attempt was recorded. It covers the
410-case corrected catalog selection plus 95 relevant repository/launcher safety
cases. Intermediate 410- and 95-case successful runs are not counted again.

The PostgreSQL run used **18.3**, exactly `127.0.0.1:55432/moulai_pytest`, the
independent local settings namespace, an attested generated instance marker,
the unprivileged runtime role, legacy revision **`dce91870b4a2`** and **47 public
tables**. The existing local migration history was applied only to that new
disposable cluster. No revision was created or changed. No remote target or
DATABASE_URL/TEST_DATABASE_URL fallback was used.

Observed local run: `2393bf33d58442b8a64c7908b17869b0`. All 21 cases passed,
with `network_denied_categories={}` and `server_stopped=true`. An earlier
sandbox-restricted native startup failed before tests; that separate failed
attempt is retained rather than reported as a test result. The approved retry
outside the sandbox completed successfully.

PostgreSQL cases verify:

- Natural second-item conflict produces 409 and no partial committed option;
  successful batches return 201; foreign parents return 404 unchanged.
- Late second UPDATE failure rolls back the first actual UPDATE for categories,
  groups and options. Late parent-delete failure retains original rows/children.
- Explicit caller and managed AUTOBEGIN transactions do not commit prematurely;
  a failed nested batch preserves earlier caller work. Pending unrelated new,
  dirty or deleted objects are refused before implicit savepoint flushing.
- Fresh and read-AUTOBEGIN operations commit on success and roll back on failure,
  restoring the repository flag. Independent real sessions inspect outcomes.
- Summary values are correct for populated/empty groups, foreign-owner filtering
  and **1,002 options**, beyond the previous 1,000-row read limit.

These tests exercise real PostgreSQL transactions and deterministic injected
failures, not an unexecuted concurrency benchmark or a full production rehearsal.
HTTP uses explicitly trusted synthetic fixture identities; the existing simulated
JWT tests verify cryptographic authentication separately. No real account is linked.

Focused offline reproduction from the repository root, preserving historical
reports under their original names:

```powershell
$catalogTests = @(
    'tests/api/unit/business/test_catalog_authorization.py'
    'tests/api/unit/business/test_catalog_membership.py'
    'tests/api/unit/business/test_catalog_sqlite_authorization.py'
    'tests/api/unit/business/test_catalog_http.py'
    'tests/test_owner_tenant_scope.py'
    'tests/test_orders_api_auth.py'
    'tests/api/unit/business/test_catalog_a2_a5.py'
    'tests/test_remaining_repository_contracts.py'
    'tests/test_repository_transaction_mode.py'
    'tests/test_local_postgres_safety.py'
    'tests/test_offline_api_runner.py'
    'tests/api/unit/business/test_product_option_creation.py'
)
.venv\Scripts\python.exe scripts/run_offline_api_tests.py --name a2-a5-recheck --minimum 0 @catalogTests
```

Focused PostgreSQL reproduction, without repeating the accepted broad campaigns:

```powershell
$env:DEBUG = 'false'
.venv\Scripts\python.exe scripts/run_local_postgres_tests.py --backend native --suite catalog
```

The local environment guide documents this selection. Ordinary offline runs
continue to skip opt-in PostgreSQL cases; the dedicated campaign has zero skips.
The full application suite and the accepted K9/K10 campaigns were not rerun here.

Local ignored final evidence:

- `artifacts/api-test-review/a2-a5-validated-results.json` and coverage outputs.
- `artifacts/postgres-local-tests/2393bf33d58442b8a64c7908b17869b0/validation.json`,
  `postgres-results.xml` and `postgres-tests.log`.
- `artifacts/catalog-a2-a5/correction-validation.json`, complete copyable Python
  sources and source hashes. Historical initial FAIL evidence remains available.

No frontend, `.env`, Neon guard, remote database, Keycloak, Render, Redis,
Telegram, OIDC indicator, Git branch, push/merge or deployment was changed.
**A2 + A5 is PASS for this corrected and tested scope.** Business-route tenant
integration and K11 remain in their existing roadmap positions.

## Complete HTTP inventory

All entries below inherit the existing verified-owner dependency. Prefixes
include the production registration path; no endpoint was invented or activated.

| Method | Path                                                 | Handler                               |
| ------ | ---------------------------------------------------- | ------------------------------------- |
| GET    | `/api/v1/option-groups/`                             | `list_option_groups`                  |
| GET    | `/api/v1/option-groups/{group_id}`                   | `get_option_group`                    |
| GET    | `/api/v1/option-groups/product/{product_id}`         | `get_product_option_groups`           |
| POST   | `/api/v1/option-groups/`                             | `create_option_group`                 |
| PATCH  | `/api/v1/option-groups/{group_id}`                   | `update_option_group`                 |
| PATCH  | `/api/v1/option-groups/{group_id}/sort-order`        | `update_option_group_sort_order`      |
| PATCH  | `/api/v1/option-groups/{group_id}/required`          | `update_option_group_required`        |
| PATCH  | `/api/v1/option-groups/{group_id}/multiple-choice`   | `update_option_group_multiple_choice` |
| POST   | `/api/v1/option-groups/reorder`                      | `reorder_option_groups`               |
| DELETE | `/api/v1/option-groups/{group_id}`                   | `delete_option_group`                 |
| DELETE | `/api/v1/option-groups/product/{product_id}`         | `delete_product_option_groups`        |
| GET    | `/api/v1/option-groups/product/{product_id}/summary` | `get_option_groups_summary`           |
| GET    | `/api/v1/product-options/`                           | `list_product_options`                |
| GET    | `/api/v1/product-options/group/{group_id}`           | `get_group_options`                   |
| GET    | `/api/v1/product-options/{option_id}`                | `get_product_option`                  |
| POST   | `/api/v1/product-options/`                           | `create_product_option`               |
| POST   | `/api/v1/product-options/bulk`                       | `create_product_options_bulk`         |
| PATCH  | `/api/v1/product-options/{option_id}`                | `update_product_option`               |
| PATCH  | `/api/v1/product-options/{option_id}/availability`   | `update_product_option_availability`  |
| PATCH  | `/api/v1/product-options/{option_id}/price`          | `update_product_option_price`         |
| PATCH  | `/api/v1/product-options/{option_id}/sort-order`     | `update_product_option_sort_order`    |
| POST   | `/api/v1/product-options/reorder`                    | `reorder_product_options`             |
| DELETE | `/api/v1/product-options/{option_id}`                | `delete_product_option`               |
| DELETE | `/api/v1/product-options/group/{group_id}`           | `delete_group_options`                |
| GET    | `/api/v1/product-options/group/{group_id}/summary`   | `get_group_options_summary`           |
| GET    | `/api/v1/products/`                                  | `list_products`                       |
| GET    | `/api/v1/products/{product_id}`                      | `get_product`                         |
| POST   | `/api/v1/products/`                                  | `create_product`                      |
| PATCH  | `/api/v1/products/{product_id}`                      | `update_product`                      |
| PATCH  | `/api/v1/products/{product_id}/availability`         | `update_product_availability`         |
| POST   | `/api/v1/products/{product_id}/enable`               | `enable_product`                      |
| POST   | `/api/v1/products/{product_id}/disable`              | `disable_product`                     |
| DELETE | `/api/v1/products/{product_id}`                      | `delete_product`                      |
| GET    | `/api/v1/products/stats/summary`                     | `get_product_summary`                 |
| GET    | `/api/v1/products/restaurant/{restaurant_id}`        | `get_restaurant_products`             |
| GET    | `/api/v1/products/category/{category_id}`            | `get_category_products`               |
| GET    | `/api/v1/products/{product_id}/details`              | `get_product_with_details`            |
| GET    | `/api/v1/categories/`                                | `list_categories`                     |
| GET    | `/api/v1/categories/{category_id}`                   | `get_category`                        |
| POST   | `/api/v1/categories/`                                | `create_category`                     |
| PATCH  | `/api/v1/categories/{category_id}`                   | `update_category`                     |
| POST   | `/api/v1/categories/reorder`                         | `reorder_categories`                  |
| DELETE | `/api/v1/categories/{category_id}`                   | `delete_category`                     |
| GET    | `/api/v1/categories/stats/summary`                   | `get_category_summary`                |
| GET    | `/api/v1/categories/restaurant/{restaurant_id}`      | `get_restaurant_categories`           |
| GET    | `/api/v1/categories/{category_id}/products`          | `get_category_products`               |
