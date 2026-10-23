// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { fr } from './fr';

/** Exact base-catalog parity is enforced at compile time. */
export const en: Record<keyof typeof fr, string> = {
  'brand.tagline': 'Your restaurant workspace',
  'review.banner': 'Local review · synthetic data · no connected service',
  'review.badge': 'Test data',
  'review.title': 'Explore a review journey',
  'review.help':
    'This profile previews the interface only. It creates no account and grants no real access.',
  'review.profile': 'Test profile',
  'review.open': 'Open local review',
  'review.invalid': 'Choose a review profile.',
  'profile.owner': 'Owner · two companies',
  'profile.manager': 'Manager · company A',
  'profile.employee': 'Staff · one granted restaurant',
  'profile.empty': 'Staff · no granted restaurants',
  'profile.admin': 'Platform administration',
  'profile.unlinked': 'Identity without a local association',
  'profile.suspended': 'Suspended access',
  'profile.error': 'Temporary error',
  'access.eyebrow': 'YOUR MOULAI WORKSPACE',
  'access.title': 'Welcome to your workspace.',
  'access.description':
    'Bring your companies, teams and restaurants together in one workspace.',
  'access.signin': 'Continue with Keycloak',
  'access.unavailable':
    'Sign-in will become available after Business Integration. No credentials are requested here.',
  'access.privacy': 'Personal access. A clearly defined scope.',
  'access.editorialTitle': 'Your restaurants.\nOne shared perspective.',
  'access.editorialBody':
    'A workspace for the people who bring restaurants to life, every day.',
  'access.editorialFooter': 'DESIGNED FOR YOUR EVERYDAY WORK',
  'access.featureOne': 'One company at a time',
  'access.featureTwo': 'Access tailored to each team',
  'access.featureThree': 'From the office to service, on every screen',
  'nav.workspace': 'My companies',
  'nav.restaurants': 'Restaurants',
  'nav.catalogue': 'Catalogue',
  'nav.orders': 'Orders',
  'nav.agents': 'Agents & conversations',
  'nav.reports': 'Reports',
  'nav.billing': 'Subscription & payments',
  'nav.management': 'MANAGEMENT',
  'nav.context': 'WORKSPACE',
  'nav.platform': 'Platform overview',
  'nav.requests': 'Registration requests',
  'nav.receipts': 'Payment review',
  'nav.audit': 'Administration & logs',
  'nav.menu': 'Open menu',
  'nav.close': 'Close menu',
  'nav.menuDescription': 'Workspace navigation',
  'nav.skip': 'Skip to content',
  'nav.tenantArea': 'Company workspace',
  'nav.platformArea': 'Platform administration',
  'nav.account': 'Review account',
  'nav.signout': 'Leave review',
  'nav.boundary': 'Each company keeps its own access scope.',
  'common.refresh': 'Refresh',
  'common.back': 'Back to companies',
  'common.loading': 'Loading your workspace…',
  'common.loadingDescription': 'Preparing information for your selection.',
  'common.retry': 'Try again',
  'common.changeProfile': 'Change review profile',
  'common.soon': 'Awaiting connection',
  'common.readOnly': 'Read only',
  'common.active': 'Active',
  'common.inactive': 'Inactive',
  'common.open': 'Open',
  'role.owner': 'Owner',
  'role.manager': 'Manager',
  'role.employee': 'Staff',
  'scope.company-wide': 'Company-wide scope',
  'scope.explicit': 'Granted restaurants',
  'companies.eyebrow': 'YOUR WORKSPACES',
  'companies.title': 'Each company, its own workspace.',
  'companies.description':
    'Choose a company to find the restaurants you can access.',
  'companies.open': 'Open company',
  'companies.footerTitle': 'A clear context, at every step.',
  'companies.footerBody':
    'Your restaurants and permissions always belong to the selected company. You can switch workspaces at any time.',
  'restaurants.eyebrow': 'SELECTED COMPANY',
  'restaurants.description':
    'Choose a restaurant to open its management workspace.',
  'restaurants.open': 'Open restaurant',
  'restaurants.count_one': '{{count}} accessible restaurant',
  'restaurants.count_other': '{{count}} accessible restaurants',
  'restaurants.emptyTitle': 'No restaurants granted.',
  'restaurants.emptyBody':
    'Your membership of this company currently grants access to no restaurants. Contact your manager.',
  'restaurant.eyebrow': 'RESTAURANT WORKSPACE',
  'restaurant.description':
    'Your restaurant is selected. Business tools will become available after connection to authorized services.',
  'restaurant.context': 'Your current access scope',
  'restaurant.contextBody':
    'The displayed sections follow this test profile’s permissions. No real business operation is performed.',
  'restaurant.back': 'All restaurants',
  'platform.eyebrow': 'MOULAI ADMINISTRATION',
  'platform.title': 'A dedicated platform workspace.',
  'platform.description':
    'Platform supervision is separate from company management. Access to company data is never implicit.',
  'platform.card.requests': 'Review registration requests',
  'platform.card.receipts': 'Verify received funds before approval',
  'platform.card.audit': 'View authorized administration tools',
  'state.notConnected.title': 'Connection not enabled.',
  'state.notConnected.body':
    'This workspace has no business connection yet. No remote service has been contacted.',
  'state.noAccess.title': 'You cannot access this workspace.',
  'state.noAccess.body':
    'Your profile lacks the permissions required for this workspace.',
  'state.unlinked.title': 'No access is associated with this identity.',
  'state.unlinked.body':
    'A verified company association is required. No account or access has been created automatically.',
  'state.suspended.title': 'Your access is suspended.',
  'state.suspended.body':
    'This access no longer allows you to view company data. Contact your manager.',
  'state.notFound.title': 'This workspace is unavailable.',
  'state.notFound.body':
    'The resource is missing or outside your access scope.',
  'state.temporary.title': 'Your workspace could not be loaded.',
  'state.temporary.body':
    'A temporary error occurred in this review. Try again or choose another profile.',
  'preferences.language': 'Interface language',
  'preferences.theme': 'Appearance',
  'theme.light': 'Light',
  'theme.dark': 'Dark',
  'theme.system': 'System preference',
  'app.title': 'MoulAI™ — Management workspace',
};
