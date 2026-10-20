# Order architecture audit — 8 October 2026

Historical logs were consolidated on 15 October 2026 in
[`artifacts/test-logs/`](../artifacts/test-logs/INDEX.md), a local folder excluded
from Git and Docker images. Keeping them does not constitute a new validation
of the results below.

This is a chronological record. Earlier setup instructions and commands describe
their recorded dates and do not authorize execution under the current scope.
For the current authorized setup and approval status, see the
[development verification](billing-development-verification.md) and
[operational runbook](billing-production-runbook.md).

## Conclusion and scope

Latest validation after the correction: **178 tests passed, no failures, no
warnings**, with coverage and caching enabled and `-W error`. Log:
[warnings-fix-full-tests.log](../artifacts/test-logs/warnings-fix-full-tests.log).

The corrections described here cover the inspected order paths: the owner API,
customer actions, business services, and associated repositories.
A complete baseline run recorded on 8 October 2026 produced
**178 tests passed, no failures, 3 warnings**, in 18 min 13 s.
This result is evidence for the tested scenarios, not a general guarantee
covering every access path, business rule, or concurrency case.

## Authorization and restaurant boundaries

| Caller | Observed control | Limitation |
| --- | --- | --- |
| Owner API | `Order.restaurant_id -> Restaurant.owner_id -> OwnerPrincipal`, checked by the API's authorization dependencies. | The boundary is the owner. One owner may access orders from several restaurants they own. |
| Customer within a restaurant | `Order.user_id -> User.chat_id`, supplemented by `Order.restaurant_id` when the restaurant is supplied to the service. | The caller must provide a trusted restaurant context to enforce this boundary. |
| Customer without a restaurant | Filtering by customer account, without a restaurant filter. | Global mode remains allowed; it does not provide restaurant-level isolation. |
| Internal administrative services | Receive order identifiers; authorization occurs at the API entry point. | These services do not, by themselves, provide an authorization boundary. |

Here, "tenant" means the logical owner boundary used by the inspected API.
The control does not demonstrate isolation based on a separate tenant
identifier or a PostgreSQL RLS policy.

For tracking, cancellation, and modification actions, the restaurant from the
channel context takes precedence over the extracted entity. The helper converts
the context into an identifier; a value it rejects produces the
`restaurant_id=0` filter. A missing value retains global mode.

Order creation and item addition look up the product within the order's
restaurant. The name and base price come from the server catalogue. A supplied
branch must belong to the restaurant. Generic updates reject reassignment of
`restaurant_id` or `user_id`. Exposed names and phone numbers come from the
customer profile; changing them through an order is explicitly rejected.

## Corrections and responsibilities

| Topic | State of the inspected code |
| --- | --- |
| Creation | The API delegates to the business service. Creation with and without items shares the same core; the order, items, history, counter, usage, and metrics are composed within the unit of work. |
| Creation action | `OrderFoodAction` adapts parameters and responses. Quoting, consent, and placement are in `orders/placement.py`. |
| Order transitions | Status mutations and history use `transition_locked_order`. The customer cancellation policy remains separate from the administrative policy. |
| Payment | Confirmation checks the payment/order association and updates the payment ledger without replacing preparation/delivery status with `paid`. Repeating this confirmation has no additional effect. |
| Calculations | `item_total` validates quantity/price and calculates an item's amount; `compute_order_totals` provides the shared totals formula. This is not an exhaustive audit of promotions, options, or pricing policies. |
| Order repositories | `OrdersRepository`, `OrderItemsRepository`, `OrderItemOptionsRepository`, `OrderStatusHistoryRepository`, and `OrderPaymentsRepository` use `commit_on_write=False`. The affected inherited methods do not independently commit or roll back. |
| Auxiliary repositories | Generic repositories retain their historical convention. The `defer_repository_commit` flag defers commits/rollbacks in methods that honor it when participating in the unit of work. |
| Response contracts | Payments use the existing order schemas, separate from subscriptions. Detailed retrieval serializes the item list returned by the service. |

Facades adapt contracts and compose operations. Business modules implement
policies and orchestration; they also retain some direct SQL queries.
Moving every SQL access into repositories is therefore incomplete.
The centralization described above does not demonstrate the absence of all
duplication elsewhere in the application.

## Transaction ownership

The behavior of [order_transaction](../app/services/business/orders/transaction.py)
depends on the SQLAlchemy session state:

| State on entry | Behavior |
| --- | --- |
| No active transaction | `session.begin()` opens a transaction; exiting it handles commit or rollback. |
| Implicit root `AUTOBEGIN` transaction | A savepoint wraps the operation, then the service commits the root transaction on success or rolls it back on failure. |
| Explicit caller transaction | A savepoint wraps the operation; the caller retains responsibility for the root commit/rollback. |
| Composed call under `order_unit_of_work` | A nested savepoint is created; this call does not finalize the root transaction. |

The `AUTOBEGIN` case finalizes the session's entire transaction, including any
earlier writes. A caller that wants to retain ownership of its writes must
open an explicit transaction.

Savepoints protect writes executed within their scope. They do not establish
that every earlier write will be rolled back: SQLAlchemy can, in particular,
flush pending changes before opening a savepoint.

The inspected status, payment, and quantity paths lock the order before
sensitive checks. Catalogue validation locks the product. The tests below do
not simulate concurrent writes and therefore do not demonstrate every effect
of these locks under real concurrency.

Cancellation with a refund updates the internal ledger within the same unit
of work. It does not perform a refund through an external banking gateway.
This audit added no migration or RLS policy.

## Test evidence and limitations

The 26 cases in [test_order_tenant_isolation.py](../tests/test_order_tenant_isolation.py)
are distributed as follows:

