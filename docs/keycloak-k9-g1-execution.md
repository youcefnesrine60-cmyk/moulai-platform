# K9 G1 - Exact lineage and initial logical equivalence validated

Date: 2026-10-19. Status: **G1 confirmed at 09:26:14 UTC (10:26:14 Africa/Lagos)**.
The existing B/W/V branches were retained. No resource or expiration was changed.
**E1 migration and write tests remain unauthorized and unexecuted.**

This report supersedes the earlier same-LSN admission block following the user's
explicit decision to require exact lineage and measured logical equivalence.
The [previous report](../artifacts/keycloak-k9-g1-resolution/previous-execution-report.md)
is retained locally with the comparison evidence.

## 1. Identities and provenance confirmed in Neon

Project: `shiny-lab-60817779`. Before/after authenticated inventories confirm
five unchanged branches/endpoints, the following exact parentage and fixed
0.25 CU temporary computes. LSNs are retained as provenance, not equality proof.

| Resource | Branch ID | Endpoint ID | Direct parent | Parent LSN |
| --- | --- | --- | --- | --- |
| B | `br-old-hill-as7g8xe8` | `ep-winter-wind-asu1em6m` | development | `0/562CF808` |
| W | `br-nameless-hall-asvgljm8` | `ep-spring-fire-asgkya2x` | B | `0/562D08B8` |
| V | `br-red-star-asuzlvno` | `ep-blue-wind-as1patkx` | B | `0/562D09B0` |

Production `br-plain-firefly-as17il6w`, development `br-lively-truth-asga1dtk`
and their endpoints remain excluded as B/W/V destinations. Unknown endpoints,
source replicas/pooler aliases, incorrect database/project and wrong parentage
remain refused. Every resource's declared LSN still must match its own verified
control-plane record; only cross-branch LSN equality was removed.

## 2. Actual read-only comparison

The existing collector connected separately to B, W and V using verified TLS,
explicit REPEATABLE READ / READ ONLY transactions, pinned identity/revision
checks, bounded streaming and final rollback. No credentials or raw business
rows were exported. No SQL connection to production or development was opened
in this correction.

| Observation | B | W | V |
| --- | --- | --- | --- |
| Database | `neondb_test` | `neondb_test` | `neondb_test` |
| Exact Alembic revision | `dce91870b4a2` | `dce91870b4a2` | `dce91870b4a2` |
| Initial public tables | 47 | 47 | 47 |
| Columns / constraints / indexes | 393 / 313 / 118 | 393 / 313 / 118 | 393 / 313 / 118 |
| Sequences | 43 | 43 | 43 |
| Tables, catalogs and sequence-state differences | None | None | None |
| Collection completed, UTC | 09:25:31 | 09:08:41 | 09:14:20 |
| Read-only transaction rolled back | Yes | Yes | Yes |

All primary-key-ordered table counts/hashes, column definitions, constraints,
indexes, schema/database/relation ACLs and ownership, roles/memberships, default
privileges, RLS, routine/trigger fingerprints and sequence definitions/values
match exactly. B also matches its historical initial snapshot. No differences
were normalized away to obtain equality.

Common canonical logical-state SHA-256:

```text
b978493eef810c74abf83a71732f7041427830386387c9bacee5727bc155a83a
```

**Scope limitation:** the 46 business tables are empty; only `alembic_version`
contains a row. The evidence validates this empty reference state and its schema,
authorizations and sequences, not preservation of populated financial records.
V is an independent readable reference equivalent to B. **No post-incident
restore, failover or production recovery has been demonstrated.**

One fresh B collection failed with `DBAPIError`. Its cause was not established;
the arbitrary error payload was not retained to avoid exposing connection data.
A single full read-only retry succeeded with unchanged limits and rollback.
The successful snapshot, not the failed attempt, forms the comparison evidence.

## 3. Guard correction and offline tests

[The admission module](../app/core/rehearsal_admission.py) now separates inventory
admission from state acceptance. Inventory requires exact approved identities
and direct lineage. `verify_initial_equivalence` then requires three fresh,
complete read-only observations bound to the same reviewed manifest, exact
revision, 47 tables and 43 sequences. Any unexplained data, catalog, permissions
or sequence difference causes refusal.

E1 destination admission additionally requires the fresh compared evidence;
a topology manifest alone is insufficient. This code-level condition grants no
G2 authorization and introduces no migration launcher or route changes.

Observed offline results: **156 tests plus 59 sub-tests passed; zero warnings,
failures or detected network attempts**. Shared database conftest files were
not loaded. Coverage includes different provenance LSNs with equal states,
wrong direct parents, endpoints, production/development destinations, missing
observations, data/schema/ACL/sequence divergence, stale evidence and E1 without
proof. Existing central guard regressions also passed. Black and Ruff pass.

## 4. Scope, evidence and remaining boundary

Exactly three repository files were modified:

- [Admission contracts and comparison](../app/core/rehearsal_admission.py).
- [Offline regression tests](../tests/test_rehearsal_admission.py).
- This report.

The original central test guard, `.env`, application routes and both Alembic
histories are unchanged. DATABASE_TARGET remains development; DEBUG, DB_ECHO
and both OIDC flags remain false. No branch creation/deletion, expiry change,
business write, seed, migration, deployment or Keycloak/Telegram/GitHub change
occurred. No existing production/development setting was changed.

Expirations remain **2026-10-20 08:32:04Z for W** and **08:32:58Z for V**;
B has no automatic expiration and retains its mandatory review deadline
**2026-10-22 08:25:35Z**. In Africa/Lagos these are 09:32:04, 09:32:58 and
09:25:35 respectively. No reminder or cleanup was scheduled.

Local ignored evidence: [comparison](../artifacts/keycloak-k9-g1-resolution/comparison.json),
[immutable equivalence result](../artifacts/keycloak-k9-g1-resolution/initial-state-equivalence.json),
[reviewed manifest](../artifacts/keycloak-k9-g1-resolution/reviewed-manifest.json),
[resource checks](../artifacts/keycloak-k9-g1-resolution/resource-verification.json),
[offline test results](../artifacts/keycloak-k9-g1-admission/validation.json) and
[complete copyable Python sources](../artifacts/keycloak-k9-g1-admission/complete-python-sources.md).
The actual B/W/V inventories are `resolution-B.json`, `resolution-W.json` and
`resolution-V.json` in [the execution evidence directory](../artifacts/keycloak-k9-g1-execution).

**G1 is confirmed for the measured initial state.** This is dated evidence,
not an ongoing write permit. PostgreSQL E1 rehearsal on W still requires the
user's separate authorization and fresh admission checks before execution.
