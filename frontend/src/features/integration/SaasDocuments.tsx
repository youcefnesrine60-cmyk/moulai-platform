// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Read retained documentary facts; no browser action confirms funds, changes service or infers administrator grants.
import { useEffect, useState, type FormEvent } from 'react';
import { createPortal, flushSync } from 'react-dom';
import { Link, useParams, useLocation } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { identityKey, useSession } from '../../app/access';
import { Button, LoadingPanel } from '../../shared/ui/primitives';
import { ExactAmount } from '../../shared/ui/ExactAmount';
import { CopyDocumentFact, DocumentDate } from '../../shared/ui/DocumentFacts';
import { useUnsavedChanges } from '../../shared/ui/UnsavedChanges';
import { enrollmentRequest } from './EnrollmentPage';
import styles from './saasDocuments.module.css';

const content = z.object({
  amount: z.string(),
  currency: z.string(),
  restaurant_name: z.string(),
  starts_at: z.string(),
  expires_at: z.string(),
  period_status_at_issue: z.string(),
  synthetic: z.literal(true),
});
export const saasDocument = z.object({
  id: z.number(),
  reference: z.string(),
  version: z.number(),
  replaces_id: z.number().nullable(),
  state: z.enum(['valid', 'invalidated']),
  issued_at: z.string(),
  issuer: z.string(),
  content,
  verification_url: z.string().url(),
  svg: z.string(),
  events: z.array(
    z.object({
      event: z.enum(['issued', 'invalidated']),
      author: z.string(),
      at: z.string(),
      reason: z.string(),
    }),
  ),
});
type Document = z.infer<typeof saasDocument>;
const requestSchema = z.object({
  id: z.number(),
  amount: z.string(),
  currency: z.string(),
  status: z.string(),
  starts_at: z.string().nullable().optional(),
  expires_at: z.string().nullable().optional(),
});
const queueSchema = z.array(
  z.object({
    payment_id: z.number(),
    amount: z.string(),
    currency: z.string(),
    payment_status: z.string(),
    restaurant_name: z.string(),
    documents: z.array(saasDocument),
  }),
);

/** Map known refusal facts only; arbitrary exception messages never become a diagnosis. */
function failureKey(error: unknown): string {
  const code = error instanceof Error ? error.message : '';
  return code === 'subscription_document_migration_required'
    ? 'saasDoc.migration'
    : [
          'subscription_document_funds_unverified',
          'subscription_document_period_incoherent',
          'subscription_document_snapshot_missing',
          'subscription_document_snapshot_incoherent',
        ].includes(code)
      ? 'saasDoc.funds'
      : 'saasDoc.failure';
}

