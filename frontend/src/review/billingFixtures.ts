import type { BillingWorkspace } from '../shared/office/contracts';

/** Nonpayable synthetic terms, never read from Settings or included in the normal build. */
export function billingFixture(restaurantId: number): BillingWorkspace {
  const name = { fr: 'Offre de revue', en: 'Review plan', ar: 'خطة المراجعة' };
  return {
    restaurantId,
    subscription: {
      id: restaurantId * 100 + 50,
      planId: 980101,
      planName: name,
      status:
        restaurantId === 9202
          ? 'trial'
          : restaurantId === 9203
            ? 'expired'
            : 'active',
      billingCycle: 'monthly',
      amount: 250000,
      startsAt:
        restaurantId === 9203 ? '2026-08-01T00:00:00Z' : '2026-10-01T00:00:00Z',
      expiresAt:
        restaurantId === 9203 ? '2026-09-01T00:00:00Z' : '2026-11-01T00:00:00Z',
    },
    offers: [{ id: 980101, name, monthly: 250000, yearly: 3000000 }],
    instructions: (['ccp', 'baridimob'] as const).map((method) => ({
      method,
      enabled: true,
      beneficiary: {
        fr: 'Bénéficiaire fictif — ne pas payer',
        en: 'Fictional recipient — do not pay',
        ar: 'مستفيد وهمي — لا تدفع',
      },
      destination:
        method === 'ccp'
          ? 'SYNTHETIC-CCP-NOT-PAYABLE'
          : 'SYNTHETIC-RIP-NOT-PAYABLE',
      key: method === 'ccp' ? 'TEST' : null,
    })),
  };
}
