# K9.2-A — Detailed tenant architecture design

Design date: 2026-10-18. Status: **submitted for validation; not implemented**.

Architecture B is approved: Keycloak authenticates; PostgreSQL is the sole
authority for companies, memberships, tenant permissions and business resources.
This document specifies the proposed implementation contracts following the
[K9.1 audit](keycloak-k9-architecture-audit.md). Approval of B does not imply
approval of every policy or migration proposed below.

Only this document is added. No application code, Alembic revision or
configuration is changed, and no database connection, test suite, Keycloak,
Render, Telegram or GitHub operation is performed. Local `.env` entries for
`OIDC_DIAGNOSTICS_ENABLED` and `OIDC_ALLOW_LOCAL_HTTP` were checked selectively:
both are `false`, with no enabling override in the tool process. They remain
unchanged; no application was started to inspect its runtime environment.

## 1. Proposed decisions and conceptual schema

| ID | Proposed decision | Alternative and consequence |
| --- | --- | --- |
| D1 | Company is the tenant boundary; several restaurants can belong to one company, and one person can join several companies. | Owner-as-tenant cannot separate companies A and B owned by the same person. Restaurant-as-tenant duplicates company governance. |
| D2 | Use local integer primary keys consistent with the existing base models; keys are immutable and never intentionally reused. | UUIDs are possible but add a new identifier convention without providing authorization. Neither choice uses Keycloak Organization IDs. |
| D3 | Exactly one tenant role per membership; three initial roles and explicit database permission rows. | Custom roles, overrides and role inheritance add policy complexity and are deferred. |
| D4 | Owners use company-wide scope; managers and employees can use either supported mode. New employees default to explicit grants with an empty set. | Owner restaurant subsets complicate company governance; owner governance is intentionally company-wide. |
| D5 | Canonical grouping is the existing group/restaurant association table, with corrected semantics and constraints. | Keeping only `Restaurant.group_id` would discard the multiple-group capability already represented by link APIs. Section 5 evaluates the consequences before recommending D5. |
| D6 | Membership changes are owner-controlled initially; managers administer operations, without membership delegation. | Manager-to-employee delegation can be added later with a separate bounded delegation policy. It is not implied by the title manager. |
| D7 | Identity registration and profile linking require explicit approved workflows; no login-time provisioning. | Matching email, Telegram ID or realm role would create unauthorized business associations. |
| D8 | Company enforcement has an explicit, irreversible cutover marker; legacy owner access cannot bypass it. | Running owner-wide and membership authorization against the same converted resources creates a second access path. |

```text
Keycloak verified (issuer, subject)
                 |
                 v
              Identity
                 |
                 +-- explicit optional link <-- Owner / Admin profiles
                 |
                 +-- OrganizationMembership -- Organization
                           |        |                 |
                           |        +-- TenantRole    +-- RestaurantGroup
                           |              |           |         |
                           |         explicit         |   GroupRestaurant link
                           |         permissions      |         |
                           +-- RestaurantGrant -------+-- Restaurant
                                                               |
                                                   physical Branch / catalog
                                                   agents / orders / billing
```

`User` remains the existing customer registry. `Owner` remains an existing owner,
registration and financial profile. `Admin` and its current RBAC remain platform
administration. None is automatically converted into Organization or employee.

## 2. Model and integrity contracts

Names below are proposed contracts, not new Python modules or migration files.
Use the existing [declarative Base](../app/models/base.py), SQLAlchemy 2.x typed
mapping and asyncpg. Preserve existing IDs, relationships and billing references.
New authorization lifecycle timestamps use non-null timezone-aware UTC creation
and update timestamps; override the new models' inherited timestamp declarations
where necessary instead of changing the shared base or historical timestamps.

### 2.1 Identity

Proposed table: `identities`; local identity for one issuer-qualified subject.

| Field | SQLAlchemy / PostgreSQL contract |
| --- | --- |
| `id` | Integer primary key using existing local ID conventions. |
| `issuer` | `String(1024, collation="C")`, non-null; exact trusted issuer, bounded ASCII URL. |
| `subject` | `String(255, collation="C")`, non-null; exact opaque subject, bounded ASCII string. |
| `status` | Non-null checked string: `active`, `suspended`, `retired`. |
| `revision` | Non-null positive BigInteger, initially 1; increment on lifecycle changes. |
| `created_at`, `updated_at` | Non-null `DateTime(timezone=True)`, server creation default. |

Constraints: `uq_identities_issuer_subject`; nonempty issuer/subject, no leading
or trailing whitespace or control characters; ASCII and length bounds; checked
status and positive revision. The trusted-issuer URL validator additionally
requires the existing business HTTPS policy. Reject oversized input rather
than truncate. Do not lowercase, trim, rewrite trailing slashes or otherwise
normalize a verified issuer/subject to match another identity.

