# K9.2-B2 — E1 migration creation and static review

Date: 2026-10-18. Status: **revision files created; offline review passed;
database execution and PostgreSQL rehearsal are not authorized**.

This report follows the [detailed design](keycloak-k9-detailed-design.md),
[B1 validation](keycloak-k9-b1-validation.md) and
[E1 proposal](keycloak-k9-e1-proposal.md). It supersedes their revision-creation
gate only. It grants no database, deployment or company-cutover authorization.

## 1. Revision ancestry and applicable starting points

The two repository histories were inspected using Python AST, without importing
their environments or executing older revisions. They remain independent.

| History | Existing repository head | New E1 revision | Root and length after E1 |
| --- | --- | --- | --- |
| `alembic` | `c413b7918a20` | `e1a92b200001` | `17b6b58772b7`; 17 revisions |
| `alembic_test` | `dce91870b4a2` | `e1b92b200001` | `ae6a266365fb`; 4 revisions |

Main-history tail:

```text
6bf21d4a8c30 -> a91e7c2b4d10 -> c413b7918a20 -> e1a92b200001
```

Isolated-test history:

```text
ae6a266365fb -> b7d33e89f4a1 -> dce91870b4a2 -> e1b92b200001
```

There is one head per history, no cross-history parent and no merge revision.
Both E1 wrappers call the same frozen migration-only contract. Their compiled
upgrade bodies match exactly; their compiled downgrade bodies also match.

These are **repository revisions**, not verified current Neon revisions. The
last reported production version was `a91e7c2b4d10`; it was not queried again.
Moving from that version to the main E1 head would also traverse the manual
payment revision `c413b7918a20`. That predecessor changes financial structures
and requires its own existing approval gates. E1 approval must never be read as
permission to run the full chain, stamp a different baseline or skip a parent.

## 2. Exact repository file inventory

Nine files were added:

| File | Purpose |
| --- | --- |
| [Main E1 revision](../alembic/versions/2026_10_18_15_00_00_tenant_foundation_e1.py) | Main-history wrapper, parent `c413b7918a20`. |
| [Test E1 revision](../alembic_test/versions/e1b92b200001_tenant_foundation_e1.py) | Test-history wrapper, parent `dce91870b4a2`. |
| [Migration support initializer](../migration_support/__init__.py) | Dedicated migration-only package. |
| [Frozen schema and policies](../migration_support/tenant_e1_schema.py) | Explicit nine-table definitions and approved permission rows. |
| [E1 operations](../migration_support/tenant_e1.py) | Table creation, five nullable expansions, metadata integration and guarded rollback. |
| [Lifecycle SQL](../migration_support/tenant_e1_sql.py) | Nine functions and 28 triggers, including deferred owner checks and closed governance. |
| [Offline review runner](../scripts/review_tenant_e1.py) | Guarded compilation, static tests, graph inventory and local artifacts. |
| [Static tests](../tests/test_tenant_e1_static.py) | Metadata, dependencies, scope, policies, SQL and rollback checks. |
| This report | Observed results, limitations and the next approval gate. |

Three existing files were modified:

- [Main Alembic environment](../alembic/env.py): import the migration metadata
  builder and use a complete copied target metadata.
- [Test Alembic environment](../alembic_test/env.py): the same metadata change;
  existing branch, endpoint and database attestation remain intact.
- [Documentation index](README.md): link this review.

No application source, old revision, settings file, dependency declaration or
business model was changed. In particular, authentication, payment processing,
current owner associations and business-route behavior remain unchanged.
The scope record compares the pre-task hashes of 542 existing files. Its final
allowed differences are the two environments and documentation index.

## 3. Metadata integration and explicit object inventory

Read-only inspection found **46 legacy tables in the repository's loaded
Base.metadata**, not a live database table count. The copied target contains
55 tables after adding the nine tenant tables. Earlier reported database counts
of 47 are historical observations; this task does not reconcile them by guessing.
A later live inventory must explain any actual differences before execution.

