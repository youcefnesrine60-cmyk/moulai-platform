// MoulAI™ — mocked HTTP presentation tests; real account and persistence proofs are recorded separately.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import i18n from '../../src/shared/i18n';
import { o3 } from '../../src/shared/i18n/o3';
import {
  EnrollmentPage,
  enrollmentRequest,
} from '../../src/features/integration/EnrollmentPage';

const sessionFixture = vi.hoisted(() => ({ source: 'authenticated-local' }));
vi.mock('../../src/app/access', () => ({
  identityKey: () => ['local-test-account'],
  useSession: () => ({
    data: { subject: 'local-test-account', source: sessionFixture.source },
  }),
}));
afterEach(() => {
  vi.unstubAllGlobals();
  sessionFixture.source = 'authenticated-local';
});

describe('explicit local enrollment documents', () => {
  it.each(['fr', 'en', 'ar'])(
    'does not advertise unverified staging drafts in %s',
    async (locale) => {
      sessionFixture.source = 'authenticated-staging';
      await i18n.changeLanguage(locale);
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('null')));
      render(
        <MemoryRouter>
          <QueryClientProvider
            client={
              new QueryClient({ defaultOptions: { queries: { retry: false } } })
            }
          >
            <EnrollmentPage />
          </QueryClientProvider>
        </MemoryRouter>,
      );
      expect(
        await screen.findByText(i18n.t('followup.draftUnavailableStaging')),
      ).toBeVisible();
      expect(
        screen.queryByRole('button', { name: i18n.t('followup.saveDraft') }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: i18n.t('followup.restoreDraft') }),
      ).not.toBeInTheDocument();
    },
  );
  it('keeps the same translated keys in FR, EN and AR', () => {
    expect(Object.keys(o3.fr).sort()).toEqual(Object.keys(o3.en).sort());
    expect(Object.keys(o3.fr).sort()).toEqual(Object.keys(o3.ar).sort());
  });
  it.each(['fr', 'en', 'ar'])(
    'does not preselect responses or confuse optional refusal with acceptance in %s',
    async (locale) => {
      await i18n.changeLanguage(locale);
      const fetcher = vi
        .fn()
        .mockImplementation(async (url: string, init?: RequestInit) => {
          if (url.endsWith('/enrollment'))
            return new Response(
              JSON.stringify({
                id: 1,
                organization_id: 2,
                company_name: 'LOCAL-FAKE',
                restaurant_name: 'LOCAL-RESTAURANT',
                branch_name: 'LOCAL-BRANCH',
                legal_entity_reference: 'LOCAL-FAKE-ENTITY',
                status: 'draft',
                restaurant_id: null,
                revision: 1,
              }),
            );
          if (url.includes('/billing-country'))
            return new Response(
              JSON.stringify({
                organization_id: 2,
                revision: 1,
                declared_country: null,
                validated_country: null,
                pending_country: null,
                pending_effective_at: null,
                requests: [],
                decisions: [],
              }),
            );
          if (url.includes('/documents/present'))
            return new Response(
              JSON.stringify(
                ['acceptance', 'information', 'optional_consent'].map(
                  (response_kind, index) => ({
                    id: index + 1,
                    version: 'LOCAL-TEST-v1',
                    sha256: 'a'.repeat(64),
                    locale,
                    content: 'FICTITIOUS LOCAL TEST ' + response_kind,
                    response_kind,
                    required: index < 2,
                    synthetic: true,
                  }),
                ),
              ),
            );
          if (url.endsWith('/documents/respond') && init?.method === 'POST')
            return new Response(null, { status: 204 });
          return new Response(null, { status: 404 });
        });
      vi.stubGlobal('fetch', fetcher);
      render(
        <MemoryRouter>
          <QueryClientProvider
            client={
              new QueryClient({ defaultOptions: { queries: { retry: false } } })
            }
          >
            <EnrollmentPage />
          </QueryClientProvider>
        </MemoryRouter>,
      );
      await userEvent.click(
        await screen.findByRole('button', { name: i18n.t('o3.present') }),
      );
      const optionalNo = await screen.findByRole('radio', {
        name: i18n.t('o3.no'),
      });
      expect(optionalNo).not.toBeChecked();
      expect(
        screen.getByRole('radio', { name: i18n.t('o3.yes') }),
      ).not.toBeChecked();
      expect(
        screen.getByRole('checkbox', { name: i18n.t('o3.accept') }),
      ).not.toBeChecked();
      expect(
        screen.getByRole('checkbox', { name: i18n.t('o3.informed') }),
      ).not.toBeChecked();
      await userEvent.click(optionalNo);
      const form = optionalNo.closest('form');
      if (!form) throw new Error('optional response form missing');
      await userEvent.click(form.querySelector('button')!);
      await waitFor(() =>
        expect(
          fetcher.mock.calls.some(
            ([url, init]) =>
              String(url).endsWith('/documents/respond') &&
              JSON.parse(String(init.body)).action === 'declined',
          ),
        ).toBe(true),
      );
      const response = fetcher.mock.calls.find(([url]) =>
        String(url).endsWith('/documents/respond'),
      );
      expect(JSON.parse(String(response?.[1].body))).toEqual({
        document_id: 3,
        version: 'LOCAL-TEST-v1',
        sha256: 'a'.repeat(64),
        locale,
        action: 'declined',
      });
      expect(
        screen
          .getByRole('heading', { name: i18n.t('o3.title') })
          .closest('section'),
      ).toHaveAttribute('dir', locale === 'ar' ? 'rtl' : 'ltr');
    },
  );
  it('never renders an arbitrary backend failure payload', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'PRIVATE SQL OR TOKEN' }), {
          status: 500,
        }),
      ),
    );
    await expect(enrollmentRequest('/enrollment')).rejects.toThrow(
      'operation_requires_review',
    );
  });
});

