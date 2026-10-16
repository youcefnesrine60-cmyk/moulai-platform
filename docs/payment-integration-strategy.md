# MoulAI™ — Payment Integration Strategy

Approved project direction: 13 October 2026. This roadmap follows the owner's
explicit instruction to implement phase one and keep later integrations dormant
until official provider documentation, contracts, and approval are available.

## Delivery stages

| Stage | Scope | Activation condition |
| --- | --- | --- |
| 1 — Local launch | Manual CCP and BaridiMob transfers; private receipt upload; transaction reference; independent administrative verification; audit history; RBAC; duplicate prevention | Deploy the manual-billing migration, configure trusted identities, and establish the administrative bank-verification procedure |
| 2 — Algerian electronic payments | CIB and Edahabia through an approved provider; authenticated notifications or official status queries | Official documentation, contracts, licences, and a reviewed adapter |
| 3 — International SaaS | Stripe, PayPal and additional providers; multiple currencies; recurring billing; refunds; reconciliation; invoices and transaction history | Country availability, commercial approval, provider documentation and separate implementation work |

No Stripe, PayPal, CIB or Edahabia integration is enabled by this change. No
provider API, callback signature format, or successful payment response is invented.
CCP and BaridiMob in phase one are manual transfers, with `manual_transfer` as
their provider. A method and a provider are distinct concepts.

## Current architecture

- `payment_providers/contracts.py` defines a small typed provider contract and
  immutable payment instructions. The manual adapter requires evidence and
  administrative review; it has no external network API.
- `SubscriptionCheckoutService` coordinates authoritative pricing, a pending
  subscription, and its pending invoice within one transaction.
- `PaymentService` owns the payment ledger. `SubscriptionService` applies
  subscription activation and feature transfer after verified settlement.
- `ManualPaymentService` owns receipt submission and administrative decisions.
  It rechecks live database RBAC for review commands.
- HTTP routes own authentication and bounded file transport. Repositories own
  queries and flushes; the business transaction owns commit or rollback.
- Restaurant ownership and the authenticated owner's database identity establish
  the tenant boundary. Platform financial reviewers can review tenant invoices
  only with the explicit `payments.review` permission.

The subscription price comes from stored plans, pricing rules and server-side
tenant metrics. Checkout accepts no client amount or discount override. New
prices are rounded to DZD cents before the invoice is stored. Current billing
supports DZD only; multi-currency billing is a later stage. Historical ledger
amount columns remain unchanged by this migration.

## Manual workflow

1. An authenticated owner creates a pending subscription checkout. The method
   must be enabled and the plan active. Identical retries reuse its pending
   invoice; conflicting current checkouts are rejected.
2. The owner performs the transfer using the bank details supplied through the
   platform's established payment instructions, then uploads its evidence and
   transaction reference against the invoice.
3. Submission leaves both payment and subscription pending. Evidence is stored
   privately in PostgreSQL and never exposed through a public static URL.
4. A financial reviewer checks the actual bank credit independently of the
   uploaded image. Approval must explicitly attest received funds, record the
   bank transaction reference, amount, currency, and a review note. These values
   must match the invoice and reference.
5. Approval changes the payment to paid, activates the subscription, transfers
   requested features, finalizes the receipt review, and appends the audit record
   in one transaction. Any failure rolls back all these effects.
6. Rejection records a final decision and failed payment without activating the
   subscription. A rejected submission cannot subsequently be approved through
   the same review command; discrepancies require an independently audited
   reconciliation procedure, which is outside phase one.

Uploading a receipt or checking a box alone never activates a subscription.
The server cannot independently observe a manual bank credit: the authorized
reviewer's verified ledger check is the operational control.

## API contracts

All paths below start with `/api/v1`. Owner and reviewer requests require
verified OIDC bearer identities. Amounts, references, review notes and file
contents must not be placed in public URLs or logs.

| Method and path | Purpose |
| --- | --- |
| `POST /billing/subscriptions` | Create/reuse a pending manual subscription invoice |
| `POST /payments/{payment_id}/receipt` | Upload the raw PNG, JPEG or PDF body, with `Content-Type` and `X-Transaction-Reference` headers |
| `GET /payments/{payment_id}/receipt` | Read the authenticated owner's receipt metadata |
| `GET /payments/{payment_id}/receipt/file` | Download the authenticated owner's private evidence |
| `GET /admin/manual-payments` | Paginated queue of pending receipt reviews |
| `GET /admin/manual-payments/{payment_id}` | Expected invoice, evidence metadata, and immutable audit history for a reviewer |
| `GET /admin/manual-payments/{payment_id}/receipt/file` | Authorized reviewer download |
| `POST /admin/manual-payments/{payment_id}/review` | Independently approve or reject a manual payment |

Checkout JSON:

```json
{"restaurant_id": 12, "plan_id": 3, "billing_cycle": "monthly", "payment_method": "ccp"}
```

Approval JSON must use the independently observed bank amount and reference:

```json
{
  "decision": "approve",
  "funds_received": true,
  "bank_transaction_reference": "POSTAL-REFERENCE-123",
  "received_amount": "1500.00",
  "received_currency": "DZD",
  "note": "Credit checked in the bank ledger by the authorized reviewer"
}
```

Rejection JSON:

```json
{"decision": "reject", "note": "Transfer was not found in the bank ledger"}
```

Evidence is limited to 2 MiB and checked against its declared PNG, JPEG or PDF
signature. Downloads force attachment, disable caching and use `nosniff`.
Files are evidence for human review, never executed or trusted as payment events.

Exact repeat submissions against the same invoice are idempotent. Database
uniqueness constraints prevent reusing the same file hash or normalized postal
transaction reference across invoices and tenants, including after rejection.
Punctuation and case variants normalize to the same reference. Conflict responses
do not disclose the matching tenant. This prevents reuse of submitted evidence;
altered images still require the independent bank-reference check.

Review row locks refresh previously loaded ORM objects before deciding whether
an operation is a retry. A completed review retains its original settlement
timestamp, subscription dates and audit entries even when a long-lived session
previously loaded the pending state. Audit payloads preserve the reviewer ID
in addition to its foreign-key reference.

Legacy owner endpoints that directly edit, confirm, fail, cancel, refund or
delete subscription-payment ledger entries now reject those operations. Their
owner scope check remains in place. Telegram payment selection and confirmation
submit pending order-payment requests; a customer's button press is not proof
of received money. Order payments remain a separate ledger from SaaS billing.

## Deployment and operational setup

1. Obtain independent approval before applying production migration
   `c413b7918a20` from the inspected revision `a91e7c2b4d10`. The isolated test
   history has its own migration, `dce91870b4a2`. Production migrations have not
   been applied by this task. Startup validates tables and columns and never
   silently creates them. Existing receipt tables are adopted only after a
   strict schema comparison; mismatches abort before the first schema change.
2. Keycloak is the approved identity provider. Its Realm, API client, issuer,
   audience, JWKS endpoint, and actual administrator subjects are not ready.
   Protected administrative APIs fail closed until real trusted configuration
   exists. Map each authorized administrator's trusted OIDC `sub` to `admins.auth_subject`
   through the trusted deployment/database administration procedure. A bearer
   claim containing an arbitrary admin ID is not accepted. Active normalized
   roles and `payments.review` are required; support roles do not receive it.
   The pending migration registers the permission without granting it to any
   role or binding administrator identities. Existing explicit grants and the
   `super_admin` wildcard remain unchanged; reviewer assignment is a separate
   authorized decision.
3. Keep `MANUAL_CCP_ENABLED` and `MANUAL_BARIDIMOB_ENABLED` aligned with the
   accepted methods. Disabling a method blocks new checkouts and submissions;
   existing evidence remains available for review and private history.
4. Publish the tested code through the existing GitHub-to-Render service after
   verifying its actual service name and connected branch. Set the same
   `TELEGRAM_WEBHOOK_SECRET_TOKEN` in Render and in the registration operation.
   Register only after the deployed endpoint rejects unauthenticated updates
   and recognizes the configured secret. No live registration has occurred.
5. Configure `MANUAL_TRANSFER_BENEFICIARY`, `MANUAL_CCP_ACCOUNT`,
   `MANUAL_CCP_KEY`, and `MANUAL_BARIDIMOB_RIP` through central Settings in the
   real environment. CCP and BaridiMob details must belong to the same intended
   postal account; no RIP is fabricated or derived. Unconfigured methods are
   hidden in Telegram, and no beneficiary values appear in source or logs.
6. Provide private database backup and receipt-retention procedures. Audit and
   evidence references prevent ledger deletion through ordinary CRUD. There is
   no public audit-edit or audit-delete endpoint for manual billing.

Telegram now provides `/billing`, owned restaurant and plan selection, monthly
or yearly checkout, a server-priced invoice with its payment-request reference,
private receipt upload, cancellation, and status tracking. It accepts PNG, JPEG,
or PDF evidence up to 2 MiB through the official Telegram file API. The signed
update must identify the actual private-chat sender. Receipt content, reference,
and invoice ownership are revalidated by the shared billing service.

Telegram cannot approve, reject, download an administrative receipt, or activate
a subscription. Administrative review is available only through the verified
OIDC API with live `payments.review` RBAC. Telegram IDs and Keycloak subjects
remain separate; no automatic identity mapping is created.

See [the production runbook](billing-production-runbook.md) for the verified
deployment sequence, required environment keys, and independent migration step.

## Contracts for later stages

New providers require independent adapters and explicit configuration. An adapter
must authenticate the official notification on the exact transport payload or
perform an official status query before producing a settlement command. The
command must bind provider identity, invoice, tenant, amount and currency, and
use provider event IDs for durable idempotency. No provider may directly mutate
subscription state. Card details must remain with the approved provider.

Multi-currency billing will require currency-aware money storage and accounting;
recurring billing requires its own billing-period and retry model; refunds and
reconciliation require audited ledger commands and official provider receipts.
These belong to the long-term Agent-as-a-Service roadmap and are not implemented
as placeholder successful operations.
