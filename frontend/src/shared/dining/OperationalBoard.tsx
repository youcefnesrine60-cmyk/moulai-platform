// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useState, type ReactNode, type ReactElement } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircle2,
  UtensilsCrossed,
  Sparkles,
  Wrench,
  Ban,
  CalendarCheck2,
  CalendarClock,
  Hourglass,
  Wallet,
  Clock3,
  TriangleAlert,
  HelpCircle,
  CalendarX2,
  Users,
  type LucideIcon,
} from 'lucide-react';
import { Button } from '../ui/primitives';
import {
  physicalStates,
  countPhysical,
  displayMoment,
  civilDay,
  type DisplayPhysical,
  type DiningTone,
  type OperationalBadgeKind,
  type OperationalPeriod,
  type OperationalTable,
} from './operational';
import styles from './operational.module.css';
import { DiningReference } from './reference';
import { RenderBoundary } from '../ui/RenderRecovery';
import { checkedDay, checkedTimezone, isWallClock } from './temporal';

const semantics: Readonly<
  Record<OperationalBadgeKind, { tone: DiningTone; icon: LucideIcon }>
> = {
  available: { tone: 'green', icon: CheckCircle2 },
  occupied: { tone: 'orange', icon: UtensilsCrossed },
  dirty: { tone: 'amber', icon: Sparkles },
  maintenance: { tone: 'purple', icon: Wrench },
  out_of_service: { tone: 'gray', icon: Ban },
  unknown: { tone: 'neutral', icon: HelpCircle },
  full: { tone: 'blue', icon: CalendarCheck2 },
  confirmed: { tone: 'blue', icon: CalendarCheck2 },
  hold: { tone: 'amber', icon: Hourglass },
  holdExpired: { tone: 'danger', icon: TriangleAlert },
  paymentPending: { tone: 'amber', icon: Wallet },
  paymentReview: { tone: 'amber', icon: Wallet },
  humanPending: { tone: 'neutral', icon: Clock3 },
  closed: { tone: 'neutral', icon: CalendarX2 },
  planningUnknown: { tone: 'neutral', icon: HelpCircle },
  planningOccupation: { tone: 'neutral', icon: Users },
};
/** Text, icon and theme-specific semantic colors always travel together. */
export function DiningBadge({
  kind,
  physical = false,
}: {
  kind: OperationalBadgeKind;
  physical?: boolean;
}): ReactElement {
  const { t } = useTranslation();
  const { tone, icon: Icon } = semantics[kind];
  return (
    <span
      className={styles.badge}
      data-ui-tone={tone}
      data-state={physical ? kind : undefined}
      data-testid={
        physical
          ? 'physical-badge'
          : kind === 'full'
            ? 'planning-full'
            : undefined
      }
    >
      <Icon size={16} aria-hidden="true" focusable="false" />
      <span>{t(`ops.${kind}`)}</span>
    </span>
  );
}
export function RequestBadges({
  status,
  badges,
  timezone = 'UTC',
  holdExpires,
  day,
}: {
  status: string;
  badges: readonly OperationalBadgeKind[];
  timezone?: string;
  holdExpires?: string | null;
  day?: string;
}): ReactElement {
  const { t, i18n } = useTranslation();
  return (
    <div className={styles.badges}>
      {status === 'confirmed' ? (
        <DiningBadge kind="confirmed" />
      ) : status === 'manual_review' ? (
        <span className={styles.badge} data-ui-tone="danger">
          <TriangleAlert size={16} aria-hidden="true" />
          {t('ops.manualReview')}
        </span>
      ) : status === 'held' ? null : (
        <span className={styles.badge} data-ui-tone="neutral">
          <Clock3 size={16} aria-hidden="true" />
          {t(`d1.state_${status}`)}
        </span>
      )}
      {badges.map((kind) => (
        <DiningBadge key={kind} kind={kind} />
      ))}
      {status === 'held' && (
        <span className={styles.expiry}>
          {t('ops.expires')}:{' '}
          {holdExpires ? (
            <bdi>
              {displayMoment(holdExpires, i18n.language, timezone, day)}
            </bdi>
          ) : (
            t('ops.notRecorded')
          )}
        </span>
      )}
    </div>
  );
}
function Period({
  period,
  locale,
  timezone,
  day,
}: {
  period: OperationalPeriod;
  day: string;
  locale: string;
  timezone: string;
}) {
  const { t } = useTranslation();
  const sameDay =
    (isWallClock(period.start) && isWallClock(period.end)) ||
    (civilDay(period.start, timezone) !== null &&
      civilDay(period.start, timezone) === civilDay(period.end, timezone));
  return (
    <div className={styles.period}>
      <DiningBadge
        kind={
          period.kind === 'reservation'
            ? 'confirmed'
            : period.kind === 'hold'
              ? 'hold'
              : period.kind === 'occupation'
                ? 'planningOccupation'
                : 'closed'
        }
      />
      <bdi>
        <time dateTime={period.start}>
          {displayMoment(
            period.start,
            locale,
            timezone,
            sameDay ? day : undefined,
          )}
        </time>{' '}
        –{' '}
        <time dateTime={period.end}>
          {displayMoment(
            period.end,
            locale,
            timezone,
            sameDay ? day : undefined,
          )}
        </time>
      </bdi>
      {period.kind === 'hold' && (
        <span>
          {t('ops.expires')}:{' '}
          {period.expires ? (
            <bdi>{displayMoment(period.expires, locale, timezone)}</bdi>
          ) : (
            t('ops.notRecorded')
          )}
        </span>
      )}
      {period.reason && (
        <span>
          {t('ops.blockReason')}: {period.reason}
        </span>
      )}
    </div>
  );
}

