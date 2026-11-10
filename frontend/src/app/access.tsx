// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { isAuthenticatedAccess } from '../shared/access/contracts';
import {
  createContext,
  useEffect,
  useState,
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
import { useTranslation } from 'react-i18next';
import { SessionInformation } from '../shared/ui/SessionInformation';
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
  const client = useQueryClient();
  useEffect(() => {
    const clear = () => {
      void client.cancelQueries();
      client.clear();
      client.setQueryData(sessionKey, null);
    };
    window.addEventListener('moulai-session-expired', clear);
    return () => window.removeEventListener('moulai-session-expired', clear);
  }, [client]);
  return (
    <AdapterContext.Provider value={adapter}>
      {adapter.mode === 'authenticated-staging' && <StagingNotice />}
      {children}
      {isAuthenticatedAccess(adapter.mode) && <SessionWarning />}
    </AdapterContext.Provider>
  );
}

export function useAdapter(): AccessAdapter {
  const adapter = useContext(AdapterContext);
  if (!adapter) throw new Error('Access provider required.');
  return adapter;
}

/** Remote acceptance is synthetic and does not certify production readiness. */
function StagingNotice(): ReactElement {
  const { i18n } = useTranslation();
  const label = i18n.language.startsWith('ar')
    ? 'بيئة اختبار بعيدة معزولة — بيانات اصطناعية فقط — ليست بيئة إنتاج'
    : i18n.language.startsWith('en')
      ? 'Isolated remote staging — synthetic data only — not production'
      : 'Staging distant isolé — données fictives uniquement — hors production';
  return (
    <aside className="staging-notice" role="status">
      {label}
    </aside>
  );
}

export function useSession() {
  const adapter = useAdapter();
  return useQuery({
    queryKey: sessionKey,
    queryFn: ({ signal }) => adapter.getSession(signal),
    staleTime: isAuthenticatedAccess(adapter.mode) ? 0 : Infinity,
    refetchInterval: isAuthenticatedAccess(adapter.mode) ? 30000 : false,
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

/** Warn before token expiry; no refresh or business command is replayed. */
export function SessionWarning(): ReactElement | null {
  const { t } = useTranslation();
  const session = useSession();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const remaining = Math.ceil(
    (session.data?.expiresAt ?? Infinity) - now / 1000,
  );
  useEffect(() => {
    if (remaining <= 0 && session.data)
      window.dispatchEvent(new Event('moulai-session-expired'));
  }, [remaining, session.data]);
  if (!session.data || remaining > 60) return null;
  return (
    <aside role="status" aria-live="polite" className="session-warning">
      <strong>
        {t('followup.session', { seconds: Math.max(0, remaining) })}
      </strong>
      <SessionInformation
        local={session.data.source === 'authenticated-local'}
      />
      <a href="/api/web/auth/login">{t('followup.reconnect')}</a>
    </aside>
  );
}
