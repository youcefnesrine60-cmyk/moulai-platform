// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Local manual SaaS evidence; uploads never claim receipt of funds or bypass server permissions.
import { useId, useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { identityKey, useSession } from '../../app/access';
import {
  Badge,
  Button,
  ErrorPanel,
  LoadingPanel,
} from '../../shared/ui/primitives';
import { AccessError } from '../../shared/access/contracts';
import { useUnsavedChanges } from '../../shared/ui/UnsavedChanges';
import { ExactAmount } from '../../shared/ui/ExactAmount';
import { enrollmentRequest } from './EnrollmentPage';
import styles from './integration.module.css';

const payment = z.object({
  id: z.number(),
  amount: z.string(),
  currency: z.string(),
  status: z.string(),
  receipt_status: z.string().nullable(),
  subscription_status: z.string().optional(),
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

/** Browser/network text is never a reliable domain diagnosis or proof of rollback. */
const failureCode = (error: unknown) =>
  error instanceof Error && /^[a-z_]{1,120}$/.test(error.message)
    ? error.message
    : 'operation_result_unknown';
const readError = (error: unknown) =>
  new AccessError(
    failureCode(error) === 'permission_required' ? 'noAccess' : 'temporary',
  );

/** Render three independent server facts; a paid future period stays scheduled. */
export function PaymentProgress({ row }: { row: Payment }) {
  const { t } = useTranslation();
  const subscription = row.subscription_status;
  const known =
    subscription &&
    ['active', 'scheduled', 'pending', 'expired'].includes(subscription);
  return (
    <ol className={styles.progress}>
      <li>
        <span>{t('quality.proofStage')}</span>
        <Badge tone={row.receipt_status === 'approved' ? 'green' : 'neutral'}>
          {row.receipt_status
            ? t('o3.' + row.receipt_status, {
                defaultValue: t('quality.notConfirmed'),
              })
            : t('quality.notConfirmed')}
        </Badge>
      </li>
      <li>
        <span>{t('quality.fundsStage')}</span>
        <Badge
          tone={
            row.status === 'paid' && row.receipt_status === 'approved'
              ? 'green'
              : 'neutral'
          }
        >
          {t(
            row.status === 'paid' && row.receipt_status === 'approved'
              ? 'quality.confirmed'
              : 'quality.notConfirmed',
          )}
        </Badge>
      </li>
      <li>
        <span>{t('quality.activationStage')}</span>
        <Badge tone={subscription === 'active' ? 'green' : 'neutral'}>
          {known
            ? t('quality.subscription.' + subscription)
            : t('quality.notConfirmed')}
        </Badge>
      </li>
    </ol>
  );
}

/** Show a safe explanation and keep server domain diagnostics secondary. */
const uncertain = (code: string) =>
  ['operation_result_unknown', 'operation_requires_review'].includes(code);
function PaymentOutcome({
  code,
  recheck,
  onRechecked,
}: {
  code: string;
  recheck?: () => Promise<unknown>;
  onRechecked?: () => void;
}) {
  const { t } = useTranslation();
  const [checking, setChecking] = useState(false),
    [failedRead, setFailedRead] = useState(false);
  return code ? (
    <div role="alert">
      <p>
        {t(
          (
            {
              permission_required: 'state.noAccess.body',
              trial_period_not_finished: 'quality.trialWait',
              operation_result_unknown: 'quality.uncertain',
              operation_requires_review: 'quality.uncertain',
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
      {uncertain(code) && recheck && (
        <Button
          type="button"
          variant="secondary"
          disabled={checking}
          onClick={() => {
            setChecking(true);
            setFailedRead(false);
            void recheck()
              .then((result) => {
                if (
                  z.object({ isSuccess: z.literal(true) }).safeParse(result)
                    .success
                )
                  onRechecked?.();
                else setFailedRead(true);
              })
              .catch(() => setFailedRead(true))
              .finally(() => setChecking(false));
          }}
        >
          {t('quality.recheck')}
        </Button>
      )}
      {failedRead && <p>{t('quality.readFailed')}</p>}
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
    if (busy || uncertain(error)) return;
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
      setError(failureCode(caught));
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
        disabled={busy || uncertain(error) || row.receipt_status !== null}
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
              <li key={reason}>
                {t('followup.reason.' + reason, {
                  defaultValue: t('followup.previewChanged'),
                })}
              </li>
            ))}
          </ul>
          <dl>
            <div>
              <dt>{t('quality.oldOffer')}</dt>
              <dd>
                <ExactAmount value={row.amount} currency={row.currency} />
              </dd>
            </div>
            <div>
              <dt>{t('quality.newOffer')}</dt>
              <dd>
                <bdi>
                  {preview.review.pricing.final_amount_due}{' '}
                  {preview.review.currency}
                </bdi>
              </dd>
            </div>
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
        <PaymentOutcome
          code={error}
          recheck={refresh}
          onRechecked={() => setError('')}
        />
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
  const hintId = useId();
  const [file, setFile] = useState<File | null>(null),
    [reference, setReference] = useState(''),
    [synthetic, setSynthetic] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const [dirty, setDirty] = useState(false);
  useUnsavedChanges(dirty);
  async function upload(event: FormEvent) {
    event.preventDefault();
    if (busy || uncertain(error) || !file || !synthetic) return;
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
      setDirty(false);
      await refresh();
    } catch (caught) {
      setError(failureCode(caught));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form
      className={styles.form}
      onChange={() => setDirty(true)}
      onSubmit={(event) => void upload(event)}
      aria-busy={busy}
    >
      <p id={hintId}>{t('quality.receiptHelp')}</p>
      <label>
        {t('o3.reference')}
        <input
          disabled={busy}
          required
          value={reference}
          minLength={3}
          onChange={(event) => setReference(event.target.value)}
        />
      </label>
      <label>
        {t('o3.receipt')}
        <input
          disabled={busy}
          required
          aria-describedby={hintId}
          type="file"
          accept="application/pdf,image/png,image/jpeg"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </label>
      <label className={styles.choice}>
        <input
          disabled={busy}
          type="checkbox"
          required
          checked={synthetic}
          onChange={(event) => setSynthetic(event.target.checked)}
        />
        {t('o3.synthetic')}
      </label>
      <Button
        type="submit"
        disabled={busy || uncertain(error) || !synthetic || !file}
      >
        {t(busy ? 'quality.processing' : 'o3.uploadReceipt')}
      </Button>
      <PaymentOutcome
        code={error}
        recheck={refresh}
        onRechecked={() => setError('')}
      />
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
    if (busy || uncertain(error)) return;
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
      setError(failureCode(caught));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className={styles.panel}>
      <h2>{t('o3.payments')}</h2>
      <p>{t('o3.paymentLocal')}</p>
      <p>{t('quality.noAutomaticFunds')}</p>
      <form className={styles.form} onSubmit={(event) => void checkout(event)}>
        <label>
          {t('o3.transferMethod')}
          <select
            disabled={busy}
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
          disabled={busy || uncertain(error) || !planId || !currency || !method}
        >
          {t(busy ? 'quality.processing' : 'o3.checkout')}
        </Button>
      </form>
      <PaymentOutcome
        code={error}
        recheck={() => query.refetch()}
        onRechecked={() => setError('')}
      />
      {query.isPending ? (
        <LoadingPanel />
      ) : query.isError ? (
        <ErrorPanel
          error={readError(query.error)}
          retry={() => void query.refetch()}
        />
      ) : !query.data.length ? (
        <p role="status">{t('quality.noPayments')}</p>
      ) : (
        query.data.map((row) => (
          <article className={styles.record} key={row.id}>
            <PaymentProgress row={row} />
            <p>
              <strong>
                <ExactAmount value={row.amount} currency={row.currency} />
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
                {t('quality.periodUTC')}:{' '}
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
  const [dirty, setDirty] = useState(false);
  useUnsavedChanges(
    dirty && row.status === 'pending' && row.receipt_status === 'pending',
  );
  async function approve(event: FormEvent) {
    event.preventDefault();
    if (busy || uncertain(error)) return;
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
      setDirty(false);
      await refresh();
    } catch (caught) {
      setError(failureCode(caught));
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className={styles.record} data-saas-payment-id={row.id}>
      <h2>{row.restaurant_name}</h2>
      <p>
        <ExactAmount value={row.amount} currency={row.currency} /> ·{' '}
        {t('o3.payment.' + row.status, { defaultValue: t('o3.failure') })}
      </p>
      <p>
        {t('o3.reference')}: <bdi>{row.reference ?? '—'}</bdi>
      </p>
      {row.status === 'pending' && row.receipt_status === 'pending' && (
        <form
          className={styles.form}
          onChange={() => setDirty(true)}
          onSubmit={(event) => void approve(event)}
          aria-busy={busy}
        >
          <label>
            {t('o3.receivedAmount')}
            <small>
              <ExactAmount value={row.amount} currency={row.currency} /> —{' '}
              {t('quality.required')}
            </small>
            <input
              disabled={busy}
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
              disabled={busy}
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
              disabled={busy}
              required
              value={reference}
              onChange={(event) => setReference(event.target.value)}
              minLength={3}
            />
          </label>
          <label>
            {t('o3.reason')}
            <input
              disabled={busy}
              required
              value={note}
              onChange={(event) => setNote(event.target.value)}
              minLength={3}
            />
          </label>
          <label className={styles.choice}>
            <input
              disabled={busy}
              type="checkbox"
              required
              checked={checked}
              onChange={(event) => setChecked(event.target.checked)}
            />
            {t('o3.fundsChecked')}
          </label>
          <Button type="submit" disabled={busy || uncertain(error) || !checked}>
            {t(busy ? 'quality.processing' : 'o3.confirmFunds')}
          </Button>
        </form>
      )}
      <PaymentOutcome
        code={error}
        recheck={refresh}
        onRechecked={() => setError('')}
      />
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
        <ErrorPanel
          error={readError(query.error)}
          retry={() => void query.refetch()}
        />
      ) : !query.data.length ? (
        <p role="status">{t('quality.noReview')}</p>
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
