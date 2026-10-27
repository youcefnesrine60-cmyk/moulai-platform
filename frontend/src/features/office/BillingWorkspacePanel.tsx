import { useState, type ReactElement } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAdapter } from '../../app/access';
import { localized } from '../../shared/i18n';
import { checkoutPreview } from '../../shared/office/simulation';
import type { BillingWorkspace } from '../../shared/office/contracts';
import {
  Badge,
  Button,
  ErrorPanel,
  LoadingPanel,
} from '../../shared/ui/primitives';
import {
  useBusinessFormatting,
  useRestaurantContext,
} from '../management/scope';
import common from '../management/management.module.css';
import styles from './office.module.css';

/** All state is component-local; offers/instructions are supplied only by the review adapter. */
function SubscriptionPreview({
  data,
  checkoutAllowed,
}: {
  data: BillingWorkspace;
  checkoutAllowed: boolean;
}): ReactElement {
  const { t } = useTranslation();
  const { money, date } = useBusinessFormatting();
  const { register, getValues, watch } = useForm({
    defaultValues: {
      planId: String(data.offers[0]?.id ?? ''),
      cycle: 'monthly',
      method: 'ccp',
    },
  });
  const [quote, setQuote] = useState<number | null>(null);
  const [invalid, setInvalid] = useState(false);
  const method = watch('method');
  const instruction = data.instructions.find(
    (i) => i.method === method && i.enabled,
  );
  const subscription = data.subscription;
  return (
    <section className={common.panel}>
      <div className={common.titleRow}>
        <h2>{t('office.subscription')}</h2>
        <Badge tone="test">{t('office.simulation')}</Badge>
      </div>
      {subscription ? (
        <dl className={styles.definition}>
          <dt>{t('office.plan')}</dt>
          <dd>{localized(subscription.planName)}</dd>
          <dt>{t('office.status')}</dt>
          <dd>{t(`office.${subscription.status}`)}</dd>
          <dt>{t('office.cycle')}</dt>
          <dd>{t(`office.${subscription.billingCycle}`)}</dd>
          <dt>{t('office.amount')}</dt>
          <dd>{money(subscription.amount)}</dd>
          <dt>{t('office.starts')}</dt>
          <dd>{date(subscription.startsAt)}</dd>
          <dt>{t('office.expires')}</dt>
          <dd>{date(subscription.expiresAt)}</dd>
        </dl>
      ) : (
        <p>{t('office.noSubscription')}</p>
      )}
      <p className={styles.note}>{t('office.syntheticPricing')}</p>
      {checkoutAllowed && (
        <form
          aria-label={t('office.offerPreview')}
          className={styles.form}
          noValidate
          onChange={() => {
            setQuote(null);
            setInvalid(false);
          }}
          onSubmit={(event) => {
            event.preventDefault();
            const fields = getValues();
            const amount = checkoutPreview(data, {
              ...fields,
              planId: Number(fields.planId),
            });
            setQuote(amount);
            setInvalid(amount === null);
          }}
        >
          <h3>{t('office.offerPreview')}</h3>
          <label className={common.field}>
            {t('office.plan')}
            <select {...register('planId')} aria-invalid={invalid}>
              {data.offers.map((o) => (
                <option key={o.id} value={o.id}>
                  {localized(o.name)}
                </option>
              ))}
            </select>
          </label>
          <label className={common.field}>
            {t('office.cycle')}
            <select {...register('cycle')}>
              <option value="monthly">{t('office.monthly')}</option>
              <option value="yearly">{t('office.yearly')}</option>
            </select>
          </label>
          <label className={common.field}>
            {t('office.method')}
            <select {...register('method')}>
              {['ccp', 'baridimob'].map((m) => (
                <option
                  key={m}
                  value={m}
                  disabled={
                    !data.instructions.some((i) => i.method === m && i.enabled)
                  }
                >
                  {t(`office.${m}`)}
                </option>
              ))}
            </select>
          </label>
          {invalid && (
            <p role="alert" className={common.fieldError}>
              {t('office.invalidCheckout')}
            </p>
          )}
          <Button
            type="submit"
            disabled={data.offers.length === 0 || !instruction}
          >
            {t('office.simulateCheckout')}
          </Button>
          {quote !== null && (
            <section aria-label={t('office.checkoutPreview')}>
              <p role="status">{t('office.checkoutPreview')}</p>
              <strong>{money(quote)}</strong>
              <p className={styles.note}>{t('office.previewNotSaved')}</p>
            </section>
          )}
        </form>
      )}
      <section aria-label={t('office.instructions')}>
        <h3>{t('office.instructions')}</h3>
        <p className={styles.note}>{t('office.noTransfer')}</p>
        {instruction ? (
          <dl className={styles.definition}>
            <dt>{t('office.method')}</dt>
            <dd>{t(`office.${instruction.method}`)}</dd>
            <dt>{t('office.beneficiary')}</dt>
            <dd>{localized(instruction.beneficiary)}</dd>
            <dt>{t('office.destination')}</dt>
            <dd>
              <bdi>{instruction.destination}</bdi>
            </dd>
            {instruction.key && (
              <>
                <dt>{t('office.accountKey')}</dt>
                <dd>
                  <bdi>{instruction.key}</bdi>
                </dd>
              </>
            )}
          </dl>
        ) : (
          <p>{t('office.instructionsUnavailable')}</p>
        )}
        <p className={styles.note}>{t('office.transferSteps')}</p>
      </section>
      {checkoutAllowed && <Button disabled>{t('office.checkout')}</Button>}
    </section>
  );
}

export function BillingWorkspacePanel(): ReactElement {
  const context = useRestaurantContext();
  const adapter = useAdapter();
  const query = useQuery({
    queryKey: [...context.queryKey, 'billing-workspace'],
    queryFn: ({ signal }) => adapter.billingWorkspace(context.scope, signal),
    enabled: context.company.permissions.includes('tenant.billing.read'),
  });
  if (query.isError)
    return (
      <ErrorPanel error={query.error} retry={() => void query.refetch()} />
    );
  if (query.isPending) return <LoadingPanel />;
  return (
    <SubscriptionPreview
      data={query.data}
      checkoutAllowed={context.company.permissions.includes(
        'tenant.billing.checkout',
      )}
    />
  );
}
