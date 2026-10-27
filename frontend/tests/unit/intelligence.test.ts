// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { describe, expect, it } from 'vitest';
import { createSyntheticAdapter } from '../../src/review/syntheticAdapter';
import { createIntelligenceAdapter } from '../../src/review/intelligenceAdapter';
import { disconnectedAdapter } from '../../src/shared/access/disconnected';
import { agentDraftSchema } from '../../src/shared/intelligence/validation';
import { intelligenceFr } from '../../src/shared/i18n/intelligence.fr';
import { intelligenceEn } from '../../src/shared/i18n/intelligence.en';
import { intelligenceAr } from '../../src/shared/i18n/intelligence.ar';
import {
  AccessError,
  type ReviewProfile,
} from '../../src/shared/access/contracts';

const a = { organizationId: 9101, restaurantId: 9201 };
const b = { organizationId: 9102, restaurantId: 9203 };
const filter = { query: '', agentId: null, status: 'all', skip: 0 } as const;
const signal = (): AbortSignal => new AbortController().signal;

/** Each test gets isolated transient records and the existing permission/grant authority. */
async function review(profile: ReviewProfile = 'owner') {
  const adapter = createSyntheticAdapter(0);
  await adapter.openReview(profile);
  return adapter;
}

describe('intelligence projections and scoped review authorization', () => {
  it('never unions companies A/B belonging to the same owner', async () => {
    const adapter = await review();
    const first = await adapter.agentWorkspace(a, signal());
    const second = await adapter.agentWorkspace(b, signal());
    expect(
      first.agents.every((row) => row.restaurantId === a.restaurantId),
    ).toBe(true);
    expect(
      second.agents.every((row) => row.restaurantId === b.restaurantId),
    ).toBe(true);
    expect(first.agents.map((row) => row.id)).not.toEqual(
      second.agents.map((row) => row.id),
    );
    await expect(
      adapter.agentWorkspace({ ...a, restaurantId: 9203 }, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
    await expect(
      adapter.conversation(a, 920321, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
    await expect(
      adapter.messages(a, 920321, 0, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
    await expect(
      adapter.conversations(a, { ...filter, agentId: 920301 }, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
  });

  it('checks each conversation channel against the exact agent in the same restaurant', async () => {
    const adapter = await review();
    const workspace = await adapter.agentWorkspace(a, signal());
    const conversations = await adapter.conversations(a, filter, signal());
    for (const row of conversations.items) {
      expect(workspace.agents.some((agent) => agent.id === row.agentId)).toBe(
        true,
      );
      expect(
        workspace.channels.some(
          (channel) =>
            channel.id === row.channelId && channel.agentId === row.agentId,
        ),
      ).toBe(true);
    }
    const safeKeys = Object.keys(workspace.agents[0]!);
    expect(safeKeys).not.toContain('config');
    expect(safeKeys).not.toContain('ai_config');
    expect(Object.keys(workspace.channels[0]!)).not.toContain('config');
  });

  for (const profile of [
    'employee',
    'empty',
    'admin',
    'unlinked',
    'suspended',
    'error',
  ] as const)
    it(`${profile} has no implicit module access`, async () => {
      const adapter = await review(profile);
      const scope = profile === 'employee' ? { ...a, restaurantId: 9202 } : a;
      await expect(
        adapter.agentWorkspace(scope, signal()),
      ).rejects.toBeInstanceOf(AccessError);
      await expect(
        adapter.conversations(scope, filter, signal()),
      ).rejects.toBeInstanceOf(AccessError);
      await expect(
        adapter.messages(scope, 920121, 0, signal()),
      ).rejects.toBeInstanceOf(AccessError);
    });

  it('manager uses only granted restaurants without any platform elevation', async () => {
    const adapter = await review('manager');
    expect((await adapter.agentWorkspace(a, signal())).agents).toHaveLength(2);
    await expect(
      adapter.agentWorkspace({ ...a, restaurantId: 9202 }, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
    await expect(adapter.agentWorkspace(b, signal())).rejects.toMatchObject({
      code: 'notFound',
    });
  });

  it('owner can see an empty granted restaurant without inventing agents', async () => {
    const adapter = await review();
    expect(
      (await adapter.agentWorkspace({ ...a, restaurantId: 9202 }, signal()))
        .agents,
    ).toHaveLength(0);
  });

  it('paginates filtered conversations and ordered messages without losing rows', async () => {
    const adapter = await review();
    const first = await adapter.conversations(a, filter, signal());
    const next = await adapter.conversations(
      a,
      { ...filter, skip: 5 },
      signal(),
    );
    expect(first.total).toBe(7);
    expect(first.items).toHaveLength(5);
    expect(next.items).toHaveLength(2);
    expect(
      new Set([...first.items, ...next.items].map((row) => row.id)).size,
    ).toBe(7);
    expect(
      (
        await adapter.conversations(
          a,
          { ...filter, status: 'closed' },
          signal(),
        )
      ).items.map((row) => row.status),
    ).toEqual(['closed']);
    expect(
      (
        await adapter.conversations(
          a,
          { ...filter, query: 'visiteur de revue 3' },
          signal(),
        )
      ).items,
    ).toHaveLength(1);
    const messages = [];
    for (const skip of [0, 5, 10])
      messages.push(
        ...(await adapter.messages(a, 920121, skip, signal())).items,
      );
    expect(messages).toHaveLength(12);
    expect(messages.map((row) => row.createdAt)).toEqual(
      messages.map((row) => row.createdAt).sort(),
    );
    expect((await adapter.messages(a, 920122, 0, signal())).items).toHaveLength(
      0,
    );
    await expect(
      adapter.messages(a, 920121, -1, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
  });

  for (const profile of ['owner', 'manager'] as const)
    it(`${profile} applies descriptive edits only, with stale and foreign-ID refusal`, async () => {
      const adapter = await review(profile);
      const before = await adapter.agentWorkspace(a, signal());
      const agent = before.agents[0]!;
      const draft = {
        name: 'Nom local revu',
        description: 'Description',
        language: 'ar',
        tone: 'friendly',
      } as const;
      await adapter.saveAgentReview(
        a,
        agent.id,
        before.reviewRevision,
        draft,
        signal(),
      );
      const after = await adapter.agentWorkspace(a, signal());
      expect(after.agents[0]).toMatchObject({
        ...draft,
        active: agent.active,
        createdAt: agent.createdAt,
      });
      await expect(
        adapter.saveAgentReview(
          a,
          agent.id,
          before.reviewRevision,
          draft,
          signal(),
        ),
      ).rejects.toThrow('Review changed');
      await expect(
        adapter.saveAgentReview(
          a,
          920301,
          after.reviewRevision,
          draft,
          signal(),
        ),
      ).rejects.toMatchObject({ code: 'notFound' });
      adapter.releaseAgentScope(a);
      expect((await adapter.agentWorkspace(a, signal())).agents[0]!.name).toBe(
        agent.name,
      );
    });

  it('denies a missing manage permission independently of read permission', async () => {
    const adapter = createIntelligenceAdapter(
      (_scope, permission) => {
        if (permission !== 'tenant.agents.read')
          throw new AccessError('noAccess');
      },
      async () => {},
    );
    const data = await adapter.agentWorkspace(a, signal());
    await expect(
      adapter.saveAgentReview(
        a,
        data.agents[0]!.id,
        1,
        { name: 'Name', description: '', language: 'fr', tone: 'professional' },
        signal(),
      ),
    ).rejects.toMatchObject({ code: 'noAccess' });
  });

  it('cancels old identity/scope work and clears edits at identity change', async () => {
    const adapter = createSyntheticAdapter(30);
    await adapter.openReview('owner');
    const pending = adapter.conversations(a, filter, signal());
    const assertion = expect(pending).rejects.toMatchObject({
      code: 'noAccess',
    });
    await adapter.openReview('manager');
    await assertion;
    const data = await adapter.agentWorkspace(a, signal());
    await adapter.saveAgentReview(
      a,
      920101,
      data.reviewRevision,
      { name: 'Ephemeral', description: '', language: 'en', tone: 'casual' },
      signal(),
    );
    await adapter.signOut();
    await adapter.openReview('owner');
    expect(
      (await adapter.agentWorkspace(a, signal())).agents[0]!.name,
    ).not.toBe('Ephemeral');
    const controller = new AbortController();
    const aborted = adapter.messages(a, 920121, 0, controller.signal);
    const rejected = expect(aborted).rejects.toMatchObject({
      name: 'AbortError',
    });
    controller.abort();
    await rejected;
  });

  it('returns clones so caller mutation cannot contaminate stored review data', async () => {
    const adapter = await review();
    const data = await adapter.agentWorkspace(a, signal());
    Object.assign(data.agents[0]!, { name: 'tampered' });
    expect(
      (await adapter.agentWorkspace(a, signal())).agents[0]!.name,
    ).not.toBe('tampered');
  });

  it('disconnected runtime refuses every data/save operation', async () => {
    for (const call of [
      () => disconnectedAdapter.agentWorkspace(a, signal()),
      () => disconnectedAdapter.conversations(a, filter, signal()),
      () => disconnectedAdapter.conversation(a, 1, signal()),
      () => disconnectedAdapter.messages(a, 1, 0, signal()),
      () =>
        disconnectedAdapter.saveAgentReview(
          a,
          1,
          1,
          { name: 'x', description: '', language: 'fr', tone: 'professional' },
          signal(),
        ),
    ])
      await expect(call()).rejects.toMatchObject({ code: 'notConnected' });
  });
});

describe('schema boundaries and translations', () => {
  const valid = {
    name: 'Agent',
    description: '',
    language: 'fr',
    tone: 'professional',
  };
  it.each([
    { name: ' ' },
    { name: 'x'.repeat(101) },
    { description: 'x'.repeat(501) },
    { language: 'de' },
    { tone: 'aggressive' },
    { is_active: true },
    { config: {} },
    { ai_config: {} },
  ])('rejects unsupported or invalid input %j', (value) => {
    expect(agentDraftSchema.safeParse({ ...valid, ...value }).success).toBe(
      false,
    );
  });
  for (const catalog of [intelligenceEn, intelligenceAr])
    it('keeps exact locale keys and interpolation placeholders', () => {
      expect(Object.keys(catalog).sort()).toEqual(
        Object.keys(intelligenceFr).sort(),
      );
      for (const key of Object.keys(
        intelligenceFr,
      ) as (keyof typeof intelligenceFr)[])
        expect(
          [...catalog[key].matchAll(/{{(\w+)}}/g)].map((row) => row[1]).sort(),
        ).toEqual(
          [...intelligenceFr[key].matchAll(/{{(\w+)}}/g)]
            .map((row) => row[1])
            .sort(),
        );
    });
});
