import { useState, type ReactElement } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  ReceiptText,
  Package,
  ClipboardList,
  type LucideIcon,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { useAdapter } from '../../app/access';
import { AccessError } from '../../shared/access/contracts';
import type { PaymentView } from '../../shared/office/contracts';
import { receiptDraftSchema } from '../../shared/office/validation';
import {
  Badge,
  Button,
  ErrorPanel,
  LoadingPanel,
} from '../../shared/ui/primitives';
import {
  useBusinessFormatting,
  useRestaurantContext,
} from '../management/scope';
import common from '../management/management.module.css';
import styles from './office.module.css';
import { ReportVisuals } from './ReportVisuals';
import { BillingWorkspacePanel } from './BillingWorkspacePanel';

export function OfficeEmpty(): ReactElement {
  const { t } = useTranslation();
  return (
    <section className={common.empty}>
      <h2>{t('office.empty')}</h2>
      <p>{t('office.emptyHelp')}</p>
    </section>
  );
}

/** Long semantic values use normal word boundaries; a missing metric is never a zero. */
function MetricCard({
  label,
  value,
  icon: Icon,
  unavailable = false,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  unavailable?: boolean;
}): ReactElement {
  return (
    <section className={`${common.panel} ${styles.metricCard}`}>
      <Icon size={22} aria-hidden="true" />
      <h3>{label}</h3>
      <strong
        className={`${styles.metric} ${unavailable ? styles.metricText : ''}`}
        data-metric-state={unavailable ? 'unavailable' : 'value'}
      >
        {value}
      </strong>
    </section>
  );
}

/** Both route and adapter check existing permissions; no company-wide financial aggregation. */
export function ReportsPage(): ReactElement {
  const context = useRestaurantContext();
  const adapter = useAdapter();
  const { t, i18n } = useTranslation();
  const { money } = useBusinessFormatting();
  const allowed = context.company.permissions.includes('tenant.reports.read');
  const query = useQuery({
    queryKey: [...context.queryKey, 'reports'],
    queryFn: ({ signal }) => adapter.report(context.scope, signal),
    enabled: allowed,
  });
  if (!allowed) return <ErrorPanel error={new AccessError('noAccess')} />;
  if (query.isError)
    return (
      <ErrorPanel error={query.error} retry={() => void query.refetch()} />
    );
  if (query.isPending) return <LoadingPanel />;
  const data = query.data;
  const number = (n: number) => new Intl.NumberFormat(i18n.language).format(n);
  return (
    <>
      <h1>{t('nav.reports')}</h1>
      <p className={styles.note}>{t('office.reportsIntro')}</p>
      <p className={styles.note}>{t('office.boundary')}</p>
      {!data ? (
        <OfficeEmpty />
      ) : (
        <div className={styles.indicatorGroups}>
          <section aria-labelledby="activity-indicators">
            <h2 id="activity-indicators">{t('office.activityIndicators')}</h2>
            <div className={styles.activityCards}>
              <MetricCard
                label={t('office.orders')}
                value={number(data.totalOrders)}
                icon={ClipboardList}
              />
              <MetricCard
                label={t('office.products')}
                value={number(data.totalProducts)}
                icon={Package}
              />
              <MetricCard
                label={t('office.categories')}
                value={number(data.totalCategories)}
                icon={BarChart3}
              />
            </div>
          </section>
          <section aria-labelledby="additional-indicators">
            <h2 id="additional-indicators">
              {t('office.additionalIndicators')}
            </h2>
            <div className={styles.additionalCards}>
              <MetricCard
                label={t('office.average')}
                value={
                  data.averageOrderValue === null
                    ? t('office.unavailable')
                    : money(data.averageOrderValue)
                }
                icon={ReceiptText}
                unavailable={data.averageOrderValue === null}
              />
              <MetricCard
                label={t('office.growth')}
                value={
                  data.monthlyGrowth === null
                    ? t('office.unavailable')
                    : new Intl.NumberFormat(i18n.language, {
                        style: 'percent',
                        maximumFractionDigits: 1,
                      }).format(data.monthlyGrowth / 100)
                }
                icon={BarChart3}
                unavailable={data.monthlyGrowth === null}
              />
            </div>
          </section>
        </div>
      )}
      <p className={styles.note}>{t('office.metricsNote')}</p>
      {data && <ReportVisuals />}
    </>
  );
}

