# Catalog authorization and tenant isolation

Review updated: 2026-10-16.

The catalog authentication and tenant-isolation finding recorded on 2026-10-13
has been remediated in the API, business, and SQLAlchemy session boundaries.
This supersedes the earlier statement that catalog administration was public.

## Verified identity and SQL scope

- Products, categories, option groups, and product options require the existing
  trusted Keycloak owner dependency for every administrative HTTP operation,
  including list, search, count, summary, and related-resource reads.
- Their service constructors require a keyword-only `owner_id` and bind the
  SQLAlchemy session to that identity. Rebinding a session to a different owner
  is forbidden. A request parameter cannot select the authenticated owner.
- The session guard applies owner predicates to ORM reads and bulk writes,
  including relationship loads and aggregates. Before flushing, it validates
  pending catalog rows and their parent relationships before emitting writes.
- The group ownership chain is
  `OptionGroup -> Product -> Restaurant -> Owner`. Product-option ownership adds
  `ProductOption -> OptionGroup` to that chain. A foreign identifier is hidden
  with HTTP 404 rather than exposing another owner's record.
- Category and product creation check their restaurant relationship before any
  write. Product creation and category changes also verify that the category
  belongs to the product's restaurant. Reordering validates the complete set
  before updating its first member.

The implementation is in
[`tenant_scope.py`](../app/core/security/tenant_scope.py) and the four catalog
routers and services. Existing trusted Telegram menu reads continue to use their
explicit selected-restaurant repository contracts; they do not become global
public catalog-administration endpoints.

## Regression verification

The following tests exercise the actual implementation:

- [Authentication contracts](../tests/api/unit/business/test_catalog_authorization.py)
  reject missing bearer credentials before database access, including unfiltered
  lists and searches.
- [Business membership checks](../tests/api/unit/business/test_catalog_membership.py)
  prevent partial reordering when a later member is invalid and reject product
  categories from another restaurant before writes.
- [Relational HTTP checks](../tests/api/unit/business/test_catalog_sqlite_authorization.py)
  run real routers, services, repositories, and owner-scoped SQL against two
  owners in disposable in-memory SQLite databases. They cover list/search totals,
  foreign reads, updates, deletion, creation through foreign parents, mixed-owner
  reorder batches, and legitimate updates by the correct owner. Mutation tracing
  verifies that denied operations emit no SQL insert, update, or delete.

The SQLite adapter preserves SQLAlchemy session events and relational queries.
It does not test asyncpg, PostgreSQL locking, or production data. A PostgreSQL
deployment rehearsal remains a separate environment-specific validation step.

## Operational limits

Real Keycloak issuer, audience, JWKS configuration, and verified stored identity
bindings remain prerequisites for operational access. The routes fail closed
when trusted authentication is unavailable. This review creates no identity,
changes no administrator permission, and performs no production migration.

This catalog remediation does not certify the entire application or replace
the independent manual-payment review and deployment safeguards. Current test
execution and coverage results are documented in [API testing](api-testing.md).

## A2 + A5 follow-up — 2026-10-22

The [targeted follow-up](catalog-a2-a5-validation.md) confirms the tested historical
authentication and owner-isolation fixes. It separately reproduces partial
commits in bulk creation/reordering and two failing summary response contracts.
Its initial result was FAIL pending reviewed corrections; the earlier
authentication finding was not reopened. Following authorization, the targeted
correction passed **505 offline cases and 21 disposable local PostgreSQL cases**,
with zero failures or skips. The current focused result is **PASS**. The report
retains the original reproductions and limits; no Neon or production operation
was performed.
