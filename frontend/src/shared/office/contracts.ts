import type { RestaurantScope } from '../business/contracts';
import type { OrderStatus } from '../business/contracts';
import type { LocalizedLabel } from '../access/contracts';

/** Same order/category reads as the existing workspace, grouped locally for visualization. */
export interface ReportBreakdown {
  readonly restaurantId: number;
  readonly orderCounts: readonly {
    readonly status: OrderStatus;
    readonly count: number;
  }[];
  readonly categoryCounts: readonly {
    readonly id: number;
    readonly name: string;
    readonly count: number;
  }[];
}
export interface BillingWorkspace {
  readonly restaurantId: number;
  readonly subscription: {
    readonly id: number;
    readonly planId: number;
    readonly planName: LocalizedLabel;
    readonly status: 'pending' | 'trial' | 'active' | 'expired' | 'cancelled';
    readonly billingCycle: 'monthly' | 'yearly';
    readonly amount: number;
    readonly startsAt: string;
    readonly expiresAt: string;
  } | null;
  /** UI-only offer projection; no public plan-discovery endpoint is assumed. */
  readonly offers: readonly {
    readonly id: number;
    readonly name: LocalizedLabel;
    readonly monthly: number;
    readonly yearly: number;
  }[];
  readonly instructions: readonly {
    readonly method: 'ccp' | 'baridimob';
    readonly enabled: boolean;
    readonly beneficiary: LocalizedLabel;
    /** Deliberately nonnumeric, nonpayable placeholders in review fixtures. */
    readonly destination: string;
    readonly key: string | null;
  }[];
}

/** Read projections of existing backend contracts, never new API declarations. */
export interface ReportSummary {
  readonly restaurantId: number;
  readonly totalOrders: number;
  readonly totalProducts: number;
  readonly totalCategories: number;
  /** Integer centimes; null means unavailable, never inferred from unpaid orders. */
  readonly averageOrderValue: number | null;
  readonly monthlyGrowth: number | null;
}
export type PaymentStatus =
  'pending' | 'paid' | 'failed' | 'cancelled' | 'refunded';
export interface PaymentView {
  readonly id: number;
  readonly restaurantId: number;
  readonly amount: number;
  readonly currency: 'DZD';
  readonly method: 'ccp' | 'baridimob';
  readonly status: PaymentStatus;
  readonly createdAt: string;
  readonly receipt: {
    readonly reviewStatus: 'pending' | 'approved' | 'rejected';
    readonly reference: string;
  } | null;
}
export type PlatformSection = 'requests' | 'receipts' | 'audit';
export interface PlatformRecord {
  readonly id: number;
  readonly label: string;
  readonly status: string;
  readonly at: string;
  /** Payment review data, absent for registration/audit records. */
  readonly payment?: PaymentView;
}
export interface OfficeAdapter {
  reportBreakdown(
    scope: RestaurantScope,
    signal: AbortSignal,
  ): Promise<ReportBreakdown>;
  billingWorkspace(
    scope: RestaurantScope,
    signal: AbortSignal,
  ): Promise<BillingWorkspace>;
  report(
    scope: RestaurantScope,
    signal: AbortSignal,
  ): Promise<ReportSummary | null>;
  payments(
    scope: RestaurantScope,
    signal: AbortSignal,
  ): Promise<readonly PaymentView[]>;
  platformRecords(
    section: PlatformSection,
    signal: AbortSignal,
  ): Promise<readonly PlatformRecord[]>;
}
/** Existing platform permission names; tenant ownership never grants these. */
export const platformSectionPermission: Record<PlatformSection, string> = {
  requests: 'admins.manage',
  receipts: 'payments.review',
  audit: 'admins.manage',
};