| Case | Count | Evidence provided |
| --- | ---: | --- |
| Owner authorization | 4 | Predicates executed on SQLite, covering allowed and denied access. |
| HTTP rejection | 9 | Read, update, status, cancellation, completion, payment, deletion, listing, and statistics requests from a foreign owner rejected before the business call. |
| Customer tracking | 4 | Filtering by customer and restaurant, including a different restaurant owned by the same owner. |
| Rejected customer mutations | 6 | Cancellation or modification outside the customer/restaurant boundary, with no write observed in the test adapter. |
| Action context | 3 | Mocked services: verification that the channel's restaurant takes precedence. |

These 26 cases are therefore not all SQL tests: the three action tests use
mocks. The list and statistics tests establish entry-point rejection, not
content filtering of an authorized list or aggregate.
SQLite validates neither PostgreSQL locks nor production transactions.

The 18 cases in [test_order_postgres_transactions.py](../tests/test_order_postgres_transactions.py)
use a real PostgreSQL test database and reads from a second session.
They cover persistence of creation and mutations, implicit/explicit transaction
ownership, rollback after item, history, usage, metric, or payment failures,
rejection of foreign products/payments, cross-owner HTTP rejection, detailed
rereads, transitions, deletion, and atomic cancellation/internal refunds.
They do not establish every concurrent interleaving or an external bank refund.

The [architecture-boundary tests](../tests/test_order_architecture_boundaries.py)
check certain prohibited operations in the creation action and invalid
price/quantity inputs. The
[repository transaction-mode tests](../tests/test_repository_transaction_mode.py)
verify, in particular, the absence of commit/rollback during an `update` for
the five order repositories; they do not individually test every method.

Result recorded in
[completion-full-tests.log](../artifacts/test-logs/completion-full-tests.log):
**178 passed, 3 warnings in 1093.36s (0:18:13)**, exit code 0.
The three warnings concern FastAPI's deprecation of
`HTTP_422_UNPROCESSABLE_ENTITY`. No test was reported as skipped in this run.
This documentation correction does not constitute a new test execution.

## Reproduction and test environment

From the project root in PowerShell:

```powershell
$env:DEBUG = 'false'
.venv\Scripts\python.exe -u -m pytest -W error --tb=short
```

This command retains caching, enables the coverage configured in pytest.ini,
and treats warnings as errors. `DEBUG=false` overrides the `DEBUG=release`
value observed during the previous execution, without changing `.env`.

The configuration in [tests/conftest.py](../tests/conftest.py) uses a dedicated
database derived from the configured URL with the `_test` suffix. It cleans
tables using `TRUNCATE ... RESTART IDENTITY CASCADE` for tests using `client`
or `db_session`; this command must run with an appropriate test-database
configuration.

Test connections use a pool of at most five connections,
`pool_pre_ping=True`, a 60-second connection timeout, a 60-second command timeout,
and `lock_timeout=5000`. The idle transaction timeout is disabled for these
connections. The pool closes at the end of the pytest session; asyncio tests
and fixtures share a session loop while retaining per-test fixture scope
where declared.

These settings were introduced after query/TLS connection timeouts and a
cleanup disconnection during earlier attempts. The server had then reported
`idle_in_transaction_session_timeout=5min`; this is insufficient to attribute
every disconnection conclusively to that parameter alone. The latest suite's
success does not guarantee the absence of future network problems.
These test adjustments did not change production settings.

## Correction of the incident reported after the audit

A subsequent run supplied by the user produced **177 passed,
1 failed, 5 warnings**. The failure concerned updating payment methods, with
a connection closed during a read of `products`. That trace alone does not
identify the cause of the network closure.

The payment-settings repository now loads only scalar fields for retrieval
by restaurant and identifier. It no longer traverses the restaurant/catalogue
graph on this path. The update test verifies that restaurants, products, and
categories are not read and that changed payment methods persist.
No write is replayed automatically after a disconnection.

The deprecated `HTTP_422_UNPROCESSABLE_ENTITY` constant was replaced with
`HTTP_422_UNPROCESSABLE_CONTENT` in the APIs; the HTTP status remains 422.
The pytest cache now uses `.cache/pytest`, whose writability was verified,
instead of the inaccessible `.pytest_cache` directory. Caching remains enabled.
A rerun also revealed a TLS timeout after 15 seconds while opening a connection;
the test harness's connection timeout is now 60 seconds.

Targeted validation: **22 passed**, without warnings, with `-W error` and caching
enabled ([payment-warning-check.log](../artifacts/test-logs/payment-warning-check.log)).
Complete revalidation with coverage, caching, and `-W error` succeeded:
**178 passed in 1452.81s (0:24:12)**, no warnings, exit code 0.
Overall coverage: **40 %**.
Log: [warnings-fix-full-tests.log](../artifacts/test-logs/warnings-fix-full-tests.log).
An additional complete attempt passed the metrics tests but failed during their
cleanup: the fixture connection was already closed. API fixtures no longer
perform unnecessary preparation `refresh` calls after `flush`/`commit`.
Identifiers are already available, and values are retained through
`expire_on_commit=False`. This avoids reopening an idle read transaction and
holding its connection during API requests. Assertions, commits needed for
preparation data, and cleanup rollback/truncate operations remain; no error
is ignored.

## Progressive removal of SQLAlchemy compatibility facades

This step removes only adapters whose calls no longer remained in either
`app/` or `tests/`. It does not replace active business services, handlers,
or HTTP contracts.

- The 16 unreferenced compatibility functions in the `orders` domain were
  removed in the first substep.
- The six `compat.py` modules for the restaurant, metrics, order-counter,
  payment-settings, group, and branch domains were removed.
- The corresponding exports were removed from the `restaurant` and `business`
  package initializers. The concrete SQLAlchemy services and handlers remain
  those packages' only public APIs.

Evidence specific to this substep: `black --check` left the 21 inspected files
unchanged; `compileall` and imports of `app.services.business` and
`app.services.business.restaurant` succeeded; Ruff, restricted to undefined or
unused symbols (`F401`, `F811`, `F821`, `F841`), reported no errors.
The order architecture boundary also passed: **8 passed in 0.10s**
with `DEBUG=false`, `--no-cov`, and `-W error`.

