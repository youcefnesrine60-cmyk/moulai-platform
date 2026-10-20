# Administrative session credential transport

Administrative session operations require a verified Keycloak access token and
the current `admins.manage` permission. A legacy session token, administrative
identifier, or Telegram chat identifier never grants API access by itself.

## Credential transport

Session lookup credentials travel in the `X-Admin-Session-Token` request header.
They must contain a non-whitespace character and have a maximum length of 255
characters. Surrounding whitespace is removed before the service lookup.

All paths below use the `/api/v1/admin-sessions` prefix.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/lookup` | Read a session by its credential. |
| `GET` | `/lookup/active` | Read an active session. |
| `GET` | `/lookup/status` | Read session status. |
| `PATCH` | `/lookup/activity` | Update session activity. |
| `DELETE` | `/lookup/deactivate` | Deactivate one session. |

Bulk deactivation keeps the `DELETE /admin/{admin_id}/all` path. To preserve one
session, provide its credential in the optional `X-Preserve-Session-Token` header.
Omitting that header explicitly requests deactivation of every session for the
selected administrator. An empty, blank, or oversized header returns `422`
before the service can perform the operation.

The existing `PATCH /extend` operation keeps its session credential in the JSON
body. Session creation and response schemas remain unchanged.

## Client migration

The former `/token/{session_token}` paths and their suffixes have been removed.
They return `404`; there are no compatibility aliases. Update clients to the
static paths above and send the credential in the documented header.

The former `except_session_token` query parameter has also been removed. Requests
that put `session_token` or `except_session_token` in an administrative session
URL query return `422`. Rejection prevents an old preservation parameter from
being silently ignored during bulk deactivation.

Use the normal `Authorization: Bearer` header for the Keycloak access token in
addition to the appropriate session credential header. A session credential
header alone still fails authentication. A verified identity without the
required permission receives `403` before any session operation.

## Logging and operations

The supported request URLs contain no session credentials. Application event
logs continue to omit session tokens, including storage exceptions with bound
parameters. Standard Uvicorn and HTTPX request logs can therefore record these
supported URLs without disclosing a session token from the URL.

Clients must stop sending the retired credential URLs: a server or proxy can
log a received URL before the application rejects it. Configure any proxy,
request tracing, or debugging facility to exclude `Authorization`,
`X-Admin-Session-Token`, `X-Preserve-Session-Token`, and sensitive JSON fields
from captured headers or bodies. Headers and responses require HTTPS in transit.

No database migration, real identity binding, deployment, or production data
change is required by this HTTP contract update.

## Verification

Offline HTTP tests exercise successful header delegation, whitespace
normalization, required and optional header validation, removed routes,
credential query rejection, permission failures, and OpenAPI parameter locations.
They also check that the HTTPX request log for supported session operations
contains no credential. The isolated runner blocks external socket access and
does not load the database integration fixtures.
