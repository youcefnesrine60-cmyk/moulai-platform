# K9 — Organizations / Tenant Mapping: Closure

Date: **2026-10-19**. Official status:
**CLOSED — Foundation & Functional Tenant Reads Validated**.

The user has accepted K9 for the developed and tested scope. This is the final
closure record; it introduces no new validation campaign or operational action.

## Accepted scope and evidence

- Issuer-qualified Identity, Organization, OrganizationMembership, tenant roles,
  explicit permissions and immutable TenantContext, with their PostgreSQL models,
  repositories and services. Keycloak authenticates; PostgreSQL is the authority
  for company membership, business permissions and resource access.
- E1 migration on isolated W, empty-foundation downgrade and **12 PostgreSQL
  scenario groups passed**: constraints, triggers, owner invariants, concurrent
  transactions and organization isolation. **219 offline tests** also passed.
- Functional `TenantAccessService` reads for personal memberships and authorized
  restaurants, reusing existing authorization logic. Optional FastAPI
  dependencies remain unwired to existing routes. The latest functional
  validation recorded **41 passing tests**.
- G2 evidence retains the initial comparator failure, its exact-trigger
  allowlist correction and the successful independent read-only preservation
  check. The original failed runner result remains part of the record.

The [G2 results](keycloak-k9-g2-postgres-validation.md) and
[functional delivery](tenant-functional-integration.md) retain the detailed
results and evidence links. Code, tests and evidence are preserved; none was
rerun or regenerated for this closure.

## Deferred scope and validation limits

- Integration and activation of authorization on existing business routes.
- Controlled linking of Keycloak users to local identities; no automatic
  association of `owner-test` or another real user.
- Production migration and multi-tenant cutover.
- Production security configuration, reserved for **K11**.
- Platform deployment.

These boundaries do not reopen the accepted K9 scope. The PostgreSQL baseline
contained empty business tables, so it does not establish preservation of
representative populated financial history. V proves that an independent
reference is readable and equivalent to B, not recovery after an incident.

## Existing temporary-resource commitments

| Resource | Existing deadline or retention, UTC |
| --- | --- |
| W | Automatic expiration: **2026-10-20 08:32:04**. |
| V | Automatic expiration: **2026-10-20 08:32:58**. |
| B | No automatic expiration; mandatory review: **2026-10-22 08:25:35**. |

The exact resource identities and custody requirements remain in the
[G2 custody record](keycloak-k9-g2-postgres-validation.md#6-temporary-resource-custody-after-g2-acceptance).
No new Neon operation, deletion, expiration change or reminder is scheduled.
Manual cleanup remains subject to separate authorization.

## Official transition

Next step: **K10 — Authorization MoulAI™**. Status: **NOT STARTED**.
K10 implementation awaits validation of this closure report and its own scope.
This closure authorizes no database change, OIDC activation, deployment or push.
