# Frontend — Shared Gateway, transparent logos and readable panels

Date: 2026-10-24. Status: **implemented and locally tested; visual review pending**.

The later [approved logo and signature delivery](frontend-brand-signature-validation.md)
supersedes this report's active-logo dimensions and sizing. Original verification
results below retain their historical scope; the DAS reference remains unchanged.

This delivery applies the requested visual adjustments to the existing frontend.
It supersedes the access-only background and opaque-panel presentation described
in the [previous Gateway report](frontend-gateway-validation.md). That report and
its local evidence remain historical records. No business workflow is added.

## Official assets and shared presentation

The supplied `moulai-logo-light.png` and `moulai-logo-dark.png` are copied
byte-for-byte into `frontend/public/brand/`. Both are transparent RGBA PNGs,
2172 × 724 pixels. Their original dimensions, colors and proportions are retained;
there is no tracing, recoloring, filtering, cropping or image regeneration.
The [logo manifest](../frontend/brand-sources/logo-manifest.json) records SHA-256
values, also checked against the supplied Desktop originals. The earlier
`moulai-logo.png` is retained unchanged.

The shared Brand component selects the light or dark official asset from the
existing effective theme. Its prominent width scales up to 520 CSS pixels and
contracts to its available mobile width. Access, enterprise and platform headers
center the logo; enterprise/platform branding moves from the sidebar to the
header. Language and appearance controls remain accessible in stacked layouts.

One BrandCanvas inside the existing providers supplies the fixed decorative
Gateway behind every route, including loading, denied and error states. It uses
the previously approved responsive Light/Dark WebPs, unchanged. There is no
second theme system, per-page background copy or mirrored Arabic artwork.
Future screens inside these providers inherit the same background. Theme changes
replace only the decorative image, without remounting page children or forms.

The semantic tokens centralize the visual treatment:

| Surface                                      | Treatment                                               |
| -------------------------------------------- | ------------------------------------------------------- |
| Principal content, business panels and cards | 90% theme surface, transmitting 10% of the scene below. |
| Header and footer                            | 94% page surface.                                       |
| Navigation                                   | 96% Deep Navy surface.                                  |
| Scene wash                                   | 16% page surface above the decorative image.            |
| Inputs, menus, dialogs and mobile drawer     | Existing opaque surfaces retained for readability.      |

The background has no pointer interaction or accessible name. The existing palette
remains the fallback if the artwork cannot load. Translation resources,
permissions, context selection and typed adapters are unchanged.

## Files added or updated in this adjustment

| Files                                                                                             | Responsibility                                                                            |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `frontend/src/shared/ui/BrandCanvas.tsx`, `brand-canvas.module.css`                               | New shared decorative background.                                                         |
| `frontend/public/brand/moulai-logo-{light,dark}.png`, `frontend/brand-sources/logo-manifest.json` | New exact official assets and integrity record.                                           |
| `frontend/src/app/Providers.tsx`                                                                  | Shared canvas placement.                                                                  |
| `frontend/src/app/Shell.tsx`, `shell.module.css`                                                  | Centered enterprise/platform header and responsive panels.                                |
| `frontend/src/features/access/AccessPage.tsx`, `access.module.css`                                | Centered access branding; remove duplicate access-only background.                        |
| `frontend/src/shared/ui/primitives.tsx`, `ui.module.css`                                          | Theme-specific Brand and readable state panels.                                           |
| `frontend/src/shared/styles/tokens.css`                                                           | Shared translucent surface tokens.                                                        |
| `frontend/src/features/{workspace,management}/*.module.css`                                       | Consistent company, restaurant, catalogue and order surfaces.                             |
| `frontend/tests/unit/brand-surfaces.test.ts`                                                      | New contrast and PNG integrity checks.                                                    |
| `frontend/tests/e2e/brand-platform.spec.ts`, `frontend/playwright.brand.config.ts`                | New responsive cross-platform visual/accessibility checks.                                |
| `frontend/tests/{unit/gateway.test.tsx,e2e/gateway.spec.ts}`                                      | Update earlier Gateway expectations for the newly supplied logos and global presentation. |
| This report                                                                                       | Current delivery, observations and review links.                                          |

Earlier uncommitted Gateway sources, original backgrounds, encoder script and
configuration are retained. They are not newly attributed to this adjustment.

## Observed local validation

- **150 unit tests passed**, zero failures or skips, across eight files.
- **44 Chromium browser tests passed**, zero failures, skips or flaky results.
- **115 axe scans** completed with no reported violations across the exercised
  access and platform views; this is not a complete accessibility certification.
- **114 screenshots** retained locally. Access covers 360, 390, 834, 1440 and
  1920 CSS-pixel widths in FR/EN/AR and Light/Dark. Enterprise/platform checks cover
  360 and 1440 widths, all six language/theme combinations, and seven views:
  company selection, restaurant selection, profile, catalogue, orders, order
  detail and platform administration.
- System preference changes, explicit theme persistence, keyboard focus,
  transparent logo backing, original logo ratio and centered positioning pass.
  The normal build stays disconnected and excludes review fixtures.
- Twelve contrast tests check six foreground/control tokens in both themes over
  eight RGB backdrop extremes. Both official PNG integrity tests pass.
- Strict TypeScript, production build, fixture-exclusion checks, review guards,
  formatting and whitespace checks pass. No dependency or lockfile change.

Manual inspection covered desktop access, workspace, catalogue and platform,
plus Arabic mobile access and workspace. Browser checks use emulated Chromium
viewports; physical devices and other browser engines were not tested here.

Reproduce from `frontend/` with the existing Node 24 tooling and installed
Playwright Chromium:

```powershell
npm test
npm run build
npm run test:guards
npx playwright test --config playwright.brand.config.ts
```

The browser configuration owns loopback-only review and preview servers on ports
5273 and 4273. No real authentication or business API is used. The new evidence
directory is [frontend-platform-brand-validation](../artifacts/frontend-platform-brand-validation/):
`unit-results.json`, `playwright-results.json`, `validation.json` and screenshots.
These ignored artifacts remain local; they must not be force-added to Git.

## Review and scope boundary

Examples: [desktop access, Dark](../artifacts/frontend-platform-brand-validation/access-1440-fr-dark.png),
[desktop catalogue, Light](../artifacts/frontend-platform-brand-validation/1440-fr-light-catalogue.png),
[Arabic mobile access, Light](../artifacts/frontend-platform-brand-validation/access-390-ar-light.png)
and [Arabic mobile workspace, Dark](../artifacts/frontend-platform-brand-validation/360-ar-dark-workspace.png).

The 611 pre-existing tracked non-frontend files and local `.env` retain their
pre-task fingerprints. No backend, migration, authorization, K9/K10, Neon,
Keycloak, Render, Redis or Telegram operation occurred. No Git staging, commit,
push, merge or deployment was performed. The previous uncommitted delivery is
preserved. Agents and Conversations are not implemented in this adjustment.

Roadmap: **Frontend → Business Integration → K11 Production Security → Pilot**.
