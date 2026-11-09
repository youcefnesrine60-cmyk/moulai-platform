// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
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
  requestOptions,
  quoteOptions,
  receiptOptions,
  useValues,
  type FormContext,
} from './fields';
import styles from './local.module.css';

export function ReceiptForm({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const v = useValues({
    quote: '',
    amount: '',
    currency: '',
    mode: '',
    reference: '',
    received: '',
    fold: '',
  });
  const [checked, setChecked] = useState(false);
  return (
    <FormBox
      context={context}
      title="receipt"
      operation="receipt"
      submit={async () => {
        if (!checked) throw new Error('receipt_observation_required');
        const quote = context.data.quotes?.find(
          (row) => String(row.id) === v.get('quote'),
        );
        if (!quote) throw new Error('proposal_required');
        return context.api.receipt(context.scope, {
          request_id: quote.request_id,
          quote_id: quote.id,
          received_amount: v.get('amount'),
          currency: v.get('currency'),
          mode: v.get('mode'),
          reference: v.get('reference'),
          received_at: await context.api.instant(
            context.scope,
            v.get('received'),
            v.get('fold'),
          ),
        });
      }}
    >
      <Pick
        label="proposal"
        name="quote"
        value={v.get('quote')}
        set={(value) => v.set('quote', value)}
        options={quoteOptions(context)}
      />
      <Field
        label="receivedAmount"
        name="amount"
        value={v.get('amount')}
        set={(value) => v.set('amount', value)}
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
      <Pick
        label="mode"
        name="mode"
        value={v.get('mode')}
        set={(value) => v.set('mode', value)}
        options={Object.keys(
          context.data.policy?.payment_instructions ?? {},
        ).map((value) => ({ value, label: value }))}
      />
      <Field
        label="receiptReference"
        name="reference"
        value={v.get('reference')}
        set={(value) => v.set('reference', value)}
      />
      <Instant
        label="receivedAt"
        name="received"
        value={v.get('received')}
        set={(value) => v.set('received', value)}
        fold={v.get('fold')}
        setFold={(value) => v.set('fold', value)}
      />
      <label className={styles.check}>
        <input
          name="received_observed"
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          required
        />
        {t('d1.certifyTestReceipt')}
      </label>
      <p>{t('d1.noRealFunds')}</p>
    </FormBox>
  );
}

export function InvoiceForm({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const v = useValues({
    request: '',
    occupation: '',
    currency: '',
    currencySource: '',
    roundingSource: '',
    reconciliation: '',
  });
  const [visitContext, setVisitContext] = useState(false);
  const [orders, setOrders] = useState<string[]>([]);
  const [prices, setPrices] = useState<Record<string, string>>({});
  const [sources, setSources] = useState<Record<string, string>>({});
  const [ack, setAck] = useState(false);
  const selected = (context.data.food_orders ?? []).filter((row) =>
    orders.includes(String(row.id)),
  );
  const lines = selected.flatMap((order) =>
    order.items.map((item) => ({ order, item })),
  );
  return (
    <FormBox
      context={context}
      title="invoice"
      operation="invoice"
      submit={() =>
        command(context, {
          operation: 'invoice',
          data: {
            ...(visitContext
              ? { occupation_id: integer(v.get('occupation')) }
              : { request_id: integer(v.get('request')) }),
            currency: v.get('currency'),
            lines: lines.map(({ order, item }) => ({
              order_id: order.id,
              order_item_id: item.id,
              description: item.description,
              quantity: String(item.quantity),
              unit_price: prices[String(item.id)] ?? '',
              source_reference: sources[String(item.id)] ?? '',
            })),
            currency_source: v.get('currencySource'),
            rounding_source: v.get('roundingSource'),
            reconciliation_reference: v.get('reconciliation'),
            legacy_discrepancies_acknowledged: ack,
          },
        })
      }
    >
      <label>
        <input
          type="checkbox"
          checked={visitContext}
          onChange={(e) => {
            setVisitContext(e.target.checked);
            setOrders([]);
            setPrices({});
            setSources({});
          }}
        />
        {t('d1.invoiceVisitContext')}
      </label>
      {visitContext ? (
        <Pick
          label="occupation"
          name="occupation"
          value={v.get('occupation')}
          set={(value) => v.set('occupation', value)}
          options={(context.data.occupations ?? [])
            .filter((row) => row.status === 'occupied')
            .map((row) => ({ value: String(row.id), label: '#' + row.id }))}
        />
      ) : (
        <Pick
          label="reservation"
          name="request"
          value={v.get('request')}
          set={(value) => v.set('request', value)}
          options={requestOptions(context)}
        />
      )}
      <Multi
        label="sourceOrders"
        name="orders"
        values={orders}
        set={(values) => {
          setOrders(values);
          const exact = (context.data.visit_orders ?? []).filter((row) =>
            values.includes(String(row.order_id)),
          );
          setPrices(
            Object.fromEntries(
              exact.flatMap((row) =>
                row.exact_lines.map((line) => [
                  String(line.order_item_id),
                  line.unit_price,
                ]),
              ),
            ),
          );
          setSources(
            Object.fromEntries(
              exact.flatMap((row) =>
                row.exact_lines.map((line) => [
                  String(line.order_item_id),
                  'tariff:' + line.tariff_id,
                ]),
              ),
            ),
          );
          if (exact[0]) v.set('currency', exact[0].currency);
        }}
        options={(context.data.food_orders ?? []).map((row) => ({
          value: String(row.id),
          label: `#${row.id} · ${row.status}`,
        }))}
        required
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
      <p className={styles.wide}>{t('d1.floatNotAuthoritative')}</p>
      {lines.map(({ order, item }) => (
        <div className={`${styles.row} ${styles.wide}`} key={item.id}>
          <p>
            {item.description} · {t('d1.quantity')}: {item.quantity} ·{' '}
            {t('d1.legacyDiagnostic')}: <bdi>{item.legacy_unit_price}</bdi>
          </p>
          <Field
            label="exactUnitPrice"
            name={`price_${item.id}`}
            value={prices[String(item.id)] ?? ''}
            set={(value) =>
              setPrices((current) => ({ ...current, [String(item.id)]: value }))
            }
          />
          <Field
            label="exactSource"
            name={`source_${item.id}`}
            value={sources[String(item.id)] ?? ''}
            set={(value) =>
              setSources((current) => ({
                ...current,
                [String(item.id)]: value,
              }))
            }
          />
          <span>#{order.id}</span>
        </div>
      ))}
      <Field
        label="currencySource"
        name="currency_source"
        value={v.get('currencySource')}
        set={(value) => v.set('currencySource', value)}
      />
      <Field
        label="roundingSource"
        name="rounding_source"
        value={v.get('roundingSource')}
        set={(value) => v.set('roundingSource', value)}
      />
      <Text
        label="reconciliation"
        name="reconciliation"
        value={v.get('reconciliation')}
        set={(value) => v.set('reconciliation', value)}
      />
      <Check label="ackDiscrepancies" name="ack" value={ack} set={setAck} />
    </FormBox>
  );
}

export function FinalizeInvoiceForm({ context }: { context: FormContext }) {
  const [id, setId] = useState('');
  const { t } = useTranslation();
  const selected = context.data.invoices?.find((row) => String(row.id) === id);
  const needsAllocation = Boolean(
    selected &&
    context.data.receipts?.some(
      (row) =>
        row.request_id === selected.request_id && row.status === 'verified',
    ),
  );
  const missingAllocation =
    needsAllocation && !context.data.capabilities.includes('advances.allocate');
  return (
    <FormBox
      context={context}
      title="finalizeInvoice"
      operation="finalize_invoice"
      submitDisabled={missingAllocation}
      submit={() => {
        const row = context.data.invoices?.find((row) => String(row.id) === id);
        if (!row) throw new Error('invoice_required');
        return command(context, {
          operation: 'finalize_invoice',
          invoice_id: row.id,
          expected_revision: row.revision,
        });
      }}
    >
      {missingAllocation && <p>{t('d1.allocationPermissionRequired')}</p>}
      <Pick
        label="invoice"
        name="invoice"
        value={id}
        set={setId}
        options={(context.data.invoices ?? []).map((row) => ({
          value: String(row.id),
          label: `#${row.id} · ${row.status} · ${row.total} ${row.currency}`,
        }))}
      />
    </FormBox>
  );
}

export function AllocationForm({ context }: { context: FormContext }) {
  const [invoice, setInvoice] = useState('');
  const [receipt, setReceipt] = useState('');
  return (
    <FormBox
      context={context}
      title="allocation"
      operation="allocate"
      submit={() =>
        command(context, {
          operation: 'allocate',
          invoice_id: integer(invoice),
          receipt_id: integer(receipt),
        })
      }
    >
      <Pick
        label="invoice"
        name="invoice"
        value={invoice}
        set={setInvoice}
        options={(context.data.invoices ?? []).map((row) => ({
          value: String(row.id),
          label: `#${row.id} · ${row.status}`,
        }))}
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
