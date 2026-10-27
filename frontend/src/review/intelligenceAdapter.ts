// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { AccessError } from '../shared/access/contracts';
import {
  ReviewConflict,
  type RestaurantScope,
} from '../shared/business/contracts';
import type {
  IntelligenceAdapter,
  PageResult,
} from '../shared/intelligence/contracts';
import {
  agentDraftSchema,
  conversationFilterSchema,
  pageSize,
} from '../shared/intelligence/validation';
import { intelligenceFixture } from './intelligenceFixtures';

/** Reuse the existing personal membership/grant authority; never infer ownership from IDs. */
export function createIntelligenceAdapter(
  authorize: (scope: RestaurantScope, permission: string) => void,
  wait: (signal: AbortSignal) => Promise<void>,
): IntelligenceAdapter & { reset(): void } {
  const stores = new Map<number, ReturnType<typeof intelligenceFixture>>();
  let generation = 0;
  const get = (
    scope: RestaurantScope,
  ): ReturnType<typeof intelligenceFixture> => {
    let store = stores.get(scope.restaurantId);
    if (!store) {
      store = intelligenceFixture(scope.restaurantId);
      stores.set(scope.restaurantId, store);
    }
    return store;
  };
  /** Revalidate both before and after cancellable work and identity/scope changes. */
  const ready = async (
    scope: RestaurantScope,
    permission: string,
    signal: AbortSignal,
  ): Promise<void> => {
    const started = generation;
    authorize(scope, permission);
    signal.throwIfAborted();
    await wait(signal);
    signal.throwIfAborted();
    if (started !== generation) throw new AccessError('noAccess');
    authorize(scope, permission);
  };
  const page = <T>(rows: readonly T[], skip: number): PageResult<T> => {
    if (!Number.isSafeInteger(skip) || skip < 0)
      throw new AccessError('notFound');
    return structuredClone({
      items: rows.slice(skip, skip + pageSize),
      total: rows.length,
      skip,
      limit: pageSize,
    });
  };
  const conversation = (scope: RestaurantScope, id: number) => {
    const store = get(scope);
    const row = store.conversations.find((item) => item.id === id);
    if (
      !row ||
      !store.workspace.agents.some(
        (agent) =>
          agent.id === row.agentId && agent.restaurantId === scope.restaurantId,
      ) ||
      !store.workspace.channels.some(
        (channel) =>
          channel.id === row.channelId && channel.agentId === row.agentId,
      )
    )
      throw new AccessError('notFound');
    return row;
  };
  return {
    reset() {
      generation += 1;
      stores.clear();
    },
    releaseAgentScope(scope) {
      generation += 1;
      stores.delete(scope.restaurantId);
    },
    async agentWorkspace(scope, signal) {
      await ready(scope, 'tenant.agents.read', signal);
      return structuredClone(get(scope).workspace);
    },
    async conversations(scope, filter, signal) {
      await ready(scope, 'tenant.conversations.read', signal);
      const values = conversationFilterSchema.parse(filter);
      const store = get(scope);
      if (
        values.agentId !== null &&
        !store.workspace.agents.some((row) => row.id === values.agentId)
      )
        throw new AccessError('notFound');
      const query = values.query.trim().toLocaleLowerCase();
      return page(
        store.conversations.filter(
          (row) =>
            (values.agentId === null || row.agentId === values.agentId) &&
            (values.status === 'all' || row.status === values.status) &&
            `${row.userName ?? ''} ${row.userId}`
              .toLocaleLowerCase()
              .includes(query),
        ),
        values.skip,
      );
    },
    async conversation(scope, id, signal) {
      await ready(scope, 'tenant.conversations.read', signal);
      return structuredClone(conversation(scope, id));
    },
    async messages(scope, id, skip, signal) {
      await ready(scope, 'tenant.conversations.read', signal);
      conversation(scope, id);
      return page(
        get(scope)
          .messages.filter((row) => row.conversationId === id)
          .sort(
            (a, b) => a.createdAt.localeCompare(b.createdAt) || a.id - b.id,
          ),
        skip,
      );
    },
    async saveAgentReview(scope, id, revision, draft, signal) {
      await ready(scope, 'tenant.agents.manage', signal);
      const store = get(scope);
      const value = agentDraftSchema.parse(draft);
      const agent = store.workspace.agents.find(
        (row) => row.id === id && row.restaurantId === scope.restaurantId,
      );
      if (!agent) throw new AccessError('notFound');
      if (store.workspace.reviewRevision !== revision)
        throw new ReviewConflict();
      // Only approved descriptive fields change; activation and provider JSON are excluded.
      store.workspace = {
        ...store.workspace,
        reviewRevision: revision + 1,
        agents: store.workspace.agents.map((row) =>
          row.id === id ? { ...row, ...value } : row,
        ),
      };
    },
  };
}
