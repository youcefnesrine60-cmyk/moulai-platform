// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import {
  createContext,
  useEffect,
  useContext,
  useId,
  useState,
  type ReactNode,
  type FormEvent,
} from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../shared/ui/primitives';
import { LocalDiningError } from '../../../shared/dining/local/client';
import type {
  LocalDiningClient,
  LocalScope,
  Snapshot,
  OperationResult,
} from '../../../shared/dining/local/client';
import type { DiningOperation } from '../../../shared/dining/local/operations';
import styles from './local.module.css';
import { shortReference } from '../../../shared/dining/referenceValue';
import { HelpLink } from './HelpLink';
import { ElementHelp } from './ElementHelp';
import { OptionHelp } from './OptionHelp';

const BranchTimezone = createContext('UTC');
const CurrentForm = createContext<FormContext | null>(null);

export interface FormContext {
  readonly api: LocalDiningClient;
  readonly scope: LocalScope;
  readonly data: Snapshot;
  readonly busy: boolean;
  readonly selectedTableId?: number;
  readonly selectedRequestId?: number;
  readonly run: (work: () => Promise<OperationResult>) => Promise<void>;
}
export function integer(value: string): number {
  if (!/^\d+$/.test(value) || !Number.isSafeInteger(Number(value)))
    throw new Error('integer_required');
  return Number(value);
}
export function nullableId(value: string): number | null {
  return value === '' ? null : integer(value);
}
export function foldValue(value: string): 0 | 1 | null {
  if (value === '') return null;
  if (value === '0') return 0;
  if (value === '1') return 1;
  throw new Error('fold_invalid');
}
export function ids(values: readonly string[]): number[] {
  return values.map(integer);
}
export function amount(value: string, precision?: number): string {
  const [whole, fraction = ''] = value.split('.');
  const significant = fraction.replace(/0+$/, '');
  const displayed = precision ?? significant.length;
  return (
    whole +
    (displayed
      ? '.' +
        fraction
          .padEnd(displayed, '0')
          .slice(0, Math.max(displayed, significant.length))
      : '')
  );
}
export function FormBox({
  title,
  operation,
  context,
  submit,
  children,
  submitLabel,
  submitDisabled = false,
}: {
  title: string;
  submitLabel?: string;
  submitDisabled?: boolean;
  operation: string;
  context: FormContext;
  submit: () => Promise<OperationResult>;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const submitId = useId();
  const saveLabel =
    submitLabel ??
    {
      arrival: 'saveArrival',
      physical_state: 'saveObservation',
      extend: 'saveExtension',
    }[operation] ??
    'save';
  const [failed, setFailed] = useState(false);
  const [saved, setSaved] = useState(false);
  const [failures, setFailures] = useState(0);
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFailed(false);
    setSaved(false);
    void context.run(async () => {
      try {
        const result = await submit();
        setSaved(true);
        setFailures(0);
        return result;
      } catch (value) {
        setFailed(true);
        setFailures((count) => count + 1);
        throw value;
      }
    });
  };
  return (
    <CurrentForm.Provider value={context}>
      <BranchTimezone.Provider value={context.data.policy?.timezone ?? 'UTC'}>
        <details className={styles.card}>
          <summary>{t(`d1.${title}`)}</summary>
          <form
            aria-label={t(`d1.${title}`)}
            data-operation={operation}
            data-help-title={title}
            onSubmit={onSubmit}
          >
            <fieldset
              disabled={context.busy}
              data-help-busy={context.busy ? 'true' : undefined}
              className={styles.fields}
            >
              {children}
              <div className={styles.submitElement}>
                <Button
                  id={submitId}
                  data-help-label={saveLabel}
                  type="submit"
                  disabled={submitDisabled}
                >
                  {t('d1.' + saveLabel)}
                </Button>
                <ElementHelp targetId={submitId} labelKey={saveLabel} />
              </div>
            </fieldset>
            {saved && (
              <p role="status">
                {t('d1.savedNext')}{' '}
                {t(
                  `d1.${{ request: 'next_request', quote: 'next_quote', restaurant_consent: 'next_agreement', customer_consent: 'next_agreement', human_proof: 'next_human_proof', hold: 'next_hold', receipt: 'next_receipt', confirm_human: 'next_confirmation', confirm_assistant: 'next_confirmation', arrival: 'next_arrival', invoice: 'next_invoice', finalize_invoice: 'next_finalized', physical: 'next_physical', cancel_before_arrival: 'next_cancel' }[operation] ?? 'next_configuration'}`,
                )}
              </p>
            )}
            {failed && (
              <p role="alert" className={styles.fieldError}>
                {t('d1.formError')}
                <HelpLink operation={operation} resolve />
              </p>
            )}
            {failures >= 2 && (
              <p role="status" className={styles.card}>
                {t('help.suggest')} <HelpLink operation={operation} resolve />
              </p>
            )}
          </form>
        </details>
      </BranchTimezone.Provider>
    </CurrentForm.Provider>
  );
}
export function Field({
  label,
  name,
  value,
  set,
  type = 'text',
  required = true,
  step,
  disabled = false,
  disabledExplanation,
}: {
  label: string;
  name: string;
  value: string;
  set: (value: string) => void;
  type?: string;
  required?: boolean;
  step?: number | string;
  disabled?: boolean;
  disabledExplanation?: 'fixedReference';
}) {
  const id = useId();
  const { t } = useTranslation();
  return (
    <div className={styles.fieldControl}>
      <div className={styles.elementLabel}>
        <label htmlFor={id}>{t(`d1.${label}`)}</label>
        <ElementHelp targetId={id} labelKey={label} />
      </div>
      <input
        data-help-label={label}
        id={id}
        name={name}
        value={value}
        onChange={(e) => set(e.target.value)}
        type={type}
        required={required}
        disabled={disabled}
        data-help-disabled={disabledExplanation}
        step={step}
      />
    </div>
  );
}
export function Text({
  label,
  name,
  value,
  set,
  required = true,
}: {
  label: string;
  name: string;
  value: string;
  set: (value: string) => void;
  required?: boolean;
}) {
  const id = useId();
  const { t } = useTranslation();
  return (
    <div className={styles.fieldControl}>
      <div className={styles.elementLabel}>
        <label htmlFor={id}>{t(`d1.${label}`)}</label>
        <ElementHelp targetId={id} labelKey={label} />
      </div>
      <textarea
        data-help-label={label}
        id={id}
        name={name}
        value={value}
        onChange={(e) => set(e.target.value)}
        required={required}
      />
    </div>
  );
}
export function Check({
  label,
  name,
  value,
  set,
}: {
  label: string;
  name: string;
  value: boolean;
  set: (value: boolean) => void;
}) {
  const { t } = useTranslation();
  const id = useId();
  return (
    <div className={styles.checkRow}>
      <label htmlFor={id} className={styles.check}>
        <input
          id={id}
          data-help-label={label}
          name={name}
          type="checkbox"
          checked={value}
          onChange={(e) => set(e.target.checked)}
        />
        {t(`d1.${label}`)}
      </label>
      <ElementHelp targetId={id} labelKey={label} />
    </div>
  );
}
export function Pick({
  label,
  name,
  value,
  set,
  options,
  required = true,
  disabled = false,
  disabledExplanation,
}: {
  label: string;
  name: string;
  value: string;
  set: (value: string) => void;
  options: readonly { value: string; label: string }[];
  required?: boolean;
  disabled?: boolean;
  disabledExplanation?: 'fixedReference';
}) {
  const id = useId();
  const { t } = useTranslation();
  return (
    <div className={styles.pick}>
      <div className={styles.elementLabel}>
        <label htmlFor={name === 'physical_action' ? undefined : id}>
          {t(`d1.${label}`)}
        </label>
        <ElementHelp targetId={id} labelKey={label} />
      </div>
      {name === 'physical_action' ? (
        <span
          id={id}
          data-help-label={label}
          role="radiogroup"
          className={styles.choices}
          aria-label={t(`d1.${label}`)}
        >
          {options.map((row) => (
            <label key={row.value}>
              <input
                data-help-label={label}
                type="radio"
                name={name}
                value={row.value}
                checked={value === row.value}
                onChange={() => set(row.value)}
                disabled={disabled}
                required={required}
              />
              {row.label}
            </label>
          ))}
        </span>
      ) : (
        <select
          aria-describedby={id + '-choices'}
          data-help-label={label}
          id={id}
          name={name}
          value={value}
          onChange={(e) => set(e.target.value)}
          required={required}
          disabled={disabled}
          data-help-disabled={disabledExplanation}
        >
          <option value="">{t('d1.choose')}</option>
          {label === 'testProfile'
            ? ['business', 'scenarios'].map((group) => (
                <optgroup key={group} label={t('options.' + group)}>
                  {options
                    .filter(
                      (row) =>
                        [
                          'assistant',
                          'customer',
                          'outsider',
                          'new_employee',
                        ].includes(row.value) ===
                        (group === 'scenarios'),
                    )
                    .map((row) => (
                      <option key={row.value} value={row.value}>
                        {row.label}
                      </option>
                    ))}
                </optgroup>
              ))
            : options.map((row) => (
                <option key={row.value} value={row.value}>
                  {row.label}
                </option>
              ))}
        </select>
      )}
      <OptionHelp
        name={name}
        label={label}
        value={value}
        options={options}
        id={id + '-choices'}
      />
    </div>
  );
}
/** Checkbox groups retain complete labels and keyboard access on narrow screens. */
export function Multi({
  label,
  name,
  values,
  set,
  options,
  required = false,
  disabled = false,
}: {
  label: string;
  name: string;
  values: readonly string[];
  set: (value: string[]) => void;
  options: readonly {
    value: string;
    label: string;
    capacity?: readonly [number, number];
    state?: string;
  }[];
  required?: boolean;
  disabled?: boolean;
}) {
  const id = useId();
  const groupId = useId();
  const { t } = useTranslation();
  return (
    <fieldset
      id={groupId}
      data-help-label={label}
      className={styles.multi}
      aria-describedby={id}
      disabled={disabled}
    >
      <legend>
        {t(`d1.${label}`)} <ElementHelp targetId={groupId} labelKey={label} />
      </legend>
      {options.map((row, index) => (
        <label key={row.value}>
          <input
            type="checkbox"
            name={name}
            value={row.value}
            checked={values.includes(row.value)}
            required={required && !values.length && index === 0}
            onChange={(event) =>
              set(
                event.target.checked
                  ? [...values, row.value]
                  : values.filter((value) => value !== row.value),
              )
            }
          />
          <span>
            {row.label}
            {row.state && <small>{t(`dining.${row.state}`)}</small>}
          </span>
        </label>
      ))}
      {!options.length && <p>{t('d1.noRows')}</p>}
      <p id={id} role="status">
        {t('d1.selectedCount', { count: values.length })}
        {values.length > 0 &&
          ': ' +
            options
              .filter((row) => values.includes(row.value))
              .map((row) => row.label)
              .join(' · ')}
      </p>
    </fieldset>
  );
}
/** Ask the same authenticated server resolver; hidden selectors never guess DST folds. */
export function WallFold({
  value,
  fold,
  setFold,
  name,
  label = 'fold',
}: {
  value: string;
  fold: string;
  setFold: (value: string) => void;
  name: string;
  label?: string;
}) {
  const context = useContext(CurrentForm);
  const zone = useContext(BranchTimezone);
  const { t } = useTranslation();
  const [state, setState] = useState<
    'idle' | 'ambiguous' | 'invalid' | 'error'
  >('idle');
  useEffect(() => {
    let current = true;
    setState('idle');
    setFold('');
    if (!context || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) return;
    const timer = window.setTimeout(() => {
      void context.api
        .instant(context.scope, value)
        .then(() => {
          if (current) setState('idle');
        })
        .catch((error) => {
          if (!current) return;
          setState(
            error instanceof LocalDiningError &&
              error.code ===
                'dining_calendar_ambiguous_local_time_requires_fold'
              ? 'ambiguous'
              : error instanceof LocalDiningError &&
                  error.code === 'dining_calendar_nonexistent_local_time'
                ? 'invalid'
                : 'error',
          );
        });
    }, 200);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [context?.api, context?.scope, zone, value]);
  return state === 'ambiguous' ? (
    <Pick
      label={label}
      name={name}
      value={fold}
      set={setFold}
      required
      options={[
        { value: '0', label: t('d1.firstOccurrence') },
        { value: '1', label: t('d1.secondOccurrence') },
      ]}
    />
  ) : state === 'invalid' || state === 'error' ? (
    <p role="alert">
      {t(
        state === 'invalid' ? 'd1.nonexistentTime' : 'd1.timeCheckUnavailable',
      )}
    </p>
  ) : null;
}
export function Instant({
  label,
  name,
  value,
  set,
  fold,
  setFold,
  required = true,
}: {
  label: string;
  name: string;
  value: string;
  set: (value: string) => void;
  fold: string;
  setFold: (value: string) => void;
  required?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const timezone = useContext(BranchTimezone);
  return (
    <div className={styles.time}>
      <small>
        {t('d1.wallTime')}: <bdi>{timezone}</bdi>
      </small>
      <Field
        label={label}
        name={name}
        value={value}
        set={set}
        type="datetime-local"
        step={1}
        required={required}
      />
      {value && Number.isFinite(Date.parse(value + 'Z')) && (
        <small>
          <bdi>
            {new Intl.DateTimeFormat(i18n.language, {
              dateStyle: 'long',
              timeStyle: 'short',
              timeZone: 'UTC',
              hourCycle: 'h23',
            }).format(new Date(value + 'Z'))}
          </bdi>
        </small>
      )}
      <WallFold
        value={value}
        fold={fold}
        setFold={setFold}
        name={`${name}_fold`}
      />
    </div>
  );
}
export function command(
  context: FormContext,
  data: DiningOperation,
): Promise<OperationResult> {
  return context.api.command(context.scope, data);
}
export const tableOptions = (context: FormContext) =>
  (context.data.tables ?? []).map((row) => ({
    value: String(row.id),
    label: `${row.code} · ${row.min_capacity}–${row.max_capacity}`,
    capacity: [row.min_capacity, row.max_capacity] as const,
    state: row.physical_state,
  }));
export const requestOptions = (context: FormContext) =>
  (context.data.requests ?? []).map((row) => ({
    value: String(row.id),
    label: shortReference(row.id),
  }));
export const quoteOptions = (context: FormContext) =>
  (context.data.quotes ?? []).map((row) => ({
    value: String(row.id),
    label: `#${row.id} / v${row.version} · ${amount(row.amount)} ${row.currency}`,
  }));
export const receiptOptions = (context: FormContext) =>
  (context.data.receipts ?? []).map((row) => ({
    value: String(row.id),
    label: `#${row.id} · ${amount(row.received_amount)} ${row.currency} · ${row.status}`,
  }));

export function useValues<T extends Record<string, string>>(initial: T) {
  const [values, setValues] = useState(initial);
  return {
    get: (key: keyof T): string => values[key] ?? '',
    set: (key: keyof T, value: string): void =>
      setValues((current) => ({ ...current, [key]: value })),
    replace: (value: T): void => setValues(value),
  };
}
