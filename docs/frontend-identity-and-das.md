# Frontend — Internationalization, official themes and DAS adaptation

Date: **2026-10-22**. Scope: the existing local-review frontend, without business
integration, backend changes or deployment. This report records the web adaptation
of the supplied identity references; it does not amend or certify the original DAS.

## Source references and precedence

The operator supplied this directory:

```text
D:\MOULAI — The Architecture of a Living Identity\MOULAI DOCUMENT ARCHITECTURE SYSTEM
```

Both PDF files were read in full: `ChatGPT - MOULAI DOCUMENT ARCHITECTURE
SYSTEM.pdf` (10 pages) and `ChatGPT - MOULAI DOCUMENT ARCHITECTURE SYSTEM-APP.pdf`
(9 pages). All eleven `DAS-01.png` through `DAS-11.png` plates were visually
examined. The plates identify **Version 3.0 / 2026**; their titles and numbering
are also reproduced by the APP document. The earlier PDF is a foundation draft
with different section numbering. It informs the philosophy, but does not
renumber the eleven v3 plates below. The APP filename does not imply an existing
SaaS implementation: its content discusses applying DAS to the identity book.

Fingerprints for all 13 source files are retained locally in
`artifacts/frontend-identity-validation/das-source-manifest.json`. Original
documents and embedded logos were neither modified nor copied into the app.
The PDF SHA-256 values are:

| Source         | SHA-256                                                            |
| -------------- | ------------------------------------------------------------------ |
| Foundation PDF | `0107e13014348259d27b02096a6b3b346d5eb8bc97f6da37be348d5b12bc992e` |
| APP PDF        | `243f089ed28c2c1c284ab46483f16748ca6629e0ab7dcb3f736177ef9c312962` |

## DAS-01 to DAS-11: source, implementation and interpretation

The quoted principles below are original wording from the corresponding plates.
The web application column is an explicitly identified adaptation, not a rewritten
DAS rule or a replacement set of eleven rules.

| Original reference and principle                                                                                       | SaaS adaptation and implementation evidence                                                                                                                                                                                        | Interpretation or remaining decision                                                                                                                                                                                                                |
| ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **DAS-01 — Document Philosophy**: “Every visual element must carry meaning.”                                           | Scope selection, permission-filtered navigation, truthful review banners and explicit confirmation remain central. Unsupported purely decorative access-screen rings were removed.                                                 | A working view replaces a book page; no fabricated chapter, discovery or operational result is added.                                                                                                                                               |
| **DAS-02 — Document Specifications**: “Every specification exists to protect meaning.”                                 | Shared tokens, reusable components, spacing rhythm and responsive CSS replace independent page styling. Card layouts use a 12-column modular grid.                                                                                 | A4 landscape, 297 × 210 mm, print margins and 8 pt baseline are document specifications. Web uses flexible viewports, an 8 px spacing rhythm with 4 px subdivisions and accessible 44 px controls; no fixed paper canvas is imposed.                |
| **DAS-03 — Layout System**: “Information flows before graphics.”                                                       | Existing header, explicit company/restaurant context, title, explanatory lead, content and footer are retained. Grid spans collapse consistently on mobile; directional navigation follows RTL.                                    | Header height and text wrap adapt to viewport/language rather than copying fixed printed positions. There is no unnecessary quote or illustration on every screen.                                                                                  |
| **DAS-04 — Typography System**: “Same scale. Same rhythm. Same hierarchy. Different script. One system.”               | **Sora** serves Latin text and **Tajawal** Arabic, loaded from pinned local Fontsource packages. Shared weight tokens and semantic headings preserve hierarchy. Arabic tracking remains normal.                                    | French extends the Latin Sora use originally described for English. Tajawal has no 600 face: Arabic semibold maps to its actual 700 face; no fabricated font file or faux semibold is supplied. Web sizes/line heights adapt for readable controls. |
| **DAS-05 — Color Philosophy**: “Color supports meaning. Never replaces it.”                                            | Deep Navy, Light Mint and Teal anchor both themes. Status names, error messages, icons, aria-invalid and dashed cancelled-state boundaries supplement color. Text/focus/control contrast is tested.                                | The current user-specified hex values take precedence for this UI. The plate's 60/25/10/5 balance is not mechanically imposed on a Mint-dominant light workspace. See the explicit palette discrepancy below.                                       |
| **DAS-06 — Visual Language**: “Clarity is seen before it is read.”                                                     | Existing restrained layouts, readable labels, spacing, boundaries and consistent responsive cards are reused. State meanings remain understandable without decorative color.                                                       | No new mascot, architectural illustration or ornamental brand shape is invented.                                                                                                                                                                    |
| **DAS-07 — Graphic Language**: “Great graphics do not add noise. They remove confusion.”                               | Company/restaurant context, grouped data cards, filters, confirmation summaries and order history communicate actual relationships. Teal gradients are bounded to actions and supporting card surfaces.                            | No fake chart, KPI, revenue or simulated progress graphic is introduced.                                                                                                                                                                            |
| **DAS-08 — Illustration & Icon System**: “A good illustration explains. A good icon guides. A great system unifies.”   | The existing Lucide outline family is retained with one semantic 1.5 px stroke token. Action icons have text or accessible names; nonessential icons are hidden from assistive technology.                                         | Lucide is the current UI icon implementation, not an assertion that these are official MoulAI artwork. No logo is traced, cropped from a plate, recolored or replaced by an icon.                                                                   |
| **DAS-09 — Journey System**: “Keep users informed with clear status and feedback.”                                     | Access → company → restaurant → feature remains explicit. Loading, denial, empty state, validation, review confirmation, pending/success/refusal and order history provide truthful feedback. Drafts survive locale/theme changes. | The printed Discover → Explore → Engage → Achieve → Grow → Advocate narrative is not forced onto restaurant tasks. No unimplemented onboarding milestones or fulfillment transitions are claimed.                                                   |
| **DAS-10 — Production Standards**: “Accurate”, “Consistent”, “Professional”, “Performant”, “Reusable”, “Maintainable”. | Translation parity, source typing including the bootstrap and browser tests, build checks, local fonts, contrast checks, axe scans, keyboard/mobile review and permission regressions form the delivery checks.                    | Print bleed, DPI, CMYK and PDF/X rules do not become CSS requirements. These frontend checks do not reopen K9/K10 or certify K11 production security. Final visual acceptance remains the user's review.                                            |
| **DAS-11 — Architecture Locked**: “No changes without purpose. No exceptions without approval.”                        | Changes stay within the authorized frontend; shared tokens and catalogs prevent per-screen theme/translation forks. Source references, adaptations and local evidence remain traceable.                                            | This document submits web adaptations for review; it does not fill the source plate's approval fields, declare governance approval, authorize publication or alter the original locked architecture.                                                |

