// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Explicit local enrollment; all authority, eligibility and accepted versions are checked by the server.
import { useId, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import { identityKey, useSession } from '../../app/access';
import { Button, LoadingPanel } from '../../shared/ui/primitives';
import styles from './integration.module.css';
import { useUnsavedChanges } from '../../shared/ui/UnsavedChanges';

const dossierSchema = z.object({
  id: z.number(),
  organization_id: z.number(),
  company_name: z.string(),
  restaurant_name: z.string(),
  branch_name: z.string(),
  legal_entity_reference: z.string(),
  status: z.string(),
  restaurant_id: z.number().nullable(),
  revision: z.number(),
});
const countrySchema = z.object({
  organization_id: z.number(),
  revision: z.number(),
  declared_country: z.string().nullable(),
  validated_country: z.string().nullable(),
  pending_country: z.string().nullable(),
  pending_effective_at: z.string().nullable(),
  requests: z.array(
    z.object({
      id: z.number(),
      country: z.string(),
      status: z.string(),
      evidence_id: z.string(),
      legal_entity_reference: z.string(),
    }),
  ),
  decisions: z.array(z.record(z.unknown())),
});
const documentSchema = z.object({
  id: z.number(),
  version: z.string(),
  sha256: z.string(),
  locale: z.enum(['fr', 'en', 'ar']),
  content: z.string(),
  response_kind: z.enum(['acceptance', 'information', 'optional_consent']),
  required: z.boolean(),
  synthetic: z.literal(true),
  response: z
    .enum(['accepted', 'acknowledged', 'declined'])
    .nullable()
    .default(null),
  response_locale: z.string().nullable().optional(),
  response_at: z.string().nullable().optional(),
});
type PresentedDocument = z.infer<typeof documentSchema>;

/** Decode only a closed domain code, never display raw server exception content. */
export async function enrollmentRequest(
  path: string,
  method = 'GET',
  body?: unknown,
  binary?: File,
): Promise<unknown> {
  const response = await fetch('/api/web' + path, {
    method,
    credentials: 'same-origin',
    cache: 'no-store',
    ...(binary
      ? { body: binary, headers: { 'Content-Type': binary.type } }
      : body === undefined
        ? {}
        : {
            body: JSON.stringify(body),
            headers: { 'Content-Type': 'application/json' },
          }),
  });
  if (!response.ok) {
    if (response.status === 401)
      window.dispatchEvent(new Event('moulai-session-expired'));
    const error: unknown = await response.json().catch(() => null);
    const code = z
      .object({
        detail: z.object({ code: z.string().regex(/^[a-z_]{1,120}$/) }),
      })
      .safeParse(error);
    throw new Error(
      code.success
        ? code.data.detail.code
        : response.status === 403
          ? 'permission_required'
          : 'operation_requires_review',
    );
  }
  return response.status === 204 ? null : response.json();
}

/** Keep a generic translated explanation and a secondary copyable technical diagnosis. */
function Outcome({ message, error }: { message: string; error: boolean }) {
  const { t } = useTranslation();
  if (!message) return null;
  return (
    <div role={error ? 'alert' : 'status'}>
      <p>{t(error ? 'o3.failure' : 'o3.saved')}</p>
      {error && (
        <details>
          <summary>{t('o3.technical')}</summary>
          <code dir="ltr">{message}</code>
        </details>
      )}
    </div>
  );
}

/** Upload is private and separate from declaring or approving a billing country. */
export function BillingCountryPanel({
  organizationId,
  legalEntity,
}: {
  organizationId: number;
  legalEntity: string;
}) {
  const { t } = useTranslation(),
    session = useSession();
  const root = `/organizations/${organizationId}/billing-country`;
  const query = useQuery({
    queryKey: [...identityKey(session.data), root],
    queryFn: async () => countrySchema.parse(await enrollmentRequest(root)),
    retry: false,
  });
  const [country, setCountry] = useState(''),
    [entity, setEntity] = useState(legalEntity),
    [reason, setReason] = useState(''),
    [file, setFile] = useState<File | null>(null),
    [synthetic, setSynthetic] = useState(false),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState(''),
    [error, setError] = useState(false);
  const [dirty, setDirty] = useState(false);
  useUnsavedChanges(dirty);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || !synthetic || !query.data) return;
    setBusy(true);
    setMessage('');
    try {
      if (file.size > 2 * 1024 * 1024)
        throw new Error('billing_country_document_too_large');
      const evidence = z
        .object({ id: z.string() })
        .parse(
          await enrollmentRequest(
            `${root}/evidence?filename=${encodeURIComponent(file.name)}&synthetic=true`,
            'POST',
            undefined,
            file,
          ),
        );
      await enrollmentRequest(root, 'POST', {
        declared_country: country,
        legal_entity_reference: entity,
        reason,
        evidence_id: evidence.id,
        expected_revision: query.data.revision,
        idempotency_key: crypto.randomUUID(),
      });
      setDirty(false);
      setMessage('saved');
      setError(false);
      await query.refetch();
    } catch (caught) {
      setError(true);
      setMessage(
        caught instanceof Error ? caught.message : 'operation_requires_review',
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className={styles.panel} aria-label={t('o3.countryTitle')}>
      <h2>{t('o3.countryTitle')}</h2>
      <p>{t('o3.countryHelp')}</p>
      {query.isPending ? (
        <LoadingPanel />
      ) : query.isError ? (
        <Outcome error message="operation_requires_review" />
      ) : (
        query.data && (
          <>
            <p>
              {t('o3.declared')}:{' '}
              <bdi>{query.data.declared_country ?? '—'}</bdi>
            </p>
            <p>
              {t('o3.validated')}:{' '}
              <strong>
                <bdi>{query.data.validated_country ?? t('o3.noCountry')}</bdi>
              </strong>
            </p>
            {query.data.pending_country && (
              <p>
                {t('o3.pendingCountry')}:{' '}
                <bdi>
                  {query.data.pending_country} ·{' '}
                  {query.data.pending_effective_at}
                </bdi>
              </p>
            )}
            {query.data.requests.map((request) => (
              <p key={request.id}>
                {t('o3.' + request.status)} · <bdi>{request.country}</bdi>
              </p>
            ))}
            <form
              className={styles.form}
              onChange={() => setDirty(true)}
              onSubmit={(event) => void submit(event)}
            >
              <label>
                {t('o3.country')}
                <input
                  data-testid="billing-country"
                  value={country}
                  onChange={(event) => setCountry(event.target.value)}
                  pattern="[A-Z]{2}"
                  maxLength={2}
                  required
                  dir="ltr"
                />
              </label>
              <label>
                {t('o3.legal_entity_reference')}
                <input
                  value={entity}
                  onChange={(event) => setEntity(event.target.value)}
                  minLength={3}
                  required
                />
              </label>
              <label>
                {t('o3.proof')}
                <input
                  type="file"
                  accept="application/pdf,image/png,image/jpeg"
                  required
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </label>
              <label>
                {t('o3.reason')}
                <input
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  minLength={3}
                  required
                />
              </label>
              <label className={styles.choice}>
                <input
                  type="checkbox"
                  checked={synthetic}
                  onChange={(event) => setSynthetic(event.target.checked)}
                  required
                />
                {t('o3.synthetic')}
              </label>
              <Button
                type="submit"
                disabled={
                  busy ||
                  !synthetic ||
                  !file ||
                  query.data.requests.some(
                    (request) => request.status === 'pending',
                  )
                }
              >
                {t('o3.submitCountry')}
              </Button>
            </form>
            <Button variant="secondary" onClick={() => void query.refetch()}>
              {t('o3.refresh')}
            </Button>
          </>
        )
      )}
      <Outcome message={message} error={error} />
    </section>
  );
}

/** Document controls start unselected and keep acceptance, information and optional refusal distinct. */
function DocumentCard({ document }: { document: PresentedDocument }) {
  const { t } = useTranslation();
  const [choice, setChoice] = useState(
      document.response === 'acknowledged'
        ? 'accepted'
        : (document.response ?? ''),
    ),
    [saved, setSaved] = useState(document.response !== null),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState('');
  useUnsavedChanges(!saved && choice !== '');
  const label =
    document.response_kind === 'acceptance'
      ? 'o3.accept'
      : document.response_kind === 'information'
        ? 'o3.informed'
        : 'o3.optional';
  async function respond(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await enrollmentRequest('/enrollment/documents/respond', 'POST', {
        document_id: document.id,
        version: document.version,
        sha256: document.sha256,
        locale: document.locale,
        action:
          document.response_kind === 'information' ? 'acknowledged' : choice,
      });
      setSaved(true);
    } catch (caught) {
      setMessage(
        caught instanceof Error ? caught.message : 'operation_requires_review',
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className={styles.record}>
      <p
        className={styles.document}
        dir={document.locale === 'ar' ? 'rtl' : 'ltr'}
      >
        {document.content}
      </p>
      <form onSubmit={(event) => void respond(event)}>
        {document.response_kind === 'optional_consent' ? (
          <fieldset>
            <legend>{t(label)}</legend>
            {(['accepted', 'declined'] as const).map((value) => (
              <label className={styles.choice} key={value}>
                <input
                  type="radio"
                  name={'document-' + document.id}
                  value={value}
                  checked={choice === value}
                  disabled={saved}
                  onChange={() => setChoice(value)}
                />
                {t(value === 'accepted' ? 'o3.yes' : 'o3.no')}
              </label>
            ))}
          </fieldset>
        ) : (
          <label className={styles.choice}>
            <input
              type="checkbox"
              checked={choice === 'accepted'}
              disabled={saved}
              onChange={(event) =>
                setChoice(event.target.checked ? 'accepted' : '')
              }
            />
            {t(label)}
          </label>
        )}
        <Button type="submit" disabled={!choice || saved || busy}>
          {t(saved ? 'o3.recorded' : 'o3.saveResponse')}
        </Button>
      </form>
      <Outcome error message={message} />
    </article>
  );
}

/** Resume the same persisted dossier after reload; no business identity is manufactured by a browser scenario selector. */
export function EnrollmentPage() {
  const { t, i18n } = useTranslation(),
    session = useSession(),
    cache = useQueryClient();
  const query = useQuery({
    queryKey: [...identityKey(session.data), 'enrollment'],
    queryFn: async () =>
      dossierSchema.nullable().parse(await enrollmentRequest('/enrollment')),
    retry: false,
  });
  const draftForm = useRef<HTMLFormElement>(null);
  const formId = useId();
  const [dirty, setDirty] = useState(false);
  useUnsavedChanges(dirty);
  const localDraft = session.data?.source === 'authenticated-local';
  const [busy, setBusy] = useState(false),
    [message, setMessage] = useState(''),
    [error, setError] = useState(false),
    [documents, setDocuments] = useState<PresentedDocument[]>([]);
  async function operation(task: () => Promise<void>) {
    setBusy(true);
    setMessage('');
    try {
      await task();
      setError(false);
      setMessage('saved');
      await query.refetch();
    } catch (caught) {
      setError(true);
      setMessage(
        caught instanceof Error ? caught.message : 'operation_requires_review',
      );
    } finally {
      setBusy(false);
    }
  }
  const fields = [
    'company_name',
    'legal_entity_reference',
    'full_name',
    'phone',
    'email',
    'restaurant_name',
    'branch_name',
  ] as const;
  return (
    <section
      className={styles.panel}
      dir={i18n.language === 'ar' ? 'rtl' : 'ltr'}
    >
      <h1>{t('o3.title')}</h1>
      <p>{t('o3.local')}</p>
      {query.isPending ? (
        <LoadingPanel />
      ) : query.isError ? (
        <Outcome error message="operation_requires_review" />
      ) : !query.data ? (
        <form
          ref={draftForm}
          onChange={() => setDirty(true)}
          className={styles.form}
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            void operation(async () => {
              await enrollmentRequest(
                '/enrollment',
                'POST',
                Object.fromEntries(
                  fields.map((key) => [
                    key,
                    data.get(key) || (key === 'email' ? null : ''),
                  ]),
                ),
              );
              setDirty(false);
              if (localDraft)
                await enrollmentRequest('/enrollment-draft', 'DELETE');
            });
          }}
        >
          <p>
            {t(
              localDraft
                ? 'followup.draftInfo'
                : 'followup.draftUnavailableStaging',
            )}
          </p>
          {localDraft && (
            <div>
              <Button
                type="button"
                variant="secondary"
                disabled={busy}
                onClick={() =>
                  void operation(async () => {
                    if (!draftForm.current) return;
                    const data = new FormData(draftForm.current);
                    await enrollmentRequest(
                      '/enrollment-draft',
                      'PUT',
                      Object.fromEntries(
                        fields.map((field) => [
                          field,
                          String(data.get(field) ?? ''),
                        ]),
                      ),
                    );
                  })
                }
              >
                {t('followup.saveDraft')}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={busy}
                onClick={() =>
                  void operation(async () => {
                    const saved = z
                      .object({
                        fields: z.record(z.string()),
                        expires_at: z.number(),
                      })
                      .nullable()
                      .parse(await enrollmentRequest('/enrollment-draft'));
                    if (!saved || !draftForm.current)
                      throw new Error('enrollment_draft_unavailable');
                    for (const field of fields) {
                      const input = draftForm.current.elements.namedItem(field);
                      if (input instanceof HTMLInputElement)
                        input.value = saved.fields[field] ?? '';
                    }
                    setDirty(true);
                  })
                }
              >
                {t('followup.restoreDraft')}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={busy}
                onClick={() =>
                  void operation(async () => {
                    await enrollmentRequest('/enrollment-draft', 'DELETE');
                  })
                }
              >
                {t('followup.deleteDraft')}
              </Button>
            </div>
          )}
          {fields.map((field) => (
            <label key={field}>
              <span id={formId + field}>{t('o3.' + field)}</span>
              <small id={formId + field + '-requirement'}>
                {t(field === 'email' ? 'quality.optional' : 'quality.required')}
              </small>
              <input
                aria-labelledby={formId + field}
                aria-describedby={formId + field + '-requirement'}
                name={field}
                type={field === 'email' ? 'email' : 'text'}
                minLength={
                  field === 'phone' || field === 'legal_entity_reference'
                    ? 3
                    : 2
                }
                maxLength={field === 'phone' ? 20 : 180}
                required={field !== 'email'}
              />
            </label>
          ))}
          <Button type="submit" disabled={busy}>
            {t('o3.create')}
          </Button>
        </form>
      ) : (
        <>
          <h2>{query.data.company_name}</h2>
          <p>
            {query.data.restaurant_name} · {query.data.branch_name}
          </p>
          {query.data.status === 'completed' ? (
            <>
              <p role="status">{t('o3.completed')}</p>
              <Link
                to="/workspace"
                onClick={() => void cache.invalidateQueries()}
              >
                {t('o3.workspace')}
              </Link>
            </>
          ) : (
            <>
              <BillingCountryPanel
                organizationId={query.data.organization_id}
                legalEntity={query.data.legal_entity_reference}
              />
              <section className={styles.panel}>
                <h2>{t('o3.documents')}</h2>
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() =>
                    void operation(async () => {
                      const locale =
                        i18n.language === 'ar'
                          ? 'ar'
                          : i18n.language === 'en'
                            ? 'en'
                            : 'fr';
                      setDocuments(
                        z
                          .array(documentSchema)
                          .parse(
                            await enrollmentRequest(
                              '/enrollment/documents/present?locale=' + locale,
                              'POST',
                            ),
                          ),
                      );
                    })
                  }
                >
                  {t('o3.present')}
                </Button>
                {documents.map((document) => (
                  <DocumentCard
                    key={document.id + '-' + document.locale}
                    document={document}
                  />
                ))}
              </section>
              <p>{t('o3.notReady')}</p>
              <Button
                disabled={busy}
                onClick={() =>
                  void operation(async () => {
                    await enrollmentRequest('/enrollment/finalize', 'POST');
                    await cache.invalidateQueries({
                      queryKey: [...identityKey(session.data), 'organizations'],
                    });
                  })
                }
              >
                {t('o3.finalize')}
              </Button>
            </>
          )}
        </>
      )}
      <Outcome message={message} error={error} />
    </section>
  );
}