The Alembic builder copies each complete legacy Table into new metadata, adds
only the approved nullable references and then attaches frozen tenant tables.
It never imports or concatenates B1's partial `restaurants`/`admins` metadata.
The original Base.metadata, Restaurant mapper and startup exports are untouched.
Missing prerequisites, already-expanded columns or duplicate tenant tables fail
explicitly instead of being silently accepted.

For migration operations, a separate temporary metadata contains minimal FK
targets, marked external. An explicit nine-name allowlist is the only source of
CREATE TABLE operations; its guard rejects any external reference table.
No create_all, reflection, autogenerate or database engine is used by the review.

| New table | Main integrity purpose |
| --- | --- |
| `identities` | Exact case-sensitive issuer/subject pair, explicit status and positive revision. |
| `organizations` | Stable local company, draft default, lifecycle/revision and enforcement marker. |
| `tenant_roles` | Exactly the three tenant role codes, separate from platform RBAC. |
| `organization_memberships` | Unique company/identity, checked lifecycle and scope, acceptance evidence and immutable endpoints. |
| `tenant_role_permissions` | Explicit composite-key policies bounded by each role's catalogue ceiling. |
| `membership_restaurant_grants` | Unique explicit grant with company-qualified membership and restaurant references. |
| `membership_change_proposals` | Checked actor/target, revisions, enrollment generation and proposed role/scope; usage fenced. |
| `membership_proposal_restaurants` | Normalized company-qualified intent set; usage fenced. |
| `tenant_audit_events` | Company-qualified actor/target, revisions and policy snapshots; retained append-only history. |

The new tables contain **9 named primary keys, 7 UNIQUE constraints, 32 CHECK
constraints, 17 RESTRICT foreign keys and 11 indexes**. All new FK targets and
referenced unique/primary keys resolve against complete target metadata.
Constraint, index, function and trigger names are explicit and within the
63-byte PostgreSQL identifier limit. No collision was found with named legacy
key/index objects in repository metadata; live catalog collisions remain untested.

### Existing-table expansion

| Existing table | Nullable column | Added integrity objects |
| --- | --- | --- |
| `restaurants` | `organization_id INTEGER` | RESTRICT FK to companies; UNIQUE `(organization_id, id)`; company index. |
| `restaurant_groups` | `organization_id INTEGER` | RESTRICT FK to companies; UNIQUE `(organization_id, id)`; company index. |
| `restaurant_branches` | `organization_id INTEGER` | Two composite RESTRICT FKs to group/company and restaurant/company; two supporting indexes. |
| `owners` | `identity_id INTEGER` | RESTRICT identity FK and nullable UNIQUE identity link. |
| `admins` | `identity_id INTEGER` | RESTRICT identity FK and nullable UNIQUE identity link. |

Dependency review confirmed that the existing group/link tables and owner/admin
profiles already exist in repository metadata. Composite keys on restaurants
and groups are added before dependent links and grants. No original key, owner,
group association, profile subject or platform role is rewritten.

These additions total **5 nullable columns, 6 NOT VALID foreign keys, 4 UNIQUE
constraints and 4 indexes** on existing tables. New empty-table FKs are fully
validated. NOT VALID defers scanning old rows; it does not exempt subsequent
inserts or updates from the FK. Unique constraints cannot use that shortcut.
[PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html).

Null assignments remain permissible during expansion and cannot constitute
tenant authorization. The grouping association receives no new unique pair yet:
existing duplicates must first be inventoried and reconciled. `Restaurant.group_id`
is retained. Neither grouping representation is converted in E1.

### Provisioned policy definitions

| Role | Explicit permission rows |
| --- | --- |
| `owner` | 26 |
| `manager` | 17 |
| `employee` | 6 |

The revision contains only these three role rows and 49 tenant permission rows.
It inserts no identities, companies, memberships, grants, profiles or audit
events. All role assignments omit `tenant.orders.fulfill`. Its catalogue name
remains inside the frozen B1 validation ceiling, which is not a permission grant.
The post-seed policy fence also rejects later ordinary INSERT/UPDATE/DELETE.
No platform roles, permissions or administrator assignments are changed.

