# Render development configuration: prepared, not activated

**Historical preparation record.** On 2026-10-21, the operator reported successful
publication and deployment of the separate Health-Only correction. The dated
observations and proposed variables below retain their original scope; they are
not a current Render configuration inventory. The Health-Only gate supersedes
the earlier integration-disable proposals. See the
[final synchronization record](github-final-sync-preparation.md).

Date: **2026-10-20**. Service: `moulai-api` /
`srv-db7lblc9v7es73cfgfag`. Reviewed deployed source: `7a66763`, branch `main`.
No Render configuration, application code, Neon schema/data, Telegram setting,
deployment or Git publication was changed. K9/K10 campaigns were not repeated.

The [locally prepared Health-Only correction](render-health-only-validation.md)
now supplies the proposed traffic/transaction isolation. Its flag is false by
default and it has not been published or deployed. It supersedes the earlier
proposal to remove the Telegram secret: preserve that secret and use the outer
503 gate instead. The historical deployed-source observations below remain valid.

## Current read-only observations

Neon control-plane reads and the existing fail-closed SQL identity helper agree:

| Item | Observed value |
| --- | --- |
| Project | `shiny-lab-60817779` |
| Branch | `development`, `br-lively-truth-asga1dtk`; ready |
| Parent excluded from the test target | `br-plain-firefly-as17il6w` |
| Endpoint | `ep-quiet-rain-assrs0gv`; belongs to development, enabled |
| Database | `neondb_test` |
| Installed test-history revision | `dce91870b4a2` |
| Public tables | 47: 46 business tables and `alembic_version` |
| Observation transaction | READ ONLY; rolled back; TLS CA/hostname verified |

The exact deployed application and its existing startup verifier were exported
from Git into ignored local storage. The real `init_db` validated the schema,
startup and shutdown completed, and local ASGI `GET /` and `GET /health` returned
**200/200**. The earlier static inventory establishes the deployed model's 392
business columns; the real validator found no missing table/column on the current
development target. No migration is required to satisfy this startup contract.
This presence check does not certify every type, constraint or business workflow.

The verification engine enforced READ ONLY at every transaction start. The server
reported current transaction mode `on`, but default mode `off`; the current
default is not a read-only protection for the ordinary deployed application.
No database connection to production was opened. One initially restricted local
process failed with `PermissionError`; its result is retained separately before
the authorized read-only connection succeeded.

The application observation used local installed packages, isolated sessions,
Redis disabled in that process, outbound HTTP blocked and a network allowlist
limited to the approved development destination. No external HTTP transport call
or forbidden network event occurred. It is a guarded local observation of the
deployed source, not a Render deployment or proof of all remote runtime behavior.

Local evidence remains ignored under `artifacts/render-development-preparation/`:
`control-plane.json`, `startup-observation.json`, `network-policy.json`, the
complete verification helper, and the exact source export with its startup
report/hashes. No connection URL or credential is written into these reports.
The Windows source export changed line endings; normalized source and AST checks
match the deployed Git source for the verifier and its three recorded application
modules. Their observed hashes are retained with a separate comparison record.

## Startup and post-startup effects

- `init_db` inspects the schema and performs identity checks. It does not run
  migrations, seed data or create tables. Callback registration only records
  handlers in memory; its seven registration functions call the router/logger.
- `app/core/redis_client.py` performs a real Redis `PING` at import when the
  environment `REDIS_URL` is nonempty. Shared production Redis is therefore
  unsuitable for an isolated startup observation. An explicitly empty value
  avoids this import-time connection and selects the existing memory fallback.
- AI and Telegram HTTP clients are constructed at import; no AI generation,
  Telegram send or `setWebhook` operation was observed during startup. Incoming
  requests can later invoke these operations. Registering local callbacks does
  not register Telegram's remote webhook.
- Development target selection does not make `get_db` sessions read-only.
  The current endpoint is read/write. A concrete exposure exists in this exact
  commit: the users router has no router authentication dependency, and its
  create endpoint calls a repository capable of committing writes. It is not
  protected by the newer feature branch's global-user authorization correction.
  No mutation request was sent to test this finding.
- An already registered real Telegram webhook could resume delivery when this
  service becomes healthy. With a matching configured secret, requests can
  execute business actions, send messages and access real payment instructions.

