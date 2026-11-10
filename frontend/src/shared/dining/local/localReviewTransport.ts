// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

/** Local-only compatibility mapping; staging compilation removes its only caller. */
export function localReviewUrl(path: string): string {
  if (path === '/api/web/dining-session' || path === '/api/web/auth/logout')
    return '/local-d1/session';
  return path.replace(/^\/api\/web(?=\/|$)/, '/local-d1');
}
