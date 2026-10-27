import { AccessError } from '../shared/access/contracts';
import type {
  RestaurantScope,
  RestaurantWorkspace,
} from '../shared/business/contracts';
import { orderStatuses } from '../shared/business/contracts';
import { billingFixture } from './billingFixtures';
import {
  platformSectionPermission,
  type OfficeAdapter,
  type PaymentView,
} from '../shared/office/contracts';

/** Entirely synthetic financial projections; no receipt bytes, credentials or write methods. */
export function createOfficeAdapter(
  authorize: (scope: RestaurantScope, permission: string) => void,
  platformAuthorize: (permission: string) => void,
  workspace: (
    scope: RestaurantScope,
    signal: AbortSignal,
  ) => Promise<RestaurantWorkspace>,
  pause: (signal: AbortSignal) => Promise<void>,
): OfficeAdapter {
  const paymentRows = (
    restaurantId: number,
  ): readonly [PaymentView, PaymentView, PaymentView] => [
    {
      id: restaurantId * 100 + 1,
      restaurantId,
      amount: 250000,
      currency: 'DZD',
      method: 'ccp',
      status: 'pending',
      createdAt: '2026-10-26T10:00:00Z',
      receipt: {
        reference: `BILLING-REVIEW-${restaurantId}`,
        reviewStatus: 'pending',
      },
    },
    {
      id: restaurantId * 100 + 2,
      restaurantId,
      amount: 250000,
      currency: 'DZD',
      method: 'baridimob',
      status: 'paid',
      createdAt: '2026-10-01T10:00:00Z',
      receipt: {
        reference: `ARCHIVE-REVIEW-${restaurantId}`,
        reviewStatus: 'approved',
      },
    },
    {
      id: restaurantId * 100 + 3,
      restaurantId,
      amount: 250000,
      currency: 'DZD',
      method: 'ccp',
      status: 'failed',
      createdAt: '2026-09-01T10:00:00Z',
      receipt: null,
    },
  ];
  return {
    async reportBreakdown(scope, signal) {
      authorize(scope, 'tenant.reports.read');
      const data = await workspace(scope, signal);
      signal.throwIfAborted();
      authorize(scope, 'tenant.reports.read');
      return {
        restaurantId: scope.restaurantId,
        orderCounts: orderStatuses.map((status) => ({
          status,
          count: data.orders.filter((o) => o.status === status).length,
        })),
        categoryCounts: data.categories.map((c) => ({
          id: c.id,
          name: c.name,
          count: data.products.filter((p) => p.categoryId === c.id).length,
        })),
      };
    },
    async billingWorkspace(scope, signal) {
      authorize(scope, 'tenant.billing.read');
      await pause(signal);
      signal.throwIfAborted();
      authorize(scope, 'tenant.billing.read');
      return structuredClone(billingFixture(scope.restaurantId));
    },
    async report(scope, signal) {
      authorize(scope, 'tenant.reports.read');
      const data = await workspace(scope, signal);
      signal.throwIfAborted();
      authorize(scope, 'tenant.reports.read');
      return {
        restaurantId: scope.restaurantId,
        totalOrders: data.orders.length,
        totalProducts: data.products.length,
        totalCategories: data.categories.length,
        averageOrderValue: null,
        monthlyGrowth: null,
      };
    },
    async payments(scope, signal) {
      authorize(scope, 'tenant.billing.read');
      await pause(signal);
      authorize(scope, 'tenant.billing.read');
      if (!Number.isSafeInteger(scope.restaurantId))
        throw new AccessError('notFound');
      return structuredClone(paymentRows(scope.restaurantId));
    },
    async platformRecords(section, signal) {
      platformAuthorize(platformSectionPermission[section]);
      await pause(signal);
      platformAuthorize(platformSectionPermission[section]);
      if (section === 'receipts')
        return [
          {
            id: 98001,
            label: 'PAYMENT-REVIEW-9201',
            status: 'pending',
            at: '2026-10-26T10:00:00Z',
            payment: paymentRows(9201)[0],
          },
        ];
      if (section === 'requests')
        return [
          {
            id: 98002,
            label: 'REGISTRATION-REVIEW-01',
            status: 'pending',
            at: '2026-10-26T09:00:00Z',
          },
        ];
      return [
        {
          id: 98003,
          label: 'AUDIT-REVIEW-01',
          status: 'receipt_submitted',
          at: '2026-10-26T10:00:00Z',
        },
      ];
    },
  };
}
