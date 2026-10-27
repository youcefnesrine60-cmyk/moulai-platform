import { useState, type ReactElement } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  simulateVerification,
  type VerificationDraft,
} from '../../shared/office/simulation';
import type { PaymentView } from '../../shared/office/contracts';
import { Button } from '../../shared/ui/primitives';
import common from '../management/management.module.css';
import styles from '../office/office.module.css';

const emptyDraft: VerificationDraft = {
  decision: 'approve',
  fundsReceived: false,
  reference: '',
  amount: '',
  currency: '',
  note: '',
};

/** Pure, explicitly hypothetical UI evaluation; no submit API/adapter exists. */
export function VerificationSimulation({
  payment,
}: {
  payment: PaymentView;
}): ReactElement {
  const { t } = useTranslation();
  const { register, getValues, reset, watch, setValue } =
    useForm<VerificationDraft>({ defaultValues: emptyDraft });
  const [result, setResult] = useState<'approve' | 'reject' | 'error' | null>(
    null,
  );
  const reject = watch('decision') === 'reject';
  return (
    <form
      aria-label={t('office.verification')}
      className={styles.form}
      noValidate
      onChange={() => setResult(null)}
      onSubmit={(event) => {
        event.preventDefault();
        setResult(simulateVerification(payment, getValues()) ?? 'error');
      }}
    >
      <h3>{t('office.verification')}</h3>
      <p className={styles.note}>{t('office.simulation')}</p>
      <label className={common.field}>
        {t('office.decision')}
        <select
          {...register('decision', {
            onChange: () => {
              setValue('fundsReceived', false);
              setValue('reference', '');
              setValue('amount', '');
              setValue('currency', '');
            },
          })}
        >
          <option value="approve">{t('office.approve')}</option>
          <option value="reject">{t('office.reject')}</option>
        </select>
      </label>
      {!reject && (
        <>
          <label className={common.check}>
            <input type="checkbox" {...register('fundsReceived')} />
            {t('office.fundsHypothesis')}
          </label>
          <label className={common.field}>
            {t('office.bankReference')}
            <input dir="auto" maxLength={120} {...register('reference')} />
          </label>
          <label className={common.field}>
            {t('office.receivedAmount')}
            <input inputMode="decimal" dir="ltr" {...register('amount')} />
          </label>
          <label className={common.field}>
            {t('office.currency')}
            <select {...register('currency')}>
              <option value="">{t('office.noCurrency')}</option>
              <option value="DZD">DZD</option>
            </select>
          </label>
        </>
      )}
      <label className={common.field}>
        {t('office.note')}
        <textarea dir="auto" maxLength={2000} {...register('note')} />
      </label>
      {result === 'error' && (
        <p role="alert" className={common.fieldError}>
          {t('office.simulationError')}
        </p>
      )}
      <div className={common.actions}>
        <Button type="submit">{t('office.simulateReview')}</Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => {
            reset(emptyDraft);
            setResult(null);
          }}
        >
          {t('office.resetSimulation')}
        </Button>
      </div>
      {result && result !== 'error' && (
        <section aria-label={t('office.simulation')}>
          <p role="status">
            {t(
              result === 'approve'
                ? 'office.simulationApproved'
                : 'office.simulationRejected',
            )}
          </p>
          <p className={styles.note}>{t('office.previewNotSaved')}</p>
        </section>
      )}
    </form>
  );
}
