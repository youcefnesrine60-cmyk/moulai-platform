# Frontend inventory and proposed architecture

Date: **2026-10-21**. Status: **architecture approved by the user; first frontend
implementation authorized**. The inventory below retains its original pre-UI
scope; see [the frontend workspace](../frontend/README.md) for the delivery.
Roadmap: **Frontend MoulAI → Business Integration → K11 Production Security → Pilot**.
K8/K9/K10 remain accepted within their existing scope.

## 1. Observed starting point

Static inspection used the clean `feature/keycloak-k10-complete` checkout at
`cb0ef293aece0b706b81d4ad6d9c3cd4403804a0`. No application import, database
connection, test campaign, dependency installation or external-service operation
was needed. The operator reports GitHub synchronization and successful standalone
Health-Only deployment; this inventory does not revalidate that deployment.

| Existing asset | Finding and reuse |
| --- | --- |
| [Telegram location page](../app/webapp/map.html) | The only tracked browser UI found: HTML, inline CSS/JavaScript, Leaflet from an unpinned CDN, OpenStreetMap tiles and Telegram WebApp SDK. It selects coordinates and calls Telegram `sendData`; it is not a SaaS application. Preserve it; reuse its location-selection requirement when needed. |
| [Telegram UI builders](../app/views/) | Python keyboard/message builders, including owner and platform-admin dashboards. Reuse terminology and workflows, not their rendering code or callback authorization as web authentication. |
| [Location handler](../app/handlers/webapp_handler.py) | Processes Telegram location data during owner onboarding. The UI builder points to a separate GitHub Pages map URL; that external site's contents were not inspected. |
| Web tooling/assets | No tracked `package.json`, JS lockfile, React/Vue app, standalone CSS library, design-token system, Figma file or reusable graphical asset set found. No `StaticFiles`/template mount was found for a SaaS UI. |
| Backend | FastAPI/Pydantic schemas, async services/repositories, K8 JWT verification, K9 tenant authority and K10 optional dependencies are reusable. Python requirements do not establish a frontend toolchain. |

There is no existing frontend application to migrate. Node/npm were not found
on this terminal's PATH; their installation and version selection belong to
approved implementation, not this inventory. No package versions are pinned here.

## 2. Existing API map and actual access boundaries

Following router imports, re-exports, prefixes and inherited dependencies in
source yields **274 explicit method/path declarations**: **271 unconditional**
and **3 opt-in OIDC diagnostics**. This count excludes automatically generated
documentation routes and does not imply live availability or tenant readiness.
The unmounted metrics simulation route is excluded. A local machine-readable
inventory with source locations is retained in ignored
`artifacts/frontend-inventory/routes-static.json`; the map below remains in Git.

All paths below start with `/api/v1` unless stated otherwise.

