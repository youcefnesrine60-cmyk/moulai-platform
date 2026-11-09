// MoulAI™ — explicit offline journal projection; real persistence is proved separately in PostgreSQL.
import { render, screen, fireEvent, within } from '@testing-library/react';
import { it, expect, vi, afterEach } from 'vitest';
import i18n from '../../src/shared/i18n';
import { HistoryPanel } from '../../src/features/dining/local/HistoryPanel';
import { LocalDiningClient } from '../../src/shared/dining/local/client';
import { diningPresentationFixture } from '../fixtures/diningPresentation';
import { assistance } from '../../src/shared/i18n/assistance';
import { d1Fr } from '../../src/shared/i18n/d1.fr';
import { d1En } from '../../src/shared/i18n/d1.en';
import { d1Ar } from '../../src/shared/i18n/d1.ar';
afterEach(() => vi.restoreAllMocks());
for (const locale of ['fr', 'en', 'ar'] as const)
  it(
    'renders recorded changes, unknowns and missing reasons ' + locale,
    async () => {
      await i18n.changeLanguage(locale);
      const fixture = diningPresentationFixture(locale),
        api = new LocalDiningClient();
      const request = vi.spyOn(api, 'request').mockResolvedValue({
        items: [
          {
            id: 1,
            kind: 'table.physical_state_observed',
            occurred_at: '2026-11-05T10:00:00Z',
            request_id: null,
            author_key: 'member:31',
            author_name: 'Synthetic authorized name',
            author_name_source: 'current_profile',
            details: { table_id: 1, reason: '—', state: 'dirty' },
          },
          {
            id: 2,
            kind: 'future.event',
            occurred_at: '2026-11-05T10:01:00Z',
            request_id: null,
            author_key: 'kind:unknown',
            author_name: null,
            author_name_source: null,
            details: {},
          },
        ],
        total: 2,
        page: 1,
        page_size: 20,
        snapshot_id: 2,
        kinds: ['table.physical_state_observed', 'future.event'],
        authors: [],
        authors_truncated: false,
      });
      render(
        <HistoryPanel
          context={{
            api,
            scope: fixture.session.scopes[0]!,
            data: fixture.workspace,
            busy: false,
            run: async (work) => {
              await work();
            },
          }}
          onDenied={vi.fn()}
        />,
      );
      const a = assistance[locale];
      await screen.findByText('Synthetic authorized name');
      const row = screen.getByText('Synthetic authorized name').closest('tr')!;
      fireEvent.click(within(row).getByText(a['audit.changes']));
      expect(within(row).getByText(a['audit.valueMissing'])).toBeVisible();
      expect(
        within(row).getByText(
          { fr: d1Fr, en: d1En, ar: d1Ar }[locale]['d1.state_dirty'],
        ),
      ).toBeVisible();
      expect(screen.getAllByText(a['audit.reasonMissing'])).toHaveLength(2);
      expect(screen.getAllByText(a['audit.unknown']).length).toBeGreaterThan(0);
      expect(screen.queryByText('future.event')).not.toBeVisible();
      const unknownRow = screen
        .getAllByText(a['audit.unknown'])
        .find((e) => e.closest('tr'))!
        .closest('tr')!;
      fireEvent.click(within(unknownRow).getByText(a['audit.tech']));
      expect(within(unknownRow).getByText('future.event')).toBeVisible();
      expect(request).toHaveBeenCalledOnce();
    },
  );
