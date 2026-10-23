// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import {
  createContext,
  useContext,
  type ReactElement,
  type ReactNode,
} from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Navigate, Outlet, useNavigate } from 'react-router';
import {
  AccessError,
  type AccessAdapter,
  type AccessSession,
} from '../shared/access/contracts';
import { ErrorPanel, LoadingPanel } from '../shared/ui/primitives';

const AdapterContext = createContext<AccessAdapter | null>(null);
export const sessionKey = ['access', 'session'] as const;

export function AccessProvider({
  adapter,
  children,
}: {
  adapter: AccessAdapter;
  children: ReactNode;
}): ReactElement {
  return (
    <AdapterContext.Provider value={adapter}>
      {children}
    </AdapterContext.Provider>
  );
}

export function useAdapter(): AccessAdapter {
  const adapter = useContext(AdapterContext);
  if (!adapter) throw new Error('Access provider required.');
  return adapter;
}

export function useSession() {
  const adapter = useAdapter();
  return useQuery({
    queryKey: sessionKey,
    queryFn: ({ signal }) => adapter.getSession(signal),
    staleTime: Infinity,
    retry: false,
  });
}

/** Bind all caches to the exact synthetic identity, never just its role. */
export function identityKey(
  session: AccessSession | null | undefined,
): readonly string[] {
  return [
    'access',
    session?.issuer ?? 'anonymous',
    session?.subject ?? 'anonymous',
  ];
}

export function useOrganizations() {
  const adapter = useAdapter();
  const session = useSession();
  return useQuery({
    queryKey: [...identityKey(session.data), 'organizations'],
    queryFn: ({ signal }) => adapter.organizations(signal),
    enabled: session.data?.area === 'tenant',
    retry: false,
  });
}

/** Cancel in-flight reads before changing identity; no stale tenant cache survives. */
export function useLeaveReview(): () => Promise<void> {
  const adapter = useAdapter();
  const client = useQueryClient();
  const navigate = useNavigate();
  return async () => {
    await client.cancelQueries();
    await adapter.signOut();
    client.clear();
    navigate('/access', { replace: true });
  };
}

/** UI area separation supplements, but never replaces, future backend checks. */
export function RequireSession({
  area,
}: {
  area: AccessSession['area'];
}): ReactElement {
  const session = useSession();
  const leave = useLeaveReview();
  if (session.isPending) return <LoadingPanel />;
  if (session.isError) return <ErrorPanel error={session.error} />;
  if (!session.data) return <Navigate to="/access" replace />;
  if (session.data.area !== area)
    return (
      <ErrorPanel
        error={new AccessError('noAccess')}
        leave={() => void leave()}
      />
    );
  return <Outlet />;
}