This evidence does not replace a complete run after removal. An attempt to
start the restaurant API tests was interrupted because overlapping reruns of
the same subset were using the test database simultaneously; its result is
therefore not recorded as validation. A single complete rerun, without
concurrent execution, remains required before delivery.

Final validation of this substep: a complete, isolated, nonconcurrent run passed
after removal: **181 passed in 500.57s (0:08:20)**, exit code 0,
with `DEBUG=false`, `--no-cov`, and `-W error`. The log is
[compatibility-removal-full-tests.log](../artifacts/test-logs/compatibility-removal-full-tests.log).
This run does not measure coverage because `--no-cov` was deliberately used;
the actual coverage recorded earlier in this report is therefore neither
recalculated nor presented as coverage for this substep.

Additional substeps removed seven unreferenced facades from the restaurant
metrics repository and six unreferenced facades from the order-counter
repository. Isolated tests passed with `DEBUG=false`, `--no-cov`, and `-W error`:
metrics + order creation, **12 passed in
33.94s**; counter + order creation, **11 passed in 36.64s**.
These results cover the directly affected contracts; another complete run will
be required after the last removal substep.

A third substep removed three unreferenced facades from the restaurant
payment-settings repository. Isolated payment-settings and payment-isolation
validation passed: **7 passed in 13.71s** with
`DEBUG=false`, `--no-cov`, and `-W error`.

### Restaurant repository — removal of the remaining facades

The six remaining compatibility functions in `restaurant_repo`
(`get_restaurant_by_id`, `get_restaurants_by_owner`, `search_restaurants`,
`get_restaurant_with_details`, `get_all_restaurants`, and `create_restaurant`)
were removed after searching imports and calls in `app/` and `tests/`.
Consumers had already migrated to `RestaurantRepository` and an explicit
SQLAlchemy session. The `func` import required by `count_search` was retained
at the SQLAlchemy level.

Targeted validation after removal: **19 passed in 228.35s (0:03:48)**
with `DEBUG=false`, `--no-cov`, and `-W error`:
`tests/api/v1/restaurant/test_restaurants.py` and
`tests/test_payment_tenant_isolation.py`. Ruff and `compileall` also passed for
the repository. This run does not measure coverage and does not replace a final
complete project run after all future removal substeps.

### Removal of order-item and order-history facades

The unreferenced compatibility functions in `order_status_history_repo`
and `order_items_repo` were removed, including their old transaction variants.
Business services already use `OrderStatusHistoryRepository` and
`OrderItemsRepository` directly with the active workflow's SQLAlchemy session.

Validation after each substep: **53 passed in 220.04s (0:03:40)** for history,
then **53 passed in 285.67s (0:04:45)** for items,
with `DEBUG=false`, `--no-cov`, and `-W error`. The selection includes order
service contracts, PostgreSQL transactions, transactional creation, and
repository transaction modes. These targeted runs do not calculate coverage
and do not replace the final complete test run after subsequent removals.

### RBAC and branch feature guard — 11 October 2026

This substep adds the normalized SQLAlchemy `roles`, `permissions`, and
`role_permissions` model, together with the nullable transitional
`admins.role_id` link. Migration `a91e7c2b4d10` seeds the `super_admin`, `admin`,
and `support` roles and their agreed permissions, then links existing
administrators when their historical `admins.role` value matches the role code.
The historical field is retained only for role checks during the transition;
a permission check fails closed without an active RBAC role.
The `super_admin` role has the universal `*` permission.

Branch creation now goes through `require_feature` with the same SQLAlchemy
session. The documented `no_active_subscription`, `feature_not_available`, and
`feature_limit_reached` errors are exposed as 403 rejections with stable codes.
The `skip_feature_check` argument remains reserved for the internal service
(migration/super-administrator) and is absent from the public endpoint.
Creation and counter increment run within the same transaction boundary;
a failure raises the exception and rolls back the savepoint or the
service-owned transaction.

Evidence executed for this substep: `DEBUG=false python -m pytest
 tests/test_branch_feature_guard.py tests/test_admin_rbac_permissions.py -vv
 --no-cov -p no:cacheprovider` produced **10 passed in 0.50s**.
These tests cover the three guard rejections, the allowed path with increment,
the transaction boundary, an explicit permission, the super-admin wildcard,
an inactive role, and the role-only transition. They do not measure coverage;
no new overall coverage is claimed. `alembic check` confirmed that the target
database is not up to date: the RBAC migration had therefore not yet been
applied there. An integration run with explicit subscription/feature/limit
fixtures and a new complete suite remain required after applying the migration.

### Isolated test database and Alembic baseline — 11 October 2026

`TEST_DATABASE_URL` is now an explicit setting: tests no longer derive a URL
by concatenating `DATABASE_URL` and a suffix. The harness accepts only a URL
whose database is `neondb_test`; `alembic_test/env.py` and `tests/conftest.py`
apply the same guard before any migration or `TRUNCATE`.

The historical `alembic/` chain was not rewritten: it remains the migration
chain for existing environments. A parallel chain dedicated to tests resides
in `alembic_test/`. Its `ae6a266365fb` baseline creates the current SQLAlchemy
schema from an empty database, and its `b7d33e89f4a1` migration seeds canonical
RBAC roles, permissions, and associations. This separation avoids running
historical migrations that assume existing tables against an empty database.

The `scripts/create_test_tables.py` script no longer uses `create_all()` or a
derived URL. With no option, it applies only `alembic_test.ini upgrade head`;
`--reset` is required to drop and recreate only the `public` schema of
`neondb_test`, then replay the migrations. The session fixture refuses to clean
tables when `alembic_version` is not at the head of this chain and indicates
the appropriate bootstrap command.

