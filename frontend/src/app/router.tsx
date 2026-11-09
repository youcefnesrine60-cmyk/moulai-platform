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
import { RouteRecovery } from '../shared/ui/RenderRecovery';

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
    ErrorBoundary: RouteRecovery,
    HydrateFallback: LoadingPanel,
    children: [
      ...(import.meta.env.DEV &&
      ['dining', 'operational'].includes(import.meta.env.MODE)
        ? [
            ...['/menu', '/verify-document'].map((path) => ({
              path,
              lazy: async () => ({
                Component:
                  import.meta.env.MODE === 'operational'
                    ? (
                        await import('../features/dining/local/PublicDiningPage')
                      ).IntegratedPublicDiningPage
                    : (
                        await import('../features/dining/local/PublicDiningPage')
                      ).PublicDiningPage,
              }),
            })),
          ]
        : []),
      ...(import.meta.env.DEV && import.meta.env.MODE === 'dining'
        ? [
            {
              path: '/dining-local',
              lazy: async () => ({
                Component: (
                  await import('../features/dining/local/LocalDiningPage')
                ).LocalDiningPage,
              }),
            },
          ]
        : []),
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
              ...(import.meta.env.DEV && import.meta.env.MODE === 'operational'
                ? [
                    {
                      path: '/workspace/enrollment',
                      lazy: async () => ({
                        Component: (
                          await import('../features/integration/EnrollmentPage')
                        ).EnrollmentPage,
                      }),
                    },
                    {
                      path: '/workspace/invitations',
                      lazy: async () => ({
                        Component: (
                          await import('../features/integration/OperationalPages')
                        ).OperationalInvitationsPage,
                      }),
                    },
                  ]
                : []),
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
                  Component:
                    import.meta.env.DEV &&
                    import.meta.env.MODE === 'operational'
                      ? (
                          await import('../features/integration/OperationalPages')
                        ).OperationalRestaurantFrame
                      : (await import('../features/management/scope'))
                          .RestaurantFrame,
                }),
                children: [
                  ...(import.meta.env.DEV &&
                  import.meta.env.MODE === 'operational'
                    ? [
                        {
                          path: 'offer',
                          lazy: async () => ({
                            Component: (
                              await import('../features/integration/OwnerOfferPage')
                            ).OwnerOfferPage,
                          }),
                        },
                      ]
                    : []),
                  {
                    path: 'tables',
                    lazy: async () => ({
                      Component:
                        import.meta.env.DEV &&
                        import.meta.env.MODE === 'operational'
                          ? (
                              await import('../features/dining/local/LocalDiningPage')
                            ).IntegratedDiningPage
                          : (await import('../features/dining/DiningPage'))
                              .DiningPage,
                    }),
                  },
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
              ...(import.meta.env.DEV && import.meta.env.MODE === 'operational'
                ? [
                    {
                      path: '/platform/billing-countries',
                      lazy: async () => ({
                        Component: (
                          await import('../features/integration/EnrollmentPage')
                        ).BillingCountryReviewPage,
                      }),
                    },
                    {
                      path: '/platform/saas-payments',
                      lazy: async () => ({
                        Component: (
                          await import('../features/integration/SaasPayments')
                        ).SaasPaymentReviewPage,
                      }),
                    },
                    {
                      path: '/platform/pricing',
                      lazy: async () => ({
                        Component: (
                          await import('../features/integration/PricingCampaignsPage')
                        ).PricingCampaignsPage,
                      }),
                    },
                  ]
                : []),
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
                  Component:
                    import.meta.env.DEV &&
                    import.meta.env.MODE === 'operational'
                      ? (
                          await import('../features/integration/OperationalPages')
                        ).OperationalPlatformPage
                      : (await import('../features/platform/PlatformPage'))
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
