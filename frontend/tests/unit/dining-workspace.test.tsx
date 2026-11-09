// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — client state races and presentation never replace server authorization.
import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import {
  LocalDiningClient,
  LocalDiningError,
  type Snapshot,
} from '../../src/shared/dining/local/client';
import { useWorkspace } from '../../src/features/dining/local/useWorkspace';
import { localSections } from '../../src/features/dining/local/navigation';
import { diningPresentationFixture } from '../fixtures/diningPresentation';
afterEach(() => {
  vi.restoreAllMocks();
  history.replaceState(null, '', '/');
});
function prepare() {
  history.replaceState(null, '', '/dining-local?branch=300');
  const fixture = diningPresentationFixture('fr');
  fixture.session.scopes.push({
    ...fixture.session.scopes[0]!,
    branch_id: 301,
    branch_name: 'Other test branch',
  });
  vi.spyOn(LocalDiningClient.prototype, 'currentSession').mockResolvedValue(
    fixture.session,
  );
  vi.spyOn(LocalDiningClient.prototype, 'instant').mockResolvedValue(
    '2026-11-03T00:00:00Z',
  );
  vi.spyOn(LocalDiningClient.prototype, 'request').mockResolvedValue(
    fixture.planning,
  );
  return fixture;
}
it('exposes financial navigation only for server financial capabilities, never for cleaning or service-role text alone', () => {
  expect(localSections(['read', 'clean'])).toEqual(['planning', 'visits']);
  expect(localSections(['read', 'clean'])).not.toContain('finance');
  expect(localSections(['read', 'customer'])).toEqual(['planning', 'requests']);
  expect(localSections(['read', 'collect'])).not.toContain('finance');
  expect(localSections(['read', 'finance.read'])).toContain('finance');
  expect(localSections(['reservations.cancel_before_arrival'])).not.toContain(
    'finance',
  );
});
it('ignores a delayed old-branch workspace and immediately clears its forms and permissions', async () => {
  const fixture = prepare();
  let release!: (value: Snapshot) => void;
  const delayed = new Promise<Snapshot>((resolve) => {
    release = resolve;
  });
  const workspace = vi
    .spyOn(LocalDiningClient.prototype, 'workspace')
    .mockResolvedValue(fixture.workspace);
  const { result } = renderHook(useWorkspace);
  await waitFor(() => expect(result.current.data).not.toBeNull());
  act(() => result.current.changeScope('300'));
  expect(result.current.data).not.toBeNull();
  workspace.mockImplementation((scope) =>
    scope.branch_id === 300
      ? delayed
      : Promise.resolve({
          ...fixture.workspace,
          capabilities: ['read', 'clean'],
          tables: [],
        }),
  );
  let read!: Promise<void>;
  act(() => {
    read = result.current.reload();
  });
  // Scope changes are blocked during a submission/reload, avoiding a late operation in another scope.
  act(() => result.current.changeScope('301'));
  expect(result.current.scope?.branch_id).toBe(300);
  await act(async () => {
    release(fixture.workspace);
    await read;
  });
  act(() => result.current.changeScope('301'));
  expect(result.current.data).toBeNull();
  await waitFor(() =>
    expect(result.current.data?.capabilities).toEqual(['read', 'clean']),
  );
  expect(result.current.data?.tables).toEqual([]);
});
it('clears identity and former data when the server expires a session', async () => {
  const fixture = prepare();
  const workspace = vi
    .spyOn(LocalDiningClient.prototype, 'workspace')
    .mockResolvedValue(fixture.workspace);
  const { result } = renderHook(useWorkspace);
  await waitFor(() => expect(result.current.data).not.toBeNull());
  workspace.mockRejectedValue(new LocalDiningError(401, 'expired'));
  await act(async () => result.current.reload());
  expect(result.current.session).toBeNull();
  expect(result.current.scope).toBeNull();
  expect(result.current.data).toBeNull();
});
it('prevents concurrent submits before React rerenders and never retries writes', async () => {
  const fixture = prepare();
  vi.spyOn(LocalDiningClient.prototype, 'workspace').mockResolvedValue(
    fixture.workspace,
  );
  const { result } = renderHook(useWorkspace);
  await waitFor(() => expect(result.current.data).not.toBeNull());
  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  const work = vi.fn(async () => {
    await pending;
    return { saved: true };
  });
  let first!: Promise<void>;
  act(() => {
    first = result.current.run(work);
    void result.current.run(work);
  });
  expect(work).toHaveBeenCalledTimes(1);
  await act(async () => {
    release();
    await first;
  });
  expect(result.current.success).toBe(true);
  expect(work).toHaveBeenCalledTimes(1);
});