Evidence executed after this update: the baseline and RBAC seeds were
successfully applied to `neondb_test`, then
`tests/api/v1/restaurant/test_categories.py` produced **3 passed in 35.18s**.
Combined category, branch-guard, and RBAC validation produced
**14 passed in 48.58s**, without warnings. The latest result is retained in
[test-schema-rbac-branch-tests.log](../artifacts/test-logs/test-schema-rbac-branch-tests.log).

This evidence is targeted: it constitutes neither new overall coverage nor
a complete post-baseline run. The branch-boundary test verifies commit deferral
and counter rollback within an isolated unit; it does not simulate every
PostgreSQL concurrent interleaving. Every new table or seed required by tests
must be added to the `alembic_test/` chain and validated on `neondb_test` before
a fixture assumes its presence.

### Unused payment and subscription compatibility removal - 12 October 2026

Removed 27 unreferenced module-level compatibility functions: seven from
`payment_repo`, nine from `subscription_repo`, eight from `payment_service`,
and three from `subscription_service`. The subscription service exports now
contain only its class and existing type aliases. Repository and service class
implementations, and the bodies of retained entry points, are unchanged (AST
comparison against HEAD). A repository-wide Python import scan found no imports
of removed symbols.

Six used entry points remain: `get_payment_by_reference`, `confirm_payment_tx`,
`fail_payment_tx`, `get_subscription_by_id`, `activate_subscription_tx`, and
`create_payment_request`. Their callers require a separate migration. In
particular, `payment_callback` omits required sessions for reads and supplies a
Psycopg connection to SQLAlchemy repositories for writes; its transaction
helpers also call keyword-only repository methods positionally. These existing
callback defects were not changed or exercised by this removal.

Validation: **11 passed in 2.35s**, with `DEBUG=false`, `--no-cov`,
`-p no:cacheprovider`, and `-W error`, covering payment tenant isolation,
subscription repository API, and repository transaction modes. The sandbox
attempt failed at PostgreSQL connection setup; the authorized retry passed on
the isolated test database. Ruff checks for `F` and `RUF022`, and compileall,
passed for the four changed modules. The unrestricted Ruff rule set still
reports existing modernization/style findings. This is targeted validation,
not a full-suite result or evidence of payment callback correctness.

### Used payment/subscription entry-point migration - 12 October 2026

The remaining six compatibility functions in `payment_repo`, `subscription_repo`
and `payment_service` have been removed after migrating their callers. The
external callback module now opens and closes one SQLAlchemy session and delegates
to `PaymentService.confirm_external_payment` or `fail_external_payment`. The
business service owns billing orchestration; repositories own queries and row
locks. `payment_transaction` follows the existing branch/order transaction
convention: suppress repository commits, commit a service-owned transaction or
read-triggered AUTOBEGIN, and use a savepoint inside an explicit caller transaction.
The previous repository-commit setting is restored on both success and failure.

Success locks the payment and subscription, validates status and owner/restaurant
scope, then confirms payment, activates the subscription, transfers requested
features, and deletes those requests in one transaction. Duplicate paid events
are no-ops. An already active subscription retains its dates. Monthly/yearly
periods remain 30/365 days, with UTC stored in the existing naive timestamp
columns. Unsupported cycles and non-pending/non-active subscriptions are rejected.
Failure events cannot downgrade paid, cancelled, or refunded payments. Failed
payments remain terminal under the existing PaymentService transition policy.
Payments without a subscription retain the previous logged no-op behavior.

Customer order confirmation now uses `OrderPaymentsService.confirm_customer_payment`
and the order-payment schema/table, rather than creating a subscription Payment
and reusing its ID as an OrderPayment ID. The service checks the persisted
customer chat/user relationship under the order lock, uses the stored order
amount, rejects incompatible active payments, reuses a matching pending/paid
payment, and composes creation and confirmation in one order transaction.
Fulfillment status is not advanced by this operation. State/UI updates happen
only after the service succeeds; owner/restaurant ID fallback values are removed.

Repository query_options are honored by the billing feature/request base queries
and user chat lookup. The new use cases choose scalar-only loading through the
existing raiseload option hook, avoiding unrelated eager relationship graphs;
other repository consumers retain their default loading behavior.

PostgreSQL regression coverage includes real persistence across sessions,
feature-transfer rollback, explicit caller rollback, AUTOBEGIN commit,
monthly/yearly dates, active-subscription date preservation, status/scope rejection,
duplicate success/failure events, concurrent duplicate confirmation, customer
ownership, order/payment domain separation, and rollback of a new order payment
when confirmation fails. Callback contract tests also verify session closure,
error propagation, authoritative amounts, and absence of paid state/UI on failure.

The first sandbox run failed at connection setup. A later run was stopped after
observing excessive eager relationship reads; scalar loading was then restricted
and **14 PostgreSQL tests passed in 79.40s**. These tests exercise service and
session boundaries, not provider signature verification or webhook routing. The
external adapters retain their external_reference-only contract and expect an
authenticated gateway caller; this change does not implement a gateway endpoint
or alter the existing Telegram router wiring. Other compatibility functions in
`order_payments_service` and other callback session migrations remain outside
this six-function removal.

Final validation after the loading changes: **60 passed in 70.67s**, with
`DEBUG=false`, `--no-cov`, `-p no:cacheprovider`, and `-W error`. The selection was
`test_payment_subscription_transactions`, `test_payment_callback_service_contracts`,
`test_payment_tenant_isolation`, `test_subscription_compat`,
`test_repository_transaction_mode`, `test_order_service_contracts`,
`test_order_creation_transaction`, and `test_user_callback_service_contracts`.
Results are retained in [payment-subscription-final-validation.log](../artifacts/test-logs/payment-subscription-final-validation.log). Ruff F checks
passed on modified existing modules; all enabled Ruff checks passed on the new
transaction module and test files. Compileall and the scoped git diff whitespace
check passed. Static import checks found no references to removed billing
compatibility functions. This targeted run is not a full-project test run or a
coverage measurement.

### Remaining application compatibility interfaces - 12 October 2026

