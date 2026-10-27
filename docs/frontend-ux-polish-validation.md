# Frontend — Final targeted UI/UX polish

Date: 2026-10-25. Status: **implemented and locally validated; visual acceptance
pending**. Scope: the five approved presentation adjustments, following the
[01 delivery](frontend-presentation-01-validation.md). No new project phase.

## Delivered adjustments

1. **Balanced Agent-as-a-Service section.** The heading/lead and team description
   share two desktop columns, following RTL order in Arabic. They stack naturally
   on smaller screens. The panel has no fixed height. Smaller local padding,
   consistent row gaps and removal of the desktop welcome illustration's 680 px
   minimum reduce artificial space. At 1440 px the Arabic Light section is
   315 px high versus 386 previously; French Dark is 308 versus 379.
2. **Four identifiable non-interactive capabilities.** Existing Lucide icons grow
   from 24 to 28 px with the same 1.5 px stroke and a 16 px label gap. Plain list
   entries use separators instead of filled rounded boxes, have no hover action,
   button role or tab stop, and retain every approved localized label. Four equal
   desktop columns become two on tablet and one on small mobile.
3. **Local transparency and readability.** The editorial panel alone uses 80%
   opacity in Light; Dark keeps the 84% reading surface. Shared tokens remain
   unchanged. Blur is 2 px; text/icons stay fully opaque. The accent heading is
   at least 20 px and weight 700, satisfying large-text contrast requirements.
   Worst-backdrop Light ratios include 6.11:1 secondary copy, 4.73:1 small muted
   text, and 4.16:1 for the large accent heading/decorative icons. Dense access
   forms and existing reading surfaces retain their approved opacity.
4. **Compact business headers through the existing Brand.** Access keeps its
   560 px maximum and unchanged prominent slogan sizing. Shell uses Brand's
   compact presentation, capped at 360 px with a readable 14–16 px Latin /
   16–18 px Arabic signature. Measured desktop access headers remain
   235.7–238.7 px; enterprise/platform headers are 163–166 px, saving about
   73 px. Centering is relative to each header's content area, with right-hand
   language, appearance and account controls preserved. No duplicate header.
5. **Shorter mobile access path.** The unnecessary 200 px mobile gap above the
   entry card is removed, without rearranging the functioning form. At both
   360 and 390 px, the disabled Keycloak button and complete integration-status
   message fit in the first 844 px viewport in all three languages and both
   themes. Review-profile explanations remain explicit; synthetic review may
   require scrolling. The full 360 px French Light page drops from 2392 to
   2188 px. The real login stays disabled until Business Integration.

All current approved `01` PNGs, historical DAS and archived logos, Gateway
images, signatures, translations, fonts, palette, theme store, adapters and
permission rules remain unchanged. Existing DAS web adaptations still apply.

## Targeted results

- **96 unit tests passed**, zero failures/skips, in six relevant files. This
  includes four new local-surface contrast cases and existing literal copy,
  assets, themes, draft/context and access-boundary checks.
- **26 browser tests passed**, zero failures/skips/flaky outcomes, in one run.
  FR/EN/AR × Light/Dark cover access, enterprise and platform at 1440, 360 and
  390 px. Arabic also covers 834 and 320 px; live System/locale changes,
  disconnected normal build and two existing keyboard/draft cases pass.
- **71 axe scans**, zero reported violations, and **82 real screenshots**.
  Checks include visible mobile access/status, compact/full variants, native
  PNG ratios/hashes, 28 px icons, reading order, non-interactive list semantics,
  focus, no control overlap or horizontal overflow, and readable text/fonts.
- Strict TypeScript, normal build, known-fixture exclusion, targeted formatting
  and whitespace checks pass. Browser color-variable and build timing notices
  do not indicate application failures. No backend campaigns were run.

The screenshots were visually inspected. These checks support scoped review;
they are not a full WCAG or production-security certification. Final visual
acceptance and real business integration remain outstanding by design.

## Files changed in this intervention

| File                                             | Change                                                                                                |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `frontend/src/shared/ui/primitives.tsx`          | Explicit compact/prominent presentation metadata; same Brand component and unchanged assets.          |
| `frontend/src/shared/ui/ui.module.css`           | Compact business artwork/signature; access prominence retained.                                       |
| `frontend/src/app/Shell.tsx`                     | Use the existing compact Brand variant.                                                               |
| `frontend/src/features/access/AccessPage.tsx`    | Group editorial heading/lead and use 28 px icons.                                                     |
| `frontend/src/features/access/access.module.css` | Balanced grid, local opacity, non-interactive capabilities and shorter access spacing.                |
| `frontend/tests/e2e/brand-signature.spec.ts`     | Compact/full measurements, 390 px cases, icon/opacity/reading-order and first-viewport access checks. |
| `frontend/tests/unit/brand-surfaces.test.ts`     | Local Light contrast verification.                                                                    |
| `frontend/README.md`, `docs/README.md`           | Current presentation and review instructions.                                                         |
| `docs/frontend-presentation-01-validation.md`    | Supersession note preserving historical results.                                                      |

Added: `frontend/playwright.ux.config.ts` and this report. The new config reuses
the existing focused suite and records evidence separately. Earlier uncommitted
work is preserved; this inventory is relative to the start of this intervention.

From `frontend/`:

```powershell
npm.cmd run build
node node_modules/@playwright/test/cli.js test --config playwright.ux.config.ts
```

## Local review, evidence and Git

- [Gallery: six language/theme combinations, before/after and mobile](../artifacts/frontend-ux-final-validation/index.html).
- Header comparison: [access](../artifacts/frontend-ux-final-validation/1440-fr-light-access-header.png),
  [enterprise](../artifacts/frontend-ux-final-validation/1440-fr-light-enterprise-header.png),
  [platform](../artifacts/frontend-ux-final-validation/1440-fr-light-platform-header.png).
- Editorial section: [FR Light](../artifacts/frontend-ux-final-validation/1440-fr-light-service.png),
  [EN Dark](../artifacts/frontend-ux-final-validation/1440-en-dark-service.png),
  [AR Light](../artifacts/frontend-ux-final-validation/1440-ar-light-service.png).
- Mobile: [390 px FR](../artifacts/frontend-ux-final-validation/390-fr-light-access.png)
  and [360 px AR](../artifacts/frontend-ux-final-validation/360-ar-dark-access.png).
- [Unit results](../artifacts/frontend-ux-final-validation/unit-results.json),
  [browser results](../artifacts/frontend-ux-final-validation/playwright-results.json),
  [measurements](../artifacts/frontend-ux-final-validation/header-measurements.json)
  and [scope/integrity record](../artifacts/frontend-ux-final-validation/validation.json).
- [Complete final Git status](../artifacts/frontend-ux-final-validation/git-status-final.txt).

Branch: `feature/keycloak-k10-complete`. HEAD remains
`457154a2598a4d8a1313e0449faa855e8e32f1f1`. The working tree contains prior and
current frontend/documentation changes; nothing is staged. No commit, branch
change, fetch, pull, push, merge or deployment. No remote synchronization check
was performed. Local evidence stays ignored and is not forced into Git.

No backend, environment, migration, business permission, dependency or official
asset change. No Keycloak/API/Neon/Render/Redis/Telegram operation. K9/K10 and
A2+A5 remain closed. Further modules wait for this visual acceptance.
Roadmap: Frontend → Business Integration → K11 Production Security → Pilot.
