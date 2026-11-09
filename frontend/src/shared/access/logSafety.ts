// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — remove one-use login codes and tokens before local diagnostics are written.
export function redactLocalMessage(message: string): string {
  return message
    .replace(
      /((?:https?:\/\/[^\s?#'"<>]+|\/(?:api\/web\/auth|realms\/)[^\s?#'"<>]*))[?#][^\s'"<>]*/g,
      '$1?[REDACTED]',
    )
    .replace(
      /\b(?:code|state|session_state|session_code|access_token|refresh_token|client_secret|password)=([^\s&'"<>]+)/gi,
      (entry) => entry.slice(0, entry.indexOf('=') + 1) + '[REDACTED]',
    )
    .replace(/eyJ[A-Za-z0-9_.-]{30,}/g, '[TOKEN REDACTED]')
    .replace(/Bearer\s+[^\s'"<>]+/gi, 'Bearer [REDACTED]');
}

/** Sanitize values before JSON re-encoding so escaped diagnostic quotes stay valid. */
export function redactEvidenceJson(source: string): string {
  return JSON.stringify(
    JSON.parse(source),
    (_key: string, value: unknown) =>
      typeof value === 'string' ? redactLocalMessage(value) : value,
    2,
  );
}
