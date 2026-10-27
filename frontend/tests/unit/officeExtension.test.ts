import { describe, expect, it } from 'vitest';
import { createSyntheticAdapter } from '../../src/review/syntheticAdapter';
import { disconnectedAdapter } from '../../src/shared/access/disconnected';
import {
  checkoutPreview,
  simulateVerification,
} from '../../src/shared/office/simulation';
import { officeFr } from '../../src/shared/i18n/office.fr';
import { officeEn } from '../../src/shared/i18n/office.en';
import { officeAr } from '../../src/shared/i18n/office.ar';
import type { VerificationDraft } from '../../src/shared/office/simulation';
import type { PaymentView } from '../../src/shared/office/contracts';

const scope = { organizationId: 9101, restaurantId: 9201 };
const signal = () => new AbortController().signal;
const payment: PaymentView = {
  id: 1,
  restaurantId: 9201,
  amount: 250000,
  currency: 'DZD',
  method: 'ccp',
  status: 'pending',
  createdAt: '2026-10-26T10:00:00Z',
  receipt: { reviewStatus: 'pending', reference: 'TEST-REF-001' },
};
const approve: VerificationDraft = {
  decision: 'approve',
  fundsReceived: true,
  reference: 'test ref 001',
  amount: '2500,00',
  currency: 'DZD',
  note: 'Synthetic bank verification hypothesis',
};

