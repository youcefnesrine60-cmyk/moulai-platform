# K9.2-B3-FIX — Corrected Neon production branch reference

Date: 2026-10-18. Status: **local correction validated offline; validator logic
unchanged**. This resolves the protected-branch transcription defect recorded in
[B3-A](keycloak-k9-b3-preflight.md). It does not authorize a rehearsal branch,
migration, production operation or deployment.

## 1. Corrected files and exact scope

The official operator-confirmed production branch is:

```text
br-plain-firefly-as17il6w
```

| File | Change |
| --- | --- |
| Local .env | Replace only the PROTECTED_DATABASE_BRANCH_ID value `br-plain-firefly-as17li6w` with `br-plain-firefly-as17il6w`. |
| [Operational runbook](billing-production-runbook.md) | Correct the same ID in its current Neon environment description. |
| [B3-A report](keycloak-k9-b3-preflight.md) | Add a resolution notice; preserve the original observations and old-value evidence. |
| This annex | Record the correction, tests and remaining gates. |

The .env edit preserved every other byte and every other parsed variable value.
No application code, test source, migration, validation rule or endpoint was
changed. .env remains ignored by Git and is not tracked. No credential, URL or
secret value is included in this annex or the generated validation summaries.

### Definition and usage inventory

The active local configuration occurrence was .env. The additional operational
reference was the runbook. The blank declaration in .env.example needs no value
and was left unchanged. Historical B3 source snapshots and evidence deliberately
retain the old ID because they describe the earlier observation.

PROTECTED_DATABASE_BRANCH_ID is defined as an optional Settings field in
[config.py](../app/core/config.py). Its existing consumers are:

- [test_database.py](../app/core/test_database.py): protected-branch exclusion and
  the complete server identity check.
- [database.py](../app/core/database.py): development target validation and its
  paired expected-identity configuration.
- [Test Alembic environment](../alembic_test/env.py): branch validation and live
  identity attestation before migration execution.
- [Billing rehearsal](../scripts/billing_test_rehearsal.py),
  [test-table tooling](../scripts/create_test_tables.py) and
  [development startup verifier](../scripts/verify_development_startup.py).
- [Shared database fixtures](../tests/conftest.py) and the isolated safety tests
  that use synthetic settings declarations.

Those consumers already read Settings; none contains the erroneous production
ID as an application constant. Their implementation was not edited. Shared
database fixtures and write-capable operational scripts were not executed.

## 2. Consistent effective development configuration

Fresh instances of the existing Settings class, without constructor overrides,
loaded these values after the correction:

| Parameter | Validated value |
| --- | --- |
| PROTECTED_DATABASE_BRANCH_ID | `br-plain-firefly-as17il6w` |
| TEST_DATABASE_PROJECT_ID | `shiny-lab-60817779` |
| TEST_DATABASE_BRANCH_ID | `br-lively-truth-asga1dtk` |
| TEST_DATABASE_ENDPOINT_ID | `ep-quiet-rain-assrs0gv` |
| Test database and driver | `neondb_test`; postgresql+asyncpg |
| DATABASE_TARGET | development |
| APP_ENV | development |
| DEBUG / DB_ECHO | false / false |
| OIDC_DIAGNOSTICS_ENABLED / OIDC_ALLOW_LOCAL_HTTP | false / false |

The actual configured TEST_DATABASE_URL passed the unchanged endpoint, database,
driver, routing-option and transport-preference validator entirely in memory.
The existing protected endpoint declaration was preserved and used in negative
tests. Its current control-plane mapping was not queried again.

### Process environment precedence

No process, Windows user or machine environment value was present for
PROTECTED_DATABASE_BRANCH_ID during inspection. The corrected .env value was
therefore not hidden by an inherited production-branch override. No inherited
project, development branch, endpoint or DATABASE_TARGET override was found.

The host shell still supplied DEBUG=`release`. The validation runner explicitly
used DEBUG=`false` in its own process, preserving .env and the parent shell.
A negative precedence test temporarily supplied the stale branch ID, confirmed
that a fresh Settings instance sees that environment override, then restored the
environment and confirmed that Settings again reads the official .env value.
Settings precedence was demonstrated, not changed or bypassed.

