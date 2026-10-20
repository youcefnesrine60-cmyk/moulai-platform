# K9.2-B1 — Tenant foundation implementation and validation

Date: 2026-10-18. Status: **B1 complete within its preparatory scope; B2 awaits
separate authorization**. Architecture B remains the approved direction.

## 1. Scope and exact file inventory

No existing source or configuration file was modified. SHA-256 comparisons
against the pre-B1 working tree verify preservation of existing files, including
authentication, payments, Restaurant/group mappings, startup imports, migration
histories, `.env`, `.env.example` and requirements. Preexisting uncommitted work
was preserved; the [scope verification record](../artifacts/keycloak-k9-b1/scope-verification.json)
records the comparison of 527 existing files. The following eleven repository
files were added:

| File | Purpose |
| --- | --- |
| [tenant_types.py](../app/core/security/tenant_types.py) | Closed role/scope vocabulary, 27-code catalogue, role validation ceilings and domain failures. |
| [tenant_context.py](../app/core/security/tenant_context.py) | Frozen/slotted internal context with a process-local issuance proof and immutable collections. |
| [tenant package initializer](../app/models/tenant/__init__.py) | Opt-in package; no startup export or DDL execution. |
| [tenant schema](../app/models/tenant/schema.py) | Nine typed SQLAlchemy models, constraints, reference contracts and ORM immutability/history protections. |
| [tenant_repo.py](../app/repositories/tenant_repo.py) | Explicit BASE SELECT projections, exact identity lookup, company-qualified membership queries, locks, CAS revocation and flush-only audit. |
| [tenant_foundation.py](../app/services/business/tenant_foundation.py) | Owned unit of work, identity/context resolution, current-state authorization, restaurant scope and bounded non-owner revocation. |
| [foundation test runner](../scripts/run_tenant_foundation_tests.py) | Offline guard, disabled conftest/autoload, warnings as errors, focused evidence and coverage. |
| [foundation tests](../tests/test_tenant_foundation.py) | Executed memory SQL constraints, same-owner company isolation, lifecycle denial, immutable context and atomic rollback. |
| [mocked OIDC tests](../tests/test_tenant_foundation_oidc.py) | Real ephemeral RS256 signatures and simulated JWKS through the unchanged business verifier. |
| [E1 SQL proposal](keycloak-k9-e1-proposal.md) | Review-only PostgreSQL DDL, optional existing-table expansion and lifecycle-enforcement review gates. |
| This report | Observed validation, implemented boundaries, limitations and B2 plan. |

Generated local evidence is centralized under
[artifacts/keycloak-k9-b1](../artifacts/keycloak-k9-b1/). The existing offline
runner also writes its normal named regression artifacts under
`artifacts/api-test-review`. No results were added to the project root.

Complete copyable versions of all nine new Python files are available in the
[source document](../artifacts/keycloak-k9-b1/complete-python-sources.md),
[source archive](../artifacts/keycloak-k9-b1/b1-python-sources.zip) and
[source manifest](../artifacts/keycloak-k9-b1/source-manifest.json).

## 2. Models, constraints and migration status

| Model | Implemented contract | Not asserted by B1 |
| --- | --- | --- |
| Identity | Exact case-sensitive `(issuer, subject)` unique key; bounded ASCII validation; business HTTPS issuer; explicit status/revision; suspended default; ORM immutable keys and retained history. | No live enrollment/linking, issuer backfill or installed PostgreSQL immutability trigger. PostgreSQL ASCII CHECK is compiled, not executed. |
| Organization | Local stable ID, name, explicit lifecycle/revision, draft default; active requires enforcement timestamp; ORM rejects resetting an existing timestamp. | No actual company created/activated, cutover or company recovery workflow. |
| OrganizationMembership | Unique company/identity; checked role/scope/status; owner company-wide; required acceptance/activation evidence; revisions/generation; immutable endpoints; RESTRICT FKs. | No owner promotion, re-enrollment, activation or transfer service. Cross-row last-owner database enforcement is not installed. |
| TenantRole | Separate checked owner/manager/employee codes and policy revision. | No live role/policy provisioning or change to platform roles. |
| TenantRolePermission | Explicit composite-key rows and per-role permission ceilings; no wildcard/platform code acceptance. | Catalogue ceilings never become granted permissions automatically. |
| MembershipRestaurantGrant | Unique membership/restaurant; explicit-only mode; composite membership/company/mode and restaurant/company FKs. | Restaurant's future company column is a schema reference contract; its live ORM mapping is unchanged. |
| MembershipChangeProposal | Company-qualified actor/target references, revisions, enrollment generation, role/mode and expiry/application fields; checked actor kinds and immutable ORM intent fields. | No proposal acceptance/sealing, escalation, owner-transfer or automatic invitation processor. |
| MembershipProposalRestaurant | Normalized proposed restaurant set with unique pairs and company/mode composite FKs. | Complete sealed-graph immutability and acceptance validation remain prerequisites for a future proposal processor. |
| TenantAuditEvent | Company-qualified actor/target, previous/resulting revisions, generation, reason/correlation ID and bounded policy snapshots; ORM update/delete rejection. | SQL-level append-only privileges/triggers and every later governance event type need PostgreSQL implementation/review. |

