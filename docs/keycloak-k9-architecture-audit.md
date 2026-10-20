# K9.1 — Organizations and tenant mapping architecture audit

Audit date: 2026-10-18. Status: **audit complete; K9.2 implementation awaits approval**.

## Scope and decision proposed for review

Use **architecture B for the first K9 implementation**: Keycloak authenticates
identities; PostgreSQL owns company membership, business permissions and resource
access. Keep a future integration boundary for architecture A, where Keycloak
Organizations also supports customer identity administration. In both options,
PostgreSQL remains the final authority for business access.

The proposed tenant is a **business or commercial group with a shared access
boundary**. A tenant can contain multiple restaurants and physical branches. An
individual owner can participate in several tenants. Neither an existing owner
record, restaurant group nor Keycloak Organization should automatically become
the tenant without an explicit mapping decision.

This is a static audit of the local working tree, including existing uncommitted
K8 and authorization changes. The review examined models, route composition,
authentication dependencies, tenant session guards, associated services and
repositories, migration declarations and relevant test sources. It is not a new
penetration test or a verification of deployed schemas and data.

Only this report was added. No application code or configuration was changed;
no application startup, database connection, migration, test suite, Keycloak
administration, deployment or Telegram operation was performed. K8 diagnostics
were not reactivated. The earlier real-user validation is recorded in the
[K8 final E2E report](keycloak-k8-final-e2e.md); it establishes diagnostic
authentication, not business membership. Existing test results were not rerun
or remeasured for this audit.

## 1. Existing models and relationships

### 1.1 Identity and authorization records

| Model | Existing meaning and relationships | Consequence for K9 |
| --- | --- | --- |
| [Owner](../app/models/owner.py) | Owner, registration and billing profile; required unique Telegram `chat_id`; nullable unique `auth_subject`; one-to-many restaurants, groups, subscriptions and payments. | A person/profile and an existing ownership anchor, not an established company entity. No issuer, company membership or employee delegation is recorded. |
| [User](../app/models/user.py) | Customer/Telegram registry with consent, contact information and nullable unique `chat_id`; associated customer orders and payments. | Not a general workforce identity table. It has no OIDC subject or organization membership. |
| [Admin](../app/models/admin.py) | Platform administrator with nullable unique `auth_subject`, active flag, required unique `chat_id`, optional persisted RBAC role and a legacy role string. | Platform authority is separate from restaurant ownership. There is no company-specific administrator assignment. |
| [Role, Permission and role_permissions](../app/models/rbac.py) | Global role and permission codes; many-to-many role/permission links; roles are assigned to administrators. | Existing RBAC does not model employee membership, restaurant grants or tenant role assignments. |

There is no foreign-key identity link between `User`, `Owner` and `Admin`.
Matching Telegram IDs, names or email addresses is not a verified OIDC account
association. Subject uniqueness is enforced separately in owners and admins;
the same subject could therefore appear in both tables. That can be legitimate
only with explicit, separately authorized associations.

`Owner.auth_subject` and `Admin.auth_subject` are nullable. The source code does
not establish how many existing records are linked, or whether `owner-test` is
linked to either kind of business identity. No live records were inspected.

### 1.2 Business resource hierarchy

| Model | Actual association | Boundary implications |
| --- | --- | --- |
| [Restaurant](../app/models/restaurant.py) | Required `owner_id`; optional `group_id`; catalog, agents, orders, subscriptions and operational records reference restaurants. | The current owner access partition is reached through `Restaurant.owner_id`. The location uniqueness constraint is not a tenant integrity constraint. |
| [Branch](../app/models/branch.py), table `branches` | Physical outlet with required `restaurant_id`; orders can reference it. | Inherits its restaurant's ownership. It has no independent membership or company identity. |
| [RestaurantGroup](../app/models/restaurant_group.py), table `restaurant_groups` | Required `owner_id` and name; `restaurants` relationship uses `Restaurant.group_id`. | A grouping structure, without a workforce membership, company lifecycle or legal identity. |
| [RestaurantBranch](../app/models/restaurant_group.py), table `restaurant_branches` | Link containing `group_id` and `restaurant_id`. | Despite its name, this is a group-to-restaurant link, not a physical `Branch`. It provides a second grouping mechanism. |
| [Order](../app/models/order.py) and [order item/history models](../app/models/order_item.py) | Order belongs to a restaurant, optionally a physical branch and customer. `employee_id` and history `changed_by_employee_id` are nullable integers without workforce foreign keys. | Employee audit labels do not establish employee identity, company membership or permission. |
| [Payment](../app/models/payment.py) and [Subscription](../app/models/subscription.py) | Both retain owner and restaurant identifiers; payments can reference subscriptions. | Billing ownership and restaurant consistency must survive K9. Company membership does not itself authorize billing changes. |