/** Shared safe metadata presentation, also used by the separate platform reviewer. */
export function PaymentDetails({
  payment,
}: {
  payment: PaymentView;
}): ReactElement {
  const { t } = useTranslation();
  const { money, date } = useBusinessFormatting();
  return (
    <dl className={styles.definition}>
      <dt>{t('office.amount')}</dt>
      <dd>{money(payment.amount)}</dd>
      <dt>{t('office.method')}</dt>
      <dd>{t(`office.${payment.method}`)}</dd>
      <dt>{t('office.status')}</dt>
      <dd>{t(`office.${payment.status}`)}</dd>
      <dt>{t('office.created')}</dt>
      <dd>
        <time dateTime={payment.createdAt}>{date(payment.createdAt)}</time>
      </dd>
      <dt>{t('office.receiptStatus')}</dt>
      <dd>
        {payment.receipt
          ? t(`office.${payment.receipt.reviewStatus}`)
          : t('office.noReceipt')}
      </dd>
      {payment.receipt && (
        <>
          <dt>{t('office.reference')}</dt>
          <dd>
            <bdi>{payment.receipt.reference}</bdi>
          </dd>
        </>
      )}
    </dl>
  );
}

/** Preview only: no file reads, object URLs, upload adapter or payment mutation exists. */
function ReceiptDraft({ payment }: { payment: PaymentView }): ReactElement {
  const { t } = useTranslation();
  const { register, getValues } = useForm<{ reference: string }>({
    defaultValues: { reference: '' },
  });
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState(false);
  const [preview, setPreview] = useState<{
    reference: string;
    name: string;
  } | null>(null);
  const prefix = `receipt-${payment.id}`;
  return (
    <form
      className={styles.form}
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const parsed = receiptDraftSchema.safeParse({
          reference: getValues('reference'),
          file: file
            ? { name: file.name, type: file.type, size: file.size }
            : null,
        });
        setError(!parsed.success);
        if (parsed.success)
          setPreview({
            reference: parsed.data.reference,
            name: parsed.data.file.name,
          });
      }}
    >
      <h3>{t('office.localDraft')}</h3>
      <div hidden={preview !== null}>
        <label className={common.field} htmlFor={`${prefix}-reference`}>
          {t('office.reference')}
          <input
            id={`${prefix}-reference`}
            dir="auto"
            {...register('reference')}
            maxLength={120}
            aria-invalid={error}
            aria-describedby={error ? `${prefix}-error` : undefined}
          />
        </label>
        <label className={common.field} htmlFor={`${prefix}-file`}>
          {t('office.file')}
          <input
            id={`${prefix}-file`}
            type="file"
            accept="image/png,image/jpeg,application/pdf"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            aria-invalid={error}
            aria-describedby={`${prefix}-help${error ? ` ${prefix}-error` : ''}`}
          />
        </label>
        <p id={`${prefix}-help`} className={styles.note}>
          {t('office.fileNote')}
        </p>
        {error && (
          <p id={`${prefix}-error`} role="alert" className={common.fieldError}>
            {t('office.invalid')}
          </p>
        )}
        <Button type="submit">{t('office.preview')}</Button>
      </div>
      {preview && (
        <section aria-label={t('office.previewReady')}>
          <p role="status">{t('office.previewReady')}</p>
          <p>
            <bdi>{preview.reference}</bdi> · <bdi>{preview.name}</bdi>
          </p>
          <div className={common.actions}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setPreview(null)}
            >
              {t('office.edit')}
            </Button>
            <Button type="button" disabled>
              {t('office.send')}
            </Button>
          </div>
          <p className={styles.note}>{t('office.integrationRequired')}</p>
        </section>
      )}
    </form>
  );
}

