import type { ReactElement } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAdapter } from '../../app/access';
import { ErrorPanel, LoadingPanel } from '../../shared/ui/primitives';
import { useRestaurantContext } from '../management/scope';
import common from '../management/management.module.css';
import styles from './office.module.css';

/** Text values remain readable without color, chart rendering or pointer interaction. */
function BarChart({
  title,
  rows,
}: {
  title: string;
  rows: readonly { id: string; label: string; count: number }[];
}): ReactElement {
  const { i18n, t } = useTranslation();
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  return (
    <figure className={`${common.panel} ${styles.chart}`} aria-label={title}>
      <figcaption>
        <h2>{title}</h2>
      </figcaption>
      {rows.length === 0 ? (
        <p>{t('office.empty')}</p>
      ) : (
        <ul className={styles.bars}>
          {rows.map((row) => {
            const proportion = total === 0 ? 0 : row.count / total;
            return (
              <li key={row.id}>
                <div className={styles.barLabel}>
                  <span dir="auto">{row.label}</span>
                  <span className={styles.barNumbers}>
                    <strong>
                      {new Intl.NumberFormat(i18n.language).format(row.count)}
                    </strong>
                    <small>
                      <bdi>
                        {new Intl.NumberFormat(i18n.language, {
                          style: 'percent',
                          maximumFractionDigits: 1,
                        }).format(proportion)}
                      </bdi>
                    </small>
                  </span>
                </div>
                <div className={styles.barTrack} aria-hidden="true">
                  <div
                    className={styles.barFill}
                    data-proportion={proportion * 100}
                    style={{ inlineSize: `${proportion * 100}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </figure>
  );
}

export function ReportVisuals(): ReactElement {
  const context = useRestaurantContext();
  const adapter = useAdapter();
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: [...context.queryKey, 'report-breakdown'],
    queryFn: ({ signal }) => adapter.reportBreakdown(context.scope, signal),
    enabled: context.company.permissions.includes('tenant.reports.read'),
  });
  if (query.isError)
    return (
      <ErrorPanel error={query.error} retry={() => void query.refetch()} />
    );
  if (query.isPending) return <LoadingPanel />;
  return (
    <>
      <div className={styles.charts}>
        <BarChart
          title={t('office.orderChart')}
          rows={query.data.orderCounts.map((r) => ({
            id: r.status,
            label: t(`business.status.${r.status}`),
            count: r.count,
          }))}
        />
        <BarChart
          title={t('office.categoryChart')}
          rows={query.data.categoryCounts.map((r) => ({
            id: String(r.id),
            label: r.name,
            count: r.count,
          }))}
        />
      </div>
      <p className={styles.note}>{t('office.chartNote')}</p>
    </>
  );
}