Issuer and subject are immutable after creation. A changed issuer needs a new
identity and an independently reviewed association; it is not a profile edit or
an automatic merge. A retired identity is a retained tombstone, not an identifier
available for reassignment. OIDC subjects are issuer-local identifiers.
[Source: OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html#SubjectIDTypes).

No JWT, password, authorization code or signing key is stored here. Display
names and email are not authorization keys and need not be duplicated.

### 2.2 Organization

Proposed table: `organizations`; company/business access boundary.

| Field | Contract |
| --- | --- |
| `id` | Stable local Integer primary key. |
| `name` | Non-null `String(255)`, trimmed and nonempty; not globally unique. |
| `status` | Non-null checked string: `draft`, `active`, `suspended`, `archived`. |
| `revision` | Positive BigInteger, initially 1; lifecycle/authorization changes increment it. |
| `tenant_enforced_at` | Nullable timezone-aware timestamp during staging; once set, immutable. Active companies require it. |
| `created_at`, `updated_at` | Non-null timezone-aware UTC timestamps. |

No Keycloak Organization foreign key, country-based identity, billing owner or
single-person owner column is required. Company owners are active memberships.
The cutover marker is a transition safeguard, not an additional permission
authority: PostgreSQL membership remains authoritative after enforcement.

Organization deletion is unavailable through ordinary services. Resource company
assignment is write-once after reviewed backfill. Changing a display name or
commercial brand does not change the tenant ID or move historical data.

### 2.3 OrganizationMembership

Proposed table: `organization_memberships`.

| Field | Contract |
| --- | --- |
| `id` | Stable local Integer primary key. |
| `organization_id` | Non-null FK to Organization, `ON DELETE RESTRICT`. |
| `identity_id` | Non-null FK to Identity, `ON DELETE RESTRICT`. |
| `role_code` | Non-null FK to `tenant_roles.code`; checked initial roles `owner`, `manager`, `employee`. |
| `access_mode` | Non-null checked string: `company-wide` or `explicit-grants`. |
| `status` | Non-null checked string: `pending`, `active`, `suspended`, `revoked`. |
| `revision`, `enrollment_generation` | Positive BigIntegers, initially 1; optimistic concurrency and explicit re-enrollment history. |
| `accepted_at`, `activated_at`, `suspended_at`, `revoked_at` | Nullable timezone-aware timestamps with state checks described below; latest transition evidence, not the complete history. |
| `created_at`, `updated_at` | Non-null timezone-aware UTC timestamps. |

Constraints: unique `(organization_id, identity_id)`; unique
`(organization_id, id, access_mode)` for grant integrity; owner implies
`access_mode = 'company-wide'`; active requires acceptance and activation
timestamps; suspended/revoked requires its corresponding transition timestamp.
Pending re-enrollment clears current acceptance/activation timestamps but retains
historical transition evidence in append-only audit events.

One row represents the stable identity/company association. A revoked row cannot
be directly resumed: a fresh approved enrollment moves it to pending, increments
generation/revision and needs new acceptance. No duplicate active membership or
grant resurrection is allowed. Its company and identity are immutable.

Indexes: `(identity_id, status, organization_id)` for company selection;
`(organization_id, status, role_code)` for governance; the declared unique keys
for association lookup and composite FKs. Foreign-key referencing columns must
have appropriate supporting indexes.

### 2.4 Tenant role and permission policy

Use a separate `tenant_roles` table with stable role `code` primary key and a
positive `policy_revision`. It contains exactly the three initial role codes.
Use `tenant_role_permissions(role_code, permission_code)` with a composite primary
key, FK to tenant roles and a CHECK allowlist containing exactly the codes in
section 3. This is a small tenant policy table, not a new global IAM system.

The permission descriptions in this document form the initial catalogue; a
second permission-definition table is unnecessary initially. PostgreSQL stores
the effective role/permission rows. Application types validate the same allowed
codes but do not override the database with a hard-coded role fallback.

Tenant permission codes have a `tenant.` namespace because their semantics
require company/resource scope. Do not copy or reference platform Role IDs,
`role_permissions`, wildcard `*` or Keycloak realm role assignments. Existing
global RBAC tables and grants are unchanged. No tenant-facing API edits role
templates; later policy changes require reviewed versioned provisioning and
invalidation through `policy_revision`.

### 2.5 Restaurant grants and resource company constraints

Proposed `membership_restaurant_grants` has an Integer primary key,
`organization_id`, `membership_id`, `restaurant_id`, fixed
`access_mode = 'explicit-grants'`, creation timestamp and unique
`(membership_id, restaurant_id)`.

Require both composite foreign keys:

- `(organization_id, membership_id, access_mode)` references the membership's
  unique `(organization_id, id, access_mode)`.
- `(organization_id, restaurant_id)` references Restaurant's unique
  `(organization_id, id)`.

This deliberately duplicates the company ID and a fixed mode in the grant row
to enforce consistency. A grant for another company, a company-wide membership
with grant rows or a duplicate grant is rejected by the database. Changing from
explicit to company-wide deletes the old grants inside the same locked
transaction before updating the mode; switching back starts empty unless a new
explicit set is approved. Revocation clears current grants and audits their old
set. Foreign keys use RESTRICT; no identity/company deletion cascade removes
historical business data.

Restaurant and RestaurantGroup gain nullable `organization_id` during expand,
non-null after validated backfill, each with FK RESTRICT and unique
`(organization_id, id)`. Their organization assignment becomes immutable once
populated. Physical Branch and most children derive company from Restaurant;
add no blanket tenant column to every child table. Existing branch/order and
product/category consistency checks remain required.

Simple cross-row CHECK constraints cannot establish company membership or the
last active owner. Composite FKs establish the declared parent equalities;
cross-row lifecycle rules require the transaction/trigger contracts in section 6.
[Source: PostgreSQL constraints](https://www.postgresql.org/docs/18/ddl-constraints.html).

Existing profile links may later gain nullable unique `identity_id` FKs with
RESTRICT. An identity may link to one Owner and separately one Admin, only with
independent approvals. This is a staged profile reference, not a membership or
automatic permission grant. Initial K9 foundation work must not relink any
existing administrator or owner.

## 3. Initial tenant permission catalogue and delegation

Every table cell is an explicit initial assignment; there is no role hierarchy
or wildcard expansion. Permission possession is necessary but never sufficient:
active context, resource scope and existing business rules also apply.

| Permission | Owner | Manager | Employee | Meaning / additional restriction |
| --- | --- | --- | --- | --- |
| `tenant.organization.read` | Yes | Yes | No | Company profile; contains no financial evidence or identity directory. |
| `tenant.organization.update` | Yes | No | No | Company display metadata only; not status, identity links or resource ownership. |
| `tenant.organization.suspend` | Yes | No | No | Explicit company-wide suspension; resume uses the separate recovery workflow. |
| `tenant.membership.self.read` | Yes | Yes | Yes | Own membership/selected-company metadata only, even when restaurant grants are empty. |
| `tenant.membership.self.leave` | Yes | Yes | Yes | Confirmed self-revocation only; an owner cannot leave an active company without another qualifying active owner. |
| `tenant.restaurants.read` | Yes | Yes | Yes | Authorized restaurant information. |
| `tenant.restaurants.update` | Yes | Yes | No | Allowed operational metadata; never company/legacy owner reassignment, payer or financial credentials. |
| `tenant.branches.read` | Yes | Yes | Yes | Physical branches under authorized restaurants. |
| `tenant.branches.manage` | Yes | Yes | No | Authorized outlet operations; no cross-restaurant move or destructive history deletion. |
| `tenant.catalog.read` | Yes | Yes | Yes | Authorized menu/products/options. |
| `tenant.catalog.manage` | Yes | Yes | No | Catalog mutations with parent consistency and existing domain rules. |
| `tenant.orders.read` | Yes | Yes | Yes | Authorized restaurant orders and necessary fulfillment data. |
| `tenant.orders.fulfill` | Yes | Yes | Yes | Only currently valid preparation/ready/fulfillment status transitions. Never mark paid, refund, alter prices or bypass order locks. |
| `tenant.orders.manage` | Yes | Yes | No | Authorized create/edit/cancel operations subject to current pricing, status and transaction rules. No arbitrary totals or payment approval. |
| `tenant.agents.read` | Yes | Yes | No | Authorized agent/channel metadata with credentials redacted. |
| `tenant.agents.manage` | Yes | Yes | No | Authorized agent/channel operations; no unreviewed provider credential disclosure or unrelated webhook administration. |
| `tenant.conversations.read` | Yes | Yes | No | Authorized conversations/messages; do not grant customer-wide registry access. |
| `tenant.conversations.respond` | Yes | Yes | No | Response operations within authorized conversation/channel relationships. |
| `tenant.reports.read` | Yes | Yes | No | Scoped aggregates and exports; no unfiltered group or portfolio totals. |
| `tenant.groups.read` | Yes | Yes | No | Company groups intersected with the actor's authorized restaurants. |
| `tenant.groups.manage` | Yes | No | No | Company-wide grouping changes; groups never grant restaurant access. |
| `tenant.memberships.read` | Yes | No | No | Company membership administration data only, without external identity secrets. |
| `tenant.memberships.manage` | Yes | No | No | Invite, suspend, revoke or change manager/employee assignments in this company. Does not promote/demote owners or link legacy profiles. |
| `tenant.ownership.manage` | Yes | No | No | Initiate the accepted ownership-change workflow, not an arbitrary role PATCH. |
| `tenant.billing.read` | Yes | No | No | Scoped invoice/subscription/receipt access plus legacy payer eligibility below. |
| `tenant.billing.checkout` | Yes | No | No | Server-priced manual checkout with existing payer and restaurant consistency. |
| `tenant.receipts.submit` | Yes | No | No | Submit evidence for an eligible owned invoice; submission never activates a subscription. |

Employee fulfillment is a proposal for review, not permission to expose the
current unrestricted status-update service. An implementation must map it to an
explicit approved transition allowlist; until that mapping is reviewed, the
employee mutation endpoint stays unavailable. No restaurant creation/deletion,
company creation, refunds, payment approval, automatic renewals or sensitive
financial configuration is added to this initial catalogue.

Delegation rules:

1. Only an active company owner can create pending manager/employee memberships
   and replace their restaurant grants. The invitee must accept the exact
   proposed role and scope under their verified identity before activation.
2. Owners can grant company-wide manager/employee access only by explicit
   action. Empty/default grants never imply company-wide access.
3. Managers and employees cannot change any membership, role template, grants,
   identity association, owner assignment or platform permission, including their
   own. Managers' operational mutations remain restaurant-scoped.
4. Owner promotion, demotion and replacement use section 6's workflow. Ordinary
   membership administration cannot edit another owner or bypass last-owner
   protection. A non-last owner's voluntary departure is a separate audited
   self-revocation operation requiring explicit confirmation.
5. New permissions grant nothing until explicit rows are reviewed and provisioned
   for each intended role. Unknown permissions and unsupported operations deny.

Billing remains intentionally narrower than company ownership. During initial
conversion, an owner needs a separately approved local Owner profile link and
must match the invoice/subscription's legacy owner and restaurant. A new co-owner
without that payer association cannot use billing permissions to claim the old
owner's invoices. Preserve payment/subscription/restaurant owner checks and
receipt privacy. Payer changes and multi-payer/company billing need a separate
design. Platform `payments.review` remains exclusively platform authorization.

## 4. Restaurant scope and immutable TenantContext

### 4.1 Two explicit access modes

For selected company C and active membership M, define eligible restaurants:

```text
company-wide:
  R.organization_id = C.id

explicit-grants:
  R.organization_id = C.id
  AND an exact (C.id, M.id, R.id) grant exists

explicit-grants with no grant rows:
  FALSE
```

Company-wide scope deliberately includes future restaurants assigned to C.
Explicit grants do not expand when a restaurant is created or added to a group.
Restaurant operational `is_active` is a separate domain policy: being in scope
does not permit ordering from an inactive restaurant. Grant scope does not
bypass subscriptions, entitlements, order locks or payment rules.

Empty explicit grants mean **no restaurant/business resource access**, including
counts, group members, orders, invoices and exports. Minimal own-membership
metadata is a control-plane exception, not access to company business records.
Company metadata changes, grouping and governance require company-wide owner
authority; an empty grant set cannot be treated as a global organization filter.

### 4.2 TenantContext contract

Implement later as a frozen, slotted value object; no mutable containers or ORM
entities. Proposed fields:

| Field | Type / invariant |
| --- | --- |
| `identity_id`, `organization_id`, `membership_id` | Positive local `int`; reject booleans masquerading as integers. |
| `role_code` | Unified `TenantRoleCode` literal alias for the three exact roles. |
| `access_mode` | Unified `RestaurantAccessMode` literal alias for the two exact modes. |
| `permissions` | `frozenset[TenantPermissionCode]` from current database policy rows. |
| `restaurant_ids` | `frozenset[int]`; exact explicit set or empty for company-wide. The mode, never collection truthiness, selects the predicate. |
| `identity_revision`, `organization_revision`, `membership_revision`, `role_policy_revision` | Positive version snapshots for stale-context detection. |

No JWT, password, subject, authorization code, Telegram ID, arbitrary caller
owner ID, database session or platform bypass flag belongs in the context.
Factory construction is internal to verified resolution; public HTTP callers
cannot submit or deserialize a trusted context.

Resolution order for future tenant routes:

1. Reuse the existing RS256/JWKS verifier, trusted issuer/audience and business
   HTTPS requirements. Do not enable either diagnostic flag.
2. Resolve exact `(iss, sub)` to an active local Identity; absent or disabled
   association is denied, without login-time creation or account linking.
3. Require an explicit company path parameter. A proposed route family is
   `/api/v1/organizations/{organization_id}/...`; no route is created here.
   Do not default to the first membership or union several companies.
4. Require company `active`, non-null enforcement marker and the selected
   identity's active membership with accepted enrollment. An unknown company or
   absent membership returns the same 404; authenticated insufficient permission
   or suspended access within a known membership returns 403.
5. Load the current tenant role policy and explicit grants; construct the frozen
   context and evaluate the requested action plus scope.
6. Bind a clean request session to exactly that context. Reuse only within its
   authorized transaction; a new transaction rechecks current states/revisions.

Malformed/expired JWTs remain 401; missing/invalid trusted provider configuration
remains fail-closed 503 according to the existing authentication contract.
Unauthorized resource IDs return generic 404. Version conflicts during an
otherwise authorized governance mutation return 409 without foreign details.

### 4.3 Freshness and cutover boundaries

A frozen context is an authorization snapshot, not a permanent capability.
No cross-request positive permission cache is introduced initially. Database
checks and locks in section 7 prevent a previously resolved context from writing
after a completed revocation. Reads are authorized against current state at
transaction resolution; already delivered responses cannot be recalled.
Long-running jobs/exports reauthorize each bounded unit and never hold a
database transaction open across an external provider call.

Before a company's `tenant_enforced_at` is set, all affected entry points must
have reviewed tenant guards or explicit denial behavior. After cutover, legacy
owner-only APIs, lists, counts, bots, background jobs and lower-level services
must not perform workforce business operations without a valid tenant context.
Filter converted resources from legacy list/count paths; reject legacy direct
access. Platform administration uses its separately authorized context.

Existing customer ordering is a separate purpose, not employee access. Preserve
its reviewed customer/channel/restaurant binding, consent and own-order checks;
it may expose published menus and the customer's own permitted order actions,
never workforce configuration, other customers' records or owner-wide data.
Customer authentication does not fabricate a membership or TenantContext.
Likewise, a system job needs an explicit company-bound, allowlisted operational
purpose; a job acting for a member revalidates that membership. Neither a
webhook secret nor an unrestricted internal session substitutes for these
bounded contracts. Each alternate entry point must be classified and tested
before cutover, rather than disabling genuine customer ordering or granting it
staff authority.

The legacy exclusion depends on the immutable enforcement marker, **not** on
current company or membership status. Suspending/revoking access must not reopen
an owner-wide path. Do not bind both the legacy owner guard and a new tenant
guard to the same session. Staging migrations alone do not establish company
isolation; business cutover requires a complete reviewed entry-point inventory.

### 4.4 Security invariants

| ID | Invariant |
| --- | --- |
| I1 | A verified JWT identifies an exact issuer/subject pair; it never creates a company, profile link or business grant. |
| I2 | One TenantContext selects one company and one active accepted membership. Memberships are never unioned. |
| I3 | Workforce access requires active Identity, active enforced company, active membership, explicit permission and matching resource scope together. |
| I4 | Explicit grants with an empty set authorize no restaurant, child data, aggregate or mutation. |
| I5 | Every parent/link/grant used for authorization belongs to the selected company; group membership is not employee membership. |
| I6 | Realm roles, platform roles, Telegram identifiers and legacy payer ownership never substitute for tenant authorization. |
| I7 | Identity keys, membership endpoints, resource company assignments and the enforcement marker are immutable under ordinary updates. |
| I8 | An active company cannot commit without a qualifying active owner; acceptance/revocation races cannot evade this rule. |
| I9 | Authority reductions take effect through transaction revalidation; an old frozen context alone authorizes no later database operation. |
| I10 | No legacy owner-wide fallback exists for enforced companies, including suspended companies or revoked members. |
| I11 | Receipt submission never approves payment; company governance changes never rewrite payer history or grant platform RBAC. |
| I12 | Governance effects, proposal consumption and required audit evidence commit atomically; offboarding preserves historical business data. |

## 5. Canonical restaurant grouping: consequences and recommendation

### 5.1 Source findings and alternatives

The [Restaurant model](../app/models/restaurant.py) has nullable `group_id`.
The [group/link models](../app/models/restaurant_group.py) also define a separate
`restaurant_branches` association. The
[group repository](../app/repositories/restaurant/restaurant_group_repo.py)
loads both `restaurants` and `branch_links`; the
[link repository](../app/repositories/restaurant/restaurant_branch_repo.py)
provides lists/counts by group and by restaurant. Existing
[group link services](../app/services/business/restaurant/groups/service.py)
write the latter without synchronizing the former. These are static facts, not
evidence of the number of live links or actual customer grouping requirements.

| Canonical choice | Benefits | Consequences before selection |
| --- | --- | --- |
| Only `Restaurant.group_id` | Simple optional one-group relationship and joins. | Multiple links for one restaurant must be rejected or reduced through explicit business decisions. Link IDs and group-link API semantics need retirement. Possible loss of current represented capability. |
| Only group/restaurant association | Preserves represented many-to-many behavior and link IDs; matches existing link operations. | Direct-FK callers and eager loads must change; joins require deduplication for counts and aggregates. Singular group payloads cannot continue as an independent writer. |
| Keep both | Lowest immediate change. | Leaves contradictory sources of truth and requires permanent synchronization. Rejected as a target. |

**Proposed D5: retain the existing association table as the sole canonical
representation.** Its conceptual ORM name becomes `RestaurantGroupRestaurant`;
retain physical table `restaurant_branches` and existing IDs initially to avoid
an unnecessary table-copy/rename migration. Rename consumers consistently during
implementation, without creating a compatibility re-export. Physical
`Branch` / `branches` remains unchanged.

This recommendation preserves the richer represented relationship. It is not
an assertion that all restaurants need multiple groups. A confirmed exclusive
one-group business rule could justify the first alternative before implementation.

### 5.2 Target grouping constraints and behavior

Each group belongs to exactly one company. Each canonical link includes
`organization_id`, `group_id`, `restaurant_id`, retained Integer ID and timestamps.
Require unique `(group_id, restaurant_id)` and composite FKs from
`(organization_id, group_id)` and `(organization_id, restaurant_id)` to their
respective company-qualified parents, both RESTRICT. Keep indexes for reverse
restaurant lookup as well as group lookup. Groups never span companies.

The direct `Restaurant.group_id` column is removed only in contract. There is
one association writer after cutover. Group listing, statistics and batch
operations all use that same relationship. Use distinct restaurant sets so a
restaurant in two groups is not counted or mutated twice in company totals.

Group membership never implies workforce access. A scoped manager sees only
the intersection of group restaurants and their grants, including matching
scoped counts; hide groups with no accessible restaurants from that manager.
Owners can see/manage empty groups. Any future group-wide operational batch
must authorize every target and reject unauthorized mixed batches atomically;
do not silently widen grants or issue a global update by group ID.

Historical cross-owner links are not automatically valid or invalid company
assignments: they need actual business verification. A company may eventually
contain restaurants with different legacy financial owners, but that cannot be
inferred from a group name or existing link. Financial owner checks remain.

### 5.3 Reconciliation before removing the direct FK

| Observed development data case | Required decision |
| --- | --- |
| Direct FK and link agree | Preserve the existing link ID; record correspondence. |
| Direct FK only | Add a canonical link only after the approved company/group mapping confirms it. |
| Link only | Preserve only after that same review; do not invent a direct FK. |
| Both represent different sets | Produce an explicit conflict record and block affected cutover. Do not automatically union, overwrite or choose the latest timestamp. |
| Duplicate pair | Review references to each link ID, select a retained ID and audit reconciliation; do not delete blindly. |
| Group/restaurant belongs to different companies or mapping is unknown | Quarantine the association from cutover pending business disposition. |

Consequences requiring review include request/response schemas, restaurant
create/update payloads, group detail eager loading, link APIs, caches, counters,
statistics and existing tests. A singular `group_id` cannot round-trip an
arbitrary many-group set. Propose explicit group-link commands and a plural
group list in a reviewed API contract, rather than preserving two writers or
silently selecting a primary group. Do not change those APIs in K9.2-A.

## 6. Lifecycle, ownership and historical retention

### 6.1 Company and identity states

| Transition | Authorization and conditions |
| --- | --- |
| Create company as draft | Explicit approved provisioning by a separately authorized platform operator; no default tenant from login or Owner. No business access. |
| Draft to active | Approved initial owner accepts; at least one active owner with active Identity; enforcement prerequisites complete. Activate first owner and company atomically with cutover marker. |
| Active to suspended | Confirmed active owner using `tenant.organization.suspend`, or separately authorized platform security operation. Block business access; preserve all rows and financial history. |
| Suspended to active | Dedicated platform recovery procedure, explicit owner confirmation and valid active owner/membership/policy checks. Ordinary suspended-company TenantContext is not accepted as an authorization bypass. |
| Active/suspended to archived | Separately approved platform lifecycle operation after retention/operational review. No routine tenant hard deletion or automatic unarchive. |
| Identity active to suspended | Explicit identity-security authority, not a tenant manager. Denies all its companies; must preserve the last-owner invariant or explicitly suspend affected companies in the same approved emergency transaction. |
| Identity suspended to active | Separately approved recovery; does not resume suspended/revoked memberships, companies or old grants. |
| Identity to retired | Explicit permanent offboarding policy; retain subject key, links and history. Last-owner protection applies. |

Initial tenant functionality does not add platform provisioning/recovery rights
to any existing role. Names such as `identities.link` or a company-recovery
permission are future platform permissions needing separate review and explicit
granting, never tenant permissions or automatic migration grants.

### 6.2 Membership states

| Transition | Rule |
| --- | --- |
| Absent to pending | Approved identity exists; owner proposes role/scope. Identity existence or realm `owner` alone is insufficient. |
| Pending to active | Invitee accepts the exact current proposal; authorized owner approval remains valid; company activation policy passes. |
| Active to suspended | Owner-authorized non-owner change; owner suspension requires the ownership/lifecycle workflow and last-owner protection. Grants remain dormant and auditable. |
| Suspended to active | Explicit owner approval and target acknowledgment of the current role/scope; no resurrection of revoked enrollment. |
| Pending/active/suspended to revoked | Authorized non-owner revocation, accepted owner workflow or explicit self-departure; clear current grants, increment revision and audit atomically. |
| Revoked to pending | New approved enrollment generation, empty explicit grants by default and fresh acceptance. Never automatic direct activation. |

Changes increasing role authority, adding grants or switching to company-wide
scope are proposals requiring target acceptance before their effective mutation.
Reductions/revocation take effect through an authorized transaction without
requiring the target's consent. Pending changes leave existing active scope
unchanged and cannot be accepted after their expected revisions change.

Use a small `membership_change_proposals` record for accepted governance
changes: local ID, company, actor kind/local ID, optional actor membership and
required target membership ID, immutable proposed role/mode/exact grant set,
expected revisions, enrollment generation, expiry and
`pending/applied/cancelled/expired` state. Initial enrollment, scope elevation and
ownership transfer share this mechanism instead of parallel invitation/transfer
engines. No bearer invitation token is necessary when the already registered
target accepts under their verified Identity. Composite company-qualified FKs
and grant-parent validation apply to proposal targets too. Audit application of
each proposal; mark it consumed in the same transaction as its effects.

Store the proposal's restaurant set in normalized proposal/restaurant rows with
unique `(proposal_id, restaurant_id)` and company-qualified parent FKs, rather
than trusting arbitrary JSON resource IDs. Actor kind requires exactly one
applicable local actor reference: tenant membership/Identity or a separately
authorized platform administrator. Bootstrap proposals for the first owner use
the platform provisioning authority and can be accepted only as part of the
reviewed draft-company activation workflow. No existing owner membership is
invented to authorize bootstrap. Role/scope edits on active memberships keep
the same membership row; enrollment generations change only on re-enrollment.

### 6.3 Last active owner and transfer contract

An **active** company must have at least one membership satisfying all of:
`role_code = owner`, membership active and accepted, Identity active, and
company-wide access. Neither a suspended owner nor a pending invitation counts.
Draft/suspended companies may await an approved owner recovery, but cannot
serve business resources. Archived companies retain historical memberships.

Prevent loss of the last qualifying owner through role/membership changes,
identity suspension/retirement, deletion or activation races. A service-only
count before UPDATE is insufficient. Proposed enforcement is a deferred
constraint trigger checking affected organizations at transaction end, together
with locked governance operations. Observe membership, identity and organization
lifecycle changes, not only membership deletes. The trigger must lock the company
before a fresh qualifying-owner query and raise a named integrity error when an
active company would be ownerless. At PostgreSQL READ COMMITTED, perform lock
and validation as separate commands, with serialization/retry tests; do not
rely on an earlier snapshot after waiting for a lock. Trigger design needs
PostgreSQL integration validation before adoption. PostgreSQL supports deferred
constraint triggers; an ordinary row CHECK is not a cross-table owner count.
[Source: PostgreSQL CREATE TRIGGER](https://www.postgresql.org/docs/18/sql-createtrigger.html).

Ownership transfer uses an immutable change proposal initiated by an active
owner. The target must already have an active Identity and an accepted local
membership, and must accept company-wide ownership under that exact identity.
Recheck initiating owner authority, both membership revisions and proposal
expiry on acceptance. In one transaction, promote the target and, for a
replacement transfer, apply the initiator's explicitly approved departure or
reduced scope; commit only if the active-owner invariant holds. Addition of a
co-owner uses the same acceptance mechanism. Replay is idempotent for the same
applied proposal; altered or stale intent conflicts.

This transfers company governance only. It does not change legacy
`Restaurant.owner_id`, Payment/Subscription owners, payer eligibility, invoices,
bank instructions or legal ownership evidence. Moving a restaurant between
companies is unavailable in the initial design. A business sale/resource
transfer requires its own historical-data and financial migration design.

### 6.4 Audit and retention

Use append-only tenant audit events for company/membership state changes,
proposals, grants, ownership transfers and approved identity links. Include
company, actor kind and local ID, target IDs, action, sanitized before/after
policy values, generation/revisions, UTC time, reason and correlation ID.
Tenant actors and platform actors must be distinguishable. Account linking
evidence uses an approved reference, not raw JWTs, passwords, codes or
unnecessary subject/account details in logs.

Restrict ordinary database role updates/deletes on these audit records and avoid
ORM delete-orphan cascades from identity/membership. Revocation, archiving and
identity retirement preserve orders, payment evidence, subscriptions, grant
history and audit events. Hard deletion/anonymization requires a separate
retention policy; none is executed or prescribed as an automatic cascade here.

## 7. SQLAlchemy, service and transaction architecture

### 7.1 Responsibility boundaries

| Layer / proposed component | Contract |
| --- | --- |
| Existing JWT verifier and `OIDCPrincipal` | Identity verification only; reuse issuer/audience/JWKS policy. No tenant authorization from realm roles. |
| `IdentityRepository` | Keyword-only exact issuer/subject BASE SELECT and explicit approved persistence. No fuzzy identity lookup. |
| `TenantContextResolver` | Async keyword-only verified principal, selected company and session; returns frozen context or denies. Loads current membership/policy/grants. |
| `TenantAuthorizationService` | Revalidates context state/version and required permission in the operation transaction; supplies company/restaurant predicates. |
| Scoped business services | Keyword-only trusted context plus session and typed commands. Resource/parent checks are repeated here for non-HTTP callers. No caller-controlled optional owner filter. |
| Membership/governance service | Role/scope proposal, acceptance, revocation, locks, last-owner policy, idempotency and audit in one unit of work. |
| Scoped repositories | BASE SELECT always includes company and applicable restaurant predicates. Inserts derive immutable parents from validated data; updates cannot change company/identity keys. |
| Unit-of-work boundary | One explicit outer async transaction owns commit/rollback; repositories flush only within it. Business mutation, audit and proposal consumption commit together. |
| Existing platform services | Separate verified active administrator context and live platform RBAC; no tenant-to-platform context conversion. |

The existing [BaseRepository](../app/repositories/base.py) can commit writes by
default and detects a single primary-key component. New authorization workflows
must explicitly use the existing commit-deferral capability or specialized
flush-only repositories throughout the unit of work; no nested helper may commit
early. Composite-key policy associations need explicit composite predicates,
not generic `get_by_id`/delete based on the first key. Do not globally refactor
unrelated repositories merely to implement K9.

The request unit-of-work dependency begins the single owned transaction before
the first identity/membership database lookup, and shares its session through
resolution and the business operation. Do not call a second `begin()` over an
already autobegun transaction or commit from an authorization dependency. Check
affected row counts on revision-qualified updates; lost races are conflicts,
not successful no-op permission changes.

Use one AsyncSession per request/task, explicit async queries and eager loads
where required. Constructors/session binding perform no SQL. Do not share a
session among concurrent jobs or allow lazy IO to escape the async execution
boundary. These constraints align with SQLAlchemy's async guidance.
[Source: SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html).

### 7.2 Operation transactions and revocation ordering

Proposed initial contract uses READ COMMITTED and a uniform lock order:
tenant role rows in code order, involved Identity IDs in ascending order,
Organization IDs in ascending order, Membership IDs in ascending order, then
business resources in a documented order. Transactions must know their target
set before acquiring these locks; reject unbounded mixed-company operations.

Normal bounded business operations, including reads, take shared row locks on
the applicable role, identity, company and actor membership, then re-read
authorization state and versions before reading or changing resources.
Company governance/grant changes take an
exclusive company row lock and exclusive affected membership locks; identity
suspension takes an exclusive identity lock before affected company locks.
Policy provisioning takes an exclusive role lock and increments its revision.
All writers must follow the same protocol, including administrative and worker
paths. Shared locks permit concurrent ordinary business writes but serialize
them against authority reduction. PostgreSQL row-lock conflict rules support
this design; deadlocks remain possible and require bounded retry of the entire
idempotent transaction, not a partial continuation.
[Source: PostgreSQL explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html).

Thus a mutation either commits before revocation, or waits and fails current
authorization after revocation commits. A prebuilt context cannot authorize a
later mutation by itself. Lock timeout, stale revision or validation failure
rolls back business data and audit application together. Identity emergency
suspension covering several companies locks them in sorted order and applies
any separately approved company suspensions atomically. No database lock is
held while obtaining user acceptance or calling an external provider.

Any preliminary SELECT used to discover lock targets is not an authorization
decision. After acquiring locks in the prescribed order, reload state and
compare target IDs, role and revisions; if they changed, restart resolution or
deny instead of continuing with mismatched policy locks. Increment membership
revision for any effective role, scope, enrollment, status or grant-set change.

### 7.3 Resource scope inventory required for implementation

Extend the current [owner guard](../app/core/security/tenant_scope.py)'s proven
techniques under a new immutable company/membership binding; do not treat its
ten-model map as universal coverage. Protection must include:

- Restaurant, physical Branch, catalog parents/options and group associations.
- Agent, Channel, Conversation and Message with both company and parent checks.
- Orders/items/options/history and any customer relationship exposed through an
  authorized restaurant; never the customer's unrelated orders/records.
- Payments, subscriptions, private receipts and audit evidence with payer
  compatibility restrictions as well as restaurant/company scope.
- Metrics, counters, reports, exports, carts and other operational entities
  reached by a converted entry point; unmapped paths stay denied.

Queries, eager loading, counts and aliases must share scope semantics. Writes
validate the entire pending batch before flush. Reject raw SQL, unsafe Core/ORM
mixing and bulk paths that cannot prove equivalent protection. Bind only a
clean unit of work, evict preloaded scoped entities safely and forbid scope
rebinding. No claim of PostgreSQL RLS is made: RLS would be a separately reviewed
hardening layer with pool/reset semantics, not an assumed existing safeguard.

## 8. Explicit issuer-qualified identity association

Three approvals have distinct effects:

1. **Identity enrollment:** create/enable a local Identity only through a
   reviewed registration operation after verified authentication and operator
   approval. Accept only an already trusted issuer; no new issuer from a token.
   This alone grants no company or platform access.
2. **Business membership:** an authorized company owner approves a role/scope
   for that identity; the target accepts the current proposal. This does not
   modify Owner/Admin profiles or any other company.
3. **Legacy profile association:** link an existing Owner or Admin only through
   a separately approved operator workflow, verified target authentication,
   recorded evidence of authority over the existing local profile, and explicit
   target acknowledgment. Knowledge of IDs, Telegram chat or email is not proof.

For profile linking, the operator needs a specifically reviewed platform
identity-linking permission, distinct from tenant ownership. Lock the identity
and target profile, require expected current link/revision, verify uniqueness,
and apply association plus sanitized audit atomically. Reject conflicting links;
repeated identical approved requests are idempotent. Owner and administrator
associations require separate evidence and approvals. A co-owner cannot link
the existing payer's Owner profile merely by holding `tenant.ownership.manage`.

Existing nullable `auth_subject` values require issuer provenance review before
backfill. Do not assign them the current issuer automatically. Preserve legacy
values while readers transition, with one approved linking writer and enforced
agreement for any linked profile; then retire redundant subject columns only
after reviewed reader migration. Do not implement indefinite dual authority.

`owner-test` remains unassociated unless the user later approves a concrete,
verified binding to a specified record. No live binding, synthetic identity,
default administrator or automatic tenant creation occurs in this design stage.
Synthetic test fixtures must be clearly separate from real profile association.

## 9. Progressive Alembic proposal: expand, backfill, validate, contract

No revision IDs, migration scripts or DDL execution are created here. Proposed
stages must follow the actual [application](../alembic/versions/) and
[test](../alembic_test/versions/) histories; revision IDs are not sortable dates.

| Stage | Proposed operations after approval | Required exit evidence |
| --- | --- | --- |
| E1 — Expand foundation | Add identity/company/membership, tenant role-policy, grants, proposal and audit structures. Add nullable company/profile references, named CHECK/unique/FK constraints and indexes. Provision only approved role policy definitions, never real identities, links or memberships. | Reviewed SQL/autogenerate diff contains no unrelated model drift; constraints and flush-only workflows tested on isolated targets. Existing app still operates under its current guards. |
| E2 — Prepare cutover guards | Implement/test all future scoped paths and legacy exclusions before marking any company enforced. No access change merely from a schema column. | Complete entry-point inventory, no owner-wide fallback, platform/payment regressions pass. This is later application work, not part of this document. |
| B1 — Approved backfill | Produce a versioned mapping of restaurants/groups to actual companies; resolve grouping and issuer-provenance conflicts. Apply only reviewed rows in bounded transactions with audit/idempotency. | All rows accounted for, conflicts remain blocked, IDs and financial values unchanged. No automatic one-owner/one-company or subject mapping. |
| V1 — Validate constraints and data | Validate same-company FKs and unique links/grants; activate deferred owner checks; verify row counts, parent relations, payer invariants and historical/audit preservation. | No unresolved affected contradictions, orphan references or duplicate associations; migration/concurrency tests pass on PostgreSQL. |
| V2 — Enforce company access | Approved company-by-company activation with accepted initial owner and immutable enforcement marker. Converted resources require tenant context or explicit platform authority on every entry path. | Same-owner A/B and all legacy-path bypass tests pass; suspension never reopens legacy access. |
| C1 — Contract later | Make fully backfilled company references non-null; remove `Restaurant.group_id` and duplicate ORM/API writers only after canonical-link readers migrate. Retire redundant subject fields only after separate identity reader review. | No remaining consumer depends on retired fields; recovery/rollback is rehearsed. Legacy financial owner IDs are retained. |

CHECK/FK constraints eligible for staged validation may use `NOT VALID` followed
by validation in the reviewed PostgreSQL migration plan. Unique constraints and
indexes need their own duplicate checks and appropriate creation strategy; do
not apply `NOT VALID` indiscriminately. Inspect lock duration and table size
before choosing concurrent index creation/autocommit steps. No such commands
are run here.

Development rehearsals must pass the existing
[test database protection](../app/core/test_database.py): approved development
branch/project and endpoint attestation, actual `neondb_test`, asyncpg URL and
production endpoint exclusion. Missing or mismatching evidence denies writes;
production `DATABASE_URL` is never a fallback. Use only explicitly approved
isolated test targets and preserve existing data; no reset/drop/recreate is
authorized by this design.

Before enforcement, application rollback can leave unused additive structures.
After enforcement, rollback must preserve the enforcement barrier or temporarily
deny tenant business access; it must never restore the unguarded owner-wide
application against converted companies. A forward correction or isolated
restore/reconciliation may be needed. Dropping new tables or unsetting cutover
markers is not an acceptable automatic rollback. Production migration, restore,
identity linking and deployment retain their independent approval requirements.

## 10. Isolation tests and acceptance criteria

### 10.1 Test fixture model

Use mocked JWKS for the ordinary suite, with no local Keycloak dependency.
Fixtures include companies A and B sharing the same legacy Owner ID; company C
with another legacy owner; two restaurants and physical outlets in A, at least
one restaurant each in B/C, multiple groups including overlapping A groups,
and scoped agents/catalog/orders/billing evidence. Include active owners,
manager/employee company-wide and explicit memberships, an empty-grant employee,
multi-company identity, pending/suspended/revoked/retired identities or
memberships, unlinked identity, platform administrator with limited RBAC and
administrator with explicit payment review authority.

### 10.2 Required matrix

| ID | Cases | Acceptance assertion |
| --- | --- | --- |
| T01 | JWT signature, issuer, audience, expiry, missing claims, realm-role changes | Existing authentication failures remain; role `owner`/`admin` creates no local link or grant. Diagnostics stay disabled. |
| T02 | Same subject/different issuer; case/slash variants; changed email/username | Exact pair matches only; no normalization, inference, collision or automatic merge. |
| T03 | Valid JWT with no Identity, no membership or wrong company selection | Denial without database provisioning or information about foreign companies. |
| T04 | One identity with A and B memberships; A selected; same legacy owner | A selection never exposes B/C resources; no union and no default company. |
| T05 | Company-wide versus explicit grants, including empty set | Company-wide includes only C's restaurants; explicit includes exact grants. Empty explicit grants return no restaurant resources/counts and deny mutations. |
| T06 | Newly created restaurant/group link | Company-wide scope follows company assignment; explicit scope does not expand. Group membership grants no workforce authority. |
| T07 | Each permission row and denied action for every role | Catalogue matches persisted rows exactly; unknown permission, platform wildcard and missing policy row deny. |
| T08 | Manager/employee role/grant edits and arbitrary owner promotion | No membership delegation or self-escalation; target acceptance cannot authorize an invalid initiator. |
| T09 | Pending changes, replay, expiry, changed revisions/generation | Only the target identity accepts exact intent; one atomic application; stale/replayed-altered requests fail safely. |
| T10 | Paths, filters, nested payloads, IDs and parent moves to B/C | Generic foreign-resource denial; no inserts, updates, deletes or unscoped metadata leak. |
| T11 | Cross-company group links/grants and duplicate pairs | Real PostgreSQL constraints reject bypassing service validation; approved overlapping groups do not duplicate totals or batch effects. |
| T12 | Grant reduction, role reduction, suspension/revocation, stale context | Subsequent operations deny revoked access despite a valid JWT; prior grants do not reappear on re-enrollment. |
| T13 | Two concurrent owner demotions/revocations; Identity suspension; first-owner activation | Named invariant prevents ownerless active company; exactly one safe serial outcome or bounded whole-transaction retry. Test trigger enforcement directly as well as services. |
| T14 | Ownership transfer acceptance, concurrent changes and rollback | Target promotion plus agreed initiator change is atomic; last owner retained; financial/legacy ownership unchanged. |
| T15 | Write races with grant revocation or company suspension | Operation serializes before revocation or rechecks and denies afterward; no mutation based only on an old context. |
| T16 | ORM SELECT/count/alias/eager load, identity map, bulk and pending batches | Executed queries enforce scope; unsafe raw/Core paths denied, cached foreign rows cannot leak, mixed unauthorized batches write nothing, no async implicit IO. |
| T17 | Legacy APIs/lists/counts, internal services, customer/Telegram/worker paths after cutover | Converted resources have no owner-wide bypass; suspended or archived company never re-enters legacy scope. Existing customer-facing flows use only their separately approved resource contract. |
| T18 | Platform administrator versus company owner/manager | Tenant rights never satisfy platform RBAC; existing active-admin/permission requirements and global administration behavior remain. |
| T19 | Existing payments, checkout, receipt file/metadata, subscription activation and review | Payer/restaurant/subscription consistency, receipt confidentiality, duplicate evidence prevention, idempotency and transactional audit remain; no activation from upload alone. |
| T20 | New co-owner without payer link; forged admin/chat IDs; company A selection with B payment | No invoice takeover or review privilege; genuine platform reviewer still uses explicit global permission, not fabricated tenant context. |
| T21 | Migration each supported starting revision; additive rollback; backfill repeats/conflicts; contract rehearsal | Constraint/data comparisons pass, unresolved cases block cutover, IDs/amounts/history preserved, rollback never reopens legacy access. |
| T22 | Scope/context/session reuse across companies/tasks and transactions | Immutable values, no mutable collection changes, no rebinding, fresh session/task and authorization recheck. |
| T23 | Error/log/audit/output capture | No JWT/code/password/secret or unrelated identity/account data stored or printed; authorized events contain necessary local actor/target evidence. |

Mock/service tests alone cannot validate FKs, deferred triggers, PostgreSQL
locks, concurrent transactions or migration behavior. Those cases require real
SQLAlchemy/asyncpg tests on an approved isolated PostgreSQL target after explicit
preflight, with disposable fixture ownership and safe cleanup. SQLite may be
used for suitable unit contracts, not as the evidence for PostgreSQL guarantees.

### 10.3 Acceptance gates before enabling any tenant business path

- Model/type/constraint review passes, including exact permission assignments,
  last-owner enforcement, explicit-grant emptiness and the grouping decision.
- Every converted entry point has a scope/permission rule and negative tests,
  including legacy, aggregate, file download and internal caller paths.
- All catalogue authorization cases and cross-company denial cases pass;
  migration/locking guarantees have PostgreSQL evidence rather than mocks alone.
- Existing billing and platform RBAC regressions pass with unchanged financial
  outcomes and permissions. No production identities or associations are seeded.
- Backfill coverage and conflict reports account for every affected row before
  its company cutover; rollback remains fail-closed.
- Run the appropriate existing full offline regression/coverage command only
  during implementation verification, retain separate app/API coverage reports
  and avoid lowering the accepted baseline without review. This design does not
  claim new test results or a new coverage measurement.
- Keep `OIDC_DIAGNOSTICS_ENABLED=false`, `OIDC_ALLOW_LOCAL_HTTP=false`,
  `DEBUG=false`, `DB_ECHO=false` in the approved development execution profile.
  A later real business E2E test requires trusted HTTPS and separately approved
  test identity mapping, not reactivation of K8 diagnostics.

## 11. Approvals required before K9.2-B

The following remain proposals requiring validation:

1. D1–D4: company boundary, local integer IDs, single-role policy, owner
   company-wide scope and exact field/state/constraint contracts.
2. D5: many-to-many canonical grouping, direct-FK retirement, conflict handling
   and the later singular-to-plural API contract change.
3. D6 and section 3: exact role/permission rows, no initial manager delegation,
   employee fulfillment allowlist review and billing payer restrictions.
4. D7: operator-approved issuer-qualified Identity registration/linking,
   target acceptance and separate Owner/Admin approval. No `owner-test` binding
   is requested or authorized by approval of the design alone.
5. Section 6: lifecycle/recovery authorities, acceptance proposals, last-owner
   deferred enforcement, governance-only transfers and emergency company
   suspension when identity security action would remove the last owner.
6. D8 and sections 7–9: transaction lock/revision contracts, explicit cutover
   barrier, migration sequencing and recovery without owner-wide fallback.
7. The exact K9.2-B implementation scope and which development-only schema
   work may be prepared afterward. Creating a revision, executing it, applying
   real mappings and opening tenant business endpoints are separate reviewable
   actions; none follows automatically from this document's existence.

K9.2-A ends with this document. Existing application protections remain in place.
K9.2-B begins only after design validation and agreement on its implementation
scope; production, deployment, identity links and external services remain
outside the present authorization.
