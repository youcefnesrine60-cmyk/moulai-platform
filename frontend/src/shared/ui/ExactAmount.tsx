// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useTranslation } from 'react-i18next';

/** Remove padding zeroes for reading; never round or feed this presentation into a calculation. */
export function exactAmountText(value: string, locale: string): string {
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value);
  if (!match) return value;
  const formatter = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  const parts = new Intl.NumberFormat(locale).formatToParts(1.1);
  const separator = parts.find((part) => part.type === 'decimal')?.value ?? '.';
  const fraction = (match[3] ?? '').replace(/0+$/, '');
  const digits = Array.from({ length: 10 }, (_, index) =>
    formatter.format(index),
  );
  return (
    match[1] +
    formatter.format(BigInt(match[2]!)) +
    (fraction
      ? separator + [...fraction].map((digit) => digits[Number(digit)]).join('')
      : '')
  );
}

export function ExactAmount({
  value,
  currency,
}: {
  value: string;
  currency?: string | null;
}) {
  const { i18n } = useTranslation();
  return (
    <bdi>
      {exactAmountText(value, i18n.language)}
      {currency ? ' ' + currency : ''}
    </bdi>
  );
}
