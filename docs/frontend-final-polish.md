# Frontend — Final header and surface polish

Date: 2026-10-24. Scope: the existing React frontend on
`feature/keycloak-k10-complete`. Visual acceptance remains with the user;
logo substitution and readability exceptions are explicitly recorded below.

Subsequent decision: the user approved the new web display variants and a visible
localized signature. The [brand integration delivery](frontend-brand-signature-validation.md)
supersedes the logo reservation and hidden-signature presentation below; the
original observations and test results remain historical evidence.

## Delivered behavior

- A larger, horizontally centered logo uses the available space independently
  of the controls. Prominent artwork scales from 340 to 600 CSS pixels, capped
  by its container. Its intrinsic ratio and all source pixels are preserved.
- Smaller header padding and a screen-reader-only secondary tagline reduce
  vertical overhead. On narrow layouts, controls occupy the upper-right row,
  followed by the centered logo and the existing business context.
- The header background is **60% opaque / 40% transparent**. Its children remain
  fully opaque. Deep Navy and Light Mint still follow the existing effective theme.
- Language buttons become one labeled Radix selector: Français — FR,
  English — EN, العربية — AR. It calls the existing i18next store; no new locale
  state or persistence layer is introduced.
- Language, appearance and the existing account/security indicator remain in
  physical left-to-right order at the right edge, including Arabic. Controls
  have matching 44-pixel heights. The existing indicator remains absent from
  access; no security status or account capability is invented.
- Gateway artwork remains global, decorative and unchanged. Main header/content
  blur is reduced from 12 to 4 pixels. The approved Sora/Tajawal fonts, palette,
  translations, typed adapters and isolated review fixtures remain in place.

### Local readability exception

The shared card/panel token is 60% opaque. However, dense reading surfaces,
access forms, editorial copy, state messages, header breadcrumbs and footer
use a separate **84% opaque** semantic surface. Inputs, menus and dialogs stay
opaque. These are local exceptions to the initial transparency target, not
opacity applied to text or entire containers.

The contrast test composites the actual reading token over the existing 16%
scene wash at all eight RGB backdrop extremes. At 60%, several text/control
pairs fail; at 84%, all six tested foreground/control tokens pass in both themes.
For example, the Light accent has a minimum ratio of approximately 4.53:1 and
the Dark strong border approximately 3.34:1 with the reading surface. Nested
60% cards sit over that reading surface. Detailed calculations remain local in
`artifacts/frontend-polish-validation/contrast-policy.json`.

One live System-theme test exposed a transient contrast defect: secondary-button
backgrounds interpolated between themes while their text switched immediately.
The shared button now transitions only its shadow, making text and background
switch together. The initial failure evidence is retained locally.

The 1101-pixel breakpoint check also exposed a logo-box overlap. The Brand root
is now capped to its available track, and both side tracks reserve control space.
The corrected edge case and a 320-pixel narrow layout are explicitly tested.

## Supplied logo review and explicit reservation

The newly supplied files in `Desktop/MoulAI-Plateform` were inspected read-only.
Both are genuinely transparent RGBA PNGs. They are different from the previously
supplied theme variants currently used in the app:

| Latest supplied file    | Dimensions | SHA-256                                                            |
| ----------------------- | ---------- | ------------------------------------------------------------------ |
| `moulai-logo-dark.png`  | 2172 × 724 | `99f0bd0ee1e7818ffb789e0ffbbc9d208812fa5675e1b66acc26ca03c504909f` |
| `moulai-logo-light.png` | 2168 × 725 | `2d15af201b074dfd5dafe31bb341da785b0852f957452c6db0ac005449b7db80` |

Visual comparison with `moulai-logo.png` and the previously supplied theme
variants shows different contours and relative spacing. Visible artwork bounds
also change; the latest Light canvas has a different aspect ratio. These
observations do not establish an approved DAS geometry or an exact A/I spacing
contract. No authoritative vector/measurement grid was supplied to resolve it.

Following the explicit instruction to retain the reference when geometry differs,
**the latest files are not substituted**. The existing official reference and
previously supplied transparent theme variants remain byte-identical. Neither
the old nor the new logo is cropped, stretched, recolored or reconstructed.
Approval of the changed variants is a remaining brand decision, not a technical
test result. Their integrity record is retained locally as `new-logo-review.json`.

The existing [DAS adaptation](frontend-identity-and-das.md) remains the reference
for DAS-01–DAS-11. This delivery preserves that numbering and its stated web/print
distinctions; it does not redefine the rules or claim formal brand certification.

## Files in this adjustment

| Files                                                                                                                       | Change                                                                                                     |
| --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `frontend/src/shared/ui/primitives.tsx`                                                                                     | Accessible language selector; prominent secondary tagline stays available to assistive technology.         |
| `frontend/src/shared/ui/ui.module.css`                                                                                      | Larger logo, compact selector, physical control ordering, readable states and atomic button color changes. |
| `frontend/src/shared/styles/tokens.css`                                                                                     | 60% header/panel and 84% reading surfaces.                                                                 |
| `frontend/src/{app/shell,features/access/access}.module.css`                                                                | Compact responsive headers, right-aligned controls, preserved context direction and lower blur.            |
| `frontend/tests/unit/{setup.ts,appearanceRoutes.test.tsx,routes.test.tsx,managementRoutes.test.tsx,brand-surfaces.test.ts}` | Update selector interactions; jsdom-only pointer/layout shims; contrast bounds.                            |
| `frontend/tests/e2e/{appearance,workspace,management,gateway,brand-platform}.spec.ts`                                       | Update existing language interactions and preserve earlier evidence locations.                             |
| `frontend/tests/e2e/polish-checks.ts`, `polish.spec.ts`                                                                     | New header measurements and real keyboard/draft/System checks.                                             |
| `frontend/playwright.polish.config.ts`                                                                                      | New targeted loopback-only validation configuration and evidence destination.                              |
| This report                                                                                                                 | Results, before/after evidence and brand/readability reservations.                                         |