The repository-wide review covered compatibility markers in English and Arabic,
module-level service/repository facades, pure aliases, exports, and their static
call sites across app, tests, and scripts. This step removes 28 functions/methods:

- Ten module-level OrderPaymentsService facades, after migrating four handler
  modules to the class interface and explicit SQLAlchemy session lifetimes.
- Three unused administrative session facades and two unused administrative
  logging/audit facades; their package exports are removed.
- The check_order_editable_from_dict, get_valid_subscription, get_password_hash,
  and get_next_statuses aliases, using the existing primary interfaces instead.
- The unused duplicate get_async_session generator (get_db remains canonical),
  the unused send_screen facade, and UIManager.update. Its 85 remaining callers
  now select send_new_message or edit explicitly. These callers already identify
  whether a message exists; message tracking and keyboard resolution stay in
  the primary UIManager methods.
- AIClient.chat_completion, after migrating intent classification and entity
  extraction to AIClient.chat with the same user/system prompts and parameters.
- RestaurantGroupRepository.toggle_active/bulk_toggle_active,
  RestaurantGroupService.toggle_active, its event-handler facade, and the
  PATCH /restaurant-groups/{group_id}/toggle-status endpoint. RestaurantGroup has
  no is_active column, so these methods previously reported success without
  changing persisted state. No replacement activation endpoint is introduced.

The group-only ignored include_inactive/only_active parameters are removed from
repository/service/API signatures. The ignored permanent flag is removed from
all three group deletion layers; group deletion keeps its existing physical
operation. The delete route and group CRUD/branch/statistics interfaces remain.
Query flags are no longer documented or propagated. FastAPI's general treatment
of unknown query parameters is not changed. Existing statistics fields that
represent all groups as active are not database activation controls.

Telegram success/failure callbacks now call the transactional
OrderPaymentsService.set_customer_payment_status with chat_id, order_id, and
payment_id. Persisted user ownership and payment/order association are checked
under the order lock; repeated identical events are no-ops. A failed operation
cannot overwrite UI/state with a paid/failed result, and late failure cannot
turn a paid payment into failed. Successful UI amounts/methods come from the
persisted payment. Checkout without an order reads restaurant payment settings
instead of querying a synthetic order 0. An explicitly empty allowed-method set
is no longer replaced with cash/card by the migrated callers.

Canonical business use cases, type aliases, HTTP parameter aliases, token
verification with exception handling, session factories, and Telegram exception
classes are not obsolete function facades and are retained. The old wording in
orders/totals described an earlier architecture; its implemented calculation
and persistence use cases remain. No database migration is required by this step.

A full test attempt initially failed at application import because
payment_transaction.py contained RBAC model declarations instead of the billing
transaction context. The unexpected content was preserved as
[payment-transaction-unexpected-content.snapshot.txt](../artifacts/test-logs/payment-transaction-unexpected-content.snapshot.txt) and the previously validated
transaction context restored. The RBAC models remain in app/models/rbac.py.
The complete suite was then restarted against the isolated neondb_test schema.

Final functional validation: **243 passed in 810.94s (13:30)** for the complete
configured tests/ suite, with DEBUG=false, --no-cov, -p no:cacheprovider,
and -W error. The result is retained in [remaining-compatibility-full-tests.log](../artifacts/test-logs/remaining-compatibility-full-tests.log).
This includes restaurant CRUD/branches/groups/metrics/payment settings, RBAC,
order PostgreSQL transactions, tenant isolation, authentication, billing and
customer-payment transactions, callback contracts, UI sends/edits, NLU prompt
migration, and the OpenAPI removal contract. No coverage percentage is claimed.

The global Ruff F check on app/ and tests/ passed, as did all enabled Ruff checks
on the new transaction/contract-test modules, compileall, static application
import checks, and git diff --check on app/tests/the audit document. Four existing
unnecessary f-string prefixes were normalized without changing string contents;
trailing blank lines left by 16 earlier facade removals were also normalized.
Final reference scans found no callers of the removed names or compatibility
function markers in app/. Historical notes about Telegram exception inheritance,
cryptographic algorithm deprecation, typing aliases, and HTTP aliases are outside
obsolete function-facade removal and remain meaningful documentation/contracts.

## 13 October 2026 — session lifecycle and phase-one manual billing

This step follows the owner's explicit payment strategy in
`docs/payment-integration-strategy.md`. CCP and BaridiMob are manual transfers.
Electronic Algerian providers and international providers remain roadmap work,
without fabricated APIs or provisional live gateway adapters.

All ten remaining `async with get_session()` sites now await the asynchronous
session factory. Subscription-price calculation receives an open session and
normalizes stored UTC dates before date comparisons. Restaurant selection accepts
the router's `match` argument and awaits UI helpers with their actual signatures.
Private owner dashboards check persisted restaurant ownership before reading
orders or catalog data.

Customer payment routes are registered once, with a noncapturing payment-method
group so group 1 remains the order ID. Method selection, request submission,
retry and navigation dispatch to their own handlers. Gateway success/failure
events are no longer Telegram routes and do not fall through the generic order
handler. The unused external and Telegram status-handler modules are removed.

The previous Telegram status-settlement description above is superseded:
`submit_customer_payment` records or reuses a pending order payment. A customer
cannot mark a payment paid by pressing a button. Its response uses persisted
ownership, amount and status. The obsolete customer status mutation method is
removed. The subscription quote's old `payment_confirm_{plan_id}` button is
removed because it incorrectly interpreted a plan ID as an order ID.

Telegram requests require the configured `TELEGRAM_WEBHOOK_SECRET_TOKEN`, checked
before dispatch. The existing registration helper supplies it to Telegram's
`setWebhook` call. No live bot registration or message is sent during this work.

Phase-one billing now includes:

- A typed provider contract and an independent manual-transfer adapter, with
  explicit CCP/BaridiMob configuration flags. Method and provider identity are
  separate; current billing currency is DZD.
