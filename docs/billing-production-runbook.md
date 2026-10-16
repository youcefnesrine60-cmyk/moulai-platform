# MoulAI™ — Manual Payment and Recovery Plan; Production Deferred

This runbook prepares phase one: CCP/BaridiMob transfers, receipt submission, and administrative review through an authenticated API. A receipt alone never activates a subscription.

**Current user decision:** production remains deferred, and no migration, DML, or DDL is permitted in `neondb`. Authorized work is limited to `neondb_test`, local checks, and documentation. Do not request production approval again until all eight prerequisites below are complete and their report has been delivered. Every production, recovery, and deployment step described later is a future plan; documenting a command does not authorize its execution.

**Update, 2026-10-15:** production remains deferred. The user supplied Render startup results and limited historical recovery evidence dated 2026-10-14, identified the isolated development branch and endpoint, and configured the local connection. Render and historical recovery results were supplied by the account owner; the tools performed and passed the read-only development check described in section 2. The last reported production revision is `a91e7c2b4d10`, and the deferred migration target is `c413b7918a20`. The independently maintained test history was verified at `dce91870b4a2`; Alembic identifiers must not be compared as chronological values.

**Earlier read-only production check:** the earlier inspection established `existing_manual_schema_validation.compatible=true`, validating `manual_payment_receipts` and `manual_payment_audit` against the `c413b7918a20` contract. The previous blocker arose from differences in constraint-type representation between PostgreSQL and asyncpg; casting that type to `text` corrected it without weakening constraint checks. The installed revision remained `a91e7c2b4d10`. This result established that the two tables could be adopted at the time of that check; it was not a migration rehearsal. OIDC configuration remains incomplete, the webhook remains unregistered, and administrative identities were unchanged. Recheck the state when a later execution window is approved.

## 1. Confirm the Deployment Target and Authorization Boundaries

