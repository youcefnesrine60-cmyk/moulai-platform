# K9.2-B3 — Offline admission validation and G1 readiness

Date: 2026-10-18. Status: **offline implementation validated; G1 resource
creation remains unauthorized**. The [B/W/V design](keycloak-k9-b3-rehearsal-plan.md)
is architecturally approved. This report prepares its next gate; it does not
authorize connections, resource creation, migration or cleanup.

## 1. Scope and observed verification

Added files:

| File | Responsibility |
| --- | --- |
| [Admission module](../app/core/rehearsal_admission.py) | Immutable resource contracts, manifest parsing/fingerprinting, destination admission and read-only connection inspection. |
| [Offline tests](../tests/test_rehearsal_admission.py) | Synthetic topology, process settings, URL and mocked PostgreSQL identity/revision checks. |
| [Review runner](../scripts/review_rehearsal_admission.py) | Network-denied targeted tests, schema export and complete copyable Python sources. |
| This report | Results, resource manifest specification, expiration proposal and G1 conditions. |

No existing source/configuration file was modified. The 556 pre-existing files
in the scope snapshot, including `.env`, existing safety code and both Alembic
histories, retain their original hashes. No dependency was added. The new module
is opt-in and is not imported by routes or wired into either Alembic environment.

Run only this offline review:

```powershell
.venv\Scripts\python.exe scripts/review_rehearsal_admission.py
```

Observed: **123 tests passed, plus 59 passing sub-tests; zero warnings, failures
or detected network attempts**. Shared database conftest files were not loaded.
The selection includes the existing `test_test_database_safety.py` regressions.
Black and Ruff pass for all three new Python files. PostgreSQL observations are
mocked; no SQL was executed, including against SQLite. Previously validated
application tests were not repeated.

Local ignored artifacts:

- [Machine-readable results](../artifacts/keycloak-k9-g1-admission/validation.json).
- [Resource manifest JSON Schema](../artifacts/keycloak-k9-g1-admission/resource-manifest.schema.json).
- [Complete copyable Python sources](../artifacts/keycloak-k9-g1-admission/complete-python-sources.md).
- [Scope and standards verification](../artifacts/keycloak-k9-g1-admission/verification.json).

The runner regenerates the first three artifacts without a database. These local
artifact links are not published to GitHub.

## 2. Admission contract and rejection coverage

The dedicated layer reuses `validated_test_database_url`,
`validate_test_branch_configuration`, `read_test_database_identity` and verified
TLS arguments from [the existing guard](../app/core/test_database.py).
It does not change their implementation or the application's development target.

| Boundary | Enforced rule and tested refusal |
| --- | --- |
| Project and sources | Exact `shiny-lab-60817779`; production `br-plain-firefly-as17il6w` and development `br-lively-truth-asga1dtk` excluded from all B/W/V destinations. Wrong project, old production typo and unknown branches refused. |
| Endpoints | Complete approved inventory includes source primaries and replicas. An exact temporary branch/endpoint/host allowlist excludes source URLs, pooler aliases and unknown endpoints. A declared W endpoint mapped to a source branch is refused. |
| Purpose | B and V allow inventory admission only; E1 destination admission requires W in a complete manifest. Swapped purposes, duplicate IDs and incorrect parents fail. |
| URL | `postgresql+asyncpg`, `neondb_test`, approved direct host or its exact pooler alias, default/5432 port; no URL query options. Wrong database/driver/host/port and routing/TLS overrides fail. TLS is supplied through central connection arguments. |
| Process | All effective target/project/branch/endpoint/protected IDs must match. APP_ENV and DATABASE_TARGET must be development; DEBUG, DB_ECHO and both OIDC flags must be false. Every missing or mismatching value, including inherited DEBUG=release, fails. |
| Revision | Exact starting `dce91870b4a2`, intended target `e1b92b200001`; empty, multiple, wrong-history and already-E1 observations fail. No head, stamp, adoption or predecessor traversal. |
| Manifest integrity | Strict frozen nested models, forbidden unknown fields, bounded parsing, UTC times, independent approved SHA-256 and control-plane evidence no older than one hour. Incomplete/stale/future evidence, invalid forks and unsafe expirations fail. |
| Connection | Re-admit the supplied connection's engine URL; require an active PostgreSQL read-only transaction, then check immutable Neon branch/project settings and endpoint settings with the existing helper. Session overrides, pending restart, changed database/identity and connection substitution fail. |

