# K9.2-B3-A — PostgreSQL preflight and recovery readiness

Subsequent local correction: the protected production ID defect described below
was resolved and validated offline in [B3-FIX](keycloak-k9-b3-guard-fix.md).
The original observations remain historical evidence. Recovery readiness and
authorization for an independent rehearsal or migration remain pending.

Date: 2026-10-18. Scope: **read-only observations and rehearsal planning only**.
Decision: **NO-GO for branch creation or migration execution**. The E1 test
parent is installed, but the protected production branch reference is wrong in
local configuration and actual recovery has not been demonstrated for a new
rehearsal target. No configuration correction was applied automatically.

This report follows the [B2 static review](keycloak-k9-b2-migration-review.md).
It records real development-database observations, separately identified
operator-provided Neon control-plane information, and work requiring a new
authorization. It does not approve a migration or release tenant business access.

## 1. Observed connection and read-only guarantees

The database observation began at **2026-10-18T13:54:43Z**, using a dedicated
SQLAlchemy asyncpg connection to the validated TEST_DATABASE_URL. The existing
helpers in [test_database.py](../app/core/test_database.py) performed URL,
endpoint, project and branch checks; the production DATABASE_URL was not used
to open a connection. Verified CA/hostname TLS settings were retained.

| Observed item | Result |
| --- | --- |
| Actual database | `neondb_test` |
| Neon project | `shiny-lab-60817779` |
| Attested development branch | `br-lively-truth-asga1dtk` |
| Attested endpoint | `ep-quiet-rain-assrs0gv` |
| Identity evidence | Server pg_settings; branch/project postmaster context, configuration-file source, matching reset values and no pending restart |
| Endpoint context | `superuser`, accepted by the existing endpoint-specific rule |
| PostgreSQL version | `18.6 (653b019)`; numeric version `180006` |
| Transaction isolation | `repeatable read` |
| transaction_read_only | `on`, including the final check |
| Transaction completion | Explicit rollback; connection then disposed |
| Installed Alembic revision | Exactly one row: `dce91870b4a2` |

Before inventory reads, the collector explicitly set the transaction to
REPEATABLE READ, READ ONLY. Its SQLAlchemy statement listener allowed only the
fixed SELECT/SHOW statements and that transaction-control statement. The event
record contains 17 SELECT, 6 SHOW and 1 SET statements; driver setup and
BEGIN/ROLLBACK are not an exhaustive part of that event count.

The server reported default_transaction_read_only=`off`, despite the requested
connection startup setting. The guarantee therefore comes from the explicitly
verified transaction state and statement guard, not an assumption that the
server default changed. No SET READ WRITE, DDL, DML, seed, Alembic command or
commit was issued by this collector. No production connection was opened.

An initial attempt stopped before connection because the shell inherited
DEBUG=`release`; a separate sandboxed attempt was denied network access.
After network authorization, the successful process used DEBUG=`false` without
editing .env. Environment-variable precedence must be checked again before a
future launch; a correct .env value alone does not override the shell.

## 2. Blocking protected-branch configuration discrepancy

The operator subsequently confirmed the production ID from both the production
branch's id and development's parent_id. The values differ by the order of i/l:

| Reference | Value |
| --- | --- |
| Production ID confirmed by the operator from Neon | `br-plain-firefly-as17il6w` |
| Local PROTECTED_DATABASE_BRANCH_ID used during the observation | `br-plain-firefly-as17li6w` |
| Source expected by the existing exclusion helper | The configured PROTECTED_DATABASE_BRANCH_ID |
| Required disposition | Correct and re-attest through a separately reviewed configuration step before migration |

The existing validator checks the protected ID's syntax and excludes that
configured ID; it cannot independently establish that it is the real production
branch. Thus its configured exclusion reference was syntactically valid but
incorrect. This is a genuine safety configuration defect, not a value to ignore
or silently normalize.

