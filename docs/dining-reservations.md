# Tables, reservations and restaurant advances

Status: **local implementation delivered for review — 2026-11-03**. Owner-authorized
scope: local code, additive migrations from S1a and disposable-local tests.
Permanent database activation, live transports, model providers and deployment
are excluded. The initial inventory is retained in
[the targeted gap matrix](../artifacts/dining-module-20261102/plan.md).

## Financial contract approved during implementation

One food invoice belongs to one reservation and its associated existing orders.
This is separate from the owner's SaaS subscription and its payment permissions.
New money uses `Decimal` in services and `Numeric(24,8)` in persistence. Currency
and its configured precision are explicit; currency conversion is unsupported.

An invoice has `draft` and `finalized` states. Its immutable identity includes
restaurant, branch, reservation, currency and precision. A draft retains exact
food-line descriptions, quantities and unit prices, source order/item IDs and
the evidence used for reconciliation. The total is the sum of exact line
products, rounded once at the final total with `ROUND_HALF_UP`. No new tax,
service charge or reservation-quote component is added automatically.

Finalization must verify the request's actual arrival, all source orders in the
same restaurant and branch, the selected reservation tables, all included order
items, a nonempty authoritative decimal source reference, currency provenance,
and rounding provenance. Existing order amounts are Float and cannot establish
authoritative exact money merely through `Decimal(str(old_float))`. Raw legacy
values are retained as diagnostic strings; reviewed exact values must come from
an explicitly identified source and a recorded authorized human reviewer. Any
discrepancy requires explicit acknowledgement and traceable reconciliation.
Missing or unreliable provenance blocks finalization without rewriting orders.

Source order links are unique: an order cannot silently fund two invoices.
Finalized lines, quantities, prices, provenance and total cannot be changed by
later catalogue edits or invoice updates. One reservation has one invoice in
this first scope; splitting between invoices is unsupported.

An independently committed restaurant receipt is an already received payment.
Its one-time allocation reduces the balance, never the sales total. For example,
6,000 DZD sales minus an allocated 1,500 DZD advance leaves 4,500 DZD payable.
The receipt row and invoice are locked; a unique receipt allocation prevents
repeated or concurrent reuse. Allocation rollback cannot erase the earlier
receipt. Different currencies, an unresolved payment, or missing invoice
provenance block allocation. An excess is identified for human handling, with
no negative balance, automatic refund or invented split policy.

## Authority and state separation

The existing E1 services resolve current OIDC identity, active membership and
restaurant scope. New explicit branch dining grants distinguish service,
cleaning, collection and assistant responsibilities. Owner configuration is
separate from those operational grants. SaaS review permissions, JWT realm
role names and Telegram identifiers do not grant dining collection authority.
No personal grant is seeded by migration.

Physical table state is independent of exclusive schedule claims, customer
requests, human availability confirmations and actual occupations. Elapsing a
planned departure never frees an occupied table. Cleaning completion changes
physical availability without cancelling future reservations or blackouts.

## Schema and local validation path

The additive main-history revision is `d1a20261102`, directly after
`s1a20261028`. The disposable dining profile reconstructs the principal bootstrap
and S1a before applying D1's real DDL. It does not use `create_all` or `stamp`.
Dining mappings have opt-in independent metadata, preserving the existing S1a
startup and fixture registry when the new module is not selected.

Active time claims use `[start,end)` ranges with a PostgreSQL exclusion
constraint. The trusted `btree_gist` extension is an explicit prerequisite
requiring database CREATE privilege. No privilege is granted by the migration.
The database's accepted six NOT VALID E1 foreign keys remain unchanged.

