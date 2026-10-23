// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import {
  AccessError,
  type AccessAdapter,
  type AccessSession,
  type OrganizationView,
  type RestaurantView,
  type ReviewProfile,
  type TenantRole,
} from '../shared/access/contracts';
import { createManagementAdapter } from './managementAdapter';

// E1 seed projections for UI review only; never a runtime authorization policy.
const permissions: Record<TenantRole, readonly string[]> = {
  owner: [
    'tenant.agents.manage',
    'tenant.agents.read',
    'tenant.billing.checkout',
    'tenant.billing.read',
    'tenant.branches.manage',
    'tenant.branches.read',
    'tenant.catalog.manage',
    'tenant.catalog.read',
    'tenant.conversations.read',
    'tenant.conversations.respond',
    'tenant.groups.manage',
    'tenant.groups.read',
    'tenant.membership.self.leave',
    'tenant.membership.self.read',
    'tenant.memberships.manage',
    'tenant.memberships.read',
    'tenant.orders.manage',
    'tenant.orders.read',
    'tenant.organization.read',
    'tenant.organization.suspend',
    'tenant.organization.update',
    'tenant.ownership.manage',
    'tenant.receipts.submit',
    'tenant.reports.read',
    'tenant.restaurants.read',
    'tenant.restaurants.update',
  ],
  manager: [
    'tenant.agents.manage',
    'tenant.agents.read',
    'tenant.branches.manage',
    'tenant.branches.read',
    'tenant.catalog.manage',
    'tenant.catalog.read',
    'tenant.conversations.read',
    'tenant.conversations.respond',
    'tenant.groups.read',
    'tenant.membership.self.leave',
    'tenant.membership.self.read',
    'tenant.orders.manage',
    'tenant.orders.read',
    'tenant.organization.read',
    'tenant.reports.read',
    'tenant.restaurants.read',
    'tenant.restaurants.update',
  ],
  employee: [
    'tenant.branches.read',
    'tenant.catalog.read',
    'tenant.membership.self.leave',
    'tenant.membership.self.read',
    'tenant.orders.read',
    'tenant.restaurants.read',
  ],
};

const companies = [
  {
    id: 9101,
    name: { en: 'Maison Safran', fr: 'Maison Safran', ar: 'دار الزعفران' },
    city: { en: 'Algiers', fr: 'Alger', ar: 'الجزائر' },
  },
  {
    id: 9102,
    name: { en: 'Comptoir Atlas', fr: 'Comptoir Atlas', ar: 'مائدة الأطلس' },
    city: { en: 'Oran', fr: 'Oran', ar: 'وهران' },
  },
] as const;
const places: readonly RestaurantView[] = [
  {
    id: 9201,
    organizationId: 9101,
    name: {
      en: 'Algiers · Centre',
      fr: 'Alger · Centre',
      ar: 'الجزائر · الوسط',
    },
    city: { en: 'Algiers', fr: 'Alger', ar: 'الجزائر' },
    active: true,
  },
  {
    id: 9202,
    organizationId: 9101,
    name: {
      en: 'Algiers · Les Jardins',
      fr: 'Alger · Les Jardins',
      ar: 'الجزائر · الحدائق',
    },
    city: { en: 'Algiers', fr: 'Alger', ar: 'الجزائر' },
    active: true,
  },
  {
    id: 9203,
    organizationId: 9102,
    name: {
      en: 'Oran · Waterfront',
      fr: 'Oran · Front de mer',
      ar: 'وهران · الواجهة البحرية',
    },
    city: { en: 'Oran', fr: 'Oran', ar: 'وهران' },
    active: true,
  },
];
const explicitGrants: Partial<Record<ReviewProfile, readonly number[]>> = {
  manager: [9201],
  employee: [9202],
  empty: [],
};

