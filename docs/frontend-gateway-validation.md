# Frontend — Official Gateway access experience

Date: **2026-10-23**. Status: **implemented and locally verified; awaiting visual
review**. Starting commit: `457154a2598a4d8a1313e0449faa855e8e32f1f1`, branch
`feature/keycloak-k10-complete`. No commit, push or deployment is part of this delivery.

## Artwork and implementation

Only the two supplied Gateway images are used. Byte-identical originals are
retained in `frontend/brand-sources/gateway/`; the Desktop originals are untouched.

| Original                 | Dimensions | SHA-256                                                            |
| ------------------------ | ---------- | ------------------------------------------------------------------ |
| `moulai-fond-dark.png`   | 1672 × 941 | `672001c4347c9056139d05aa3113a45a56d0922579fc96ee0c3733ca59fd40e4` |
| `moulai-fond-Leight.png` | 1672 × 941 | `3ccd82e3c7d3411cdd0ec6fe0ed41d5bdfe99911f6955d4defd43023bd19d8d5` |

The reproduction script attests these hashes before encoding six WebP copies,
at widths 640, 1024 and 1672, with quality 0.92. It resizes the complete frame,
rounding the proportional height to a whole pixel. It generates no new artwork
and applies no crop or filter to the source files. Encoding provenance and all
output hashes are in `frontend/brand-sources/gateway/manifest.json`.

| Theme | Original PNG | 640 px WebP | 1024 px WebP | 1672 px WebP |
| ----- | ------------ | ----------- | ------------ | ------------ |
| Dark  | 1,869,748 B  | 34,182 B    | 71,298 B     | 165,744 B    |
| Light | 1,751,546 B  | 27,686 B    | 56,034 B     | 125,582 B    |

Only the active theme is requested. The existing pre-paint theme store supplies
Light/Dark/System; it was not modified or duplicated. Responsive image selection
uses `srcset`. Desktop/tablet preserve the complete composition with `contain`;
mobile uses a left-anchored `cover` frame. Neither image is mirrored in Arabic.
Background layers are decorative, noninteractive and excluded from accessibility
semantics. Fixed geometry avoids layout shifts caused by image dimensions.

The access header opts into a larger Brand presentation. Its backing hugs the
artwork more closely, while retaining the readable original colors. The official
logo remains byte-identical, with SHA-256
`548d877ec2d08e286aec12bc38f1969b9e8653cc18ddeaf9ff724e7cb5bb067a`.
Workspace branding retains its prior size. No business page receives the Gateway.

Forms and explanatory content use opaque existing theme surfaces. The access
flow, truthful disconnected state, review warning, selectors and profile form
remain available. Mobile prioritizes access controls before the supporting story.

## DAS and integration boundaries

The accepted [DAS adaptation and original references](frontend-identity-and-das.md)
remain authoritative. This delivery preserves all eleven rules within that web
adaptation: purposeful access-only artwork and hierarchy (01/03/06/07), existing
spacing and Sora/Tajawal typography (02/04), approved semantic colors (05), supplied
artwork and unchanged logo (08), existing access journey (09), optimized loading
and accessibility checks (10), and hash-attested controlled changes (11).
No original DAS document or brand symbol was changed.

No backend, authorization, dependency, migration, environment file or theme-store
change was made. No Keycloak/API integration or external service is involved.
K9/K10 and A2 + A5 campaigns were not repeated. Agents, channels and conversations
remain outside this delivery.

## Observed targeted validation

| Check                            | Result                                                                                                                        |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Frontend unit/component tests    | **136 passed**, zero failures/skips: 128 existing cases plus 8 Gateway cases.                                                 |
| Chromium browser tests           | **32 passed**, zero failures/skips, final runner exit code 0.                                                                 |
| Responsive/language/theme matrix | 30 states: 1440, 1920, 834, 390 and 360 px × FR/EN/AR × Light/Dark.                                                           |
| Accessibility automation         | **31 axe scans**, zero violations; 30 matrix states plus failed-image fallback.                                               |
| System and persistence           | Live OS changes, explicit overrides, reload persistence, language and selected review profile preserved.                      |
| Images and logo                  | Served WebP hashes verified; one active image request per cold matrix page; no filter/mirror; intrinsic logo ratio preserved. |
| Keyboard and bounds              | Visible keyboard focus and no horizontal overflow in every matrix state.                                                      |
| Normal build                     | Disabled real sign-in, no review control; effective-theme artwork and readable failed-image fallback.                         |
| Strict types/build               | Passed; normal build contains no known synthetic fixture data.                                                                |
| Review guards                    | Publication review build and non-loopback review binding refused as expected.                                                 |

An initial unit harness waited for the loading heading rather than the access
heading; its six failures are retained in `initial-unit-results.json`. The wait
was corrected without weakening assertions. Initial browser harness startup/import
issues and Windows sandbox process cleanup were resolved before the final run.
The final browser run used the authorized execution outside the sandbox and
closed its temporary servers. Intermediate smoke runs are not added to totals.

Evidence and 30 actual full-page captures are local and ignored under
`artifacts/frontend-gateway-validation/`. Earlier frontend and backend evidence
was not overwritten. Screenshot names are `access-{width}-{locale}-{theme}.png`.
These are actual synthetic-review screens, visibly labeled, not live accounts.

Reproduce from `frontend/`, using the existing Node 24 tooling:

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run test:guards
npx.cmd playwright test --config playwright.gateway.config.ts
```

The dedicated browser configuration owns loopback ports **5273** and **4273**,
refuses occupied ports and does not replace the existing local review server.
To regenerate only optimized assets from the attested originals:

```powershell
node scripts/prepare-gateway-assets.mjs
```

## Exact source inventory and limits

Four existing files changed:

- `frontend/src/features/access/AccessPage.tsx`
- `frontend/src/features/access/access.module.css`
- `frontend/src/shared/ui/primitives.tsx`
- `frontend/src/shared/ui/ui.module.css`

Fourteen files were added:

- `frontend/brand-sources/gateway/moulai-fond-dark.png`
- `frontend/brand-sources/gateway/moulai-fond-Leight.png`
- `frontend/brand-sources/gateway/manifest.json`
- `frontend/public/brand/gateway/dark-640.webp`
- `frontend/public/brand/gateway/dark-1024.webp`
- `frontend/public/brand/gateway/dark-1672.webp`
- `frontend/public/brand/gateway/light-640.webp`
- `frontend/public/brand/gateway/light-1024.webp`
- `frontend/public/brand/gateway/light-1672.webp`
- `frontend/scripts/prepare-gateway-assets.mjs`
- `frontend/playwright.gateway.config.ts`
- `frontend/tests/unit/gateway.test.tsx`
- `frontend/tests/e2e/gateway.spec.ts`
- This report.

The originals are source assets, not public build inputs. Only the derivatives
are copied into the normal build. WebP is lossy; the original PNGs remain the
reference, and re-encoding requires the reviewed browser/toolchain. The mobile
frame crops surrounding scenery without stretching or mirroring the artwork.
Validation uses Chromium at emulated viewports, not physical devices or
Safari/Firefox. Axe checks do not constitute a full WCAG certification, and no
field Core Web Vitals or slow-network performance guarantee is claimed.

All changes remain local and unstaged on the original branch. No database,
Render, Neon, Redis, Telegram, Keycloak, OIDC flag, commit or push changed.
Roadmap: **Frontend → Business Integration → K11 Production Security → Pilot**.
