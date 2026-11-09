// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useState, type ReactElement } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { CalendarDays, UtensilsCrossed, ReceiptText } from 'lucide-react';
import { useAdapter, identityKey, useSession } from '../../app/access';
import { useRestaurantContext, positiveId } from '../management/scope';
import { localized } from '../../shared/i18n';
import { Button, ErrorPanel, LoadingPanel } from '../../shared/ui/primitives';
import { AccessError } from '../../shared/access/contracts';
import {
  OperationalBoard,
  RequestBadges,
} from '../../shared/dining/OperationalBoard';
import { reviewTablePresentation } from './reviewPresentation';
import type { DiningReviewCommand } from '../../shared/dining/contracts';
import shared from '../management/management.module.css';
import styles from './dining.module.css';

/** Review-only writes remain explicit simulations in the injected adapter. */
export function DiningPage(): ReactElement {
  const { t, i18n } = useTranslation();
  const adapter = useAdapter();
  const session = useSession();
  const { scope, company } = useRestaurantContext();
  const [branchId, setBranchId] = useState<number | null>(null);
  const [day, setDay] = useState('2026-11-03');
  const client = useQueryClient();
  const root = [
    ...identityKey(session.data),
    'dining',
    scope.organizationId,
    scope.restaurantId,
  ] as const;
  const branches = useQuery({
    queryKey: [...root, 'branches'],
    queryFn: ({ signal }) => adapter.diningBranches(scope, signal),
  });
  const queryKey = [...root, branchId, day] as const;
  const review = useQuery({
    queryKey,
    enabled: branchId !== null && day.length === 10,
    queryFn: ({ signal }) =>
      adapter.diningWorkspace({ ...scope, branchId: branchId! }, day, signal),
  });
  const simulation = useMutation({
    mutationFn: (command: DiningReviewCommand) =>
      adapter.simulateDining(
        { ...scope, branchId: branchId! },
        command,
        new AbortController().signal,
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: root }),
  });
  if (!company.permissions.includes('tenant.restaurants.read'))
    return <ErrorPanel error={new AccessError('noAccess')} />;
  if (branches.isPending) return <LoadingPanel />;
  if (branches.error) return <ErrorPanel error={branches.error} />;
  const data = review.data;
  const invoice = data?.invoice;
  return (
    <>
      <div className={shared.titleRow}>
        <div>
          <h1>
            <UtensilsCrossed aria-hidden="true" size={25} /> {t('dining.title')}
          </h1>
          <p className={shared.intro}>{t('dining.notice')}</p>
        </div>
      </div>
      <div className={styles.filters}>
        <label>
          {t('dining.branch')}
          <select
            value={branchId ?? ''}
            onChange={(event) => {
              setBranchId(positiveId(event.target.value));
              simulation.reset();
            }}
          >
            <option value="">{t('dining.choose')}</option>
            {branches.data?.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {localized(branch.name)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('dining.date')}
          <input
            type="date"
            value={day}
            onChange={(event) => setDay(event.target.value)}
          />
        </label>
        {data && <span dir="ltr">{data.timezone}</span>}
      </div>
      {review.isFetching && branchId !== null && <LoadingPanel />}
      {review.error && <ErrorPanel error={review.error} />}
      {simulation.error && <ErrorPanel error={simulation.error} />}
      {simulation.isSuccess && <p role="status">{t('dining.saved')}</p>}
      {data && (
        <>
          {!data.capabilities.includes('service') && (
            <p>{t('dining.readOnly')}</p>
          )}
          <OperationalBoard
            tables={reviewTablePresentation(
              data,
              i18n.language === 'ar'
                ? 'ar'
                : i18n.language === 'en'
                  ? 'en'
                  : 'fr',
            )}
            day={day}
            timezone={data.timezone}
            actions={(row) => {
              const table = data.tables.find((table) => table.id === row.id);
              return table &&
                data.capabilities.includes('clean') &&
                ['occupied', 'dirty'].includes(table.physical) ? (
                <Button
                  variant="secondary"
                  disabled={simulation.isPending}
                  onClick={() =>
                    simulation.mutate({
                      kind:
                        table.physical === 'occupied' ? 'departure' : 'clean',
                      tableId: table.id,
                    })
                  }
                >
                  {t(
                    table.physical === 'occupied'
                      ? 'dining.departure'
                      : 'dining.clean',
                  )}
                </Button>
              ) : (
                <span>{t('ops.readOnly')}</span>
              );
            }}
          />
          <section className={shared.panel}>
            <h2>
              <CalendarDays aria-hidden="true" size={21} />{' '}
              {t('dining.requests')}
            </h2>
            <div
              className={styles.scroll}
              tabIndex={0}
              role="region"
              aria-label={t('dining.requests')}
            >
              <table>
                <thead>
                  <tr>
                    {[
                      'reference',
                      'party',
                      'slot',
                      'status',
                      'proof',
                      'delivery',
                    ].map((key) => (
                      <th scope="col" key={key}>
                        {t(`dining.${key}`)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.requests.map((request) => (
                    <tr key={request.id}>
                      <th scope="row">
                        <bdi>{request.reference}</bdi>
                      </th>
                      <td>{request.party}</td>
                      <td>
                        <bdi>
                          {request.startsAt}–{request.endsAt}
                        </bdi>
                      </td>
                      <td>
                        <RequestBadges
                          status={request.status}
                          badges={
                            request.status === 'pending' && !request.humanProof
                              ? ['humanPending']
                              : request.status === 'held'
                                ? ['hold']
                                : []
                          }
                          timezone={data.timezone}
                        />
                      </td>
                      <td>
                        {t(request.humanProof ? 'dining.yes' : 'dining.no')}
                      </td>
                      <td>
                        {t(
                          request.delivery === 'delivered'
                            ? 'dining.delivered'
                            : 'dining.notDelivered',
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          {invoice && (
            <section className={shared.panel}>
              <h2>
                <ReceiptText aria-hidden="true" size={21} />{' '}
                {t('dining.invoice')} · {t(`dining.${invoice.status}`)}
              </h2>
              <p>{t('dining.provenance')}</p>
              <dl className={styles.amounts}>
                {(['total', 'received', 'allocated', 'balance'] as const).map(
                  (key) => (
                    <div key={key}>
                      <dt>{t(`dining.${key}`)}</dt>
                      <dd>
                        <bdi>
                          {invoice[key]} {invoice.currency}
                        </bdi>
                      </dd>
                    </div>
                  ),
                )}
              </dl>
              <p>{t('dining.accounting')}</p>
              {data.capabilities.includes('service') && (
                <Button
                  disabled={
                    simulation.isPending || invoice.status === 'finalized'
                  }
                  onClick={() =>
                    simulation.mutate({
                      kind: 'finalizeInvoice',
                      invoiceId: invoice!.id,
                    })
                  }
                >
                  {t('dining.finalize')}
                </Button>
              )}
            </section>
          )}
        </>
      )}
    </>
  );
}
