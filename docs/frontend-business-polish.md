# Targeted business UI polish — Reports and Manual Billing

Date: 2026-10-27. Status: **implemented and locally verified; pending user review
before synthetic Frontend closure**. Platform Administration and the approved
brand/layout remain unchanged. External spending: **USD 0**.

## Corrections

- Unavailable metric text uses a smaller semantic value style with normal word
  boundaries and no hyphenation. Missing values remain unavailable, never zero.
  Three activity cards and two complementary cards form separate responsive rows;
  no indicator was added. Legitimate zero values remain distinguishable from null.
- Both distributions use each count divided by the sum of all displayed counts.
  Eight equal orders show **12.5% each**; two/one products show **66.7%/33.3%**.
  Exact counts stay visible alongside localized percentages. A zero total gives
  zero-width bars/0%, with no NaN or invented category. Restaurant-authored labels
  keep their original Latin/Arabic content and direction isolation.
- Payment history now uses compact responsive rows with six essential fields:
  reference, amount, method, payment status, date and receipt status. Collapsed
  details expose only contextual information or the existing local receipt form;
  summary fields are not repeated in the expanded content. Filters remain intact.
  Pending payments still show a local receipt preview rather than a real upload.

## Files

Production frontend changes are limited to:

- `frontend/src/features/office/OfficePages.tsx` — report grouping and tenant-only history.
- `frontend/src/features/office/ReportVisuals.tsx` — count/total shares and visible percentages.
- `frontend/src/features/office/office.module.css` — scoped metric/history styles.
- `frontend/src/shared/i18n/office.fr.ts`, `office.en.ts`, `office.ar.ts` — four local labels each.

Added verification files: `tests/unit/businessPolish.test.tsx`,
`tests/e2e/business-polish.spec.ts` and `playwright.business-polish.config.ts`
under `frontend/`. This report and documentation links describe the result.

The exported `PaymentDetails` renderer used by Platform Administration is
byte-for-byte unchanged. Its existing shared CSS rules remain unchanged; the
original CSS reconstructs to its pre-task hash after removing the report-only
grid change and new scoped selectors. All Platform source files remain unchanged.
Existing translations are preserved; new strings do not change platform wording.
No platform screen, global component, header, theme, token, font or brand asset
was altered. Subscription/transfer/simulation services, adapters and validation
logic were not changed.

## Targeted verification

- **12 unit/component tests passed**, zero failures/skips. Coverage includes
  mathematical shares, FR/EN/AR text, zero/empty totals, null versus actual zero,
  three/two metric groups, compact summaries, filters, denied Staff reads,
  unchanged pending payment state and retained form/simulation selections.
- **25 Chromium scenarios passed**, zero failures/skips/flaky outcomes. The
  matrix covers FR/EN/AR × Light/Dark × 1440/320/360/390 px, plus keyboard receipt
  disclosure and System/Arabic draft preservation. Checks cover actual word
  rectangles (no word spans multiple lines), visible values, proportional widths,
  collapsed controls, compact row height and no horizontal overflow. Automated
  axe checks found no violations at captured states, not a full WCAG certification.
- Strict TypeScript, production build/fixture exclusions and formatting passed.
  No backend or previously completed general campaign was rerun.
- A separate pre-change capture pass recorded 24 view combinations. It is
  documentation of the old rendering, not acceptance of its known visual defects.
  **48 before and 50 after captures** remain local, unedited and ignored by Git.

See the [side-by-side before/after gallery](../artifacts/frontend-business-polish/gallery.html)
and local `before-results.json`, `after-results.json`, `unit-results.json`,
`shared-renderer-verification.json` and `validation.json` in the same directory.
No ignored evidence is force-added or published.

Reproduce the corrected checks from `frontend/` with the existing Node on PATH:

```powershell
npm.cmd run build
npm.cmd test -- tests/unit/businessPolish.test.tsx --maxWorkers=1 --no-file-parallelism
node node_modules/@playwright/test/cli.js test --config playwright.business-polish.config.ts
```

The optional `MOULAI_POLISH_STAGE=before` switch labels a capture-only run; it
does not restore old sources. Historical before screenshots were captured before
the correction and must not be overwritten as a reproduction step.

## Limits, Git and stop point

All financial data and CCP/BaridiMob destinations remain explicitly synthetic
and nonpayable. Payment declaration, receipt evidence, independent funds
verification and authorized subscription activation remain distinct. No invoice,
funds, receipt upload or financial decision was created by a local preview.
Real identity/API/banking integration and server transactions remain deferred.

Branch: `feature/keycloak-k10-complete`. HEAD:
`457154a2598a4d8a1313e0449faa855e8e32f1f1`. Existing local work is preserved;
the working tree remains modified, with no staged files and no new commit.
No push, merge, deployment, provider call, database access or external-service
change occurred. Exact task scope and protected-file hashes are retained locally.

Work stops for the requested visual review. Frontend closure and controlled Git
backup remain subsequent user decisions. Roadmap: **Frontend → Business
Integration → K11 Production Security → Pilot**.