export function BillingPage(): ReactElement {
  const context = useRestaurantContext();
  const adapter = useAdapter();
  const { t } = useTranslation();
  const { money, date } = useBusinessFormatting();
  const [status, setStatus] = useState('all');
  const allowed = context.company.permissions.includes('tenant.billing.read');
  const query = useQuery({
    queryKey: [...context.queryKey, 'payments'],
    queryFn: ({ signal }) => adapter.payments(context.scope, signal),
    enabled: allowed,
  });
  if (!allowed) return <ErrorPanel error={new AccessError('noAccess')} />;
  if (query.isError)
    return (
      <ErrorPanel error={query.error} retry={() => void query.refetch()} />
    );
  if (query.isPending) return <LoadingPanel />;
  const filtered = query.data.filter(
    (row) => status === 'all' || row.status === status,
  );
  return (
    <>
      <h1>{t('nav.billing')}</h1>
      <p className={styles.note}>{t('office.billingIntro')}</p>
      <p className={styles.note}>{t('office.boundary')}</p>
      <BillingWorkspacePanel />
      <label className={`${common.field} ${styles.filters}`}>
        {t('office.status')}
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          {['all', 'pending', 'paid', 'failed', 'cancelled', 'refunded'].map(
            (value) => (
              <option value={value} key={value}>
                {t(`office.${value}`)}
              </option>
            ),
          )}
        </select>
      </label>
      <div className={styles.paymentHistory}>
        {filtered.length === 0 ? (
          <OfficeEmpty />
        ) : (
          filtered.map((payment) => (
            <article
              className={styles.paymentRow}
              key={payment.id}
              data-payment-row={payment.id}
              aria-labelledby={`payment-heading-${payment.id}`}
            >
              <div className={styles.paymentHeader}>
                <h2 id={`payment-heading-${payment.id}`}>
                  {t('office.payment')} <bdi>#{payment.id}</bdi>
                </h2>
                <Badge tone="test">{t('review.badge')}</Badge>
              </div>
              <dl className={styles.paymentSummary}>
                <div>
                  <dt>{t('office.reference')}</dt>
                  <dd>
                    <bdi>
                      {payment.receipt?.reference ?? t('office.unavailable')}
                    </bdi>
                  </dd>
                </div>
                <div>
                  <dt>{t('office.amount')}</dt>
                  <dd>{money(payment.amount)}</dd>
                </div>
                <div>
                  <dt>{t('office.method')}</dt>
                  <dd>{t(`office.${payment.method}`)}</dd>
                </div>
                <div>
                  <dt>{t('office.status')}</dt>
                  <dd>{t(`office.${payment.status}`)}</dd>
                </div>
                <div>
                  <dt>{t('office.created')}</dt>
                  <dd>
                    <time dateTime={payment.createdAt}>
                      {date(payment.createdAt)}
                    </time>
                  </dd>
                </div>
                <div>
                  <dt>{t('office.receiptStatus')}</dt>
                  <dd>
                    {payment.receipt
                      ? t(`office.${payment.receipt.reviewStatus}`)
                      : t('office.noReceipt')}
                  </dd>
                </div>
              </dl>
              <details className={styles.paymentDisclosure}>
                <summary>
                  {t(
                    payment.status === 'pending' &&
                      context.company.permissions.includes(
                        'tenant.receipts.submit',
                      )
                      ? 'office.localDraft'
                      : 'office.details',
                  )}
                </summary>
                <p className={styles.note}>
                  {t('office.recordRestaurant')} :{' '}
                  <bdi>{payment.restaurantId}</bdi>
                </p>
                {payment.status === 'pending' &&
                context.company.permissions.includes(
                  'tenant.receipts.submit',
                ) ? (
                  <ReceiptDraft payment={payment} />
                ) : (
                  <p className={styles.note}>{t('office.evidenceBoundary')}</p>
                )}
              </details>
            </article>
          ))
        )}
      </div>
    </>
  );
}