/** A complete retained version remains visible even after its QR reports invalidation. */
export function SaasDocumentContent({
  document: value,
}: {
  document: Document;
}) {
  const { t } = useTranslation();
  return (
    <article
      className={styles.sheet}
      data-saas-printable
      dir={document.documentElement.dir || 'ltr'}
    >
      <img className={styles.logo} src="/brand/moulai-logo.png" alt="MoulAI™" />
      <h1>{t('saasDoc.final')}</h1>
      <p className={styles.warning}>{t('saasDoc.fake')}</p>
      <h2>
        <bdi>{value.content.restaurant_name}</bdi>
      </h2>
      <p>
        <strong>{t('saasDoc.' + value.state)}</strong>
      </p>
      <p>
        {t('documents.reference')}:{' '}
        <bdi className={styles.reference} dir="ltr">
          {value.reference}
        </bdi>{' '}
        <CopyDocumentFact
          value={value.reference}
          label={t('documents.reference')}
          className={styles.noPrint}
        />{' '}
        · {t('saasDoc.version')} <bdi>{value.version}</bdi>
      </p>
      <p>
        {t('saasDoc.issuer')}: <bdi>{value.issuer}</bdi> ·{' '}
        {t('saasDoc.issuedAt')}: <DocumentDate value={value.issued_at} />
      </p>
      <p className={styles.amount}>
        <ExactAmount
          value={value.content.amount}
          currency={value.content.currency}
        />
      </p>
      <p>
        {t('saasDoc.period')}: <DocumentDate value={value.content.starts_at} />
        {' → '}
        <DocumentDate value={value.content.expires_at} />
      </p>
      <p>
        {t('saasDoc.atIssue')}:{' '}
        {t('quality.subscription.' + value.content.period_status_at_issue, {
          defaultValue: t('quality.notConfirmed'),
        })}
      </p>
      {value.content.period_status_at_issue === 'scheduled' && (
        <p>{t('saasDoc.scheduled')}</p>
      )}
      {value.replaces_id !== null && (
        <p>
          {t('saasDoc.previous')}: <bdi>{value.replaces_id}</bdi>
        </p>
      )}
      <section className={styles.verification}>
        <img
          width="176"
          height="176"
          alt={t('documents.qrAlt')}
          src={
            'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(value.svg)
          }
        />
        <div>
          <h2>{t('saasDoc.verify')}</h2>
          <p>{t('saasDoc.verifyHelp')}</p>
          <a
            href={value.verification_url}
            target="_blank"
            rel="noreferrer"
            dir="ltr"
          >
            {t('saasDoc.openVerification')}
          </a>
          <p className={styles.reference} dir="ltr">
            {value.verification_url}
          </p>
          <CopyDocumentFact
            value={value.verification_url}
            label={t('saasDoc.verify')}
            className={styles.noPrint}
          />
          <p>{t('saasDoc.currentValidity')}</p>
          {['127.0.0.1', 'localhost', '[::1]'].includes(
            new URL(value.verification_url).hostname,
          ) && <p>{t('documents.localOnly')}</p>}
        </div>
      </section>
      <details className={styles.noPrint}>
        <summary>{t('saasDoc.audit')}</summary>
        {value.events.map((event) => (
          <p key={event.event}>
            {t(
              event.event === 'issued'
                ? 'saasDoc.issued'
                : 'saasDoc.invalidatedEvent',
            )}{' '}
            · <bdi>{event.author}</bdi> · <DocumentDate value={event.at} /> ·{' '}
            {event.reason}
          </p>
        ))}
        <p dir="ltr">
          {value.issued_at}
          <br />
          {value.content.starts_at}
          <br />
          {value.content.expires_at}
        </p>
      </details>
    </article>
  );
}

/** Render the same retained source for screen and the isolated print root. */
function OwnedDocumentContent({
  data,
}: {
  data: { payment: z.infer<typeof requestSchema>; documents: Document[] };
}) {
  const { t } = useTranslation();
  return data.documents.length ? (
    <>
      <p className={styles.noPrint} data-saas-payment-status>
        {t('saasDoc.paymentStatus')}:{' '}
        {t('o3.payment.' + data.payment.status, {
          defaultValue: t('quality.notConfirmed'),
        })}
      </p>
      {data.documents.map((value, index) => (
        <div key={value.id} className={index ? styles.oldVersion : ''}>
          <SaasDocumentContent document={value} />
        </div>
      ))}
    </>
  ) : (
    <article className={styles.sheet} data-saas-printable>
      <img className={styles.logo} src="/brand/moulai-logo.png" alt="MoulAI™" />
      <h1>
        {t(
          data.payment.status === 'pending'
            ? 'saasDoc.request'
            : 'saasDoc.retainedPayment',
        )}
      </h1>
      <p className={styles.warning}>{t('saasDoc.fake')}</p>
      <p>
        {t(
          data.payment.status === 'pending'
            ? 'saasDoc.requestHelp'
            : 'saasDoc.retainedHelp',
        )}
      </p>
      <p>
        {t('documents.reference')}: <bdi>{data.payment.id}</bdi>
      </p>
      <p>
        <ExactAmount
          value={data.payment.amount}
          currency={data.payment.currency}
        />
      </p>
      <p>
        {t('o3.payment.' + data.payment.status, {
          defaultValue: t('quality.notConfirmed'),
        })}
      </p>
      <p>{t('saasDoc.unissued')}</p>
    </article>
  );
}