The current shape is:

```text
Owner
  +-- Restaurant -- physical Branch (branches)
  |      +-- catalog / agents / orders / billing / operational data
  +-- RestaurantGroup
          +-- Restaurant.group_id             [direct association]
          +-- RestaurantBranch -> Restaurant  [separate link table]

User -> customer orders/payments
Admin -> platform Role -> Permissions
```

The direct group association permits one group per restaurant; the link table
permits multiple group links. No mechanism reviewed guarantees agreement between
the two. The model and the
[test schema baseline](../alembic_test/versions/ae6a266365fb_test_schema_baseline.py)
declare independent foreign keys, but no unique group/restaurant pair or
constraint establishing equal owners. This is a statement about source
declarations, not a live-schema inspection.

The risk is observable in both
[`RestaurantGroupService.add_branches_to_group`](../app/services/business/restaurant/groups/service.py)
and
[`RestaurantBranchService.create`](../app/services/business/restaurant/branches/service.py):
they verify group and restaurant existence, but do not compare their owners.
The group bulk operation writes links without synchronizing `Restaurant.group_id`.
The [restaurant creation handler](../app/services/business/restaurant/restaurants/handlers.py)
also passes the supplied `group_id` to persistence without a group-owner
comparison in that creation path.

These paths are currently behind platform administration at the HTTP aggregate.
This audit identifies consistency defects and a barrier to future delegation;
it does not demonstrate an unauthenticated cross-tenant exploit.

### 1.3 Lifecycle constraints

Owner relationships declare deletion cascades for several business and billing
collections. `OwnerService.delete_owner` currently refuses owners with
restaurants, which limits that particular service path. Customer relationships
also declare order/payment cascades. Staff offboarding must therefore revoke a
membership, not delete or repurpose an owner/customer record. Retention of
financial and audit records needs an explicit policy before identity lifecycle
changes.

## 2. Current JWT subject to business access flow

### 2.1 Shared authentication boundary

The implementation is in [auth.py](../app/api/auth.py),
[oidc.py](../app/core/security/oidc.py) and
[central Settings](../app/core/config.py).

1. A Bearer token is checked against configured issuer, audience and trusted JWKS.
2. The allowed algorithm is RS256. Validation checks signature, `iss`, `aud`,
   expiry, required `iat`, token type and nonempty bounded `sub`; `nbf` is checked
   when present. Token headers cannot select an arbitrary JWKS endpoint.
3. Invalid or missing credentials produce authentication rejection; unavailable
   or invalid trust configuration/keys can instead fail closed with 503.
4. A verified token establishes identity only. It does not create an owner,
   administrator, restaurant, tenant or membership.

`OIDCPrincipal` carries issuer, subject and roles extracted from
`realm_access.roles`. The diagnostic `require_realm_roles` dependency checks
those roles without granting database business permissions. There is no
Organization claim consumer or Organization-to-resource mapping today.

### 2.2 Owner path

```text
Verified JWT
  -> _get_authenticated_subject()
  -> get_current_owner(): owners.auth_subject == verified sub
  -> OwnerPrincipal(owner_id)
  -> explicit resource ownership checks and/or owner-bound SQLAlchemy session
  -> business operation
```

An unlinked identity receives 403. A realm role named `owner` is neither a
substitute for the stored association nor a requirement in `get_current_owner`;
the existing stored ownership association is the business authority.

