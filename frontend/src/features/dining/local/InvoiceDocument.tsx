// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// This read-only presentation cannot issue, rotate or reactivate a document.
import { useTranslation } from 'react-i18next';
import type { z } from 'zod';
import { ownInvoice } from '../../../shared/dining/local/settlement';
import styles from './local.module.css';

type Invoice = Extract<z.infer<typeof ownInvoice>, { balance: string }>;

/** A real server-generated QR is displayed only for an explicitly issued current version. */
export function InvoiceDocument({
  document,
}: {
  document: Invoice['document'];
}) {
  const { t } = useTranslation();
  return (
    <section
      className={styles.invoiceDocument}
      aria-label={t('documents.verification')}
    >
      <h3>{t('documents.verification')}</h3>
      {document?.status === 'issued' ? (
        <>
          <div className={styles.documentQr}>
            <img
              width={176}
              height={176}
              alt={t('documents.qrAlt')}
              src={
                'data:image/svg+xml;charset=utf-8,' +
                encodeURIComponent(document.qr_svg)
              }
            />
          </div>
          <div>
            <p>
              {t('documents.reference')}: <bdi>{document.reference}</bdi> ·{' '}
              {t('d1.documentVersion')} <bdi>{document.version}</bdi>
            </p>
            <p>{t('documents.verificationHelp')}</p>
            <a href={document.url} target="_blank" rel="noreferrer" dir="ltr">
              {document.url}
            </a>
            {document.local_only && <p>{t('documents.localOnly')}</p>}
          </div>
        </>
      ) : (
        <p role="status">
          {t('documents.' + (document?.status ?? 'unissued'))}
        </p>
      )}
    </section>
  );
}