/** Owner route: reread server state before print; a request has no definitive documentary QR. */
export function OwnerSaasDocumentsPage() {
  const { organizationId, restaurantId, paymentId } = useParams();
  const { t, i18n } = useTranslation(),
    session = useSession();
  const locale = ['fr', 'en', 'ar'].includes(i18n.language)
    ? i18n.language
    : 'fr';
  const root = `/organizations/${organizationId}/restaurants/${restaurantId}/saas-payments`;
  const [printing, setPrinting] = useState(false),
    [error, setError] = useState('');
  const query = useQuery({
    queryKey: [
      ...identityKey(session.data),
      'saas-documents',
      root,
      paymentId,
      locale,
    ],
    queryFn: async () => {
      const [payments, documents] = await Promise.all([
        enrollmentRequest(`${root}?payment_id=${paymentId}`),
        enrollmentRequest(`${root}/${paymentId}/documents?locale=${locale}`),
      ]);
      const payment = z
        .array(requestSchema)
        .parse(payments)
        .find((row) => String(row.id) === paymentId);
      if (!payment) throw new Error('unavailable');
      return { payment, documents: z.array(saasDocument).parse(documents) };
    },
    retry: false,
  });
  useEffect(() => {
    document.body.dataset.saasDocumentPage = 'true';
    return () => {
      delete document.body.dataset.saasDocumentPage;
    };
  }, []);
  async function print() {
    if (printing) return;
    setPrinting(true);
    setError('');
    try {
      const result = await query.refetch();
      if (result.error || !result.data) throw result.error;
      flushSync(() => setPrinting(false));
      window.print();
    } catch (caught) {
      setError(failureKey(caught));
      setPrinting(false);
    }
  }
  return (
    <section className={styles.page}>
      <div className={styles.noPrint}>
        <Link
          to={`/workspace/organizations/${organizationId}/restaurants/${restaurantId}/offer`}
        >
          {t('offer.title')}
        </Link>
        <h1>{t('saasDoc.title')}</h1>
        <div className={styles.actions}>
          <Button
            disabled={printing || !query.data || query.isError}
            onClick={() => void print()}
          >
            {t('saasDoc.print')}
          </Button>
          <Button
            variant="secondary"
            disabled={printing || query.isFetching}
            onClick={() =>
              void query.refetch().then((result) => {
                if (!result.error) setError('');
              })
            }
          >
            {t('o3.refresh')}
          </Button>
        </div>
      </div>
      {query.isPending ? (
        <LoadingPanel />
      ) : query.isError ? (
        <p role="alert">{t(failureKey(query.error))}</p>
      ) : (
        <OwnedDocumentContent data={query.data} />
      )}
      {query.data &&
        !query.isError &&
        createPortal(
          <div
            className={styles.printLayer}
            data-saas-print-root
            dir={locale === 'ar' ? 'rtl' : 'ltr'}
          >
            <OwnedDocumentContent data={query.data} />
          </div>,
          document.body,
        )}
      {error && !query.isError && (
        <p role="alert" className={styles.noPrint}>
          {t(error)}
        </p>
      )}
    </section>
  );
}

/** Commands never retry automatically; a failed confirmation keeps the reason and checkbox values. */
function DocumentActions({
  row,
  refresh,
}: {
  row: z.infer<typeof queueSchema>[number];
  refresh: () => Promise<unknown>;
}) {
  const { t, i18n } = useTranslation(),
    session = useSession();
  const grants = session.data?.platformPermissions ?? [];
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [reason, setReason] = useState(''),
    [confirmed, setConfirmed] = useState(false);
  useUnsavedChanges(Boolean(reason || confirmed));
  const latest = row.documents[0];
  async function command(path: string, body: unknown) {
    if (busy || error) return;
    setBusy(true);
    try {
      await enrollmentRequest(path + '?locale=' + i18n.language, 'POST', body);
      setReason('');
      setConfirmed(false);
      await refresh();
    } catch (caught) {
      setError(failureKey(caught));
    } finally {
      setBusy(false);
    }
  }
  function invalidate(event: FormEvent) {
    event.preventDefault();
    if (latest)
      void command(`/platform/saas-documents/${latest.id}/invalidate`, {
        reason,
        confirmed,
      });
  }
  return (
    <article
      className={styles.record}
      data-saas-document-payment={row.payment_id}
    >
      <h2>
        <bdi>{row.restaurant_name}</bdi>
      </h2>
      <p>
        {t('documents.reference')}: <bdi>{row.payment_id}</bdi> ·{' '}
        <ExactAmount value={row.amount} currency={row.currency} />
      </p>
      {!latest && <p>{t('saasDoc.unissued')}</p>}
      {grants.includes('subscriptions.documents.issue') &&
        (!latest || latest.state === 'invalidated') && (
          <Button
            disabled={busy || Boolean(error)}
            onClick={() =>
              void command(
                `/platform/saas-payments/${row.payment_id}/documents`,
                latest ? { replaces_id: latest.id } : {},
              )
            }
          >
            {t(latest ? 'saasDoc.replace' : 'saasDoc.issue')}
          </Button>
        )}
      {latest?.state === 'valid' &&
        grants.includes('subscriptions.documents.invalidate') && (
          <form onSubmit={invalidate}>
            <label>
              {t('saasDoc.reason')}
              <textarea
                value={reason}
                required
                minLength={3}
                maxLength={2000}
                disabled={busy}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            <label>
              <input
                type="checkbox"
                checked={confirmed}
                required
                disabled={busy}
                onChange={(event) => setConfirmed(event.target.checked)}
              />
              {t('saasDoc.confirm')}
            </label>
            <Button
              type="submit"
              disabled={busy || Boolean(error) || !confirmed}
            >
              {t('saasDoc.invalidate')}
            </Button>
          </form>
        )}
      {error && (
        <div role="alert">
          <p>{t(error)}</p>
          <Button
            variant="secondary"
            onClick={() => void refresh().then(() => setError(''))}
          >
            {t('o3.refresh')}
          </Button>
        </div>
      )}
      {row.documents.map((value) => (
        <SaasDocumentContent document={value} key={value.id} />
      ))}
    </article>
  );
}

