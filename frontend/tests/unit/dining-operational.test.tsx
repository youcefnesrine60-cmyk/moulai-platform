// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import i18n from '../../src/shared/i18n';
import { OperationalBoard } from '../../src/shared/dining/OperationalBoard';
import {
  countPhysical,
  displayPhysical,
  displayMoment,
} from '../../src/shared/dining/operational';
import {
  localTablePresentation,
  requestPresentation,
} from '../../src/features/dining/local/presentation';
import { diningPresentationFixture } from '../fixtures/diningPresentation';
import { diningOpsFr } from '../../src/shared/i18n/diningOps.fr';
import { diningOpsEn } from '../../src/shared/i18n/diningOps.en';
import { diningOpsAr } from '../../src/shared/i18n/diningOps.ar';

const day = '2026-11-03';
const project = () => {
  const f = diningPresentationFixture('fr');
  return {
    fixture: f,
    tables: localTablePresentation(f.workspace, f.planning, day, 'fr'),
  };
};
describe('operational presentation preserves physical/business facts', () => {
  it('counts physically available/full-planning independently and never mutates inputs', () => {
    const f = diningPresentationFixture('fr');
    const before = JSON.stringify(f);
    const tables = localTablePresentation(f.workspace, f.planning, day, 'fr');
    expect(countPhysical(tables)).toMatchObject({
      available: 2,
      occupied: 1,
      dirty: 1,
      maintenance: 1,
      out_of_service: 2,
    });
    expect(tables[0]).toMatchObject({
      physical: 'available',
      fullyReserved: true,
      nextReservation: {
        start: '2026-11-03T19:00:00Z',
        end: '2026-11-03T22:00:00Z',
      },
    });
    expect(tables[1]).toMatchObject({
      physical: 'occupied',
      alerts: ['occupationLate'],
    });
    expect(tables[2]?.facts).toContainEqual({
      label: 'cleanStartActual',
      value: '2026-11-03T17:55:00Z',
      temporal: true,
    });
    expect(JSON.stringify(f)).toBe(before);
  });
  it('keeps current physical counts when planning is absent or a different date is selected', () => {
    const f = diningPresentationFixture('en');
    const tables = localTablePresentation(
      f.workspace,
      null,
      '2026-11-04',
      'en',
    );
    expect(countPhysical(tables).available).toBe(2);
    expect(tables.every((row) => !row.planningKnown)).toBe(true);
    expect(tables.flatMap((row) => row.requests)).toEqual([]);
    expect(tables[1]?.physical).toBe('occupied');
  });
  it('does not release late dirty tables or invent absent outage reasons and times', () => {
    const f = diningPresentationFixture('fr');
    f.workspace.server_time = '2026-11-03T19:00:00Z';
    const tables = localTablePresentation(f.workspace, f.planning, day, 'fr');
    expect(tables[2]).toMatchObject({
      physical: 'dirty',
      alerts: ['cleaningLate'],
    });
    expect(tables[4]?.facts).toEqual([
      { label: 'blockReason', value: null },
      { label: 'unavailableUntil', value: null, temporal: true },
    ]);
  });
  it('uses the current associated maintenance block, never tomorrow’s block as today’s reason', () => {
    const f = diningPresentationFixture('fr');
    const tables = localTablePresentation(f.workspace, f.planning, day, 'fr');
    expect(
      tables[3]?.facts.some(
        (row) =>
          row.label === 'blockReason' && row.value?.includes('Réparation'),
      ),
    ).toBe(true);
    f.workspace.blackouts = f.workspace.blackouts?.map((row) => ({
      ...row,
      starts_at: '2026-11-04T17:00:00Z',
      ends_at: '2026-11-04T22:00:00Z',
    }));
    expect(
      localTablePresentation(f.workspace, f.planning, day, 'fr')[3]?.facts[0]
        ?.value,
    ).toBeNull();
  });
  it('does not infer payment awaited when financial evidence is not visible', () => {
    const f = diningPresentationFixture('en');
    const held = f.workspace.requests![1]!;
    expect(requestPresentation(f.workspace, held)).toEqual([
      'hold',
      'humanPending',
      'paymentPending',
    ]);
    delete f.workspace.receipts;
    expect(requestPresentation(f.workspace, held)).toEqual([
      'hold',
      'humanPending',
    ]);
  });
  it('distinguishes expired holds and unvalidated receipts without changing a reservation', () => {
    const f = diningPresentationFixture('en');
    const held = f.workspace.requests![1]!;
    f.workspace.receipts = [
      {
        id: 1,
        request_id: held.id,
        currency: 'DZD',
        received_amount: '1000',
        status: 'manual_review',
      },
    ];
    expect(requestPresentation(f.workspace, held)).toContain('paymentReview');
    f.workspace.server_time = '2026-11-03T18:20:00Z';
    expect(requestPresentation(f.workspace, held)).toEqual([
      'holdExpired',
      'humanPending',
    ]);
    expect(held.status).toBe('held');
    delete f.workspace.claims;
    expect(requestPresentation(f.workspace, held)).not.toContain('holdExpired');
  });
  it('reports a conflict without modifying availability or claims', () => {
    const f = diningPresentationFixture('fr');
    f.workspace.blackouts!.push({
      id: 91,
      starts_at: '2026-11-03T19:30:00Z',
      ends_at: '2026-11-03T20:00:00Z',
      kind: 'maintenance',
      reason: 'Synthetic conflict',
      active: true,
      table_id: 1,
      zone_id: null,
    });
    const tables = localTablePresentation(f.workspace, f.planning, day, 'fr');
    expect(tables[0]).toMatchObject({
      physical: 'available',
      alerts: ['planningConflict'],
    });
    expect(f.workspace.claims![0]?.active).toBe(true);
  });
  it('keeps unknown physical states neutral and formats times in the branch timezone', () => {
    expect(displayPhysical('not-a-physical-state')).toBe('unknown');
    expect(
      displayMoment('2026-11-03T19:00:00Z', 'fr', 'Africa/Algiers'),
    ).toContain('20:00');
    expect(displayMoment('20:00', 'ar', 'Africa/Algiers')).toBe('20:00');
  });
  it('has complete nonempty FR/EN/AR labels', () => {
    for (const copy of [diningOpsEn, diningOpsAr]) {
      expect(Object.keys(copy).sort()).toEqual(Object.keys(diningOpsFr).sort());
      expect(Object.values(copy).every((value) => value.trim())).toBe(true);
    }
  });
});