it.each(['fr', 'en', 'ar'])(
  'saves and explicitly restores partial enrollment text without submitting a dossier in %s',
  async (locale) => {
    await i18n.changeLanguage(locale);
    let saved: Record<string, string> = {};
    const fetcher = vi
      .fn()
      .mockImplementation(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/enrollment')) return new Response('null');
        if (url.endsWith('/enrollment-draft')) {
          if (init?.method === 'PUT') saved = JSON.parse(String(init.body));
          return new Response(
            JSON.stringify({ fields: saved, expires_at: 1900000000 }),
          );
        }
        return new Response(null, { status: 404 });
      });
    vi.stubGlobal('fetch', fetcher);
    render(
      <MemoryRouter>
        <QueryClientProvider
          client={
            new QueryClient({ defaultOptions: { queries: { retry: false } } })
          }
        >
          <EnrollmentPage />
        </QueryClientProvider>
      </MemoryRouter>,
    );
    const company = await screen.findByRole('textbox', {
      name: i18n.t('o3.company_name'),
    });
    await userEvent.type(company, 'LOCAL-FAKE partial');
    await userEvent.click(
      screen.getByRole('button', { name: i18n.t('followup.saveDraft') }),
    );
    await waitFor(() => expect(saved.company_name).toBe('LOCAL-FAKE partial'));
    expect(Object.keys(saved).sort()).toEqual(
      [
        'company_name',
        'legal_entity_reference',
        'full_name',
        'phone',
        'email',
        'restaurant_name',
        'branch_name',
      ].sort(),
    );
    await userEvent.clear(company);
    await userEvent.click(
      screen.getByRole('button', { name: i18n.t('followup.restoreDraft') }),
    );
    await waitFor(() => expect(company).toHaveValue('LOCAL-FAKE partial'));
    expect(
      fetcher.mock.calls.filter(
        ([url, init]) =>
          String(url).endsWith('/enrollment') && init?.method === 'POST',
      ),
    ).toHaveLength(0);
  },
);