The lookup does not filter `registration_status`, and Owner has no active flag.
Approval checks exist in specific business policies, such as trial eligibility,
but owner authentication is not a general approval/suspension gate. K9 must
define the desired active-company and active-membership policies explicitly.
Owner self-service updates already reject administrative fields beyond name,
phone and email; this report does not infer a self-approval bypass.

The normal owner create/update schemas and service paths do not provision an
OIDC association. No general verified owner account-linking workflow was found
in those paths. Do not backfill missing subjects from Telegram IDs or email.

### 2.3 Platform administrator path

```text
Verified JWT
  -> get_current_admin(): admins.auth_subject == sub AND is_active
  -> AdminPrincipal(admin_id)
  -> require_admin_permission(code)
  -> current active persisted RBAC role and its permissions
  -> platform administration operation
```

[`AdminService.check_admin_permission`](../app/services/business/admin/admin_service.py)
loads the authorization context through
[AdminRepository](../app/repositories/admin/admin_repo.py). A required permission
needs an active persisted role and its explicit code or `*`. A legacy role string
or a Keycloak `admin`/`owner` role alone does not satisfy this dependency.
Role-name checks elsewhere are a distinct legacy mechanism and must not become
the employee authorization contract.

The explicit `bind_admin` operation in
[billing_operations.py](../scripts/billing_operations.py) includes configuration,
database confirmation, active administrator/permission, uniqueness and guarded
replacement checks. It was inspected, not executed. It is not automatic
provisioning or permission to alter existing identities in K9.

### 2.4 Issuer and local-development limitations

