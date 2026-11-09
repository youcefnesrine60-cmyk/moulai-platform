// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Reusable persisted administrative history, protected by the same server permission as each editor.
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { identityKey, useSession } from '../../app/access';
import { webRequest } from '../../shared/access/operational';
import { LoadingPanel, ErrorPanel } from '../../shared/ui/primitives';
const auditEntry = z.object({
  id: z.number(),
  author_admin_id: z.number(),
  author_name: z.string().nullable(),
  action: z.string(),
  recorded_at: z.string(),
  details: z.record(z.unknown()),
});

/** A separate authenticated read shows committed evidence, never frontend-invented before/after data. */
export function PricingHistory({ path }: { path: string }) {
  const { t, i18n } = useTranslation(),
    session = useSession();
  const [open, setOpen] = useState(false);
  const query = useQuery({
    queryKey: [...identityKey(session.data), 'pricing-history', path],
    queryFn: async ({ signal }) =>
      z
        .array(auditEntry)
        .parse(await webRequest('/platform/pricing/' + path, signal)),
    enabled: open,
    retry: false,
    staleTime: 0,
  });
  return (
    <details onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>{t('pricing.history')}</summary>
      {open &&
        (query.isPending ? (
          <LoadingPanel />
        ) : query.isError ? (
          <ErrorPanel error={query.error} />
        ) : (
          <ol>
            {query.data.map((entry) => (
              <li key={entry.id}>
                <p>
                  <bdi>{entry.author_name || t('pricing.unspecified')}</bdi> ·{' '}
                  {t('pricing.action.' + entry.action.replaceAll('.', '_'), {
                    defaultValue: t('pricing.actionUnknown'),
                  })}{' '}
                  ·{' '}
                  <bdi>
                    {new Date(entry.recorded_at).toLocaleString(i18n.language, {
                      timeZone: 'UTC',
                    })}{' '}
                    UTC
                  </bdi>
                </p>
                <details>
                  <summary>{t('pricing.technical')}</summary>
                  <pre dir="ltr">{JSON.stringify(entry.details, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ol>
        ))}
    </details>
  );
}
