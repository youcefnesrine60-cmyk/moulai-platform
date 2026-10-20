# K9 G2 — PostgreSQL rehearsal results

Date: 2026-10-19. Status: **the authorized replay completed: 12 PostgreSQL
scenario groups passed; independent final preservation checks passed.**

The user accepted these results on 2026-10-19. G2 is closed for the executed
matrix, including the empty downgrade and 219 offline tests. The comparator
incident and its SELECT-only correction below remain part of the retained
record. G2 was not rerun for the subsequent functional tenant-read delivery.

E1 remains installed on W with synthetic tenant fixtures. No further write,
cleanup, source-branch migration or deployment is authorized by this report.

## 1. Exact destination and admission

| Property | Verified value |
| --- | --- |
| Project | `shiny-lab-60817779` |
| W branch | `br-nameless-hall-asvgljm8` |
| W endpoint | `ep-spring-fire-asgkya2x` |
| Database | `neondb_test` |
| Required initial revision | `dce91870b4a2`, exactly one row |
| Installed final revision | `e1b92b200001` |

Fresh real read-only collections confirmed B/W/V's initial equivalence before
the replay. The manifest's control-plane observation was 13:03:57 UTC; the
successful execution session started at 13:18:15 UTC. Initial equality was
verified at 13:19:46 UTC. Its reviewed manifest SHA-256 is:

```text
852dbe9b804c8718bf3485995fade11482ff234772bcdd6df4cc777264953b37
```

The launcher retained exact branch/endpoint admission, production/development
exclusions, verified TLS, frozen E1 source hashes and the one-hour freshness
limit. B/V received read-only collectors only. Credentials stayed in memory;
the application's `.env` and current authentication/payment routes were unchanged.

The earlier expired-evidence attempt remained refused. In this replay, terminal
access was obtained before handing fresh reviewed evidence to the running
process. An initial W collection failure was diagnosed by a separate successful
read-only collection; its original cause was not established. No SQL write
occurred until complete initial admission and equivalence succeeded.

## 2. Actual migration and PostgreSQL results

E1 committed on W at **13:21:21 UTC**. Real catalog checks verified nine new
tables, five nullable integer columns, 65 named new-table constraints, six
NOT VALID legacy foreign keys, expected indexes, 28 triggers including two
initially deferred owner triggers, nine functions, three tenant roles and
exactly 49 permission rows. No role received `tenant.orders.fulfill`.

| Matrix mapping | Executed PostgreSQL observation | Result |
| --- | --- | --- |
| P03/P05 | Synthetic foundation committed with explicit IDs and no initial legacy rows | Passed |
| P04/P05/P06 | Ownerless activation rejected at real commit; final-owner reductions and identity suspension/retirement rejected; atomic owner replacement committed | Passed |
| P07 | Two real transactions removed different owners under READ COMMITTED: one committed, one failed `23514`; actual blocking observed | Passed |
| P07 | Identity suspension raced with a new owner membership; invalid activation failed `23514` | Passed |
| P08/P09/P10/P12 | Same legacy owner across companies A/B, empty employee grants, company-qualified FK failures and immutable restaurant assignments | Passed |
| P12/P14/P15 | Fourteen direct-SQL refusals covering retained principals, closed governance/policy, audit TRUNCATE and issuer-qualified uniqueness | Passed |
| P13/P16 | Actual async SQLAlchemy revocation, stale CAS refusal, trigger revision refresh, append-only audit and fresh pending enrollment | Passed |
| P11 | Revocation waited for bounded authorized work; subsequent membership resolution denied access | Passed |
| P17 | REPEATABLE READ owner race produced `40001`; one fresh full retry correctly refused removing the last owner | Passed |
| P17 | Statement `57014` and lock `55P03` timeouts; full rollback and one fresh transaction retry | Passed |
| P17 | Real two-connection deadlock produced `40P01`; one fresh ordered full-transaction retry succeeded | Passed |
| P18 | Populated downgrade refused `23514` before drops; E1 catalog remained intact | Passed |