The connection helper performs SELECTs only and neither creates an engine nor
begins, commits or rolls back a transaction. Its return value is an observation,
not a transferable write permit. Future read-only tooling must create its engine
with `read_only_connection_arguments()` and explicitly verify transaction mode;
the startup default alone is not sufficient evidence. Existing externally supplied
connections are not automatically proof of correct TLS construction.

**Trust boundary:** offline code cannot prove that a supplied Neon API inventory
is authentic or exhaustive. The operator must review the original control-plane
evidence and approve its manifest hash through a separate trusted channel. The
hash detects changes; it is not a signature or an independent authorization.
Even an omitted source replica is outside the positive destination allowlist;
live immutable branch/project attestation remains mandatory after connection.

## 3. Resource manifests prepared for G1

No real B/W/V IDs or endpoints exist yet. No production-ready manifest containing
invented values was created. The executable contract and generated JSON Schema
define every required field. Synthetic IDs appear only in unit tests.

| Contract | Required content |
| --- | --- |
| Envelope | Version, stage, exact project/source IDs, database, starting/target revisions, resource records and control-plane evidence. |
| Control plane | UTC observation time, completeness declaration, source evidence SHA-256, complete project branch/parent/fork inventory and endpoint/branch/direct-host/primary mappings, including replicas. |
| Each resource | Purpose, real branch ID, real primary endpoint ID, parent ID, actual fork LSN, creation time, expiration or explicit null, mandatory review deadline. |
| Approval | Independently recorded canonical manifest SHA-256. URLs, passwords, tokens and credentials are excluded. |

Admission has two stages so that the first baseline can be checked safely:

1. After separate G1 authorization and B creation, approve a `baseline-only`
   manifest containing B's real IDs and the refreshed source inventory. It admits
   only B inventory. Verify B's exact parent revision before proceeding to children.
2. After separately authorized W/V creation from B's captured state, approve a
   `complete` manifest with all three distinct resources. W/V must share the
   recorded B fork LSN, each with exactly one primary endpoint and no replica.
3. Use read-only comparisons to prove the initial B/W/V state and recovery V.
   A fresh manifest approval is required when its evidence changes or expires.
   E1/write tests still require G2 authorization after these observations.

Actual endpoint hosts must be copied from the authorized Neon inventory, then
compared with the credential URL and the connected server's identity. Names or
database suffixes alone are never identity evidence. Never set Neon identity
GUCs, persist W's URL into `.env` or fall back to DATABASE_URL.

This module is not a migration launcher. Bare Alembic still lacks the dedicated
purpose gate. Any later execution harness must own the checked engine/connection,
repeat admission on its actual pinned write transaction and enforce the separate
G2 authorization, recovery proof, baseline comparison and frozen E1 hashes.
No migration command should be run at G1.
This initial-state inspector intentionally rejects a database already at E1;
post-upgrade testing needs a separately reviewed phase-aware harness.

## 4. Quotas, compute, storage and spending

The operator supplied these read-only account observations on 2026-10-18; this
task did not authenticate to the Neon account or query its API:

| Item | Observation and admission consequence |
| --- | --- |
| Plan | Free `free_v3`. No paid upgrade or billed overrun authorized. |
| Branches | 2 of 10; three proposed additions yield 5 of 10. Recount immediately before each creation. |
| Computes | Two existing endpoints, both observed idle. Three new primaries proposed; account-specific capacity to admit all three still requires confirmation. |
| Compute usage | API returned 56,721 cumulative compute seconds, approximately 15.76 compute-hours. This is not a reliable billing-period CU-hour measurement; do not subtract it from the allowance. |
| Storage | Logical sizes approximately 47.4 MB production and 47.5 MB development. These do not establish total billable child/history storage or remaining capacity. |
| Recovery | Six-hour history; no development snapshot/schedule identified. B/V recovery proof still required under G1. |