| Area / declarations | Exact existing path examples | Current boundary and UI use |
| --- | --- | --- |
| Restaurant administration / 56 | `GET /restaurants/`, `GET /restaurants/{restaurant_id}`, `GET /restaurant-metrics/{restaurant_id}/summary`; `/restaurant-groups`, `/restaurant-branches`, `/restaurant-order-counters`, `/restaurant-payment-settings` families | The aggregate inherits platform `restaurants.manage`. Its restaurant list must not be used as an unrestricted tenant selector. |
| Catalogue / 46 | `GET /products/`, `GET /categories/restaurant/{restaurant_id}`, `GET /option-groups/product/{product_id}`, `GET /product-options/group/{group_id}` | Existing owner authentication and scoped sessions; CRUD, ordering, availability and option contracts are reusable after tenant integration. |
| Orders and items / 19 | `GET /orders/`, `GET /orders/{order_id}`, `PATCH /orders/{order_id}/status`, `GET /order-items/` | Existing owner/resource checks; not yet Manager/Staff tenant authorization. Existing status/completion endpoints do not authorize a Staff fulfillment button. |
| Operational branches / 11 | `GET /branches/restaurant/{restaurant_id}`, `GET /branches/{branch_id}/cost` | Owner-scoped location/activation contracts. `Branch` is a restaurant location; `RestaurantBranch` is a group-to-restaurant association, not the same object. |
| Agent, channels, conversations, messages / 53 | `GET /agents/restaurant/{restaurant_id}`, `GET /channels/agent/{agent_id}`, `GET /conversations/agent/{agent_id}`, `GET /messages/conversation/{conversation_id}` | Owner-scoped management/history. Message CRUD is not proof of an operator-to-customer delivery workflow. No mounted WebSocket/SSE contract was found. |
| Owners / 12 | `GET /owners/{owner_id}`, `GET /owners/`, `GET /owners/stats` | Mixed self-owner and platform-admin operations; inspect the individual action, not just the URL family. |
| Registration requests / 10 | `GET /registration-requests/`, `POST /registration-requests/{request_id:int}/approve` | Platform `admins.manage`; not self-service organization creation or membership enrollment. |
| Payments and manual billing / 21 | `GET /payments/`, `POST /billing/subscriptions`, `POST /payments/{payment_id}/receipt`, `POST /admin/manual-payments/{payment_id}/review` | Owner payment access versus platform `payments.review`. Server pricing and independent funds verification remain authoritative. |
| Platform administrators/logs/sessions / 30 | `GET /admins/`, `GET /admin-logs/recent`, `GET /admin-sessions/lookup` | Platform `admins.manage` and trusted admin identity; session credentials are not an alternative login mechanism. |
| Telegram user registry / 10 | `GET /users/`, `GET /users/stats/summary` | Platform `admins.manage`; these Telegram users are not the K9 identity/membership directory. |
| Channel and health / 3 | `POST /webhook`, `GET /`, `GET /health` | Telegram entry point and health checks, not browser authentication APIs. |
| Conditional diagnostics / 3 | `GET /diagnostics/oidc/me`, `/owner`, `/admin` | K8 probes only, disabled; not profile, permission or organization APIs. |

The [main registrations](../app/main.py), [legacy authentication](../app/api/auth.py),
[authorization policy](api-authorization.md) and
[manual-payment routes](../app/api/v1/manual_payments.py) define these boundaries.
Filters such as `owner_id` are never credentials. Grouping fields remain as
implemented; the UI must not reconcile their representations by guessing.

### K10 is reusable authorization, not a published tenant API

[Tenant dependencies](../app/api/tenant_dependencies.py) resolve the verified
`(iss, sub)`, personal associations and transaction-bound selected-company reads.
Only [the isolated test application](../test_support/tenant_http_app.py) registers:

- `GET /test/memberships`.
- `GET /test/organizations/{organization_id}/restaurants`.
- `GET /test/organizations/{organization_id}/restaurants/{restaurant_id}`.

These are test URLs, not production integration targets. Existing legacy
owner/admin mapping uses profile `auth_subject`; it must not replace K9's exact
issuer-qualified identity resolution. A Keycloak realm role never grants a
restaurant, company or platform-admin permission.

The current `MembershipSummary` contains IDs, role, scope, status and revision;
it does not provide company display names or effective permissions.
`RestaurantSummary` is deliberately a small read projection. The internal
`TenantContext` is not a client DTO or transferable capability. These are
specific Business Integration contract needs, not defects reopening K9/K10.

The deployed Health-Only service permits only `GET /` and `GET /health` by
design. The frontend must not try business requests against it, remove its gate
or reactivate K8 diagnostics. No new backend endpoint is proposed as existing.

## 3. User journeys and permission separation

Every tenant journey starts with sign-in, personal association discovery,
**explicit company selection**, then an authorized restaurant selection.
Unknown/unlinked identities get an access-unavailable screen, never automatic
onboarding or linkage. Historical/pending/suspended memberships do not authorize
entry merely because discovery lists them. Backend validation remains required.

