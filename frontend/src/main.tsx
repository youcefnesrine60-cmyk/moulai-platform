// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router';
import './shared/styles/fonts.css';
import './shared/i18n';
import './shared/styles/global.css';
import { createAccessAdapter } from './shared/access/runtime';
import { createQueryClient, Providers } from './app/Providers';
import { routes } from './app/router';

const root = document.getElementById('root');
if (!root) throw new Error('Application root is required.');
const adapter = await createAccessAdapter();
createRoot(root).render(
  <StrictMode>
    <Providers adapter={adapter} client={createQueryClient()}>
      <RouterProvider router={createBrowserRouter(routes)} />
    </Providers>
  </StrictMode>,
);