P01/P02 remain covered by offline refusal regressions plus actual W/exact-parent
admission. The earlier **empty upgrade/downgrade round trip** committed at
10:44:08/10:46:03 UTC and restored W's exact pre-E1 reference before this replay.
Expected security failures above are passing negative tests, not ignored errors.

## 3. Final preservation and comparator correction

All twelve scenario groups passed. The original runner then exited **1** at its
final catalog comparison: its name-prefix filter failed to exclude the approved
`ct_e1_organization_owner` and `ct_e1_membership_owner` triggers. This was a
verification defect. The original failed output and exit status are retained.

Writes stopped at that point. The comparator was corrected to exclude exact
`(table, trigger)` pairs from the frozen E1 contract, preserving every other
trigger even if its name has a similar prefix. A network-denied regression test
covers both E1 trigger families and a similarly prefixed legacy trigger.
The legacy fixture timestamps also use the server clock with their existing
SQL types; no application timestamp model was changed.

The corrected final checker ran **only SELECTs in a READ ONLY transaction**,
rolled it back and closed its engine. At **13:30:24 UTC**, it confirmed:

- W's exact E1 revision and approved catalog/policy inventory.
- Every original business row projection and all **43 original sequence values**
  unchanged; temporary legacy restaurant/owner fixtures were rolled back.
- Original catalog fingerprints unchanged: **393 columns, 313 constraints,
  118 indexes**, original routines/triggers, ownership, ACLs, SQL roles and role
  memberships, default privileges, RLS and sequence definitions.

B/V were independently reread after W's write tests; their logical states still
matched the historical B reference. Their shared logical fingerprint remained:

```text
b978493eef810c74abf83a71732f7041427830386387c9bacee5727bc155a83a
```

No additional migration or synthetic write was replayed after the comparator
failure. The passing final conclusion combines the twelve retained case results,
the B/V comparisons and the successful independent read-only preservation check;
it does not rewrite the original runner's exit code as zero.

## 4. Verification scope and limitations

Offline result: **219 tests and 59 sub-tests passed**, with zero warnings,
network attempts or shared database conftest imports. Black and Ruff pass for
the changed Python scripts/tests. The previously validated application suite
was not repeated.

This validates the concrete matrix above, not every possible P01–P20 variation.
SERIALIZABLE races, every group-link-specific FK variation and every possible
TRUNCATE/delegation combination were not independently exercised. READ COMMITTED
and REPEATABLE READ, actual commit boundaries, blocking and deadlock behavior
were tested. Current business routes remain outside tenant cutover.

The 46 original business tables were empty. Their exact preservation was proven,
but preservation of representative populated historical financial data was not.
V proves an independent readable equivalent reference, not a completed incident
restore, disaster recovery or application failover.

W retains only the authorized synthetic tenant fixture and E1. Its populated
foundation cannot be downgraded by deleting retained history or disabling guards.
No cleanup or expiration extension occurred. W/V keep their approved expiration
on 2026-10-20 at 08:32:04/08:32:58 UTC; B has no automatic expiration and its
mandatory review remains 2026-10-22 at 08:25:35 UTC.

The final control-plane read at 13:32:07 UTC confirmed the same five branches,
endpoints, parentage, temporary 0.25 CU computes and Free plan. No paid operation,
source-branch SQL connection, production/development/B/V write, real account
association, resource creation/deletion, Keycloak/Render/Telegram change, OIDC
activation, deployment or GitHub push occurred.

## 5. Files and reproducible evidence

G2 additions:

- [W-only Alembic launcher](../scripts/rehearse_tenant_e1.py).
- [PostgreSQL scenarios](../scripts/validate_tenant_e1_postgres.py).
- [SELECT-only preservation checker](../scripts/verify_tenant_e1_preservation.py).
- [Launcher tests](../tests/test_tenant_e1_launcher.py) and
  [transaction/comparator tests](../tests/test_tenant_e1_postgres_harness.py).