| Persona | Proposed journey after integration | Boundary |
| --- | --- | --- |
| Owner | Selected company → restaurants → catalogue/orders/agents/reports → billing and receipt tracking | Company-bound permissions and resource grants; ownership of A and B never combines their resources. |
| Manager | Selected company → allowed restaurants → permitted catalogue, operations, conversations and reports | Stored permissions and scope; no default billing, membership governance or platform administration. |
| Staff | Selected company → explicitly granted restaurants → order/catalogue/branch reads | UI label maps to stored role `employee`. Empty grants give no restaurant access. No fulfillment or mutation enabled without an approved permission/transition contract. |
| Platform administrator | Separate platform area → registration, global restaurant administration, receipt review, admin logs/sessions | Local active admin and platform RBAC. No implicit tenant membership or Owner-to-admin elevation. |

The E1 initial policy rows contain owner **26**, manager **17**, employee **6**
permissions; none grants `tenant.orders.fulfill`. Use these rows for test-case
coverage, not as a hard-coded browser authorization engine. Membership changes,
invitation/acceptance and ownership transfers are not released just because
their permission names or models exist; E1 intentionally fences governance.

## 4. Recommended frontend architecture

Recommend **one TypeScript React SPA in `frontend/`**, independently built beside
the existing Python application. The authenticated management product has no
identified SSR/SEO requirement. A separate Node backend/BFF or Next.js runtime
would add another deployment surface without a demonstrated need here.
React documents the Vite/TypeScript starting point and its framework trade-offs;
use established routing/data libraries rather than inventing their equivalents.
[React guidance](https://react.dev/learn/build-a-react-app-from-scratch).

| Concern | Recommended choice |
| --- | --- |
| Build/language | React, strict TypeScript, Vite; npm with a committed lockfile and reproducible clean installs. [Vite](https://vite.dev/guide/). |
| Navigation/server state | React Router Data Mode for nested layouts/navigation; TanStack Query owns API cache, invalidation and retries. Route loaders coordinate Query rather than creating a second cache. [Router modes](https://reactrouter.com/start/modes), [Query](https://tanstack.com/query/latest/docs/framework/react/overview). |
| UI/design system | Accessible Radix primitives with explicit direction provider, CSS Modules and shared CSS tokens for typography, color, spacing, focus and component states. Start with one coherent theme. [Radix direction](https://www.radix-ui.com/primitives/docs/utilities/direction-provider). |
| Forms/contracts | React Hook Form and Zod for form UX; generated/reviewed TypeScript API types from the existing FastAPI OpenAPI contract. Server validation remains authoritative. [Form source](https://github.com/react-hook-form/react-hook-form), [Zod](https://zod.dev/). |
| Languages | i18next/react-i18next, French and Arabic message catalogs from the first screen; locale-aware dates, numbers and currency through `Intl`. [i18next](https://react.i18next.com/latest/using-with-hooks). |
| Verification | [Vitest](https://vitest.dev/guide/)/[Testing Library](https://testing-library.com/docs/react-testing-library/intro/) for components and adapters, [Playwright](https://playwright.dev/docs/intro) for browser journeys and RTL, [MSW](https://mswjs.io/docs/) for isolated development/test HTTP fixtures. No library is installed by this proposal. |

Proposed layout only; no directories or application code are created yet:

```text
frontend/
  src/
    app/          # Routing, providers, tenant and platform layouts
    features/     # Access, restaurants, catalogue, orders, agents, billing, platform
    shared/       # UI primitives, design tokens, API transport, i18n, formatting
  tests/          # Synthetic fixtures and browser journeys
```

Tenant views and platform administration share primitives but have separate
navigation, route boundaries and data adapters. Lazy-load feature areas. Browser
URLs may include selected company/restaurant IDs; these are navigation context,
never authority. On company change, cancel prior requests, clear scoped state
and invalidate caches. Query keys include exact identity, company and resource;
logout clears them. Ignore late responses from an earlier selection.

The future identity adapter uses Keycloak Authorization Code + PKCE S256 with
an approved public browser client, narrow redirect URIs and tokens in memory.
No browser client secret, persistent token storage, password form or realm-role
tenant mapping. This is a design contract only: no Keycloak or OIDC setting is
changed. [Official Keycloak adapter](https://www.keycloak.org/securing-apps/javascript-adapter).

Use one API boundary for Bearer headers, cancellation, typed responses and
401/403/404/409/422/503 presentation. Retry only appropriate bounded reads;
do not blindly repeat payment/review/order mutations. Never optimistically
confirm a settlement, subscription activation or order transition. Payment
upload already expects a raw PNG/JPEG/PDF body, at most 2 MiB, plus
`X-Transaction-Reference`, not an invented multipart endpoint.

## 5. French, Arabic and mobile product requirements

Set document `lang` and `dir` with the selected locale; use CSS logical
properties and direction-aware primitives. Isolate mixed identifiers, phone
numbers and bank references; use `dir="auto"` for user-entered mixed text.
Translate labels, errors, validation, plurals, empty states and confirmations,
not just navigation. Localize display without changing API enum values or
financial arithmetic. Follow [W3C direction guidance](https://www.w3.org/International/questions/qa-html-dir.en.html).

Design mobile-first at 360 px, tablet and desktop: persistent company/restaurant
context, collapsible navigation, readable order cards, filters and accessible
table alternatives, receipt upload from a phone, clear destructive confirmations.
Cover loading, empty, denied, expired-session, failed-save and offline states.
Do not queue business writes offline. Aim for WCAG 2.2 AA with keyboard/focus,
labels, contrast and generous touch targets; verify, rather than claim,
conformance. [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## 6. Concrete implementation order and roadmap boundary

After this architecture is approved, implement within the existing Frontend step:

1. Establish the build, strict checks, design tokens, accessible primitives,
   French/Arabic catalogs and responsive tenant/platform layouts.
2. Build the sign-in/session and company/restaurant selection experience,
   including unlinked, inactive, empty-grant and revoked-access states.
3. Deliver restaurant detail, catalogue/category/options and order list/detail
   screens, then agent/channel/conversation history and actual-data report views.
4. Deliver manual-billing/receipt tracking and the separate platform review,
   registration and administration screens, limited to mapped contracts.
5. Finish browser/component checks across roles, A/B switching, RTL/mobile,
   empty/error states and financial confirmations; submit one coherent frontend.

Develop these screens against typed adapters and clearly isolated synthetic
fixtures until Business Integration. Fixtures are development/test support,
never fallback "real" data. Unsupported actions remain explicitly unavailable;
no fabricated metrics, successful payments or unimplemented controls presented
as operational. This is the actual product UI prepared for connection, not a
separate disposable demonstration.

**Business Integration** then connects approved identity bindings, publishes or
adapts tenant routes using existing K9/K10 authority, supplies selected-company
display/capability contracts and maps each legacy owner/admin action correctly.
It also resolves missing web contracts for transfer instructions/plan discovery,
organization/member governance, permitted order transitions and outbound human
responses before releasing those actions. No generic organization, invitation,
subscription-list, invoice, reservation or public-cart API is assumed to exist.
Current frontend filtering must never substitute for that backend integration.

Integration verifies API base URL/CORS, real response/pagination formats
(`skip`/`limit` versus tenant `after_id`), stale permissions, server errors and
transactions on approved isolated targets. It does not connect to the public
Health-Only service by changing its mode. K11 retains production-security
configuration and release hardening; Pilot and deployment remain later steps.

## 7. Approved decision and implementation boundary

The user approved the stack, `frontend/` location, shared design system,
separate tenant/platform areas, French/Arabic/mobile baseline and the first
coherent implementation set. Initial access/selection screens use isolated
synthetic adapters pending Business Integration. Official logo artwork must be
used when supplied; no approximate logo may be drawn. Approval does not include
backend changes, migrations, runtime configuration, main integration or deployment.
