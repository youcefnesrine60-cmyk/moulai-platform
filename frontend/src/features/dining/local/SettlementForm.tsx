// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Human-recorded full balance only; no gateway, automatic payment, refund or silent fixture.
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { invoiceBalance } from '../../../shared/dining/local/settlement';
import {
  FormBox,
  Field,
  Pick,
  Check,
  Instant,
  integer,
  useValues,
  type FormContext,
} from './fields';

export function SettlementForm({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const v = useValues({
    invoice: '',
    amount: '',
    currency: '',
    mode: '',
    reference: '',
    received: '',
    fold: '',
  });
  const [observed, setObserved] = useState(false);
  const [balance, setBalance] = useState<ReturnType<
    typeof invoiceBalance.parse
  > | null>(null);
  const [failed, setFailed] = useState(false);
  const selected = v.get('invoice');
  useEffect(() => {
    let current = true;
    setBalance(null);
    setFailed(false);
    if (selected)
      void context.api
        .request(
          context.api.root(context.scope) +
            `/invoices/${integer(selected)}/balance`,
        )
        .then((value) => {
          if (current) setBalance(invoiceBalance.parse(value));
        })
        .catch(() => {
          if (current) setFailed(true);
        });
    return () => {
      current = false;
    };
  }, [selected, context.api, context.scope]);
  return (
    <FormBox
      context={context}
      title="settlement"
      operation="settlement"
      submit={async () => {
        if (!observed) throw new Error('human_receipt_observation_required');
        const result = invoiceBalance.parse(
          await context.api.request(
            context.api.root(context.scope) +
              `/invoices/${integer(selected)}/settlement`,
            'POST',
            {
              amount: v.get('amount'),
              currency: v.get('currency'),
              mode: v.get('mode'),
              reference: v.get('reference'),
              received_at: await context.api.instant(
                context.scope,
                v.get('received'),
                v.get('fold'),
              ),
              observed: true,
            },
          ),
        );
        setBalance(result);
        return result;
      }}
    >
      <p>{t('d1.settlementScope')}</p>
      <Pick
        label="invoice"
        name="invoice"
        value={selected}
        set={(x) => v.set('invoice', x)}
        options={(context.data.invoices ?? [])
          .filter((x) => x.status === 'finalized')
          .map((x) => ({
            value: String(x.id),
            label: `#${x.id} · ${x.total} ${x.currency}`,
          }))}
      />
      {balance && (
        <p data-testid="invoice-balance">
          {t('d1.invoiceTotal')}:{' '}
          <bdi>
            {balance.total} {balance.currency}
          </bdi>{' '}
          · {t('d1.balance')}:{' '}
          <bdi>
            {balance.balance} {balance.currency}
          </bdi>
        </p>
      )}
      {failed && <p role="alert">{t('d1.publicUnavailable')}</p>}
      <Field
        label="receivedAmount"
        name="amount"
        value={v.get('amount')}
        set={(x) => v.set('amount', x)}
      />
      <Pick
        label="currency"
        name="currency"
        value={v.get('currency')}
        set={(x) => v.set('currency', x)}
        options={Object.keys(context.data.policy?.currencies ?? {}).map(
          (x) => ({ value: x, label: x }),
        )}
      />
      <Pick
        label="mode"
        name="mode"
        value={v.get('mode')}
        set={(x) => v.set('mode', x)}
        options={Object.keys(
          context.data.policy?.payment_instructions ?? {},
        ).map((x) => ({ value: x, label: x }))}
      />
      <Field
        label="receiptReference"
        name="reference"
        value={v.get('reference')}
        set={(x) => v.set('reference', x)}
      />
      <Instant
        label="receivedAt"
        name="received"
        value={v.get('received')}
        set={(x) => v.set('received', x)}
        fold={v.get('fold')}
        setFold={(x) => v.set('fold', x)}
      />
      <Check
        label="settlementObserved"
        name="observed"
        value={observed}
        set={setObserved}
      />
    </FormBox>
  );
}
