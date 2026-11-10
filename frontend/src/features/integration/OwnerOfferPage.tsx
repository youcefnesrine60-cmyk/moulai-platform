// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Owned, nonbinding offer consultation; the server remains the sole calculation source.
import { useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { useSelection } from '../management/scope';
import { identityKey, useSession } from '../../app/access';
import { webRequest } from '../../shared/access/operational';
import { Button, ErrorPanel, LoadingPanel } from '../../shared/ui/primitives';
import styles from './integration.module.css';
import { BillingCountryPanel } from './EnrollmentPage';
import { SaasPayments } from './SaasPayments';

const offer = z.object({
  base_reference: z.string().nullable(),
  currency: z.string().nullable(),
  country_code: z.string().nullable(),
  currencies: z.array(z.string()),
  plans: z.array(
    z.object({ id: z.number(), name: z.string(), code: z.string() }),
  ),
  blockers: z.array(z.string()),
  binding_quote: z.literal(false),
  registration_connected: z.boolean(),
  registration_scope: z
    .enum([
      'local_fictitious_documents_only',
      'isolated_staging_fictitious_documents_only',
    ])
    .optional(),
});
const pricing = z.object({
  binding_quote: z.literal(false),
  pricing: z.record(z.unknown()),
});
const amountKeys = [
  'base_price',
  'restaurant_score',
  'loyalty_discount',
  'multi_restaurant_discount',
  'promotion_discount',
  'multi_branch_cost',
  'final_price',
  'payment_adjustment',
  'final_amount_due',
] as const;

export function OwnerOfferPage() {
  const { t } = useTranslation(),
    selection = useSelection(),
    session = useSession();
  const root = `/organizations/${selection.organizationId}/restaurants/${selection.restaurantId}/offer`;
  const query = useQuery({
    queryKey: [...identityKey(session.data), root],
    queryFn: async ({ signal }) => offer.parse(await webRequest(root, signal)),
    retry: false,
  });
  const [plan, setPlan] = useState(''),
    [cycle, setCycle] = useState('monthly'),
    [method, setMethod] = useState('electronic'),
    [currency, setCurrency] = useState(''),
    [busy, setBusy] = useState(false),
    [result, setResult] = useState<z.infer<typeof pricing> | null>(null),
    [failed, setFailed] = useState(false);
  async function simulate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFailed(false);
    setResult(null);
    try {
      setResult(
        pricing.parse(
          await webRequest(root + '/simulation', undefined, 'POST', {
            plan_id: Number(plan),
            billing_cycle: cycle,
            payment_method: method,
            currency: currency || query.data?.currency,
            additional_feature_ids: [],
          }),
        ),
      );
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }
  if (query.isPending) return <LoadingPanel />;
  if (query.isError) return <ErrorPanel error={query.error} />;
  return (
    <section className={styles.panel}>
      <h1>{t('offer.title')}</h1>
      <p>{t('offer.scope')}</p>
      {selection.organizationId !== null && (
        <BillingCountryPanel
          organizationId={selection.organizationId}
          legalEntity=""
        />
      )}
      <p>
        {t('offer.base')}:{' '}
        <bdi>
          {query.data.base_reference} {query.data.currency}
        </bdi>
      </p>
      {query.data.blockers.length > 0 && (
        <>
          <p role="status">{t('offer.blocked')}</p>
          <details>
            <summary>{t('o3.technical')}</summary>
            {query.data.blockers.map((code) => (
              <p key={code}>
                <code>{code}</code>
              </p>
            ))}
          </details>
        </>
      )}
      <form className={styles.form} onSubmit={(e) => void simulate(e)}>
        <label>
          {t('o3.currency')}
          <select
            required
            value={currency || query.data.currency || ''}
            onChange={(event) => setCurrency(event.target.value)}
          >
            <option value="">{t('offer.choose')}</option>
            {query.data.currencies.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('offer.plan')}
          <select
            value={plan}
            onChange={(e) => setPlan(e.target.value)}
            required
            disabled={busy || !query.data.plans.length}
          >
            <option value="">{t('offer.choose')}</option>
            {query.data.plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('offer.cycle')}
          <select
            value={cycle}
            onChange={(e) => setCycle(e.target.value)}
            disabled={busy}
          >
            {['monthly', 'quarterly', 'semiannual', 'yearly'].map((c) => (
              <option key={c} value={c}>
                {t('offer.' + c)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('offer.method')}
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            disabled={busy}
          >
            <option value="electronic">{t('offer.electronic')}</option>
            <option value="cash">{t('offer.cash')}</option>
          </select>
        </label>
        <Button
          disabled={
            busy ||
            !plan ||
            !(currency || query.data.currency) ||
            query.data.blockers.length > 0
          }
        >
          {t('offer.simulate')}
        </Button>
      </form>
      {failed && <p role="alert">{t('offer.blocked')}</p>}
      {result && (
        <div>
          <p>
            {t('followup.paymentRate')}:{' '}
            <bdi>
              {String(
                (result.pricing.parameters as Record<string, unknown>)
                  ?.payment_adjustment_rate ?? '—',
              )}
            </bdi>
          </p>
          <p>
            {t('followup.B')}:{' '}
            <bdi>
              {String(
                (result.pricing.parameters as Record<string, unknown>)?.B ??
                  '—',
              )}{' '}
              {currency || query.data.currency}
            </bdi>
          </p>
          <dl>
            {amountKeys.map((key) => (
              <div key={key}>
                <dt>{t('offer.' + key)}</dt>
                <dd>
                  <bdi>
                    {String(result.pricing[key])}{' '}
                    {currency || query.data.currency}
                  </bdi>
                </dd>
              </div>
            ))}
          </dl>
          <details>
            <summary>{t('pricing.technical')}</summary>
            <pre dir="ltr">
              {JSON.stringify(result.pricing.parameters, null, 2)}
            </pre>
          </details>
        </div>
      )}
      {selection.organizationId !== null && selection.restaurantId !== null && (
        <SaasPayments
          organizationId={selection.organizationId}
          restaurantId={selection.restaurantId}
          planId={plan ? Number(plan) : null}
          cycle={cycle}
          currency={currency || query.data.currency}
        />
      )}
    </section>
  );
}
