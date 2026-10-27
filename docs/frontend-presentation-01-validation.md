# Frontend — 01 logos, unframed slogan and capability icons

Date: 2026-10-25. Scope: frontend presentation only on
`feature/keycloak-k10-complete`; visual acceptance remains with the user.
This supersedes the active-asset and presentation choices in the
[previous signature delivery](frontend-brand-signature-validation.md), whose
original evidence is retained.

The later [targeted UX polish](frontend-ux-polish-validation.md) supersedes this
report's shared large business header and boxed capability styling. Approved
assets, wording and historical test results remain unchanged.

## Delivered presentation

- Shared Brand now loads `moulai-logo-light01.png` in Light and
  `moulai-logo-dark01.png` in Dark. System follows the effective theme.
  Both supplied transparent PNGs are **2172 × 724 px**, copied without changing
  any pixels, colors, spacing or proportions. No filter or transform is applied.
- The 560 px maximum, proportional responsive sizing and canvas centering remain.
  The exact previous PNGs and their manifest are preserved in
  `frontend/brand-sources/archive/presentation-before-20261025/`, alongside the
  earlier archive. They are absent from active public assets and the normal build.
  The historical DAS reference `public/brand/moulai-logo.png` is unchanged.
- The unchanged FR/EN/AR slogan appears directly on the existing header background:
  **no capsule, background, border, radius, padding or shadow of its own**.
  It uses primary text, weight 700, Sora at 16–20 px and Tajawal at 18–22 px,
  centered below the logo. Arabic retains RTL and the right-hand controls remain.
- The capability paragraph becomes four semantic list items using the existing
  Lucide family: MessagesSquare, CalendarDays, ClipboardList and Clock3.
  Each has a visible localized label; decorative icons are hidden from assistive
  technology. Layout adapts from four columns to two and then one, with RTL order.
- Existing shared tokens, translucent surfaces, Gateway assets, introductory copy,
  disabled real sign-in and synthetic-review warning remain intact. The localized
  product-vision qualification still explains that integrations are not all live.
  The presentation creates no operational capability or new permission.

| Asset                     | SHA-256                                                            |
| ------------------------- | ------------------------------------------------------------------ |
| `moulai-logo-light01.png` | `f98556da16c7b63ad33242402c523de220d8782a246c8cd940b9d7fc75582dba` |
| `moulai-logo-dark01.png`  | `82d125604fbfe68162ed5ad85bb336df3c146554d43080d38afbedd04a0040f2` |

## Changes and reproducibility

Modified files:

- `frontend/src/shared/ui/primitives.tsx`, `ui.module.css`.
- `frontend/src/features/access/AccessPage.tsx`, `access.module.css`.
- `frontend/src/shared/i18n/fr.ts`, `en.ts`, `ar.ts`.
- `frontend/brand-sources/logo-manifest.json`.
- `frontend/tests/unit/brand-message.test.tsx`, `brand-surfaces.test.ts`,
  `gateway.test.tsx`.
- `frontend/tests/e2e/brand-signature.spec.ts`, `brand-platform.spec.ts`.
- `frontend/tests/e2e/polish.spec.ts`: synchronize keyboard checks with invalid-field focus.
- `frontend/playwright.signature.config.ts`.
- `frontend/README.md`, `docs/README.md`,
  `docs/frontend-brand-signature-validation.md`.

Added files are the two public `01` PNGs, this report, and the archive directory's
two prior PNGs, original manifest and README. The previous two public presentation
files were moved into that archive without changing their bytes or destroying them.
Earlier uncommitted work is preserved; this inventory is relative to this task.

From `frontend/`, use `npm.cmd run dev:review` for the loopback-only local review.
The normal build remains disconnected and excludes synthetic fixtures.

```powershell
npm.cmd run build
node node_modules/@playwright/test/cli.js test --config playwright.signature.config.ts
```

## Targeted verification and review evidence

**92 unit tests and 20 browser scenarios passed**, with no remaining failed or
unexecuted required scenario. **53 axe scans** reported zero violations, and
**55 screenshots** were retained. Strict TypeScript, the normal build, known-fixture
exclusion, targeted formatting and whitespace checks pass. The tested desktop
headers measure approximately **235.7–238.7 CSS px**, excluding the review banner.

The initial run passed all 18 presentation scenarios, then an existing keyboard
test raced React Hook Form's scheduled error focus after invalid submission.
Its global Enter keypress did not open the language selector; the final small-mobile
case was not reached because fail-fast was enabled. The failure report, screenshot
and trace remain local. The test now waits for the invalid price field and its focus,
then sends Enter through the language-control locator. Both keyboard/draft scenarios
passed on the targeted recheck. No application form or business behavior was changed,
and the 18 successful presentation scenarios were not unnecessarily repeated.

Observed results and exact scope/integrity checks are retained in
[validation.json](../artifacts/frontend-presentation-01-validation/validation.json).
The delivery checks include strict TypeScript, the normal build and known-fixture
exclusion, exact PNG hashes/transparency, two-generation archive preservation,
localized icon labels, and worst-case header/slogan contrast of at least 4.5:1
over the existing scene wash in both themes.

Browser coverage includes FR/EN/AR × Light/Dark at 1440 and 360 px on access,
enterprise and platform; additional Arabic access checks at 834 and 320 px;
live language/System changes; the normal disconnected build; and the existing
1440/320 px keyboard, validation, draft and selected-context regressions.
It checks decoded PNGs, correct origin asset hashes, native ratios, centered
unframed bold slogans, fonts, four labeled decorative icons, bounds, controls,
and WCAG axe scans. Automated scans support review, not full WCAG certification.

- [Local screenshot gallery](../artifacts/frontend-presentation-01-validation/index.html).
- Access: [FR Light](../artifacts/frontend-presentation-01-validation/1440-fr-light-access.png),
  [FR Dark](../artifacts/frontend-presentation-01-validation/1440-fr-dark-access.png),
  [AR RTL](../artifacts/frontend-presentation-01-validation/1440-ar-dark-access.png).
- Capability section: [FR](../artifacts/frontend-presentation-01-validation/1440-fr-light-service.png),
  [EN](../artifacts/frontend-presentation-01-validation/1440-en-dark-service.png),
  [AR](../artifacts/frontend-presentation-01-validation/1440-ar-light-service.png).
- [Mobile RTL](../artifacts/frontend-presentation-01-validation/320-ar-dark-access.png),
  [enterprise](../artifacts/frontend-presentation-01-validation/1440-fr-light-enterprise.png)
  and [platform](../artifacts/frontend-presentation-01-validation/1440-fr-dark-platform.png).
- [Unit results](../artifacts/frontend-presentation-01-validation/unit-results.json)
  and [final keyboard recheck](../artifacts/frontend-presentation-01-validation/playwright-results.json).
- [Initial browser run, including the 18 passes and the preserved failure](../artifacts/frontend-presentation-01-validation/initial-browser-results.json).

All evidence stays under ignored local `artifacts/`; links may be absent on GitHub.
No backend tests, backend/permission/migration/environment/dependency changes,
external-service operations, real API integration, commit, push, merge or
deployment. The existing DAS adaptations remain in force; original DAS geometry
is not redefined. The roadmap remains Frontend → Business Integration →
K11 Production Security → Pilot.
