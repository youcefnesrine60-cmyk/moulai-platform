// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { ManagementAdapter } from '../business/contracts';

/** View-adapter contracts, not a claim that matching public APIs exist. */
export type TenantRole = 'owner' | 'manager' | 'employee';
export type Locale = 'fr' | 'en' | 'ar';
export type LocalizedLabel = Readonly<Record<Locale, string>>;
export type AccessErrorCode =
  | 'notConnected'
  | 'noAccess'
  | 'unlinked'
  | 'suspended'
  | 'notFound'
  | 'temporary';
export type ReviewProfile =
  | 'owner'
  | 'manager'
  | 'employee'
  | 'empty'
  | 'admin'
  | 'unlinked'
  | 'suspended'
  | 'error';

export interface AccessSession {
  readonly issuer: string;
  readonly subject: string;
  readonly displayName: LocalizedLabel;
  readonly area: 'tenant' | 'platform';
  readonly source: 'synthetic';
  readonly platformPermissions: readonly string[];
}

export interface OrganizationView {
  readonly id: number;
  readonly name: LocalizedLabel;
  readonly city: LocalizedLabel;
  readonly role: TenantRole;
  readonly accessMode: 'company-wide' | 'explicit';
  readonly permissions: readonly string[];
}

export interface RestaurantView {
  readonly id: number;
  readonly organizationId: number;
  readonly name: LocalizedLabel;
  readonly city: LocalizedLabel;
  readonly active: boolean;
}

/** Future integration must obtain these projections through verified backend reads. */
export interface AccessAdapter extends ManagementAdapter {
  readonly mode: 'disconnected' | 'synthetic';
  getSession(signal: AbortSignal): Promise<AccessSession | null>;
  openReview(profile: ReviewProfile): Promise<void>;
  signOut(): Promise<void>;
  organizations(signal: AbortSignal): Promise<readonly OrganizationView[]>;
  restaurants(
    organizationId: number,
    signal: AbortSignal,
  ): Promise<readonly RestaurantView[]>;
  restaurant(
    organizationId: number,
    restaurantId: number,
    signal: AbortSignal,
  ): Promise<RestaurantView>;
}

/** Carry only bounded UI outcomes; never token data or raw provider errors. */
export class AccessError extends Error {
  constructor(readonly code: AccessErrorCode) {
    super(code);
    this.name = 'AccessError';
  }
}
