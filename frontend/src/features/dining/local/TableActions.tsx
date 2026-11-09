// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useTranslation } from 'react-i18next';
import {
  ArrivalForm,
  OperationalForm,
  ExtendForm,
  PhysicalForms,
  ProofForm,
} from './ServiceForms';
import type { FormContext } from './fields';
import { DiningBadge } from '../../../shared/dining/OperationalBoard';
import { displayPhysical } from '../../../shared/dining/operational';
import { DiningReference } from '../../../shared/dining/reference';
import { Button } from '../../../shared/ui/primitives';
import styles from './local.module.css';

/** Context is convenience only: the server rechecks state, scope and current grants. */
export function TableActions({
  context,
  tableId,
  clear,
}: {
  context: FormContext;
  tableId: number | null;
  clear: () => void;
}) {
  const { t } = useTranslation();
  const table = context.data.tables?.find((row) => row.id === tableId);
  const has = (cap: string) => context.data.capabilities.includes(cap);
  const linkedRequests =
    context.data.request_tables
      ?.filter((row) => row.table_id === tableId)
      .map((row) => row.request_id) ?? [];
  const requests =
    context.data.requests?.filter((row) => linkedRequests.includes(row.id)) ??
    [];
  const related = requests.find((row) =>
    ['held', 'confirmed', 'pending'].includes(row.status),
  );
  const selectedContext = {
    ...context,
    ...(table ? { selectedTableId: table.id } : {}),
    ...(related ? { selectedRequestId: related.id } : {}),
  };
  return (
    <section
      id="dining-physical-actions"
      tabIndex={-1}
      className={table ? styles.card : undefined}
      data-testid="table-actions"
    >
      {table && (
        <header>
          <h2>{t('d1.actionsForTable', { table: table.code })}</h2>
          <DiningBadge kind={displayPhysical(table.physical_state)} physical />
          {requests.map((row) => (
            <div key={row.id}>
              <DiningReference id={row.id} reference={row.reference} />
            </div>
          ))}
          <Button type="button" variant="quiet" onClick={clear}>
            {t('d1.allActions')}
          </Button>
        </header>
      )}
      <div key={table?.id ?? 'all'}>
        {has('service') && (
          <>
            {(!table || table.physical_state === 'available') && (
              <ArrivalForm context={selectedContext} />
            )}
            {(!table ||
              !['occupied', 'dirty'].includes(table.physical_state)) && (
              <OperationalForm context={selectedContext} />
            )}
            {(!table || table.physical_state === 'occupied') && (
              <ExtendForm context={selectedContext} />
            )}
            {table?.physical_state === 'available' && (
              <ProofForm context={selectedContext} />
            )}
          </>
        )}
        {has('clean') &&
          (!table || ['occupied', 'dirty'].includes(table.physical_state)) && (
            <PhysicalForms context={selectedContext} />
          )}
        {table &&
          !has('service') &&
          !['occupied', 'dirty'].includes(table.physical_state) && (
            <p>{t('d1.noContextAction')}</p>
          )}
      </div>
    </section>
  );
}
