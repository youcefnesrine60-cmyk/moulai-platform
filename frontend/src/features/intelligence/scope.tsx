// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useEffect, useMemo, type ReactElement } from 'react';
import { Outlet, useLocation, useOutletContext } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { identityKey, useAdapter, useSession } from '../../app/access';
import { AccessError } from '../../shared/access/contracts';
import { ErrorPanel } from '../../shared/ui/primitives';
import {
  useRestaurantContext,
  type RestaurantContext,
} from '../management/scope';
import styles from './intelligence.module.css';

interface IntelligenceContext extends RestaurantContext {
  readonly intelligenceKey: readonly (string | number)[];
}

/** Reuse admitted restaurant context and existing permissions; platform roles grant nothing. */
export function IntelligenceFrame(): ReactElement {
  const context = useRestaurantContext();
  const session = useSession();
  const adapter = useAdapter();
  const client = useQueryClient();
  const { t } = useTranslation();
  const location = useLocation();
  const { organizationId, restaurantId } = context.scope;
  const key = useMemo(
    () => [
      ...identityKey(session.data),
      organizationId,
      'restaurant',
      restaurantId,
      'intelligence',
    ],
    [session.data?.issuer, session.data?.subject, organizationId, restaurantId],
  );
  useEffect(
    () => () => {
      void client.cancelQueries({ queryKey: key });
      client.removeQueries({ queryKey: key });
      adapter.releaseAgentScope({ organizationId, restaurantId });
    },
    [adapter, client, key, organizationId, restaurantId],
  );
  const permission = location.pathname.includes('/conversations')
    ? 'tenant.conversations.read'
    : 'tenant.agents.read';
  if (!context.company.permissions.includes(permission))
    return <ErrorPanel error={new AccessError('noAccess')} />;
  return (
    <>
      <p className={styles.notice}>{t('intelligence.boundary')}</p>
      <Outlet
        context={
          { ...context, intelligenceKey: key } satisfies IntelligenceContext
        }
      />
    </>
  );
}

/** Identity/company/restaurant-qualified queries never reuse another context's payload. */
export function useIntelligence(): IntelligenceContext {
  return useOutletContext<IntelligenceContext>();
}

/** Safe agent/channel projection; permissions are checked in frame and adapter independently. */
export function useAgentWorkspace() {
  const context = useIntelligence();
  const adapter = useAdapter();
  return useQuery({
    queryKey: [...context.intelligenceKey, 'agents'],
    queryFn: ({ signal }) => adapter.agentWorkspace(context.scope, signal),
    enabled: context.company.permissions.includes('tenant.agents.read'),
    retry: false,
  });
}
