# Frontend — Restaurant, catalogue and order interfaces

Date: **2026-10-22**. Status: **implemented and locally verified; synthetic review only**.
This delivery extends the accepted frontend workspace and reuses its design
tokens, components, tenant selection, role catalogue, query provider and FR/AR
direction handling. Real business connections remain for Business Integration.

## Available screens and interactions

All paths below start at
`/workspace/organizations/:organizationId/restaurants/:restaurantId`.
They are browser views, not new API endpoints.

| View                            | Delivered behavior                                                                                                        |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Restaurant root                 | Explicit company/restaurant context, profile consultation and permitted name/type/phone/wilaya review edits.              |
| `/catalogue` — Products         | Category/search/availability filters; product creation and editing; exact decimal-price validation; availability editing. |
| `/catalogue` — Categories       | Ordered categories with create/edit forms.                                                                                |
| `/catalogue` — Options & groups | Product-bound groups, required/single/multiple choice settings, option creation/editing, supplements and availability.    |
| `/orders`                       | Status/type/reference-or-customer filters, five-row pagination, responsive order cards and empty results.                 |
| `/orders/:orderId`              | Items/options/quantities, projected totals, payment observation, state history and permitted note editing.                |

One shared Radix dialog implements edit, validation, review confirmation,
back-to-form, cancellation, pending, refusal and success states. Its final action
is explicitly **Apply to review**, never a real persistence claim. Staff controls
are read-only; Owner and Manager controls use the existing permission projections
and their selected restaurant grants. Platform administration remains separate.

The input contracts follow the existing restaurant, category, product,
option-group, product-option and order schemas/services. Product prices are
positive and at most 10,000,000 DZD; supplements allow zero and at most
1,000,000 DZD. View amounts use integer centimes; conversion to actual transport
schemas is deferred. New products keep the backend's available-by-default
behavior; availability is changed through editing. No invented option-selection
minimum/maximum fields are introduced.

Order-note editing respects the backend's locked states: delivering, delivered,
completed and cancelled. No role receives `tenant.orders.fulfill`. There is no
fulfillment, cancellation, settlement, refund, ownership/activation, deletion or
platform-administration action hidden behind a working-looking button.

## Files added and existing code reused

**15 frontend files added; 12 existing frontend files updated** relative to the
accepted first delivery. Dependencies and the lockfile are unchanged.

| Added files                                                  | Responsibility                                                                                    |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| `src/features/management/scope.tsx`                          | Shared company/restaurant admission, query keys, frame, navigation, formatting and empty results. |
| `src/features/management/RestaurantProfilePage.tsx`          | Restaurant profile consultation/edit entry.                                                       |
| `src/features/management/CataloguePage.tsx`                  | Products, categories and options/groups interfaces.                                               |
| `src/features/management/OrdersPage.tsx`                     | Order list/detail and shared status presentation.                                                 |
| `src/features/management/ReviewEditor.tsx`                   | React Hook Form/Zod edit/confirmation workflow and mutation cancellation.                         |
| `src/features/management/management.module.css`              | Shared responsive layout, forms, cards, status and dialog styles using existing tokens.           |
| `src/shared/business/contracts.ts`, `validation.ts`          | Typed projections, bounded review commands and input validation.                                  |
| `src/review/managementAdapter.ts`, `restaurantFixtures.ts`   | Session-local synthetic state and scoped mutations; no HTTP transport or storage.                 |
| `src/shared/i18n/business.fr.ts`, `business.ar.ts`           | Complete French/Arabic business-screen catalogs.                                                  |
| `tests/unit/management.test.ts`, `managementRoutes.test.tsx` | Adapter/contract/form/route regressions.                                                          |
| `tests/e2e/management.spec.ts`                               | Desktop/mobile interactions, isolation, keyboard, RTL and axe checks.                             |

Existing frontend updates: `README.md`, `playwright.config.ts`,
`scripts/verify-build.mjs`, `src/app/Shell.tsx`, `src/app/router.tsx`,
`src/features/workspace/WorkspacePages.tsx`, `src/review/syntheticAdapter.ts`,
`src/shared/access/contracts.ts`, `src/shared/access/disconnected.ts`,
`src/shared/i18n/index.ts`, `src/shared/styles/global.css` and
`tests/unit/setup.ts`. The original restaurant selection now reuses the shared
selection helper; its obsolete detail implementation is replaced by the new
restaurant frame. The documentation index links this report.

## Isolation and validation observed

Adapter caches and queries include the exact review identity and both selected
IDs. Every synthetic mutation rechecks the existing personal grants and its
permission after cancellable latency, validates child references against that
restaurant and commits one in-memory snapshot. Empty grants grant no access;
common ownership never unions companies. Stale review revisions refuse
overwrites. Session changes discard edits and pending operations; navigating
away aborts the editor's pending request. No backend revision/CAS API is implied
by this local review counter.

| Check             | Result                                                                                                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Strict TypeScript | Application, configuration and test projects passed.                                                                                                                                        |
| Vitest            | **77 passed**, including 23 existing tests and 54 new targeted tests; no failures/skips.                                                                                                    |
| Playwright        | **38 passed**, including 22 existing and 16 new desktop/mobile cases; no failures, skips or flaky results.                                                                                  |
| Responsive/RTL    | French/Arabic, desktop 1440 px, mobile 390 px and 360 px Arabic checks; no measured horizontal overflow.                                                                                    |
| Accessibility     | Keyboard escape/focus restoration and targeted axe checks on forms, catalogue and orders; no detected violations across 14 final axe scans. This is not a full accessibility certification. |
| Normal build      | Passed; 23 JavaScript assets checked for known fixture markers/chunks. Synthetic data is absent and sign-in remains disconnected.                                                           |
| Review guards     | Real Vite config still refuses review publication builds and non-loopback binding.                                                                                                          |
| Source scope      | 63 frontend source/configuration/document files; all 46 program/style files carry the standard header. No backend, migration or dependency change.                                          |

The tests caught and corrected an error-label accessibility issue: validation
text had changed the price input's accessible name. Stable labelled-by and
described-by references now preserve both the field name and error explanation.
The final service-contract review also aligned price ceilings, locked-order
notes and product-creation availability with existing backend behavior.

Run the commands in the [frontend guide](../frontend/README.md). Open the
loopback review, select a synthetic profile, then select a company and restaurant.
Catalogue/order navigation appears in that explicit restaurant context.

Evidence, source hashes and screenshots stay under ignored
`artifacts/frontend-management-validation/`. Initial first-delivery evidence
remains local under `artifacts/frontend-validation/`; artifacts are not Git
publication inputs. The first expanded browser result is retained separately
as `initial-playwright-results.json`; repeated checks are not added to test totals.

## Integration boundary

No Keycloak/API transport or K10 test endpoint is connected. The normal build
cannot enter the synthetic review. No account, token, real tenant or business
data is persisted. Full server-side validation, quotas, authoritative permissions,
transport mapping/pagination and real mutation outcomes must be connected and
tested during Business Integration; fixture behavior is not backend acceptance.

The text signature and existing provisional palette are retained. No logo was
redrawn; official artwork remains pending the approved original. Browser coverage
is Chromium desktop/mobile, not Firefox/WebKit or a real-device certification.

No backend campaign was repeated. No database/migration, external service,
Health-Only or Auto-Deploy setting, Git branch/commit, merge, push or deployment
was changed. The roadmap remains **Frontend → Business Integration → K11
Production Security → Pilot**.
