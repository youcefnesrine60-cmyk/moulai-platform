// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Format retained documentary facts for reading; never replace exact source values or browser-localize UTC storage implicitly.
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

/** Historical service timestamps without an offset follow the existing UTC storage contract. */
export function readableDocumentDate(
  value: string,
  language: string,
): string | null {
  if (
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?$/.test(
      value,
    )
  )
    return null;
  const utc = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : value + 'Z';
  const date = new Date(utc);
  if (!Number.isFinite(date.getTime())) return null;
  const locale = language.startsWith('ar')
    ? 'ar-DZ'
    : language.startsWith('en')
      ? 'en-GB'
      : 'fr-FR';
  return (
    new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'medium',
      timeZone: 'UTC',
    }).format(date) + ' UTC'
  );
}

/** Keep the exact ISO timestamp available to assistive tools and technical inspection. */
export function DocumentDate({ value }: { value: string }) {
  const { t, i18n } = useTranslation();
  const label = readableDocumentDate(value, i18n.language);
  return label ? (
    <time dateTime={value} title={value}>
      <bdi>{label}</bdi>
    </time>
  ) : (
    <span>{t('saasDoc.dateUnavailable')}</span>
  );
}

/** Copy the full opaque reference on explicit request; a denied clipboard never claims success. */
export function CopyDocumentFact({
  value,
  label,
  className,
}: {
  value: string;
  label: string;
  className?: string | undefined;
}) {
  const { t } = useTranslation();
  const [outcome, setOutcome] = useState<'copied' | 'copyFailed' | null>(null);
  async function copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(value);
      setOutcome('copied');
    } catch {
      setOutcome('copyFailed');
    }
  }
  return (
    <span className={className} data-document-copy>
      <button
        type="button"
        onClick={() => void copy()}
        aria-label={`${t('saasDoc.copy')} — ${label}`}
      >
        {t('saasDoc.copy')}
      </button>
      <span role="status">{outcome ? t('saasDoc.' + outcome) : ''}</span>
    </span>
  );
}