- Server-priced pending subscription checkout and invoice creation. The owner
  cannot override the price, claim another tenant's subscription, or request an
  undocumented provider adapter.
- Bounded private receipt uploads, metadata, authenticated attachment downloads,
  a financial-review queue, expected invoice details, and read-only audit history.
- PostgreSQL uniqueness constraints on the invoice's receipt, receipt hash, and
  normalized postal transaction reference, including across tenants. Exact
  repeated submissions are idempotent and never activate subscriptions.
- Live normalized RBAC checks for `payments.review`. Administrative identities
  map a verified OIDC subject to `admins.auth_subject`; client-supplied admin IDs
  are not accepted. The administrators CRUD router requires `admins.manage`.
- Independent approval inputs for actual bank credit: amount, DZD currency,
  bank reference, an explicit received-funds attestation, and an audit note.
- Atomic payment settlement, subscription activation and feature transfer,
  receipt review, and audit persistence. Nested billing transactions no longer
  commit an enclosing AUTOBEGIN transaction prematurely.
- Final rejection without subscription activation. Conflicting decisions and
  attempts to reuse submitted evidence are rejected.

`PaymentService` manages the ledger; activation and feature transfer now belong
to `SubscriptionService`. `SubscriptionCheckoutService` coordinates their
creation, and `ManualPaymentService` coordinates administrative settlement. The
unused unverified subscription-activation method is removed. Legacy owner HTTP
ledger mutation endpoints reject direct changes after checking ownership.
SaaS subscription payments and restaurant order payments remain distinct ledgers.

Production migration `c413b7918a20` is prepared with a single production head.
The dedicated test migration `dce91870b4a2` was applied to `neondb_test` without
resetting that schema. The production database and the real `.env` are unchanged.
Historical amount columns are preserved; new subscription prices are rounded
to DZD cents, and review validation uses Decimal values.

Targeted checks: 57 contract/authentication/session tests passed; the manual
workflow proved private uploads, cross-tenant duplicate prevention, live RBAC,
concurrent approval, rejection, and rollback on feature/audit failures. The
server-priced checkout test and all 14 billing transaction regressions passed
together (15 tests). Ruff F, enabled checks on the new modules, compilation,
production migration-head inspection, and whitespace checks passed.

Deployment must apply the production migration, provision trusted reviewer
identity mappings, and configure/register the Telegram secret. The upload and
review APIs are implemented; dedicated receipt-upload screens remain a separate
presentation-layer task. Manual bank details and ledger verification are real
operational inputs, not simulated gateway results. The complete-suite result is
recorded in the final validation entry below.

Final payment-selection review additionally moved the displayed amount and
allowed-method list to an owned persisted-order query. Retry/back navigation
checks the same customer scope and does not overwrite financial status. An
explicitly configured empty method set remains empty. The related scalar
repository reads use scoped raiseload options. All 15 focused callback/quote
checks passed before restarting the complete suite on this final version.

### Final validation and cached-session correction

The complete configured suite passed: **294 passed in 1339.17s (22:19)**,
with `DEBUG=false --no-cov -p no:cacheprovider -W error`. The complete log is
[manual-billing-full-tests.log](../artifacts/test-logs/manual-billing-full-tests.log).

A subsequent additional PostgreSQL regression deliberately retained pending
Payment/Receipt ORM objects while another session committed approval. It proved
that a row lock alone did not refresh those cached attributes: replay changed
`paid_at` and appended a duplicate approval audit. The locked payment/receipt
queries and the internal settlement query now use `populate_existing=True`,
consistent with the existing subscription and external-payment row locks.

After this final correction, the complete affected payment, subscription,
authentication, webhook, and callback/session set passed again:
**95 passed in 396.27s (6:36)**. This includes all 15 manual-workflow regressions,
16 subscription/order-payment transaction regressions, 21 manual contracts,
13 customer payment callback contracts, 14 authentication tests, six webhook
contracts, and ten session-lifecycle tests. Its log is
[manual-billing-final-tests.log](../artifacts/test-logs/manual-billing-final-tests.log). The new regression preserves the original
payment timestamp, subscription dates, finalized receipt, and two audit entries
when an old session repeats an already approved decision.

The 294-test complete-suite result precedes the final cached-row correction;
the 95-test affected-suite result validates that final correction. These are
separate results, not a claimed 389 distinct tests or a new complete-suite run.
No coverage percentage is claimed. Final source/reference, Ruff, compilation,
and whitespace checks are recorded alongside this implementation review.

## 2026-10-13 — Telegram receipts and guarded production preparation

The private `/billing` flow now resolves the approved owner from the signed
Telegram sender, verifies restaurant and invoice ownership, creates a server-priced
checkout, displays the payment-request reference and configured beneficiary, and
accepts bounded PNG/JPEG/PDF evidence. Unconfigured or disabled methods are hidden.
Existing invoice metadata remains visible when transfer instructions are unavailable.
Receipt uploads do not activate subscriptions and are consumed before the AI agent.

Keycloak is the approved OIDC provider, but its real realm, client, issuer, audience,
JWKS endpoint, and administrator subjects are not supplied yet. The administrative
API fails closed before database access when configuration is missing. It validates
RS256 access-token signatures, issuer, audience, timing, subject, and `typ=Bearer`,
then resolves stored identity and current RBAC permissions. Administrative CRUD,
logs, sessions, registration requests, and manual reviews are protected. Telegram
has no administrative receipt review, approval, rejection, or receipt-download path.
Telegram and Keycloak identities remain separate and no administrator was created
or reassigned. Cached ORM authorization state now refreshes before each decision.

The configured production database was inspected read-only. Its revision remains
`a91e7c2b4d10`; both existing empty manual-evidence tables satisfy the strict
`c413b7918a20` contract. PostgreSQL 18 internal `char` values required an explicit
text cast in the schema validator; all constraint checks remain enforced. The
migration adopts compatible tables, rejects drift before its first change, and
requires independent approval. No production migration or administrator update ran.
Production recovery availability has not been verified; confirmation of a usable
backup or Neon restore point remains required before executing the migration.
Startup validates required tables and columns without issuing `create_all`.