### Explicit palette discrepancy

DAS-10's printed color examples show Navy `#0A2056`, Teal `#0D8A97` and Mint
`#6EE0C2`. The present user instruction explicitly requires Navy **`#0B1324`**,
reference Teal **`#006E5F`** and Light Mint **`#E6F6E3`**. The implementation uses
the latter for the SaaS interface. This is a documented, user-authorized web
palette decision, not a claim that the source plate contains those values.
Original artwork colors remain outside this adaptation and will not be changed.

## One semantic theme system

`frontend/src/shared/styles/tokens.css` remains the single color/style token
boundary. Both themes share the same components and CSS Modules.

| Semantic purpose                        | Light                                           | Dark                              |
| --------------------------------------- | ----------------------------------------------- | --------------------------------- |
| Page                                    | Light Mint `#E6F6E3`                            | Deep Navy `#0B1324`               |
| Card / muted surface                    | `#FFFFFF` / `#D9EEE4`                           | `#122238` / `#1A3144`             |
| Main / secondary text                   | `#0B1324` / `#304D53`                           | `#E6F6E3` / `#B6DAD0`             |
| Link / interactive accent               | Reference Teal `#006E5F`                        | Readable Teal tint `#88DDC3`      |
| Primary action                          | Teal gradient `#006E5F` → `#005448`, white text | Same Teal gradient and white text |
| Link hover (separate from action hover) | `#005448`                                       | `#BCEFD9`                         |
| Action hover                            | Teal gradient `#005448` → `#004238`, white text | Same gradient and white text      |
| Focus                                   | `#006E5F`                                       | `#96E3CD`                         |
| Disabled control                        | `#C5DDD2` / `#344C50`                           | `#233D4C` / `#B7CBC7`             |
| Sidebar                                 | Deep Navy with Mint/Teal text and focus tokens  | Same semantic sidebar boundary    |

Other neutral, review, positive, error, status, border, overlay and shadow tokens
are defined there as Navy/Teal/Mint/monochrome interface shades. These UI shades
are documented adaptations, not additional claimed official logo colors.
Component CSS contains no independent hex palette. Dark surfaces use lighter
Teal for text because reference Teal is retained for action backgrounds, where
white text remains readable. Gradient endpoints are both covered by contrast
checks. Disabled controls remain readable even though WCAG exempts them from
normal text-contrast requirements.

The **Light / Dark / System preference** selector is available on access and
workspace headers and inside editing/confirmation dialogs. The same pre-paint
store in `public/theme-init.js` serves React through `useSyncExternalStore`.
Vite embeds that exact source synchronously in the HTML head before the app
module: no delayed theme request and no React-only theme correction after paint.
The normal build is tested on its first animation frame as well as after reload.

`moulai.theme` stores only an explicit light/dark preference; choosing System
removes it and follows live OS changes. Storage denial falls back to working
in-memory controls. Cross-tab appearance changes are synchronized. The bootstrap
does not read authentication settings, tokens, identities or tenant records.
No authentication, cache or form provider is remounted by preference changes.
Any future restrictive production CSP must account for the inline bootstrap at
the separately authorized production-security stage; no policy was disabled here.

