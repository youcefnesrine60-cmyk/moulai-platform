// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { Fragment } from 'react';
import { createPortal } from 'react-dom';
import { useParams } from 'react-router';
import { useEffect, useState, useId, type ReactNode } from 'react';
import { LocalDiningError } from '../../../shared/dining/local/client';
import { useWorkspace } from './useWorkspace';
import shell from '../../../app/shell.module.css';
import { DiningReference } from '../../../shared/dining/reference';
import { shortReference } from '../../../shared/dining/referenceValue';
import { displayMoment } from '../../../shared/dining/operational';
import { localSections } from './navigation';
import { useTranslation } from 'react-i18next';
import { BrandCanvas } from '../../../shared/ui/BrandCanvas';
import {
  Brand,
  AppearanceControls,
  Button,
} from '../../../shared/ui/primitives';
import {
  ReferenceForm,
  TableForm,
  PolicyForm,
  CalendarForm,
  TariffForm,
  GrantForm,
  CombinationForm,
  BlackoutForm,
} from './ConfigurationForms';
import {
  RequestForm,
  SelectionForm,
  QuoteForm,
  ConsentForm,
  HoldForm,
  ProofForm,
  ConfirmationForm,
  CancelForm,
  SignalForm,
} from './ServiceForms';
import {
  ReceiptForm,
  InvoiceForm,
  FinalizeInvoiceForm,
  AllocationForm,
} from './FinanceForms';
import {
  Field,
  Pick,
  Text,
  FormBox,
  command,
  requestOptions,
  useValues,
  integer,
  amount,
  type FormContext,
} from './fields';
import {
  OperationalBoard,
  RequestBadges,
} from '../../../shared/dining/OperationalBoard';
import { localTablePresentation, requestPresentation } from './presentation';
import styles from './local.module.css';
import { TableActions } from './TableActions';
import { VisitForms } from './VisitForms';
import { StaffForms, PersonalInvitations } from './StaffForms';
import { HelpDesk } from './HelpDesk';
import { HelpLink } from './HelpLink';
import { HistoryPanel } from './HistoryPanel';
import { ElementHelp } from './ElementHelp';
import { SettlementForm } from './SettlementForm';

