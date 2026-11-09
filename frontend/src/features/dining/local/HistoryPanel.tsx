// MoulAI™ — explain recorded facts without changing the underlying audit record.
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../shared/ui/primitives';
import { LocalDiningError } from '../../../shared/dining/local/client';
import { displayMoment } from '../../../shared/dining/operational';
import { localized } from '../../../shared/i18n';
import {
  readHistory,
  type HistoryEvent,
  type HistoryPage,
  type HistoryFilter,
} from '../../../shared/dining/local/historyClient';
import type { FormContext } from './fields';
import styles from './local.module.css';

const referenceKinds = new Set([
  'shape',
  'category',
  'zone',
  'location',
  'view',
  'proximity',
  'feature',
  'event',
]);
export function eventLabel(
  event: HistoryEvent,
  t: (key: string, options?: { defaultValue: string }) => string,
): string {
  if (
    event.kind === 'reference.created' &&
    typeof event.details.kind === 'string' &&
    referenceKinds.has(event.details.kind)
  )
    return t('audit.reference.' + event.details.kind);
  return t('audit.event.' + event.kind, { defaultValue: t('audit.unknown') });
}
export function recordedChanges(
  event: HistoryEvent,
): { field: string; before: unknown; after: unknown }[] {
  const result: { field: string; before: unknown; after: unknown }[] = [];
  for (const [before, after] of [
    ['previous_expected_end', 'expected_end'],
    ['previous_cleaning_expected_end', 'cleaning_expected_end'],
  ])
    if (before! in event.details || after! in event.details)
      result.push({
        field: after!,
        before: event.details[before!],
        after: event.details[after!],
      });
  for (const [before, after] of [
    ['before', 'after'],
    ['old', 'new'],
    ['from', 'to'],
  ])
    if (before! in event.details || after! in event.details)
      result.push({
        field: '',
        before: event.details[before!],
        after: event.details[after!],
      });
  if (!result.length)
    for (const field of ['active', 'state', 'initial_state'])
      if (field in event.details)
        result.push({ field, before: undefined, after: event.details[field] });
  return result;
}
export function HistoryPanel({
  context,
  onDenied,
}: {
  context: FormContext;
  onDenied: () => void;
}) {
  const { t, i18n } = useTranslation();
  const [draft, setDraft] = useState({
    from: '',
    until: '',
    kind: '',
    author: '',
  });
  const [filter, setFilter] = useState<HistoryFilter>({ ...draft, page: 1 });
  const [data, setData] = useState<HistoryPage | null>(null),
    [failed, setFailed] = useState(false),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    let current = true;
    setLoading(true);
    setFailed(false);
    setData(null);
    void readHistory(context.api, context.scope, filter)
      .then((value) => {
        if (current) setData(value);
      })
      .catch((error) => {
        if (!current) return;
        setFailed(true);
        if (
          error instanceof LocalDiningError &&
          [401, 403].includes(error.status)
        )
          onDenied();
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [
    context.api,
    context.scope.organization_id,
    context.scope.restaurant_id,
    context.scope.branch_id,
    filter,
  ]);
  const actor = (key: string, name: string | null = null) =>
    name ??
    (key.startsWith('member:')
      ? t('audit.member', { id: key.slice(7) })
      : t('audit.actor_' + key.slice(5), {
          defaultValue: t('audit.unknownAuthor'),
        }));
  const target = (row: HistoryEvent) => {
    const details = row.details;
    if (typeof details.table_id === 'number')
      return (
        context.data.tables?.find((table) => table.id === details.table_id)
          ?.code ?? t('d1.table') + ' #' + details.table_id
      );
    if (typeof details.reference_id === 'number')
      return context.data.references?.find(
        (reference) => reference.id === details.reference_id,
      )
        ? localized(
            context.data.references!.find(
              (reference) => reference.id === details.reference_id,
            )!.labels,
          )
        : t('d1.references') + ' #' + details.reference_id;
    if (row.request_id) return t('d1.reservation') + ' #' + row.request_id;
    if (Array.isArray(details.table_ids))
      return details.table_ids
        .filter((id): id is number => typeof id === 'number')
        .map(
          (id) =>
            context.data.tables?.find((table) => table.id === id)?.code ??
            '#' + id,
        )
        .join(' · ');
    const keys = [
      'occupation_id',
      'invoice_id',
      'receipt_id',
      'order_id',
      'visit_id',
      'membership_id',
      'policy_id',
      'calendar_id',
      'tariff_id',
      'combination_id',
      'link_id',
      'blackout_id',
      'quote_id',
      'confirmation_id',
      'human_confirmation_id',
      'presence_id',
      'outbox_id',
      'allocation_id',
      'identifier',
    ];
    const found = keys.find((key) => typeof details[key] === 'number');
    return found
      ? t('audit.target.' + found) + ' #' + String(details[found])
      : t('audit.missingTarget');
  };
  const value = (item: unknown) =>
    item === undefined
      ? t('audit.valueMissing')
      : typeof item === 'boolean'
        ? t(item ? 'd1.yes' : 'd1.no')
        : typeof item === 'string'
          ? i18n.exists('d1.state_' + item)
            ? t('d1.state_' + item)
            : item
          : JSON.stringify(item);
  return (
    <section>
      <header className={styles.sectionIntro}>
        <h2>{t('audit.title')}</h2>
        <p>{t('audit.pinned')}</p>
        <p>{t('audit.currentLabels')}</p>
      </header>
      <form
        className={styles.card}
        onSubmit={(event) => {
          event.preventDefault();
          setFilter({
            ...draft,
            page: 1,
            ...(data ? { snapshot: data.snapshot_id } : {}),
          });
        }}
      >
        <div className={styles.fields}>
          <label>
            {t('audit.from')}
            <input
              type="date"
              value={draft.from}
              onChange={(e) => setDraft({ ...draft, from: e.target.value })}
            />
          </label>
          <label>
            {t('audit.until')}
            <input
              type="date"
              min={draft.from || undefined}
              value={draft.until}
              onChange={(e) => setDraft({ ...draft, until: e.target.value })}
            />
          </label>
          <label>
            {t('audit.type')}
            <select
              aria-label={t('audit.type')}
              value={draft.kind}
              onChange={(e) => setDraft({ ...draft, kind: e.target.value })}
            >
              <option value="">{t('audit.all')}</option>
              {data?.kinds.map((kind) => (
                <option key={kind} value={kind}>
                  {t('audit.event.' + kind, {
                    defaultValue: t('audit.unknown'),
                  })}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('audit.author')}
            <select
              aria-label={t('audit.author')}
              value={draft.author}
              onChange={(e) => setDraft({ ...draft, author: e.target.value })}
            >
              <option value="">{t('audit.all')}</option>
              {data?.authors.map((row) => (
                <option key={row.key} value={row.key}>
                  {actor(row.key, row.name)}
                </option>
              ))}
            </select>
          </label>
          <Button type="submit" disabled={loading}>
            {t('audit.apply')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              const reset = { from: '', until: '', kind: '', author: '' };
              setDraft(reset);
              setFilter({ ...reset, page: 1 });
            }}
          >
            {t('audit.reset')}
          </Button>
        </div>
      </form>
      {loading && (
        <p role="status" className={styles.card}>
          {t('common.loading')}
        </p>
      )}
      {failed && (
        <p role="alert" className={styles.card}>
          {t('audit.failed')}
        </p>
      )}
      {data && (
        <>
          <div
            className={styles.table}
            role="region"
            aria-label={t('audit.title')}
            tabIndex={0}
          >
            <table>
              <thead>
                <tr>
                  {['date', 'action', 'target', 'author', 'reason'].map(
                    (key) => (
                      <th key={key}>
                        {t(
                          key === 'date' || key === 'reason'
                            ? 'd1.' + key
                            : 'audit.' + key,
                        )}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {data.items.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <time dateTime={row.occurred_at}>
                        {displayMoment(
                          row.occurred_at,
                          i18n.language,
                          context.data.policy?.timezone ?? 'UTC',
                        )}
                      </time>
                    </td>
                    <td>
                      {eventLabel(row, (key, options) =>
                        options ? t(key, options) : t(key),
                      )}
                      <details>
                        <summary>{t('audit.changes')}</summary>
                        {typeof row.details.capability === 'string' && (
                          <p>
                            {t('d1.capability')}:{' '}
                            {t('d1.cap_' + row.details.capability, {
                              defaultValue: t('audit.valueMissing'),
                            })}
                          </p>
                        )}
                        {recordedChanges(row).length ? (
                          recordedChanges(row).map((change, index) => (
                            <dl key={index}>
                              {change.field && (
                                <dt>
                                  {t(
                                    'd1.' +
                                      ({
                                        expected_end: 'expectedEnd',
                                        cleaning_expected_end: 'cleaning',
                                        initial_state: 'initialState',
                                      }[change.field] ?? change.field),
                                    { defaultValue: t('d1.state') },
                                  )}
                                </dt>
                              )}
                              <dt>{t('audit.previous')}</dt>
                              <dd>
                                <bdi>{value(change.before)}</bdi>
                              </dd>
                              <dt>{t('audit.next')}</dt>
                              <dd>
                                <bdi>{value(change.after)}</bdi>
                              </dd>
                            </dl>
                          ))
                        ) : (
                          <p>{t('audit.noChange')}</p>
                        )}
                      </details>
                      <details>
                        <summary>{t('audit.tech')}</summary>
                        <p>
                          {t('audit.code')}: <code>{row.kind}</code>
                        </p>
                        <p>
                          #{row.id} · <bdi>{row.author_key}</bdi>
                        </p>
                        <pre className={styles.auditJson}>
                          {JSON.stringify(row.details, null, 2)}
                        </pre>
                      </details>
                    </td>
                    <td>
                      <bdi>{target(row)}</bdi>
                    </td>
                    <td>
                      <bdi>{actor(row.author_key, row.author_name)}</bdi>
                      {row.author_name && (
                        <small className={styles.notice}>
                          {' '}
                          · {t('audit.currentName')}
                        </small>
                      )}
                    </td>
                    <td>
                      {typeof row.details.reason === 'string' &&
                      row.details.reason.trim() &&
                      !['-', '—', '–'].includes(row.details.reason.trim())
                        ? row.details.reason
                        : t('audit.reasonMissing')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!data.items.length && <p>{t('audit.empty')}</p>}
          </div>
          <nav className={styles.card} aria-label={t('audit.title')}>
            <p>{t('audit.page', { page: data.page, total: data.total })}</p>
            <div className={styles.row}>
              <Button
                type="button"
                variant="secondary"
                disabled={data.page <= 1}
                onClick={() =>
                  setFilter({
                    ...filter,
                    page: data.page - 1,
                    snapshot: data.snapshot_id,
                  })
                }
              >
                {t('audit.prev')}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={data.page * data.page_size >= data.total}
                onClick={() =>
                  setFilter({
                    ...filter,
                    page: data.page + 1,
                    snapshot: data.snapshot_id,
                  })
                }
              >
                {t('audit.more')}
              </Button>
            </div>
            {data.authors_truncated && <p>{t('audit.limit')}</p>}
          </nav>
        </>
      )}
    </section>
  );
}
