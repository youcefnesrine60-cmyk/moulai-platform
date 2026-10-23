# MoulAI frontend

React/strict TypeScript/Vite workspace for the approved Frontend roadmap step.
No backend, Keycloak, K10 test route or deployed Render service is connected.
The workspace implements access, organization/restaurant selection, restaurant
profiles, catalogue management and order views, plus a separate platform shell.
All changes described below operate on explicitly synthetic local review data.

## Local startup

Use **Node 24 LTS** and npm. All direct versions are exact in `package.json`;
`package-lock.json` locks the complete installation. Do not use peer-dependency
bypass flags. PowerShell examples use `npm.cmd` without changing execution policy.

```powershell
Set-Location D:\MoulAI\frontend
npm.cmd ci
npm.cmd run dev:review
```

Open [the loopback review](http://127.0.0.1:5173/access). Every screen carries a
synthetic-data banner. Use the labeled review profile selector; it never asks
for credentials or creates an identity. The review adapter lives only in memory
and uses no HTTP endpoint. Reloading clears the synthetic session; only the
language and theme preferences are stored. Reviewer profiles cover Owner with companies A/B,
Manager, Staff with one/zero grants, platform admin, unlinked/suspended identity
and a recoverable error screen.

For this checkout, Node was installed portably under ignored project tools.
If Node is not already on PATH, prepend it in the current terminal only:

```powershell
$env:Path = 'D:\MoulAI\artifacts\frontend-tooling\node-v24.22.1-win-x64;' + $env:Path
```

The normal command `npm.cmd run dev` starts the **disconnected** profile.
The real sign-in button is explicitly unavailable. There is no simulated-data
fallback in normal development or the production build. This is the intended
closed integration boundary, not a configured Keycloak login.

## Screens and source responsibilities

| Browser view                                                         | Implementation                                                                      |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `/access`                                                            | Access explanation, FR/EN/AR and theme selection and local-only review entry.       |
| `/workspace`                                                         | Explicit organization selection for the exact synthetic identity.                   |
| `/workspace/organizations/:organizationId/restaurants`               | Only the selected organization's authorized restaurant projection.                  |
| `/workspace/organizations/:organizationId/restaurants/:restaurantId` | Restaurant profile and permission-filtered navigation.                              |
| `…/:restaurantId/catalogue`                                          | Categories, products, prices/availability, product-bound option groups and options. |
| `…/:restaurantId/orders`                                             | Filtered, paginated order list with responsive cards.                               |
| `…/:restaurantId/orders/:orderId`                                    | Items, totals, payment projection, history and permitted note review.               |
| `/platform`                                                          | Separate platform administration shell; no implicit tenant membership.              |

These are browser navigation paths, not API endpoints. Profile and catalogue
create/edit operations and order-note changes use a shared validated two-step
dialog. Its final button explicitly applies a **local review change**; nothing
is sent to a backend or saved persistently. Staff is read-only; Owner/Manager
controls depend on the existing permission catalogue and their restaurant grants.
No fulfillment, payment mutation, activation, ownership transfer or deletion
control is released. Other modules remain visibly awaiting integration.

Company and restaurant query keys include the exact identity and selected IDs.
Each adapter instance owns separate mutable snapshots. Session changes clear
those snapshots, and sign-out cancels reads and clears the cache. The adapter
checks scope and permission again after its cancellable delay; foreign category,
product, group, option and order references fail. Stale review revisions refuse
overwrites, and closing/navigating away cancels a pending edit. This review-only
counter is not a claim that existing APIs provide a revision field.

`src/shared/business/` defines view contracts and input constraints; the shared
restaurant frame, editor, empty states, formatting and feature screens live in
`src/features/management/`. `src/review/managementAdapter.ts` and
`restaurantFixtures.ts` are imported only through the existing loopback review
boundary. No production adapter or new HTTP contract is invented here.

`src/shared/access/contracts.ts` defines adapter view projections. It does not
claim a public organization/capability API exists. The fixture permissions match
the frozen E1 seed and are checked against it without executing Python or SQL.
They are review data only, not a second real authorization system. No profile
receives `tenant.orders.fulfill` or automatic platform permissions.

## Languages, themes and official brand assets

The operator-supplied DAS v3 plates and two PDFs have been examined. The exact
source titles, eleven-rule mapping and web interpretations are recorded in
[the identity delivery](../docs/frontend-identity-and-das.md). Current user-approved
SaaS anchors are Deep Navy `#0B1324`, Light Mint `#E6F6E3` and Teal `#006E5F`;
their difference from DAS-10's printed examples is explicitly documented.

`tokens.css` defines both Light and Dark with semantic surfaces, text, gradients,
hover/focus/disabled and status tokens. Choose Light, Dark or System preference
using the appearance control in headers or edit dialogs. The single pre-paint
store is embedded synchronously from `public/theme-init.js` into the HTML by
Vite; React subscribes without replacing providers or drafts. Explicit theme
preference persists, system changes are followed when selected, and blocked
storage keeps controls usable in memory.

i18next provides complete French, English and Arabic UI catalogs. Locale changes
preserve selected company/restaurant, filters, raw merchant content, drafts and
confirmations. Arabic retains semantic RTL and direction-aware controls. Sora
and Tajawal are self-hosted according to DAS-04; no font/CDN request is needed.
Arabic semibold maps to Tajawal's real 700 face because no 600 exists.

The approved `MOULAI-ANG 02.png` is copied byte-for-byte to
`public/brand/moulai-logo.png`. Shared `Brand` renders it at its original
1265:331 aspect ratio, with a constant light backing in both themes so its Navy
details stay readable. No recoloring, tracing, cropping or RTL mirroring is used.
The supplied icon presentation sheet is a reference, not an individual favicon;
standalone approved icon exports are still needed before adding browser/app icons.

Radix primitives provide direction-aware select/dialog interactions. Shared
buttons, badges, pending/error panels, CSS Modules and tokens keep states
consistent. French, English and Arabic catalogs, Arabic plural forms, semantic document
`lang`/`dir`, logical CSS, mirrored directional arrows and local Sora/Tajawal
fonts are included. No font CDN is contacted. The font licenses are distributed
under `public/licenses/` and retain their original terms.

## Checks and evidence

```powershell
npm.cmd run typecheck
npm.cmd test
npm.cmd run test:guards
npm.cmd run build
npm.cmd run format:check
npx.cmd playwright install chromium --only-shell
npm.cmd run test:e2e
```

Playwright owns separate loopback review/production-preview servers and stops
them after tests. It refuses HTTP requests outside those two local ports.
The config keeps downloaded browsers and results under ignored `artifacts/`;
before browser installation on this Windows checkout, use the same browser path:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = 'D:\MoulAI\artifacts\frontend-tooling\browsers'
```

Tests cover route composition, grants, same-owner A/B separation, denied company
selection, unlinked/suspended access, error/retry, platform separation, logout,
catalogue forms/confirmations, availability, price precision, order filtering,
note-only updates, stale writes, cancellation, theme changes, Arabic direction and mobile navigation.
The latest delivery report is [internationalization, themes and DAS](../docs/frontend-identity-and-das.md),
following the accepted [restaurant/catalogue/order delivery](../docs/frontend-management-delivery.md).
Current browser output is retained in ignored `artifacts/frontend-identity-validation/`;
prior evidence remains in `artifacts/frontend-validation/` and
`artifacts/frontend-management-validation/`.
Automated accessibility checks support
review; they are not a full WCAG certification. Accepted backend campaigns are
not part of these commands.

The guard check resolves the real Vite configuration without starting a server:
it requires refusal of both a review publication build and a non-loopback review
host. Normal builds also check that known synthetic fixture data is absent.

## Publication boundary

`npm.cmd run build` emits an independently built **disconnected** application.
Review mode cannot be built and cannot bind to a non-loopback host. Synthetic
data is dynamically imported only for a loopback development review and is
eliminated from production output. Vite does not load root or frontend `.env`
files (`envDir: false`); no Python environment or secret is read by this app.

Business Integration will supply approved Keycloak bindings and backend tenant
contracts, then connect the typed adapters. Do not connect `/test/*`, diagnostic
probes or the Health-Only Render URL. Do not disable Health-Only, enable
Auto-Deploy, publish or deploy this frontend as part of local review.
K11 and Pilot retain their approved positions after Business Integration.
