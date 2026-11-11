// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Presentation fixtures only; PostgreSQL/HTTP tests separately prove documentary authority and persistence.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider, createMemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import i18n from '../../src/shared/i18n';
import {
  SaasDocumentContent,
  OwnerSaasDocumentsPage,
  VerifySaasDocumentPage,
  saasDocument,
} from '../../src/features/integration/SaasDocuments';
import { enrollmentRequest } from '../../src/features/integration/EnrollmentPage';

vi.mock('../../src/features/integration/EnrollmentPage', () => ({
  enrollmentRequest: vi.fn(),
}));

vi.mock('../../src/app/access', () => ({
  useSession: () => ({ data: null }),
  identityKey: () => ['document-unit'],
}));

const fixture = {
  id: 1,
  reference: 'a'.repeat(43),
  version: 1,
  replaces_id: null,
  state: 'valid',
  issuer: 'MoulAI™',
  issued_at: '2026-11-11T04:00:00+00:00',
  content: {
    amount: '6000.00000000',
    currency: 'DZD',
    restaurant_name: 'SYNTHETIC RESTAURANT',
    starts_at: '2026-12-01T00:00:00',
    expires_at: '2027-01-01T00:00:00',
    period_status_at_issue: 'scheduled',
    synthetic: true,
  },
  verification_url:
    'https://127.0.0.1:5180/verify-saas-document?locale=fr#' + 'a'.repeat(43),
  svg: '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
  events: [],
};

describe('retained SaaS document presentation', () => {
  for (const language of ['fr', 'en', 'ar']) {
    for (const state of ['valid', 'invalidated'] as const) {
      it(`${language} shows ${state}, fictitious status and a scheduled period without a mutation control`, async () => {
        await i18n.changeLanguage(language);
        render(
          <SaasDocumentContent
            document={saasDocument.parse({ ...fixture, state })}
          />,
        );
        expect(
          screen.getByText(i18n.t('saasDoc.' + state)),
        ).toBeInTheDocument();
        expect(screen.getByText(i18n.t('saasDoc.fake'))).toBeInTheDocument();
        expect(
          screen.getByText(i18n.t('saasDoc.scheduled')),
        ).toBeInTheDocument();
        expect(screen.getAllByRole('button')).toHaveLength(2);
        expect(
          screen.queryByRole('button', { name: i18n.t('saasDoc.issue') }),
        ).not.toBeInTheDocument();
        expect(
          screen.queryByRole('button', { name: i18n.t('saasDoc.invalidate') }),
        ).not.toBeInTheDocument();
        expect(screen.getByRole('link')).toHaveAttribute(
          'href',
          fixture.verification_url,
        );
        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
          i18n.t('saasDoc.final'),
        );
        expect(screen.getByRole('article')).toHaveAttribute(
          'dir',
          language === 'ar' ? 'rtl' : 'ltr',
        );
      });
    }
  }
  it('rejects a non-synthetic document from this local-only contract', () => {
    expect(() =>
      saasDocument.parse({
        ...fixture,
        content: { ...fixture.content, synthetic: false },
      }),
    ).toThrow();
  });
  it('keeps a pending payment request distinct from an emitted document and prints only after a fresh read', async () => {
    await i18n.changeLanguage('fr');
    vi.mocked(enrollmentRequest).mockImplementation(async (path) =>
      path.includes('/documents?')
        ? []
        : [
            {
              id: 7,
              amount: '3000.00000000',
              currency: 'DZD',
              status: 'pending',
            },
          ],
    );
    const router = createMemoryRouter(
      [
        {
          path: '/:organizationId/:restaurantId/:paymentId',
          element: <OwnerSaasDocumentsPage />,
        },
      ],
      { initialEntries: ['/1/2/7'] },
    );
    const view = render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    const local = within(view.container);
    await local.findByRole('heading', {
      name: i18n.t('saasDoc.request'),
    });
    expect(local.getByText(i18n.t('saasDoc.requestHelp'))).toBeInTheDocument();
    expect(local.getAllByRole('img')).toHaveLength(1);
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    vi.mocked(enrollmentRequest).mockClear();
    await userEvent.click(
      local.getByRole('button', { name: i18n.t('saasDoc.print') }),
    );
    expect(enrollmentRequest).toHaveBeenCalledTimes(2);
    expect(print).toHaveBeenCalledOnce();
    expect(
      vi
        .mocked(enrollmentRequest)
        .mock.calls.every((call) => call[1] === undefined),
    ).toBe(true);
    print.mockRestore();
  });
  it('does not print or replay a command after a failed refresh', async () => {
    await i18n.changeLanguage('fr');
    let fail = false;
    vi.mocked(enrollmentRequest).mockImplementation(async (path) => {
      if (fail) throw new Error('operation_requires_review');
      return path.includes('/documents?')
        ? []
        : [{ id: 8, amount: '3000', currency: 'DZD', status: 'pending' }];
    });
    const router = createMemoryRouter(
      [
        {
          path: '/:organizationId/:restaurantId/:paymentId',
          element: <OwnerSaasDocumentsPage />,
        },
      ],
      { initialEntries: ['/1/2/8'] },
    );
    const view = render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    const local = within(view.container);
    await local.findByRole('heading', {
      name: i18n.t('saasDoc.request'),
    });
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    fail = true;
    await userEvent.click(
      local.getByRole('button', { name: i18n.t('saasDoc.print') }),
    );
    await local.findByRole('alert');
    expect(print).not.toHaveBeenCalled();
    print.mockRestore();
  });
  it('uses the QR locale and fragment for the minimal Arabic reader', async () => {
    await i18n.changeLanguage('fr');
    vi.mocked(enrollmentRequest)
      .mockReset()
      .mockResolvedValue({
        state: 'invalidated',
        reference: 'R'.repeat(43),
        issuer: 'MoulAI™',
        issued_at: '2026-11-11T00:00:00Z',
      });
    const router = createMemoryRouter(
      [{ path: '/verify-saas-document', element: <VerifySaasDocumentPage /> }],
      { initialEntries: ['/verify-saas-document?locale=ar#' + 'R'.repeat(43)] },
    );
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    await screen.findByRole('heading', {
      name: 'وثيقة أُلغي اعتمادها — يُحتفظ بالأصل',
    });
    expect(document.documentElement.dir).toBe('rtl');
    expect(enrollmentRequest).toHaveBeenCalledWith(
      '/saas-documents/verify',
      'POST',
      { reference: 'R'.repeat(43) },
    );
  });
  it('does not present an already paid unissued source as another payment request', async () => {
    await i18n.changeLanguage('fr');
    vi.mocked(enrollmentRequest)
      .mockReset()
      .mockImplementation(async (path) =>
        path.includes('/documents?')
          ? []
          : [{ id: 9, amount: '3000', currency: 'DZD', status: 'paid' }],
      );
    const router = createMemoryRouter(
      [
        {
          path: '/:organizationId/:restaurantId/:paymentId',
          element: <OwnerSaasDocumentsPage />,
        },
      ],
      { initialEntries: ['/1/2/9'] },
    );
    const view = render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    const local = within(view.container);
    await local.findByRole('heading', {
      name: i18n.t('saasDoc.retainedPayment'),
    });
    expect(
      local.queryByRole('heading', { name: i18n.t('saasDoc.request') }),
    ).not.toBeInTheDocument();
    expect(local.getByText(i18n.t('saasDoc.retainedHelp'))).toBeInTheDocument();
  });
});