References: [PostgreSQL range exclusion](https://www.postgresql.org/docs/18/rangetypes.html),
[btree_gist privilege requirements](https://www.postgresql.org/docs/18/btree-gist.html).

## Policies that require actual restaurant configuration

Timezone, weekly services/rest days, dated exceptions, margins, response/hold/
lateness/confirmation durations, alert offsets and escalation recipients,
currency precision, payment instructions, terms and tariff versions have no
commercial seed defaults. The owner explicitly supplies them.

Only table-set prior confirmations are initially supported. A broader zone or
branch-wide autonomous confirmation requires its own reviewed contract; it is
not inferred. Ambiguous or nonexistent DST boundaries require an explicit valid
choice, not a guessed timestamp. A single calendar query has a 366-day technical
bound; this is not a commercial duration or billing rule.

Late, partial, excess or different-currency receipts remain financial facts for
manual review. Silence, a client departure, or an elapsed delay is not human
availability approval. Post-payment changes, cancellation treatment and refunds
have no automatic implementation without an approved policy.


## Persisted data and transitions

| Responsibility | Persisted records | Decision boundary |
| --- | --- | --- |
| Owner configuration | policies, references, tables, traits, combinations/members, tariffs, calendar, blackouts, grants | Existing verified E1 owner; no automatic personal operational grants |
| Demand and agreement | requests, request_tables, quotes, acceptances, confirmations | Customer issuer/subject verified by the trusted channel; human service proof is separate |
| Planning | active claims with GiST exclusion | Hold expires explicitly; finalization transforms all matching claims atomically |
| Actual service | occupations, occupation_tables | Human service installs; separately habilitated cleaner observes departure, starts and finishes cleaning |
| Received funds | receipts | Human collector commits receipt independently before later confirmation/allocation |
| Food sales | invoices, invoice_orders | One reservation, explicit complete reconciled order/item sources, frozen Decimal lines |
| Advance application | allocations | Unique receipt, matching reservation and currency; row locks plus SQL uniqueness |
| Audit and delivery | immutable events, transactional outbox | No delivery inside the originating transaction; injected acknowledged transport only |

Request states are `pending`, `held`, `confirmed`, `arrived`, `served`,
`manual_review`, `cancelled`. There is no automatic cancellation/refund command
for the policy-dependent cases. Occupation states (`occupied`, `dirty`,
`cleaning`, `closed`) are distinct from table physical state. Maintenance and
future bookings survive cleaning. A deadline scan queues configured alerts but
never manufactures a departure or an available physical table.

Durations use **UTC elapsed seconds**, including when a caller supplies an IANA
zone-aware datetime across a daylight-saving transition. Calendars separately
interpret configured local wall times. Tests cover both spring and autumn.

For an invoice, require `request_id`, explicit currency and currency source,
rounding source, human reconciliation reference and unique complete lines:
`order_id`, `order_item_id`, description, exact quantity/unit price and exact
source reference. Record the preparing membership and all original order/item/
option snapshots. Finalization requires arrived/served status and unchanged
sources. Only completed `dine_in` orders in the same restaurant, branch and
selected tables are admitted. A legacy integer `table_id` is not historical
proof by itself; human reconciliation must establish the association. Legacy
paid Float receipts, taxes, delivery charges or adjustments have no inferred
currency/fiscal treatment and block that invoice until a separate contract exists.

`Decimal(str(legacy_float))` is used **only for diagnostic comparison**, never
for the new sale calculation. Declaring a source reference is a traceable human
attestation, not automated recovery of lost precision. Final totals alone round
HALF_UP at the configured precision. PostgreSQL additionally rejects Numeric NaN.

A finalized invoice and its source links are immutable. A receipt remains
immutable even if a subsequent confirmation/finalization fails. Repeated and
concurrent application returns the original allocation. It does not create a
second collection. A receipt exceeding the invoice balance is retained in full
and application is suspended for human review: the computed excess is identified,
no portion is silently allocated, no negative balance/refund/split is created.
The approved normal example remains 6000 sales, 1500 advance, 4500 balance.

Tariffs are immutable explicit versions. Use an explicit new pricing reference
and owner-reviewed table/group assignment for a new price schedule, or initially
bounded nonoverlapping validity windows. An indefinite old tariff is never
silently rewritten. A tariff boundary inside one request requires a complete-
period applicable version; there is no unapproved automatic rate splitting.
Accepted proposals keep their frozen components, product names, rates and terms.

Human proof is table-set scoped in this first contract. Table revisions invalidate
proof conservatively on relevant configuration/physical changes; no broad zone
proof is inferred. Branch operations currently serialize on the policy row before
module-grant locks, prioritizing deterministic safety over unmeasured throughput.
An assistant identity cannot hold an E1 owner role or human capability in this
module. This is not an expansion of the closed K9/K10 permission vocabulary.

## Outbox, public QR and explicit integration

Transport jobs become visible only after commit. A delivery acknowledgement is
required to record `transmitted_at`. Definite non-delivery may retry with the same
key; uncertain/sending results require reconciliation and never automatically
repeat. The injected transport must honor deduplication keys. Service and
escalation recipient sets receive the configured alert offsets; a richer staged
escalation policy needs an explicit contract before activation. No worker or
transport is installed on application startup.

The authenticated human confirmation document includes restaurant/branch/tables,
customer, guests, aware times/duration, event reference, frozen quote components,
received advance/currency, terms and a genuine offline SVG QR. The initial
standalone technical print/viewer template is English; the application review
screens have FR/EN/AR. Printed-document localization remains a presentation
follow-up; it does not change the financial/booking contract.

QR data is an opaque read capability in a URL fragment, posted to the same-origin
verification endpoint outside HTTP access-log URL paths. Public verification
returns only reference/status, never personal contacts or payment authority.
No-store, no-referrer and restricted CSP headers apply to the viewer/print.

`app.api.dining.dining_router` requires an explicit session dependency. Optional
`verification_origin` is a trusted host setting, not a customer request field.
The router is **not mounted in app.main**. Its scoped HTTP surfaces cover planning,
receipt recording, invoice preparation/finalization and human print, plus separate
customer consent and public read-only verification. Remaining owner/request/
occupancy operations are concrete transaction-bound service methods, not implicitly
published endpoints. `DiningAssistantTools` is a restricted typed facade, not
registered in AgentEngine or a real provider channel.

Permanent activation requires separate review of D1, configured restaurant
policies/prices/grants, verified customer/staff identity channels, UI/API binding,
transport destination resolution/idempotency, periodic scanner scheduling and
public endpoint rate limiting. No such external activation is performed here.

## Local review and reproducible checks

Frontend route: `/workspace/organizations/9101/restaurants/9201/tables`, after
opening the **synthetic owner review** from `/access`. Select a physical branch.
The review fixture date is 2026-11-03; other dates have no fixture reservations.
The view keeps physical state alongside future reservations, both pending and
human-approved requests, and the exact 6000/1500/4500 invoice simulation. Departure,
cleaning and invoice buttons operate in memory only. No real money is received.
Capabilities are explicit fictional fixture data, not a runtime owner-role policy.
A review identity reset rejects old in-flight writes. The normal build remains
disconnected. Additional production configuration/request forms and the live
adapter are not represented as completed integrations.

```powershell
# Only creates an owned disposable loopback PostgreSQL instance, then stops it.
.\.venv\Scripts\python.exe -B scripts/run_local_postgres_tests.py `
  --backend native --profile dining --test-paths tests/dining

# Existing local Node 24 runtime, no installation or paid service required.
$env:PATH = 'D:\MoulAI\artifacts\frontend-tooling\node-v24.22.1-win-x64;' + $env:PATH
Set-Location D:\MoulAI\frontend
npm.cmd run dev:review -- --port 5573 --strictPort
node node_modules/vitest/vitest.mjs run tests/unit/dining.test.ts tests/unit/access.test.ts tests/unit/appearanceRoutes.test.tsx --maxWorkers=1 --testTimeout=30000
node node_modules/@playwright/test/cli.js test -c playwright.dining.config.ts
```

This is a local business implementation and review, not a certification of the
whole project, a fiscal invoice certification or a production-security approval.
The delivery evidence and full-source archive are indexed in
[the report](../artifacts/dining-module-20261102/rapport.md).

## Raccordement local suivant D1b

Le raccordement persistant des formulaires, l’autorisation dédiée d’annulation et
les nouvelles preuves sont documentés dans
[Dining local integration](dining-local-integration.md). Les chiffres ci-dessus
restent ceux de la livraison D1a historique.
