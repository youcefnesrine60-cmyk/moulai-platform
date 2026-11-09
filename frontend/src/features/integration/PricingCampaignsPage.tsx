// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — actual persisted SaaS campaigns; all mutations require exact server permission.
import { useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { identityKey, useSession } from '../../app/access';
import { webRequest } from '../../shared/access/operational';
import { Button, ErrorPanel, LoadingPanel } from '../../shared/ui/primitives';
import styles from './integration.module.css';
import { campaignDateInput, campaignDateValue } from './campaignDates';
import { ReminderEditor } from './ReminderEditor';
import { PricingHistory } from './PricingHistory';

const campaign = z.object({
  id: z.number(),
  name: z.string(),
  discount_percent: z.string(),
  starts_at: z.string().nullable(),
  expires_at: z.string().nullable(),
  priority: z.number(),
  active: z.boolean(),
  state: z.enum(['draft', 'published', 'deactivated', 'legacy']),
  sha256: z.string(),
  restaurant_id: z.number().nullable(),
  owner_id: z.number().nullable(),
  plan_id: z.number().nullable(),
});
type Campaign = z.infer<typeof campaign>;
const initial = {
  name: '',
  discount_percent: '',
  starts_at: '',
  expires_at: '',
  priority: '0',
  reason: '',
};

/** Never reproduce the price formula or update retained subscription snapshots here. */
export function PricingCampaignsPage() {
  const { t, i18n } = useTranslation(),
    session = useSession();
  const query = useQuery({
    queryKey: [...identityKey(session.data), 'saas-campaigns'],
    queryFn: async ({ signal }) =>
      z
        .array(campaign)
        .parse(await webRequest('/platform/pricing/campaigns', signal)),
    retry: false,
  });
  const [baseContext, setBaseContext] = useState('DZ:DZD');
  const contexts = useQuery({
    queryKey: [...identityKey(session.data), 'base-contexts'],
    queryFn: async () =>
      z
        .array(z.object({ country_code: z.string(), currency: z.string() }))
        .parse(await webRequest('/platform/pricing/base-contexts')),
    retry: false,
  });
  const countryCode = baseContext.slice(0, baseContext.indexOf(':'));
  const currencyCode = baseContext.slice(baseContext.indexOf(':') + 1);
  const base = useQuery({
    queryKey: [...identityKey(session.data), 'saas-base', baseContext],
    queryFn: async ({ signal }) =>
      z
        .object({
          amount: z.string(),
          country_code: z.string(),
          currency: z.string(),
          revision: z.string(),
          sha256: z.string(),
        })
        .parse(
          await webRequest(
            `/platform/pricing/base?country_code=${encodeURIComponent(countryCode)}&currency=${encodeURIComponent(currencyCode)}`,
            signal,
          ),
        ),
    retry: false,
  });
  const [baseAmount, setBaseAmount] = useState(''),
    [baseReason, setBaseReason] = useState('');
  const [values, setValues] = useState(initial),
    [editing, setEditing] = useState<Campaign | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(false),
    [saved, setSaved] = useState(false);
  async function send(body: unknown) {
    if (busy) return;
    setBusy(true);
    setError(false);
    setSaved(false);
    try {
      await webRequest('/platform/pricing/campaigns', undefined, 'POST', body);
      await query.refetch();
      setEditing(null);
      setValues(initial);
      setSaved(true);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  const submit = (event: FormEvent) => {
    event.preventDefault();
    let starts: string, expires: string;
    try {
      starts = campaignDateValue(values.starts_at, editing?.starts_at ?? null);
      expires = campaignDateValue(
        values.expires_at,
        editing?.expires_at ?? null,
      );
    } catch {
      setError(true);
      return;
    }
    void send({
      operation: editing ? 'update' : 'create',
      ...(editing
        ? { identifier: editing.id, expected_sha256: editing.sha256 }
        : {}),
      reason: values.reason,
      values: {
        name: values.name,
        discount_percent: values.discount_percent,
        priority: Number(values.priority),
        starts_at: starts,
        expires_at: expires,
        restaurant_id: null,
        owner_id: null,
        plan_id: null,
      },
    });
  };
  const saveBase = async (event: FormEvent) => {
    event.preventDefault();
    if (busy || !base.data) return;
    setBusy(true);
    setError(false);
    setSaved(false);
    try {
      await webRequest('/platform/pricing/base', undefined, 'POST', {
        amount: baseAmount,
        country_code: countryCode,
        currency: currencyCode,
        expected_sha256: base.data.sha256,
        effective: 'on_commit',
        reason: baseReason,
      });
      await base.refetch();
      setBaseAmount('');
      setBaseReason('');
      setSaved(true);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  };
  if (query.isPending) return <LoadingPanel />;
  if (query.isError) return <ErrorPanel error={query.error} />;
  return (
    <section className={styles.panel}>
      <h1>{t('pricing.campaigns')}</h1>
      <p>{t('pricing.scope')}</p>
      <p>{t('integration.notice')}</p>
      <section className={styles.record}>
        <h2>{t('pricing.base')}</h2>
        <label className={styles.field}>
          {t('o3.countryTitle')} / {t('o3.currency')}
          <select
            value={baseContext}
            onChange={(event) => {
              setBaseContext(event.target.value);
              setBaseAmount('');
              setBaseReason('');
            }}
            disabled={busy || !contexts.data?.length}
          >
            {contexts.data?.map((context) => (
              <option
                key={context.country_code + context.currency}
                value={context.country_code + ':' + context.currency}
              >
                {context.country_code} / {context.currency}
              </option>
            ))}
          </select>
        </label>
        <p>{t('pricing.baseScope')}</p>
        {base.isPending ? (
          <LoadingPanel />
        ) : base.isError ? (
          <ErrorPanel error={base.error} />
        ) : (
          <>
            <p>
              <strong>
                <bdi>
                  {base.data.amount} {base.data.currency}
                </bdi>
              </strong>
            </p>
            <details>
              <summary>{t('pricing.technical')}</summary>
              <bdi>{base.data.revision}</bdi>
            </details>
            <PricingHistory path="base/history" />
            <form
              onSubmit={(event) => void saveBase(event)}
              className={styles.form}
              aria-label={t('pricing.base')}
            >
              <label>
                {t('pricing.newBase')}
                <input
                  name="baseAmount"
                  value={baseAmount}
                  onChange={(e) => setBaseAmount(e.target.value)}
                  required
                  pattern="(?:0|[1-9][0-9]{0,11})(?:[.][0-9]{1,2})?"
                  inputMode="decimal"
                  disabled={busy}
                />
              </label>
              <label>
                {t('pricing.reason')}
                <input
                  name="baseReason"
                  value={baseReason}
                  onChange={(e) => setBaseReason(e.target.value)}
                  required
                  disabled={busy}
                />
              </label>
              <Button disabled={busy}>{t('pricing.applyNow')}</Button>
            </form>
          </>
        )}
      </section>
      <p>{t('pricing.rules')}</p>
      <ReminderEditor />
      {error && <p role="alert">{t('pricing.refused')}</p>}
      {saved && <p role="status">{t('pricing.saved')}</p>}
      <form
        onSubmit={submit}
        className={styles.form}
        aria-label={t('pricing.draft')}
      >
        <h2>{t('pricing.draft')}</h2>
        <p>{t('pricing.targetAll')}</p>
        {(
          [
            'name',
            'discount_percent',
            'starts_at',
            'expires_at',
            'priority',
            'reason',
          ] as const
        ).map((name) => (
          <label key={name}>
            {t('pricing.' + name)}
            <input
              name={name}
              type={
                name.endsWith('_at')
                  ? 'datetime-local'
                  : name === 'priority'
                    ? 'number'
                    : 'text'
              }
              required
              disabled={busy}
              value={values[name]}
              onChange={(event) =>
                setValues({ ...values, [name]: event.target.value })
              }
              {...(name === 'priority' ? { min: 0, step: 1 } : {})}
              {...(name.endsWith('_at') ? { step: '0.001' } : {})}
              {...(name === 'discount_percent'
                ? {
                    pattern: '(?:0|[1-9][0-9]{0,2})(?:[.][0-9]{1,8})?',
                    inputMode: 'decimal' as const,
                  }
                : {})}
            />
          </label>
        ))}
        <p>{t('pricing.utcTime')}</p>
        <Button type="submit" disabled={busy}>
          {t(editing ? 'pricing.update' : 'pricing.create')}
        </Button>
        {editing && (
          <Button
            variant="secondary"
            type="button"
            onClick={() => {
              setEditing(null);
              setValues(initial);
            }}
          >
            {t('pricing.cancelEdit')}
          </Button>
        )}
      </form>
      {query.data.length === 0 && <p>{t('pricing.empty')}</p>}
      <div className={styles.campaigns}>
        {query.data.map((row) => (
          <article key={row.id} className={styles.record}>
            <h2>
              <bdi>{row.name}</bdi>
            </h2>
            <p>
              {t('pricing.' + row.state)} · <bdi>{row.discount_percent}%</bdi> ·{' '}
              {t('pricing.priority')}: {row.priority}
            </p>
            <p>
              {t('pricing.starts_at')}:{' '}
              <bdi>
                {row.starts_at
                  ? new Date(row.starts_at).toLocaleString(i18n.language, {
                      timeZone: 'UTC',
                    }) + ' UTC'
                  : t('pricing.unspecified')}
              </bdi>
            </p>
            <p>
              {t('pricing.expires_at')}:{' '}
              <bdi>
                {row.expires_at
                  ? new Date(row.expires_at).toLocaleString(i18n.language, {
                      timeZone: 'UTC',
                    }) + ' UTC'
                  : t('pricing.unspecified')}
              </bdi>
            </p>
            <p>
              {row.restaurant_id || row.owner_id || row.plan_id
                ? t('pricing.targetSpecific')
                : t('pricing.targetAll')}
            </p>
            <div className={styles.actions}>
              {row.state === 'draft' && (
                <>
                  <Button
                    type="button"
                    disabled={
                      busy ||
                      Boolean(row.restaurant_id || row.owner_id || row.plan_id)
                    }
                    onClick={() => {
                      setEditing(row);
                      setValues({
                        name: row.name,
                        discount_percent: row.discount_percent,
                        starts_at: campaignDateInput(row.starts_at),
                        expires_at: campaignDateInput(row.expires_at),
                        priority: String(row.priority),
                        reason: '',
                      });
                    }}
                  >
                    {t('pricing.edit')}
                  </Button>
                  <Button
                    type="button"
                    disabled={busy || !values.reason.trim()}
                    onClick={() =>
                      void send({
                        operation: 'publish',
                        identifier: row.id,
                        expected_sha256: row.sha256,
                        reason: values.reason,
                      })
                    }
                  >
                    {t('pricing.publish')}
                  </Button>
                </>
              )}
              {row.state === 'published' && (
                <Button
                  type="button"
                  variant="secondary"
                  disabled={busy || !values.reason.trim()}
                  onClick={() =>
                    void send({
                      operation: 'deactivate',
                      identifier: row.id,
                      expected_sha256: row.sha256,
                      reason: values.reason,
                    })
                  }
                >
                  {t('pricing.deactivate')}
                </Button>
              )}
            </div>
            <details>
              <summary>{t('pricing.technical')}</summary>
              <p>
                <bdi>
                  #{row.id} · restaurant={row.restaurant_id ?? '—'} / owner=
                  {row.owner_id ?? '—'} / plan={row.plan_id ?? '—'}
                </bdi>
              </p>
              <p>
                <bdi>{row.sha256}</bdi>
              </p>
            </details>
            <PricingHistory path={`campaigns/${row.id}/history`} />
          </article>
        ))}
      </div>
      <p>{t('pricing.reasonHint')}</p>
    </section>
  );
}