For a later authorized launch from that same parent terminal, set the valid
boolean there before starting the application:

```powershell
$env:DEBUG = 'false'
```

This command is a launch prerequisite, not a migration command. No persistent
Windows environment setting, parent terminal or running application was modified.
Already running processes retain their loaded Settings until an explicitly
authorized restart/reload; no service was restarted in this task.

## 3. Positive and negative checks performed

Observed result: **48 tests passed, plus 76 successful subtests; zero warnings,
zero failed tests and no detected socket/DNS attempts**.

The focused local tests and the existing test_database_safety and
database_target_selection suites ran with shared conftest disabled, plugin
autoload disabled and warnings treated as errors. The server identity helper
received mocked SELECT results. No actual SQL, SQLite fixture, engine connection
or live Neon re-attestation was used. Detailed pytest output was kept only in
transient memory to avoid exposing a credential-bearing Settings representation
if an assertion failed; reports contain counts and test identifiers only.

| Check | Observed result |
| --- | --- |
| Corrected .env and freshly loaded Settings | Accepted; official production ID and required development values match. |
| Real configured test URL, inspected only in memory | Accepted; exact development endpoint and neondb_test required. |
| Mocked approved server project/branch/endpoint/database | Accepted with both permitted endpoint contexts. |
| Official production branch as the requested test branch | Rejected before even the mocked SELECT calls. |
| Configured production endpoint, direct and pooler forms | Rejected. |
| Unapproved or malformed endpoint declaration | Rejected against the configured development URL. |
| Wrong project, production/unknown branch or unauthorized endpoint in server results | Rejected by complete identity comparison. |
| Wrong expected project/branch/endpoint against the approved server results | Rejected. |
| Actual database name neondb | Rejected. |
| Missing project, branch, protected branch or endpoint declaration | Rejected. |
| Missing server identity row, mutable/spoofed source or pending configuration | Rejected. |
| Invalid database/driver/host, route overrides and weakened TLS preferences | Rejected by existing regressions. |
| Stale inherited branch value in a temporary environment | Override observed; after restoration, the official .env value is effective again. |

The distinction between guard stages remains important: the branch declaration
helper checks syntax and protected-branch exclusion. The full server attestation
compares declared project, branch and endpoint with server-reported identities.
It does not discover the official production ID on its own. The correction fixes
the trusted local reference; it does not introduce a global hardcoded project or
change these responsibilities.

## 4. Evidence, unchanged scope and remaining gates

Local generated evidence is centralized under the ignored directory
artifacts/keycloak-k9-b3-fix:

- [Correction record](../artifacts/keycloak-k9-b3-fix/correction.json).
- [Configuration location inventory](../artifacts/keycloak-k9-b3-fix/configuration-locations.json).
- [Validation results](../artifacts/keycloak-k9-b3-fix/validation.json).
- [Complete validation runner](../artifacts/keycloak-k9-b3-fix/validate_configuration.py)
  and [focused test source](../artifacts/keycloak-k9-b3-fix/test_corrected_guard.py).
- [Scope verification](../artifacts/keycloak-k9-b3-fix/verification.json).

The correction is complete within its authorized local scope. Remaining gates:

1. Current recoverable points and a successful recovery into an independently
   authorized destination remain unverified. The previously reported six-hour
   history setting is not a substitute for that proof.
2. The working development database is not an approved E1 rehearsal destination.
   Branch creation and every migration execution still require distinct approval.
3. Any future connection must freshly attest its approved destination and exclude
   production plus working development when targeting a disposable rehearsal.
4. The inherited DEBUG value must be corrected in the actual launching terminal;
   this validation did not alter its parent or restart running services.

No database access or modification, migration, Alembic stamp, Neon branch,
identity link, Keycloak/Render/Telegram change or GitHub push occurred.
**Work stops after this correction and its offline validation.**
