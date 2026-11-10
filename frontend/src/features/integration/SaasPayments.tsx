// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Local manual SaaS evidence; uploads never claim receipt of funds or bypass server permissions.
import { useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { identityKey, useSession } from '../../app/access';
import { Button, LoadingPanel } from '../../shared/ui/primitives';
import { enrollmentRequest } from './EnrollmentPage';
import styles from './integration.module.css';

const payment = z.object({
  id: z.number(),
  amount: z.string(),
  currency: z.string(),
  status: z.string(),
  receipt_status: z.string().nullable(),
  retained_country: z.string().nullable().optional(),
  retained_B: z.string().nullable().optional(),
  retained_rate: z.string().nullable().optional(),
  retained_pre_payment: z.string().nullable().optional(),
  starts_at: z.string().nullable().optional(),
  expires_at: z.string().nullable().optional(),
});
const reviewPayment = payment.extend({
  restaurant_name: z.string(),
  reference: z.string().nullable(),
});
type Payment = z.infer<typeof payment>;

/** Show a safe explanation and keep server domain diagnostics secondary. */
function PaymentOutcome({ code }: { code: string }) {
  const { t } = useTranslation();
  return code ? (
    <div role="alert">
      <p>
        {t(
          (
            {
              billing_country_pending_offer_requires_recalculation:
                'followup.obsolete',
              offer_not_obsolete: 'followup.currentOffer',
              offer_preview_changed_review_again: 'followup.previewChanged',
              country_base_missing: 'followup.missingPair',
              validated_billing_country_required: 'followup.countryRequired',
              payment_adjustment_configuration_missing:
                'followup.policyRequired',
              payment_adjustment_configuration_invalid:
                'followup.policyRequired',
            } as Record<string, string>
          )[code] ?? 'o3.failure',
        )}
      </p>
      <details>
        <summary>{t('o3.technical')}</summary>
        <code dir="ltr">{code}</code>
      </details>
    </div>
  ) : null;
}

/** Two explicit steps; financial evidence always requires separate administrative handling. */
function ReplaceOffer({
  row,
  root,
  currency,
  refresh,
}: {
  row: Payment;
  root: string;
  currency: string | null;
  refresh: () => Promise<unknown>;
}) {
  const { t } = useTranslation();
  const [preview, setPreview] = useState<{
    approval: string;
    review: {
      pricing: Record<string, string>;
      reasons: string[];
      currency: string;
    };
  } | null>(null);
  const [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  async function submit(confirm: boolean) {
    setBusy(true);
    setError('');
    try {
      const result = await enrollmentRequest(
        `${root}/${row.id}/replacement`,
        'POST',
        {
          currency: currency || row.currency,
          ...(confirm && preview ? { approval: preview.approval } : {}),
        },
      );
      if (confirm) {
        setPreview(null);
        await refresh();
      } else
        setPreview(
          z
            .object({
              approval: z.string(),
              review: z.object({
                pricing: z.record(z.string()),
                reasons: z.array(z.string()),
                currency: z.string(),
              }),
            })
            .parse(result),
        );
    } catch (caught) {
      setPreview(null);
      setError(
        caught instanceof Error ? caught.message : 'operation_requires_review',
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <p>{t('followup.replacementInfo')}</p>
      <Button
        type="button"
        variant="secondary"
        disabled={busy || row.receipt_status !== null}
        onClick={() => void submit(false)}
      >
        {t('followup.preview')}
      </Button>
      {row.receipt_status !== null && <p>{t('followup.financial')}</p>}
      {preview && (
        <div>
          <p>{t('followup.obsolete')}</p>
          <ul>
            {preview.review.reasons.map((reason) => (
              <li key={reason}>{t('followup.reason.' + reason)}</li>
            ))}
          </ul>
          <dl>
            {[
              'base_price',
              'multi_branch_cost',
              'final_price',
              'payment_adjustment',
              'final_amount_due',
            ].map((key) => (
              <div key={key}>
                <dt>{t('offer.' + key)}</dt>
                <dd>
                  <bdi>
                    {preview.review.pricing[key]} {preview.review.currency}
                  </bdi>
                </dd>
              </div>
            ))}
          </dl>
          <Button
            type="button"
            disabled={busy}
            onClick={() => void submit(true)}
          >
            {t('followup.confirm')}
          </Button>
        </div>
      )}
      {error === 'offer_financial_evidence_requires_administration' ? (
        <p role="alert">{t('followup.financial')}</p>
      ) : (
        <PaymentOutcome code={error} />
      )}
    </section>
  );
}

/** A receipt is a separate explicit upload, with no prechecked statement or implicit settlement. */
function ReceiptForm({
  row,
  root,
  refresh,
}: {
  row: Payment;
  root: string;
  refresh: () => Promise<unknown>;
}) {
  const { t } = useTranslation();
  const [file, setFile] = useState<File | null>(null),
    [reference, setReference] = useState(''),
    [synthetic, setSynthetic] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file || !synthetic) return;
    setBusy(true);
    setError('');
    try {
      if (file.size > 2 * 1024 * 1024)
        throw new Error('billing_country_document_too_large');
      await enrollmentRequest(
        `${root}/${row.id}/receipt?synthetic=true&reference=${encodeURIComponent(reference)}`,
        'POST',
        undefined,
        file,
      );
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : 'operation_requires_review',
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className={styles.form} onSubmit={(event) => void upload(event)}>
      <label>
        {t('o3.reference')}
        <input
          required
          value={reference}
          minLength={3}
          onChange={(event) => setReference(event.target.value)}
        />
      </label>
      <label>
        {t('o3.receipt')}
        <input
          required
          type="file"
          accept="application/pdf,image/png,image/jpeg"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </label>
      <label className={styles.choice}>
        <input
          type="checkbox"
          required
          checked={synthetic}
          onChange={(event) => setSynthetic(event.target.checked)}
        />
        {t('o3.synthetic')}
      </label>
      <Button type="submit" disabled={busy || !synthetic || !file}>
        {t('o3.uploadReceipt')}
      </Button>
      <PaymentOutcome code={error} />
    </form>
  );
}

/** Persist an owned offer through the shared pricing engine; do not compute or trust a browser amount. */
export function SaasPayments({
  organizationId,
  restaurantId,
  planId,
  cycle,
  currency,
}: {
  organizationId: number;
  restaurantId: number;
  planId: number | null;
  cycle: string;
  currency: string | null;
}) {
  const { t } = useTranslation(),
    session = useSession();
  const root = `/organizations/${organizationId}/restaurants/${restaurantId}/saas-payments`;
  const query = useQuery({
    queryKey: [...identityKey(session.data), root],
    queryFn: async () => z.array(payment).parse(await enrollmentRequest(root)),
    retry: false,
  });
  const [method, setMethod] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  async function checkout(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await enrollmentRequest(root, 'POST', {
        plan_id: planId,
        billing_cycle: cycle,
        payment_method: method,
        currency,
        additional_feature_ids: [],
      });
      await query.refetch();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : 'operation_requires_review',
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className={styles.panel}>
      <h2>{t('o3.payments')}</h2>
      <p>{t('o3.paymentLocal')}</p>
      <form className={styles.form} onSubmit={(event) => void checkout(event)}>
        <label>
          {t('o3.transferMethod')}
          <select
            required
            value={method}
            onChange={(event) => setMethod(event.target.value)}
          >
            <option value="">{t('offer.choose')}</option>
            <option value="ccp">CCP</option>
            <option value="baridimob">BaridiMob</option>
          </select>
        </label>
        <Button
          type="submit"
          disabled={busy || !planId || !currency || !method}
        >
          {t('o3.checkout')}
        </Button>
      </form>
      <PaymentOutcome code={error} />
      {query.isPending ? (
        <LoadingPanel />
      ) : query.isError ? (
        <PaymentOutcome code="permission_required" />
      ) : (
        query.data.map((row) => (
          <article className={styles.record} key={row.id}>
            <p>
              <strong>
                <bdi>
                  {row.amount} {row.currency}
                </bdi>
              </strong>{' '}
              ·{' '}
              {t('o3.payment.' + row.status, { defaultValue: t('o3.failure') })}
            </p>
            <p>
              {t('followup.retained')}:{' '}
              <bdi>
                {row.retained_country ?? '—'} / {row.currency}
              </bdi>
            </p>
            <p>
              {t('followup.B')}: <bdi>{row.retained_B ?? '—'}</bdi> ·{' '}
              {t('followup.paymentRate')}: <bdi>{row.retained_rate ?? '—'}</bdi>
            </p>
            {row.starts_at && (
              <p>
                <bdi>
                  {row.starts_at} → {row.expires_at ?? '—'}
                </bdi>
              </p>
            )}
            {row.receipt_status && (
              <p>
                {t('o3.' + row.receipt_status, {
                  defaultValue: t('o3.pending'),
                })}
              </p>
            )}
            {row.status === 'pending' && (
              <ReplaceOffer
                row={row}
                root={root}
                currency={currency}
                refresh={() => query.refetch()}
              />
            )}
            {row.status === 'pending' && row.receipt_status === null && (
              <ReceiptForm
                row={row}
                root={root}
                refresh={() => query.refetch()}
              />
            )}
            <details>
              <summary>{t('o3.technical')}</summary>
              <code dir="ltr">{row.id}</code>
            </details>
          </article>
        ))
      )}
      <Button variant="secondary" onClick={() => void query.refetch()}>
        {t('o3.refresh')}
      </Button>
    </section>
  );
}

/** Verify funds facts independently; a successful repeated review is idempotent on the server. */
function FundsReview({
  row,
  refresh,
}: {
  row: z.infer<typeof reviewPayment>;
  refresh: () => Promise<unknown>;
}) {
  const { t } = useTranslation();
  const [amount, setAmount] = useState(''),
    [currency, setCurrency] = useState(''),
    [reference, setReference] = useState(''),
    [note, setNote] = useState(''),
    [checked, setChecked] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  async function approve(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await enrollmentRequest(
        `/platform/saas-payments/${row.id}/review`,
        'POST',
        {
          decision: 'approve',
          funds_received: checked,
          received_amount: amount,
          received_currency: currency,
          bank_transaction_reference: reference,
          note,
        },
      );
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : 'operation_requires_review',
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className={styles.record} data-saas-payment-id={row.id}>
      <h2>{row.restaurant_name}</h2>
      <p>
        <bdi>
          {row.amount} {row.currency}
        </bdi>{' '}
        · {t('o3.payment.' + row.status, { defaultValue: t('o3.failure') })}
      </p>
      <p>
        {t('o3.reference')}: <bdi>{row.reference ?? '—'}</bdi>
      </p>
      {row.status === 'pending' && row.receipt_status === 'pending' && (
        <form className={styles.form} onSubmit={(event) => void approve(event)}>
          <label>
            {t('o3.receivedAmount')}
            <input
              required
              inputMode="decimal"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              dir="ltr"
            />
          </label>
          <label>
            {t('o3.receivedCurrency')}
            <input
              required
              value={currency}
              onChange={(event) => setCurrency(event.target.value)}
              pattern="[A-Z]{3}"
              maxLength={3}
              dir="ltr"
            />
          </label>
          <label>
            {t('o3.reference')}
            <input
              required
              value={reference}
              onChange={(event) => setReference(event.target.value)}
              minLength={3}
            />
          </label>
          <label>
            {t('o3.reason')}
            <input
              required
              value={note}
              onChange={(event) => setNote(event.target.value)}
              minLength={3}
            />
          </label>
          <label className={styles.choice}>
            <input
              type="checkbox"
              required
              checked={checked}
              onChange={(event) => setChecked(event.target.checked)}
            />
            {t('o3.fundsChecked')}
          </label>
          <Button type="submit" disabled={busy || !checked}>
            {t('o3.confirmFunds')}
          </Button>
        </form>
      )}
      <PaymentOutcome code={error} />
    </article>
  );
}

export function SaasPaymentReviewPage() {
  const { t } = useTranslation(),
    session = useSession();
  const query = useQuery({
    queryKey: [...identityKey(session.data), 'saas-payment-review'],
    queryFn: async () =>
      z
        .array(reviewPayment)
        .parse(await enrollmentRequest('/platform/saas-payments')),
    retry: false,
  });
  return (
    <section className={styles.panel}>
      <h1>{t('o3.paymentReview')}</h1>
      <p>{t('o3.paymentLocal')}</p>
      {query.isPending ? (
        <LoadingPanel />
      ) : query.isError ? (
        <PaymentOutcome code="permission_required" />
      ) : (
        query.data.map((row) => (
          <FundsReview key={row.id} row={row} refresh={() => query.refetch()} />
        ))
      )}
      <Button variant="secondary" onClick={() => void query.refetch()}>
        {t('o3.refresh')}
      </Button>
    </section>
  );
}
