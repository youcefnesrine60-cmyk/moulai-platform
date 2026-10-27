// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { ReactElement, ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DirectionProvider } from '@radix-ui/react-direction';
import { useTranslation } from 'react-i18next';
import type { AccessAdapter } from '../shared/access/contracts';
import { AccessProvider } from './access';
import { BrandCanvas } from '../shared/ui/BrandCanvas';

/** No mutation retries, persisted query cache or cross-identity retained data. */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 15_000, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
}

export function Providers({
  adapter,
  client,
  children,
}: {
  adapter: AccessAdapter;
  client: QueryClient;
  children: ReactNode;
}): ReactElement {
  const { i18n } = useTranslation();
  return (
    <DirectionProvider dir={i18n.language === 'ar' ? 'rtl' : 'ltr'}>
      <QueryClientProvider client={client}>
        <AccessProvider adapter={adapter}>
          <BrandCanvas>{children}</BrandCanvas>
        </AccessProvider>
      </QueryClientProvider>
    </DirectionProvider>
  );
}