/** Explicit human review under a separate grant; pricing editors cannot access this page's API. */
export function BillingCountryReviewPage() {
  const { t } = useTranslation(),
    session = useSession();
  const queue = useQuery({
    queryKey: [...identityKey(session.data), 'country-review'],
    queryFn: async () =>
      z
        .array(
          z.object({
            id: z.number(),
            organization_id: z.number(),
            company_name: z.string(),
            status: z.string(),
          }),
        )
        .parse(await enrollmentRequest('/platform/billing-countries')),
    retry: false,
  });
  const [detail, setDetail] = useState<z.infer<typeof countrySchema> | null>(
      null,
    ),
    [reason, setReason] = useState(''),
    [checked, setChecked] = useState(false),
    [same, setSame] = useState(false),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState(''),
    [error, setError] = useState(false);
  async function review(decision: 'approve' | 'reject' | 'needs_information') {
    const request = detail?.requests.find(
      (value) => value.status === 'pending',
    );
    if (!request || !detail) return;
    setBusy(true);
    try {
      setDetail(
        countrySchema.parse(
          await enrollmentRequest(
            `/platform/billing-country-requests/${request.id}/review`,
            'POST',
            {
              decision,
              expected_revision: detail.revision,
              justification: reason,
              evidence_checked: checked,
              same_legal_entity: same,
            },
          ),
        ),
      );
      setError(false);
      setMessage('saved');
      await queue.refetch();
    } catch (caught) {
      setError(true);
      setMessage(
        caught instanceof Error ? caught.message : 'operation_requires_review',
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className={styles.panel}>
      <h1>{t('o3.reviewTitle')}</h1>
      <p>{t('o3.reviewHelp')}</p>
      {queue.isPending ? (
        <LoadingPanel />
      ) : queue.isError ? (
        <Outcome error message="permission_required" />
      ) : (
        queue.data?.map((row) => (
          <div className={styles.actions} key={row.id}>
            <span>
              {row.company_name} · {t('o3.' + row.status)}
            </span>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => {
                setBusy(true);
                setMessage('');
                setChecked(false);
                setSame(false);
                setReason('');
                void enrollmentRequest(
                  '/platform/billing-countries/' + row.organization_id,
                )
                  .then((value) => setDetail(countrySchema.parse(value)))
                  .catch(() => {
                    setError(true);
                    setMessage('permission_required');
                  })
                  .finally(() => setBusy(false));
              }}
            >
              {t('o3.open')}
            </Button>
          </div>
        ))
      )}
      {detail && (
        <article className={styles.record}>
          <p>
            {t('o3.declared')}: <bdi>{detail.declared_country}</bdi> ·{' '}
            {t('o3.validated')}:{' '}
            <bdi>{detail.validated_country ?? t('o3.noCountry')}</bdi>
          </p>
          {detail.requests.map((row) => (
            <div key={row.id}>
              <p>
                <bdi>{row.legal_entity_reference}</bdi> ·{' '}
                {t('o3.' + row.status)}
              </p>
              <a
                href={`/api/web/billing-country-evidence/${row.evidence_id}?reviewer=true`}
                target="_blank"
                rel="noreferrer"
              >
                {t('o3.download')}
              </a>
            </div>
          ))}
          <form
            className={styles.form}
            onSubmit={(event) => {
              event.preventDefault();
              void review('approve');
            }}
          >
            <label>
              {t('o3.reason')}
              <input
                value={reason}
                minLength={3}
                required
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            <label className={styles.choice}>
              <input
                type="checkbox"
                checked={checked}
                onChange={(event) => setChecked(event.target.checked)}
              />
              {t('o3.checked')}
            </label>
            <label className={styles.choice}>
              <input
                type="checkbox"
                checked={same}
                onChange={(event) => setSame(event.target.checked)}
              />
              {t('o3.sameEntity')}
            </label>
            <Button
              type="submit"
              disabled={
                busy ||
                !checked ||
                !same ||
                !detail.requests.some((row) => row.status === 'pending')
              }
            >
              {t('o3.approve')}
            </Button>
            <Button
              variant="secondary"
              disabled={busy || reason.trim().length < 3}
              onClick={() => void review('needs_information')}
            >
              {t('o3.needsInformation')}
            </Button>
            <Button
              variant="secondary"
              disabled={busy || reason.trim().length < 3}
              onClick={() => void review('reject')}
            >
              {t('o3.reject')}
            </Button>
          </form>
        </article>
      )}
      <Outcome message={message} error={error} />
    </section>
  );
}
