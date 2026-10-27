# Frontend — Approved logos, multilingual signature and product presentation

Date: 2026-10-24. Status: **implemented and locally validated; final visual
acceptance pending**. Branch: `feature/keycloak-k10-complete`.

The subsequent [01 presentation adjustment](frontend-presentation-01-validation.md)
supersedes this delivery's active logo filenames, framed signature and linear
capability paragraph. The results and evidence below retain their original scope.

## Approved identity and delivered behavior

The user explicitly approved the two new transparent display variants after
reviewing their geometric differences. This supersedes the logo reservation in
[final polish](frontend-final-polish.md), without changing the historical DAS
reference or asserting vector equivalence with it.

| Active file in `frontend/public/brand/` | Original dimensions | SHA-256                                                            |
| --------------------------------------- | ------------------- | ------------------------------------------------------------------ |
| `moulai-logo-light.png`                 | 2168 × 725          | `2d15af201b074dfd5dafe31bb341da785b0852f957452c6db0ac005449b7db80` |
| `moulai-logo-dark.png`                  | 2172 × 724          | `99f0bd0ee1e7818ffb789e0ffbbc9d208812fa5675e1b66acc26ca03c504909f` |

Both files are byte-identical to the supplied originals in `Desktop/MoulAI-Plateform`.
Their RGBA transparency, geometry, spacing and colors are unchanged. The existing
effective-theme store selects Light/Dark and follows System changes. Brand image
attributes use each PNG's actual dimensions; CSS scales proportionally without
filtering, recoloring, cropping, deformation or mirroring.

The historical `public/brand/moulai-logo.png` is unchanged. The previous two
presentation PNGs and their original manifest are retained byte-for-byte in
[`brand-sources/archive/presentation-before-20261024/`](../frontend/brand-sources/archive/presentation-before-20261024/README.md).
They are outside the public build and are not used by active UI components.

The shared prominent Brand uses `clamp(320px, 42vw, 560px)`, capped by its available
container. The canvas and signature are centered independently of the right-hand
controls, including in Arabic. At 320 px viewport width the access image fits
within 296 px. Transparent padding remains part of the original PNG; 560 px is
the file canvas width, not the visible drawing width. Approximate visible widths
at that cap are 500 px in Light and 515 px in Dark.

The signature is visible immediately below the logo in access, enterprise and
platform headers. It uses the existing i18next catalogs and Sora/Tajawal fonts:

| Locale | Exact approved signature                 |
| ------ | ---------------------------------------- |
| FR     | Pour chaque activité, son propre MoulAI. |
| EN     | For every business, its own MoulAI.      |
| AR     | لكل نشاط «مولاي» الخاص به                |

The previous footer signature is removed. A compact shared reading surface keeps
the new signature legible over the translucent header. The desktop header measures
approximately **225.2–227.3 CSS px** in the tested access/enterprise/platform views,
excluding the local-review banner. This includes the newly visible signature;
the preceding comparison's approximately 204 px excluded that signature.

## Agent-as-a-Service editorial section

One accessible section below the main welcome area on `/access` presents the
user's exact FR/EN/AR headline, team description and capability text. Only the
selected locale is shown. `Agent-as-a-Service` remains unchanged and reads LTR
within the Arabic RTL section. Content is native text, not a new banner image.

A localized note explicitly identifies product vision and planned capabilities,
and states that business integrations are not all connected. Real sign-in remains
disabled; the synthetic-review warning and isolated review entry remain intact.
No capability, permission, operational action, endpoint or real integration is added.

The section reuses existing typography, spacing, colors, 84% reading surfaces,
borders, radius and shadow tokens. Gateway imagery and other approved translucent
panels remain intact. The existing [DAS-01–DAS-11 web adaptation](frontend-identity-and-das.md)
is preserved: meaningful content, semantic hierarchy, script-specific typography,
readability, truthful capability status and a scoped user-approved asset change.
This is not an amendment or new certification of the original DAS documents.

## Exact file inventory for this delivery

Modified files, relative to the state at the start of this intervention:

| Files                                                                    | Change                                                                                             |
| ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| `frontend/public/brand/moulai-logo-light.png`, `moulai-logo-dark.png`    | Approved byte-identical PNG replacement.                                                           |
| `frontend/brand-sources/logo-manifest.json`                              | Current dimensions, hashes, approval and archive reference.                                        |
| `frontend/src/shared/ui/primitives.tsx`, `ui.module.css`                 | Actual theme-specific intrinsic dimensions, visible localized signature and responsive 560 px cap. |
| `frontend/src/features/access/AccessPage.tsx`, `access.module.css`       | Accessible editorial section and responsive RTL styling; remove duplicate footer signature.        |
| `frontend/src/shared/i18n/fr.ts`, `en.ts`, `ar.ts`                       | Exact signatures, approved product copy and localized integration qualification.                   |
| `frontend/tests/unit/gateway.test.tsx`                                   | Approved Light intrinsic dimensions.                                                               |
| `frontend/tests/e2e/brand-platform.spec.ts`, `gateway.spec.ts`           | Use each approved PNG's actual aspect ratio.                                                       |
| `frontend/tests/e2e/polish-checks.ts`                                    | Header size bound accounts for the newly visible signature.                                        |
| `frontend/README.md`                                                     | Correct current asset usage, archived references and review instructions.                          |
| `docs/README.md`                                                         | Delivery link.                                                                                     |
| `docs/frontend-final-polish.md`, `frontend-platform-brand-validation.md` | Short supersession notes; historical results retained.                                             |