/** Platform documentary workspace is independent of payments.review and pricing administration. */
export function PlatformSaasDocumentsPage() {
  const { t, i18n } = useTranslation(),
    session = useSession();
  const query = useQuery({
    queryKey: [
      ...identityKey(session.data),
      'platform-saas-documents',
      i18n.language,
    ],
    queryFn: async () =>
      queueSchema.parse(
        await enrollmentRequest(
          '/platform/saas-documents?locale=' + i18n.language,
        ),
      ),
    retry: false,
  });
  return (
    <section className={styles.page}>
      <h1>{t('saasDoc.title')}</h1>
      <p>{t('saasDoc.fake')}</p>
      {query.isPending ? (
        <LoadingPanel />
      ) : query.isError ? (
        <p role="alert">{t(failureKey(query.error))}</p>
      ) : !query.data.length ? (
        <p>{t('saasDoc.empty')}</p>
      ) : (
        query.data.map((row) => (
          <DocumentActions
            key={row.payment_id}
            row={row}
            refresh={() => query.refetch()}
          />
        ))
      )}
      <Button variant="secondary" onClick={() => void query.refetch()}>
        {t('o3.refresh')}
      </Button>
    </section>
  );
}

/** Read only the URL fragment; it is not a login, business action or administrative address. */
export function VerifySaasDocumentPage() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const locale = new URLSearchParams(location.search).get('locale');
  useEffect(() => {
    if (locale && ['fr', 'en', 'ar'].includes(locale))
      void i18n.changeLanguage(locale);
  }, [i18n, locale]);
  const reference = location.hash.slice(1);
  const query = useQuery({
    queryKey: ['verify-saas-document', reference],
    queryFn: async () =>
      z
        .object({
          state: z.enum(['unknown', 'valid', 'invalidated']),
          reference: z.string().optional(),
          issuer: z.string().optional(),
          issued_at: z.string().optional(),
        })
        .parse(
          await enrollmentRequest('/saas-documents/verify', 'POST', {
            reference,
          }),
        ),
    retry: false,
  });
  return (
    <main className={styles.page}>
      <div className={styles.sheet}>
        <h1>{t('saasDoc.verify')}</h1>
        <p>{t('saasDoc.fake')}</p>
        <p>{t('saasDoc.verifyHelp')}</p>
        {query.isPending ? (
          <LoadingPanel />
        ) : query.isError ? (
          <p role="alert">{t(failureKey(query.error))}</p>
        ) : (
          <section>
            <h2>{t('saasDoc.' + query.data.state)}</h2>
            {query.data.reference && (
              <p>
                {t('documents.reference')}: <bdi>{query.data.reference}</bdi>
              </p>
            )}
            {query.data.issuer && (
              <p>
                {t('saasDoc.issuer')}: <bdi>{query.data.issuer}</bdi>
              </p>
            )}
            {query.data.issued_at && (
              <p>
                {t('saasDoc.issuedAt')}:{' '}
                <DocumentDate value={query.data.issued_at} />
              </p>
            )}
          </section>
        )}
      </div>
    </main>
  );
}