The completed read still attested the expected development project, branch,
endpoint and database. That successful target observation does **not** make the
overall safety configuration ready for migration. The production branch/endpoint
exclusion must be reconfirmed together before any later operation.

The local B3 collector was subsequently made to expect the operator-confirmed
production ID. An offline check, with socket operations blocked, proves that it
now refuses the unchanged local configuration with the public code
`approved_project_or_branch_mismatch` before attempting a database connection.
No .env, Settings module, existing guard, migration or endpoint was changed.

## 3. Revision compatibility

The database contains `dce91870b4a2`, which is the exact down_revision of
[test E1](../alembic_test/versions/e1b92b200001_tenant_foundation_e1.py):

```text
ae6a266365fb -> b7d33e89f4a1 -> dce91870b4a2 -> e1b92b200001
                                           installed      proposed only
```

There is no missing predecessor or need to stamp, merge histories, recreate the
schema or execute a main-history payment revision. This is **parent compatibility**,
not evidence that E1 functions, triggers or downgrade work on PostgreSQL.

The main-history E1 revision `e1a92b200001` is not the migration for this test
history. No production version was queried. The default alembic.ini environment
uses DATABASE_URL directly; DATABASE_TARGET=development does not redirect that
main migration environment. A future rehearsal must explicitly use the test
history and an independently attested rehearsal connection.

## 4. Real catalog inventory and model comparison

The full sanitized inventory is retained locally; SQL string literals in defaults
and definitions are omitted. Role passwords, connection URLs, credentials,
Keycloak subjects and application row contents were not exported.

| Public schema inventory | Observed count |
| --- | --- |
| Ordinary tables | 47 |
| Sequences | 43 |
| Columns | 393 |
| Primary-key constraints | 47 |
| Foreign-key constraints | 62 |
| Unique constraints | 8 |
| CHECK constraints | 2 |
| NOT NULL catalog constraints | 194 |
| Total catalog constraints | 313 |
| Indexes, including constraint-backed indexes | 118 |
| Non-internal triggers | 0 |
| Public routines | 0 |
| Expanded relation ACL entries | 419 |

