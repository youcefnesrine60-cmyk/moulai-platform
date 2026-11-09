// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Shared primary entry points only; small contextual field icons retain their existing presentation.
import { useId, type ReactElement } from 'react';
import { useTranslation } from 'react-i18next';
import styles from './assistanceLaunchers.module.css';

export function AssistanceLaunchers({
  onHelp,
  onAssistant,
  expanded,
}: {
  onHelp: () => void;
  onAssistant: () => void;
  expanded?: 'guide' | 'assistant' | null;
}): ReactElement {
  const { t, i18n } = useTranslation();
  const id = useId();
  return (
    <nav
      className={styles.launchers}
      data-assistance-dock
      aria-label={t('help.open')}
      dir={i18n.dir()}
    >
      {(
        [
          [
            'guide',
            'Icon-help-MoulAI.png',
            'help.open',
            'help.tooltip',
            onHelp,
          ],
          [
            'assistant',
            'Icon-Assistant-MoulAI.png',
            'help.assistant',
            'help.assistant',
            onAssistant,
          ],
        ] as const
      ).map(([mode, file, label, tooltip, action]) => (
        <span className={styles.item} key={mode}>
          <button
            type="button"
            className={styles.button}
            aria-label={t(label)}
            aria-haspopup="dialog"
            aria-expanded={expanded === mode}
            aria-describedby={`${id}-${mode}-tooltip${mode === 'assistant' ? ` ${id}-unavailable` : ''}`}
            onClick={action}
          >
            <img
              src={`/brand/${file}`}
              width={48}
              height={48}
              alt=""
              aria-hidden="true"
              draggable={false}
            />
          </button>
          <span
            className={styles.tooltip}
            id={`${id}-${mode}-tooltip`}
            role="tooltip"
          >
            {t(tooltip)}
          </span>
        </span>
      ))}
      <span className={styles.srOnly} id={`${id}-unavailable`}>
        {t('help.pendingShort')}
      </span>
    </nav>
  );
}