All new authorization FKs use RESTRICT rather than destructive cascades. New
lifecycle timestamps are timezone-aware. Model-level relationships are expressed
as foreign keys with explicit repository queries; no delete-orphan relationships
or implicit relationship IO were introduced.

Every constraint is currently **a model/test/schema-review contract**, not an
installed change to Neon. SQLite executes compatible FK/unique/CHECK constraints.
The PostgreSQL dialect compiles the proposed DDL; this does not validate a live
PostgreSQL schema, functions, privileges or concurrent locking.

### Metadata compatibility decision

The existing declarative registry is reused, with separate preparatory metadata
on an abstract TenantBase. Existing Base.metadata, model exports and application
startup stay unchanged. SQLAlchemy supports alternate metadata on abstract
declarative hierarchies.
[Source: SQLAlchemy declarative metadata](https://docs.sqlalchemy.org/en/20/orm/declarative_config.html#metadata).

The partial `restaurants` and `admins` declarations are explicit future FK
reference contracts, not alternate ORM mappings or tables to create in E1.
Only memory tests create them as fixture tables. Never run create_all on this
metadata against a deployed database. A future revision must explicitly select
new objects and reviewed existing-table additions. B2 must decide how Alembic
will assemble the target schema without duplicate table definitions; blindly
concatenating the two metadata objects would be unsafe.

This staging avoids mapping a nonexistent organization column into every current
Restaurant SELECT. Tests verify the shared registry configures successfully,
legacy Restaurant still contains `group_id`, and its current mapping has no
organization column. Canonical grouping is not converted during B1.

## 3. Services and authorization behavior

No package is wired into FastAPI dependencies, route registration, Telegram,
startup, authentication or payment processing. Existing public routes retain
their current protections. The foundation has no provisioning API, deployment
hook or executable migration entry point.

- IdentityService accepts an internal, already verified OIDCPrincipal and finds
  an existing active exact pair. It does not verify a raw HTTP payload or create
  an identity. The future HTTP adapter must reuse the existing trusted verifier.
- TenantContextResolver discovers lock targets, then locks/reloads role,
  Identity, company and membership. It requires accepted active membership,
  active enforced company and a qualifying active owner. Unknown associations,
  missing policy authority or changed targets never get an owner-derived fallback.
- Frozen/slotted TenantContext has frozenset permissions/grants and version
  snapshots. Its constructor requires a nonserializable internal issuance proof;
  raw HTTP data cannot construct one. This is an internal programming boundary,
  not a sandbox against malicious code running inside Python.
- TenantAuthorizationService rechecks persisted states, roles, revisions,
  permissions and grants inside the owned transaction. Restaurant equality is
  tested by company even when A and B have the same legacy owner. Empty explicit
  grants produce a false restaurant predicate and no restaurant access.
- tenant_unit_of_work begins before database resolution, rejects autobegun or
  pending work and owns commit/rollback. Session binding cannot switch company,
  actor or read/governance mode. Repositories never commit independently.
- MembershipService implements only owner-authorized non-owner revocation.
  CAS revision checks, grant removal and audit share a savepoint and outer
  transaction; an audit failure or later outer failure restores the old state.
  Owner targets, foreign targets, employees and managers are rejected. Owner
  changes deliberately have no service method in B1.

The permission catalogue is disjoint from platform RBAC. Stored rows are the
authority; empty policy rows grant nothing. Per-role ceilings reject corrupt
escalated assignments rather than supplying defaults. `tenant.orders.fulfill`
is removed from resolved permissions and explicitly denied for **every role**
until approved transition mapping exists. No employee fulfillment route exists.

Payment, receipt approval, subscription activation, identity-linking and platform
administrator dependencies remain byte-for-byte unchanged. No `owner-test`
association or real tenant was created; a synthetic unknown-subject test verifies
that such a login does not create a local record.

## 4. Observed test results

Both runs install the existing socket audit guard before application imports,
disable shared conftest loading and reject warnings. No production/development
database connection or real Keycloak request is required. The tests generate
only ephemeral RSA keys/tokens in memory.

| Verification | Observed result |
| --- | --- |
| Focused B1 runner | **84 passed**, zero warnings, zero network-denial events, shared conftest not loaded. |
| Initial B1 full available offline regression | **2,403 passed**, plus **128 passed subtests**, zero warnings, zero network-denial events. Preserved historical evidence; not rerun for the standards correction. |
| B1 application modules, focused line coverage after standards correction | **96.31%**: 391 covered statements of 406; six new application files only. |
| Entire app, initial B1 offline regression line coverage | **58.47%**: 12,836 covered statements of 21,955; all 391 application Python files included at that run. |
| API, separate initial B1 offline line coverage | **81.64%**: 3,699 covered statements of 4,531 across 56 files. |
| Ruff and Black, new Python sources | Checks pass. |
| ORM compatibility / PostgreSQL DDL | Shared registry mapper configuration and PostgreSQL compilation pass. |

Focused evidence: [results](../artifacts/keycloak-k9-b1/validation.json),
[test log](../artifacts/keycloak-k9-b1/foundation-tests.log),
[coverage](../artifacts/keycloak-k9-b1/foundation-coverage.json).
Regression evidence:
[results](../artifacts/api-test-review/k9-b1-regression-results.json),
[log](../artifacts/keycloak-k9-b1/offline-regression.log).

The historical 64% figure came from a different full-suite scope, including
database integration, before these additional source files. It is not a directly
comparable baseline for this offline-only run. No PostgreSQL integration tests
were rerun because B1 forbids Neon writes. Neither source denominator was reduced
to make a threshold pass; the current offline app and API measures exceed 50%.

### What the fixtures prove and do not prove

Disposable SQLite memory databases enforce FKs and real SQLAlchemy transactions
and savepoints. A test-only AsyncSession subclass uses public run_sync to execute
buffered SQLite results without adding a new async SQLite dependency. It is a
unit bridge, not asyncpg or PostgreSQL driver evidence. SQLAlchemy documents
run_sync as its bridge for synchronous session operations.
[Source: SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#running-synchronous-methods-and-functions-under-asyncio).

Tests cover same-owner A/B separation, exact/empty grants, explicit permission
denial, no provisioning from roles/subjects, invalid issuer/subject input,
cross-company constraints, immutable keys/context, policy/state revisions,
proposal actor/target constraints, ORM audit protection and transaction rollback.
The existing HTTPS JWT verifier is separately exercised with simulated JWKS for
valid, expired, wrong-signature, wrong-issuer/audience, absent-subject and absent
credentials cases, while both diagnostic switches remain false in that runner.

The network guard observes Python socket audit events, not OS-level isolation.
No denied event was recorded, which means no covered operation attempted those
network paths. Existing regressions involving PostgreSQL are explicitly excluded
by the offline runner; a pass here is not proof of their execution.

### Standards correction after B1 review

The supplied IDE diagnostics contained 147 MD010 findings, all caused by hard
tabs in compiled SQL indentation in the E1 proposal. They were replaced with
spaces without changing SQL tokens or executing SQL.

All nine B1 Python files were reviewed. The correction adds uniform section
titles before all 89 function/method definitions, completes 37 missing
docstrings, and provides explicit BASE SELECT helpers for role, permission,
grant, restaurant-company and active-owner projections. Existing company,
membership, status and permission predicates remain in place. Imports, complete
function annotations and keyword-only repository/service parameters are checked.
SQLAlchemy event/validation callbacks and framework callbacks retain their
required positional signatures.

The focused suite was rerun after these changes: 84 tests passed, zero warnings
and no network attempt detected. Ruff and Black pass. The earlier full-suite
and global/API coverage results above remain dated initial-B1 evidence; they
are not presented as a new run against the standards correction. Complete
source exports and their hashes were refreshed. The
[standards verification record](../artifacts/keycloak-k9-b1/standards-review.json)
captures the final structural checks and change scope.

## 5. Remaining limitations and security gates

1. **No deployed schema or access conversion.** New services require the reviewed
   E1 schema. They are preparatory, not a claim that the current application's
   tenant migration is complete. Do not connect them to existing routes yet.
2. **Cross-row database lifecycle guards.** Last-active-owner constraint triggers,
   SQL immutability and append-only runtime privileges are review requirements.
   ORM events do not cover all bulk/direct SQL paths. Read-side active-owner
   checks and refusing owner mutations reduce B1 scope but do not replace those
   database guarantees.
3. **Concurrency.** Shared/exclusive row locks are emitted by repositories;
   SQLite does not exercise PostgreSQL lock conflicts. Concurrent revocation,
   last-owner changes, deadlock handling and bounded retries require B2/next-stage
   PostgreSQL tests before relevant mutation paths are exposed.
4. **Proposal processing.** Models store checked intent and normalized target
   sets. No acceptance, sealing, promotion, re-enrollment, scope elevation,
   initial-company bootstrap or ownership-transfer processor is implemented or
   exposed. Complete immutable-graph and lifecycle rules remain review gates.
5. **Resource-wide enforcement.** A scoped restaurant predicate and foundational
   membership checks are not a universal session guard for every legacy entity.
   Orders, billing, metrics, exports, customers, groups and alternate entry points
   need the design's explicit conversion inventory and cutover barrier later.
6. **Financial eligibility and global RBAC.** Holding a tenant permission does not
   replace legacy payer checks or authorize receipt review. B1 intentionally has
   no payment adapter, automatic administrator link or tenant-to-platform grant.
7. **No automatic policy provisioning.** Tests contain synthetic fixture policies.
   No live roles, permission rows, identities, links or memberships were seeded.
   Future provisioning needs exact reviewed rows, preserving platform tables.
8. **Identity registration/linking.** No enrollment/linking service has been added.
   Missing associations deny. Review concrete issuer provenance and explicit
   operator/target approvals before creating any association, including owner-test.

Local `.env` remains unchanged, with `OIDC_DIAGNOSTICS_ENABLED=false` and
`OIDC_ALLOW_LOCAL_HTTP=false`. No actual diagnostics listener was enabled. The
ordinary existing K8 regression fixtures can vary isolated in-memory settings;
that does not change the user's application configuration or start a live server.

## 6. Precise K9.2-B2 plan — separate approval required

1. Validate B1 and the [E1 review proposal](keycloak-k9-e1-proposal.md). Decide
   the exact existing-table additions and metadata/autogenerate integration;
   review nullable profile columns separately from any actual profile linking.
2. Authorize **creation** of an E1 Alembic revision on the correct existing
   migration chain. Review generated SQL and explicit guards, policy rows,
   constraint/index names, lock impact and transaction boundaries. Reject
   unrelated schema drift. No identity/company seed or backfill belongs to E1.
3. Authorize the exact isolated rehearsal target independently. Pass fail-closed
   project/branch/endpoint and actual `neondb_test` attestation with the existing
   [preflight implementation](../app/core/test_database.py). A missing proof,
   production endpoint or fallback to DATABASE_URL must refuse execution.
4. Obtain baseline schema/data/financial/RBAC comparisons and reviewed recovery
   evidence before upgrade. Use only approved isolated fixtures; no reset,
   destructive recreation or production operation follows from B1 approval.
5. Execute the separately approved E1 rehearsal and inspect installed CHECK/FK,
   unique constraints, privileges, defaults and triggers. Run real asyncpg tests
   for FK bypass attempts, atomic audit failure, owner/revocation races and lock
   behavior. These results must be reported as new evidence, not inferred from
   the B1 SQLite pass.
6. Rehearse rollback/recovery without losing existing data. Keep companies
   unenforced, grouping unchanged and routes under their current guards.
   Report exact starting/ending revisions, data integrity and remaining risks.
7. Submit that report before any backfill, live identity association, company
   activation, route conversion, production migration or external deployment.

**Stop point:** B1 ends here. No Alembic revision has been created or executed;
no Neon writes, Keycloak/Render/Telegram changes or GitHub push occurred.