function DataTable({
  label,
  columns,
  rows,
  emptyMessage = 'd1.noRows',
}: {
  label: string;
  emptyMessage?: string;
  columns: readonly string[];
  rows: readonly (readonly ReactNode[])[];
}) {
  const { t } = useTranslation();
  return (
    <div
      className={styles.table}
      role="region"
      aria-label={t(`d1.${label}`)}
      tabIndex={0}
    >
      <table>
        <caption>{t(`d1.${label}`)}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} scope="col">
                {t(`d1.${column}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {row.map((cell, n) => (
                <td key={n}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && <p>{t(emptyMessage)}</p>}
    </div>
  );
}

/** This page exists only in the loopback dining mode; it never falls back to simulations. */
export function LocalDiningPage() {
  return <DiningWorkspace />;
}
export function IntegratedDiningPage() {
  const params = useParams();
  return (
    <DiningWorkspace
      operational
      organizationId={Number(params.organizationId)}
      restaurantId={Number(params.restaurantId)}
    />
  );
}
function DiningWorkspace({
  operational: requestedOperational = false,
  organizationId,
  restaurantId,
}: {
  operational?: boolean;
  organizationId?: number;
  restaurantId?: number;
}) {
  const operational =
    import.meta.env.MODE === 'staging' || requestedOperational;
  const { t, i18n } = useTranslation();
  const openId = useId(),
    closeId = useId();
  const {
    api,
    session,
    actor,
    setActor,
    scope,
    data,
    busy,
    error,
    success,
    committedStale,
    tab,
    setTab,
    day,
    planning,
    planningError,
    result,
    run,
    signIn,
    signOut,
    changeScope,
    selectDay,
    reload,
  } = useWorkspace({
    operational,
    ...(organizationId ? { organizationId } : {}),
    ...(restaurantId ? { restaurantId } : {}),
  });
  const Canvas = operational ? Fragment : BrandCanvas;
  const MainRegion = operational ? 'section' : 'main';
  const [helpHost, setHelpHost] = useState<HTMLElement | null>(null);
  useEffect(() => {
    if (operational)
      setHelpHost(document.getElementById('operational-help-slot'));
  }, [operational]);
  const [selectedTableId, setSelectedTableId] = useState<number | null>(null);
  useEffect(() => setSelectedTableId(null), [session, scope]);
  const [requestSearch, setRequestSearch] = useState('');
  const context: FormContext | null =
    scope && data ? { api, scope, data, busy, run } : null;
  const has = (capability: string) =>
    Boolean(data?.capabilities.includes(capability));
  const sections = localSections(data?.capabilities ?? []);
  const activeTab = sections.includes(tab) ? tab : 'planning';
  const date = (value: string) =>
    displayMoment(value, i18n.language, data?.policy?.timezone ?? 'UTC');
  const err =
    error instanceof LocalDiningError
      ? error.status === 401
        ? 'sessionExpired'
        : error.status >= 500
          ? 'loadFailed'
          : error.status === 403
            ? 'permissionRefused'
            : error.status === 422
              ? 'invalidInput'
              : 'operationRefused'
      : 'loadFailed';
  const navigation = (desktop: boolean) => (
    <nav
      className={desktop ? shell.sidebarInterior : styles.tabs}
      aria-label={t('d1.sections')}
    >
      {desktop && (
        <p className={styles.sidebarTitle}>
          <bdi dir="ltr">MoulAI™</bdi>
          <span>{t('d1.title')}</span>
        </p>
      )}
      {sections.map((name) => (
        <button
          type="button"
          key={name}
          className={
            desktop
              ? `${shell.navLink} ${activeTab === name ? shell.navActive : ''} ${styles.navButton}`
              : styles.tabButton
          }
          aria-pressed={activeTab === name}
          disabled={!data || busy}
          onClick={() => setTab(name)}
        >
          {t(`d1.section_${name}`)}
        </button>
      ))}
    </nav>
  );
  const helpContent = (
    <HelpDesk
      operational={operational}
      key={`${session?.actor}:${scope?.branch_id}:${data?.capabilities.join(',')}`}
      section={data ? activeTab : 'unscoped'}
      role={scope?.role ?? 'none'}
      capabilities={data?.capabilities ?? []}
      permissionsKnown={!!data}
      policyPresent={data ? !!data.policy : null}
      tables={data?.tables ?? []}
      selectedTable={selectedTableId}
      busy={busy}
      errorCode={error instanceof LocalDiningError ? error.code : null}
    />
  );
  return (
    <Canvas>
      <div className={operational ? styles.integratedFrame : shell.frame}>
        {!operational && (
          <aside className={shell.desktopSidebar}>{navigation(true)}</aside>
        )}
        <div className={operational ? styles.integratedBody : shell.body}>
          <MainRegion
            id={operational ? 'dining-workspace' : 'main-content'}
            tabIndex={-1}
            className={styles.page}
          >
            {operational ? (
              helpHost ? (
                createPortal(helpContent, helpHost)
              ) : null
            ) : (
              <header className={`${shell.header} ${styles.header}`}>
                <div className={styles.compactBrand}>
                  <Brand />
                </div>
                <div
                  className={styles.headerControls}
                  data-testid="header-controls"
                  dir={i18n.language === 'ar' ? 'rtl' : 'ltr'}
                >
                  {helpContent}
                  <AppearanceControls />
                </div>
              </header>
            )}

            <section className={styles.intro}>
              <h1>{t('d1.title')}</h1>
              <p className={styles.reviewNotice}>
                {t(operational ? 'integration.notice' : 'd1.localNotice')}
              </p>
              <section
                className={styles.activeContext}
                aria-label={t('d1.activeSession')}
                data-testid="active-session"
              >
                <p>
                  <strong>{t('d1.activeSession')}:</strong>{' '}
                  {session ? (
                    operational ? (
                      <bdi>{session.actor}</bdi>
                    ) : (
                      t(`d1.actor_${session.actor}`)
                    )
                  ) : (
                    t('d1.noSession')
                  )}
                </p>
                <p>
                  <strong>{t('d1.restaurant')}:</strong>{' '}
                  <bdi>{scope?.restaurant_name ?? t('d1.chooseScope')}</bdi> ·{' '}
                  <strong>{t('d1.branch')}:</strong>{' '}
                  <bdi>{scope?.branch_name ?? t('d1.chooseScope')}</bdi>
                </p>
              </section>
              {!operational && (
                <details className={styles.environment}>
                  <summary>{t('ops.environmentDetails')}</summary>
                  <p>{t('d1.realPersistence')}</p>
                  <p>{t('d1.identitySimulation')}</p>
                  <p>{t('d1.noRealFunds')}</p>
                  {scope && (
                    <p>
                      <bdi>
                        Restaurant #{scope.restaurant_id} / Branch #
                        {scope.branch_id}
                      </bdi>
                    </p>
                  )}
                </details>
              )}
              <details
                className={styles.sessionControls}
                data-testid="session-settings"
                open={!session || !scope}
              >
                <summary>
                  {session ? (
                    <>
                      {t('d1.signedIdentity')}:{' '}
                      {operational ? (
                        <bdi>{session.actor}</bdi>
                      ) : (
                        t(`d1.actor_${session.actor}`)
                      )}
                    </>
                  ) : (
                    t('ops.sessionSettings')
                  )}
                </summary>
                {!operational && (
                  <>
                    {' '}
                    <form
                      aria-label={t('d1.localIdentity')}
                      onSubmit={(event) => {
                        event.preventDefault();
                        void signIn();
                      }}
                      className={styles.sessionForm}
                    >
                      <Pick
                        label="testProfile"
                        name="actor"
                        value={actor}
                        set={setActor}
                        disabled={busy}
                        options={[
                          'owner',
                          'service',
                          'cleaner',
                          'collector',
                          'finance',
                          'finance_reader',
                          'kitchen',
                          'service_cleaner',
                          'canceller',
                          'assistant',
                          'customer',
                          'outsider',
                          'new_employee',
                        ].map((value) => ({
                          value,
                          label: t(`d1.actor_${value}`),
                        }))}
                      />
                      <div className={styles.sessionActions}>
                        <div className={styles.sessionAction}>
                          <Button
                            id={openId}
                            data-help-label="signIn"
                            data-help-action="session-open"
                            data-testid="session-open"
                            disabled={busy}
                          >
                            {t('d1.signIn')}
                          </Button>
                          <ElementHelp targetId={openId} labelKey="signIn" />
                        </div>
                        {session && (
                          <div className={styles.sessionAction}>
                            <Button
                              id={closeId}
                              data-help-label="signOut"
                              data-help-action="session-close"
                              data-testid="session-close"
                              type="button"
                              variant="secondary"
                              disabled={busy}
                              onClick={() => void signOut()}
                            >
                              {t('d1.signOut')}
                            </Button>
                            <ElementHelp
                              targetId={closeId}
                              labelKey="signOut"
                            />
                          </div>
                        )}
                      </div>
                    </form>
                    {session && actor !== session.actor && (
                      <p role="status" data-testid="pending-profile">
                        {t('d1.pendingProfile')}
                      </p>
                    )}
                  </>
                )}
                {session && !session.scopes.length && (
                  <p>{t('d1.permissionRefused')}</p>
                )}
                {session && (
                  <Pick
                    label="authorizedBranch"
                    name="branch"
                    value={scope ? String(scope.branch_id) : ''}
                    set={changeScope}
                    disabled={busy}
                    options={session.scopes.map((row) => ({
                      value: String(row.branch_id),
                      label: `${row.restaurant_name ?? t('d1.restaurant')} / ${row.branch_name ?? t('d1.branch')}`,
                    }))}
                  />
                )}
              </details>
            </section>
            {session &&
              session.actor !== 'customer' &&
              session.actor !== 'assistant' && (
                <PersonalInvitations key={session.actor} api={api} />
              )}
            {error !== null && (
              <div role="alert" className={`${styles.banner} ${styles.error}`}>
                {t(`d1.${err}`)}
                <HelpLink resolve />
                {scope && (
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void reload()}
                  >
                    {t('d1.reload')}
                  </Button>
                )}
              </div>
            )}
            {committedStale && (
              <p role="alert" className={styles.banner}>
                {t('d1.committedStale')}
              </p>
            )}
            {success && (
              <div role="status" className={styles.banner}>
                {t('d1.persistedReloaded')}
              </div>
            )}
            {scope && !data && !error && (
              <p role="status">{t('common.loading')}</p>
            )}
            {context && data && (
              <div
                key={`${session?.actor}:${scope?.branch_id}`}
                className={styles.workspace}
              >
                {data.tables?.some((row) =>
                  row.name?.startsWith('VISUAL FIXTURE'),
                ) && <p className={styles.banner}>{t('d1.visualSnapshots')}</p>}
                <section
                  className={styles.accessBar}
                  data-testid="effective-permissions"
                >
                  <details>
                    <summary>
                      {t('d1.permissionsVerified')}: {data.capabilities.length}
                    </summary>
                    <p>
                      {data.capabilities
                        .map((cap) => t(`d1.cap_${cap}`))
                        .join(' · ')}
                    </p>
                    {data.policy && (
                      <p>
                        {t('d1.timezone')}: <bdi>{data.policy.timezone}</bdi>
                      </p>
                    )}
                  </details>
                  {!data.policy && !has('customer') && (
                    <p>{t('d1.policyRequired')}</p>
                  )}
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void reload()}
                  >
                    {t('d1.reload')}
                  </Button>
                </section>
                <div className={styles.mobileNavigation}>
                  {navigation(false)}
                </div>
                {activeTab === 'planning' && (
                  <>
                    {!has('customer') && (
                      <section className={styles.planningPanel}>
                        <div className={styles.planningToolbar}>
                          <Field
                            label="date"
                            name="planning_date"
                            type="date"
                            value={day}
                            set={selectDay}
                          />
                        </div>
                        {planningError && <p>{t('d1.planningUnavailable')}</p>}
                        {data.policy && day ? (
                          <OperationalBoard
                            key={context.scope.branch_id}
                            tables={localTablePresentation(
                              data,
                              planning,
                              day,
                              i18n.language === 'ar'
                                ? 'ar'
                                : i18n.language === 'en'
                                  ? 'en'
                                  : 'fr',
                            )}
                            day={day}
                            timezone={data.policy?.timezone ?? 'UTC'}
                            {...(data.server_time
                              ? { physicalAsOf: data.server_time }
                              : {})}
                            {...(has('service') || has('clean')
                              ? {
                                  actions: (table) => (
                                    <Button
                                      type="button"
                                      variant="quiet"
                                      onClick={() => {
                                        setSelectedTableId(table.id);
                                        requestAnimationFrame(() => {
                                          const target =
                                            document.getElementById(
                                              'dining-physical-actions',
                                            );
                                          target?.focus();
                                          target?.scrollIntoView({
                                            block: 'start',
                                          });
                                        });
                                      }}
                                    >
                                      {t('ops.authorizedActions')}
                                    </Button>
                                  ),
                                }
                              : {})}
                          />
                        ) : (
                          <p role="status">{t('d1.policyRequired')}</p>
                        )}
                      </section>
                    )}
                    <TableActions
                      context={context}
                      tableId={selectedTableId}
                      clear={() => setSelectedTableId(null)}
                    />
                    {has('service') || has('assistant') ? (
                      <section className={styles.card}>
                        <h2>{t('d1.deadlines')}</h2>
                        <p>{t('d1.noDelivery')}</p>
                        <Button
                          disabled={busy}
                          onClick={() =>
                            void run(() =>
                              command(context, { operation: 'scan_deadlines' }),
                            )
                          }
                        >
                          {t('d1.scan')}
                        </Button>
                      </section>
                    ) : null}
                  </>
                )}
                {activeTab === 'visits' && sections.includes('visits') && (
                  <VisitForms context={context} />
                )}
                {activeTab === 'staff' && has('configure') && (
                  <StaffForms context={context} />
                )}
                {activeTab === 'configuration' && has('configure') && (
                  <>
                    <PolicyForm context={context} />
                    <ReferenceForm context={context} />
                    <TableForm context={context} />
                    <CombinationForm context={context} />
                    <CalendarForm context={context} />
                    <TariffForm context={context} />
                    <GrantForm context={context} />
                    <BlackoutForm context={context} />
                    <DataTable
                      label="references"
                      columns={['referenceKind', 'code', 'fr', 'en', 'ar']}
                      rows={(data.references ?? []).map((row) => [
                        t(`d1.${row.kind}`),
                        row.code,
                        row.labels.fr,
                        row.labels.en,
                        row.labels.ar,
                      ])}
                    />
                    <DataTable
                      label="calendar"
                      columns={['weekday', 'date', 'services']}
                      rows={(data.calendar ?? []).map((row) => [
                        row.weekday === null ? '—' : t(`d1.day${row.weekday}`),
                        row.service_date ?? '—',
                        row.windows
                          .map(
                            (w) =>
                              `${w.start}–${w.end}${w.next_day ? ' +1' : ''}`,
                          )
                          .join(' / ') || t('d1.closed'),
                      ])}
                    />
                    <DataTable
                      label="tariffs"
                      columns={[
                        'pricingRef',
                        'component',
                        'currency',
                        'exactUnitPrice',
                        'validFrom',
                        'validUntilOptional',
                      ]}
                      rows={(data.tariffs ?? []).map((row) => [
                        row.reference,
                        t(`d1.${row.component}`),
                        row.currency,
                        row.unit_price,
                        date(row.valid_from),
                        row.valid_until ? date(row.valid_until) : '—',
                      ])}
                    />
                    <DataTable
                      label="permissions"
                      columns={['person', 'capability', 'actorKind', 'active']}
                      rows={(data.grants ?? []).map((row) => [
                        `#${row.membership_id}`,
                        t(`d1.cap_${row.capability}`),
                        t(`d1.${row.actor_kind}`),
                        t(row.active ? 'd1.yes' : 'd1.no'),
                      ])}
                    />
                    <DataTable
                      label="blackouts"
                      columns={['reason', 'start', 'end', 'active', 'action']}
                      rows={(data.blackouts ?? []).map((row) => [
                        row.reason,
                        date(row.starts_at),
                        date(row.ends_at),
                        t(row.active ? 'd1.yes' : 'd1.no'),
                        row.active ? (
                          <Button
                            disabled={busy}
                            onClick={() =>
                              void run(() =>
                                command(context, {
                                  operation: 'close_blackout',
                                  identifier: row.id,
                                }),
                              )
                            }
                          >
                            {t('d1.closeBlock')}
                          </Button>
                        ) : (
                          '—'
                        ),
                      ])}
                    />
                  </>
                )}
                {activeTab === 'requests' && sections.includes('requests') && (
                  <>
                    <section className={styles.card}>
                      <Field
                        label="findReference"
                        name="request_search"
                        value={requestSearch}
                        set={setRequestSearch}
                        required={false}
                      />
                    </section>
                    <DataTable
                      label="requests"
                      emptyMessage={requestSearch ? 'ops.noMatch' : 'd1.noRows'}
                      columns={[
                        'reference',
                        'customerName',
                        'party',
                        'start',
                        'end',
                        'state',
                        'confirmation',
                      ]}
                      rows={(data.requests ?? [])
                        .filter(
                          (row) =>
                            !requestSearch.trim() ||
                            shortReference(row.id)
                              .toLowerCase()
                              .includes(requestSearch.trim().toLowerCase()) ||
                            row.reference
                              .toLowerCase()
                              .includes(requestSearch.trim().toLowerCase()),
                        )
                        .map((row) => [
                          <DiningReference
                            id={row.id}
                            reference={row.reference}
                          />,
                          row.customer_name ?? '—',
                          row.party_size,
                          date(row.starts_at),
                          date(row.ends_at),
                          <RequestBadges
                            status={row.status}
                            badges={requestPresentation(data, row)}
                            timezone={data.policy?.timezone ?? 'UTC'}
                            holdExpires={
                              data.claims?.find(
                                (claim) =>
                                  claim.request_id === row.id &&
                                  claim.active &&
                                  claim.kind === 'hold',
                              )?.expires_at ?? null
                            }
                          />,
                          ['confirmed', 'arrived', 'served'].includes(
                            row.status,
                          ) &&
                          (has('customer') ||
                            (has('finance.read') &&
                              (has('service') || has('configure')))) ? (
                            <a
                              href={api.printUrl(
                                context.scope,
                                row.id,
                                i18n.language,
                              )}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {t('d1.consultPrint')}
                            </a>
                          ) : (
                            '—'
                          ),
                        ])}
                    />
                    {has('customer') ? (
                      <>
                        <ConsentForm context={context} customer />
                        <CustomerCancellation context={context} />
                      </>
                    ) : (
                      <>
                        {(has('service') || has('assistant')) && (
                          <>
                            <RequestForm context={context} />
                            <SelectionForm context={context} />
                            <QuoteForm context={context} />
                            <HoldForm context={context} />
                            <SignalForm context={context} />
                          </>
                        )}
                        {has('service') && (
                          <>
                            <ConsentForm context={context} />
                            <ProofForm context={context} />
                            <ConfirmationForm context={context} />
                          </>
                        )}
                        {has('assistant') && (
                          <ConfirmationForm context={context} assistant />
                        )}
                        {has('reservations.cancel_before_arrival') && (
                          <CancelForm context={context} />
                        )}
                      </>
                    )}
                    <DataTable
                      label="proposals"
                      columns={[
                        'proposal',
                        'reservation',
                        'currency',
                        'amount',
                        'proposalExpires',
                      ]}
                      rows={(data.quotes ?? []).map((row) => [
                        `#${row.id} / v${row.version}`,
                        `#${row.request_id}`,
                        row.currency,
                        amount(
                          row.amount,
                          row.components[0]?.currency_precision,
                        ),
                        date(row.expires_at),
                      ])}
                    />
                    {result &&
                      Object.keys(result).some((key) =>
                        key.startsWith('instruction_'),
                      ) && (
                        <section className={styles.card}>
                          <h2>{t('d1.paymentInstructions')}</h2>
                          {Object.entries(result)
                            .filter(
                              ([key, value]) =>
                                key.startsWith('instruction_') &&
                                typeof value === 'string',
                            )
                            .map(([key, value]) => (
                              <p key={key}>
                                {key.slice(12)} : {String(value)}
                              </p>
                            ))}
                        </section>
                      )}
                  </>
                )}
                {activeTab === 'finance' && has('finance.read') && (
                  <>
                    {has('collect') && (
                      <>
                        <ReceiptForm context={context} />
                        {operational && <SettlementForm context={context} />}
                        {has('advances.allocate') && (
                          <AllocationForm context={context} />
                        )}
                      </>
                    )}
                    {has('invoices.create') && (
                      <InvoiceForm context={context} />
                    )}
                    {has('invoices.finalize') && (
                      <FinalizeInvoiceForm context={context} />
                    )}
                    {has('advances.allocate') && !has('collect') && (
                      <AllocationForm context={context} />
                    )}
                    <DataTable
                      label="receipts"
                      columns={[
                        'receiptReference',
                        'reservation',
                        'amount',
                        'currency',
                        'state',
                      ]}
                      rows={(data.receipts ?? []).map((row) => [
                        row.reference ?? `#${row.id}`,
                        `#${row.request_id}`,
                        amount(
                          row.received_amount,
                          data.policy?.currencies[row.currency],
                        ),
                        row.currency,
                        t(`d1.state_${row.status}`),
                      ])}
                    />
                    <DataTable
                      label="invoices"
                      columns={[
                        'invoice',
                        'reservation',
                        'state',
                        'salesTotal',
                        'appliedAdvance',
                        'balance',
                      ]}
                      rows={(data.invoices ?? []).map((row) => {
                        const allocation = data.allocations?.find(
                          (credit) => credit.invoice_id === row.id,
                        );
                        return [
                          `#${row.id}`,
                          row.request_id !== null
                            ? `#${row.request_id}`
                            : t('d1.occupation') + ' #' + row.occupation_id,
                          t(`d1.state_${row.status}`),
                          <bdi>
                            {amount(row.total, row.precision)} {row.currency}
                          </bdi>,
                          allocation ? (
                            <bdi>
                              {amount(allocation.amount, row.precision)}{' '}
                              {allocation.currency}
                            </bdi>
                          ) : (
                            t('d1.unallocated')
                          ),
                          allocation ? (
                            <bdi>
                              {amount(allocation.balance, row.precision)}{' '}
                              {allocation.currency}
                            </bdi>
                          ) : (
                            t('d1.notFinalized')
                          ),
                        ];
                      })}
                    />
                    <p>{t('d1.noRefund')}</p>
                  </>
                )}
                {activeTab === 'history' && sections.includes('history') && (
                  <>
                    <HistoryPanel
                      context={context}
                      onDenied={() => void reload()}
                    />
                    <p>{t('d1.noDelivery')}</p>
                    <DataTable
                      label="outbox"
                      columns={['event', 'state', 'attempts']}
                      rows={(data.outbox ?? []).map((row) => [
                        <>
                          <span>
                            {t('audit.event.' + row.event_key, {
                              defaultValue: t('audit.unknown'),
                            })}
                          </span>
                          <details>
                            <summary>{t('audit.tech')}</summary>
                            <code>{row.event_key}</code>
                          </details>
                        </>,
                        t(`d1.state_${row.status}`),
                        row.attempts,
                      ])}
                    />
                  </>
                )}
              </div>
            )}
          </MainRegion>
        </div>
      </div>
    </Canvas>
  );
}

function CustomerCancellation({ context }: { context: FormContext }) {
  const v = useValues({ request: '', reason: '' });
  return (
    <FormBox
      context={context}
      title="requestCancellation"
      operation="customer_cancellation"
      submit={() =>
        context.api.requestCancellation(
          context.scope,
          integer(v.get('request')),
          v.get('reason'),
        )
      }
    >
      <Pick
        label="reservation"
        name="request"
        value={v.get('request')}
        set={(value) => v.set('request', value)}
        options={requestOptions(context)}
      />
      <Text
        label="reason"
        name="reason"
        value={v.get('reason')}
        set={(value) => v.set('reason', value)}
      />
    </FormBox>
  );
}
