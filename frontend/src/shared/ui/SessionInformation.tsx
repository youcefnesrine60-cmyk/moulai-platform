// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useTranslation } from 'react-i18next';
import styles from './ui.module.css';

/** Native disclosure remains usable by keyboard and never stores or restores input. */
export function SessionInformation({ local }: { local: boolean }) {
  const { t } = useTranslation();
  return (
    <details className={styles.disclosure}>
      <summary>{t('quality.sessionDetails')}</summary>
      <p>{t('quality.identity')}</p>
      <p>{t('quality.expiry')}</p>
      <p>{t(local ? 'quality.localDraft' : 'followup.sessionDraftStaging')}</p>
    </details>
  );
}
