// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { localized } from '../../../shared/i18n';
import { Button } from '../../../shared/ui/primitives';
import type {
  GrantOperation,
  ReferenceInput,
} from '../../../shared/dining/local/operations';
import {
  Field,
  Text,
  Check,
  Pick,
  Multi,
  Instant,
  WallFold,
  FormBox,
  command,
  integer,
  nullableId,
  ids,
  foldValue,
  tableOptions,
  useValues,
  type FormContext,
} from './fields';
import styles from './local.module.css';

const kinds = [
  'shape',
  'category',
  'zone',
  'location',
  'view',
  'proximity',
  'feature',
  'event',
] as const;
function labels(context: FormContext, kind: string) {
  return (context.data.references ?? [])
    .filter((row) => row.kind === kind && row.active)
    .map((row) => ({ value: String(row.id), label: localized(row.labels) }));
}

export function ReferenceForm({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const [edit, setEdit] = useState('');
  const v = useValues({
    kind: 'category',
    code: '',
    fr: '',
    en: '',
    ar: '',
    pricing: '',
  });
  const [active, setActive] = useState(true);
  const [ack, setAck] = useState(false);
  const load = (value: string) => {
    setEdit(value);
    const row = context.data.references?.find(
      (row) => String(row.id) === value,
    );
    if (row) {
      v.replace({
        kind: row.kind,
        code: row.code,
        fr: row.labels.fr,
        en: row.labels.en,
        ar: row.labels.ar,
        pricing: row.pricing_ref ?? '',
      });
      setActive(row.active);
    }
  };
  return (
    <FormBox
      context={context}
      title="references"
      operation="reference"
      submit={() =>
        command(context, {
          operation: 'reference',
          identifier: nullableId(edit),
          acknowledge_conflicts: ack,
          data: {
            kind: v.get('kind') as ReferenceInput['kind'],
            code: v.get('code'),
            labels: { fr: v.get('fr'), en: v.get('en'), ar: v.get('ar') },
            active,
            pricing_ref: v.get('pricing') || null,
          },
        })
      }
    >
      <Pick
        label="editOrCreate"
        name="reference_edit"
        value={edit}
        set={load}
        required={false}
        options={(context.data.references ?? []).map((row) => ({
          value: String(row.id),
          label: `${t(`d1.${row.kind}`)} · ${localized(row.labels)}`,
        }))}
      />
      <Pick
        label="referenceKind"
        name="kind"
        value={v.get('kind')}
        disabled={Boolean(edit)}
        disabledExplanation="fixedReference"
        set={(value) => v.set('kind', value)}
        options={kinds.map((value) => ({ value, label: t(`d1.${value}`) }))}
      />
      {v.get('kind') === 'shape' ? (
        <Pick
          label="code"
          name="code"
          value={v.get('code')}
          set={(value) => v.set('code', value)}
          disabled={Boolean(edit)}
          disabledExplanation="fixedReference"
          options={['round', 'rectangular', 'square', 'oval'].map((value) => ({
            value,
            label: t(`d1.shape_${value}`),
          }))}
        />
      ) : (
        <Field
          label="code"
          name="code"
          value={v.get('code')}
          set={(value) => v.set('code', value)}
          disabled={Boolean(edit)}
          disabledExplanation="fixedReference"
        />
      )}
      {(['fr', 'en', 'ar'] as const).map((key) => (
        <Field
          key={key}
          label={key}
          name={key}
          value={v.get(key)}
          set={(value) => v.set(key, value)}
        />
      ))}
      <Field
        label="pricingRef"
        name="pricing"
        value={v.get('pricing')}
        set={(value) => v.set('pricing', value)}
        required={false}
      />
      <Check label="active" name="active" value={active} set={setActive} />
      <Check label="ackConflicts" name="ack" value={ack} set={setAck} />
    </FormBox>
  );
}

export function TableForm({ context }: { context: FormContext }) {
  const [edit, setEdit] = useState('');
  const v = useValues({
    code: '',
    name: '',
    minimum: '',
    maximum: '',
    shape: '',
    category: '',
    zone: '',
    location: '',
    description: '',
    floor: '',
    room: '',
    photos: '',
    pricing: '',
    initial: '',
  });
  const [traits, setTraits] = useState<string[]>([]);
  const [active, setActive] = useState(true);
  const [ack, setAck] = useState(false);
  const load = (value: string) => {
    setEdit(value);
    const row = context.data.tables?.find((row) => String(row.id) === value);
    if (row) {
      v.replace({
        code: row.code,
        name: row.name ?? '',
        minimum: String(row.min_capacity),
        maximum: String(row.max_capacity),
        shape: String(row.shape_id),
        category: String(row.category_id),
        zone: String(row.zone_id),
        location: String(row.location_id),
        description: row.description,
        floor: row.floor_label ?? '',
        room: row.room_label ?? '',
        photos: row.photos.join('\n'),
        pricing: row.pricing_ref,
        initial: '',
      });
      setTraits(
        (context.data.traits ?? [])
          .filter((trait) => trait.table_id === row.id)
          .map((trait) => String(trait.reference_id)),
      );
      setActive(row.in_service);
    }
  };
  const { t } = useTranslation();
  return (
    <FormBox
      context={context}
      title="tables"
      operation="table"
      submit={() =>
        command(context, {
          operation: 'table',
          identifier: nullableId(edit),
          initial_state: edit
            ? null
            : (v.get('initial') as
                'available' | 'maintenance' | 'out_of_service'),
          acknowledge_conflicts: ack,
          data: {
            code: v.get('code'),
            name: v.get('name') || null,
            min_capacity: integer(v.get('minimum')),
            max_capacity: integer(v.get('maximum')),
            shape_id: integer(v.get('shape')),
            category_id: integer(v.get('category')),
            zone_id: integer(v.get('zone')),
            location_id: integer(v.get('location')),
            description: v.get('description'),
            floor_label: v.get('floor') || null,
            room_label: v.get('room') || null,
            photos: v
              .get('photos')
              .split('\n')
              .map((value) => value.trim())
              .filter(Boolean),
            pricing_ref: v.get('pricing'),
            in_service: active,
            trait_ids: ids(traits),
          },
        })
      }
    >
      <Pick
        label="editOrCreate"
        name="table_edit"
        value={edit}
        set={load}
        required={false}
        options={tableOptions(context)}
      />
      {(['code', 'name', 'minimum', 'maximum'] as const).map((key) => (
        <Field
          key={key}
          label={key}
          name={key}
          type={key === 'minimum' || key === 'maximum' ? 'number' : 'text'}
          value={v.get(key)}
          set={(value) => v.set(key, value)}
          required={key !== 'name'}
        />
      ))}
      {(['shape', 'category', 'zone', 'location'] as const).map((key) => (
        <Pick
          key={key}
          label={key}
          name={key}
          value={v.get(key)}
          set={(value) => v.set(key, value)}
          options={labels(context, key)}
        />
      ))}
      <Multi
        label="traits"
        name="traits"
        values={traits}
        set={setTraits}
        options={(context.data.references ?? [])
          .filter(
            (row) =>
              ['view', 'proximity', 'feature'].includes(row.kind) && row.active,
          )
          .map((row) => ({
            value: String(row.id),
            label: `${t(`d1.${row.kind}`)} · ${localized(row.labels)}`,
          }))}
      />
      <Text
        label="description"
        name="description"
        value={v.get('description')}
        set={(value) => v.set('description', value)}
        required={false}
      />
      <Field
        label="floorLabel"
        name="floor"
        value={v.get('floor')}
        set={(value) => v.set('floor', value)}
        required={false}
      />
      <Field
        label="roomLabel"
        name="room"
        value={v.get('room')}
        set={(value) => v.set('room', value)}
        required={false}
      />
      <Text
        label="photos"
        name="photos"
        value={v.get('photos')}
        set={(value) => v.set('photos', value)}
        required={false}
      />
      <Field
        label="pricingRef"
        name="pricing"
        value={v.get('pricing')}
        set={(value) => v.set('pricing', value)}
      />
      <Check label="inService" name="active" value={active} set={setActive} />
      {!edit && (
        <Pick
          label="initialPhysical"
          name="initial"
          value={v.get('initial')}
          set={(value) => v.set('initial', value)}
          options={['available', 'maintenance', 'out_of_service'].map(
            (value) => ({ value, label: t(`dining.${value}`) }),
          )}
        />
      )}
      <Check label="ackConflicts" name="ack" value={ack} set={setAck} />
    </FormBox>
  );
}

export function PolicyForm({ context }: { context: FormContext }) {
  const p = context.data.policy;
  const { t } = useTranslation();
  const keys = [
    'response_seconds',
    'hold_seconds',
    'lateness_seconds',
    'preparation_seconds',
    'cleaning_seconds',
    'confirmation_seconds',
  ] as const;
  const v = useValues({
    timezone: p?.timezone ?? '',
    response_seconds: p ? String(p.response_seconds) : '',
    hold_seconds: p ? String(p.hold_seconds) : '',
    lateness_seconds: p ? String(p.lateness_seconds) : '',
    preparation_seconds: p ? String(p.preparation_seconds) : '',
    cleaning_seconds: p ? String(p.cleaning_seconds) : '',
    confirmation_seconds: p ? String(p.confirmation_seconds) : '',
    offsets: p?.alert_offsets_seconds.join(',') ?? '',
    terms: p?.terms ?? '',
  });
  const [services, setServices] = useState(
    p?.service_recipients.map(String) ?? [],
  );
  const [escalations, setEscalations] = useState(
    p?.escalation_recipients.map(String) ?? [],
  );
  const [currencies, setCurrencies] = useState(
    Object.entries(p?.currencies ?? {}).map(([code, precision]) => ({
      code,
      precision: String(precision),
    })),
  );
  const [modes, setModes] = useState(
    Object.entries(p?.payment_instructions ?? {}).map(
      ([mode, instruction]) => ({ mode, instruction }),
    ),
  );
  const people = (context.data.memberships ?? [])
    .filter((row) => row.status === 'active')
    .map((row) => ({
      value: String(row.id),
      label: `#${row.id} · ${t(`d1.role_${row.role}`)}`,
    }));
  return (
    <FormBox
      context={context}
      title="parameters"
      operation="policy"
      submit={() => {
        if (
          new Set(currencies.map((row) => row.code)).size !==
            currencies.length ||
          new Set(modes.map((row) => row.mode)).size !== modes.length
        )
          throw new Error('duplicate_configuration');
        return command(context, {
          operation: 'policy',
          data: {
            timezone: v.get('timezone'),
            response_seconds: integer(v.get('response_seconds')),
            hold_seconds: integer(v.get('hold_seconds')),
            lateness_seconds: integer(v.get('lateness_seconds')),
            preparation_seconds: integer(v.get('preparation_seconds')),
            cleaning_seconds: integer(v.get('cleaning_seconds')),
            confirmation_seconds: integer(v.get('confirmation_seconds')),
            confirmation_scope: 'tables',
            alert_offsets_seconds: v
              .get('offsets')
              .split(',')
              .map((value) => integer(value.trim())),
            service_recipients: ids(services),
            escalation_recipients: ids(escalations),
            currencies: Object.fromEntries(
              currencies.map((row) => [row.code, integer(row.precision)]),
            ),
            payment_instructions: Object.fromEntries(
              modes.map((row) => [row.mode, row.instruction]),
            ),
            terms: v.get('terms'),
          },
        });
      }}
    >
      <Field
        label="timezone"
        name="timezone"
        value={v.get('timezone')}
        set={(value) => v.set('timezone', value)}
      />
      {keys.map((key) => (
        <Field
          key={key}
          label={key}
          name={key}
          type="number"
          value={v.get(key)}
          set={(value) => v.set(key, value)}
        />
      ))}
      <Field
        label="alertOffsets"
        name="offsets"
        value={v.get('offsets')}
        set={(value) => v.set('offsets', value)}
      />
      <Multi
        label="serviceRecipients"
        name="services"
        values={services}
        set={setServices}
        options={people}
        required
      />
      <Multi
        label="escalationRecipients"
        name="escalations"
        values={escalations}
        set={setEscalations}
        options={people}
      />
      <div className={styles.wide}>
        <h3>{t('d1.currencyPrecision')}</h3>
        {currencies.map((row, index) => (
          <div className={styles.row} key={index}>
            <Field
              label="currency"
              name={`currency_${index}`}
              value={row.code}
              set={(value) =>
                setCurrencies((rows) =>
                  rows.map((item, n) =>
                    n === index ? { ...item, code: value } : item,
                  ),
                )
              }
            />
            <Field
              label="precision"
              name={`precision_${index}`}
              type="number"
              value={row.precision}
              set={(value) =>
                setCurrencies((rows) =>
                  rows.map((item, n) =>
                    n === index ? { ...item, precision: value } : item,
                  ),
                )
              }
            />
            <Button
              type="button"
              variant="quiet"
              onClick={() =>
                setCurrencies((rows) => rows.filter((_, n) => n !== index))
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
            setCurrencies((rows) => [...rows, { code: '', precision: '' }])
          }
        >
          {t('d1.addCurrency')}
        </Button>
      </div>
      <div className={styles.wide}>
        <h3>{t('d1.paymentInstructions')}</h3>
        {modes.map((row, index) => (
          <div className={styles.row} key={index}>
            <Field
              label="mode"
              name={`mode_${index}`}
              value={row.mode}
              set={(value) =>
                setModes((rows) =>
                  rows.map((item, n) =>
                    n === index ? { ...item, mode: value } : item,
                  ),
                )
              }
            />
            <Text
              label="instructions"
              name={`instructions_${index}`}
              value={row.instruction}
              set={(value) =>
                setModes((rows) =>
                  rows.map((item, n) =>
                    n === index ? { ...item, instruction: value } : item,
                  ),
                )
              }
            />
            <Button
              type="button"
              variant="quiet"
              onClick={() =>
                setModes((rows) => rows.filter((_, n) => n !== index))
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
            setModes((rows) => [...rows, { mode: '', instruction: '' }])
          }
        >
          {t('d1.addMode')}
        </Button>
      </div>
      <Text
        label="terms"
        name="terms"
        value={v.get('terms')}
        set={(value) => v.set('terms', value)}
      />
      <p>{t('d1.noCommercialDefaults')}</p>
    </FormBox>
  );
}

export function CalendarForm({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const [kind, setKind] = useState('weekly');
  const [weekday, setWeekday] = useState('');
  const [day, setDay] = useState('');
  const [closed, setClosed] = useState(false);
  const [ack, setAck] = useState(false);
  const [windows, setWindows] = useState<
    {
      start: string;
      end: string;
      next_day: boolean;
      start_fold: 0 | 1 | null;
      end_fold: 0 | 1 | null;
    }[]
  >([
    { start: '', end: '', next_day: false, start_fold: null, end_fold: null },
  ]);
  return (
    <FormBox
      context={context}
      title="calendar"
      operation="calendar"
      submit={() =>
        command(context, {
          operation: 'calendar',
          weekday: kind === 'weekly' ? integer(weekday) : null,
          service_date: kind === 'dated' ? day : null,
          windows: closed ? [] : windows,
          acknowledge_conflicts: ack,
        })
      }
    >
      <Pick
        label="calendarKind"
        name="calendar_kind"
        value={kind}
        set={setKind}
        options={[
          { value: 'weekly', label: t('d1.weekly') },
          { value: 'dated', label: t('d1.dated') },
        ]}
      />
      {kind === 'weekly' ? (
        <Pick
          label="weekday"
          name="weekday"
          value={weekday}
          set={setWeekday}
          options={Array.from({ length: 7 }, (_, value) => ({
            value: String(value),
            label: t(`d1.day${value}`),
          }))}
        />
      ) : (
        <Field label="date" name="date" type="date" value={day} set={setDay} />
      )}
      <Check label="closed" name="closed" value={closed} set={setClosed} />
      {!closed && (
        <div className={styles.wide}>
          {windows.map((row, index) => (
            <div className={styles.row} key={index}>
              <Field
                label="start"
                name={`start_${index}`}
                type="time"
                step={1}
                value={row.start}
                set={(value) =>
                  setWindows((rows) =>
                    rows.map((item, n) =>
                      n === index ? { ...item, start: value } : item,
                    ),
                  )
                }
              />
              <Field
                label="end"
                name={`end_${index}`}
                type="time"
                step={1}
                value={row.end}
                set={(value) =>
                  setWindows((rows) =>
                    rows.map((item, n) =>
                      n === index ? { ...item, end: value } : item,
                    ),
                  )
                }
              />
              {kind === 'dated' &&
                day &&
                (['start_fold', 'end_fold'] as const).map((key) => (
                  <WallFold
                    key={key}
                    label={key === 'start_fold' ? 'startFold' : 'endFold'}
                    name={`${key}_${index}`}
                    value={`${key === 'end_fold' && row.next_day ? new Date(Date.parse(day + 'T12:00:00Z') + 86400000).toISOString().slice(0, 10) : day}T${key === 'start_fold' ? row.start : row.end}`}
                    fold={row[key] === null ? '' : String(row[key])}
                    setFold={(value) =>
                      setWindows((rows) =>
                        rows.map((item, n) =>
                          n === index
                            ? { ...item, [key]: foldValue(value) }
                            : item,
                        ),
                      )
                    }
                  />
                ))}
              <Check
                label="nextDay"
                name={`next_${index}`}
                value={row.next_day}
                set={(value) =>
                  setWindows((rows) =>
                    rows.map((item, n) =>
                      n === index ? { ...item, next_day: value } : item,
                    ),
                  )
                }
              />
              <Button
                type="button"
                variant="quiet"
                onClick={() =>
                  setWindows((rows) => rows.filter((_, n) => n !== index))
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
              setWindows((rows) => [
                ...rows,
                {
                  start: '',
                  end: '',
                  next_day: false,
                  start_fold: null,
                  end_fold: null,
                },
              ])
            }
          >
            {t('d1.addService')}
          </Button>
        </div>
      )}
      <Check label="ackConflicts" name="ack" value={ack} set={setAck} />
    </FormBox>
  );
}

export function TariffForm({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const v = useValues({
    reference: '',
    component: 'table',
    currency: '',
    unit: 'per_hour',
    price: '',
    start: '',
    end: '',
    startFold: '',
    endFold: '',
  });
  const currencies = Object.keys(context.data.policy?.currencies ?? {}).map(
    (value) => ({ value, label: value }),
  );
  return (
    <FormBox
      context={context}
      title="tariffs"
      operation="tariff"
      submit={async () =>
        command(context, {
          operation: 'tariff',
          data: {
            reference: v.get('reference'),
            component: v.get('component') as 'table' | 'preparation' | 'menu',
            currency: v.get('currency'),
            unit: v.get('unit') as
              'per_hour' | 'flat' | 'per_person' | 'per_item',
            unit_price: v.get('price'),
            valid_from: await context.api.instant(
              context.scope,
              v.get('start'),
              v.get('startFold'),
            ),
            valid_until: v.get('end')
              ? await context.api.instant(
                  context.scope,
                  v.get('end'),
                  v.get('endFold'),
                )
              : null,
          },
        })
      }
    >
      <Field
        label="pricingRef"
        name="reference"
        value={v.get('reference')}
        set={(value) => v.set('reference', value)}
      />
      <Pick
        label="component"
        name="component"
        value={v.get('component')}
        set={(value) => v.set('component', value)}
        options={['table', 'preparation', 'menu'].map((value) => ({
          value,
          label: t(`d1.${value}`),
        }))}
      />
      <Pick
        label="currency"
        name="currency"
        value={v.get('currency')}
        set={(value) => v.set('currency', value)}
        options={currencies}
      />
      <Pick
        label="unit"
        name="unit"
        value={v.get('unit')}
        set={(value) => v.set('unit', value)}
        options={['per_hour', 'flat', 'per_person', 'per_item'].map(
          (value) => ({ value, label: t(`d1.${value}`) }),
        )}
      />
      <Field
        label="exactUnitPrice"
        name="price"
        value={v.get('price')}
        set={(value) => v.set('price', value)}
      />
      <Instant
        label="validFrom"
        name="start"
        value={v.get('start')}
        set={(value) => v.set('start', value)}
        fold={v.get('startFold')}
        setFold={(value) => v.set('startFold', value)}
      />
      <Instant
        label="validUntilOptional"
        name="end"
        value={v.get('end')}
        set={(value) => v.set('end', value)}
        fold={v.get('endFold')}
        setFold={(value) => v.set('endFold', value)}
        required={false}
      />
    </FormBox>
  );
}

export function GrantForm({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const v = useValues({ member: '', capability: '', actor: 'human' });
  const [active, setActive] = useState(false);
  return (
    <FormBox
      context={context}
      title="permissions"
      operation="grant"
      submit={() =>
        command(context, {
          operation: 'grant',
          membership_id: integer(v.get('member')),
          capability: v.get('capability') as GrantOperation['capability'],
          actor_kind: v.get('actor') as 'human' | 'assistant',
          active,
        })
      }
    >
      <Pick
        label="person"
        name="member"
        value={v.get('member')}
        set={(value) => v.set('member', value)}
        options={(context.data.memberships ?? []).map((row) => ({
          value: String(row.id),
          label: `#${row.id} · ${t(`d1.role_${row.role}`)}`,
        }))}
      />
      <Pick
        label="capability"
        name="capability"
        value={v.get('capability')}
        set={(value) => v.set('capability', value)}
        options={[
          'read',
          'service',
          'clean',
          'collect',
          'assistant',
          'reservations.cancel_before_arrival',
          'finance.read',
          'invoices.create',
          'invoices.finalize',
          'advances.allocate',
          'orders.read',
          'orders.approve',
          'orders.prepare',
          'orders.complete',
          'documents.issue',
        ].map((value) => ({ value, label: t(`d1.cap_${value}`) }))}
      />
      <Pick
        label="actorKind"
        name="actor"
        value={v.get('actor')}
        set={(value) => v.set('actor', value)}
        options={['human', 'assistant'].map((value) => ({
          value,
          label: t(`d1.${value}`),
        }))}
      />
      <Check label="grantActive" name="active" value={active} set={setActive} />
    </FormBox>
  );
}

export function CombinationForm({ context }: { context: FormContext }) {
  const [edit, setEdit] = useState('');
  const [ack, setAck] = useState(false);
  const v = useValues({ code: '', minimum: '', maximum: '', pricing: '' });
  const [tables, setTables] = useState<string[]>([]);
  const [active, setActive] = useState(true);
  return (
    <FormBox
      context={context}
      title="combinations"
      operation="combination"
      submit={() =>
        command(context, {
          operation: 'combination',
          identifier: nullableId(edit),
          acknowledge_conflicts: ack,
          data: {
            code: v.get('code'),
            table_ids: ids(tables),
            min_capacity: integer(v.get('minimum')),
            max_capacity: integer(v.get('maximum')),
            pricing_ref: v.get('pricing'),
            active,
          },
        })
      }
    >
      <Pick
        label="editOrCreate"
        name="combination_edit"
        value={edit}
        set={(value) => {
          setEdit(value);
          const row = context.data.combinations?.find(
            (row) => String(row.id) === value,
          );
          if (row) {
            v.replace({
              code: row.code,
              minimum: String(row.min_capacity),
              maximum: String(row.max_capacity),
              pricing: row.pricing_ref,
            });
            setActive(row.active);
            setTables(
              (context.data.members ?? [])
                .filter((member) => member.combination_id === row.id)
                .map((member) => String(member.table_id)),
            );
          }
        }}
        required={false}
        options={(context.data.combinations ?? []).map((row) => ({
          value: String(row.id),
          label: row.code,
        }))}
      />
      <Field
        label="code"
        name="code"
        disabled={Boolean(edit)}
        value={v.get('code')}
        set={(value) => v.set('code', value)}
      />
      <Multi
        label="tables"
        name="tables"
        values={tables}
        set={setTables}
        options={tableOptions(context)}
        required
      />
      {(['minimum', 'maximum', 'pricing'] as const).map((key) => (
        <Field
          key={key}
          label={key === 'pricing' ? 'pricingRef' : key}
          name={key}
          type={key === 'pricing' ? 'text' : 'number'}
          value={v.get(key)}
          set={(value) => v.set(key, value)}
        />
      ))}
      <Check label="active" name="active" value={active} set={setActive} />
      <Check label="ackConflicts" name="ack" value={ack} set={setAck} />
    </FormBox>
  );
}

export function BlackoutForm({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const v = useValues({
    start: '',
    end: '',
    startFold: '',
    endFold: '',
    kind: 'maintenance',
    reason: '',
    target: '',
    table: '',
    zone: '',
  });
  const [ack, setAck] = useState(false);
  return (
    <FormBox
      context={context}
      title="blackouts"
      operation="blackout"
      submit={async () => {
        if (!['branch', 'table', 'zone'].includes(v.get('target')))
          throw new Error('target_required');
        return command(context, {
          operation: 'blackout',
          starts_at: await context.api.instant(
            context.scope,
            v.get('start'),
            v.get('startFold'),
          ),
          ends_at: await context.api.instant(
            context.scope,
            v.get('end'),
            v.get('endFold'),
          ),
          kind: v.get('kind') as
            'closure' | 'maintenance' | 'preparation' | 'cleaning',
          reason: v.get('reason'),
          table_id:
            v.get('target') === 'table' ? integer(v.get('table')) : null,
          zone_id: v.get('target') === 'zone' ? integer(v.get('zone')) : null,
          acknowledge_conflicts: ack,
        });
      }}
    >
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
      <Pick
        label="blockKind"
        name="kind"
        value={v.get('kind')}
        set={(value) => v.set('kind', value)}
        options={['closure', 'maintenance', 'preparation', 'cleaning'].map(
          (value) => ({ value, label: t(`d1.${value}`) }),
        )}
      />
      <Pick
        label="blockTarget"
        name="target"
        value={v.get('target')}
        set={(value) => v.set('target', value)}
        options={['branch', 'zone', 'table'].map((value) => ({
          value,
          label: t(`d1.${value}`),
        }))}
      />
      {v.get('target') === 'table' && (
        <Pick
          label="tableOptional"
          name="table"
          value={v.get('table')}
          set={(value) => {
            v.set('table', value);
            v.set('zone', '');
          }}
          options={tableOptions(context)}
        />
      )}
      {v.get('target') === 'zone' && (
        <Pick
          label="zoneOptional"
          name="zone"
          value={v.get('zone')}
          set={(value) => {
            v.set('zone', value);
            v.set('table', '');
          }}
          options={labels(context, 'zone')}
        />
      )}
      <Text
        label="reason"
        name="reason"
        value={v.get('reason')}
        set={(value) => v.set('reason', value)}
      />
      <Check label="ackConflicts" name="ack" value={ack} set={setAck} />
    </FormBox>
  );
}