Published Free allowances checked on this date are **100 CU-hours per project
per month, 1 GB database storage per project and 10 branches per project**, with
compute sizes up to 2 CU. Account usage and remaining availability require the
project's Billing/Usage view; public allowances alone do not admit creation.
[Neon pricing](https://neon.com/pricing).

Proposed initial computes: one fixed **0.25 CU** primary per temporary branch,
with scale-to-zero and no replica or automatic enlargement. As a conservative
planning calculation, B active for 72 hours plus W/V each active for 24 hours
would consume `0.25 × (72 + 24 + 24) = 30 CU-hours`, before existing workloads
or retention beyond B's initial review horizon. This is a hypothetical envelope,
not observed consumption or a reserved allowance. All project computes share
usage, and child changes/history can consume storage.
[Neon plan accounting](https://neon.com/docs/introduction/plans).

At the last admission before creation, record the current billing period,
remaining CU-hours, total storage/history and transfer headroom, endpoint capacity
and any applicable account restrictions. Reserve room for existing workloads,
inventory traffic and synthetic changes. If capacity is insufficient or unclear,
stop; do not upgrade, resize or stop existing computes to make room.

**Proposed additional spending ceiling: EUR 0.** This remains the creation
proposal to approve at G1, not permission to spend. Only operations confirmed
within available Free allocations may proceed. No price conversion or paid
fallback is used. The user explicitly reserves exact consumption checks for the
last pre-creation admission; their absence does not block this offline preparation.

## 5. Explicit lifetime proposal

| Resource | Proposed lifetime/expiration | Safeguard |
| --- | --- | --- |
| W | Automatic expiration exactly 24 hours after its actual creation. | Review by creation +22 hours; admission closes at least two hours before expiration. Export failed-run evidence before expiry; extensions need approval. |
| V | Automatic expiration exactly 24 hours after its actual creation. | Same two-hour margin; its availability must cover recovery checks before and after W testing. Expiry before completion stops E1 admission. |
| B | Initial review/budget horizon 72 hours; explicitly **no automatic expiration** while evidence review is open. | Retain until results are accepted and W/V are gone. Propose manual deletion within 24 hours after separate exact-ID cleanup approval; retention beyond 72 hours needs renewed budget/review approval. |

A fixed auto-delete TTL for B could destroy the only retained pre-E1 baseline
before review ends. Its explicit `expires_at=null` is therefore intentional; the
72-hour `review_due_at` closes admission without deleting evidence. No extension
or deletion is automated. Resolve ongoing storage capacity before authorizing
retention beyond that checkpoint; preserve B and escalate for review if unresolved.
Extended retention alone does not reopen this guard's 72-hour admission window.
The user must approve this B retention exception and W/V TTLs at G1. Record actual
UTC timestamps then, never assume Console defaults. Neon supports disabling a
branch's automatic expiration.
[Neon expiration controls](https://neon.com/docs/manage/branches).

## 6. Remaining gates and stop point

Offline preparation is complete. Before any creation, G1 must explicitly approve
the three proposed resources/primary computes, this retention policy and the
zero-spend envelope after the final quota/usage check. Resource creation remains
blocked for missing capacity evidence or authorization. Before connections, pin
and approve the real resource manifests; wrong identities, incomplete inventory,
expired evidence or an unexpected starting revision stop the workflow.

P01/P02 admission preparation is exercised offline here. P03–P20 PostgreSQL,
concurrency, financial preservation, recovery and rollback tests remain unexecuted.
No live guarantee about their outcome is made. G1 permits neither migration nor
fixtures; G2 remains separate. Cleanup also requires its own exact-ID approval.

No Neon connection, SQL execution, branch creation/change, Alembic invocation,
identity enrollment, deployment, Keycloak/Telegram change or GitHub push occurred.
The two OIDC flags remain false. **Work stops for report review and explicit G1
authorization before any Neon resource creation.**
