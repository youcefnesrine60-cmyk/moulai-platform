// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/primitives';

import { shortReference } from './referenceValue';
export function DiningReference({
  id,
  reference,
}: {
  id?: number;
  reference: string;
}) {
  const { t } = useTranslation();
  const [copy, setCopy] = useState<'idle' | 'ok' | 'error'>('idle');
  return (
    <div>
      {id && <bdi>{shortReference(id)}</bdi>}
      <details>
        <summary>{t('d1.referenceDetails')}</summary>
        <p>
          <bdi>
            {reference}
            {id ? ` · #${id}` : ''}
          </bdi>
        </p>
        <Button
          variant="secondary"
          type="button"
          onClick={async () => {
            try {
              if (!navigator.clipboard)
                throw new Error('clipboard_unavailable');
              await navigator.clipboard.writeText(reference);
              setCopy('ok');
            } catch {
              setCopy('error');
            }
          }}
        >
          {t('d1.copyReference')}
        </Button>
        {copy !== 'idle' && (
          <span role="status">
            {t(copy === 'ok' ? 'd1.copied' : 'd1.copyFailed')}
          </span>
        )}
      </details>
    </div>
  );
}
