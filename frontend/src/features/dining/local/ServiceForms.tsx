// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { z } from 'zod';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { localized } from '../../../shared/i18n';
import { Button } from '../../../shared/ui/primitives';
import {
  Field,
  Text,
  Check,
  Pick,
  Multi,
  Instant,
  FormBox,
  command,
  integer,
  nullableId,
  ids,
  tableOptions,
  requestOptions,
  quoteOptions,
  receiptOptions,
  useValues,
  type FormContext,
} from './fields';
import styles from './local.module.css';

const matching = z.object({
  table_ids: z.array(z.number().int().positive()),
  availability_confirmed: z.literal(false),
});

export function RequestForm({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const v = useValues({
    customer: '',
    contact: '',
    start: '',
    fold: '',
    minutes: '',
    party: '',
    event: '',
    zone: '',
    category: '',
  });
  const [tables, setTables] = useState<string[]>([]);
  const [views, setViews] = useState<string[]>([]);
  const [proximities, setProximities] = useState<string[]>([]);
  const [features, setFeatures] = useState<string[]>([]);
  const [preparation, setPreparation] = useState(false);
  const [menu, setMenu] = useState<{ product: string; quantity: string }[]>([]);
  const refs = (kind: string) =>
    (context.data.references ?? [])
      .filter((row) => row.kind === kind && row.active)
      .map((row) => ({ value: String(row.id), label: localized(row.labels) }));
  return (
    <FormBox
      context={context}
      title="request"
      operation="request"
      submit={async () =>
        command(context, {
          operation: 'request',
          data: {
            customer_name: v.get('customer'),
            contact: v.get('contact'),
            starts_at: await context.api.instant(
              context.scope,
              v.get('start'),
              v.get('fold'),
            ),
            duration_seconds: integer(v.get('minutes')) * 60,
            party_size: integer(v.get('party')),
            table_ids: ids(tables),
            criteria: {
              view_ids: ids(views),
              proximity_ids: ids(proximities),
              feature_ids: ids(features),
              ...(v.get('zone') ? { zone_id: integer(v.get('zone')) } : {}),
              ...(v.get('category')
                ? { category_id: integer(v.get('category')) }
                : {}),
            },
            event_id: nullableId(v.get('event')),
            preparation,
            menu: menu.map((row) => ({
              product_id: integer(row.product),
              quantity: row.quantity,
            })),
          },
        })
      }
    >
      <Field
        label="customerName"
        name="customer"
        value={v.get('customer')}
        set={(value) => v.set('customer', value)}
      />
      <Field
        label="contact"
        name="contact"
        value={v.get('contact')}
        set={(value) => v.set('contact', value)}
      />
      <Instant
        label="start"
        name="start"
        value={v.get('start')}
        set={(value) => v.set('start', value)}
        fold={v.get('fold')}
        setFold={(value) => v.set('fold', value)}
      />
      <Field
        label="durationMinutes"
        name="minutes"
        type="number"
        value={v.get('minutes')}
        set={(value) => v.set('minutes', value)}
      />
      <Field
        label="party"
        name="party"
        type="number"
        value={v.get('party')}
        set={(value) => v.set('party', value)}
      />
      <Multi
        label="tables"
        name="tables"
        values={tables}
        set={setTables}
        options={tableOptions(context)}
      />
      <Pick
        label="zoneOptional"
        name="zone"
        value={v.get('zone')}
        set={(value) => v.set('zone', value)}
        options={refs('zone')}
        required={false}
      />
      <Pick
        label="categoryOptional"
        name="category"
        value={v.get('category')}
        set={(value) => v.set('category', value)}
        options={refs('category')}
        required={false}
      />
      <Multi
        label="view"
        name="views"
        values={views}
        set={setViews}
        options={refs('view')}
      />
      <Multi
        label="proximity"
        name="proximities"
        values={proximities}
        set={setProximities}
        options={refs('proximity')}
      />
      <Multi
        label="feature"
        name="features"
        values={features}
        set={setFeatures}
        options={refs('feature')}
      />
      <Pick
        label="event"
        name="event"
        value={v.get('event')}
        set={(value) => v.set('event', value)}
        options={refs('event')}
        required={false}
      />
      <Check
        label="preparationRequested"
        name="preparation"
        value={preparation}
        set={setPreparation}
      />
      <div className={styles.wide}>
        <h3>{t('d1.specialMenu')}</h3>
        {menu.map((row, index) => (
          <div key={index} className={styles.row}>
            <Pick
              label="product"
              name={`menu_product_${index}`}
              value={row.product}
              set={(value) =>
                setMenu((rows) =>
                  rows.map((item, n) =>
                    n === index ? { ...item, product: value } : item,
                  ),
                )
              }
              options={(context.data.products ?? [])
                .filter((row) => row.is_available)
                .map((row) => ({ value: String(row.id), label: row.name }))}
            />
            <Field
              label="quantity"
              name={`menu_quantity_${index}`}
              value={row.quantity}
              set={(value) =>
                setMenu((rows) =>
                  rows.map((item, n) =>
                    n === index ? { ...item, quantity: value } : item,
                  ),
                )
              }
            />
            <Button
              type="button"
              variant="quiet"
              onClick={() =>
                setMenu((rows) => rows.filter((_, n) => n !== index))
              }
            >
              {t('d1.remove')}
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="secondary"
          onClick={() =>
            setMenu((rows) => [...rows, { product: '', quantity: '' }])
          }
        >
          {t('d1.addDish')}
        </Button>
      </div>
    </FormBox>
  );
}

export function SelectionForm({ context }: { context: FormContext }) {
  const [request, setRequest] = useState('');
  const [tables, setTables] = useState<string[]>([]);
  const [matches, setMatches] = useState<number[]>([]);
  const { t } = useTranslation();
  return (
    <FormBox
      context={context}
      title="selection"
      operation="select_tables"
      submit={() =>
        command(context, {
          operation: 'select_tables',
          request_id: integer(request),
          table_ids: ids(tables),
        })
      }
    >
      <Pick
        label="reservation"
        name="request"
        value={request}
        set={setRequest}
        options={requestOptions(context)}
      />
      <Button
        type="button"
        variant="secondary"
        onClick={() =>
          void context.run(async () => {
            const value = await context.api.request(
              context.api.root(context.scope) +
                `/requests/${integer(request)}/matches`,
            );
            const parsed = matching.parse(value);
            setMatches(parsed.table_ids);
            return parsed;
          })
        }
      >
        {t('d1.matches')}
      </Button>
      <p>
        {t('d1.matchesOnly')}:{' '}
        {matches
          .map(
            (id) =>
              context.data.tables?.find((row) => row.id === id)?.code ?? id,
          )
          .join(' · ')}
      </p>
      <Multi
        label="tables"
        name="tables"
        values={tables}
        set={setTables}
        options={tableOptions(context)}
        required
      />
    </FormBox>
  );
}

export function QuoteForm({ context }: { context: FormContext }) {
  const v = useValues({ request: '', currency: '', expires: '', fold: '' });
  return (
    <FormBox
      context={context}
      title="quote"
      operation="quote"
      submit={async () =>
        command(context, {
          operation: 'quote',
          request_id: integer(v.get('request')),
          currency: v.get('currency'),
          expires_at: await context.api.instant(
            context.scope,
            v.get('expires'),
            v.get('fold'),
          ),
        })
      }
    >
      <Pick
        label="reservation"
        name="request"
        value={v.get('request')}
        set={(value) => v.set('request', value)}
        options={requestOptions(context)}
      />
      <Pick
        label="currency"
        name="currency"
        value={v.get('currency')}
        set={(value) => v.set('currency', value)}
        options={Object.keys(context.data.policy?.currencies ?? {}).map(
          (value) => ({ value, label: value }),
        )}
      />
      <Instant
        label="proposalExpires"
        name="expires"
        value={v.get('expires')}
        set={(value) => v.set('expires', value)}
        fold={v.get('fold')}
        setFold={(value) => v.set('fold', value)}
      />
    </FormBox>
  );
}

export function ConsentForm({
  context,
  customer = false,
}: {
  context: FormContext;
  customer?: boolean;
}) {
  const [id, setId] = useState('');
  const [approved, setApproved] = useState(false);
  const { t } = useTranslation();
  const selected = context.data.quotes?.find((row) => String(row.id) === id);
  return (
    <FormBox
      context={context}
      title={customer ? 'customerConsent' : 'restaurantConsent'}
      operation={customer ? 'customer_consent' : 'restaurant_consent'}
      submit={async () => {
        if (!approved || !selected) throw new Error('consent_required');
        return customer
          ? context.api.accept(context.scope, selected.id, selected.digest)
          : command(context, {
              operation: 'restaurant_consent',
              quote_id: selected.id,
              digest: selected.digest,
            });
      }}
    >
      <Pick
        label="proposal"
        name="quote"
        value={id}
        set={(value) => {
          setId(value);
          setApproved(false);
        }}
        options={quoteOptions(context)}
      />
      {selected && (
        <div className={styles.wide}>
          <p>{selected.terms}</p>
          <ul>
            {selected.components.map((row, index) => (
              <li key={index}>
                <bdi>
                  {row.description ?? t(`d1.${row.kind}`)} : {row.quantity} ×{' '}
                  {row.rate} = {row.amount} {selected.currency}
                </bdi>
              </li>
            ))}
          </ul>
        </div>
      )}
      <label className={styles.check}>
        <input
          name="consent"
          type="checkbox"
          checked={approved}
          onChange={(e) => setApproved(e.target.checked)}
          required
        />
        {t(customer ? 'd1.acceptExactProposal' : 'd1.acceptExactMenu')}
      </label>
    </FormBox>
  );
}

export function HoldForm({ context }: { context: FormContext }) {
  const [quote, setQuote] = useState('');
  return (
    <FormBox
      context={context}
      title="hold"
      operation="hold"
      submit={() => {
        const row = context.data.quotes?.find(
          (row) => String(row.id) === quote,
        );
        if (!row) throw new Error('proposal_required');
        return command(context, {
          operation: 'hold',
          request_id: row.request_id,
          quote_id: row.id,
        });
      }}
    >
      <Pick
        label="proposal"
        name="quote"
        value={quote}
        set={setQuote}
        options={quoteOptions(context)}
      />
    </FormBox>
  );
}

export function ProofForm({ context }: { context: FormContext }) {
  const [request, setRequest] = useState(
    context.selectedRequestId ? String(context.selectedRequestId) : '',
  );
  const [tables, setTables] = useState<string[]>([]);
  const v = useValues({ start: '', end: '', startFold: '', endFold: '' });
  const [observed, setObserved] = useState(false);
  const { t, i18n } = useTranslation();
  const selected = context.data.requests?.find(
    (row) => String(row.id) === request,
  );
  const protectedPeriod =
    selected && context.data.policy
      ? {
          start: new Date(
            Date.parse(selected.starts_at) -
              context.data.policy.preparation_seconds * 1000,
          ).toISOString(),
          end: new Date(
            Date.parse(selected.ends_at) +
              context.data.policy.cleaning_seconds * 1000,
          ).toISOString(),
        }
      : null;
  const tableIds = selected
    ? (context.data.request_tables ?? [])
        .filter((row) => row.request_id === selected.id)
        .map((row) => row.table_id)
    : ids(tables);
  const date = (value: string) =>
    new Intl.DateTimeFormat(i18n.language, {
      dateStyle: 'medium',
      timeStyle: 'medium',
      timeZone: context.data.policy?.timezone ?? 'UTC',
    }).format(new Date(value));
  return (
    <FormBox
      context={context}
      title="humanProof"
      operation="human_proof"
      submit={async () => {
        if (!observed) throw new Error('human_observation_required');
        return command(context, {
          operation: 'human_proof',
          request_id: selected?.id ?? null,
          table_ids: tableIds,
          starts_at:
            protectedPeriod?.start ??
            (await context.api.instant(
              context.scope,
              v.get('start'),
              v.get('startFold'),
            )),
          ends_at:
            protectedPeriod?.end ??
            (await context.api.instant(
              context.scope,
              v.get('end'),
              v.get('endFold'),
            )),
        });
      }}
    >
      <Pick
        label="reservationOptional"
        name="request"
        value={request}
        set={(value) => {
          setRequest(value);
          setObserved(false);
        }}
        options={requestOptions(context).filter(
          (row) =>
            !context.selectedTableId ||
            context.data.request_tables?.some(
              (link) =>
                link.table_id === context.selectedTableId &&
                String(link.request_id) === row.value,
            ),
        )}
        required={false}
      />
      {protectedPeriod ? (
        <p className={styles.wide}>
          {t('d1.protectedPeriod')}:{' '}
          <bdi>
            {date(protectedPeriod.start)} → {date(protectedPeriod.end)}
          </bdi>
        </p>
      ) : (
        <>
          <Multi
            label="tables"
            name="tables"
            values={tables}
            set={setTables}
            options={tableOptions(context)}
            required
          />
          <Instant
            label="start"
            name="start"
            value={v.get('start')}
            set={(value) => v.set('start', value)}
            fold={v.get('startFold')}
            setFold={(value) => v.set('startFold', value)}
          />
          <Instant
            label="end"
            name="end"
            value={v.get('end')}
            set={(value) => v.set('end', value)}
            fold={v.get('endFold')}
            setFold={(value) => v.set('endFold', value)}
          />
        </>
      )}
      <label className={styles.check}>
        <input
          name="observed"
          type="checkbox"
          checked={observed}
          onChange={(e) => setObserved(e.target.checked)}
          required
        />
        {t('d1.certifyAvailability')}
      </label>
    </FormBox>
  );
}

export function ConfirmationForm({
  context,
  assistant = false,
}: {
  context: FormContext;
  assistant?: boolean;
}) {
  const [quote, setQuote] = useState('');
  const [receipt, setReceipt] = useState('');
  return (
    <FormBox
      context={context}
      title={assistant ? 'assistantConfirmation' : 'confirmation'}
      operation={assistant ? 'confirm_assistant' : 'confirm_human'}
      submit={() => {
        const row = context.data.quotes?.find(
          (row) => String(row.id) === quote,
        );
        if (!row) throw new Error('proposal_required');
        return command(context, {
          operation: assistant ? 'confirm_assistant' : 'confirm_human',
          request_id: row.request_id,
          quote_id: row.id,
          receipt_id: integer(receipt),
        });
      }}
    >
      <Pick
        label="proposal"
        name="quote"
        value={quote}
        set={setQuote}
        options={quoteOptions(context)}
      />
      <Pick
        label="verifiedReceipt"
        name="receipt"
        value={receipt}
        set={setReceipt}
        options={receiptOptions(context)}
      />
    </FormBox>
  );
}

export function ArrivalForm({ context }: { context: FormContext }) {
  const [request, setRequest] = useState(
    context.selectedRequestId ? String(context.selectedRequestId) : '',
  );
  const [tables, setTables] = useState<string[]>(
    context.selectedTableId ? [String(context.selectedTableId)] : [],
  );
  const v = useValues({ party: '', end: '', fold: '' });
  const selected = context.data.requests?.find(
    (row) => String(row.id) === request,
  );
  return (
    <FormBox
      context={context}
      title="arrival"
      operation="arrival"
      submit={async () =>
        command(context, {
          operation: 'arrival',
          request_id: nullableId(request),
          table_ids: selected
            ? (context.data.request_tables ?? [])
                .filter((row) => row.request_id === selected.id)
                .map((row) => row.table_id)
            : ids(tables),
          party_size: integer(
            v.get('party') || String(selected?.party_size ?? ''),
          ),
          expected_end: await context.api.instant(
            context.scope,
            v.get('end'),
            v.get('fold'),
          ),
        })
      }
    >
      <Pick
        label="reservationOptional"
        name="request"
        value={request}
        set={setRequest}
        options={requestOptions(context).filter(
          (row) =>
            !context.selectedTableId ||
            context.data.request_tables?.some(
              (link) =>
                link.table_id === context.selectedTableId &&
                String(link.request_id) === row.value,
            ),
        )}
        required={false}
      />
      {!selected && (
        <Multi
          label="tables"
          name="tables"
          values={tables}
          set={setTables}
          options={tableOptions(context)}
          required
        />
      )}
      <Field
        label="actualGuests"
        name="party"
        type="number"
        value={v.get('party') || (selected ? String(selected.party_size) : '')}
        set={(value) => v.set('party', value)}
      />
      <Instant
        label="expectedEnd"
        name="end"
        value={v.get('end')}
        set={(value) => v.set('end', value)}
        fold={v.get('fold')}
        setFold={(value) => v.set('fold', value)}
      />
    </FormBox>
  );
}

export function PhysicalForms({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const assignment = context.data.occupation_tables?.find(
    (row) => row.table_id === context.selectedTableId && row.active,
  );
  const [occupation, setOccupation] = useState(
    assignment ? String(assignment.occupation_id) : '',
  );
  const current = context.data.occupations?.find(
    (row) => String(row.id) === occupation,
  );
  const operation =
    current?.status === 'occupied'
      ? 'departure'
      : current?.status === 'dirty'
        ? 'start_cleaning'
        : current?.status === 'cleaning'
          ? 'finish_cleaning'
          : '';
  return (
    <FormBox
      context={context}
      title="departureCleaning"
      operation="physical"
      submitDisabled={!operation}
      submitLabel={
        operation === 'departure'
          ? 'saveObservation'
          : operation === 'start_cleaning'
            ? 'saveStartCleaning'
            : 'saveFinishCleaning'
      }
      submit={() =>
        command(context, {
          operation: operation as
            'departure' | 'start_cleaning' | 'finish_cleaning',
          occupation_id: integer(occupation),
        })
      }
    >
      <Pick
        label="occupation"
        name="occupation"
        value={occupation}
        set={setOccupation}
        options={(context.data.occupations ?? [])
          .filter(
            (row) =>
              ['occupied', 'dirty', 'cleaning'].includes(row.status) &&
              (!context.selectedTableId ||
                row.id === assignment?.occupation_id),
          )
          .map((row) => ({
            value: String(row.id),
            label: `#${row.id} · ${t(`d1.state_${row.status}`)}`,
          }))}
      />
      {operation && <p>{t(`d1.${operation}`)}</p>}
      <p>{t('d1.distinctHumanActions')}</p>
    </FormBox>
  );
}

export function OperationalForm({ context }: { context: FormContext }) {
  const [table, setTable] = useState(
    context.selectedTableId ? String(context.selectedTableId) : '',
  );
  const [state, setState] = useState('');
  const { t } = useTranslation();
  return (
    <FormBox
      context={context}
      title="operationalState"
      operation="physical_state"
      submit={() =>
        command(context, {
          operation: 'physical_state',
          table_id: integer(table),
          state: state as 'available' | 'maintenance' | 'out_of_service',
        })
      }
    >
      <Pick
        label="table"
        name="table"
        value={table}
        set={setTable}
        options={tableOptions(context)}
      />
      <Pick
        label="physicalState"
        name="state"
        value={state}
        set={setState}
        options={['available', 'maintenance', 'out_of_service'].map(
          (value) => ({ value, label: t(`dining.${value}`) }),
        )}
      />
    </FormBox>
  );
}

export function ExtendForm({ context }: { context: FormContext }) {
  const assignment = context.data.occupation_tables?.find(
    (row) => row.table_id === context.selectedTableId && row.active,
  );
  const [occupation, setOccupation] = useState(
    assignment ? String(assignment.occupation_id) : '',
  );
  const v = useValues({ end: '', fold: '' });
  return (
    <FormBox
      context={context}
      title="extend"
      operation="extend"
      submit={async () =>
        command(context, {
          operation: 'extend',
          occupation_id: integer(occupation),
          expected_end: await context.api.instant(
            context.scope,
            v.get('end'),
            v.get('fold'),
          ),
        })
      }
    >
      <Pick
        label="occupation"
        name="occupation"
        value={occupation}
        set={setOccupation}
        options={(context.data.occupations ?? [])
          .filter((row) => row.status === 'occupied')
          .map((row) => ({ value: String(row.id), label: `#${row.id}` }))}
      />
      <Instant
        label="expectedEnd"
        name="end"
        value={v.get('end')}
        set={(value) => v.set('end', value)}
        fold={v.get('fold')}
        setFold={(value) => v.set('fold', value)}
      />
    </FormBox>
  );
}

export function CancelForm({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const v = useValues({ request: '', reason: '', origin: '' });
  return (
    <FormBox
      context={context}
      title="cancellation"
      operation="cancel_before_arrival"
      submit={() =>
        command(context, {
          operation: 'cancel_before_arrival',
          request_id: integer(v.get('request')),
          reason: v.get('reason'),
          origin: v.get('origin') as 'human' | 'customer' | 'assistant',
        })
      }
    >
      <Pick
        label="reservation"
        name="request"
        value={v.get('request')}
        set={(value) => v.set('request', value)}
        options={requestOptions(context)}
      />
      <Pick
        label="origin"
        name="origin"
        value={v.get('origin')}
        set={(value) => v.set('origin', value)}
        options={['human', 'customer', 'assistant'].map((value) => ({
          value,
          label: t(`d1.${value}`),
        }))}
      />
      <Text
        label="reason"
        name="reason"
        value={v.get('reason')}
        set={(value) => v.set('reason', value)}
      />
      <p>{t('d1.noRefund')}</p>
    </FormBox>
  );
}

export function SignalForm({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const [request, setRequest] = useState('');
  const [kind, setKind] = useState('');
  const v = useValues({ reason: '' });
  return (
    <FormBox
      context={context}
      title="signal"
      operation="signal"
      submit={() =>
        command(context, {
          operation: 'signal',
          reason: v.get('reason'),
          request_id: integer(request),
          kind: kind as
            | 'customer_departure'
            | 'customer_cancellation_requested'
            | 'late_arrival'
            | 'expected_end_passed',
        })
      }
    >
      <Pick
        label="reservation"
        name="request"
        value={request}
        set={setRequest}
        options={requestOptions(context)}
      />
      <Pick
        label="signalKind"
        name="kind"
        value={kind}
        set={setKind}
        options={[
          'customer_departure',
          'customer_cancellation_requested',
          'late_arrival',
          'expected_end_passed',
        ].map((value) => ({ value, label: t(`d1.${value}`) }))}
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
