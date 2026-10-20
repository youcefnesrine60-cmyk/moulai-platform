# API authorization boundaries

The REST API uses verified Keycloak access tokens and persisted identity
bindings. Client-supplied identifiers select resources; they never authenticate
an owner or administrator. Missing Keycloak settings keep sensitive operations
unavailable. This review creates no identity bindings, roles, or production
permission grants.

K8 adds opt-in local OIDC diagnostics without changing the business dependency
graph or granting tenant access from realm roles. Its loopback HTTP exception
does not apply to business authentication. See
[K8 validation](keycloak-k8-validation.md) for configuration and evidence.

## Access policy

| Resource | Required identity and boundary |
| --- | --- |
| Products, categories, option groups, product options | Verified owner; ownership follows the restaurant and immutable parent relationships. |
| Agents, channels, conversations, messages | Verified owner; ownership follows restaurant, agent, channel, and conversation relationships. |
| Standalone branches | Verified owner; restaurant ownership is checked before feature access and usage operations. |
| Restaurant administration aggregate | Verified administrator with `restaurants.manage`; covers global restaurant CRUD, groups, associated branches, metrics, counters, and payment configuration. |
| Global Telegram user registry | Verified administrator with the existing `admins.manage` permission. |
| Administrative sessions | Verified administrator with `admins.manage`; session credentials are additional lookup data. |

The user registry has no restaurant ownership or Keycloak customer-subject
mapping. Its identifiers and Telegram chat identifiers therefore cannot grant
customer self-service access. The administrative REST boundary does not change
the bot's internal user registration and consent workflows.

The restaurant aggregate accepts explicit owner selection and exposes global
operational administration. It is now administrator-only. Owner-facing order,
billing, catalog, agent, and standalone branch APIs keep their own scoped
contracts. The synthetic metrics simulation router is no longer registered in
the application. Existing restaurant database business tests substitute a
trusted administrator only in their directory-local client fixture; the
separate security suite tests the real administrative identity and permission
dependencies. The initial authorization review was offline; the subsequent
category and branch integration follow-up is recorded in
[API testing](api-testing.md).

Existing owner, order, payment, subscription, manual-review, and administrative
routes retain their established identity and permission checks. Administrative
permission decisions use the persisted administrator and role state rather
than trusting role names supplied by a client.

## Owner-scoped units of work

`get_owner_tenant_db` binds the request's existing SQLAlchemy session to its
verified owner. Catalog, agent, and standalone branch service constructors
require that owner explicitly and reinforce the same binding. A session cannot
switch owners. There is no public unbind operation.

Binding performs no SQL and is safe in synchronous service constructors that
receive an `AsyncSession`. A first binding requires a clean unit of work;
pending additions, changes, or deletions are rejected before installing the
scope. Clean cached tenant instances are detached so subsequent `Session.get`
calls must query with the owner predicate. Rebinding to the same owner is
idempotent and preserves pending changes within an already scoped session.
Callers must bind before changing tracked objects.

The session-local guard applies predicates to ORM entity and scalar reads,
aliases, counts, searches, relationship loads, and set-based updates and
deletes. It does not install listeners on other sessions. Public bot menu reads
keep their separate, explicit restaurant contracts through trusted internal
repositories.

Filtered aggregates preserve their explicit mapped `FROM` when SQLAlchemy's
statement traversal deduplicates it against a table referenced by a filter.
An ORM attribute in `WHERE` alone does not authorize a raw Core projection.
The regression suite checks both legitimate filtered counts and rejected raw
table/alias escape attempts.

The flush guard validates the complete pending batch before SQL writes. New
parents must already exist in the owner's scope. Parent ownership cannot be
changed on existing resources. A product category may change only within the
same restaurant. A conversation's channel must belong to its exact agent.
Direct ORM relationship reassignment is rejected in favor of validated parent
identifiers.

Raw SQL, unmapped protected tables mixed into ORM queries, bulk ORM inserts,
executemany updates by primary key, and set-based ownership changes are
rejected in these scoped sessions. Supported bulk mutations inherit an owner
predicate; mixed agent identifiers affect only owned rows and report the
actual affected count. Catalog reorder operations validate the entire list
before changing any row.

Branch activation checks subscription entitlements and capacity, including
reactivation of an existing branch. Branch transitions and usage changes share
one transaction; repeated activation or deactivation does not change usage
again. The service acquires the owned restaurant lock before the branch lock.
Rollback is verified locally; PostgreSQL concurrent locking is not certified
by SQLite tests.

These controls are application authorization for the guarded repositories.
They are not PostgreSQL row-level security and do not restrict a separately
privileged database connection. Trusted internal code remains responsible for
using the appropriate service and session boundary.

## HTTP behavior and credentials

Unauthenticated requests fail before business operations. A valid identity
without the required binding or administrative permission is denied. Foreign
resources are hidden with `404`; invalid same-owner parent relationships are
rejected with `422`. Missing trusted identity-provider configuration does not
enable a development authentication bypass.

Intentional HTTP authorization exceptions retain their status across router
error handling. Session credentials use headers on static URLs; see the
[administrative session contract](admin-session-api.md). Telegram and Keycloak
identities remain separate. No `admin_id`, owner identifier, or chat identifier
substitutes for a signed, verified access token.

## Verification and operational limits

Offline HTTP contracts assert rejection before service calls. Disposable
SQLite tests additionally execute real routers, business services,
repositories, owner predicates, flush events, and persistence. The shared
integration fixtures are not loaded, and the test runner blocks monitored
external Python socket operations.

These tests do not execute PostgreSQL migrations, certify PostgreSQL locking,
repair historical production relationships, configure Keycloak, or verify a
deployed proxy. See [API testing](api-testing.md) for the accepted execution,
coverage, and evidence. Agent state persistence is documented separately in
[agent API security](agent-api-security.md).