The local `.env` now has valid `DEBUG=false` and a generated webhook secret. The
inherited shell still supplies `DEBUG=release`, so operational commands explicitly
set `DEBUG=false`. Beneficiary values and OIDC settings remain unconfigured. The
secret is not printed, committed, or copied into artifacts. Docker and Git exclude
local credentials and operational reports. No Render deployment, Git push, or live
webhook registration occurred. The Git origin matches the approved repository;
the local branch is `main`, while Render's connected service and branch still require
the user's confirmation. Deployment steps are in
[the production runbook](billing-production-runbook.md).

Final validation: **622 tests passed** with warnings treated as errors in
[billing-production-ready-final-full-tests.log](../artifacts/test-logs/billing-production-ready-final-full-tests.log) (933.97 seconds). After the final
financial constructor and invoice-display changes, **139 affected tests passed**
in [billing-final-affected-tests.log](../artifacts/test-logs/billing-final-affected-tests.log) (168.52 seconds), including the two additional
Telegram regressions and PostgreSQL transaction/authorization checks. These are
overlapping suites, not 761 distinct tests. There are 624 current collected tests.
The earlier eight obsolete 401 expectations were corrected to the required 503
behavior and passed in the final suite. Source compilation, Ruff F, enabled checks
for the new billing modules, and dependency consistency checks passed.

The complete Python-source export contains 199 existing changed files, SHA-256
checksums, and the eight removed Python paths. It contains full code, not snippets,
and no runtime receipt data or `.env`. All 199 exported sources now begin with the
exact required platform, author, license, and copyright header. Header and final
whitespace corrections preserved each file's executable AST. The source inventory includes earlier
cleanup changes; it is not a claim that every legacy module has been restyled in
this review. The remaining catalog-options tenant/authentication boundary is
documented separately in [the catalog finding](catalog-options-isolation-finding.md).

Update dated 2026-10-16: that catalog finding now records implemented owner
authentication, SQLAlchemy tenant scope, and relational HTTP regression checks.
The preceding counts and findings describe the historical 2026-10-13 review.

## Development branch isolation update — 2026-10-15

The user deferred production migration and authorized only the permanent Neon
development branch with `neondb_test`. They supplied the existing Render service,
its `main` branch, and a scoped successful historical recovery drill. See the
[development verification report](billing-development-verification.md) for the
distinction between user-provided recovery evidence and independently run checks.

The initial local inspection on 2026-10-15 found the test URL on the production
endpoint and stopped before opening a PostgreSQL connection. That state is
superseded: the user confirmed development endpoint `ep-quiet-rain-assrs0gv` on
branch `br-lively-truth-asga1dtk` in project `shiny-lab-60817779` and configured the
local test connection. The actual read-only preflight then passed with TLS
certificate and hostname verification, actual database `neondb_test`, installed
test revision `dce91870b4a2`, and 47 public tables. It did not change schema or data.
The actual PostgreSQL server reports `server_version_num=180006` (18.6).
Legacy destructive test utilities and the bootstrap reset option were removed;
no database or tables were reset.

The server-identity guard requires exact branch/project values with `postmaster`
context. The deployed endpoint setting reports `superuser`; the guard accepts
only `postmaster` or `superuser` for that setting, with `source='configuration file'`,
`setting=reset_val` equal to the approved endpoint, and `pending_restart=false`.
Verified TLS/hostname, branch, project, and actual database remain required.
Session/client/role/database overrides, missing settings, and other contexts fail
closed. The first guard requiring all three contexts to be `postmaster` correctly
stopped before any write; the endpoint-specific rule preserves the other checks
and does not claim that a `superuser` setting is immutable within a session.

The pending production revision and its test counterpart now register
`payments.review` without automatically changing role grants or identities.
Existing wildcard permissions retain their existing scope. The real migration
rehearsal is implemented with fresh/adoption/drift scenarios, rollback-only DDL,
and full public data/schema/sequence comparisons. All three actual scenarios now
passed. Fresh and adoption each enforced ten constraint checks and an idempotent
repeat upgrade; adoption preserved existing receipt/audit evidence. Tested legacy
rows, existing non-null owner identity, custom nonfinancial grants, role links,
and subscription state were preserved, with no administrator identity binding.
Drift was rejected before core billing writes. Each scenario measured identical
public rows, columns, constraint definitions/validation, indexes, sequence state,
and Alembic state after rollback; the persistent test head remains
`dce91870b4a2` with 47 tables and no permanent database changes.

The [sanitized live results](../artifacts/billing-production-review/development-rehearsal-results.json)
record `production_touched=false`. Their `source_sha256` matches the actual
[rehearsal source](../scripts/billing_test_rehearsal.py),
`c75433123ef48b053c01684355e04b9098bea2f61978a67ce33feb3bb2e5e949`.
Earlier attempts with captured snapshots also verified rollback. One stopped
before `before_snapshot` and before any DDL; no measured rollback-hash comparison
is claimed for that attempt. Transaction rollback is distinct from archive/PITR
restoration and does not complete the remaining production prerequisites.

The diagnosed stop was the rehearsal's expected SQLSTATE for deleting a payment
with a receipt: PostgreSQL 18 correctly rejected deletion under
`manual_payment_receipts_payment_id_fkey` with `23001` (RESTRICT violation),
while the rehearsal expected the older `23503` result. That single expectation
now follows the actual server version; the constraint and rejection checks remain
enforced. All seven receipt negative cases passed before rerunning all scenarios.
This diagnoses a rehearsal expectation, not a failed financial-reference guard.
Primary PostgreSQL source links are recorded in the development report.

