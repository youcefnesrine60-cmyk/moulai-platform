// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useState, type ReactElement } from 'react';
import { Link, useParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, ArrowRight, Pencil } from 'lucide-react';
import { AccessError } from '../../shared/access/contracts';
import {
  lockedOrderStatuses,
  orderStatuses,
  type OrderStatus,
} from '../../shared/business/contracts';
import { Badge, Button, ErrorPanel } from '../../shared/ui/primitives';
import { ReviewEditor } from './ReviewEditor';
import {
  EmptyResults,
  positiveId,
  useBusinessFormatting,
  useRestaurantContext,
} from './scope';
import styles from './management.module.css';

/** State labels never imply that this UI can authorize a backend transition. */
export function OrderState({ status }: { status: OrderStatus }): ReactElement {
  const { t } = useTranslation();
  return (
    <span className={styles.status} data-status={status}>
      {t(`business.status.${status}`)}
    </span>
  );
}

/** Local review filtering/paging over already-scoped projections, without API claims. */
export function OrdersPage(): ReactElement {
  const { t } = useTranslation();
  const { data, basePath, company } = useRestaurantContext();
  const { money, date } = useBusinessFormatting();
  const [status, setStatus] = useState('all');
  const [type, setType] = useState('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  if (!company.permissions.includes('tenant.orders.read'))
    return <ErrorPanel error={new AccessError('noAccess')} />;
  const filtered = [...data.orders]
    .filter(
      (row) =>
        (status === 'all' || row.status === status) &&
        (type === 'all' || row.type === type) &&
        `${row.number} ${row.customerName}`
          .toLocaleLowerCase()
          .includes(search.trim().toLocaleLowerCase()),
    )
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt) || b.id - a.id);
  const pages = Math.max(1, Math.ceil(filtered.length / 5));
  const activePage = Math.min(page, pages);
  const rows = filtered.slice((activePage - 1) * 5, activePage * 5);
  const clear = (): void => {
    setStatus('all');
    setType('all');
    setSearch('');
    setPage(1);
  };
  return (
    <>
      <div className={styles.titleRow}>
        <div>
          <p className="eyebrow">{t('nav.orders')}</p>
          <h1>{t('business.orders')}</h1>
          <p className={styles.intro}>{t('business.ordersIntro')}</p>
        </div>
        <Badge tone="test">{t('review.badge')}</Badge>
      </div>
      <div className={styles.toolbar}>
        <label className={styles.field}>
          {t('business.searchOrders')}
          <input
            type="search"
            value={search}
            maxLength={255}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
        </label>
        <label className={styles.field}>
          {t('business.orderStatus')}
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            <option value="all">{t('business.allStatuses')}</option>
            {orderStatuses.map((value) => (
              <option key={value} value={value}>
                {t(`business.status.${value}`)}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          {t('business.orderType')}
          <select
            value={type}
            onChange={(event) => {
              setType(event.target.value);
              setPage(1);
            }}
          >
            <option value="all">{t('business.allTypes')}</option>
            {['dine_in', 'takeaway', 'delivery'].map((value) => (
              <option key={value} value={value}>
                {t(`business.type.${value}`)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {rows.length === 0 ? (
        <EmptyResults clear={clear} />
      ) : (
        <div className={styles.orderList}>
          {rows.map((row) => (
            <Link
              key={row.id}
              to={`${basePath}/orders/${row.id}`}
              className={styles.orderRow}
              aria-label={`${t('business.openOrder')} · ${row.number}`}
            >
              <span>
                <small>{t('business.order')}</small>
                <strong>
                  <bdi>{row.number}</bdi>
                </strong>
                <small>{date(row.createdAt)}</small>
              </span>
              <span>
                <small>{t('business.customer')}</small>
                {row.customerName}
                <small>{t(`business.type.${row.type}`)}</small>
              </span>
              <span>
                <small>{t('business.orderStatus')}</small>
                <OrderState status={row.status} />
              </span>
              <span>
                <small>{t('business.total')}</small>
                <bdi>{money(row.total)}</bdi>
              </span>
              <span className={styles.textLink}>
                {t('business.openOrder')}{' '}
                <ArrowRight
                  className="directional"
                  size={15}
                  aria-hidden="true"
                />
              </span>
            </Link>
          ))}
        </div>
      )}
      <div className={styles.pagination}>
        <p role="status">
          {t('business.page', {
            page: activePage,
            pages,
            count: filtered.length,
          })}
        </p>
        <div className={styles.actions}>
          <Button
            variant="secondary"
            disabled={activePage <= 1}
            onClick={() => setPage(activePage - 1)}
          >
            {t('business.previous')}
          </Button>
          <Button
            variant="secondary"
            disabled={activePage >= pages}
            onClick={() => setPage(activePage + 1)}
          >
            {t('business.next')}
          </Button>
        </div>
      </div>
      <p className={styles.integrationNote}>
        {t('business.fulfillmentBoundary')}
      </p>
    </>
  );
}

/** Display authoritative projected totals, items and history; only note editing is prepared. */
export function OrderDetailPage(): ReactElement {
  const { t } = useTranslation();
  const { orderId } = useParams();
  const { company, data, basePath } = useRestaurantContext();
  const { money, date } = useBusinessFormatting();
  const [editing, setEditing] = useState(false);
  const [saved, setSaved] = useState(false);
  const order = data.orders.find((row) => row.id === positiveId(orderId));
  if (!company.permissions.includes('tenant.orders.read'))
    return <ErrorPanel error={new AccessError('noAccess')} />;
  if (!order) return <ErrorPanel error={new AccessError('notFound')} />;
  return (
    <>
      <Link to={`${basePath}/orders`} className={styles.textLink}>
        <ArrowLeft className="directional" size={16} aria-hidden="true" />{' '}
        {t('business.backOrders')}
      </Link>
      <div className={styles.titleRow} style={{ marginBlockStart: 24 }}>
        <div>
          <p className="eyebrow">{t('business.order')}</p>
          <h1>
            <bdi>{order.number}</bdi>
          </h1>
          <p className={styles.intro}>
            {t('business.created')} · {date(order.createdAt)}
          </p>
        </div>
        <OrderState status={order.status} />
      </div>
      <div className={styles.detailGrid}>
        <div className={styles.stack}>
          <section className={styles.panel}>
            <h2>{t('business.items')}</h2>
            {order.items.map((item) => (
              <div key={item.id} className={styles.row}>
                <div>
                  <h3 className={styles.productTitle}>{item.name}</h3>
                  <p className={styles.muted}>
                    {t('business.quantity')} · {item.quantity} ·{' '}
                    {t('business.unitPrice')} ·{' '}
                    <bdi>{money(item.unitPrice)}</bdi>
                  </p>
                  {item.options.map((option, index) => (
                    <p key={`${item.id}-${index}`} className={styles.muted}>
                      {option}
                    </p>
                  ))}
                </div>
                <bdi>{money(item.total)}</bdi>
              </div>
            ))}
          </section>
          <section className={styles.panel}>
            <div className={styles.titleRow}>
              <h2>{t('business.note')}</h2>
              {company.permissions.includes('tenant.orders.manage') &&
                !lockedOrderStatuses.includes(order.status) && (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setSaved(false);
                      setEditing(true);
                    }}
                  >
                    <Pencil size={15} aria-hidden="true" />
                    {t('business.editNote')}
                  </Button>
                )}
            </div>
            <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
              {order.customerNote || t('business.noNote')}
            </p>
            {saved && (
              <p role="status" className={styles.success}>
                {t('business.saved')}
              </p>
            )}
          </section>
          <section className={styles.panel}>
            <h2>{t('business.history')}</h2>
            <ol className={styles.timeline}>
              {order.history.map((event, index) => (
                <li key={`${event.at}-${index}`}>
                  <OrderState status={event.status} />
                  <time dateTime={event.at}>{date(event.at)}</time>
                </li>
              ))}
            </ol>
          </section>
        </div>
        <div className={styles.stack}>
          <section className={styles.panel}>
            <h2>{t('business.customer')}</h2>
            <p>{order.customerName}</p>
            <Badge>{t(`business.type.${order.type}`)}</Badge>
          </section>
          <section className={styles.panel}>
            <h2>{t('business.total')}</h2>
            <dl className={styles.definition}>
              {(
                [
                  ['subtotal', order.subtotal],
                  ['discount', order.discount ? -order.discount : 0],
                  ['tax', order.tax],
                  ['delivery', order.delivery],
                  ['total', order.total],
                ] as const
              ).map(([label, amount]) => (
                <div style={{ display: 'contents' }} key={label}>
                  <dt className={label === 'total' ? styles.total : undefined}>
                    {t(`business.${label}`)}
                  </dt>
                  <dd className={label === 'total' ? styles.total : undefined}>
                    <bdi>{money(amount)}</bdi>
                  </dd>
                </div>
              ))}
            </dl>
            <p className={styles.muted} style={{ marginBlockStart: 20 }}>
              {t(order.paid ? 'business.paid' : 'business.unpaid')}
            </p>
            <p className={styles.muted}>{t('business.paymentBoundary')}</p>
          </section>
        </div>
      </div>
      <p className={styles.notice} style={{ marginBlockStart: 24 }}>
        {t('business.fulfillmentBoundary')}
      </p>
      {editing && (
        <ReviewEditor
          selection={{ kind: 'orderNote', id: order.id }}
          close={() => setEditing(false)}
          saved={() => setSaved(true)}
        />
      )}
    </>
  );
}