- This report.

G2 modifications:

- [Test Alembic environment](../alembic_test/env.py): admitted pinned connection
  and central Settings; original safeguards and generic path preserved.
- [Offline review runner](../scripts/review_rehearsal_admission.py): isolated
  regression selection and complete source export.
- [Documentation index](README.md): link the results.

The frozen migration, existing safety logic, application models/routes and
`.env` were not modified. Both OIDC indicators remain false.

Retained local ignored evidence:

- [Original G2 evidence](../artifacts/keycloak-k9-g2), including the empty round
  trip and initial refused launch.
- [Replay evidence](../artifacts/keycloak-k9-g2/retry-20261019): manifest/control
  plane, real equivalence proof, `second-upgrade.json`, all twelve case results
  in `postgres-validation.json`, original exit status in `execution.json`,
  corrected read-only `preservation.json` and consolidated `validation-summary.json`.
- [Scope/standards verification](../artifacts/keycloak-k9-g2/verification.json).
- [Complete copyable Python sources](../artifacts/keycloak-k9-g1-admission/complete-python-sources.md).

These artifacts contain sanitized observations and fingerprints. Raw collector
reports are in `artifacts/keycloak-k9-g1-execution/g2-retry-before-*.json` and
`g2-retry-after-*.json`. Ignored artifact links may be absent from GitHub.

The authorized replay ends here. Any further write, cleanup, tenant cutover or
production migration requires its own applicable approval.

## 6. Temporary-resource custody after G2 acceptance

A fresh control-plane-only inspection on **2026-10-19 at 14:10:49 UTC** confirmed
all five existing branches, their parentage and endpoints. B/W/V remain ready
with fixed 0.25 CU primaries. No SQL connection, deletion, TTL change or new
resource was used for this inspection.

| Resource | Exact branch / endpoint | Retention decision already in force |
| --- | --- | --- |
| W | `br-nameless-hall-asvgljm8` / `ep-spring-fire-asgkya2x` | Existing automatic expiration: 2026-10-20 08:32:04 UTC. Retained E1/synthetic fixtures; not a persistent development target. |
| V | `br-red-star-asuzlvno` / `ep-blue-wind-as1patkx` | Existing automatic expiration: 2026-10-20 08:32:58 UTC. Read-only recovery reference; no migration destination. |
| B | `br-old-hill-as7g8xe8` / `ep-winter-wind-asu1em6m` | No automatic expiration. Mandatory evidence/storage review: 2026-10-22 08:25:35 UTC. |

Africa/Lagos deadlines are one hour later: W/V expire at 09:32:04/09:32:58;
B's review is at 09:25:35. These are recorded deadlines, not assistant reminders.
The existing W/V automatic expirations were approved in G1; no new deletion or
expiration operation is scheduled by this delivery.

Before W/V expire, retain the sanitized G2 case results, SQL/source hashes,
equivalence proof, original failed comparator output and corrected preservation
observation. These are already saved in the linked ignored artifact directories;
do not overwrite them with later functional-test results. If their retention
must be extended, obtain approval before the expiry and recheck the Free budget.

The B review package consists of its exact manifest/parent and endpoint, the
retained pre-E1 revision `dce91870b4a2`, 47-table/43-sequence fingerprints, B/V
before/after equivalence and G2 acceptance. Review whether another retained
baseline is still required after both children expire, where evidence is kept
and whether continued storage fits the approved zero-spend envelope. The
six-hour history window is not a substitute for retaining an approved reference.

No manual cleanup is authorized. If cleanup is later requested, re-attest exact
IDs and children, verify there are no remaining consumers or unresolved failures,
and approve W/V before B. Production/development are never cleanup candidates.
Do not disable retention triggers or erase fixtures to force a downgrade. If B's
review deadline passes without a decision, close further admission and escalate
the retention decision; do not silently delete or extend resources.
