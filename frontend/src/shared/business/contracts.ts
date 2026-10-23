// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

/** UI projections of existing schemas; these are not HTTP endpoint definitions. */
export interface RestaurantScope {
  readonly organizationId: number;
  readonly restaurantId: number;
}
export interface RestaurantProfile {
  readonly name: string;
  readonly type:
    'restaurant' | 'cafe' | 'fast_food' | 'bakery' | 'pizza' | 'other';
  readonly phone: string;
  readonly wilaya: string;
}
export interface Category {
  readonly id: number;
  readonly name: string;
  readonly sortOrder: number;
}
/** Integer centimes in the view model avoid floating-point display arithmetic. */
export interface Product {
  readonly id: number;
  readonly categoryId: number;
  readonly name: string;
  readonly description: string;
  readonly price: number;
  readonly available: boolean;
  readonly sortOrder: number;
}
export interface OptionGroup {
  readonly id: number;
  readonly productId: number;
  readonly name: string;
  readonly required: boolean;
  readonly multipleChoice: boolean;
  readonly sortOrder: number;
}
export interface ProductOption {
  readonly id: number;
  readonly groupId: number;
  readonly name: string;
  readonly extraPrice: number;
  readonly available: boolean;
  readonly sortOrder: number;
}
export const orderStatuses = [
  'pending',
  'confirmed',
  'preparing',
  'ready',
  'delivering',
  'delivered',
  'completed',
  'cancelled',
] as const;
export type OrderStatus = (typeof orderStatuses)[number];
/** Mirrors orders/constants.py LOCKED_STATUSES; it grants no transition permission. */
export const lockedOrderStatuses: readonly OrderStatus[] = [
  'delivering',
  'delivered',
  'completed',
  'cancelled',
];
export interface OrderItem {
  readonly id: number;
  readonly name: string;
  readonly quantity: number;
  readonly unitPrice: number;
  readonly total: number;
  readonly options: readonly string[];
}
export interface Order {
  readonly id: number;
  readonly number: string;
  readonly type: 'dine_in' | 'takeaway' | 'delivery';
  readonly status: OrderStatus;
  readonly createdAt: string;
  readonly customerName: string;
  readonly customerNote: string;
  readonly subtotal: number;
  readonly discount: number;
  readonly tax: number;
  readonly delivery: number;
  readonly total: number;
  readonly paid: boolean;
  readonly items: readonly OrderItem[];
  readonly history: readonly {
    readonly status: OrderStatus;
    readonly at: string;
  }[];
}
export interface RestaurantWorkspace {
  /** Ephemeral review concurrency counter, not an existing API revision field. */
  readonly reviewRevision: number;
  readonly profile: RestaurantProfile;
  readonly categories: readonly Category[];
  readonly products: readonly Product[];
  readonly groups: readonly OptionGroup[];
  readonly options: readonly ProductOption[];
  readonly orders: readonly Order[];
}
/** No fulfillment, payment, owner reassignment, activation or deletion command. */
export type ReviewCommand =
  | { readonly kind: 'profile'; readonly value: RestaurantProfile }
  | {
      readonly kind: 'category';
      readonly id: number | null;
      readonly value: Omit<Category, 'id'>;
    }
  | {
      readonly kind: 'product';
      readonly id: number | null;
      readonly value: Omit<Product, 'id'>;
    }
  | {
      readonly kind: 'group';
      readonly id: number | null;
      readonly value: Omit<OptionGroup, 'id'>;
    }
  | {
      readonly kind: 'option';
      readonly id: number | null;
      readonly value: Omit<ProductOption, 'id'>;
    }
  | { readonly kind: 'orderNote'; readonly id: number; readonly note: string };

export interface ManagementAdapter {
  workspace(
    scope: RestaurantScope,
    signal: AbortSignal,
  ): Promise<RestaurantWorkspace>;
  /** All effects remain in the synthetic adapter's memory until integration. */
  saveReview(
    scope: RestaurantScope,
    revision: number,
    command: ReviewCommand,
    signal: AbortSignal,
  ): Promise<void>;
}

export class ReviewConflict extends Error {
  /** A stale review must be reloaded instead of silently overwriting local edits. */
  constructor() {
    super('Review changed');
    this.name = 'ReviewConflict';
  }
}
