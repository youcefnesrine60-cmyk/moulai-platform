# Agent API security and persisted state

The agent, channel, conversation, and message routers require a verified
Keycloak owner identity. An owner ID, administrator ID, or Telegram chat ID
supplied by a client does not authenticate a request. The service constructors
also require the verified owner ID and bind the SQLAlchemy session to that owner.

## Owner isolation

The request session applies owner predicates to reads, counts, searches,
statistics, relationship loads, and bulk updates or deletes. Ownership follows
the restaurant's owner through the agent, channel, conversation, and message
relationships. Foreign records are hidden. A mixed bulk agent status update
changes only owned agents and reports their actual count.

Pending ORM writes validate their parents before SQL is emitted. A conversation
must reference a channel belonging to the exact selected agent, even when both
agents belong to the same owner. Arbitrary SQL and bulk parent changes are
unavailable through the owner-scoped session.

## State storage without schema changes

The existing database schema has no dedicated conversation `status` or message
`content_type` column. Their public API fields now persist through SQLAlchemy
hybrid properties backed by existing JSON columns:

| Public field | Existing storage | Reserved key | Historical default |
| --- | --- | --- | --- |
| Conversation `status` | `context` | `_moulai_status` | `active` when active; otherwise `closed` |
| Message `content_type` | `meta_data` | `_moulai_content_type` | `text` |

Conversation states are `active`, `closed`, and `suspended`. Changing the state
also updates `is_active`; only `active` permits new messages. Explicit activation
or deactivation sets the state to `active` or `closed`, respectively. Context
replacement and context merging preserve the state. Clients must use the status
field or status endpoint to change it; writing the reserved JSON key cannot
override it.

Message content types are `text`, `image`, `audio`, `video`, and `file`.
Construction applies the explicit content type after metadata, so input ordering
cannot discard it. Subsequent metadata replacement preserves the type, including
when a caller supplies the reserved key. Historical rows without the key remain
readable and searchable as text messages.

The reserved keys are visible in their JSON objects. They are managed by the
model and should not be used for application context or custom metadata.
Assignments copy JSON dictionaries so SQLAlchemy detects persisted changes.
SQL expressions use typed JSON extraction and `CASE` for filtering and grouped
statistics on PostgreSQL and SQLite. No migration or production write is required
for this mapping; existing rows are interpreted when read.

## Verification scope

Offline HTTP contracts cover authentication on every operation and preserve
intentional HTTP authorization errors. A separate fixture executes the real
routers, services, repositories, and session authorization hooks against a
private SQLite database held in memory. It checks two owners, foreign parent
IDs, global searches, counts, mutations, mixed bulk updates, authorized writes,
and state round trips across independent sessions.

The SQLite fixture uses an async session adapter around its real synchronous
ORM session. It does not substitute SQL predicates or stored rows. It verifies
authorization and persistence behavior, without claiming PostgreSQL concurrency
or locking coverage. Keycloak token verification is tested separately by the
central authentication tests.