Added files:

- `frontend/brand-sources/archive/presentation-before-20261024/moulai-logo-light.png`.
- `frontend/brand-sources/archive/presentation-before-20261024/moulai-logo-dark.png`.
- `frontend/brand-sources/archive/presentation-before-20261024/logo-manifest.json`.
- `frontend/brand-sources/archive/presentation-before-20261024/README.md`.
- `frontend/tests/unit/brand-message.test.tsx`.
- `frontend/tests/e2e/brand-signature.spec.ts`.
- `frontend/playwright.signature.config.ts`.
- This report.

Earlier uncommitted frontend work remains present. This inventory describes only
this delivery's differences, not the entire working tree versus HEAD.

## Observed targeted verification

- **90 unit tests passed**, zero failures/skips, across six selected files:
  approved literal copy, six locale/theme combinations, in-place language changes,
  archived pixel integrity, active PNG transparency/hashes, Gateway, contrast
  bounds, theme behavior, draft preservation and existing access/scope regressions.
- **20 browser tests passed**, zero failures/skips/flaky results: 18 new brand
  scenarios and two existing keyboard/draft/System regressions at 1440 and 320 px.
- **53 axe scans**, zero reported violations. This supports accessibility review;
  it is not a full WCAG certification.
- **55 real screenshots**, including six standalone editorial-section captures,
  access Light/Dark, Arabic RTL, enterprise, platform, mobile and tablet views.
- Strict TypeScript, normal build, known-fixture exclusion, targeted formatting
  and whitespace checks pass. No dependency or lockfile change.

The browser matrix covers all six locale/theme combinations on access, enterprise
and platform at 1440 and 360 px. Additional access checks cover Arabic at 834 and
320 px. Live language/System switching preserves the selected review profile and
form node. Existing real-browser keyboard tests preserve invalid product drafts,
validation and company/restaurant context through FR/EN/AR and both effective
System themes. The normal build retains disabled sign-in and no synthetic entry.

The browser checks verify exact served-logo SHA-256, decoded dimensions, aspect
ratio, signature placement/direction/font, canvas centering, 44 px controls and
absence of overlap, horizontal overflow, CSS filters or image transforms.
All page requests are restricted to owned loopback servers. Those servers stop
after each targeted run. Node reports an environment color-variable warning;
no application failure was observed.

Reproduce only the scoped browser checks from `frontend/` after a normal build:

```powershell
npm.cmd run build
node node_modules/@playwright/test/cli.js test --config playwright.signature.config.ts
```

This execution recorded the 18 new scenarios and two existing draft scenarios
in separate consecutive runs. Both reports are retained; successful cases were
not rerun to produce a combined count. No backend campaigns were executed.

## Local evidence and review boundary

- [Screenshot gallery](../artifacts/frontend-brand-final-validation/index.html).
- [Access Light](../artifacts/frontend-brand-final-validation/1440-fr-light-access.png)
  and [access Dark](../artifacts/frontend-brand-final-validation/1440-fr-dark-access.png).
- Editorial section: [FR](../artifacts/frontend-brand-final-validation/1440-fr-light-service.png),
  [EN](../artifacts/frontend-brand-final-validation/1440-en-light-service.png),
  [AR RTL](../artifacts/frontend-brand-final-validation/1440-ar-dark-service.png).
- [Enterprise](../artifacts/frontend-brand-final-validation/1440-fr-light-enterprise.png)
  and [platform](../artifacts/frontend-brand-final-validation/1440-fr-dark-platform.png).
- [Small mobile RTL](../artifacts/frontend-brand-final-validation/320-ar-dark-access.png).
- [Unit results](../artifacts/frontend-brand-final-validation/unit-results.json),
  [brand browser results](../artifacts/frontend-brand-final-validation/brand-browser-results.json),
  [draft browser results](../artifacts/frontend-brand-final-validation/draft-browser-results.json),
  [header measurements](../artifacts/frontend-brand-final-validation/header-measurements.json)
  and [scope/integrity verification](../artifacts/frontend-brand-final-validation/validation.json).

Evidence stays local under ignored `artifacts/`; these links may be absent on
GitHub. No artifacts were forced into Git. Source code, test configuration and
the report are reviewable without publishing local evidence.

No backend, business permission, migration, environment, dependency or external
service configuration changes. No real API/Keycloak connection, Neon/Render/Redis/
Telegram operation, commit, push, merge or deployment. K9/K10 and A2+A5 remain
closed. Final visual acceptance remains with the user before continuing
Agents IA → Channels → Conversations → Reports → Billing → Administration.
The roadmap remains Frontend → Business Integration → K11 Production Security → Pilot.
