# Frontend: first coherent delivery

Date: **2026-10-22**. Status: **implemented and locally verified; review only**.
The [approved architecture](frontend-architecture.md) remains the boundary.
No backend, database, migration, Keycloak configuration or deployed service was
changed. K9/K10 were not reopened and their campaigns were not repeated.

## Delivered files and screens

**48 files under `frontend/`** provide the independent application:

| Source group | Responsibilities |
| --- | --- |
| `package.json`, `package-lock.json`, `.npmrc`, `.nvmrc`, four TypeScript configs, `vite.config.ts`, formatter config | Exact dependency versions, strict types, reproducible installation and loopback-only review. |
| `src/app/` | Query/access providers, browser routes, separate tenant/platform shells, cancellation and cache clearing. |
| `src/features/access/AccessPage.tsx` | Disconnected sign-in state and explicitly labeled local synthetic-profile review form. |
| `src/features/workspace/WorkspacePages.tsx` | Explicit company selection, granted restaurant list, restaurant read context, empty grants and denied/error states. |
| `src/features/platform/PlatformPage.tsx` | Platform-only navigation and permitted future module information; no tenant data or payment approval action. |
| `src/shared/access/`, `src/review/syntheticAdapter.ts` | Typed view contracts, intentional disconnected adapter and isolated ephemeral fixtures. |
| `src/shared/ui/`, `src/shared/styles/`, `src/shared/i18n/` | Components, CSS Modules/tokens, local fonts, French and Arabic catalogs, pluralization and RTL. |
| `tests/unit/`, `tests/e2e/`, `playwright.config.ts`, `scripts/` | Adapter/component/navigation/browser checks, actual Vite rejection checks and build fixture inspection. |
| `README.md`, `THIRD_PARTY_NOTICES.md`, `public/licenses/` | Launch/reproduction guide and original font/icon notices. |

The [workspace guide](../frontend/README.md) lists all browser paths and launch
commands. These paths are frontend views, not newly invented API endpoints.
No actual sign-in, catalogue update, fulfillment, settlement or approval is
advertised as operational. Unconnected modules are labeled accordingly.

Owner can explicitly select A or B without unioning resources. Manager and
Staff have distinct explicit restaurant grants; empty grants expose nothing.
Unlinked/suspended profiles have denial screens. The platform profile has its
own area and no implicit company membership. Tenant profiles receive no platform
permissions; no tenant fixture receives `tenant.orders.fulfill`. Review policy
projections are checked against the existing frozen E1 seed without executing
it. This is frontend review coverage, not a replacement backend policy system.

## Actual local verification

| Check | Observed result |
| --- | --- |
| Toolchain | Official portable Node **24.22.1 LTS**, checksum verified; npm **11.19.1**. No global Windows installation or execution-policy change. |
| Locked installation | `npm.cmd ci --offline` completed successfully from the populated local npm cache: 166 packages installed. Installation audit reported zero known vulnerabilities at that observation. |
| TypeScript | Strict project builds passed for application, configuration and tests. |
| Vitest | **23 passed, 0 failures, 0 skips**. |
| Playwright | **22 passed, 0 failures, 0 skips, 0 flaky**, Chromium desktop and mobile. |
| Mobile/RTL | FR/AR, 390 px mobile, explicit 360 px check, 1440 px desktop, no measured horizontal overflow; Arabic drawer keyboard escape/focus restoration verified. |
| Accessibility | Four axe scans on access/company screens across desktop/mobile and FR/AR completed with no detected violations for the selected WCAG tags. Not a conformance certification. |
| Review admission | Real Vite configuration rejected both a review publication build and a non-loopback review host without starting either server. |
| Normal build | Passed; lazy feature chunks, local fonts, 10 JavaScript assets; known fixture names/issuer and synthetic-adapter chunk absent. Normal build remains disconnected. |
| Formatting | Prettier passed; standard source headers and scoped Git whitespace checks reviewed. |

The source uses React **19.3.1**, TypeScript **7.0.2**, Vite **8.3.5** and the
exact remaining versions in the lockfile. Resolver 6 initially produced an
optional-peer conflict; compatible resolver **5.9.2** and Zod **3.25.76** were
installed without `--force` or peer bypass. Initial unit filesystem/type setup
and a font-subset import were corrected before final verification. Large initial
bundling was resolved by actual route splitting, not warning suppression.

The first sandboxed 18-case browser run passed its assertions but stalled while
closing its two test servers. Their exact process identities were checked and
only those servers were stopped. The final expanded 22-case run completed
normally outside that sandbox restriction, including server cleanup. No unrelated
process, database or service was stopped. Initial evidence is retained locally;
it is not added to the final test count.

Machine results, source manifest and desktop/mobile screenshots are retained
under ignored `artifacts/frontend-validation/`. Tool binaries, npm cache and
test browsers remain under ignored `artifacts/frontend-tooling/`. Neither
directory is a Git publication input. Dependency installation needed network
access to official distribution/package hosts; application tests allowed HTTP
only to the two owned loopback test servers. No backend endpoint was called.

## Brand and integration limits

No official MoulAI logo asset or approved palette was available. The interface
uses plain MoulAI text and provisional neutral UI tokens. No logo was traced,
redesigned or approximated. The official asset must be inserted unchanged with
its intrinsic proportions and original colors once supplied; brand-color
approval remains pending. Font/icon notices retain their original licenses.

Review fixtures require explicit local review mode and live only in memory.
The normal development/profile build exposes the unavailable-connection screen;
there is no automatic fixture fallback, credential collection or token storage.
Only locale preference persists. K10 test routes, diagnostics and the public
Render Health-Only URL are not used. No Render, Auto-Deploy, OIDC, Redis,
Telegram, Neon or production protection setting was changed.

Real identity bindings, company/capability contracts and business operations
remain for **Business Integration**. Firefox/WebKit, real identity-provider and
backend-integrated browser tests were not run in this delivery. No frontend
publication, deployment, merge into main or production-readiness certification
is implied. The roadmap remains **Frontend → Business Integration → K11
Production Security → Pilot**.
