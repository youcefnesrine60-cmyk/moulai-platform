# K9.2-B3-B1 — Isolated PostgreSQL rehearsal plan

Date: 2026-10-18. Status: **design submitted for review; no Neon resource created,
no database connection or migration execution in this step**.

This plan follows [B3-A](keycloak-k9-b3-preflight.md), the approved
[guard correction](keycloak-k9-b3-guard-fix.md) and the
[E1 static review](keycloak-k9-b2-migration-review.md). Plan approval, resource
creation, migration execution and cleanup are separate gates. No existing
production/development branch, local configuration, application code or revision
is changed by this document.

## 1. Confirmed inputs and remaining unknowns

The operator's latest direct Neon verification supplies these planning inputs;
they were not queried again in this step:

| Item | Planning input |
| --- | --- |
| Project | `shiny-lab-60817779` |
| Production branch to exclude | `br-plain-firefly-as17il6w` |
| Working source branch | development / `br-lively-truth-asga1dtk` |
| Development endpoint observed in B3-A | `ep-quiet-rain-assrs0gv`; reconfirm before resource creation |
| Permitted database for all rehearsal SQL | `neondb_test` only |
| Exact required starting revision | `dce91870b4a2` |
| Proposed E1 revision | `e1b92b200001`, independent test history |
| History retention | 6 hours |
| Branch quota and current use | 10 maximum; 2 present |
| Development automatic snapshot schedule | None identified |
| Existing development snapshot | None identified in the returned inventory |

Actual restorable timestamps, resource prices/allowances, compute quotas,
temporary resource IDs/endpoints, access settings and expiration times must be
recorded when their separately authorized operations occur. Names in this plan
are proposed labels, not evidence that resources exist.

The historical B3-A source inventory was 47 public tables: 46 business-model
tables plus alembic_version. It is a comparison aid, not permission to ignore
future drift. Reconfirm the exact revision and inventory on the new reference.

## 2. Branch topology and purpose separation

Proposed lineage, with all three new resources still uncreated:

```text
production                         existing; excluded
  development                     existing source; excluded from rehearsal writes
    B: moulai-k9-e1-baseline-20261018
      W: moulai-k9-e1-rehearsal-20261018
      V: moulai-k9-e1-recovery-proof-20261018
```

| Label | Parent | Purpose | Authorized SQL after future approval |
| --- | --- | --- | --- |
| B | development | Preserve one captured pre-E1 state independently of the writer branch | Read-only inventory and baseline comparison; no migration or fixtures. |
| W | B | E1 upgrade/downgrade rehearsal and synthetic PostgreSQL tests | Only separately approved E1/test operations on neondb_test. |
| V | B | Materialize and verify the recoverable pre-E1 state | Read-only recovery comparison; never an alternate migration target. |

Capture B from development at an explicit current-data fork; record the actual
parent ID, returned fork LSN/timestamp and resource metadata. Do not use schema-only
branching: original financial-data preservation requires a data-bearing reference.
Do not pause, reset, restore, rename or change settings on development to obtain
that point. Development may continue evolving after the fork; comparisons use B's
captured state, not the source's later head.