/** Provide cancellable latency without network, persistent storage or credentials. */
async function pause(signal: AbortSignal, milliseconds: number): Promise<void> {
  signal.throwIfAborted();
  await new Promise<void>((resolve, reject) => {
    const abort = (): void => {
      clearTimeout(timer);
      reject(new DOMException('Aborted', 'AbortError'));
    };
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', abort);
      resolve();
    }, milliseconds);
    signal.addEventListener('abort', abort, { once: true });
  });
}

/** Isolate each review session; no identity is auto-created in any real system. */
export function createSyntheticAdapter(latency = 350): AccessAdapter {
  let profile: ReviewProfile | null = null;
  let generation = 0;
  const session = (): AccessSession | null =>
    profile === null
      ? null
      : {
          issuer: 'urn:moulai:synthetic-review',
          subject: `review-${profile}-${generation}`,
          displayName: {
            en: 'Review account',
            fr: 'Compte de revue',
            ar: 'حساب المراجعة',
          },
          area: profile === 'admin' ? 'platform' : 'tenant',
          source: 'synthetic',
          platformPermissions:
            profile === 'admin'
              ? ['admins.manage', 'restaurants.manage', 'payments.review']
              : [],
        };

  // ==============================================
  // BOUNDED SYNTHETIC PERSONAL ASSOCIATIONS
  // ==============================================
  const ownOrganizations = (): readonly OrganizationView[] => {
    if (!profile || profile === 'admin') throw new AccessError('noAccess');
    if (profile === 'unlinked') throw new AccessError('unlinked');
    if (profile === 'suspended') throw new AccessError('suspended');
    if (profile === 'error') throw new AccessError('temporary');
    const role: TenantRole = profile === 'empty' ? 'employee' : profile;
    return companies
      .filter((company) => role === 'owner' || company.id === 9101)
      .map((company) => ({
        ...company,
        role,
        permissions: permissions[role],
        accessMode: role === 'owner' ? 'company-wide' : 'explicit',
      }));
  };

  const scopedRestaurants = (
    organizationId: number,
  ): readonly RestaurantView[] => {
    const membership = ownOrganizations().find(
      (company) => company.id === organizationId,
    );
    if (
      !membership ||
      !membership.permissions.includes('tenant.restaurants.read')
    )
      throw new AccessError('notFound');
    return places.filter(
      (place) =>
        place.organizationId === organizationId &&
        (membership.accessMode === 'company-wide' ||
          explicitGrants[profile ?? 'unlinked']?.includes(place.id)),
    );
  };

  const management = createManagementAdapter(
    (scope, permission) => {
      const membership = ownOrganizations().find(
        (row) => row.id === scope.organizationId,
      );
      if (
        !membership ||
        !scopedRestaurants(scope.organizationId).some(
          (row) => row.id === scope.restaurantId,
        )
      )
        throw new AccessError('notFound');
      if (!membership.permissions.includes(permission))
        throw new AccessError('noAccess');
    },
    (signal) => pause(signal, latency),
  );

  return {
    workspace: management.workspace,
    saveReview: management.saveReview,
    mode: 'synthetic',
    async getSession(signal) {
      signal.throwIfAborted();
      return session();
    },
    async openReview(nextProfile) {
      management.reset();
      profile = nextProfile;
      generation += 1;
    },
    async signOut() {
      management.reset();
      profile = null;
      generation += 1;
    },
    async organizations(signal) {
      await pause(signal, latency);
      return structuredClone(ownOrganizations());
    },
    async restaurants(organizationId, signal) {
      await pause(signal, latency);
      return structuredClone(
        scopedRestaurants(organizationId).map((place) => {
          const name = management.restaurantName(place.id);
          return name
            ? { ...place, name: { fr: name, en: name, ar: name } }
            : place;
        }),
      );
    },
    async restaurant(organizationId, restaurantId, signal) {
      await pause(signal, latency);
      const place = scopedRestaurants(organizationId).find(
        (row) => row.id === restaurantId,
      );
      if (!place) throw new AccessError('notFound');
      const name = management.restaurantName(place.id);
      return structuredClone(
        name ? { ...place, name: { fr: name, en: name, ar: name } } : place,
      );
    },
  };
}
