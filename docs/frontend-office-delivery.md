# Frontend — Reports, Manual Billing and Platform Administration

Date: 2026-10-26. Local frontend delivery on `feature/keycloak-k10-complete`.
No backend contract, permission seed, external service or deployed configuration
is changed. K9/K10 stay closed. Roadmap: **Frontend → Business Integration →
K11 Production Security → Pilot**.

## Screens and reuse

| Browser route | Implemented behavior and existing permission |
| --- | --- |
| `/workspace/organizations/:organizationId/restaurants/:restaurantId/reports` | Restaurant-scoped counts; `tenant.reports.read`. Owner/Manager review profiles, existing restaurant grants. Missing average/growth stay unavailable rather than invented. |
| Same restaurant prefix + `/billing` | Payment list, status filter, amount/method/date and receipt metadata; `tenant.billing.read`. Payment and receipt statuses remain distinct. |
| Billing receipt draft | `tenant.receipts.submit`; reference and PNG/JPEG/PDF metadata validation, nonempty file, maximum 2 MiB. Local confirmation only; file contents are never read or uploaded. Draft survives language/theme changes. |
| `/platform/requests` | Registration queue/detail; `admins.manage`. No Identity association or K9 enrollment inferred from approval. |
| `/platform/receipts` | Payment/receipt review context; `payments.review`. Independent bank confirmation remains required. No decision can be submitted. |
| `/platform/audit` | Administrative history/detail; `admins.manage`. No raw audit details, private receipt bytes or credentials displayed. |

The existing restaurant frame, identity/company/restaurant query keys, session
boundaries, error/loading states, design tokens, theme store, official logos and
FR/EN/AR localization are reused. Navigation now links the existing Reports,
Billing and platform entries. New view projections are in
[`shared/office`](../frontend/src/shared/office/); shared tenant pages are in
[`features/office`](../frontend/src/features/office/) and platform pages in
[`PlatformRecordsPage.tsx`](../frontend/src/features/platform/PlatformRecordsPage.tsx).

The review-only [`officeAdapter`](../frontend/src/review/officeAdapter.ts) checks
existing permissions before and after delayed reads. Report counts use the
same in-memory catalogue/order workspace as the previous delivery. Financial
records and administrative identifiers are explicitly synthetic. Fixture amounts
are not published prices, collected revenue or evidence of real subscriptions.
No extra authority is granted to Owner, Manager, Staff or platform administrators.
The normal adapter refuses all new reads as disconnected.

## Integration boundary

These are browser routes and typed view adapters, not new backend endpoints.
Source references inspected without importing the backend:

- `app/schemas/restaurant/restaurant_metric.py` and existing metrics summary route.
- `app/schemas/payment.py`, `app/schemas/manual_payment.py` and payment/manual-payment routes.
- `app/schemas/registration_request.py`, registration routes and admin-log schemas/routes.

Legacy metrics are under platform restaurant administration; they are not an
approved tenant API. Business Integration must map them through verified tenant
authority. Receipt integration must use the existing bounded raw-body contract
and `X-Transaction-Reference`, including server byte validation and authorization.
No new plan-discovery, transfer-instruction, invoice-list or subscription-list
endpoint is assumed to exist. Checkout, receipt sending, registration decisions
and financial review buttons remain unavailable. No optimistic paid/approved
state or commercial mutation is implemented.

## Initial increment validation and review (retained evidence)

Commands from `frontend/`, using the existing portable Node installation if needed:

```powershell
$env:Path = 'D:\MoulAI\artifacts\frontend-tooling\node-v24.22.1-win-x64;' + $env:Path
npm.cmd run build
npm.cmd run test:guards
npm.cmd test -- tests/unit/office.test.ts tests/unit/officeRoutes.test.tsx --maxWorkers=1 --no-file-parallelism
node node_modules/@playwright/test/cli.js test --config playwright.office.config.ts
npm.cmd run dev:review
```

Open `http://127.0.0.1:5173/access` while the last command runs. Select Owner,
then an explicit company/restaurant and Reports or Billing. The Admin review
profile opens the separate platform area. Only the local review permits these
synthetic sessions; the normal build remains disconnected.

Observed results:

- **80 unit/component tests passed**, zero failed/skipped: 38 new office cases
  and 42 existing route/form/intelligence/appearance regressions. The final run
  used one worker without file parallelism. An earlier concurrent regression run
  hit eight timing/query timeouts while Chromium was running; all the selected
  assertions subsequently passed unchanged in the sequential run.
- **13 Chromium scenarios passed**, zero failed/skipped/flaky: twelve
  FR/EN/AR × Light/Dark × desktop/mobile journeys plus the disconnected-build
  refusal. Each journey covers reports, billing, receipt preview and three
  platform sections, with zero automated axe violations or horizontal overflow
  at the captured states. Browser traffic was restricted to local GET/HEAD,
  with API/external requests rejected. Automated checks are not full WCAG certification.
- **72 unmodified browser captures**, inspected representative French desktop,
  English dark platform and Arabic dark mobile states. [Local gallery](../artifacts/frontend-office-validation/gallery.html).
