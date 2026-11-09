// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { Component, useState, type ReactNode, type ErrorInfo } from 'react';
import { useTranslation } from 'react-i18next';
import { useRouteError } from 'react-router';
import { Button } from './primitives';

/** No customer values, tokens, URLs or arbitrary exception messages enter diagnostics. */
export function recordRenderDiagnostic(
  error: unknown,
  componentStack?: string,
): string {
  const reference = `UI-${crypto.randomUUID()}`;
  console.error('moulai_render_failure', {
    reference,
    kind: error instanceof RangeError ? 'RangeError' : 'RenderError',
    code:
      error instanceof PresentationDataError
        ? error.code
        : 'unexpected_render_error',
    frames: (componentStack ?? '')
      .split('\n')
      .filter((line) => /^\s+at [A-Za-z]/.test(line))
      .map((line) => line.trim().split(' (')[0])
      .slice(0, 12),
  });
  return reference;
}

export class PresentationDataError extends Error {
  constructor(
    readonly code:
      'invalid_instant' | 'invalid_timezone' | 'invalid_planning_day',
  ) {
    super(code);
    this.name = 'PresentationDataError';
  }
}

function RecoveryPanel({
  reference,
  retry,
}: {
  reference: string;
  retry: () => void;
}) {
  const { t } = useTranslation();
  return (
    <section
      role="alert"
      data-testid="render-recovery"
      style={{
        padding: 24,
        background: 'var(--surface-card)',
        color: 'var(--text-primary)',
        border: '1px solid var(--border-strong)',
        borderRadius: 12,
      }}
    >
      <h2>{t('recovery.title')}</h2>
      <p>{t('recovery.message')}</p>
      <p>
        {t('recovery.reference')}: <bdi>{reference}</bdi>
      </p>
      <Button type="button" onClick={retry}>
        {t('recovery.retry')}
      </Button>{' '}
      <a href="/workspace">{t('recovery.dashboard')}</a>
    </section>
  );
}

/** Render failures remove the affected actions; no guessed availability survives. */
export class RenderBoundary extends Component<
  { children: ReactNode },
  { failed: boolean; reference: string }
> {
  state = { failed: false, reference: '' };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    this.setState({
      reference: recordRenderDiagnostic(error, info.componentStack ?? ''),
    });
  }
  render() {
    return this.state.failed ? (
      <RecoveryPanel
        reference={this.state.reference}
        retry={() => this.setState({ failed: false, reference: '' })}
      />
    ) : (
      this.props.children
    );
  }
}

/** Covers parent projections, lazy-route failures and all unhandled route rendering. */
export function RouteRecovery() {
  const error = useRouteError();
  const [reference] = useState(() => recordRenderDiagnostic(error));
  return (
    <RecoveryPanel
      reference={reference}
      retry={() => window.location.reload()}
    />
  );
}
