import { useState, type ReactElement } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { identityKey, useAdapter, useSession } from '../../app/access';
import { AccessError } from '../../shared/access/contracts';
import {
  platformSectionPermission,
  type PlatformSection,
} from '../../shared/office/contracts';
import {
  Badge,
  Button,
  ErrorPanel,
  LoadingPanel,
} from '../../shared/ui/primitives';
import { useBusinessFormatting } from '../management/scope';
import { OfficeEmpty, PaymentDetails } from '../office/OfficePages';
import common from '../management/management.module.css';
import styles from '../office/office.module.css';
import { VerificationSimulation } from './VerificationSimulation';

/** No tenant discovery/read, identity linkage, approval or money mutation is exposed here. */
export function PlatformRecordsPage({
  section,
}: {
  section: PlatformSection;
}): ReactElement {
  const { t } = useTranslation();
  const session = useSession();
  const adapter = useAdapter();
  const { date } = useBusinessFormatting();
  const [filter, setFilter] = useState('all');
  const allowed =
    session.data?.area === 'platform' &&
    session.data.platformPermissions.includes(
      platformSectionPermission[section],
    );
  const query = useQuery({
    queryKey: [...identityKey(session.data), 'platform', section],
    queryFn: ({ signal }) => adapter.platformRecords(section, signal),
    enabled: allowed === true,
  });
  if (!allowed) return <ErrorPanel error={new AccessError('noAccess')} />;
  if (query.isError)
    return (
      <ErrorPanel error={query.error} retry={() => void query.refetch()} />
    );
  if (query.isPending) return <LoadingPanel />;
  const rows = query.data.filter(
    (row) => filter === 'all' || row.status === filter,
  );
  return (
    <>
      <h1>{t(`nav.${section}`)}</h1>
      <p className={styles.note}>{t(`office.${section}Help`)}</p>
      <p className={styles.note}>{t('office.boundary')}</p>
      <div className={common.actions}>
        <Badge>
          {t('office.supervision')} : {query.data.length}
        </Badge>
        <Button
          variant="quiet"
          disabled={query.isFetching}
          onClick={() => void query.refetch()}
        >
          {t('office.refreshList')}
        </Button>
      </div>
      {section !== 'audit' && (
        <label className={`${common.field} ${styles.filters}`}>
          {t('office.status')}
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          >
            {['all', 'pending', 'approved', 'rejected'].map((value) => (
              <option key={value} value={value}>
                {t(`office.${value}`)}
              </option>
            ))}
          </select>
        </label>
      )}
      <div className={styles.list}>
        {rows.length === 0 ? (
          <OfficeEmpty />
        ) : (
          rows.map((row) => (
            <article key={row.id} className={common.panel}>
              <h2>
                <bdi>{row.label}</bdi>
              </h2>
              <Badge>{t(`office.${row.status}`)}</Badge>
              <p>
                <time dateTime={row.at}>{date(row.at)}</time>
              </p>
              <details className={styles.details}>
                <summary>{t('office.details')}</summary>
                <p>
                  {t('office.identifier')} : <bdi>{row.id}</bdi>
                </p>
                {row.payment && <PaymentDetails payment={row.payment} />}
                {section === 'receipts' &&
                  row.payment &&
                  adapter.mode === 'synthetic' && (
                    <VerificationSimulation payment={row.payment} />
                  )}
                {section !== 'audit' && (
                  <>
                    <div className={common.actions}>
                      <Button disabled>{t('office.approve')}</Button>
                      <Button variant="secondary" disabled>
                        {t('office.reject')}
                      </Button>
                    </div>
                    <p className={styles.note}>
                      {t('office.integrationRequired')}
                    </p>
                  </>
                )}
              </details>
            </article>
          ))
        )}
      </div>
    </>
  );
}

export function RequestsPage(): ReactElement {
  return <PlatformRecordsPage section="requests" />;
}
export function ReceiptsPage(): ReactElement {
  return <PlatformRecordsPage section="receipts" />;
}
export function AuditPage(): ReactElement {
  return <PlatformRecordsPage section="audit" />;
}
