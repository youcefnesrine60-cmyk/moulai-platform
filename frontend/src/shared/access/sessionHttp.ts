// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Same-origin session transport shared with the future authenticated target.
// This module contains no review fixture, account, provider host or secret.
import { z } from 'zod';
import { AccessError } from './contracts';

/** No host override, browser token storage, retry or implicit business resubmission. */
export async function webRequest(
  path: string,
  signal?: AbortSignal,
  method = 'GET',
  body?: unknown,
): Promise<unknown> {
  const response = await fetch('/api/web' + path, {
    credentials: 'same-origin',
    cache: 'no-store',
    method,
    ...(body === undefined
      ? {}
      : {
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }),
    ...(signal ? { signal } : {}),
  });
  if (!response.ok) {
    if (response.status === 401)
      window.dispatchEvent(new Event('moulai-session-expired'));
    const data: unknown = await response.json().catch(() => null);
    const parsed = z
      .object({ detail: z.object({ code: z.enum(['suspended', 'unlinked']) }) })
      .safeParse(data);
    throw new AccessError(
      parsed.success
        ? parsed.data.detail.code
        : response.status === 401
          ? 'notConnected'
          : response.status === 403
            ? 'noAccess'
            : response.status === 404
              ? 'notFound'
              : 'temporary',
    );
  }
  return response.status === 204 ? null : response.json();
}