- TypeScript, production build, formatting and review guards passed. The build
  check excludes known financial/admin fixtures as well as prior fixtures.
- Playwright's Windows sandbox teardown stalled after all thirteen passes. Only
  its two identified Vite processes (5373/4373) were stopped after identity checks;
  the runner then exited successfully and wrote its final JSON with no errors.
  The existing review server was not stopped. This runner-cleanup limitation is
  distinct from screen-test results.

Evidence stays local and ignored under
[`artifacts/frontend-office-validation/`](../artifacts/frontend-office-validation/).
It includes `unit-results.json`, `playwright-results.json`, `validation.json`,
`gallery.html` and the screenshots.
No ignored artifact is force-added or published.

## AI experiment closure and preserved scope

The [DeepSeek experiment is closed as inconclusive](ai-generation-test-closure.md).
Its existing evidence and launcher remain intact. The Arabic fallback for a
French request is logged as a separate deferred defect; no AI component is
changed or invoked by this delivery. No backend tests, database access,
migration, real identity/channel connection, external provider call, deployment
or Git write operation is performed.

The approved launcher hash still matches, and 425 existing backend, migration
and `.env` files match the retained pre-experiment inventory. Branch and HEAD
remain `feature/keycloak-k10-complete` /
`457154a2598a4d8a1313e0449faa855e8e32f1f1`. Previous local changes are retained;
this delivery is not committed, staged, pushed or deployed.

## Zero-USD continuation — reports, subscriptions and verification simulation

Authorized on 2026-10-26. External spending ceiling: **USD 0**. No provider,
key, credit balance, backend, database or external-service operation is needed.
This extends the existing screens; it does not restart the preceding campaigns.

- Reports now include accessible order-status and product/category distributions
  computed from the same selected restaurant's loaded review workspace. Counts
  are visible as text, with logical-direction CSS bars and existing Teal tokens.
  No revenue or historical series is fabricated from the legacy trend route.
- Billing includes the current synthetic subscription, cycle, amount, dates and
  status, plus a monthly/yearly quote preview for an existing synthetic offer.
  CCP/BaridiMob instructions follow the selected method. Destinations are
  deliberately nonnumeric `SYNTHETIC-*-NOT-PAYABLE` placeholders, never real
  Settings values. Quotes are not invoices, published prices or purchase actions.
- Platform supervision shows the authorized list size and an explicit refresh.
  The payment-review permission admits a **hypothetical verification form** in
  synthetic mode only. Approval preview requires a pending receipt/payment,
  independent-verification test hypothesis, matching reference/amount, DZD and a
  bounded note. Rejection cannot attest funds. Neither outcome changes the source
  payment, receipt, subscription or audit log. Actual decision buttons stay disabled.
- Local forms survive language/theme changes; quote previews are invalidated when
  selection changes. Restaurant navigation discards the former restaurant's draft.
  Owner, Manager, Staff and platform boundaries reuse existing permission names.

Additional implementation: `ReportVisuals.tsx`, `BillingWorkspacePanel.tsx`,
`VerificationSimulation.tsx`, read-only `billingFixtures.ts` and pure
`shared/office/simulation.ts`. Existing office contracts/adapter, translations,
build exclusions and parent screens are extended. No chart dependency is added,
no theme/logo/global layout is redesigned and no new backend API is declared.

Integration still must supply trusted plan discovery, authoritative subscription
reads/pricing, approved transfer instructions and tenant-scoped mappings. Existing
manual checkout/review contracts remain authoritative, including transactional
settlement, deduplication and independent bank verification. Frontend preview
validation does not establish those server guarantees. No complete invoice,
accounting, live bank verification or automatic subscription activation is claimed.

Targeted commands (from `frontend/`, with the existing portable Node on PATH):

```powershell
npm.cmd test -- tests/unit/officeExtension.test.ts tests/unit/officeExtensionRoutes.test.tsx --maxWorkers=1 --no-file-parallelism
node node_modules/@playwright/test/cli.js test --config playwright.office-extension.config.ts
```

New evidence/captures stay under ignored
[`artifacts/frontend-office-extension/`](../artifacts/frontend-office-extension/),
separate from the previous 80-unit/13-browser results and captures. The latter
remain historical evidence of the initial increment; they were not rerun as a
campaign for this continuation.

Continuation results: **33 targeted unit/component tests and 14 Chromium
scenarios passed**, zero failures/skips. The browser selection exercises all
FR/EN/AR × Light/Dark × 1440/390 px combinations, keyboard verification,
both hypothetical decisions, unchanged pending source states, System preference,
draft preservation and the disconnected normal build. Forty-eight original
captures are available in the [local extension gallery](../artifacts/frontend-office-extension/gallery.html).
Automated axe checks found no violations at captured states; this is not a
complete accessibility certification. TypeScript, build, fixture exclusion and
formatting checks pass. No accepted backend or prior frontend campaign was rerun.

Git remains on `feature/keycloak-k10-complete` at
`457154a2598a4d8a1313e0449faa855e8e32f1f1`, with a modified working tree and
no staged files. This continuation's exact changed/new file inventory and hashes
are retained in local `validation.json`; earlier work is preserved. No commit,
push, merge, network synchronization or deployment was performed.
