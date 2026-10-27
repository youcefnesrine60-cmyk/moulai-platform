// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useEffect, type ReactElement } from 'react';
import { Navigate, Outlet, useLocation, type RouteObject } from 'react-router';
import { AccessError } from '../shared/access/contracts';
import { ErrorPanel, LoadingPanel } from '../shared/ui/primitives';
import { RequireSession, useLeaveReview } from './access';
import { Shell } from './Shell';

/** Restore keyboard context when a navigation replaces the current main view. */
function NavigationFocus(): ReactElement {
  const { pathname } = useLocation();
  useEffect(() => {
    document.getElementById('main-content')?.focus();
  }, [pathname]);
  return <Outlet />;
}

function NotFound(): ReactElement {
  const leave = useLeaveReview();
  return (
    <ErrorPanel
      error={new AccessError('notFound')}
      leave={() => void leave()}
    />
  );
}

/** Browser view routes only: none are new API endpoints or test-K10 registrations. */
export const routes: RouteObject[] = [
  {
    element: <NavigationFocus />,
    HydrateFallback: LoadingPanel,
    children: [
      { path: '/', element: <Navigate to="/access" replace /> },
      {
        path: '/access',
        lazy: async () => ({
          Component: (await import('../features/access/AccessPage')).AccessPage,
        }),
      },
      {
        element: <RequireSession area="tenant" />,
        children: [
          {
            element: <Shell />,
            children: [
              {
                path: '/workspace',
                lazy: async () => ({
                  Component: (
                    await import('../features/workspace/WorkspacePages')
                  ).OrganizationsPage,
                }),
              },
              {
                path: '/workspace/organizations/:organizationId/restaurants',
                lazy: async () => ({
                  Component: (
                    await import('../features/workspace/WorkspacePages')
                  ).RestaurantsPage,
                }),
              },
              {
                path: '/workspace/organizations/:organizationId/restaurants/:restaurantId',
                lazy: async () => ({
                  Component: (await import('../features/management/scope'))
                    .RestaurantFrame,
                }),
                children: [
                  {
                    path: 'reports',
                    lazy: async () => ({
                      Component: (
                        await import('../features/office/OfficePages')
                      ).ReportsPage,
                    }),
                  },
                  {
                    path: 'billing',
                    lazy: async () => ({
                      Component: (
                        await import('../features/office/OfficePages')
                      ).BillingPage,
                    }),
                  },
                  {
                    index: true,
                    lazy: async () => ({
                      Component: (
                        await import('../features/management/RestaurantProfilePage')
                      ).RestaurantProfilePage,
                    }),
                  },
                  {
                    path: 'catalogue',
                    lazy: async () => ({
                      Component: (
                        await import('../features/management/CataloguePage')
                      ).CataloguePage,
                    }),
                  },
                  {
                    path: 'orders',
                    lazy: async () => ({
                      Component: (
                        await import('../features/management/OrdersPage')
                      ).OrdersPage,
                    }),
                  },
                  {
                    path: 'orders/:orderId',
                    lazy: async () => ({
                      Component: (
                        await import('../features/management/OrdersPage')
                      ).OrderDetailPage,
                    }),
                  },
                  {
                    lazy: async () => ({
                      Component: (
                        await import('../features/intelligence/scope')
                      ).IntelligenceFrame,
                    }),
                    children: [
                      {
                        path: 'agents',
                        lazy: async () => ({
                          Component: (
                            await import('../features/intelligence/IntelligencePages')
                          ).AgentsPage,
                        }),
                      },
                      {
                        path: 'agents/:agentId',
                        lazy: async () => ({
                          Component: (
                            await import('../features/intelligence/IntelligencePages')
                          ).AgentDetailPage,
                        }),
                      },
                      {
                        path: 'channels',
                        lazy: async () => ({
                          Component: (
                            await import('../features/intelligence/IntelligencePages')
                          ).ChannelsPage,
                        }),
                      },
                      {
                        path: 'channels/:channelId',
                        lazy: async () => ({
                          Component: (
                            await import('../features/intelligence/IntelligencePages')
                          ).ChannelDetailPage,
                        }),
                      },
                      {
                        path: 'conversations',
                        lazy: async () => ({
                          Component: (
                            await import('../features/intelligence/IntelligencePages')
                          ).ConversationsPage,
                        }),
                      },
                      {
                        path: 'conversations/:conversationId',
                        lazy: async () => ({
                          Component: (
                            await import('../features/intelligence/IntelligencePages')
                          ).ConversationDetailPage,
                        }),
                      },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
      {
        element: <RequireSession area="platform" />,
        children: [
          {
            element: <Shell platform />,
            children: [
              {
                path: '/platform/requests',
                lazy: async () => ({
                  Component: (
                    await import('../features/platform/PlatformRecordsPage')
                  ).RequestsPage,
                }),
              },
              {
                path: '/platform/receipts',
                lazy: async () => ({
                  Component: (
                    await import('../features/platform/PlatformRecordsPage')
                  ).ReceiptsPage,
                }),
              },
              {
                path: '/platform/audit',
                lazy: async () => ({
                  Component: (
                    await import('../features/platform/PlatformRecordsPage')
                  ).AuditPage,
                }),
              },
              {
                path: '/platform',
                lazy: async () => ({
                  Component: (await import('../features/platform/PlatformPage'))
                    .PlatformPage,
                }),
              },
            ],
          },
        ],
      },
      { path: '*', element: <NotFound /> },
    ],
  },
];