All inventoried constraints have convalidated=true; all inventoried indexes are
valid and ready. No public table had row security or forced row security enabled.
Internal FK triggers are excluded from the non-internal trigger count. PostgreSQL
18 represents NOT NULL constraints in pg_constraint, explaining their inclusion
in the 313-record total.
[PostgreSQL pg_constraint](https://www.postgresql.org/docs/18/catalog-pg-constraint.html).

### Why 47 database tables versus 46 model tables

The table-name comparison is exact:

```text
47 database tables = 46 legacy model tables + public.alembic_version
393 database columns = 392 legacy model columns + alembic_version.version_num
```

No model table is missing, and alembic_version is the only additional public
table. All 392 matching business columns agree in name, normalized PostgreSQL
type and nullability. This comparison does not certify every default expression,
CHECK literal, relationship, index expression or business-data invariant.

Two ORM-declared index names are absent:

- `ix_manual_payment_audit_id`.
- `ix_manual_payment_receipts_id`.

Both affected tables have their actual unique primary-key index on id:
`manual_payment_audit_pkey` and `manual_payment_receipts_pkey`. These are existing
metadata/index differences, not missing tables or evidence of lost receipt rows.
Constraint-backed indexes also appear in the database catalog but are not
separate Index objects in the model inventory. E1's explicit operations do not
add, drop or repair these financial indexes; do not use a broad autogenerate diff
to silently include them in tenant work.

### E1 prerequisites and collision checks

None of E1's nine tables or five existing-table columns is present. All five
existing expansion targets have their expected primary key on id. No proposed
E1 constraint/index/function/trigger name collided with the captured public
catalog names. Those checks are snapshot observations and must be repeated on
the independently created rehearsal branch before execution.

### Ownership and privileges

The database, public schema and all 90 inventoried table/sequence relations are
owned by `neondb_owner`; the connected SQL role is also `neondb_owner`. It is not
a PostgreSQL superuser, but has CREATEROLE, CREATEDB, replication and BYPASSRLS
attributes and membership in neon_superuser. All seven table privileges tested
for that role were true on all 47 tables, including write and TRUNCATE privileges.

All 419 expanded relation ACL entries name neondb_owner; no PUBLIC relation ACL
entry was observed. Two default-privilege entries owned by cloud_admin grant
neon_superuser privileges for public tables and sequences. These are inspected
catalog facts, not grants performed by this task. The complete role membership,
schema, direct/default ACL and effective-table-privilege inventories are local.

The read-only transaction constrained this privileged connection; its role is
not intrinsically read-only. Runtime least privilege remains a separate review.
SQL ownership is not a Keycloak role, a platform administrator assignment or a
tenant membership. No business permissions or identity links were inferred.

### Evidence limitation and collector correction

The executed collector serialized PostgreSQL internal char values as byte
representations. Its business-row count filter consequently selected no tables.
**No business row-count baseline was obtained; an empty row_counts object does
not mean empty tables.** The complete relation catalog and column/constraint/index
queries did succeed. The 47-table inventory was derived offline by normalizing
the captured relation kinds; no second connection was needed.

The normalizer was corrected locally and checked offline. The exact originally
executed source is retained and matches the SHA-256 in the live record. The
corrected collector was not rerun against Neon. Capture row counts, financial
digests and sequence state on the future isolated clone before any write tests.

## 5. Current recovery information and its limits

No authenticated Neon browser session, API credential or CLI was available to
the agent for a control-plane query. The operator supplied the following
read-only Neon observations on 2026-10-18, approximately 13:50 UTC:

| Operator-confirmed control-plane item | Reported value |
| --- | --- |
| Project | moulai-db / `shiny-lab-60817779` |
| Region | aws-eu-central-1, Frankfurt |
| Configured history retention | 21,600 seconds / 6 hours |
| Development branch | development / `br-lively-truth-asga1dtk` |
| Parent, confirmed after transcription review | production / `br-plain-firefly-as17il6w` |
| Development state | ready |
| Creation time | `2026-10-14T18:42:53Z` |
| Protection | protected=false |
| Expiration | No expiration timestamp returned by the consulted API |

The operator's calculated interval was **07:50Z–13:50Z on 2026-10-18**. This is
a theoretical sliding six-hour interval, not an inventory of verified restorable
points. Exact earliest/latest usable timestamps, snapshot availability, branch
quota, retention coverage during a long rehearsal and a successful current
recovery remain unverified. No returned expiration is not a guarantee against
later deletion or lifecycle changes.

Neon history retention governs past-state availability and must be checked
immediately before relying on a recovery point.
[Neon history window](https://neon.com/docs/postgres/backup-restore/history-window).
The recovery branch tested on October 14 was scheduled to expire on October 15;
that historical result does not establish an available recovery destination now.
No restore, backup export or replacement of development/production was attempted.

## 6. Proposed independent rehearsal and verifiable recovery

Recommended target: a **new disposable branch derived from development**, in the
same approved project, containing only an authorized connection to neondb_test.
Proposed descriptive name: `moulai-k9-e1-rehearsal-20261018`; this is not an
existing branch and no ID, endpoint or connection value has been invented.
Neon supports separate branches for isolated schema experiments.
[Neon branch management](https://neon.com/docs/manage/branches).

The future authorization should define the following together:

1. Reconcile the protected production ID and reconfirm its endpoint through a
   reviewed operator configuration step. Verify that no production or development
   connection is accidentally supplied as the rehearsal destination.
2. Record a source timestamp/LSN and the exact parent revision. Preserve a
   separately authorized baseline branch or supported snapshot at that point,
   with no application writers and reviewed expiration/access settings.
3. Create the separately authorized disposable rehearsal branch from that
   baseline. Attest its new branch and endpoint IDs against the expected project
   and neondb_test. Explicitly reject **both** existing production and development
   branch/endpoint IDs. A new database name on development is insufficient.
4. Confirm Neon quotas, snapshot/history features, permissions and any cost
   implications before creation. Branching may copy multiple databases; this
   grants no permission to connect to another database on the clone.
5. Prove recovery into another separately approved disposable destination:
   compare revision, schemas, constraints, indexes, ACLs, sequence state and
   deterministic data digests against the retained baseline. Never demonstrate
   recovery by restoring over production or the working development branch.
6. If the rehearsal branch becomes unusable, retain evidence and rebuild a new
   disposable destination from the verified baseline. Do not depend on empty-only
   downgrade once synthetic tenant data exists or on a six-hour point surviving
   indefinitely. Every extra branch/restore still needs explicit authorization.

A preserved Neon branch is a logical recovery baseline within the same service,
not an independent external backup. If an external backup is required, separately
approve an encrypted dump and a restore test with controlled storage outside Git.
No dump, snapshot or additional branch has been created in B3-A.

## 7. Planned PostgreSQL test matrix — not executed

Run these only on the independently attested rehearsal target after separate
authorization, with synthetic fixtures and before/after preservation evidence.

| ID | Scenario | Required result |
| --- | --- | --- |
| P01 | Wrong project/branch/endpoint/database, missing declaration, either protected source supplied | Refuse before DDL or fixtures; no production/development fallback. |
| P02 | Parent differs from exactly dce91870b4a2; dirty/duplicate E1 objects | Stop; no stamp, automatic adoption or unrelated predecessor execution. |
| P03 | Apply E1 only | 9 tables, 5 nullable columns, expected named constraints/indexes, 3 roles, 49 permission rows; no fulfillment permission or real identity. |
| P04 | Deferred activation with no qualifying owner | Commit/forced constraint check fails; whole transaction rolls back. |
| P05 | Atomic replacement of the last owner using controlled synthetic SQL | Valid final owner state commits; invalid intermediate state is tolerated only while appropriately deferred. |
| P06 | Last owner demotion, suspension, revocation, identity suspension/retirement | Active company cannot commit without another accepted active owner. |
| P07 | Two simultaneous owner removals; identity suspension versus membership creation | Serialize or abort safely; no write skew; retry the entire transaction after 40001/40P01. |
| P08 | Same identity owns companies A and B; status changes affect several companies | Check each company; no merged grants; sorted/bounded locking and current revisions. |
| P09 | Cross-company grant/link/actor/target FK; company-wide membership with explicit grants | Database rejects invalid references and modes even through direct SQL. |
| P10 | Empty explicit grant set | No restaurant access; no fallback based on common ownership. |
| P11 | Concurrent ordinary operation versus grant/member revocation or company suspension | Operation commits before reduction or revalidates and denies afterward. |
| P12 | Direct SQL mutation of immutable keys, company assignments or enforcement marker | Guard rejects reassignment/removal; legacy untagged behavior is preserved. |
| P13 | Re-enrollment from revoked | Fresh pending generation and empty grants; no automatic resurrection or activation. |
| P14 | Proposal/role policy insertion, editing or deletion after initial provisioning | E1 governance fence rejects it; do not disable triggers to release a workflow. |
| P15 | Audit update/delete, retained-principal deletion, TRUNCATE and cascades | Retained history is protected; failed cascades roll back atomically. |
| P16 | SQLAlchemy loaded state, CAS, automatic identity/company revision increments | Fresh context after mutation; correct conflict detection and atomic audit evidence. |
| P17 | Lock/statement timeout, multi-row changes, deadlock and higher isolation | Full rollback and bounded idempotent transaction retry; no partial continuation. |
| P18 | Empty-only downgrade and populated/drifted downgrade attempt | Empty baseline restores; retained data/links or changed policies cause refusal before drops. |
| P19 | Payments, subscriptions, receipts/audit, payer/restaurant ownership, platform RBAC | Original rows, values, associations, privileges and sequence state preserved. |
| P20 | Recovery into another disposable target | Restored revision, schema and data digests match the retained baseline; source branches untouched. |

Use multiple real asyncpg connections for race tests, real commit boundaries for
deferred constraints and reviewed READ COMMITTED plus higher-isolation cases.
Transaction rollback alone does not restore every sequence advance; use explicit
synthetic IDs and capture sequence state. Test fixture cleanup must not alter the
original development database or discard historical tenant evidence.

## 8. Envisaged migration command — not executed

The intended Alembic target is:

```powershell
.venv\Scripts\python.exe -m alembic -c alembic_test.ini upgrade e1b92b200001
```

**Do not run this command with the current .env.** It currently selects the
working development database, not an independent rehearsal branch, and its
protected-branch declaration is incorrect. The command is a proposed target,
not a ready-to-run deployment procedure.

Before a separately approved run, an isolated process must receive the real
approved rehearsal connection and IDs through the existing Settings variables,
keep DEBUG/DB_ECHO and both OIDC diagnostics false, attest the new destination,
exclude both source branches/endpoints and require exactly dce91870b4a2.
No rehearsal credentials or executable connection configuration are supplied here.
No revision range, downgrade, stamp, main-history command or migration executor
was run or added in this phase.

## 9. Risks, stop conditions and evidence

| Risk or condition | Required disposition |
| --- | --- |
| Incorrect protected production ID | Blocking; reviewed operator correction and fresh attestation before any migration. |
| Destination is working development or production | Blocking even if the database is called neondb_test. |
| Only theoretical history interval; no verified recovery destination | Blocking for rehearsal writes until recovery conditions are demonstrated and approved. |
| Development is unprotected; privileged SQL role can bypass protections | Keep current read-only scope; review role separation and branch controls before operational use. |
| Old financial index/model differences | Preserve them; reject unrelated autogenerate operations in E1. |
| New target schema/parent/hash differs from this snapshot | Stop and review; no automatic repair, stamp or predecessor traversal. |
| Current collector has no business-row baseline | Capture counts/digests/sequence state on the future clone; do not infer empty or preserved rows from this report. |
| Deferred triggers, revision changes and lock protocol lack real rehearsal evidence | Execute the matrix only after authorization; no production-readiness claim yet. |
| Timeout, partial failure, privilege conflict or recovery mismatch | Roll back the whole transaction; retain evidence and stop. |

Only this documentation file was added to the repository's non-artifact scope.
All existing application, guard, migration, configuration and documentation files
are preserved by SHA-256 comparison. Local evidence is centralized under the
ignored `artifacts/keycloak-k9-b3` directory:

- [Observed live catalog](../artifacts/keycloak-k9-b3/live-inventory.json).
- [Offline model comparison](../artifacts/keycloak-k9-b3/metadata-analysis.json).
- [Protected-reference refusal check](../artifacts/keycloak-k9-b3/guard-validation.json).
- [Operator-provided recovery record](../artifacts/keycloak-k9-b3/operator-recovery-record.json).
- [Exact executed collector](../artifacts/keycloak-k9-b3/executed-read-only-preflight.py)
  and [corrected collector](../artifacts/keycloak-k9-b3/read_only_preflight.py).
- [Scope and evidence verification](../artifacts/keycloak-k9-b3/verification.json).

No application suite or write test was repeated. The previously reported B2
static tests remain historical evidence. B3's observations do not validate E1
execution. OIDC_DIAGNOSTICS_ENABLED and OIDC_ALLOW_LOCAL_HTTP remain false;
.env and the incorrect protected-branch setting were deliberately left unchanged.
No branch, backup, migration, stamp, business link, deployment or remote change
was performed. Work stops with this report; branch creation, configuration
correction and E1 execution require separately reviewed authorization.
