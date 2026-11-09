// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Version the existing reminder calendar; never dispatch notifications or infer renewal.
import { useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { identityKey, useSession } from '../../app/access';
import { webRequest } from '../../shared/access/operational';
import { Button, ErrorPanel, LoadingPanel } from '../../shared/ui/primitives';
import styles from './integration.module.css';
import { PricingHistory } from './PricingHistory';
const settings = z.object({
  days: z.array(z.number().int().nonnegative()),
  sha256: z.string(),
  responsible_configured: z.boolean(),
  applies_to: z.literal('new_schedules_only'),
  delivery_active: z.literal(false),
});
export function ReminderEditor() {
  const { t } = useTranslation(),
    session = useSession();
  const query = useQuery({
    queryKey: [...identityKey(session.data), 'reminder-policy'],
    queryFn: async ({ signal }) =>
      settings.parse(await webRequest('/platform/pricing/reminders', signal)),
    retry: false,
  });
  const [days, setDays] = useState(''),
    [reason, setReason] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(false),
    [saved, setSaved] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!query.data) return;
    setBusy(true);
    setError(false);
    setSaved(false);
    try {
      const values = days.split(',').map((s) => s.trim());
      if (values.some((s) => !/^\d+$/.test(s)))
        throw new Error('integer_days_required');
      await webRequest('/platform/pricing/reminders', undefined, 'POST', {
        days: values.map(Number),
        reason,
        expected_sha256: query.data.sha256,
      });
      await query.refetch();
      setDays('');
      setReason('');
      setSaved(true);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className={styles.record}>
      <h2>{t('reminders.title')}</h2>
      <p>{t('reminders.scope')}</p>
      {query.isPending ? (
        <LoadingPanel />
      ) : query.isError ? (
        <ErrorPanel error={query.error} />
      ) : (
        <>
          <p data-testid="reminder-current">
            {t('reminders.current')}: <bdi>{query.data.days.join(', ')}</bdi>
          </p>
          {!query.data.responsible_configured && (
            <p>{t('reminders.missingResponsible')}</p>
          )}
          <form
            className={styles.form}
            onSubmit={(e) => void submit(e)}
            aria-label={t('reminders.title')}
          >
            <label>
              {t('reminders.days')}
              <input
                name="reminderDays"
                value={days}
                onChange={(e) => setDays(e.target.value)}
                required
                disabled={busy}
              />
            </label>
            <label>
              {t('pricing.reason')}
              <input
                name="reminderReason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                required
                disabled={busy}
              />
            </label>
            <Button disabled={busy}>{t('reminders.save')}</Button>
          </form>
          {error && <p role="alert">{t('pricing.refused')}</p>}
          {saved && <p role="status">{t('pricing.saved')}</p>}
          <PricingHistory path="reminders/history" />
        </>
      )}
    </section>
  );
}
