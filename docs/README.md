# MoulAI documentation

English is the standard language for documentation in this directory. Write new
documents and maintain existing ones in English, including headings, tables,
instructions, and human-facing comments or prompts in examples.

Keep source identifiers, paths, configuration keys, protocol values, hashes,
timestamps, and recorded results unchanged when translating or editing. A
historical verification result must retain its date and scope; translating a
report does not rerun its checks or authorize an operational action.

## Document index

- [GitHub backup preparation](github-k10-backup-preparation.md): reviewed K8/K9/K10
  source inventory, local feature-branch commit, secret checks and the separate
  approval required before publication.
- [K10 authorization validation](keycloak-k10-validation.md): **CLOSED —
  Authorization Validated** for isolated HTTP routes and real local E1
  PostgreSQL; existing business routes and production activation remain deferred.
- [Local PostgreSQL tests](local-postgres-tests.md): 110 formerly skipped cases
  accepted on 2026-10-20 as resolved, with independent local admission and
  preserved Neon protections. The [development guide](billing-development-verification.md)
  defines the three approved environments.
- [K9 official closure](keycloak-k9-closure.md): **CLOSED — Foundation & Functional
  Tenant Reads Validated**; accepted scope, remaining limits and transition to
  K10 — Authorization MoulAI™, the next approved implementation step.
- [Keycloak K8 validation](keycloak-k8-validation.md): shared JWT validation,
  protected local diagnostics, automated evidence and the boundary before K9.
- [K8 final end-to-end validation](keycloak-k8-final-e2e.md): observed real-user
  PKCE login and local HTTP 200/200/403/401 results, with execution limits.
- [K9 E1 migration review](keycloak-k9-b2-migration-review.md): independent
  revision histories, additive tenant DDL, offline evidence and the separate
  approval gate before any PostgreSQL rehearsal.
- [K9 G2 PostgreSQL results](keycloak-k9-g2-postgres-validation.md): successful
  E1 round trip, twelve PostgreSQL scenario groups and final preservation on W.
- [Functional tenant reads](tenant-functional-integration.md): personal
  memberships, company-bound business reads and opt-in HTTP dependencies.
- [Architecture audit](order-architecture-audit.md): order architecture findings
  and the dated refactoring history.
- [Payment strategy](payment-integration-strategy.md): manual billing contracts
  and boundaries for later provider integrations.
- [Development verification](billing-development-verification.md): recorded
  isolated-database checks, migration rehearsal, and local startup.
- [Operational runbook](billing-production-runbook.md): deployment, identity,
  migration, and recovery procedures with approval limits.
- [Catalog isolation finding](catalog-options-isolation-finding.md): corrected
  authentication and tenant boundaries, with relational verification scope.
- [Dependency review](dependency-review.md): reviewed package versions,
  compatibility decisions, and isolated checks.
- [PowerShell standards](powershell-standards.md): script conventions, process
  ownership, and isolated verification.
- [Project maintenance](project-maintenance.md): repository layout, local
  artifacts, cache policy, and retired entry points.
- [API testing](api-testing.md): offline HTTP contracts, full-source coverage
  accounting, and verification boundaries.
- [API authorization](api-authorization.md): owner isolation and administrative
  access policies for the reviewed REST resources.
- [Administrative session API](admin-session-api.md): credential headers,
  static lookup URLs, and client migration.
- [Agent API security](agent-api-security.md): owner boundaries and persisted
  conversation state and message content types.

## Reading the evidence

The project remains under development. Implemented features, pending work,
historical observations, and deployment authorization are distinct. Follow the
operational runbook before any action involving production data, administrative
identity, permission changes, or the live Telegram webhook.

Generated reports, source exports, and raw test captures are local files under
`artifacts/`, excluded from Git and Docker. Links to those artifacts in detailed
reports refer to the local checkout and may be unavailable on GitHub.

The local `artifacts/README.md` provides a central evidence index. Follow
[project maintenance](project-maintenance.md) when organizing generated output
or reviewing retired tools; recorded results remain tied to their original
source state and verification scope.
