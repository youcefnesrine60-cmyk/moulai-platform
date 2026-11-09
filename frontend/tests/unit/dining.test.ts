// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { describe, it, expect } from 'vitest';
import { createSyntheticAdapter } from '../../src/review/syntheticAdapter';
import { disconnectedAdapter } from '../../src/shared/access/disconnected';
import { syntheticBalance } from '../../src/shared/dining/contracts';
import { diningFr } from '../../src/shared/i18n/dining.fr';
import { diningEn } from '../../src/shared/i18n/dining.en';
import { diningAr } from '../../src/shared/i18n/dining.ar';

const scope = { organizationId: 9101, restaurantId: 9201, branchId: 920101 };
const signal = () => new AbortController().signal;
const date = '2026-11-03';
describe('dining synthetic boundary', () => {
  it('keeps exact balances and rejects unsupported amount formats and excess', () => {
    expect(syntheticBalance('6000.00', '1500.00')).toBe('4500.00');
    expect(syntheticBalance('9007199254740993.01', '0.01')).toBe(
      '9007199254740993.00',
    );
    expect(() => syntheticBalance('1.00', '2.00')).toThrow();
    expect(() => syntheticBalance('1.005', '0.00')).toThrow();
  });
  it('fails closed outside review mode', async () => {
    await expect(
      disconnectedAdapter.diningBranches(scope, signal()),
    ).rejects.toMatchObject({ code: 'notConnected' });
    await expect(
      disconnectedAdapter.simulateDining(
        scope,
        { kind: 'finalizeInvoice', invoiceId: 1 },
        signal(),
      ),
    ).rejects.toMatchObject({ code: 'notConnected' });
  });
  it('isolates branches and deduplicates simulated allocation', async () => {
    const adapter = createSyntheticAdapter(0);
    await adapter.openReview('owner');
    await Promise.all([
      adapter.simulateDining(
        scope,
        { kind: 'finalizeInvoice', invoiceId: 1 },
        signal(),
      ),
      adapter.simulateDining(
        scope,
        { kind: 'finalizeInvoice', invoiceId: 1 },
        signal(),
      ),
    ]);
    const current = await adapter.diningWorkspace(scope, date, signal());
    expect(current.invoice).toMatchObject({
      status: 'finalized',
      total: '6000.00',
      allocated: '1500.00',
      balance: '4500.00',
    });
    expect(
      (
        await adapter.diningWorkspace(
          { ...scope, branchId: 920102 },
          date,
          signal(),
        )
      ).invoice?.status,
    ).toBe('draft');
    await expect(
      adapter.diningWorkspace({ ...scope, branchId: 920301 }, date, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
    await adapter.signOut();
    await expect(
      adapter.diningWorkspace(scope, date, signal()),
    ).rejects.toMatchObject({ code: 'noAccess' });
  });
  it('preserves future claims after departure and cleaning', async () => {
    const adapter = createSyntheticAdapter(0);
    await adapter.openReview('owner');
    await adapter.simulateDining(
      scope,
      { kind: 'departure', tableId: 1 },
      signal(),
    );
    await adapter.simulateDining(
      scope,
      { kind: 'clean', tableId: 1 },
      signal(),
    );
    const table = (await adapter.diningWorkspace(scope, date, signal()))
      .tables[0];
    expect(table).toMatchObject({
      physical: 'available',
      nextReservation: '22:00–23:30',
    });
    expect(
      (await adapter.diningWorkspace(scope, '2026-11-04', signal())).requests,
    ).toHaveLength(0);
  });
  it('does not grant operation powers to a read-only review role', async () => {
    const adapter = createSyntheticAdapter(0);
    await adapter.openReview('employee');
    expect(
      (
        await adapter.diningWorkspace(
          { ...scope, restaurantId: 9202, branchId: 920201 },
          date,
          signal(),
        )
      ).capabilities,
    ).toEqual(['read']);
    await expect(
      adapter.simulateDining(
        { ...scope, restaurantId: 9202, branchId: 920201 },
        { kind: 'clean', tableId: 2 },
        signal(),
      ),
    ).rejects.toMatchObject({ code: 'noAccess' });
  });
  it('rejects an old in-flight simulation after review identity reset', async () => {
    const adapter = createSyntheticAdapter(20);
    await adapter.openReview('owner');
    const pending = adapter.simulateDining(
      scope,
      { kind: 'finalizeInvoice', invoiceId: 1 },
      signal(),
    );
    await adapter.openReview('owner');
    await expect(pending).rejects.toMatchObject({ code: 'noAccess' });
    expect(
      (await adapter.diningWorkspace(scope, date, signal())).invoice?.status,
    ).toBe('draft');
  });
  it('has complete FR EN AR presentation keys', () => {
    expect(Object.keys(diningFr).sort()).toEqual(Object.keys(diningEn).sort());
    expect(Object.keys(diningFr).sort()).toEqual(Object.keys(diningAr).sort());
  });
});