describe('zero-cost reports and billing projections', () => {
  it('groups only the admitted workspace orders and categories without inventing revenue', async () => {
    const adapter = createSyntheticAdapter(0);
    await adapter.openReview('owner');
    const workspace = await adapter.workspace(scope, signal());
    const report = await adapter.reportBreakdown(scope, signal());
    expect(report.orderCounts.reduce((n, r) => n + r.count, 0)).toBe(
      workspace.orders.length,
    );
    expect(report.categoryCounts.reduce((n, r) => n + r.count, 0)).toBe(
      workspace.products.length,
    );
    for (const row of report.categoryCounts)
      expect(row.count).toBe(
        workspace.products.filter((p) => p.categoryId === row.id).length,
      );
    expect('revenue' in report).toBe(false);
  });
  for (const [profile, selected] of [
    ['employee', { organizationId: 9101, restaurantId: 9202 }],
    ['manager', { organizationId: 9102, restaurantId: 9203 }],
    ['owner', { organizationId: 9101, restaurantId: 9203 }],
    ['admin', scope],
  ] as const)
    it(`denies ${profile} outside its financial/report scope`, async () => {
      const adapter = createSyntheticAdapter(0);
      await adapter.openReview(profile);
      await expect(
        adapter.billingWorkspace(selected, signal()),
      ).rejects.toBeDefined();
      await expect(
        adapter.reportBreakdown(selected, signal()),
      ).rejects.toBeDefined();
    });
  it('allows manager reports but refuses manager subscription data', async () => {
    const adapter = createSyntheticAdapter(0);
    await adapter.openReview('manager');
    expect((await adapter.reportBreakdown(scope, signal())).restaurantId).toBe(
      9201,
    );
    await expect(
      adapter.billingWorkspace(scope, signal()),
    ).rejects.toMatchObject({ code: 'noAccess' });
  });
  it('uses nonpayable data, distinct restaurant subscriptions and defensive copies', async () => {
    const adapter = createSyntheticAdapter(0);
    await adapter.openReview('owner');
    const data = await adapter.billingWorkspace(scope, signal());
    expect(
      data.instructions.every(
        (i) =>
          i.destination.startsWith('SYNTHETIC-') &&
          !/^\d+$/.test(i.destination),
      ),
    ).toBe(true);
    const other = await adapter.billingWorkspace(
      { organizationId: 9102, restaurantId: 9203 },
      signal(),
    );
    expect(data.subscription?.id).not.toBe(other.subscription?.id);
    expect(other.subscription?.status).toBe('expired');
    expect(data).not.toBe(await adapter.billingWorkspace(scope, signal()));
  });
  it('stops delayed billing reads on logout and aborted signals', async () => {
    const adapter = createSyntheticAdapter(20);
    await adapter.openReview('owner');
    const pending = adapter.billingWorkspace(scope, signal());
    const check = expect(pending).rejects.toMatchObject({ code: 'noAccess' });
    await adapter.signOut();
    await check;
    await adapter.openReview('owner');
    const controller = new AbortController();
    controller.abort();
    await expect(
      adapter.billingWorkspace(scope, controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
  });
  it('normal adapter refuses both new projections', async () => {
    await expect(
      disconnectedAdapter.billingWorkspace(scope, signal()),
    ).rejects.toMatchObject({ code: 'notConnected' });
    await expect(
      disconnectedAdapter.reportBreakdown(scope, signal()),
    ).rejects.toMatchObject({ code: 'notConnected' });
  });
  it('previews only available offers and methods; rejects a client-supplied price', async () => {
    const adapter = createSyntheticAdapter(0);
    await adapter.openReview('owner');
    const data = await adapter.billingWorkspace(scope, signal());
    const offer = data.offers[0]!;
    const valid = { planId: offer.id, cycle: 'monthly', method: 'ccp' };
    expect(checkoutPreview(data, valid)).toBe(offer.monthly);
    expect(
      checkoutPreview(data, { ...valid, cycle: 'yearly', method: 'baridimob' }),
    ).toBe(offer.yearly);
    for (const change of [
      { planId: 1 },
      { cycle: 'quarterly' },
      { method: 'card' },
      { amount: 1 },
    ])
      expect(checkoutPreview(data, { ...valid, ...change })).toBeNull();
    expect(checkoutPreview({ ...data, instructions: [] }, valid)).toBeNull();
  });
  it('retains complete FR/EN/AR copy for the extended screens', () => {
    for (const catalog of [officeEn, officeAr]) {
      expect(Object.keys(catalog).sort()).toEqual(Object.keys(officeFr).sort());
      expect(
        Object.values(catalog).every((text) => text.trim().length > 0),
      ).toBe(true);
    }
  });
});

describe('explicit bank-verification simulations without settlement', () => {
  it('accepts a consistent hypothetical approval without mutating the payment', () => {
    const before = structuredClone(payment);
    expect(simulateVerification(payment, approve)).toBe('approve');
    expect(payment).toEqual(before);
  });
  for (const change of [
    { fundsReceived: false },
    { fundsReceived: 'true' },
    { reference: 'OTHER-REF' },
    { reference: 'عربي' },
    { amount: '2499.99' },
    { amount: '2500.001' },
    { amount: '2.5e3' },
    { currency: 'USD' },
    { note: '  ' },
    { note: 'x'.repeat(2001) },
  ])
    it(`refuses incomplete/mismatching approval ${JSON.stringify(change).slice(0, 65)}`, () => {
      expect(
        simulateVerification(payment, { ...approve, ...change }),
      ).toBeNull();
    });
  it('accepts only a rejection without attested funds', () => {
    const reject = {
      decision: 'reject',
      fundsReceived: false,
      reference: '',
      amount: '',
      currency: '',
      note: 'Receipt rejected in a simulation',
    };
    expect(simulateVerification(payment, reject)).toBe('reject');
    expect(
      simulateVerification(payment, { ...reject, fundsReceived: true }),
    ).toBeNull();
    expect(
      simulateVerification(payment, { ...reject, amount: '2500' }),
    ).toBeNull();
  });
  for (const changed of [
    { ...payment, status: 'paid' as const },
    { ...payment, receipt: null },
    {
      ...payment,
      receipt: { reference: 'TEST-REF-001', reviewStatus: 'approved' as const },
    },
  ])
    it('refuses a final or missing receipt/payment state', () => {
      expect(simulateVerification(changed, approve)).toBeNull();
    });
});