## 4. SQL lifecycle protections and concurrency review

### Retention and immutable references

- Identity ID, issuer, subject and creation time are immutable; retired identity
  reactivation and ordinary identity DELETE are rejected.
- Company ID and creation time are immutable. An existing enforcement marker
  cannot be changed or cleared; archived companies cannot be reactivated.
- Membership ID, company, identity and creation time are immutable. Ordinary
  DELETE is rejected. Updates must advance revision exactly once. Re-enrollment
  from revoked requires a new pending generation, cleared lifecycle evidence,
  explicit mode and an empty current grant set.
- Identity, company and membership UPDATEs must advance revision exactly once.
  This is a database invariant, not proof that a caller supplied a CAS predicate:
  expected-revision checks and affected-row validation remain service duties.
- Once a legacy resource/profile reference is non-null, ordinary reassignment,
  unlinking, ID changes and deletion are rejected. Tagged group-link endpoints
  are immutable. Initial restaurant/group/link tagging requires a draft company
  with no enforcement marker. Untagged legacy rows retain existing behavior.
- Audit UPDATE/DELETE and TRUNCATE of every new tenant table are rejected.
  PUBLIC privileges are revoked only on newly created tables. Runtime database
  roles and grants are deliberately not invented; least-privilege provisioning
  requires a separate review before operational use.

### Last qualifying active owner

