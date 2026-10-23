// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';
import { readFileSync } from 'node:fs';

/** Keep review fixtures local; never build or bind review mode to the network. */
export default defineConfig(({ command, mode }) => {
  if (mode === 'review' && command !== 'serve') {
    throw new Error('Synthetic review mode cannot be built for publication.');
  }
  return {
    plugins: [
      react(),
      {
        name: 'moulai-appearance-before-paint',
        transformIndexHtml: {
          order: 'pre',
          handler(html) {
            const tag = '<script src="/theme-init.js"></script>';
            const source = readFileSync(
              new URL('./public/theme-init.js', import.meta.url),
              'utf8',
            );
            if (!html.includes(tag) || /<\/script/i.test(source))
              throw new Error(
                'Appearance bootstrap cannot be installed safely.',
              );
            return html.replace(
              tag,
              () => `<script id="moulai-appearance">\n${source}\n</script>`,
            );
          },
        },
      },
      {
        name: 'moulai-local-review-only',
        configResolved(config) {
          if (
            mode === 'review' &&
            !['127.0.0.1', 'localhost', '::1'].includes(
              String(config.server.host),
            )
          ) {
            throw new Error(
              'Synthetic review must bind to an explicit loopback host.',
            );
          }
        },
      },
    ],
    build: { target: 'es2022' },
    envDir: false,
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      allowedHosts: ['localhost'],
    },
    preview: { host: '127.0.0.1', port: 4173, strictPort: true },
    test: {
      environment: 'jsdom',
      setupFiles: ['./tests/unit/setup.ts'],
      include: ['tests/unit/**/*.test.{ts,tsx}'],
      restoreMocks: true,
      clearMocks: true,
    },
  };
});
