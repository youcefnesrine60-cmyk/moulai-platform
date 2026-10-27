# Frontend — Agents, Channels and Conversations

Date: 2026-10-26. Status: **implemented and tested for local review**.
All content is synthetic and transient. No backend, database, identity provider
or external messaging service is connected. The accepted visual presentation
and the closed K9/K10/A2+A5 scopes are preserved.

## Available screens

Enter [local review](http://127.0.0.1:5173/access), choose Owner or Manager,
select an organization and an authorized restaurant, then use its module tabs.
These are browser paths beneath
`/workspace/organizations/:organizationId/restaurants/:restaurantId`, not APIs.

| View                             | Delivered behavior                                                                                                   |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `/agents`                        | Name/description search, active/inactive filter, language, tone, channel count and scoped detail links.              |
| `/agents/:agentId`               | Safe descriptive fields, timestamps, related channels and a permission-controlled configuration dialog.              |
| `/channels`                      | Name/type search, type/agent filters, stored active flag and exact agent relationship.                               |
| `/channels/:channelId`           | Type, stored flag, dates and parent agent; no credentials or connection controls.                                    |
| `/conversations`                 | Participant search, status/agent filters, timestamps and five-row pagination.                                        |
| `/conversations/:conversationId` | Participant, agent/channel references and chronological five-message pages, including empty and long-message states. |

The agent form validates name (1–100 characters after trimming, with the raw
100-character ceiling), description (maximum 500), language (`fr/en/ar`) and
tone (`professional/casual/friendly`). A separate confirmation applies the
descriptive change only to this review's memory. Invalid fields have translated
errors and focus; closing the dialog restores focus to its opener.

Messages show the schema's `user`, `assistant` and `system` roles and creation
times. User-provided text is escaped, preserves line breaks and wraps on mobile.
Non-text content types are labeled and displayed as text; no external attachment,
image, link preview or script is loaded. Original merchant names/messages remain
verbatim when changing the interface language.

## Existing contracts and authorization reused

The preliminary inspection was limited to the four agent schema/router families,
their relevant services, the existing permission catalogue and
[agent API security](agent-api-security.md). No backend campaign was rerun.

| Existing contract                   | Safe frontend projection                                                               |
| ----------------------------------- | -------------------------------------------------------------------------------------- |
| `app/schemas/agent/agent.py`        | ID, restaurant, name, description, language, tone, `is_active`, creation/update times. |
| `app/schemas/agent/channel.py`      | ID, exact agent, name, type, `is_active` and times.                                    |
| `app/schemas/agent/conversation.py` | ID, exact agent/channel, participant ID/name, status, `is_active` and times.           |
| `app/schemas/agent/message.py`      | ID, exact conversation, role, content, content type and times.                         |

Types normalize field casing for view use; they do not invent an HTTP endpoint.
Existing list responses justify `items/total/skip/limit` projections. The review's
`agentWorkspace` composes safe views in memory; a restaurant aggregate API is
not assumed to exist. Agent `config`/`ai_config`, channel `config`, conversation
`context`, message entities/metadata and unrestricted provider JSON are excluded.
No independent agent “job role” field or unapproved model capability is invented.

The new frame reuses the existing admitted restaurant frame, session identity,
TanStack Query client, shared grant check, controls, tokens and i18next instance.
No permission rows, role assignments or grants change:

- Agent and channel reads require `tenant.agents.read`; channel access follows
  its exact agent. No new `tenant.channels.*` permission is introduced.
- Descriptive local edits require `tenant.agents.manage`; conversation/message
  reads require `tenant.conversations.read`.
- Owner and Manager review access remains bounded by their existing restaurant
  grants. Staff has neither read permission in the approved catalogue and is
  denied these modules even on its granted restaurant. Platform administration
  confers no tenant membership.
- Foreign child IDs are hidden, including between two companies of the same
  Owner. Conversation → channel → agent → restaurant relationships are checked.
- Queries include exact identity, organization and restaurant. Scope exit cancels
  pending reads, removes module cache entries and drops transient edits; session
  changes also reset the adapter. Local revisions refuse stale overwrites.

**Integration boundary:** the historical FastAPI agent routers still require a
verified owner. The Manager review demonstrates the frozen tenant permission
projection, not a newly granted real API authorization. Mapping those tenant
permissions to real business APIs remains Business Integration. No K10 test route
or real Keycloak session is connected. Backend enforcement remains mandatory.

## Verification actually performed

| Check                                      | Result                                                                                          |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| Strict source typing and normal Vite build | PASS; 27 JavaScript assets inspected, known synthetic fixtures absent.                          |
| Review build/network binding guards        | PASS; review publication build and non-loopback binding refused.                                |
| New unit/route checks                      | **46 passed**: 27 adapter/schema/catalogue checks and 19 real-route/provider checks.            |
| Existing targeted regressions              | **67 passed** across access, management, routes and appearance-route files.                     |
| Browser scenarios                          | **18 distinct scenarios passed**; no remaining failed or unexecuted scenario in this selection. |
| Rendered accessibility/overflow checks     | **74 scans passed**, no reported WCAG-tagged axe violation or horizontal document overflow.     |

The unit total is **113 distinct checks**. The initial selection contained 112;
one pending-read/cancellation case was then added. Focused reruns of the 46 module
checks overlap that selection and are not counted again. The browser matrix
covers all six views in FR/EN/AR × Light/Dark on 1440 px desktop and 390 px mobile
(12 scenarios, 72 captures). Six further scenarios verify Owner cross-company
isolation, Manager grants, Staff denial, platform separation, keyboard form and
System preference behavior, and the normal disconnected build. The form and
confirmation add two Arabic/Dark captures and accessibility scans.

Loading, empty data, retryable errors, unlinked/suspended identity, malformed IDs,
safe HTML display, cancellation, immutable permission projections, stale edits,
identity changes and cache cleanup are covered by targeted unit/route checks.
Browser requests are restricted to the owned loopback ports and GET/HEAD, with
no API path or external request permitted. Automated accessibility checks support
review; they are not a full accessibility certification.

During validation, one browser assertion expected `noAccess` where the existing
parent guard deliberately returns `notFound`; its expectation was corrected.
The new dialog's missing focus restoration was corrected and retested. A scope
navigation assertion was also synchronized with the actual destination heading
before returning, avoiding an immediately cancelled route transition. Original
failure reports/traces are retained locally; successful follow-ups cover only
the affected or previously unexecuted cases. No accepted backend test was rerun.

To reproduce the new targeted checks after dependency installation:

```powershell
Set-Location D:\MoulAI\frontend
node node_modules/vitest/vitest.mjs run tests/unit/intelligence.test.ts tests/unit/intelligenceRoutes.test.tsx --maxWorkers=1
npm.cmd run build
npm.cmd run test:guards
node node_modules/@playwright/test/cli.js test --config playwright.intelligence.config.ts
```

Evidence stays under ignored
[`artifacts/frontend-intelligence-validation/`](../artifacts/frontend-intelligence-validation/):
[capture gallery](../artifacts/frontend-intelligence-validation/index.html),
unit/browser JSON results, original failure traces, the before/after source
manifests and [scope verification](../artifacts/frontend-intelligence-validation/validation.json).
These files are local evidence, not automatically published documentation assets.
No ignored artifact is force-added to Git.

## Source inventory and retained boundaries

Added (16 files):

- `frontend/src/features/intelligence/{scope.tsx,IntelligencePages.tsx,AgentEditor.tsx,intelligence.module.css}`.
- `frontend/src/shared/intelligence/{contracts.ts,validation.ts}`.
- `frontend/src/shared/i18n/intelligence.{fr,en,ar}.ts`.
- `frontend/src/review/{intelligenceAdapter.ts,intelligenceFixtures.ts}`.
- `frontend/tests/unit/{intelligence.test.ts,intelligenceRoutes.test.tsx}`.
- `frontend/tests/e2e/intelligence.spec.ts`, `frontend/playwright.intelligence.config.ts` and this report.

Updated (13 existing files):

- `frontend/src/app/{router.tsx,Shell.tsx}` and `frontend/src/features/management/scope.tsx`: scoped navigation only.
- `frontend/src/shared/access/{contracts.ts,disconnected.ts}` and `frontend/src/review/syntheticAdapter.ts`: extend the existing adapter and reuse its authorization callback.
- `frontend/src/shared/i18n/{fr.ts,en.ts,ar.ts,index.ts}`: navigation labels and the three new catalogues.
- `frontend/scripts/verify-build.mjs`: additional synthetic-fixture exclusion markers.
- `frontend/README.md` and `docs/README.md`: local usage and delivery reference.

The approved logos, archived assets, Gateway, global styles, design tokens,
theme store, existing management fixtures, dependencies/lockfile, backend,
migrations and local environment files are unchanged by this delivery.

Branch remains `feature/keycloak-k10-complete`, HEAD
`457154a2598a4d8a1313e0449faa855e8e32f1f1`. The working tree is dirty, including
the accepted earlier UI deliveries; the new work is uncommitted and nothing is
staged. No Git synchronization or publication was performed or inferred from
local remote references.

Provider activation, sending, live messaging, advanced AI configuration, real
attachments, real authentication and business API integration remain deferred.
No backend, database, service setting, migration, commit, push, merge or deployment
occurred. Render Health-Only and its Auto-Deploy settings were not accessed or
changed. After review, the next requested frontend modules are Reports → Manual
Billing → Platform Administration, followed by Business Integration → K11 → Pilot.