Previously uncommitted Gateway/BrandCanvas files remain intact except the test
updates listed above. No backend, migration, permission, business data, dependency,
lockfile, local environment file or external service configuration changes.

## Verification and local review

The final browser matrix records actual header dimensions as well as layout,
keyboard, theme, logo and accessibility checks. Backend/K9/K10/A2+A5 campaigns
are not reopened.

Observed final results:

- **150 unit tests passed**, zero failures or skips, using one worker.
- **55 browser tests passed** in the complete final run, zero failures, skips
  or flaky results. The run took approximately 8.3 minutes.
- **187 axe scans**, zero reported violations: 126 enterprise/platform scans,
  30 access scans, one disconnected-build fallback scan and 30 draft/System scans.
- **161 final screenshots**, plus five separately retained before captures.
- Strict TypeScript, normal build, fixture exclusion, review publication guards,
  formatting and whitespace checks pass. No dependency changes.
- Exact served-logo hashes, natural proportions, centered positioning, physical
  control ordering, 44-pixel control heights and absence of horizontal overflow
  pass on the tested views. System preference, explicit preference persistence,
  keyboard language changes and draft/context retention pass.

Access covers FR/EN/AR × Light/Dark at 360, 390, 834, 1440 and 1920 pixels.
Enterprise/platform checks cover the same six combinations at 360, 834 and 1440
pixels over seven views. Additional keyboard/draft/System scenarios cover 320,
360, 834, 1101 and 1440 pixels. These narrower checks do not claim every screen
was exercised at 320 pixels. Broader historical browser campaigns are not counted
as new passes here; their language-control locators were updated and type-checked.

Measured catalogue header after the FR/EN/AR and System cycle, in CSS pixels:

| Viewport width | Header height | Logo canvas width |
| -------------- | ------------- | ----------------- |
| 1440           | 217.00        | 600.00            |
| 1101           | 162.66        | 437.00            |
| 834            | 225.55        | 350.27            |
| 360            | 225.00        | 336.00            |
| 320            | 211.66        | 296.00            |

In matching 1440-pixel Light captures, the access header separator moves upward
by 36 pixels and the catalogue separator by 10 pixels. The earlier access logo
canvas was 518.4 pixels wide; it is now 600 pixels without altering its ratio.

Initial locator/jsdom checks, keyboard focus-timing checks, the real System-color
failure and the breakpoint overlap reports remain local diagnostics. One unit
run overlapped browser execution and timed out; the final isolated one-worker
run passed all 150 tests. Interrupted and superseded runs are not added to the
final success counts. Intermediate trace files are not claimed as retained proof;
the corresponding JSON reports record the observed failures.

Before/after captures are retained separately:

| View                          | Before                                                                               | After                                                                        |
| ----------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Access, Light                 | [Before](../artifacts/frontend-polish-validation/before-access-1440-fr-light.png)    | [After](../artifacts/frontend-polish-validation/access-1440-fr-light.png)    |
| Access, Dark                  | [Before](../artifacts/frontend-polish-validation/before-access-1440-fr-dark.png)     | [After](../artifacts/frontend-polish-validation/access-1440-fr-dark.png)     |
| Catalogue, Light              | [Before](../artifacts/frontend-polish-validation/before-1440-fr-light-catalogue.png) | [After](../artifacts/frontend-polish-validation/1440-fr-light-catalogue.png) |
| Platform, Dark                | [Before](../artifacts/frontend-polish-validation/before-1440-fr-dark-platform.png)   | [After](../artifacts/frontend-polish-validation/1440-fr-dark-platform.png)   |
| Arabic mobile workspace, Dark | [Before](../artifacts/frontend-polish-validation/before-360-ar-dark-workspace.png)   | [After](../artifacts/frontend-polish-validation/360-ar-dark-workspace.png)   |

Reproduction from `frontend/`, using the existing Node 24 and Chromium tooling:

```powershell
npm test -- --maxWorkers=1
npm run build
npm run test:guards
npx playwright test --config playwright.polish.config.ts
```

The browser configuration owns only local servers at 127.0.0.1:5273 and
127.0.0.1:4273. It uses no real login or business API. Earlier artifacts remain
unchanged. New JSON results, source hashes, measurements and before/after PNGs
are under ignored `artifacts/frontend-polish-validation/`; none should be
force-added to Git. Browser checks are Chromium viewport emulations, not a claim
about physical devices, other engines or complete WCAG certification.

The final scope record identifies **15 existing files updated and four files
added** in this pass. All 613 pre-existing non-frontend files in the starting
snapshot, including the two earlier uncommitted frontend reports, retain their
hashes. Local `.env` and the original/logo/background assets are unchanged.
The frontend source fingerprints are pinned in `tested-source-manifest.json`
and checked again against the files after execution. Final observations are
summarized in local `validation.json`; exact per-view dimensions are in
`header-measurements.json`.

No Git staging, commit, push, merge, deployment, database action or remote-service
change occurred. Agents, Channels and Conversations are not started by this pass.
Roadmap: **Frontend → Business Integration → K11 Production Security → Pilot**.
