// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useState } from 'react';
import { z } from 'zod';
import { useTranslation } from 'react-i18next';
import {
  FormBox,
  Field,
  Pick,
  Check,
  Instant,
  useValues,
  integer,
  type FormContext,
} from './fields';
import styles from './local.module.css';
import { displayMoment } from '../../../shared/dining/operational';
import { DiningReference } from '../../../shared/dining/reference';

const acknowledgement = z.union([
  z.object({ identifier: z.number().int().positive() }),
  z.object({ status: z.string() }),
]);
export function VisitForms({ context }: { context: FormContext }) {
  const { t, i18n } = useTranslation();
  const has = (cap: string) => context.data.capabilities.includes(cap);
  const kinds = [
    ...(has('configure') ? ['table'] : []),
    ...(has('documents.issue') && has('finance.read')
      ? [...(has('service') ? ['reservation'] : []), 'food_invoice', 'receipt']
      : []),
  ];
  const v = useValues({
    kind: kinds[0] ?? 'table',
    resource: '',
    operation: 'issue',
    reason: '',
    presence: '',
    reservation: '',
    end: '',
    fold: '',
    order: '',
    action: '',
  });
  const [publish, setPublish] = useState(false),
    [observed, setObserved] = useState(false);
  const resources =
    v.get('kind') === 'table'
      ? (context.data.tables ?? [])
      : v.get('kind') === 'reservation'
        ? (context.data.requests ?? [])
        : v.get('kind') === 'food_invoice'
          ? (context.data.invoices ?? [])
          : (context.data.receipts ?? []);
  const actions = [
    ...(has('orders.approve') ? ['approve'] : []),
    ...(has('orders.prepare') ? ['prepare', 'ready'] : []),
    ...(has('orders.complete') ? ['served'] : []),
  ];
  const post = async (path: string, body: unknown) =>
    acknowledgement.parse(
      await context.api.request(
        context.api.root(context.scope) + path,
        'POST',
        body,
      ),
    );
  const links = context.data.public_links ?? [];
  return (
    <>
      <header className={styles.sectionIntro}>
        <h2>{t('d1.section_visits')}</h2>
        <p>{t('d1.visitWorkflowNotice')}</p>
        <p>{t('d1.tableQrDefault')}</p>
      </header>
      {kinds.length > 0 && (
        <FormBox
          context={context}
          title="publicLink"
          operation="public_link"
          submit={() =>
            post('/public-links', {
              operation: v.get('operation'),
              kind: v.get('kind'),
              resource_id: integer(v.get('resource')),
              public_physical_state: publish,
              reason: v.get('reason'),
            })
          }
        >
          <Pick
            label="documentKind"
            name="document_kind"
            value={v.get('kind')}
            set={(value) => {
              v.set('kind', value);
              v.set('resource', '');
            }}
            options={kinds.map((value) => ({
              value,
              label: t('d1.documentKind_' + value),
            }))}
          />
          <Pick
            label="documentResource"
            name="document_resource"
            value={v.get('resource')}
            set={(value) => v.set('resource', value)}
            options={resources.map((row) => ({
              value: String(row.id),
              label:
                'code' in row
                  ? row.code
                  : 'reference' in row
                    ? String(row.reference)
                    : '#' + row.id,
            }))}
          />
          <Pick
            label="documentAction"
            name="document_action"
            value={v.get('operation')}
            set={(value) => v.set('operation', value)}
            options={['issue', 'rotate', 'disable'].map((value) => ({
              value,
              label: t('d1.documentAction_' + value),
            }))}
          />
          {v.get('kind') === 'table' && (
            <Check
              label="publishPhysical"
              name="publish_physical"
              value={publish}
              set={setPublish}
            />
          )}
          <Field
            label="staffReason"
            name="reason"
            value={v.get('reason')}
            set={(value) => v.set('reason', value)}
            required={v.get('operation') !== 'issue'}
          />
        </FormBox>
      )}
      <section className={styles.grid} aria-label={t('d1.publicLinks')}>
        {links.map((link) => (
          <article className={styles.card} key={link.id}>
            <h3>
              {t('d1.documentKind_' + link.kind)}
              {link.table_id && (
                <>
                  {' '}
                  ·{' '}
                  {context.data.tables?.find(
                    (table) => table.id === link.table_id,
                  )?.code ?? '#' + link.table_id}
                </>
              )}
            </h3>
            {link.table_id && (
              <p>
                {[
                  context.data.tables?.find(
                    (table) => table.id === link.table_id,
                  )?.floor_label,
                  context.data.tables?.find(
                    (table) => table.id === link.table_id,
                  )?.room_label,
                  context.data.references?.find(
                    (reference) =>
                      reference.id ===
                      context.data.tables?.find(
                        (table) => table.id === link.table_id,
                      )?.location_id,
                  )?.labels[i18n.language as 'fr' | 'en' | 'ar'],
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
            )}
            <p>
              {t(
                link.active
                  ? 'd1.documentStatus_valid'
                  : 'd1.documentStatus_invalidated',
              )}{' '}
              · {t('d1.documentVersion')} {link.version}
            </p>
            <DiningReference reference={link.reference} />
            <div className={styles.row}>
              {link.active && (
                <a
                  href={
                    '/' +
                    (link.kind === 'table' ? 'menu' : 'verify-document') +
                    '?locale=' +
                    i18n.language +
                    '#' +
                    link.public_id
                  }
                  target="_blank"
                  rel="noreferrer"
                >
                  {t('d1.openPublic')}
                </a>
              )}
              {((link.kind === 'table' && has('configure')) ||
                (link.kind !== 'table' &&
                  has('finance.read') &&
                  (link.kind !== 'reservation' ||
                    has('configure') ||
                    has('service')))) && (
                <>
                  {' '}
                  <a
                    href={
                      context.api.root(context.scope) +
                      '/public-links/' +
                      link.id +
                      '/print?locale=' +
                      i18n.language
                    }
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t('d1.printDocument')}
                  </a>
                  <a
                    href={
                      context.api.root(context.scope) +
                      '/public-links/' +
                      link.id +
                      '/qr?locale=' +
                      i18n.language
                    }
                    download
                  >
                    {t('d1.downloadQr')}
                  </a>
                </>
              )}
            </div>
          </article>
        ))}
      </section>
      {has('service') && (
        <FormBox
          context={context}
          title="installPresence"
          operation="install_presence"
          submitDisabled={!observed}
          submit={async () =>
            post('/presence/install', {
              presence_id: integer(v.get('presence')),
              expected_end: await context.api.instant(
                context.scope,
                v.get('end'),
                v.get('fold'),
              ),
              request_id:
                v.get('reservation') === ''
                  ? null
                  : integer(v.get('reservation')),
              observed,
            })
          }
        >
          <Pick
            label="presenceSignal"
            name="presence"
            value={v.get('presence')}
            set={(value) => v.set('presence', value)}
            options={(context.data.presence_signals ?? [])
              .filter((row) => row.status === 'pending')
              .map((row) => ({
                value: String(row.id),
                label:
                  (context.data.tables?.find(
                    (table) => table.id === row.table_id,
                  )?.code ?? '#' + row.table_id) +
                  ' · ' +
                  row.party_size +
                  ' · ' +
                  row.expires_at,
              }))}
          />
          <Pick
            label="reservation"
            name="presence_reservation"
            value={v.get('reservation')}
            set={(value) => v.set('reservation', value)}
            required={false}
            options={(context.data.requests ?? [])
              .filter((row) => row.status === 'confirmed')
              .map((row) => ({ value: String(row.id), label: row.reference }))}
          />
          <Instant
            label="expectedEnd"
            name="end"
            value={v.get('end')}
            set={(value) => v.set('end', value)}
            fold={v.get('fold')}
            setFold={(value) => v.set('fold', value)}
          />
          <Check
            label="actualObservation"
            name="observed"
            value={observed}
            set={setObserved}
          />
          <p>{t('d1.installNoAvailabilityProof')}</p>
        </FormBox>
      )}
      {!!actions.length && (
        <FormBox
          context={context}
          title="visitOrderTransition"
          operation="visit_order_transition"
          submitDisabled={!observed}
          submit={() =>
            post('/visit-orders/transition', {
              order_id: integer(v.get('order')),
              action: v.get('action'),
              observed,
            })
          }
        >
          <Pick
            label="sourceOrders"
            name="visit_order"
            value={v.get('order')}
            set={(value) => v.set('order', value)}
            options={(context.data.visit_orders ?? []).map((row) => ({
              value: String(row.order_id),
              label:
                '#' +
                row.order_id +
                ' · ' +
                t(
                  'd1.orderStatus_' +
                    (context.data.food_orders?.find(
                      (order) => order.id === row.order_id,
                    )?.status ?? 'pending'),
                ),
            }))}
          />
          <Pick
            label="documentAction"
            name="visit_action"
            value={v.get('action')}
            set={(value) => v.set('action', value)}
            options={actions.map((value) => ({
              value,
              label: t('d1.visitAction_' + value),
            }))}
          />
          <Check
            label="actualObservation"
            name="observed_order"
            value={observed}
            set={setObserved}
          />
        </FormBox>
      )}
      <section className={styles.grid} aria-label={t('d1.visitOrders')}>
        {(context.data.visit_orders ?? []).map((order) => (
          <article className={styles.card} key={order.id}>
            <h3>
              #{order.order_id} ·{' '}
              {t(
                'd1.orderStatus_' +
                  (context.data.food_orders?.find(
                    (row) => row.id === order.order_id,
                  )?.status ?? 'pending'),
              )}
            </h3>
            <ul>
              {order.exact_lines.map((line) => (
                <li key={line.order_item_id}>
                  {line.description} · {line.quantity}
                </li>
              ))}
            </ul>
            {has('finance.read') && (
              <p>
                <bdi>
                  {order.total} {order.currency}
                </bdi>
              </p>
            )}
          </article>
        ))}
      </section>
      <section className={styles.card}>
        <h3>{t('d1.serviceEvents')}</h3>
        <p>{t('d1.eventLocalOnly')}</p>
        <ul>
          {(context.data.service_events ?? []).map((row) => (
            <li key={row.id}>
              <bdi>
                {displayMoment(
                  row.occurred_at,
                  i18n.language,
                  context.data.policy?.timezone ?? 'UTC',
                )}
              </bdi>{' '}
              ·{' '}
              {t('d1.event_' + row.kind, {
                defaultValue: t('d1.eventRecorded'),
              })}{' '}
              {Object.entries(row.details).map(([key, value]) => (
                <span key={key}>
                  {' '}
                  · {t('d1.eventTarget_' + key)} #{String(value)}
                </span>
              ))}
            </li>
          ))}
        </ul>
      </section>
      <p className={styles.sectionIntro}>{t('d1.saasInvoicePrerequisite')}</p>
    </>
  );
}