Current owner/admin rows persist only `sub`, while the verifier trusts one
configured issuer. Switching issuers in the future could otherwise reuse a
subject value against the wrong historical local identity. Identity keys should
therefore become `(issuer, subject)` with explicit provenance for backfills.
OIDC defines subject identifiers within their issuer, rather than as globally
unique person identifiers.
[Source: OpenID Connect Core, subject identifiers](https://openid.net/specs/openid-connect-core-1_0.html#SubjectIDTypes).

Business authentication deliberately remains HTTPS-only. The K8 local HTTP
exception is restricted to gated diagnostics; setting the diagnostic flags does
not enable business authentication against the HTTP test realm. Future local
business E2E work needs trusted local HTTPS or a separately reviewed development
trust policy. This audit changes neither policy nor flags.

## 3. Tenant protections, coverage and identified risks

### 3.1 Where boundaries are enforced

| Entry path | Current protection | Limit for K9 |
| --- | --- | --- |
| Catalog APIs: products, categories, option groups and product options | `get_current_owner`, `get_owner_tenant_db` and owner-aware service construction bind a real SQLAlchemy session. Parent ownership/consistency is checked. | All authorized restaurants share the same owner partition; no company selection or employee permissions. |
| Agent, channel, conversation and message APIs | Same owner session boundary; nested restaurant/agent/channel/conversation ownership checks. | An employee must not receive the owner's full partition by impersonating `OwnerPrincipal`. |
| Standalone physical branches API | Owner identity, owner-bound session and restaurant checks. | No separate company, outlet assignment or staff scope. |
| Orders and order items | `get_current_owner` plus `require_owned_restaurant`, `require_owned_order` or `require_owned_order_item`; ordinary database sessions. Child validation checks branch/catalog relationships. | Isolation depends on explicit route/service checks; these entities are not automatically included in the owner session guard. |
| Payments, manual invoices and receipt access | Verified owner, matching owner/resource checks and explicit owner filters; payment/subscription services validate relevant ownership consistency. | Preserve these checks during company mapping. Lower layers accepting identifiers are not automatically authorized for arbitrary callers. |
| Owner profile self-service | Owner ID equality; chat lookup retrieves the authenticated owner's record before comparing chat ID; administrative profile fields are rejected. | No company membership or workforce management. |
| Restaurant aggregate: restaurants, groups, group links, metrics, counters and payment settings | The parent router requires platform permission `restaurants.manage`. Child routes inherit it through application router composition. | This is global platform administration, not tenant-manager self-service. Lower services commonly query IDs without a tenant principal. |
| Admins, admin sessions/logs, user registry and registration administration | Persisted platform administrator and `admins.manage`; global owner list/create/status operations use the same permission. | Do not grant these global permissions to a company manager. |
| Manual payment review | Separate platform `payments.review`, including deliberately cross-owner review access. | Preserve the explicit administrative exception and its authorization; do not make it a tenant permission by name reuse. |
| Telegram webhook and internal customer actions | Webhook secret verification before dispatch; separate Telegram/customer context and resource checks in customer order flows. | This is not Keycloak authentication or an employee membership system. Keep any future Telegram identity link explicit and separately verified. |

Evidence: [application router composition](../app/main.py),
[restaurant aggregate guard](../app/api/v1/restaurant/__init__.py),
[owner routes](../app/api/v1/owners.py),
[orders API](../app/api/v1/orders.py),
[manual billing API](../app/api/v1/manual_payments.py),
[order creation and child validation](../app/services/business/orders/create.py),
[customer order placement](../app/services/business/orders/placement.py),
[payment service](../app/services/business/payment_service.py),
[subscription service](../app/services/business/subscription_service.py) and
[Telegram ingress](../app/api/webhook.py).

### 3.2 Exact scope of the session guard

[`tenant_scope.py`](../app/core/security/tenant_scope.py) protects ten mapped
models: `Restaurant`, `Category`, `Product`, `OptionGroup`, `ProductOption`,
`Agent`, `Channel`, `Conversation`, `Message` and physical `Branch`.

It scopes ORM reads, counts, aliases and supported bulk updates/deletes; checks
pending object parent relationships before flush; rejects raw SQL and detected
mixed Core/ORM escape paths; and refuses unsafe bulk inserts or parent changes.
Binding requires a clean initial unit of work, evicts cached protected objects
and cannot switch to a different owner. Constructor binding performs no SQL,
preserving async SQLAlchemy safety.

This is a session-level application guard, not PostgreSQL row-level security.
It is not installed automatically on every `get_db` session and does not cover
every mapped entity. In particular, group/link models, orders/items, payments,
subscriptions, customers and operational counters/metrics are outside its
automatic model map. Their protection relies on their respective entry point,
explicit predicates and authorized internal caller. Absence from this map alone
does not prove an HTTP data leak.

Generic repositories and several internal business services accept resource IDs
or optional owner filters without an authenticated context. Those are trusted
building blocks today; exposing them to delegated users requires authorization
at the service boundary as well as the API boundary. Session reuse, background
jobs and alternate entry points need their own explicit contexts.

### 3.3 Requested user scenarios

| Scenario | Current outcome established by source | Required target behavior |
| --- | --- | --- |
| Owner of one restaurant | A verified stored subject association and owned resource checks establish access. | Active membership and the selected company's restaurant scope. |
| Owner of several restaurants | Owner-bound paths cover every restaurant with that `owner_id`. | Several restaurants in one company may be shared; restaurants in distinct companies remain separate even with the same owner. |
| Authorized company manager | No company-manager membership or role assignment exists. | Explicit local membership, tenant permissions and restaurant grants. |
| Employee with limited permissions | No employee identity/assignment model exists; order employee integers do not authorize access. | Least privilege; no inherited platform administration or owner-wide access. |
| Authenticated user without local association | Owner/admin lookup denies access with 403; diagnostic identity is separate. | No automatic membership from realm role, email, domain or Organization claim. |
| Access to another owner's company data | Audited owner checks filter or reject foreign resources, commonly with 404. | Keep that behavior and add company separation within one owner's portfolio. |
| Platform administrator | Explicit active local association and persisted permission permit defined global operations. | Separate platform context; tenant-management membership is a different grant. |

### 3.4 Risk register

Priorities describe work needed before K9 delegation. They are not claims that
the current protected application has a demonstrated external exploit.

| ID | Priority | Finding and evidence | Required treatment before the affected K9 path opens |
| --- | --- | --- | --- |
| K9-R1 | High | Owner partition conflates identity/ownership and tenant boundary; no membership model. | Introduce company membership and an immutable selected-tenant context. Never delegate by substituting the business owner's ID. |
| K9-R2 | High | Group direct/link associations can diverge; audited create/link paths do not enforce matching ownership. | Resolve grouping semantics, inventory contradictions and enforce same-company relationships before backfill or delegation. |
| K9-R3 | High | Global restaurant administration and several lower services have no company membership check. Their current protection is platform RBAC. | Keep these routes protected; introduce dedicated scoped services/routes rather than weakening the aggregate guard. |
| K9-R4 | High | Session isolation covers a finite model set and only bound sessions. | Inventory every newly delegated read/write/export/count and its parent chain. Explicitly authorize unguarded entities and non-HTTP callers. |
| K9-R5 | Medium | Nullable subject-only links; no universal account association; issuer provenance is not stored locally. | Use issuer-qualified identity keys, reviewed linking and denial for unlinked identities; no inferred backfill. |
| K9-R6 | High | Platform roles and wildcard permissions are global, not employee roles. | Separate tenant role assignments and a tenant permission allowlist from platform RBAC. |
| K9-R7 | Medium | Owner authentication does not evaluate registration status; no generic owner suspension flag. | Approve explicit company/membership suspension and registration policies; enforce them consistently on business access. |
| K9-R8 | Medium | Legacy identity profiles, business ownership and financial deletion cascades have different lifecycles. | Revoke memberships without deleting historical owner, customer, invoice or audit data. |
| K9-R9 | Readiness | K8 proves local diagnostic authentication, not HTTP-realm business access or live tenant mapping. | Plan a separately authorized business E2E profile and approved association; preserve current HTTPS rules meanwhile. |

No runtime membership, deployed schema, Keycloak version, Organization settings
or actual foreign-owner group links were verified. Those remain explicit
validation tasks, not assumed facts.

## 4. Keycloak Organizations: architecture A versus B

### 4.1 Verified product capabilities and limits

The official Keycloak 26.8.1 guide describes Organizations within a realm for
B2B identity management, member onboarding and linked identity providers.
Organization claims depend on requested scopes and mapper configuration;
organization IDs are not included by default. Managed member removal can delete
the realm account; unmanaged members have an independent lifecycle. Disabling
an organization does not prevent unmanaged members from authenticating to the
realm, although their organization metadata is omitted.
[Source: Keycloak Server Administration Guide, Organizations](https://www.keycloak.org/docs/26.8.1/server_admin/).

This documentation version is a reference, not evidence of the installed local
version. Before architecture A, verify that version's exact membership, mapper,
scope and lifecycle behavior. No Keycloak configuration was inspected or changed
in this audit. The implementation conclusions below are MoulAI design proposals.

### 4.2 Comparison

| Criterion | A: Keycloak identity and Organizations; PostgreSQL business authority | B: Keycloak identity/global roles; PostgreSQL business associations |
| --- | --- | --- |
| Business authorization | Requires local resource mapping, active membership and permissions despite any Organization claim. | Same local checks, with one business membership authority. |
| Fit with current MoulAI | Needs the local membership foundation plus a Keycloak integration contract. | Direct extension of current PostgreSQL ownership joins and persisted RBAC boundaries. |
| Managers, employees and restaurant subsets | Still needs application-specific grants and resource constraints. | Modeled directly in local memberships and restaurant grants. |
| Multi-company user | Must reconcile identity membership and selected company with local access. | One identity can hold multiple independent memberships; selection is validated locally. |
| Customer identity administration | Can provide a customer identity directory/federation layer, subject to verified product/version behavior. | Requires local invitation/membership administration; identity remains with Keycloak. |
| Operational complexity | Two membership representations require an authority matrix, provisioning, retries, revocation and reconciliation. | Fewer synchronization dependencies for initial company access. |
| International expansion | Useful when enterprise identity requirements justify integration; country and billing policies remain local. | Provider-neutral business IDs and memberships support expansion without binding tenant identity to restaurant or region. |
| Failure handling | A valid or stale claim must not override revoked local access; incomplete synchronization denies business access. | Current local membership is checked independently of realm role freshness. |

**Recommendation: B first, A only when justified by a reviewed B2B requirement.**
This reduces initial synchronization work while addressing the actual missing
company/employee model. It keeps A possible without rewriting business resource
ownership. Architecture A is a valid later option, not a replacement for local
authorization.

If A is adopted later, explicitly choose the source of identity membership and
the process for approving business membership. Use an issuer-qualified external
Organization ID binding; aliases, names and email domains are not authorization
keys. Unknown claims must never create tenants or grants automatically. Review
member deletion against identities used by multiple companies. Use idempotent
provisioning, auditable reconciliation and deny access while required mappings
are absent. Do not treat organization-related role claims as global company
permissions or place tenant authority into the existing realm-role gate.

## 5. Proposed K9 target model

### 5.1 Tenant semantics and minimal additions

A tenant represents a business access boundary. A commercial group is one tenant
only if its restaurants intentionally share governance and data access. A brand
collection or an owner's entire investment portfolio does not establish that
boundary. An existing `RestaurantGroup` can remain an organizational structure
inside a company; it must not be promoted automatically into a company.

Keep existing resource primary keys and the project's base model conventions.
The following conceptual names do not create tables or finalize migration names.

| Proposed component | Minimal responsibility | Avoided duplication |
| --- | --- | --- |
| `Identity` | Unique exact `(issuer, subject)`, lifecycle state; explicit optional links from existing owner/admin profiles. | No new password store or copy of all Keycloak profile data; `User` remains the customer registry. One identity may have separately approved owner and platform-admin links. |
| `Organization` | Stable local business ID, name and lifecycle state. | Does not replace Restaurant, Branch, customer User or owner billing history. |
| `OrganizationMembership` | Unique identity/company pair, active/revoked state and tenant role assignment. | One canonical business membership record, independent of realm roles. |
| Tenant role policy | Small initial owner/manager/employee role set with persisted business permission assignments. | Reuse existing permission definitions where semantics match, with an explicit tenant allowlist. Keep tenant roles/assignments separate from `Admin.role_id`, platform `*`, `admins.manage`, global `restaurants.manage` and `payments.review`. |
| Membership restaurant grants | Explicit restaurant subset where needed, constrained to the same company. | Do not duplicate company-wide resource lists or manufacture Owner records for employees. |
| Resource company assignment | Restaurant and RestaurantGroup gain company ownership; physical Branch inherits through Restaurant. | Derive child scope through existing parents rather than copying tenant columns onto every table without a demonstrated constraint/query need. |

Start with one tenant role per membership unless actual use cases require
multiple roles. Define company-wide versus explicit restaurant scope as a
non-null, validated policy; an empty explicit grant set grants nothing.
Company-wide access is deliberate, not the fallback for missing grant rows.
Branch-specific delegation is a later explicit policy if needed; unsupported
fine-grained scopes must be denied rather than widened.

Existing `Owner.owner_id` relationships remain financial/ownership references
during transition. Membership is the future authorization source; owner IDs must
not remain a second implicit grant source for routes already converted to K9.
Do not migrate subscriptions to company-wide billing or alter currencies,
prices, entitlements or receipt approval as part of tenant mapping. Existing
manual payment verification and payment/subscription consistency stay intact.

### 5.2 Authorization contract

The future business request flow should be:

1. Validate the access token using the existing trusted verifier.
2. Resolve an active local identity by exact issuer and subject; reject absent
   association. Do not provision privileged identities during authentication.
3. Treat a selected company ID from a path/header as untrusted input. Resolve
   its active local membership and company state from PostgreSQL.
4. Build an immutable `TenantContext`: identity, company, membership, permitted
   actions and restaurant scope. Do not accept these facts from request bodies.
5. Apply the required business permission and resource scope together. Verify
   parent company and child restaurant consistency on reads, writes and moves.
6. Bind one request unit of work to that context. Prevent context switching,
   cached entity leakage and partial mixed-company writes.

An owner member can access restaurants in that selected company according to
policy; the same identity's second company needs its own context. A manager
cannot grant permissions they do not possess or issue platform administration
rights. Membership changes, identity links and owner transfers require explicit
authorization and an audit trail. Define protection of the last active company
owner before allowing offboarding or role changes.

Use a separate `PlatformAdminContext` for the existing platform APIs, retaining
their active local administrator and permission checks. An authorized global
operation is an explicit administrative use case, with actor, action and target
recorded; it is not a tenant-scope-disable option exposed to business callers.
Never use a Keycloak role or Telegram ID as that administrative authority.

Under optional future architecture A, the external organization binding is a
provider adapter, not a second RestaurantGroup or local permission engine.
PostgreSQL still decides resource access and revocation. Do not implement its
provisioning or event infrastructure before that integration is approved.

## 6. Potential migrations — proposed only, not executed

No Alembic revision was created, no schema was introspected and no database
write occurred. A future migration design should proceed in separate stages:

1. **Inventory and approve mapping.** Read-only development diagnostics should
   classify restaurants by actual business, enumerate direct/link group
   contradictions, duplicate links and owner/group inconsistencies, and identify
   nullable subject associations. Do not assume one owner equals one company.
   Stop automatic backfill for ambiguous records.
2. **Expand.** Add identity, company, membership and minimum tenant policy/grant
   structures. Add nullable resource company references and optional profile
   identity links. Preserve every existing resource and financial identifier.
   No default administrator, employee, tenant or identity association is seeded.
3. **Reviewed backfill.** Apply an approved deterministic business mapping.
   Associate historical subjects only with verified issuer provenance and
   explicit linking authorization. No guessing from a development issuer,
   email, Telegram ID or realm role; no automatic administrator relinking.
4. **Validate integrity.** Require unique issuer/subject and membership pairs;
   enforce grant/restaurant/company consistency. Resolve whether restaurant
   grouping is one-to-many or many-to-many, then retain one canonical grouping
   representation. For many-to-many, require unique links and same-company
   enforcement. Use suitable composite foreign keys where possible; any
   necessary denormalization must have constraints preventing drift.
5. **Controlled conversion.** Move approved business paths to membership-based
   authorization with complete tests. Unconverted paths retain their existing
   guards; no global fallback from a failed company check to owner-wide access.
6. **Contract later.** Make company references mandatory only after complete
   backfill validation. Remove redundant grouping/subject representations only
   after their readers and writers have migrated and rollback is reviewed.

The repository contains separate
[application](../alembic/versions/) and [test](../alembic_test/versions/)
migration histories. Future revisions must follow their actual dependency
chains, not lexical or chronological revision-ID assumptions. Rehearsals require
the existing fail-closed database preflight: approved development branch endpoint,
matching endpoint ID and actual database `neondb_test`, never production's
`DATABASE_URL` as a fallback.

An additive rollout allows application rollback while retaining new tables.
After business data uses the new model, a downgrade that drops companies or
memberships is not an adequate recovery plan. Keep reviewed mapping evidence,
test backup/restoration on an isolated target and specify reconciliation for
writes made after cutover. Production migration and identity linking require
their own later approvals; this audit provides neither.

## 7. K9.2 implementation gates and inter-tenant test strategy

### 7.1 Proposed sequence after approval

| Stage | Work | Acceptance gate |
| --- | --- | --- |
| K9.2 design | Approve B or A; define company boundary, canonical grouping, tenant permission catalogue, grant semantics and identity-linking workflow. | No ambiguity about ownership versus membership or platform versus company administration. |
| Identity and membership foundation | Add the approved minimum schema and explicit mapping services; retain current authentication. | Unlinked identities denied; no implicit creation; issuer collisions and lifecycle rules tested. |
| Scoped authorization | Introduce immutable context, BASE SELECT predicates, scoped services/repositories and parent consistency constraints. | Reads, writes and aggregates enforce the same company and restaurant scope, including non-HTTP callers. |
| Limited business rollout | Convert only an approved set of business paths; retain global administrative boundaries. | Negative inter-tenant tests pass before each path becomes available to managers/employees. |
| Development rehearsal | Review migration SQL, rehearse transitions and verify data/relationships on approved isolated test targets. | Mandatory database isolation preflight, rollback/recovery evidence and no production access. |
| Final review | Report evidence, remaining gaps and changed files. | Separate approval for additional conversions, live identity linking or deployment. |

Keep the existing project requirements during implementation: complete type
hints, async SQLAlchemy access, keyword-only service/repository interfaces,
consistent BASE SELECT patterns, the standard source header, useful audit logging
and no token/secret logging. This audit makes no style or implementation changes.

### 7.2 Required test matrix

Fixtures should contain companies A and B owned by the same legacy owner,
company C owned by another owner, multiple restaurants/branches, an A manager,
a restaurant-limited employee, a multi-company identity, a revoked member,
an unlinked identity and separate platform administrators.

| Test family | Required assertions |
| --- | --- |
| Authentication and linking | Mocked JWKS valid/invalid JWT cases remain isolated from local Keycloak; issuer-qualified identity matching; no linkage from realm role, email, domain, `admin_id` or Telegram ID. |
| Same-owner company separation | Selecting A cannot expose B's restaurants, groups, catalog, agents, conversations, orders, receipts, totals or exports even though both retain the same legacy `owner_id`. |
| Foreign-owner isolation | Guessing C's IDs in paths, query filters, request bodies or nested payloads cannot read, change, attach or delete resources. Missing/foreign resource errors do not disclose existence. |
| Multiple memberships | An identity with A and B membership sees only the selected scope; selection is validated. A missing selection must not union all memberships. |
| Limited employee | Allowed actions succeed only for granted restaurants; disallowed financial/configuration/employee-management actions fail without side effects. Empty explicit grants give no access. |
| Manager delegation | Manager is restricted to their company and permitted grants; cannot appoint platform admins, issue platform permissions, escalate their own role or affect the last active owner without the approved policy. |
| Lifecycle and freshness | Revoked membership, disabled company, reduced permission or restaurant-grant removal denies subsequent operations even with a still-valid token. Define transaction/locking behavior for concurrent revocation and mutation. |
| Relationship integrity | Reject mixed-company group links, product/category or option moves, branch/order mismatches and agent/channel/conversation mismatches. Test contradictory legacy grouping records during backfill. |
| SQLAlchemy boundary | Real query execution for lists, counts, joins, eager loads, aliases, cached `Session.get`, flushes and supported bulk operations; reject unsafe raw/Core/batch bypasses; no session rebinding or async implicit IO. |
| Atomicity | A mixed authorized/unauthorized batch performs no partial writes. Duplicate membership/grant creation and repeated requests are idempotent or conflict safely under concurrency. |
| Platform separation | Realm `owner`/`admin`, tenant owner/manager and a forged local admin identifier do not satisfy platform RBAC. Real platform permissions allow only their intended global operations; tenant roles cannot inherit `*`. |
| Alternate entry points | Background tasks, customer actions and any future Telegram-linked administration preserve actor/resource scope; a verified webhook secret alone never grants arbitrary tenant administration. |
| Optional A integration | Unknown external organization IDs, renamed aliases, multiple claimed organizations, stale claims, disabled memberships and synchronization failure do not grant access without active approved local mapping. |
| Regression and logging | Existing RBAC/manual receipt safeguards remain intact; JWTs, authorization codes, passwords and unnecessary identity/account details do not appear in logs or stored test artifacts. |

Existing test sources provide useful starting points:
[owner session scope](../tests/test_owner_tenant_scope.py),
[order isolation](../tests/test_order_tenant_isolation.py),
[administrator boundaries](../tests/test_admin_api_keycloak_boundaries.py) and
[K8 OIDC validation](../tests/test_oidc_k8.py). They do not establish company
membership coverage before such a model exists. Unit tests must continue using
simulated JWKS and isolated fixtures. Optional real Keycloak business E2E tests
come after an approved local trust profile and explicit test identity mapping;
they must not make the ordinary suite dependent on the local identity server.

### 7.3 Decisions awaiting validation

Approval is needed for the proposed B-first direction, the business/company
tenant definition, canonical group semantics and the minimum identity/membership
model before K9.2 implementation begins. Initial permission and resource-grant
policies must then be reviewed as concrete contracts. No production change,
automatic account linking, Keycloak Organization change, diagnostic activation,
Git publication or deployment is authorized by this report.