Two constraint triggers, on companies and memberships, are **DEFERRABLE
INITIALLY DEFERRED**. They inspect current state at constraint-check time:
an active company needs an active, accepted, company-wide owner membership
whose Identity is active. A company may therefore be assembled atomically
without requiring every intermediate statement to have its final owner set.
Deferral controls check timing; it does not itself serialize competing writers.
[PostgreSQL CREATE TRIGGER](https://www.postgresql.org/docs/current/sql-createtrigger.html).

The reviewed E1 mechanism adds early row writes before that deferred check:

1. A membership INSERT/UPDATE advances the referenced identity revision, then
   advances the company revision. Both are real UPDATEs, not only row locks.
2. An identity status UPDATE advances every associated company revision in
   sorted company order, which queues the company owner check.
3. Company lifecycle changes already write the company row. Retained identity
   and membership DELETEs cannot bypass these paths.
4. The deferred checker locks the company, then performs its owner query in a
   separate statement. It does not update revisions or recursively enqueue itself.

**Static reasoning, not an observed concurrency result:** the shared company
write serializes simultaneous owner reductions. The identity write also covers
an identity-status race with a newly inserted membership that an older snapshot
cannot yet see. Under READ COMMITTED, the subsequent owner query can obtain a
fresh snapshot. Under REPEATABLE READ/SERIALIZABLE, conflicting writes require
transaction retry rather than treating a lock as a snapshot refresh.
[PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html).

These automatic revision advances are deliberately conservative: a membership
change also invalidates contexts for its identity and company, potentially
including other companies of that identity. Callers must resolve fresh contexts
after commit. This is a proposed SQL enforcement detail to validate before
execution; it was not added to the running B1 services or their memory fixtures.

Row triggers may acquire locks after the original statement has already locked
a membership. Multi-row SQL or a caller holding shared identity locks can still
deadlock. Future governance callers must discover bounded target sets and acquire
required exclusive identity/company locks in the approved order before mutation.
READ COMMITTED is the design's initial operating mode. Test all supported
isolation levels and whole-transaction retry handling for SQLSTATE `40001` and
`40P01`; never continue a partially failed governance transaction.
[PostgreSQL explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html).

No claim is made that compilation proves PL/pgSQL validity, race freedom,
deadlock avoidance, ORM refresh behavior or service compatibility on PostgreSQL.

### Governance intentionally remains closed

B1 does not implement sealed proposal graphs, target acceptance, owner transfer
or reviewed policy editing. E1 therefore installs an explicit SQL fence on all
proposal/proposal-restaurant and role/policy INSERT/UPDATE/DELETE after initial
policy provisioning. No target acceptance is inferred from a timestamp or JWT.

This is an intentional deny policy, not a usable proposal workflow. A separate
reviewed revision must replace the fence with the complete sealing, acceptance,
revision, audit and delegation contract before those operations are released.
That future work is not silently enabled or represented as finished by E1.

Database owners/superusers can alter triggers and remain trusted operators.
These invoker-rights functions do not create an authorization API, grant database
access or prove an operator's identity-link approval. Routes, identity enrollment,
resource tagging and company activation still need their own reviewed workflows.

## 5. Generated SQL and observed checks

Run the safe local review only:

```powershell
.venv\Scripts\python.exe scripts/review_tenant_e1.py
```

The runner installs the existing Python socket guard before application-model
inspection. It disables shared conftest/plugin autoload, keeps both OIDC flags
false, reads graph labels statically and renders only the new E1 bodies using
MigrationContext with `as_sql=True`, PostgreSQL and StringIO. No Alembic env.py,
connection URL, engine, DBAPI connection or database execution is used to compile
the revision. Existing parent migrations are not executed or rendered as a chain;
some depend on live schema inspection, outside this authorization.

Observed result: **49 static tests passed, zero warnings, no detected network
attempts and no shared database conftest loaded**. Tests cover model-contract
compatibility, complete metadata copying, FK/key resolution, distinct ancestry,
deterministic SQL, policy limits, finance/platform exclusions, nullable additions,
transaction refusal and guarded dependency ordering. They execute no fixture SQL,
including SQLite. The previously validated application suite was not repeated.

Local generated deliverables, excluded from Git and Docker:

- [Validation and revision graph](../artifacts/keycloak-k9-b2/validation.json).
- [Repository metadata inventory](../artifacts/keycloak-k9-b2/repository-inventory.json).
- [Main upgrade SQL](../artifacts/keycloak-k9-b2/e1a92b200001-upgrade.sql)
  and [main downgrade SQL](../artifacts/keycloak-k9-b2/e1a92b200001-downgrade.sql).
- [Test upgrade SQL](../artifacts/keycloak-k9-b2/e1b92b200001-upgrade.sql)
  and [test downgrade SQL](../artifacts/keycloak-k9-b2/e1b92b200001-downgrade.sql).
- [Scope verification](../artifacts/keycloak-k9-b2/scope-verification.json)
  and [standards verification](../artifacts/keycloak-k9-b2/standards-review.json).
- [Complete copyable Python sources](../artifacts/keycloak-k9-b2/complete-python-sources.md),
  [source archive](../artifacts/keycloak-k9-b2/b2-python-sources.zip)
  and [source manifest](../artifacts/keycloak-k9-b2/source-manifest.json).

Black and Ruff pass for all eight new Python files. Each has the standard
copyright header, function headings, docstrings and typed signatures. Historical
environment formatting is preserved apart from the scoped metadata integration.
There are no unfinished execution stubs or real account/identity values in E1.
Generated artifacts are local checkout evidence; their links may be absent from
GitHub and the review runner regenerates the SQL/results without a database.

## 6. PostgreSQL rehearsal plan — requires separate authorization

Before any database connection or execution, obtain approval for a precise
isolated target and scope. Production remains prohibited. The next plan is:

1. Attest the Neon project, development branch, primary endpoint and actual
   `neondb_test` through existing fail-closed preflight. Prefer an independently
   approved disposable clone with usable recovery evidence. Never infer the
   target from DATABASE_URL or use the temporary historical recovery branch.
2. Confirm the server version, exact Alembic history/parent, table owners,
   privileges, existing columns, constraint/index names and prerequisite keys.
   Reconcile the repository/live inventory difference. Capture original row
   counts, financial values, legacy associations and platform permission sets.
3. Review the exact revision and source/SQL hashes. Main and test revisions are
   alternatives for distinct histories, not sequential migrations. Do not stamp
   or execute missing financial predecessors as part of an E1-only rehearsal.
4. Apply only the approved E1 range in one transactional DDL boundary. This
   contract requires PostgreSQL, an active non-autocommit transaction, public
   schema, a 5-second lock timeout and a 60-second statement timeout. Indexes and
   UNIQUE additions use ordinary blocking DDL, not concurrent index creation.
   Measure size/lock impact and approve any changed limits before application.
5. Inspect installed CHECK/UNIQUE/FK definitions, validation flags, indexes,
   functions, triggers and actual privileges. Verify exactly 3 role rows and
   49 permissions, no fulfillment grant and no real identity/company seed.
6. Use separately approved synthetic data to test issuer-qualified identity
   uniqueness, invalid status/revision, same-company composite FKs, empty grants,
   explicit/company-wide modes, immutable assignments, audit retention and the
   SQL governance fence. Keep those records isolated from existing test data.
7. Test deferred last-owner rejection on activation, demotion, suspension,
   revocation and identity retirement; valid atomic owner replacement using
   controlled test SQL; SET CONSTRAINTS timing; two-owner simultaneous removal;
   identity suspension versus membership creation; and two companies with the
   same identity. Exercise READ COMMITTED and higher-isolation write conflicts.
8. Test raw SQL bypass attempts, multi-row operations, FK/cascade effects,
   TRUNCATE denial, lock timeouts, full rollback and bounded whole-transaction
   retries. Test SQLAlchemy loaded-state expiration/CAS/audit behavior with the
   new automatic revision advances before permitting any B1 service to use E1.
9. Compare all original financial data, platform RBAC, administrator identity
   fields, restaurant owners and group associations before/after. Confirm current
   APIs retain their protections and no K8 diagnostic or tenant route is exposed.
10. Rehearse empty-only downgrade and recovery on the separately approved clone.
    Submit actual observations and remaining failures before any next approval.

No step above has been run. Policy workflows, identity linking, canonical group
cutover, real enrollment and business-route conversion remain outside this plan.

## 7. Recovery strategy, stop conditions and approval gate

Upgrade contains no existing-column deletion or data backfill. DDL remains in a
single transaction; no concurrent-index/autocommit block or forced CASCADE is
used. On a statement failure or timeout, stop and roll back the entire transaction;
verify actual catalog/version state before considering another attempt.

Downgrade first takes ACCESS EXCLUSIVE locks on all 14 involved tables in sorted
order. Before dropping anything, it refuses any retained identity, company,
membership, grant, proposal or audit row; any non-null new legacy reference; or
any difference from the exact initial role/policy rows and revisions. Only an
unused foundation can be removed. Triggers/functions, dependent tables and new
references are removed in dependency order. Old columns and original associations
remain. No forced data removal, CASCADE or financial rollback is provided.

Once tenant data or references exist, prefer a reviewed forward repair or restore
to a verified isolated recovery destination. Do not disable retention triggers,
delete evidence or clear links to make downgrade succeed. A past six-hour Neon
recovery demonstration is not proof of a currently available restore point;
refresh recovery evidence immediately before an authorized rehearsal.

Stop for a target/parent mismatch, missing attestation, unexpected schema/data,
name conflict, unapproved parent migration, invalid server SQL, privilege failure,
owner-invariant failure, unhandled concurrency/revision conflict, altered finance
or platform permissions, unavailable recovery, or any requirement to bypass a
safety gate. Keep rollout stopped until the discrepancy is reviewed.

The `.env` file is unchanged. Local `DATABASE_TARGET=development`, DEBUG and
DB_ECHO are false; OIDC_DIAGNOSTICS_ENABLED and OIDC_ALLOW_LOCAL_HTTP remain false.
No Neon access, migration execution, real tenant, owner-test association,
Keycloak/Render/Telegram modification or Git push occurred.

**Work stops here for approval of this static review. PostgreSQL rehearsal and
every migration execution require a separate, explicit authorization.**