export function OperationalBoard(
  props: Parameters<typeof OperationalBoardContent>[0],
): ReactElement {
  return (
    <RenderBoundary>
      <OperationalBoardContent {...props} />
    </RenderBoundary>
  );
}
/** One board keeps current physical counts independent from the selected day's planning. */
function OperationalBoardContent({
  tables,
  day,
  timezone,
  physicalAsOf,
  actions,
}: {
  tables: readonly OperationalTable[];
  day: string;
  timezone: string;
  physicalAsOf?: string;
  actions?: (table: OperationalTable) => ReactNode;
}): ReactElement {
  const { t, i18n } = useTranslation();
  checkedTimezone(timezone);
  const planningDay = checkedDay(day);
  const [filter, setFilter] = useState<DisplayPhysical | 'all'>('all');
  const counts = countPhysical(tables);
  const number = (n: number) => new Intl.NumberFormat(i18n.language).format(n);
  const visible =
    filter === 'all'
      ? tables
      : tables.filter((table) => table.physical === filter);
  return (
    <section
      className={styles.board}
      data-testid="operational-board"
      aria-label={t('ops.board')}
    >
      <div className={styles.context}>
        <div>
          <h2>{t('ops.currentPhysical')}</h2>
          <p>
            {physicalAsOf ? (
              <>
                {t('ops.observedAt')}{' '}
                <bdi>
                  {displayMoment(physicalAsOf, i18n.language, timezone)}
                </bdi>
              </>
            ) : (
              t('ops.observationTimeMissing')
            )}
          </p>
        </div>
        <p>
          {t('ops.planningDate')}:{' '}
          <bdi>
            {new Intl.DateTimeFormat(i18n.language, {
              dateStyle: 'long',
              timeZone: 'UTC',
            }).format(planningDay)}
          </bdi>{' '}
          · <bdi>{timezone}</bdi>
        </p>
      </div>
      <p className={styles.note}>{t('ops.separationNote')}</p>
      <div
        className={styles.filters}
        role="group"
        aria-label={t('ops.filterPhysical')}
      >
        <button
          type="button"
          data-testid="physical-filter-all"
          aria-pressed={filter === 'all'}
          onClick={() => setFilter('all')}
        >
          {t('ops.all')}{' '}
          <span data-testid="physical-count-all" data-count={tables.length}>
            {number(tables.length)}
          </span>
        </button>
        {[
          ...physicalStates,
          ...(counts.unknown ? ['unknown' as const] : []),
        ].map((state) => {
          const Icon = semantics[state].icon;
          return (
            <button
              key={state}
              type="button"
              data-testid={`physical-filter-${state}`}
              aria-pressed={filter === state}
              onClick={() => setFilter(state)}
            >
              <Icon size={17} aria-hidden="true" />
              {t(`ops.${state}`)}{' '}
              <span
                data-testid={`physical-count-${state}`}
                data-count={counts[state]}
              >
                {number(counts[state])}
              </span>
            </button>
          );
        })}
        <Button
          type="button"
          variant="quiet"
          data-testid="physical-filter-reset"
          onClick={() => setFilter('all')}
        >
          {t('ops.reset')}
        </Button>
      </div>
      <details className={styles.legend}>
        <summary>{t('ops.legend')}</summary>
        <ul>
          {physicalStates.map((state) => (
            <li key={state}>
              <DiningBadge kind={state} />
              <span>{t(`ops.legend_${state}`)}</span>
            </li>
          ))}
        </ul>
        <p>{t('ops.legendPlanning')}</p>
      </details>
      <p className={styles.resultCount} role="status">
        {t('ops.results', { visible: visible.length, total: tables.length })}
      </p>
      {!visible.length ? (
        <div className={styles.empty} data-testid="physical-filter-empty">
          <p>{t(tables.length ? 'ops.noMatch' : 'ops.noTables')}</p>
          <Button
            type="button"
            variant="secondary"
            onClick={() => setFilter('all')}
          >
            {t('ops.reset')}
          </Button>
        </div>
      ) : (
        <div className={styles.grid}>
          {visible.map((table) => (
            <article
              key={table.id}
              className={styles.tableCard}
              data-state={table.physical}
              data-table-card
              data-testid={`table-card-${table.id}`}
              aria-labelledby={`dining-table-${table.id}`}
            >
              <header className={styles.tableHeader}>
                <h3 id={`dining-table-${table.id}`}>
                  <bdi>{table.code}</bdi>
                </h3>
                <DiningBadge kind={table.physical} physical />
              </header>
              <p className={styles.secondary}>
                {table.location ?? t('ops.locationMissing')} ·{' '}
                {t('ops.capacity')}:{' '}
                <bdi>
                  {number(table.capacity[0])}–{number(table.capacity[1])}
                </bdi>
              </p>
              {!!table.facts.length && (
                <dl className={styles.facts}>
                  {table.facts.slice(0, 2).map((fact) => (
                    <div key={fact.key ?? fact.label}>
                      <dt>{t(`ops.${fact.label}`)}</dt>
                      <dd>
                        {fact.value === null ? (
                          t('ops.notRecorded')
                        ) : fact.temporal ? (
                          <bdi>
                            {displayMoment(
                              fact.value,
                              i18n.language,
                              timezone,
                              physicalAsOf
                                ? (civilDay(physicalAsOf, timezone) ??
                                    undefined)
                                : undefined,
                            )}
                          </bdi>
                        ) : (
                          fact.value
                        )}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
              {table.facts.length > 2 && (
                <details className={styles.schedule}>
                  <summary>{t('ops.observationDetails')}</summary>
                  <dl className={styles.facts}>
                    {table.facts.slice(2).map((fact) => (
                      <div key={fact.key ?? fact.label}>
                        <dt>{t(`ops.${fact.label}`)}</dt>
                        <dd>
                          {fact.value === null
                            ? t('ops.notRecorded')
                            : fact.temporal
                              ? displayMoment(
                                  fact.value,
                                  i18n.language,
                                  timezone,
                                  physicalAsOf
                                    ? (civilDay(physicalAsOf, timezone) ??
                                        undefined)
                                    : undefined,
                                )
                              : fact.value}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </details>
              )}
              {table.alerts.map((alert) => (
                <p key={alert} className={styles.alert} data-ui-tone="danger">
                  <TriangleAlert size={18} aria-hidden="true" />
                  <span>{t(`ops.${alert}`)}</span>
                </p>
              ))}
              <section
                className={styles.planning}
                aria-label={t('ops.tablePlanning', { table: table.code })}
              >
                <h4>
                  <CalendarClock size={16} aria-hidden="true" />
                  {t('ops.planningLabel')}
                </h4>
                <div className={styles.badges}>
                  {!table.planningKnown ? (
                    <DiningBadge kind="planningUnknown" />
                  ) : (
                    <>
                      {table.fullyReserved && <DiningBadge kind="full" />}
                      {table.closed && <DiningBadge kind="closed" />}
                    </>
                  )}
                </div>
                {table.nextReservation && (
                  <p className={styles.next}>
                    <strong>{t('ops.nextReservation')}</strong>
                    <bdi>
                      {displayMoment(
                        table.nextReservation.start,
                        i18n.language,
                        timezone,
                        civilDay(table.nextReservation.start, timezone) ===
                          civilDay(table.nextReservation.end, timezone)
                          ? day
                          : undefined,
                      )}{' '}
                      –{' '}
                      {displayMoment(
                        table.nextReservation.end,
                        i18n.language,
                        timezone,
                        civilDay(table.nextReservation.start, timezone) ===
                          civilDay(table.nextReservation.end, timezone)
                          ? day
                          : undefined,
                      )}
                    </bdi>
                  </p>
                )}
                {table.planningKnown &&
                  !table.periods.length &&
                  !table.fullyReserved &&
                  !table.closed && <p>{t('ops.noRegisteredClaim')}</p>}
                {!!table.periods.length && (
                  <details className={styles.schedule}>
                    <summary>
                      {t('ops.recordedPeriods', {
                        count: table.periods.length,
                      })}
                    </summary>
                    {table.periods.map((period, index) => (
                      <Period
                        key={index}
                        period={period}
                        locale={i18n.language}
                        timezone={timezone}
                        day={day}
                      />
                    ))}
                  </details>
                )}
              </section>
              {!!table.requests.length && (
                <section
                  className={styles.requests}
                  aria-label={t('ops.requests')}
                >
                  <h4>{t('ops.requests')}</h4>
                  {table.requests.map((request) => (
                    <div key={request.reference}>
                      <DiningReference
                        reference={request.reference}
                        {...(request.id ? { id: request.id } : {})}
                      />
                      <RequestBadges
                        status={request.status}
                        badges={request.badges}
                        timezone={timezone}
                        holdExpires={request.holdExpires ?? null}
                        day={day}
                      />
                    </div>
                  ))}
                </section>
              )}
              <footer className={styles.actions}>
                {actions ? actions(table) : <span>{t('ops.readOnly')}</span>}
              </footer>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
