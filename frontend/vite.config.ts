// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';
import { readFileSync } from 'node:fs';
import { createLogger, type ProxyOptions } from 'vite';
import { redactLocalMessage } from './src/shared/access/logSafety.ts';
import { resolve, sep } from 'node:path';

/** Keep review fixtures local; never build or bind review mode to the network. */
export default defineConfig(({ command, mode }) => {
  if (
    ['review', 'dining', 'operational'].includes(mode) &&
    command !== 'serve'
  ) {
    throw new Error('Synthetic review mode cannot be built for publication.');
  }
  const instance =
    mode === 'operational'
      ? resolve(process.env.MOULAI_OPERATIONAL_DIR ?? '')
      : null;
  const ownedRoot = resolve('../artifacts/operational-local') + sep;
  if (instance && !instance.startsWith(ownedRoot))
    throw new Error('Explicit owned operational instance required.');
  const safeLogger = createLogger();
  for (const level of ['info', 'warn', 'warnOnce', 'error'] as const) {
    const write = safeLogger[level].bind(safeLogger);
    safeLogger[level] = (message, options) =>
      write(redactLocalMessage(message), options);
  }
  return {
    ...(mode === 'operational' ? { customLogger: safeLogger } : {}),
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
            const schedule = JSON.parse(
              readFileSync(
                new URL('./public/appearance-schedule.json', import.meta.url),
                'utf8',
              ),
            );
            if (
              !/^([01]\d|2[0-3]):[0-5]\d$/.test(schedule.dayStartsAt) ||
              !/^([01]\d|2[0-3]):[0-5]\d$/.test(schedule.nightStartsAt) ||
              schedule.dayStartsAt === schedule.nightStartsAt ||
              schedule.status !== 'approved-device-local'
            )
              throw new Error(
                'Appearance schedule must be explicit and approved for device-local opening.',
              );
            if (!html.includes(tag) || /<\/script/i.test(source))
              throw new Error(
                'Appearance bootstrap cannot be installed safely.',
              );
            return html.replace(
              tag,
              () =>
                `<script type="application/json" id="moulai-appearance-schedule">${JSON.stringify(schedule)}</script><script id="moulai-appearance">\n${source}\n</script>`,
            );
          },
        },
      },
      {
        name: 'moulai-local-review-only',
        configResolved(config) {
          if (
            ['review', 'dining', 'operational'].includes(mode) &&
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
      port: mode === 'operational' ? 5180 : mode === 'dining' ? 5574 : 5173,
      ...(instance
        ? {
            https: {
              key: readFileSync(
                resolve(instance, 'private/tls/server-key.pem'),
              ),
              cert: readFileSync(resolve(instance, 'private/tls/server.pem')),
            },
          }
        : {}),
      proxy:
        mode === 'operational'
          ? ({ '/api/web': { target: 'http://127.0.0.1:5582' } } as Record<
              string,
              ProxyOptions
            >)
          : mode === 'dining'
            ? {
                '/local-d1': { target: 'http://127.0.0.1:5581' },
                '/verify-reservation': { target: 'http://127.0.0.1:5581' },
                '/dining/verify-reservation': {
                  target: 'http://127.0.0.1:5581',
                },
              }
            : undefined,
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