**Decision boundary:** schema compatibility is confirmed. A public zero-unintended-
write service is not guaranteed by an environment-variable change. Before any
live activation, establish an actually available traffic isolation mechanism
for mutating API routes, or an independently approved read-only database access
arrangement. No such role, access control or new service was created here.
Disabling Telegram alone does not isolate the REST API. Keep activation pending
if the required isolation cannot be demonstrated for this old commit.

## Exact variable proposal and known presence

Render itself was not inspected through an authenticated configuration tool.
The operator confirmed the following presence-only inventory on 2026-10-20 in
Render Environment, including DEBUG=false and DB_ECHO=false. Local `.env`
contents do not establish Render values. Presence does not establish that a
secret connection URL or an existing endpoint value has the correct destination.

| Variable | Known Render state | Proposed action after approval |
| --- | --- | --- |
| `APP_ENV` | Present: `development` | Keep. |
| `DATABASE_TARGET` | Present: `primary` | Change to `development`. |
| `DATABASE_URL` | Present: production/neondb | Keep exactly unchanged. |
| `TEST_DATABASE_URL` | Present; destination not independently inspected | Verify privately against development/neondb_test; correct only if necessary. Require the asyncpg connection and verified TLS. |
| `TEST_DATABASE_PROJECT_ID` | Absent | Add `shiny-lab-60817779`. |
| `TEST_DATABASE_BRANCH_ID` | Absent | Add `br-lively-truth-asga1dtk`. |
| `TEST_DATABASE_ENDPOINT_ID` | Present; value unconfirmed | Keep only if `ep-quiet-rain-assrs0gv`, without the pooler suffix; otherwise correct. |
| `PROTECTED_DATABASE_BRANCH_ID` | Absent | Add `br-plain-firefly-as17il6w`; reject the earlier transposition. |
| `PROTECTED_DATABASE_ENDPOINT_ID` | Absent | Add `ep-billowing-term-as9aufue`. |
| `DEBUG` | Confirmed `false` | Keep. |
| `DB_ECHO` | Confirmed `false` | Keep. |
| `REDIS_URL` | Render instance and production sharing unverified | For the isolated observation, propose an explicitly empty value; otherwise review a dedicated development instance separately. No change made. |
| `TELEGRAM_WEBHOOK_SECRET_TOKEN` | Effective Render value uninspected; bot correspondence unverified | If Telegram exclusion remains necessary, propose removing it from this service's effective configuration: `/webhook` then returns 503 before dispatch. This can interrupt a real bot and requires explicit approval. |
| `MANUAL_CCP_ENABLED` | Current state unconfirmed | Propose `false` during the isolated observation. |
| `MANUAL_BARIDIMOB_ENABLED` | Current state unconfirmed | Propose `false` during the isolated observation. |
| `BOT_TOKEN`, `OPENAI_API_KEY`, `SECRET_KEY` | Startup passed Settings validation; exact source/presence not inspected | Preserve privately; do not blank required fields as an integration-disable mechanism. |
| `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL` | Current state unconfirmed | Preserve; no authentication activation or identity binding in this operation. |
| `OIDC_DIAGNOSTICS_ENABLED`, `OIDC_ALLOW_LOCAL_HTTP` | Current state unconfirmed | Keep false where present; `7a66763` does not consume these later settings, so they are not a runtime isolation switch for this commit. |
| `DATABASE_SYNC_URL`, `TEST_DATABASE_SYNC_URL` | Current state unconfirmed | No change; canonical startup uses asyncpg. The legacy Psycopg helper is not initialized by the lifespan. |