Neon supports child branches of existing child branches, with isolated writes.
Branches can contain multiple databases and roles. Their creation may inherit
role credentials; logical branch separation is not a promise of credential
separation. Only neondb_test may be connected for this rehearsal, even if another
database is present in a clone.
[Neon branch management](https://neon.com/docs/manage/branches).

B and V are operationally read-only references: no authorized writer, application,
worker, bot, deployment or migration receives their connection. This does not
make an owner credential technically incapable of writing. Record current SQL
ownership/access, coordinate exclusive rehearsal access and stop on unexplained
sessions or baseline changes. Any new temporary credential/access arrangement
needs explicit approval and must affect only the new resources.

Review inherited database jobs, external data connections and network-capable
triggers before activating new computes or write tests. If clone activation could
start an unreviewed writer outside W, stop for an isolated-access design review;
do not disable or alter an existing source branch's jobs to make the test pass.

## 3. Resource quota, retention and budget gates

| Point | Expected branch count | Headroom against the reported quota |
| --- | --- | --- |
| Before creation | 2 | 8 |
| B created | 3 | 7 |
| B and W created | 4 | 6 |
| B, W and V present | 5 | 5 |

The proposed resource envelope is **three new branches, peak five total**, with
no automatic replacement branches or retries that create additional resources.
Include one approved primary compute/endpoint per new branch in that envelope;
do not add replicas or stop existing computes to work around a resource limit.
Recheck the live count immediately before each creation. An unexpected count,
name collision, insufficient compute allowance or changed quota stops the plan;
do not delete an unrelated branch or upgrade the project to make room.

Before approval of creation, record current plan allowances/prices, expected
compute activity for inventory and race tests, retained/changed data storage,
history usage and any transfer charges applicable to the chosen workflow.
Obtain an explicit spending ceiling or confirmed within-allowance budget and
a maximum resource lifetime. Branch-count capacity does not establish that
compute/storage is free. No paid plan change, compute enlargement or history
increase is implied.
[Neon pricing](https://neon.com/pricing).

The creation approval must specify expiration for B/W/V explicitly; do not
accept an unnoticed Console default. B must outlive W/V and the evidence review.
Do not let a disposable branch's automatic deletion remove the only remaining
verified recovery copy. TTL extensions and retention changes require review;
never alter the existing branches' expiration or the project history setting.

## 4. Recovery gate before any E1 write

Six hours of configured history is not an existing snapshot or proof that an
arbitrary timestamp is recoverable. No automatic snapshot schedule or current
snapshot was identified, so neither is a prerequisite silently assumed present.
Historical-point recovery remains conditional on actual history availability.
[Neon history window](https://neon.com/docs/postgres/backup-restore/history-window).

The proposed primary mechanism is the retained data-bearing B branch plus a
separately materialized V, both containing the exact pre-E1 state:

1. After creation authorization, attest B and capture its manifest in a read-only
   transaction. Require exactly dce91870b4a2 and no conflicting E1 objects.
2. Create W and V explicitly from the captured B state, not from the moving
   development head. Record both parents and fork points. B must have no writers.
3. Attest W/V and compare their initial revision, original table rows/digests,
   schema, constraints, indexes, sequence state and privileges with B. Allow only
   documented per-resource identity differences such as branch/endpoint IDs;
   unexplained data, ownership or privilege differences block E1.
4. Demonstrate that V can actually be connected and its reference state read.
   A successful branch-creation response or matching table count alone is not
   recovery proof. Record evidence and the measured materialization/verification
   time; do not promise a recovery time before it has been measured.
5. Release a separate migration authorization only after that comparison passes,
   B remains retained, V remains available and the budget/lifetime still covers
   the planned tests and review.

If W fails later, stop its writers and retain evidence. B/V preserve an independent
pre-E1 state; verify V again after the failure/test run. Rebuilding yet another
destination from B or promoting any connection is a new authorized operation,
not an automatic retry. Never restore over or reset production/development.

This proves branch-based reconstruction of the measured neondb_test reference,
not external-disaster recovery, application failover or restoration of every
database in the Neon project. A retained branch can preserve its head beyond
the source history window while it exists, but retention adds storage exposure.
It is not an independent provider backup.
[Neon retained branch behavior](https://neon.com/docs/manage/branches).

An encrypted external dump/restore is an alternative only after separate approval
of its scope, secure storage and independent restore target. Do not export raw
application data or global role passwords to Git, logs or this report.

## 5. Strict identity admission for each new resource

Before any connection, a reviewed resource manifest must bind project, purpose,
branch ID, endpoint ID/host, parent/fork point, permitted database and expected
revision to the exact created resource. Record the manifest hash at approval;
any later replacement ID, changed purpose or edited mapping requires review.
Names and a URL's database suffix alone are insufficient identity evidence.

### Required rejection sets and positive allowlist

- Reject production `br-plain-firefly-as17il6w` and development
  `br-lively-truth-asga1dtk` as E1/fixture destinations.
- Reconfirm all endpoints attached to those two branches, including replicas;
  exclude their IDs and canonical hosts. The known development endpoint
  ep-quiet-rain-assrs0gv remains excluded. Reconfirm the current production
  endpoint mapping rather than relying only on its old local declaration.
- Require B/W/V IDs to differ from each other and from both existing branches.
  Require their endpoint IDs to be distinct and mapped to the proper new branch.
- Only **W's exact approved branch/endpoint tuple** may receive E1 and fixtures.
  B and V are denied for writes even though they are new isolated branches.
- Normalize direct/pooler endpoint identity through the existing URL validator;
  verify TLS CA/hostname, postgresql+asyncpg and database neondb_test. Reject
  routing query overrides, endpoint substitution and incomplete declarations.
- Compare Neon control-plane project/parent/endpoint metadata with the manifest,
  then compare the live database name and immutable server branch/project
  identities through the existing read_test_database_identity helper. Require
  configuration-file/reset agreement and no pending restart; never set identity
  GUCs to manufacture an attestation.

Run initial inventory/attestation in an explicitly checked READ ONLY transaction,
then roll it back. For an eventual authorized write transaction, repeat the
same identity admission on its actual pinned connection before any mutating SQL.
No unchecked reconnect, connection substitution or production URL fallback is
permitted between attestation and execution.

### Existing implementation boundary

[test_database.py](../app/core/test_database.py) currently validates one declared
protected branch/endpoint, and [alembic_test/env.py](../alembic_test/env.py) uses
the configured test target. Those checks must be reused. They do not implement
the full B/W/V purpose allowlist or dual production/development exclusion above.
A dedicated admission/execution harness still needs separate implementation and
offline review before any resource execution phase. Do not interpret this plan
or the earlier 48 offline tests as proof that this future harness already exists.
The development-only B3 collector is not an approved W migration launcher.

## 6. Exact revision and process configuration

For B, initial W and V, require public.alembic_version to exist and contain
**exactly one row equal to dce91870b4a2**. Reject empty/multiple rows, an older
parent, an already-applied E1 revision or a different Alembic history. No stamp,
automatic adoption, predecessor traversal or unrelated schema repair is allowed.
Check the approved E1 Python/SQL hashes and the absence of its nine tables,
five expansion columns and conflicting constraint/index/function/trigger names.

Future process prerequisites in the actual PowerShell terminal:

```powershell
$env:DEBUG = 'false'
$env:DB_ECHO = 'false'
$env:OIDC_DIAGNOSTICS_ENABLED = 'false'
$env:OIDC_ALLOW_LOCAL_HTTP = 'false'
```

DATABASE_TARGET and APP_ENV must remain development. Inspect inherited values
before loading fresh Settings; reject unexpected effective project/branch/endpoint
values. Rehearsal secrets and approved destination IDs must be supplied only to
that isolated process through the existing Settings contract. Do not overwrite
the working .env or persist W's URL as the application's development connection.
Keep production references correct and test that no inherited stale ID masks them.

The eventual reviewed migration target is test-history e1b92b200001 only:

```powershell
# Not executed; requires an approved W-bound launcher and all admission gates.
.venv\Scripts\python.exe -m alembic -c alembic_test.ini upgrade e1b92b200001
```

**Do not run this with today's .env**, which selects working development. Bare
Alembic does not supply the new dual-exclusion/purpose gate. No default
alembic.ini, upgrade head, main-history revision, stamp or migration command is
executed or authorized by this plan. The existing 5-second lock and 60-second
statement limits remain subject to the future measured workload review.

## 7. Baseline evidence before migration

Collect B, W and V using the same reviewed collector, explicit read-only
transactions and identical serialization/session conventions. No other authorized
writer may touch these branches during measurement. Record collection time,
server version, source/fork identity and any active-session concern; stop on
unexpected writers rather than terminating someone else's connection.

| Evidence | Required content and comparison |
| --- | --- |
| Identity and source integrity | Resource manifest, project/branch/endpoint/database, parent/fork point, tool/source/SQL hashes and exact Alembic row. |
| Table/column inventory | All public tables, column order, types, nullability and original-column projection; account explicitly for alembic_version. |
| Data | Exact visible row counts and SHA-256 digests for every table, deterministic primary-key ordering, stable typed/canonical row representation; keep raw values only in transient controlled memory. |
| Original rows | Capture original primary-key sets privately so later comparisons distinguish original rows from separately approved synthetic fixtures. Missing/unreadable keys or unknown data differences block the test. |
| Sequences | Owner/dependency, type, start/increment/min/max/cache/cycle plus last_value/is_called; inspect without nextval or setval. |
| Integrity objects | PK/UNIQUE/CHECK/FK definitions, validation/enforcement and deferral flags, indexes including validity/readiness, triggers and routine definitions or secured hashes. |
| Authorization | Database/schema/table/sequence/routine ownership and ACLs, default privileges, role attributes/memberships, RLS policies and effective permissions. |
| Financial/platform invariants | Original payments, subscriptions, manual receipts/audit, order payments and payer history; administrator subjects, platform RBAC, restaurant owners/group associations preserved. |

Use bounded streaming and reviewed timeouts; do not load an unbounded table into
memory or extend limits automatically. Keep identifiers/counts/digests in local
ignored evidence; redact secrets and SQL literals in shared reports. Protected
raw schema definitions, if needed for exact comparison, stay in approved secure
storage. Redacted display text alone is not an exact schema-equality proof.

After E1, compare original data using the **pre-E1 column projection**, not SELECT
star: the five new nullable columns would otherwise change hashes without changing
legacy values. Account for the intended Alembic revision update separately.
Preserve and compare every original row and original sequence; track synthetic
keys/new E1 objects in a distinct test manifest. Do not exclude or overwrite an
original row merely because a test touched it unexpectedly.

The B3-A collector obtained no business-row baseline because of its catalog-char
filter issue. Reuse its reviewed normalization correction, but do not invoke its
development-bound connection path. Confirm the new collector actually produces
counts and digests for every inventoried table, including empty tables; missing
results are failures, not zero rows.

Sequence effects are not generally rolled back with a transaction. Reserve
collision-checked explicit synthetic IDs compatible with the service's positive-ID
requirements; do not consume or reset original sequences for fixture cleanup.
Verify sequence state with no concurrent writers on the measured clones.
[PostgreSQL sequence behavior](https://www.postgresql.org/docs/18/functions-sequence.html).

## 8. Execution order and PostgreSQL P01–P20 matrix

Everything below is **prepared, not executed**. After distinct authorization:
admit B, then W/V; verify recovery and baseline equality; obtain E1/write-test
approval; run the empty-foundation upgrade/downgrade round trip on W; compare
with B; re-upgrade W; execute synthetic cases; verify preserved original data
and retained B/V; stop for review before cleanup. No route conversion or real
identity/company enrollment is part of these tests.

For P18, perform the successful empty downgrade **before any tenant fixtures**.
Later test populated/drifted downgrade refusal inside a controlled transaction
and require no drops on refusal. Never delete retained audit/membership data or
disable triggers merely to make W empty. Reuse of W for this specified empty
round trip is not permission to mutate B or V.

| ID | Preparation and action on authorized W | Acceptance evidence |
| --- | --- | --- |
| P01 | Negative manifest, project, database, endpoint/pooler, B/V and production/development admission inputs | Refusal before connection to a forbidden source or before mutation; no fallback or credential disclosure. |
| P02 | Validate real W parent/catalog and inject wrong/multiple-parent or conflicting-object observations into admission tests | Exact dce91870b4a2 required; no edits to stored Alembic history, stamp, adoption or missing-parent migration. |
| P03 | Apply reviewed E1 from the exact parent | 9 tables, 5 nullable columns, approved constraints/indexes, 3 roles and 49 permissions; no fulfillment grant or real seed. |
| P04 | Activate synthetic company without a qualifying owner; force constraints and test real commit | Deferred violation and whole-transaction rollback; no invalid committed company. |
| P05 | Assemble a synthetic company/owner and replace its final owner atomically | Valid final accepted active owner succeeds; invalid final state fails. |
| P06 | Demote, suspend or revoke final owner; suspend/retire its identity | Active-company owner invariant remains enforced. |
| P07 | Two real connections remove different owners; race identity suspension with membership insertion | Coordinated overlap; no write skew, only safe serialization or transaction failure. |
| P08 | One synthetic identity owns companies A and B | Separate company/grant checks and bounded sorted locking; no ownership union. |
| P09 | Cross-company FK actor/target/grant/link and incompatible explicit/company-wide modes | Actual PostgreSQL constraints reject direct SQL bypasses. |
| P10 | Employee with an empty explicit grant set | No restaurant, aggregate or lower-level business access; no common-owner fallback. |
| P11 | Race authorized bounded work with revocation/suspension/grant reduction | Work serializes before reduction or revalidates and denies; stale contexts cannot write afterward. |
| P12 | Change immutable IDs, assignment or non-null enforcement marker via SQL | Rejected; approved untagged legacy behavior remains intact. |
| P13 | Attempt revoked membership reactivation and fresh enrollment | Invalid resurrection rejected; only permitted fresh pending generation with empty grants/evidence succeeds. |
| P14 | Mutate proposal graphs or tenant role/policy after provisioning | E1's intentional governance fence rejects all unreleased workflows. |
| P15 | Audit update/delete, principal deletion, TRUNCATE and cascading deletes | Retained history protected; failure is atomic without disabling guards. |
| P16 | Exercise real async SQLAlchemy state, CAS/audit and trigger-driven revisions | Correct refresh/expiration and conflict handling; subsequent context resolved afresh. |
| P17 | Lock/statement timeout, deadlock, multi-row and higher-isolation races | Full rollback; bounded complete-transaction retries for 40001/40P01, never a partial continuation. |
| P18 | Empty downgrade before fixtures, then populated/drifted refusal later | Empty round trip matches B; populated/drifted refusal occurs before dropping objects. |
| P19 | Compare every original financial/platform/resource invariant and original sequence | Matching counts/digests, original associations and permissions except approved E1 additions/revision. |
| P20 | Materialize V from B and compare before E1; recheck after W tests | Recoverable pre-E1 state actually readable and identical; B/V and both source branches untouched. |

Use deterministic synchronization barriers and bounded timeouts for races,
independent connections/transactions, READ COMMITTED plus reviewed higher
isolation levels, and real commit boundaries for deferred checks. Report results,
SQLSTATE, affected-row/CAS outcomes, expected failures and actual retry counts;
do not treat a skipped test or expected schema error as a general pass.
Application services remain preparatory; P10/P11/P16 do not activate HTTP routes.

## 9. Stop conditions and acceptance gates

Stop before E1 if recovery V cannot be materialized/read, any B/W/V manifest or
source exclusion fails, the exact parent differs, a baseline is incomplete,
quotas/cost/lifetime are unapproved, independent access cannot be maintained,
unexpected writers appear, or required features are unavailable. Never compensate
by changing source branches, increasing history, selecting another database,
stamping or skipping a gate.

Stop during the later authorized rehearsal for hash/revision drift, unexplained
original-data/sequence/ACL changes, an invalid owner state committing, unhandled
SQLSTATE/timeouts, loss/expiration of B/V or a failing/untested required case.
Retain failed W and evidence until reviewed; do not force rollback by deleting
history. No result constitutes a production migration approval.

| Gate | Required acceptance |
| --- | --- |
| G0 — This design | User accepts topology, scope, budget/lifetime proposal and purpose-bound identity controls; no resources yet. |
| G1 — Creation/read-only recovery proof | Explicit approval for the three named branches and their primary computes, actual quota/cost envelope and read-only comparisons; inventory their real IDs. |
| G2 — E1 and fixture rehearsal | Verified B/W/V manifests and recovery proof, complete baseline, reviewed admission harness, exact parent and frozen E1 hashes; separate write-test authorization. |
| G3 — Results and cleanup | P01–P20 outcomes reviewed; original-data/sequence preservation established; exact temporary-ID deletion list separately approved. |

## 10. Cleanup plan — no deletion executed

Maintain an explicit resource ledger containing creation approval, purpose,
project, exact ID, parent/fork point, endpoint associations, owner and expiration.
Classify B/W/V as temporary by this ledger, not by a name prefix or a broad
project-wide query. The ledger must never include existing production/development
as deletion candidates.

After results are accepted and cleanup is explicitly authorized:

1. Export sanitized test evidence and hashes; securely retain any approved
   private comparison material according to its agreed retention policy.
2. Stop only the dedicated rehearsal tool's own connections. Confirm that no
   endpoint is referenced by application/deployment configuration and that no
   unrecorded consumers or children exist. Unknown ownership stops cleanup.
3. Re-attest the ledger's temporary IDs and delete leaf W first, then V after
   recovery evidence acceptance. Verify each targeted resource's removal before
   proceeding; never use a recursive prefix-based delete or a force option.
4. Retain B until both children are gone and recovery/evidence review is closed.
   Delete B last under the approved exact-ID cleanup scope. If a failure remains
   under investigation, stop deletion and review retention/budget explicitly.
5. Confirm branch count returns to the pre-creation count only if no other
   authorized actor changed the project. Check that original branches, endpoints
   and application configuration remain unchanged. Do not delete something else
   merely to restore the old numeric count.

Neon branch deletion removes its associated resources and requires child branches
to be removed before their parent. Inspect dependencies instead of assuming a
standalone endpoint/database cleanup is needed.
[Neon deletion semantics](https://neon.com/docs/manage/branches).
No deletion command, automatic cleanup job or branch-creation request was run.

Only this plan is added outside ignored local verification artifacts. No tests,
database access, backup, snapshots, Alembic execution, backfill, configuration
change, Render/Keycloak/Telegram action or GitHub push occurred in B3-B1.
**Work stops for plan review before creating any Neon resource.**