## Internationalization and brand boundary

The existing i18next catalogs now contain **FR, EN and AR** for access, selection,
roles, platform administration, restaurant profiles, catalogue/options, order
statuses, filters, amounts/dates, validations, confirmations and preferences.
English has compile-time key parity and tested interpolation parity. Arabic
keeps its six restaurant plural forms, semantic document RTL and Radix direction.
The document title and accessible preference names are localized too.

`moulai.locale` remains a language preference only. IDs, tenant permissions,
amounts, filters, pending draft values and selected context are unchanged by a
locale switch. Merchant-authored content, including the bilingual synthetic
product names and notes, remains verbatim data; it is not silently machine
translated, overwritten or represented as an unsupported backend localization API.

Sora Variable **5.3.0** and Tajawal **5.3.0** replace the previous font packages;
the lockfile is updated. Five WOFF2 subsets are built locally, with unmodified
OFL notices. No Google Fonts/CDN request is needed. The original Inter/Noto
license files remain as historical records, but their font binaries and packages
are absent from the current build.

At the initial DAS delivery, no separate approved logo asset was available and
`Brand` used the text signature. The user subsequently supplied the official
`MOULAI-ANG 02.png` and the `App Icon-MoulAI.png` presentation sheet on 2026-10-22.
The shared `Brand` now uses `public/brand/moulai-logo.png`, an unchanged copy of
the first source: **1265 × 331 pixels**, preserving its aspect ratio, transparency
and original colors. Its SHA-256 is
`548d877ec2d08e286aec12bc38f1969b9e8653cc18ddeaf9ff724e7cb5bb067a`.
A constant light backing
keeps the Navy artwork readable in both themes; the image is never mirrored in
RTL, recolored, filtered, cropped or reconstructed.

The second image is a **1254 × 1254 presentation sheet**, containing multiple
icons, captions and size specifications. It is not installed as a favicon and
no icon is extracted or redrawn. Standalone approved icon exports remain needed
for favicon/app-icon integration. The original sheet stays in the supplied
directory rather than becoming an application asset.

Logo follow-up verification: **11 targeted unit tests passed**, strict typing and
the normal build passed, and formatting passed. A separate local browser check
verified **24 rendered states**: access and navigation, FR/EN/AR, Light/Dark,
desktop 1440 px and mobile 390 px. All retained the natural aspect ratio and
unchanged served-image SHA-256, with no mirroring, filter, overflow or automated
axe violation. The checks and screenshots are retained locally as
`logo-unit-results.json`, `logo-browser-results.json` and `logo-*.png` in the
existing ignored evidence directory. Earlier delivery results below remain
historical evidence; their complete campaigns were not repeated for this asset.

## Verification and delivery inventory

| Verification                | Observed result                                                                                                                                     |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unit tests                  | **128 passed**, zero failures/skips; translation parity, theme lifecycle, 38 contrast-pair checks and draft/confirmation preservation.              |
| Browser tests               | **66 passed**, zero failures/skips/flaky cases; desktop/mobile, all six language/theme combinations, roles and tenant boundaries.                   |
| Accessibility automation    | **86 axe scans**, zero violations: 72 attached matrix scans and 14 checks in the existing browser scenarios. This is not a full WCAG certification. |
| Type checking               | Strict TypeScript, browser test sources and the classic JavaScript bootstrap passed.                                                                |
| Build and review boundaries | Normal disconnected build and both review admission guards passed; 21 JavaScript assets, five local font subsets, no synthetic fixture payload.     |

The initial 66-case browser run found three desktop-dark hover-contrast failures;
63 cases passed. The shared action-hover token was separated from the
light-on-dark link-hover token, and both hover-gradient endpoints were added to
the contrast tests. The final complete 66-case run passed. The initial report is
retained locally as `initial-playwright-results.json` alongside the final result.

The initial frontend source manifest contains **72 files**, including **9 additions and
29 updates** against the accepted restaurant/catalogue/order delivery manifest;
no source was removed. Documentation changes are this report, its index entry
and the frontend guide.

Added: English base/business catalogs; the typed theme subscription; the single
pre-paint store; Sora/Tajawal license notices; unit appearance/store/contrast and
composition tests; the browser appearance matrix; this report. Updated: existing
locale contracts and review labels, i18next setup, shared controls, access/shell
and editor integration, CSS tokens/modules/fonts, HTML/Vite/build typing,
dependency lockfile, browser evidence location, third-party notices and guides.
No separate theme/translation framework or UI application was introduced.

Evidence remains local under ignored `artifacts/frontend-identity-validation/`.
Source documents remain in the supplied external directory. No `.env`, token,
original identity document, ignored artifact or local PDF-reading dependency is
added as a publication input. No backend, migration, Keycloak, Neon, Render,
Redis, Telegram, Health-Only/Auto-Deploy setting, Git push, merge or deployment
was changed. The roadmap remains **Frontend → Business Integration → K11
Production Security → Pilot**.
