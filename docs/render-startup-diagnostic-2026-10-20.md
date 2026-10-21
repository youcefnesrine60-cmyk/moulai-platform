# Render startup failure: deployed commit 7a66763

Date: **2026-10-20**. Scope: targeted source and existing-evidence review.
No application change, live database connection, migration, Render action,
deployment, merge or push was performed. K9/K10 remain closed.

**Operator confirmation received:** Render uses database `neondb` on endpoint
`ep-billowing-term-as9aufue`; the complete ten-object startup failure list is
now available. These values match the recorded production mapping. Findings
below distinguish this supplied Render evidence from historical SQL observations.

## Confirmed cause

The operator reports Render running commit
`7a667633f593afbabc9949cef12f603535eba94e` from `main`, with
`APP_ENV=development`, `DATABASE_TARGET=primary` and
`database_schema_requires_migration` during FastAPI startup.

That exact commit was inspected with Git, without importing the application:

- `app/core/database.py:87–119`: `_engine_configuration` selects
  `DATABASE_URL` whenever the target is `primary`. `APP_ENV=development` alone
  does not select `TEST_DATABASE_URL`.
- `app/core/database.py:203–224`: `_validate_schema` inspects table and column
  names against registered ORM metadata, logs `missing_objects` and raises
  before startup completes. It neither migrates nor creates missing objects.
- `app/main.py:103`: the lifespan calls `init_db` before registering callbacks.
- The validator checks object presence, not the installed Alembic revision,
  types, constraints or the complete identity of a primary Neon connection.

The confirmed failure is therefore **a mismatch between the deployed ORM
contract and the schema visible through Render's primary connection**.
It is not a failure of the undeployed K9/K10 tenant foundation. A successful
database inspection also distinguishes this failure from an initial network,
credential or application-import error.

`primary` identifies a configuration setting. The operator has now confirmed
the actual database name and endpoint in Render, matching the expected
production destination. No new server-side identity query was executed.

## Precise schema prerequisites and migration attribution

Static analysis of the deployed models, including inherited timestamp columns
and the Core association table, found **46 business tables and 392 columns**.
The full object-name inventory is retained locally under
`artifacts/render-diagnostic-20261020/deployed-model-columns.json`.

The deployed main migration history contains 16 revisions and ends with:

```text
6bf21d4a8c30 -> a91e7c2b4d10 -> c413b7918a20
```

It contains no tenant E1 revision. The independent test history ends at
`dce91870b4a2` in that commit; its revision IDs must not be substituted for
main-history IDs.

The existing production preflight records `neondb` at `a91e7c2b4d10`:

| Object | Historical production result | Main-history attribution |
| --- | --- | --- |
| `admins.auth_subject` | Missing | `c413b7918a20` |
| `payments.payment_provider` | Missing | `c413b7918a20` |
| `payments.currency` | Missing | `c413b7918a20` |
| `manual_payment_receipts`, `manual_payment_audit` | Present; strict adoption contract passed at that observation | Created or validated/adopted by `c413b7918a20` |
| Administrative RBAC | Recorded ready | `a91e7c2b4d10` adds roles, permissions, role-permission links and `admins.role_id` |

Thus **`c413b7918a20` is the known deferred migration in the recorded production
state**, explaining those three absent columns, which the October 20 Render
log also lists. The actual current Alembic row remains historically reported,
not freshly queried; column absence alone does not independently prove its value.

The complete supplied failure list maps as follows:

| Missing object | Attribution in the deployed commit |
| --- | --- |
| `admins.auth_subject` | Added by main revision `c413b7918a20`. |
| `payments.payment_provider` | Added by main revision `c413b7918a20`. |
| `payments.currency` | Added by main revision `c413b7918a20`. |
| `features.created_at` | Inherited ORM timestamp; no corresponding main-history addition. |
| `multi_restaurant_discounts.created_at` | Inherited ORM timestamp; no corresponding main-history addition. |
| `users.created_at` | Inherited ORM timestamp; no corresponding main-history addition. |
| `users.updated_at` | Inherited ORM timestamp; `users` is absent from revision `888e43fc4f9b`'s table list. |
| `feature_pricing.created_at` | Inherited ORM timestamp; no corresponding main-history addition. |
| `loyalty_discounts.created_at` | Inherited ORM timestamp; no corresponding main-history addition. |
| `promotions.created_at` | Inherited ORM timestamp; no corresponding main-history addition. |