**113 non-overlapping offline cases passed**: all 76 standalone unittest cases
with `-W error`, and 37 pytest cases with `--noconftest --no-cov` (13 transaction,
three SQLite-schema, and 21 manual payment contracts). The 76 include 12 target
selector cases and 21 startup-verifier/begin-guard cases; the latter expanded
from 16 by five new guard cases. The earlier 13-test result is included in the
37 and is not added again. `-W error` is not attributed to the pytest run without
its evidence. Earlier subtotals, including 108, are superseded. Earlier full-suite
results predate the independent development branch and are not proof of a new run
there.

### Actual local startup verification — 2026-10-15

`app/api/payment_webhook.py` and the obsolete `stripe_webhook.py` are absent from
disk, with no imports found in app/tests/scripts. Stale IDE tabs do not establish
runtime imports and do not justify restoring those deleted payment paths.

The attached startup traceback reports `database schema needs migration` because
ordinary `app.main` startup selected the primary `DATABASE_URL` and production
schema `a91e7c2b4d10`, whose migration remains intentionally deferred. The schema
guard correctly rejects that startup; it does not authorize a production
migration, `create_all`, or `stamp`.

A central ORM selector using `DATABASE_TARGET=primary|development` now selects
the verified test connection for local development. Its 12 tests passed. The
tools added `DATABASE_TARGET=development` to the ignored local `.env` and asserted
that both `DATABASE_URL` and `TEST_DATABASE_URL` remained unchanged.
`APP_ENV=development` alone does not select a different database. No Render or
OIDC settings were changed.

Actual local ASGI startup passed. The
[sanitized startup evidence](../artifacts/billing-production-review/development-startup-results.json)
reports `completed=true` at `2026-10-15T13:59:59.448656+00:00`: real `init_db`,
completed lifespan startup/shutdown, real `close_db` awaited once, a read-only
session from the test-bound factory, verified root/health responses with status
200, and zero outbound HTTP transport calls. Patched globals were restored and
`production_touched=false`. All four recorded source-file hashes match the
actual verifier, app entry point, database module, and test-database guard.

The pooler preflight measured `transaction_read_only=on`,
`default_transaction_read_only=off`, and an installed read-only begin listener
on the verifier's isolated engine. It enforces read-only mode at every transaction
begin; checking the current mode remains mandatory. The earlier combined
current/default requirement
failed closed before app import without recording the observed values, so no
specific old mode value is claimed. This is actual local ASGI lifespan verification,
not verification of the deployed Render service, a deployment, or live OIDC or
Telegram integration.

Local startup from `D:\MoulAI`, using the existing ignored
`DATABASE_TARGET=development` setting:

```powershell
$env:DEBUG = 'false'
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The payment transaction guard now handles nullable `sync_transaction`, and seven
call sites use the required keyword arguments. The 13-test selection now included
in the 37 above validates transaction boundaries/contracts, not deployment or a
production migration.

The user confirmed the existing Render service and `main` branch, superseding
the earlier confirmation gap recorded on 2026-10-13. No Render account access,
production migration, administrator binding, GitHub push, Render environment
change/deployment, OIDC configuration, or Telegram webhook change occurred.
Production approval will
not be requested again before the user's eight prerequisites and updated report
are satisfied. New deployment remains gated on reviewing Render's database target
and Auto-Deploy configuration.

The user's historical recovery-branch deletion deadline
`2026-10-15 14:26:08 GMT+1` has passed. Its continued existence and the old restore
point's availability were not rechecked and are not assumed; future production
planning requires a currently available recovery point.

The final 2026-10-15 source export now contains 207 reviewed Python files and
10 removed paths, superseding the 199/eight inventory recorded on 2026-10-13.
The [complete copyable sources](../artifacts/billing-production-review/complete-python-sources.md)
and [ZIP archive](../artifacts/billing-production-review/moulai-reviewed-python.zip)
include manifest checksums and removal metadata. The inventory includes earlier
cleanup work and does not claim uniform strict style across all legacy code.
Archive extraction alone does not apply the recorded file deletions.

The catalog-options isolation finding remains open. Billing verification and
transaction rollback evidence do not certify the entire legacy platform as
production ready or replace a completed backup/PITR restoration drill.

Update dated 2026-10-16: the catalog authorization and tenant-isolation finding
above has been superseded by the implemented controls and verification described
in [the updated catalog review](catalog-options-isolation-finding.md). This does
not alter the historical billing results or the independent deployment limits.

## API authorization follow-up - 2026-10-17

The subsequent API review adds verified-owner SQLAlchemy scopes for catalog,
agent, and standalone branch services. Global user administration requires the
existing `admins.manage` permission. The restaurant administration aggregate,
including global groups, metrics, counters, and payment configuration, requires
`restaurants.manage`; synthetic metric simulation is no longer published.
Administrative session credentials use headers on static paths, with no legacy
URL aliases. Agent state persists through validated existing JSON fields, and
branch state/usage transitions share an atomic transaction.

See [API authorization](api-authorization.md),
[session client migration](admin-session-api.md), and
[API testing](api-testing.md) for contracts, dated verification, and limits.
These local code changes do not configure real identities, grant production
permissions, authorize a migration, or verify a new deployment.

### Category and branch integration correction - 2026-10-17

The reported seven PostgreSQL failures exposed a verification-scope gap in the
initial offline review. Category integration fixtures now explicitly supply a
seeded owner for authorized business cases, alongside anonymous and foreign-owner
regressions. Owner-scope construction no longer executes synchronous validation
SQL outside the AsyncSession greenlet: it detaches clean cached tenant entities
and refuses initial binding with pending changes. Scoped primary-key reloads
and filtered counts preserve SQLAlchemy's mapped provenance without accepting
raw protected Core projections.

Both affected integration modules passed all 10 cases on the verified isolated
development database. The full offline selection passed 2,248 collected cases
and 128 separate subtests, with no warnings. App coverage is 57.61%; API coverage
is 81.34%, with no source exclusions. See [API testing](api-testing.md) for exact
environments, evidence, and limits. Production, migrations, real identities,
Telegram configuration, and Render were not changed.
