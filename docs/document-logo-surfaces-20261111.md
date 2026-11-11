# Surface-aware document logos

Date: 11 November 2026. Scope: local presentation correction and targeted checks.
This is not a completion claim for operational integration or a deployment.

## Correction

`frontend/src/shared/ui/BrandLogo.tsx` selects the approved light or dark artwork
for the actual surface. Headers, retained SaaS documents, SaaS payment-request
previews and public customer invoices now use this shared component. Explicitly
white previews can select the light surface independently of the application theme.
The customer invoice logo is also visible on screen, rather than only in print.

A print-only picture source always selects the approved light logo. The shared
print color scheme explicitly becomes light: setting only a white document body
left dark page margins in Chromium when printing from a dark interface. Returning
to screen media restores the selected theme without reloading the page.

The QR background remains white. No financial snapshot, document state,
permission, reference, retained amount or QR was changed. The existing server-side
table/QR printable support has an explicitly white surface and correctly retains
its light logo; it does not inherit the application's dark theme.

## Approved files

No PNG was modified. The dark original and its served copy have SHA-256
`2449087cfb4371606965a320fae2ff22880f802b91c6b84d353b098c9c5bdb0e`.
The approved light file retains SHA-256
`f98556da16c7b63ad33242402c523de220d8782a246c8cd940b9d7fc75582dba`.
The dark PNG is RGBA with transparent exterior pixels, rather than an added white
rectangle. Intrinsic dimensions and proportional CSS sizing are preserved; no
filter, recolouring, cropping or generated replacement was introduced.

## Executed checks

- 63 targeted unit tests passed across shared branding, SaaS documents, invoice
  documents and public dining. This includes four new shared-logo tests.
- Seven navigation-continuity tests passed, including two new owner-offer tests.
- Standard and staging builds passed TypeScript and their fixture-exclusion
  guards: 39 and 58 JavaScript assets respectively.
- Local Chromium produced 24 screen captures: SaaS/public customer invoice,
  FR/EN/AR, light/dark, 1440 px desktop/390 px mobile. Checks covered switching
  both ways without reload, correct image sources, no page overflow and white QR
  backgrounds.
- Twelve A4 PDFs were exported from both themes in all three languages. Every
  actual PDF was reopened with Windows.Data.Pdf: one page each. Rendered pages
  were visually reviewed, and three margin pixels per page were checked for
  opaque white. All twelve exports used the light artwork; screen theme selection
  was restored after printing.

Local evidence is under `artifacts/document-logo-surfaces-20261111/`:
`galerie.html`, `rapport.md`, full-source archive, test/build logs and
`final/browser-summary.json`, `final/paper-pixels.json`, screenshots and PDF renders.
Only `final/` contains the accepted final browser output. Earlier partial attempts
and the superseded dark-margin exports were diagnostic, not successful evidence.

## Evidence limits

The SaaS page uses an actual authorized local Keycloak session and read-only
document requests. The retained document was already invalidated; its complete
source was compared before and after and remained unchanged. No issuance or
invalidation was repeated.

Customer invoice screenshots use an explicitly labelled historical visual replay
of the retained local invoice snapshot. They validate presentation, not a fresh
guest authorization, current QR validity, payment or new end-to-end order flow.
Payment-request previews share the corrected component and their existing unit
regressions; this pass did not create another pending payment for screenshots.
No physical printer, phone scan, browser engine other than Chromium, or remote
staging service was tested. Public minimal verification readers contain no
separate internal logo; their shared header follows the same component.

## Independent local continuation

The owner-offer page now participates in the existing unsaved-navigation guard
when explicit plan, currency, cycle or payment-method choices differ from the
initial selection. Cancelling navigation preserves the choices; explicit discard
allows navigation. Session expiration is never blocked. These two new tests use
local UI fixtures and perform no POST; they are not server authorization evidence.
Pricing calculation, checkout and activation contracts are unchanged.

No migration, database write, external provider, paid activation, deployment or
merge into `main` is part of this correction. GitHub backup is restricted to the
existing preparation branch. Other operational integration work remains open.
