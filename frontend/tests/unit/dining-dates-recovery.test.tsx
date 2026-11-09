// MoulAI™ — regression for time-only synthetic planning and bounded render recovery.
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RouterProvider, createMemoryRouter } from 'react-router';
import i18n from '../../src/shared/i18n';
import { OperationalBoard } from '../../src/shared/dining/OperationalBoard';
import { civilDay, displayMoment } from '../../src/shared/dining/operational';
import { RouteRecovery } from '../../src/shared/ui/RenderRecovery';
import { localTablePresentation } from '../../src/features/dining/local/presentation';
import { diningPresentationFixture } from '../fixtures/diningPresentation';

const props = () => {
  const f = diningPresentationFixture('fr');
  return {
    tables: localTablePresentation(f.workspace, f.planning, '2026-11-03', 'fr'),
    day: '2026-11-03',
    timezone: 'Africa/Algiers',
  };
};
afterEach(() => vi.restoreAllMocks());
describe('strict civil time and recoverable planning', () => {
  it('reproduces the original time-only RangeError and retains wall-clock provenance', () => {
    expect(() =>
      new Intl.DateTimeFormat('fr').formatToParts(new Date('20:00')),
    ).toThrow(RangeError);
    expect(civilDay('20:00', 'Africa/Algiers')).toBeNull();
    expect(displayMoment('20:00', 'fr', 'Africa/Algiers')).toBe('20:00');
    expect(
      displayMoment(
        '2026-11-03T19:00:00Z',
        'fr',
        'Africa/Algiers',
        '2026-11-03',
      ),
    ).toBe('20:00');
  });
  it('renders synthetic time-only periods without inventing a date', async () => {
    await i18n.changeLanguage('fr');
    const p = props();
    const period = {
      kind: 'reservation' as const,
      start: '20:00',
      end: '23:00',
    };
    p.tables = [
      { ...p.tables[0]!, periods: [period], nextReservation: period },
    ];
    render(<OperationalBoard {...p} />);
    expect(screen.getByTestId('table-card-1')).toBeVisible();
    expect(screen.getByText('20:00', { selector: 'time' })).toBeInTheDocument();
    expect(screen.queryByTestId('render-recovery')).toBeNull();
  });
  it.each([
    '',
    'not-a-date',
    '25:00',
    '2026-02-30T19:00:00Z',
    '2026-11-03T19:00:00',
  ])(
    'refuses invalid or ambiguous instant %s without a fabricated value',
    (value) => {
      expect(() => displayMoment(value, 'fr', 'Africa/Algiers')).toThrow();
    },
  );
  it.each(['fr', 'en', 'ar'] as const)(
    'contains malformed planning and retries safely in %s',
    async (locale) => {
      await i18n.changeLanguage(locale);
      const log = vi.spyOn(console, 'error').mockImplementation(() => {});
      const p = props();
      const bad = {
        ...p,
        tables: [
          {
            ...p.tables[0]!,
            nextReservation: {
              kind: 'reservation' as const,
              start: 'invalid-private-value',
              end: '23:00',
            },
          },
        ],
      };
      const { rerender } = render(
        <OperationalBoard
          {...bad}
          actions={() => <button>Forbidden stale action</button>}
        />,
      );
      expect(screen.getByTestId('render-recovery')).toBeVisible();
      expect(screen.getByText(/UI-[a-f0-9-]+/)).toBeVisible();
      expect(screen.queryByTestId('physical-badge')).toBeNull();
      expect(screen.queryByText('Forbidden stale action')).toBeNull();
      expect(screen.queryByText(/RangeError|invalid-private-value/)).toBeNull();
      const entry = log.mock.calls.find(
        (row) => row[0] === 'moulai_render_failure',
      );
      expect(JSON.stringify(entry)).not.toContain('invalid-private-value');
      expect(entry?.[1]).toMatchObject({ code: 'invalid_instant' });
      rerender(<OperationalBoard {...p} />);
      await userEvent
        .setup()
        .click(screen.getByRole('button', { name: i18n.t('recovery.retry') }));
      expect(screen.getByTestId('table-card-1')).toBeVisible();
    },
  );
  it.each([
    { day: '2026-99-99', timezone: 'UTC' },
    { day: '2026-11-03', timezone: 'Invalid/Zone' },
  ])('contains invalid day/timezone', (input) => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    render(<OperationalBoard {...props()} {...input} />);
    expect(screen.getByTestId('render-recovery')).toBeVisible();
    expect(screen.queryByTestId('physical-badge')).toBeNull();
  });
  it('contains failures above the board at the route boundary', async () => {
    await i18n.changeLanguage('fr');
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const Broken = () => {
      throw new RangeError('invalid secret date');
    };
    render(
      <RouterProvider
        router={createMemoryRouter([
          { path: '/', Component: Broken, ErrorBoundary: RouteRecovery },
        ])}
      />,
    );
    expect(await screen.findByTestId('render-recovery')).toBeVisible();
    expect(
      screen.getByRole('link', { name: 'Retour au tableau de bord' }),
    ).toHaveAttribute('href', '/workspace');
    expect(screen.queryByText('invalid secret date')).toBeNull();
  });
});