The exact confirmed additions are the four absent project/branch/protected keys
above. For a present key, **keep if matching, correct only if mismatching**.
Effective secret removal must also account for linked
environment groups; avoid modifying a shared group. Service-specific variables
take precedence over groups according to
[Render's environment documentation](https://render.com/docs/configure-environment-variables).

## Telegram and Redis: actual read-only follow-up

At **2026-10-20 17:37:27 UTC**, the existing sanitized Telegram API request
function from `scripts/billing_operations.py` was reused for **getWebhookInfo
only**, using the locally configured bot credential in memory. Its function
definition was loaded independently to avoid importing application/Redis/database
initializers. No message, webhook change or update acknowledgement was sent.

| Question | Actual result | Limit |
| --- | --- | --- |
| Does this bot's webhook point to moulai-api? | **No.** Telegram returned an empty registered URL. | Applies to the bot represented by local configuration; equality with Render's bot credential is not established. |
| Are updates pending or delivery errors reported? | **0** pending; no delivery error returned. | Current status, not proof that the bot has never been used. |
| Is real user/business usage established? | **No evidence establishing it.** | No user messages, chat history or business data were retrieved. No inference of inactivity is made. |
| Is Render Redis shared with production? | **Undetermined.** | No authenticated Render environment access or production consumer/resource inventory is available. |

An empty webhook URL means no webhook is configured for the queried bot; pending
updates are updates awaiting delivery. Those fields do not establish successful
business use or the identity of another deployment's bot.
[Telegram WebhookInfo](https://core.telegram.org/bots/api#webhookinfo).

The first network-restricted request failed with ConnectError; its sanitized
evidence is retained. The subsequent approved network request succeeded. Neither
attempt recorded the token, request URL, raw response, connection string or raw
exception text. Both reports and the complete diagnostic source are retained
locally, ignored by Git, as `external-bindings-*.json` and
`inspect_external_bindings.py` under `artifacts/render-development-preparation/`.

The local Redis configuration is present, but it does not identify Render's
effective instance. No Redis connection or application import was performed.
No Render connector/CLI or configured Render API credential is available to
inspect that service's effective environment. Repository configuration and
existing evidence do not supply a verified mapping between Render and a
production Redis resource. A PING against the local address would not resolve
that missing mapping.

The exact deployed state repository builds keys as `user:{chat_id}` without an
environment namespace. If development and production use the same Redis instance
and logical database, normal state writes could overlap. This is a conditional
code risk, not evidence that such sharing currently exists.

To close the two remaining remote-configuration questions, compare privately
the bot identity configured in Render with the inspected local bot, and compare
the effective Redis resource ID/endpoint/port across Render and each production
consumer, including their logical database selections and provider aliases.
Different logical Redis databases still share the instance. Report only whether
the bots match and whether a production consumer uses that Redis resource; do
not copy tokens, passwords or connection URLs into this document. If they cannot
be verified, retain the unknown status and keep public activation pending.

## Simple application and rollback procedure — not executed

1. Before any change, privately record effective variables, whether each key
   originally existed, service ID, source branch, exact build SHA and automatic
   deployment state. Preserve secrets only in approved private storage. Resolve
   the API traffic isolation, Redis and live-bot questions above first.
2. After explicit configuration approval, edit only the approved keys for this
   service. Use **Save only** to avoid deployment; the new values are used at
   the next deployment, not immediately. Do not edit a linked shared group or
   import the working `.env` wholesale.
   [Render save behavior](https://render.com/docs/configure-environment-variables).
3. Only after separate deployment approval, select the reviewed build/commit
   explicitly. A generic restart is not the method for applying saved-only new
   values: Render documents restarting with the deployed environment. Verify
   the intended SHA and configuration at the deployment boundary. Check only
   `GET /` and `/health`, the development target/identity and successful schema
   validation; do not exercise mutation routes or Telegram/AI actions.
   [Render deployment behavior](https://render.com/docs/deploys).
4. If changes were merely saved, cancel them by restoring the private snapshot
   with Save only and removing keys originally absent. If a later authorized
   deployment is unhealthy or receives unwanted traffic, contain its traffic
   under the approved operational plan, restore exact prior configuration and
   use a separately approved deployment decision. Restoring `primary` returns
   to the known incompatible production configuration; it is a safe startup
   refusal, not restored service availability. No database rollback or restore
   is justified by a configuration-only change. Preserve unexpected evidence
   instead of resetting development data.

**Prepared outcome:** the current development target is compatible with the
deployed startup contract. The requested Render variable-presence inventory is
now supplied. The locally configured bot has no registered webhook; Render bot
correspondence and Redis production sharing remain unverified. Public activation
remains conditional on effective destination checks and actual request/integration
isolation. Nothing was activated, migrated, published or changed on
Render/Neon/Redis/Telegram by this preparation.
