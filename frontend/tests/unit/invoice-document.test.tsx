// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Isolated presentation checks; real issuance, scope and invalidation are exercised by the local recipe.
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import i18n from '../../src/shared/i18n';
import { InvoiceDocument } from '../../src/features/dining/local/InvoiceDocument';
import { PublicDiningClient } from '../../src/shared/dining/local/publicClient';
import type { LocalDiningClient } from '../../src/shared/dining/local/client';
import { ownInvoice } from '../../src/shared/dining/local/settlement';

describe('explicit customer document state', () => {
  for (const language of ['fr', 'en', 'ar']) {
    for (const status of [
      'unissued',
      'invalidated',
      'origin_unavailable',
    ] as const) {
      it(`${language}: ${status} never displays a QR or an issuance control`, async () => {
        await i18n.changeLanguage(language);
        render(
          <InvoiceDocument
            document={
              status === 'unissued'
                ? { status }
                : { status, reference: 'UNIT-LOCAL-ONLY', version: 2 }
            }
          />,
        );
        expect(screen.getByRole('status')).toHaveTextContent(
          i18n.t('documents.' + status),
        );
        expect(screen.queryByRole('img')).not.toBeInTheDocument();
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
        expect(screen.queryByRole('link')).not.toBeInTheDocument();
      });
    }
  }
  it('keeps the locale in a read request and the visit proof outside the URL and body', async () => {
    const request = vi.fn().mockResolvedValue({ status: 'not_issued' });
    const api = new PublicDiningClient({
      request,
    } as unknown as LocalDiningClient);
    await api.invoice('a'.repeat(43), 'b'.repeat(43), 'ar');
    expect(request).toHaveBeenCalledWith(
      '/api/web/dining/public/invoice?locale=ar',
      'POST',
      { public_id: 'a'.repeat(43) },
      { 'X-Visit-Token': 'b'.repeat(43) },
    );
  });
  it('strips stale QR fields from an invalidated reply without changing exact invoice values', () => {
    const invoice = ownInvoice.parse({
      status: 'finalized',
      invoice_id: 1,
      currency: 'DZD',
      total: '6000.00000000',
      advance: '1500.00000000',
      paid: '0.00000000',
      balance: '4500.00000000',
      settlement_id: null,
      document: {
        status: 'invalidated',
        reference: 'UNIT-LOCAL-ONLY',
        version: 2,
        url: 'https://127.0.0.1:5180/verify-document',
        qr_svg: 'MUST-NOT-RENDER',
      },
    });
    expect('balance' in invoice && invoice.balance).toBe('4500.00000000');
    expect('document' in invoice && invoice.document).toEqual({
      status: 'invalidated',
      reference: 'UNIT-LOCAL-ONLY',
      version: 2,
    });
  });
});
