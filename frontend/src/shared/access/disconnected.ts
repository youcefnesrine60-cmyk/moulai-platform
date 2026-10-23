// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { AccessError, type AccessAdapter } from './contracts';

/** Intentional fail-closed deployment state until Business Integration is approved. */
export const disconnectedAdapter: AccessAdapter = {
  mode: 'disconnected',
  async getSession() {
    return null;
  },
  async openReview() {
    throw new AccessError('notConnected');
  },
  async signOut() {
    /* No remote session or persisted token exists to clear. */
  },
  async organizations() {
    throw new AccessError('notConnected');
  },
  async restaurants() {
    throw new AccessError('notConnected');
  },
  async restaurant() {
    throw new AccessError('notConnected');
  },
  async workspace() {
    throw new AccessError('notConnected');
  },
  async saveReview() {
    throw new AccessError('notConnected');
  },
};