describe('operational filters and keyboard controls', () => {
  it('filters physical state, resets and keeps all counters independent of planning', async () => {
    await i18n.changeLanguage('fr');
    const user = userEvent.setup();
    const { tables } = project();
    render(
      <OperationalBoard tables={tables} day={day} timezone="Africa/Algiers" />,
    );
    expect(screen.getByTestId('physical-count-available')).toHaveAttribute(
      'data-count',
      '2',
    );
    expect(
      within(screen.getByTestId('table-card-1')).getByTestId('planning-full'),
    ).toBeVisible();
    await user.click(screen.getByTestId('physical-filter-maintenance'));
    expect(screen.getByTestId('table-card-4')).toBeVisible();
    expect(screen.queryByTestId('table-card-1')).not.toBeInTheDocument();
    expect(screen.getByTestId('physical-count-all')).toHaveAttribute(
      'data-count',
      '7',
    );
    screen.getByTestId('physical-filter-reset').focus();
    await user.keyboard('{Enter}');
    expect(screen.getByTestId('table-card-1')).toBeVisible();
  });
  it('explains an empty filter result and provides a clear reset', async () => {
    await i18n.changeLanguage('fr');
    const user = userEvent.setup();
    const { tables } = project();
    render(
      <OperationalBoard
        tables={tables.slice(0, 1)}
        day={day}
        timezone="Africa/Algiers"
      />,
    );
    await user.click(screen.getByTestId('physical-filter-dirty'));
    expect(screen.getByTestId('physical-filter-empty')).toHaveTextContent(
      diningOpsFr['ops.noMatch'],
    );
    await user.click(
      within(screen.getByTestId('physical-filter-empty')).getByRole('button', {
        name: diningOpsFr['ops.reset'],
      }),
    );
    expect(screen.getByTestId('table-card-1')).toBeVisible();
  });
  it('does not render a business action in read-only cards or invoke an action on filter changes', async () => {
    await i18n.changeLanguage('fr');
    const user = userEvent.setup();
    const { tables } = project();
    const action = vi.fn();
    const { rerender } = render(
      <OperationalBoard
        tables={tables.slice(0, 1)}
        day={day}
        timezone="Africa/Algiers"
      />,
    );
    expect(
      within(
        screen.getByTestId('table-card-1').querySelector('footer')!,
      ).queryByRole('button'),
    ).not.toBeInTheDocument();
    rerender(
      <OperationalBoard
        tables={tables.slice(0, 1)}
        day={day}
        timezone="Africa/Algiers"
        actions={() => (
          <button disabled onClick={action}>
            Action synthétique désactivée
          </button>
        )}
      />,
    );
    await user.click(screen.getByTestId('physical-filter-all'));
    await user.click(
      screen.getByRole('button', { name: 'Action synthétique désactivée' }),
    );
    expect(action).not.toHaveBeenCalled();
  });
});