**Three columns are covered by the deferred billing migration; seven are a
legacy-schema coverage gap.** The first main revision assumes these legacy
tables already exist and only creates the four agent tables; its synchronization
name does not mean it adds every inherited column. The later general timestamp
revision adds `updated_at` to its explicit list, not all missing `created_at`
columns, and omits `users` entirely.

The independent test baseline `ae6a266365fb` creates all seven timestamps. This
explains why the complete development/test schema and passing local campaigns
do not imply that the older production schema is compatible. No K9/K10 change
is required to diagnose or explain this failure.

Applying only `c413b7918a20` would leave the seven timestamp omissions and the
startup rejection. If production must be aligned later, prepare a separate
forward repair for those seven fields, choosing defaults/nullability and any
historical-data treatment explicitly. Do not invent historical creation times
by treating migration time as known event time. No repair revision was created;
no migration was executed, replayed or stamped during this diagnosis.

## Confirmed connection and evidence boundaries

Expected production mapping, from the approved project records:

- Project: `shiny-lab-60817779`.
- Branch: `production`, `br-plain-firefly-as17il6w`.
- Recorded production endpoint: `ep-billowing-term-as9aufue`.
- Database: `neondb`.

Expected development mapping:

- Branch: `development`, `br-lively-truth-asga1dtk`.
- Endpoint: `ep-quiet-rain-assrs0gv`.
- Database: `neondb_test`.

The October 18 read-only development inventory records `dce91870b4a2` and
47 public tables. Comparing its column names with the exact deployed models
found **no missing column**: all 392 business columns are present, with
`alembic_version` accounting for the extra table/column. The earlier October 15
read-only development startup also passed. These observations support the
development-target option; they do not establish its current unchanged state.

Render's supplied configuration confirms the production database/endpoint,
rather than the development endpoint above. No full connection URL, username
or password was requested or supplied. The remaining prerequisite before a later
production repair is a current read-only revision/catalog inventory and recovery
check, not another inference from `APP_ENV` or a request for connection secrets.

## Safest resolution and authorization boundaries

**Recommended for the current development-stage service:** prepare an explicit
Render development target, preserving the production `DATABASE_URL` unchanged.
Before applying it, revalidate the current read-only development schema and
immutable target identity against this deployed commit and the now-known
missing-object list.
Then use the existing central configuration contract:

| Setting | Proposed development value |
| --- | --- |
| `APP_ENV` | `development` |
| `DATABASE_TARGET` | `development` |
| `TEST_DATABASE_URL` | Real development/neondb_test asyncpg connection, entered privately in Render |
| `TEST_DATABASE_PROJECT_ID` | `shiny-lab-60817779` |
| `TEST_DATABASE_BRANCH_ID` | `br-lively-truth-asga1dtk` |
| `TEST_DATABASE_ENDPOINT_ID` | `ep-quiet-rain-assrs0gv` |
| `PROTECTED_DATABASE_BRANCH_ID` | `br-plain-firefly-as17il6w` |
| `PROTECTED_DATABASE_ENDPOINT_ID` | Reconfirmed production endpoint; recorded `ep-billowing-term-as9aufue` |
| `DEBUG`, `DB_ECHO` | `false` |

No OIDC setting, Telegram setting or primary connection is changed by this
proposal. Apply no configuration until the user approves the exact Render
changes; obtain separate approval for the deployment action. No new Neon
migration is implied by choosing an already compatible development schema.

**Alternative if primary production must remain the runtime target:** keep the
service stopped until a targeted, separately approved production-schema repair
has been prepared from the exact current inventory. At the recorded parent,
the manual-billing successor is `c413b7918a20`, and the seven timestamp fields
need a separate forward repair. Reconfirm recovery readiness and permission/financial
impact before seeking execution authorization. Migration approval does not
authorize a later deploy or real identity association.

Do not run a generic `upgrade head` from the newer feature checkout: its history
also contains E1, outside this deployed commit and this diagnosis. Do not use
`stamp`, `create_all`, ignored validation failures or disabled startup checks.
Changing `APP_ENV` alone cannot correct the selected database/schema mismatch.

**Conclusion:** the supplied Render configuration matches the expected
production database and endpoint. Its schema lacks three deferred billing
columns and seven legacy timestamps required by the deployed models. Prepare
the already-approved development target as the safest deployment option; any
production alignment needs both the billing successor and a separately reviewed
timestamp repair. No environment change, migration or deployment was executed.