The approved repository is [youcefnesrine60-cmyk/moulai-platform](https://github.com/youcefnesrine60-cmyk/moulai-platform). The user confirmed the existing Render service `moulai-api`, service ID `srv-db7lblc9v7es73cfgfag`, URL `https://moulai-api.onrender.com`, branch `main`, and Frankfurt region. Do not create a replacement service. The build command is `pip install -r requirements.txt`, and the start command is `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. The reported `APP_ENV=development` setting does not establish database isolation; Render's connection has not yet been switched to development.

The user's binding instruction:

> Do not modify the production database or run migrations against it without separate approval.

This includes migrations and updates to `admins.auth_subject`. Preparing code or approving its deployment does not automatically authorize either operation. The latest decision defers both entirely. Do not add automatic migrations to build, startup, or pre-deploy commands, or change Render settings or the live bot registration during this preparation.

### Eight Prerequisites Before Any New Approval Request

| Prerequisite | Evidence required for completion |
| --- | --- |
| 1. Test migration rehearsal | Exercise the actual production migration step `a91e7c2b4d10` → `c413b7918a20` inside `neondb_test` using an isolated mechanism, and record successful fresh upgrade and adoption of existing tables. The `alembic_test` history has different identifiers and must be reported separately. |
| 2. Data, table, and foreign-key integrity | Compare schema, counts, constraints, and indexes before and after; demonstrate preservation of test receipts and audit history and rejection of orphaned data. |
| 3. Recovery | Establish a backup or PITR point for the approved production target, then demonstrate successful recovery to an approved isolated test destination with a validation report. A feature listed in provider documentation does not establish protection for this project. |
| 4. Permission impact review | The amended migration defines `payments.review` only; it does not automatically grant the permission to any role or bind an identity. A role holding `*` retains its existing broad capabilities, and earlier explicit grants are not automatically revoked. Record a comparison of roles and assignments before and after the step. |
| 5. No administrative identity changes | Demonstrate that no existing identity was modified or default `auth_subject` assigned; real identity binding remains a separate deferred operation. |
| 6. Application and Render stability | Identify the existing service, branch, and deployed SHA, and inspect health, startup, and configuration. Test the amended version in an approved environment using `neondb_test` before making it available in production. |
| 7. Migration and rollback plan | Define the execution window, responsible operators, recovery point, and target application version; rehearse isolated recovery procedures and establish stop and validation criteria. |
| 8. Final report | Deliver a concise report covering tests, results, gaps, and remaining risks, with evidence for the preceding seven prerequisites, before presenting any new approval request. |

The previously inspected production schema compatibility contributes to the review; the other prerequisites still require their own evidence. Do not claim production readiness or successful deployment and recovery before documenting them.

## 2. Work Authorized Now and Subsequent Validation

### Approved Target and Connection Guard

The Neon project is `moulai-db` (`shiny-lab-60817779`) in Frankfurt. The protected `production` branch is `br-plain-firefly-as17li6w`; the permanent working `development` branch is `br-lively-truth-asga1dtk`. The only test target is `development → neondb_test`, not the database named `neondb_test` on the old production branch.

Configure these settings locally without sending connection values to the chat: `TEST_DATABASE_URL` using `postgresql+asyncpg`, `TEST_DATABASE_ENDPOINT_ID` with the actual development endpoint ID, and `PROTECTED_DATABASE_ENDPOINT_ID` with the excluded production endpoint ID. The guard accepts the direct endpoint or its pooler and rejects query options that reroute the connection. The user confirmed the association between `ep-quiet-rain-assrs0gv` and `br-lively-truth-asga1dtk` in project `shiny-lab-60817779`; a database name alone does not identify its branch.

**Superseded initial state, 2026-10-15:** the first local check found the test and primary URLs using the same production endpoint, so the guard blocked connection before any writes. The user subsequently configured the development connection locally. The `--reset` option and the old `clear_test_data.py` and `create_test_tables_debug.py` tools were removed; do not use reset tools.

**Actual development result, 2026-10-15:** read-only validation passed with TLS certificate and hostname verification. It established database `neondb_test`, project `shiny-lab-60817779`, branch `br-lively-truth-asga1dtk`, endpoint `ep-quiet-rain-assrs0gv`, revision `dce91870b4a2`, and 47 public tables. The actual PostgreSQL version was `server_version_num=180006`, meaning 18.6. This check changed neither data nor schema.

The guard checks actual `pg_catalog.pg_settings` values: `branch_id` and `project_id` must have `postmaster` context and match the approved values. `endpoint_id` is accepted only with `postmaster` or `superuser` context, `source='configuration file'`, `setting=reset_val` matching the approved endpoint, and `pending_restart=false`. The actual endpoint had `superuser` context; it is not treated as immutable within a session. TLS, hostname, branch, project, and database verification remain mandatory; session, client, role/database overrides, and disallowed contexts are rejected. The initial stricter guard rejected the connection before any writes; the remaining conditions were not weakened to accept the observed context.

Run the rehearsal alone on the approved connection, without pytest or another writer:

```powershell
$env:DEBUG = 'false'
.venv\Scripts\python.exe scripts/billing_test_rehearsal.py
```

The tool exercises the real production billing migration step inside a rollback transaction on the test database maintained under the dce history: fresh table creation, adoption of existing tables, and drift rejection. It stages the preceding billing-field state inside the transaction only; it does not replay the complete production migration history. Data, permissions, constraints, and idempotency are checked, then public-table data, schema definitions, and sequence states are compared with the baseline after rollback. The traditional fixtures that truncate test tables are not used for this rehearsal. Preparing the tool or passing its offline guard tests does not establish that the live rehearsal succeeded.

**Final rehearsal result:** the actual fresh, adoption, and drift scenarios passed. Fresh and adoption each enforced ten constraint checks and demonstrated repeatability without additional effects; adoption preserved existing payment evidence. The tested data, existing owner identity, grants, and subscription states were preserved, without binding an administrative identity or adding automatic role grants. Drift rejected schema differences before core billing changes. Measured rollback after all three scenarios established matching public rows, schema definitions, indexes, constraints, sequence states, and Alembic state; `dce91870b4a2` and 47 tables remained, with no persistent changes or production access. The [sanitized results](../artifacts/billing-production-review/development-rehearsal-results.json) document the scope; their SHA-256 matched `scripts/billing_test_rehearsal.py`. See the [development report](billing-development-verification.md) for details. This is a migration and transactional rollback result, not archive recovery or PITR.

Final local verification: **113 non-overlapping cases**, comprising 76 standalone unittest cases with `-W error` and 37 pytest cases using `--noconftest --no-cov` (13 payment transaction cases, 3 SQLite schema cases, and 21 manual payment contract cases). The 76 include twelve target-selection cases and 21 startup/begin-guard cases, after five cases were added to the earlier 16. The earlier 13 are included in the 37 and must not be added again. Do not attribute `-W error` to the pytest group without supporting evidence; this was not a rerun of the earlier full suite.

Specific diagnosis: the receipt constraint correctly prevented deletion of its linked payment, but the rehearsal expected `23503` instead of PostgreSQL 18's `23001` for a `RESTRICT` violation. Only that expectation was adjusted according to the server version, and all seven negative receipt cases passed before the complete rerun. This corrected the rehearsal without weakening the migration constraint; details and the official source are in the development report.

Run the migration rehearsal and checks on `neondb_test` only. Record the verified destination by database name without a DSN, and use the isolated test session. Do not point `DATABASE_URL` at production to run a test, or bypass the operational `migrate` command's guard to run it on the test database. Document the production migration step's test inside the isolated database using its dedicated tool and source SHA.

Rehearsal evidence includes revisions before and after, preservation of test content and counts, column/constraint/foreign-key/index checks, drift failure without partial writes, permitted repetition without additional changes, and RBAC impact without identity binding. Keep receipt data and restaurant identities out of the published report.

### Local Startup and ORM Target Selection

The `database schema needs migration` error when starting `app.main` resulted from selecting the primary `DATABASE_URL` and the production schema at `a91e7c2b4d10`, whose migration remains deferred. This error does not authorize a production migration or bypassing schema validation.

Central connection selection through `DATABASE_TARGET=primary|development` was added and passed twelve tests. The tools added `DATABASE_TARGET=development` to the local Git-ignored `.env`, while verifying that `DATABASE_URL` and `TEST_DATABASE_URL` remained unchanged. Do not infer the test connection from `APP_ENV` alone. This is a local choice, not a Render or OIDC configuration change or an instruction to deploy a new version.

**Actual local startup passed:** the [startup evidence](../artifacts/billing-production-review/development-startup-results.json) records `completed=true` at `2026-10-15T13:59:59.448656+00:00`: real `init_db`, lifespan startup and shutdown, exactly one real `close_db` call, a read-only session, and HTTP 200 for `/` and `/health` with health-content validation. No outbound HTTP connections occurred and production was untouched. All four source hashes matched the actual files.

The current pooler connection established `transaction_read_only=on` with `default_transaction_read_only=off` and a begin guard installed on the verifier's engine. Read-only mode is enforced at the start of every transaction on that engine, and checking the current mode remains mandatory; the default value is not a substitute. The check restored the original global bindings after using the isolated engine and session factory. This was actual local ASGI verification, not Render verification, deployment, or OIDC/Telegram binding.

To run locally from `D:\MoulAI` with `DATABASE_TARGET=development` saved locally:

```powershell
$env:DEBUG = 'false'
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The old `payment_webhook.py` and `stripe_webhook.py` files are absent on disk and have no imports in app/tests/scripts. Stale IDE tabs were not the cause of the reported traceback and do not justify restoring removed payment paths. The `sync_transaction` guard for `None` and seven keyword calls in the payment transaction path were corrected. The 13 transaction cases included in the 37 cover these changes; no production test or deployment is claimed.

**The next production preflight is deferred to a later approved window.** At that point, use PowerShell from the project directory:

```powershell
Get-Location
$env:DEBUG = 'false'
.venv\Scripts\python.exe scripts/billing_operations.py preflight --telegram --output production-preflight.json
```

The `--output` option accepts a JSON filename only, without a path, and saves the report independently under `artifacts/billing-reports/`, which is excluded from Git and Docker. Do not redirect console output mixed with logger records into a `.json` file. Only `preflight` and `constraint-diagnostics` support this option. The four reports recovered locally from earlier captures are listed in the [report index](../artifacts/billing-reports/INDEX.md). This repaired historical files; it did not rerun checks or establish a new production state. The next check remains deferred to the approved window described above.

Review `database_name=neondb`, `installed_revisions`, and `expected_revision`. Require `existing_manual_schema_validation.compatible=true`, including validation of both existing tables. The report exposes missing beneficiary/OIDC setting names and administrative status without account values or secrets. Do not bypass drift results or use `stamp` or `create_all` to correct them.

## 3. Prepare the Real Configuration Checklist

Review setting names now without publishing secrets or changing production environment variables. Later, configure their values in the local environment running the CLI and in **Environment for the specified Render service**; editing local `.env` does not update Render. **Save only** stores settings without deploying and defers their use until a later deploy. Do not select it during the current phase. See [Render environment variable documentation](https://render.com/docs/configure-environment-variables).

| Setting | Required value |
| --- | --- |
| `APP_ENV` / `DEBUG` | `production` / `false` on the live service |
| `DATABASE_URL` | The actual approved production database connection; do not publish its value |
| `MANUAL_TRANSFER_BENEFICIARY` | The real beneficiary name from the account documentation |
| `MANUAL_CCP_ACCOUNT` / `MANUAL_CCP_KEY` | The official CCP number and key |
| `MANUAL_BARIDIMOB_RIP` | The official RIP for the same approved postal account |
| `MANUAL_CCP_ENABLED` / `MANUAL_BARIDIMOB_ENABLED` | Enable only methods whose instructions are fully configured |
| `BOT_TOKEN` | The real bot token, stored as a secret |
| `TELEGRAM_WEBHOOK_SECRET_TOKEN` | A securely stored random secret that matches locally and on the service |
| `APP_URL` / `WEBHOOK_URL` / `WEBHOOK_PATH` | HTTPS for the approved service, the actual webhook URL, and `/webhook` |

Verify the CCP number, key, and RIP against the same account's documentation. Do not derive RIP from a CCP number, fill in test values, or publish unapproved beneficiary details. Exclude `.env`, connection credentials, and bot secrets from GitHub and source exports.

## 4. Backup Evidence and Recovery Testing Without Production Changes

### Evidence Supplied by the Account Owner

The user reported successfully creating the independent historical branch `moulai-restore-verification` (`br-icy-tooth-asgteeou`) from production at `2026-10-14 14:00 GMT+1`, then reading it without replacing production. The reported comparison matched 47 tables, revision `a91e7c2b4d10`, and counts admins=1, owners=1, payments=0, and subscriptions=0. This is practical historical recovery evidence within that scope, supplied by the user. The tools did not repeat it, and it did not cover hashes of all rows, every relationship, or operational load.

The reported history window is 6 hours. The verification branch's reported deletion deadline, `2026-10-15 14:26:08 GMT+1`, had passed when the final result was prepared; its continued existence was not checked afterward. Do not use it for ongoing development or assume that it or the previous day's recovery point remains available. Before any future production request, verify a recent available point and a recovery plan that preserves the required data. See the [official recovery-window limits](https://neon.com/docs/postgres/backup-restore/branch-restore).

There is currently no verified Neon dashboard access or confirmed recovery archive available to the tools. Procedures can be prepared from official documentation without connecting to production, but protection for the actual project requires documented account-owner evidence or approved access. Do not create branches or snapshots, change the history window, or modify provider resources during this preparation.

### A. Read-Only Metadata Evidence

The account owner records the correct project and branch, its `root` or `child` type, its relationship to the branch containing `neondb_test`, and the actual **History window** from **Settings → Postgres**. Record the inspection time in UTC, the oldest available point, and the candidate pre-migration recovery time. Do not infer retention from the plan name. Recovery availability depends on the actual window, and changing it affects the project; inspect it without selecting Save. See [History window documentation](https://neon.com/docs/postgres/backup-restore/history-window).

With approved access, the official read-only `GET` alternative provides [project details](https://api-docs.neon.tech/reference/getproject), including history retention, and [branch details](https://api-docs.neon.tech/reference/getprojectbranch), including `parent_id`. Retain only evidence of identity, scope, and retention. Do not expose raw responses, owner information, connection strings, or API keys. These requests were not executed during the current preparation.

The account owner can inspect a candidate point through **SQL Editor → Time Travel** using metadata queries and aggregate counts for the selected database. These are historical read-only queries, but Neon creates temporary provider resources for them; do not run them during this phase without an approved access scope. Inspect the point without selecting Restore, and distinguish successful historical reads from actual recovery. See the [official Time Travel documentation source](https://github.com/neondatabase/website/blob/main/content/docs/postgres/backup-restore/time-travel-assist.md).

### B. Select a Recovery Rehearsal Method

1. Use a documented existing archive or confirmed historical point, and identify an approved test destination separate from production and ongoing tests. The execution database remains `neondb_test`. Creating other resources or copying actual production data requires an explicit later scope; the word "test" alone does not authorize it.
2. If an existing archive is available, inspect its table of contents and checksum locally without a production connection. Document the source name and timestamp, PostgreSQL version/extensions, and ownership/ACL handling. Restore only to the approved destination, then validate schema, data, constraints, sequences, and application behavior. Listing an archive's contents alone does not satisfy the recovery requirement.
3. If `pg_dump` is selected later, use tools compatible with the actual PostgreSQL version and a direct, non-pooled connection. Creating a new archive from `neondb` is not an action performed now. Keep archives under private access control and exclude them from GitHub and source packages, because they may contain receipts and other data. Neon supports `pg_dump`/`pg_restore`. See [backup and recovery documentation](https://neon.com/docs/manage/backup-pg-dump).
4. If PITR is selected, test the operation on an approved branch meeting provider requirements, or create an approved isolated historical copy for validation. Do not select Restore on production. **Instant restore supports root branches only, replaces every database on the branch, and temporarily disconnects its connections.** If a branch contains both `neondb` and `neondb_test`, restoring that branch affects both; different database names do not isolate this operation. See [Instant restore documentation](https://neon.com/docs/postgres/backup-restore/branch-restore).

### C. Evidence of Successful Recovery Testing

Record the isolated test destination, source recovery time in UTC or archive SHA256, restored revision, start/end times, and validation of revision, tables, counts, constraints, and sequences. Also record application startup without sending live messages or notifications. Compare results with the reference values preserved from the available source. The responsible operator defines acceptable data loss (`RPO`) and target recovery time (`RTO`); record measured elapsed time rather than claiming those objectives from generic documentation.

Restoring synthetic test data demonstrates the procedure on the test environment. Prerequisite three is complete only when the result is tied to a confirmed backup or recovery point for the approved production target. Without that evidence, the prerequisite remains incomplete and production remains deferred.

## 5. Future Production Migration Plan — Currently Prohibited

Limited historical evidence supplied by the user is now available, as described in section 4. A suitable point must still be shown to remain available at a later execution window. Schema checks do not replace a current, executable recovery plan.

After completing all eight prerequisites and delivering the report, the specific operation can be presented for separate review: **`neondb`: `a91e7c2b4d10` → `c413b7918a20`**, with fresh checks, a still-available recovery point, and a deployment-window plan. Do not request approval now. These commands are retained for the future plan only and must not be executed under the current scope:

```powershell
.venv\Scripts\python.exe scripts/billing_operations.py migrate --confirm-database neondb --expected-revision a91e7c2b4d10
.venv\Scripts\python.exe scripts/billing_operations.py preflight --output production-post-migration-preflight.json
```

Before later approved execution, verify the SHA, PostgreSQL version, revision, and branch scope. Pause planned writes throughout the window so recovery cannot discard unaccounted changes. If the current or target revision changes, stop the plan until the actual state is reviewed. The migration runs under a deployment lock in one transaction, adopts the two matching tables without dropping or recreating them, and rejects column, constraint, or index differences. It adds `payments.payment_provider`, `payments.currency`, and `admins.auth_subject` with a unique constraint, and defines `payments.review` only, without automatic role grants or identity binding.

Success criteria are `c413b7918a20` and `billing_schema_ready=true`, preserved receipt and audit data, RBAC effects matching the review, unchanged administrative identities, and successful startup/health checks for the specified application version. Startup failure caused by a missing schema blocks deployment of the new version; it does not justify `create_all`, `stamp`, or automatic migration.

## 6. Render, Rollback, and Recovery Plan

The user identified the service, branch, and build/start commands in section 1 and reported `Application startup complete`, `GET / 200`, and `Your service is live`. The deployed SHA, Auto-Deploy setting, and any pre-deploy command still need verification. Direct HTTP checks by the tools failed with ConnectError, including a retry outside network isolation; this does not establish a service outage. No deployment or connection-setting change was performed. Review connection status and setting names while keeping secret values private.

The stability prerequisite establishes the state of the currently deployed version and includes testing the amended version in an approved Render environment using `neondb_test`, if available. Do not create another service, automatically change the existing service's connection to the test database, or deploy a version requiring `c413b7918a20` against the deferred `neondb` target to satisfy this prerequisite.

### Deployment After the Prerequisites and Later Authorization

1. In Settings for the user-specified service, verify the linked repository and branch, build/start/pre-deploy commands, and Auto-Deploy setting. Pushing a commit to a linked branch may deploy it automatically. Do not push to that branch during the deferral or add migrations to deployment commands.
2. The user authorized uploading the reviewed version after successful tests. Before pushing `main`, review Render's connection to the approved `development → neondb_test` target and the Auto-Deploy setting, because pushing may immediately deploy it. The service connection has not yet been switched, so do not push the new code now. A development deployment does not require the deferred production migration. Record the commit SHA when the development-deployment conditions are satisfied, and include no automatic migration.
3. In Deploys, deploy that approved commit, then verify successful build, startup, health checks, and deployed SHA. **Restart service** restarts the current version with its previous settings; it does not apply newly saved environment settings. See [Render deployment documentation](https://render.com/docs/deploys).

Do not select the latest commit solely because it is the newest. The service, branch, and SHA are actual decisions to verify before execution. This process does not require exposing an API key or deploy hook.

### Failure Decisions

| Condition | Action in the future plan |
| --- | --- |
| Migration fails before commit | Verify transaction rollback and preserved revision, schema, and reference data; retain the stable deployed version. Do not use stamp to bypass failure. |
| Migration succeeds but the application fails | Stop deployment and writes. Review the cause and the previous version's compatibility with the new schema before rolling back code. Do not assume Render rollback restores the Neon database. |
| Data corruption or recovery required | Identify a tested source point, branch scope, all affected databases, and subsequent changes, then recover under a separate later plan and approval. Verify the database and service before resuming writes. |

Identify a successful Render version and available build artifact for rollback in advance, and review the effects of restoring that version's settings and environment groups. Dashboard rollback disables auto-deploy; database changes remain a separate operation. See [Render rollback documentation](https://render.com/docs/rollbacks).

Do not use `alembic downgrade` to recover payment evidence: this revision's downgrade drops the receipt/audit tables and added columns. Use a tested recovery method that preserves data, accounting for subsequent changes and all databases within the branch's scope. Any production recovery operation remains prohibited during the current deferral.

## 7. Telegram After a Later Approved Deployment

After completing the prerequisites, obtaining later authorization, and deploying successfully, use the local environment holding the same secret. Do not execute these commands during the deferral:

```powershell
$billingWebhookUrl = Read-Host 'HTTPS webhook URL for the approved service'
.venv\Scripts\python.exe scripts/billing_operations.py configure-webhook --url $billingWebhookUrl
.venv\Scripts\python.exe scripts/billing_operations.py preflight --telegram --output production-telegram-preflight.json
```

The script first verifies that the server rejects an unauthenticated update with 403 and accepts the current secret with an empty update that sends no message. It then registers the webhook while preserving pending updates and verifies the registered URL. Do not register a webhook until the deployed version uses the same secret.

**Current Telegram scope:** owner invoices and receipt upload in private chats. Administrative payment approval is not available through chat IDs or Telegram buttons, and no configuration flag enables that path.

## 8. Keycloak and Later Administrative Review

Leave OIDC settings unset until the realm, API client, and actual reviewers are ready. When provider configuration is absent, the administrative API returns 503 before looking up an admin in the database, even without a bearer token; the owner path without a bearer token remains 401. An `admin_id` or `chat_id` alone never opens administrative access.

Obtain `OIDC_ISSUER` from `issuer` in the approved realm's HTTPS discovery document and `OIDC_JWKS_URL` from `jwks_uri` in the same document. Do not guess the host or realm. See [Keycloak endpoint documentation](https://www.keycloak.org/securing-apps/oidc-layers).

Set `OIDC_AUDIENCE` for the actual API and include it in the **access token** `aud` using an appropriate Audience mapper attached to the client scope actually used. Verify a signed access token valid for the API; do not substitute an ID token or disable audience checks. See [Keycloak Audience documentation](https://www.keycloak.org/docs/latest/server_admin/index.html#_audience).

The current application contract requires an `RS256` signature, a valid `kid`, and a header `typ` of `JWT` or `at+jwt`. The token payload must contain `typ=Bearer`, valid integer `iat` and `exp`, and verified `iss`, `aud`, and `sub`. Test these requirements against an actual access token issued by the approved realm; do not create a substitute local reviewer token.

Once the values are ready, reviewer authorization depends on a verified `sub` linked to `admins.auth_subject`, an active admin, and an active RBAC role granting `payments.review`. Binding updates remain deferred now. Review that operation and request separate approval only after the prerequisites and report are complete and production work is opened later. The following documents the future path; enter actual values without a default identity:

```powershell
$billingAdminId = [int](Read-Host 'Approved administrator ID in the database')
$billingAdminSubject = Read-Host 'Actual verified Keycloak sub for the same reviewer'
.venv\Scripts\python.exe scripts/billing_operations.py bind-admin --confirm-database neondb --admin-id $billingAdminId --subject $billingAdminSubject
```

Binding does not automatically grant a role or silently replace an existing identity. Review payments only through the authenticated API: the reviewer verifies actual credit in the postal account record independently of the image and records the reference, amount, currency, and note. Atomic approval activates the subscription. Until Keycloak and binding are complete, receipts and invoices remain pending. See the [payment integration strategy](payment-integration-strategy.md) for contract details.

## 9. Report and Remaining Non-Secret Information

Deliver a concise report tying every prerequisite to its evidence: test commands, SHA, revision, results, data/RBAC/identity effects, backup and recovery evidence and timing, service, branch, live SHA and health, rollback criteria, and gaps. Pending access, backup, or Render verification must not be presented as completed work. Do not request migration approval again until the report and prerequisites are complete.

Collect the following information together, without passwords, DSNs, or API keys:

- Local: connection identity, TLS, all three migration scenarios with rollback, schema validation, and actual read-only development application startup passed. Repeat checks after material changes without resetting the database.
- Render: deployed SHA, Auto-Deploy and pre-deploy state, and review of switching the connection to development before pushing or deploying `main`.
- Recovery: recheck an available point, acceptable data loss, and recovery time at a future execution window. The previous day's report and temporary branch do not guarantee permanent retention.

No backup contents, receipt images, or tokens need to be sent to provide this information. Continue independent work on `neondb_test` and documentation; production remains frozen.

This update did not access the Render account, push GitHub changes, deploy, modify service or OIDC settings, bind an admin, or register a webhook. The [catalogue option isolation finding](catalog-options-isolation-finding.md) remains open. These results concern billing and test guards only and do not establish production readiness for the rest of the platform.
