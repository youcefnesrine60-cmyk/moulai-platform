// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — real same-origin browser session; unsupported modules remain closed.
import { z } from 'zod';
import { disconnectedAdapter } from './disconnected';
import { type AccessAdapter } from './contracts';
import { webRequest } from './sessionHttp';
export { webRequest } from './sessionHttp';
const label = z.object({ fr: z.string(), en: z.string(), ar: z.string() });
const sessionFor = (mode: 'authenticated-local' | 'authenticated-staging') =>
  z.object({
    issuer: z.string(),
    subject: z.string(),
    displayName: label,
    area: z.enum(['tenant', 'platform']),
    source: z.literal(mode),
    expiresAt: z.number().int().positive(),
    platformPermissions: z.array(z.string()),
  });
const organization = z.object({
  id: z.number().int().positive(),
  name: label,
  city: label,
  role: z.enum(['owner', 'manager', 'employee']),
  accessMode: z.enum(['company-wide', 'explicit']),
  permissions: z.array(z.string()),
});
const restaurant = z.object({
  id: z.number().int().positive(),
  organizationId: z.number().int().positive(),
  name: label,
  city: label,
  active: z.boolean(),
});
export function createAuthenticatedAdapter(
  mode: 'authenticated-local' | 'authenticated-staging',
): AccessAdapter {
  const session = sessionFor(mode);
  return {
    ...disconnectedAdapter,
    mode,
    async getSession(signal) {
      return session.nullable().parse(await webRequest('/session', signal));
    },
    async signOut() {
      await webRequest('/auth/logout', undefined, 'POST');
    },
    async organizations(signal) {
      return z
        .array(organization)
        .parse(await webRequest('/organizations', signal));
    },
    async restaurants(id, signal) {
      return z
        .array(restaurant)
        .parse(await webRequest(`/organizations/${id}/restaurants`, signal));
    },
    async restaurant(company, id, signal) {
      return restaurant.parse(
        await webRequest(`/organizations/${company}/restaurants/${id}`, signal),
      );
    },
  };
}
export const operationalAdapter = createAuthenticatedAdapter(
  'authenticated-local',
);
