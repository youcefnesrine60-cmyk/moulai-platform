// MoulAI™ — option documentation and disconnected conversation never execute business operations.
import { render, screen, fireEvent, within } from '@testing-library/react';
import { it, expect, vi } from 'vitest';
import i18n from '../../src/shared/i18n';
import { Pick } from '../../src/features/dining/local/fields';
import { AccessHelp } from '../../src/features/access/AccessHelp';
import { assistance } from '../../src/shared/i18n/assistance';
import { assistanceV2 } from '../../src/shared/i18n/assistanceV2';
import {
  accessDocumentation,
  accessScenarios,
  scenarioExplanation,
} from '../../src/shared/access/help';
import { optionExplanation } from '../../src/shared/dining/help/optionHelp';
for (const locale of ['fr', 'en', 'ar'] as const) {
  it(
    'explains selected profiles and every option outside native options ' +
      locale,
    async () => {
      await i18n.changeLanguage(locale);
      const change = vi.fn();
      const options = [
        'owner',
        'service',
        'cleaner',
        'collector',
        'finance',
        'finance_reader',
        'kitchen',
        'service_cleaner',
        'canceller',
        'assistant',
        'customer',
        'outsider',
        'new_employee',
      ].map((value) => ({ value, label: i18n.t('d1.actor_' + value) }));
      const view = render(
        <Pick
          label="testProfile"
          name="actor"
          value="finance"
          set={change}
          options={options}
        />,
      );
      const select = screen.getByRole('combobox');
      expect(select).toHaveAccessibleDescription(
        expect.stringContaining(
          assistanceV2[locale]['options.profile_finance']!.split('. ')[0]!,
        ),
      );
      expect(within(select).getAllByRole('group')).toHaveLength(2);
      expect(select.querySelector('button,a,summary')).toBeNull();
      fireEvent.click(
        screen.getByText(assistanceV2[locale]['options.details']!),
      );
      expect(
        screen.getByText(assistanceV2[locale]['options.profile_outsider']!),
      ).toBeVisible();
      fireEvent.change(select, { target: { value: 'cleaner' } });
      expect(change).toHaveBeenCalledWith('cleaner');
      view.rerender(
        <Pick
          label="testProfile"
          name="actor"
          value="cleaner"
          set={change}
          options={options}
        />,
      );
      expect(select).toHaveAccessibleDescription(
        expect.stringContaining(
          assistanceV2[locale]['options.profile_cleaner']!.split('. ')[0]!,
        ),
      );
    },
  );
  it(
    'keeps access docs separate from a truthful unavailable conversation ' +
      locale,
    async () => {
      await i18n.changeLanguage(locale);
      const network = vi.spyOn(globalThis, 'fetch');
      render(<AccessHelp />);
      fireEvent.click(
        screen.getByRole('button', { name: assistance[locale]['help.open'] }),
      );
      expect(screen.getByRole('dialog')).toHaveAttribute(
        'dir',
        locale === 'ar' ? 'rtl' : 'ltr',
      );
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
      for (const section of accessDocumentation(locale))
        expect(screen.getByText(section.title)).toBeVisible();
      fireEvent.click(
        screen.getByRole('button', { name: assistance[locale]['help.close'] }),
      );
      fireEvent.click(
        screen.getByRole('button', {
          name: assistance[locale]['help.assistant'],
        }),
      );
      const input = screen.getByRole('textbox');
      fireEvent.change(input, {
        target: { value: 'A private unsent question' },
      });
      fireEvent.click(
        screen.getByRole('button', {
          name: assistanceV2[locale]['assist.send']!,
        }),
      );
      expect(screen.getByText('A private unsent question')).toBeVisible();
      expect(
        screen.getByText(assistanceV2[locale]['assist.notSent']!),
      ).toBeVisible();
      expect(network).not.toHaveBeenCalled();
      network.mockRestore();
      for (const key of Object.keys(accessScenarios))
        expect(scenarioExplanation(key, locale)).toBeTruthy();
      expect(scenarioExplanation('unknown', locale)).toBeNull();
    },
  );
}
it('documents actual capability differences and rejects unknown semantics', () => {
  expect(
    optionExplanation('capability', 'capability', 'orders.approve', 'fr'),
  ).toContain('confir');
  expect(
    optionExplanation('capability', 'capability', 'orders.complete', 'ar'),
  ).toContain('للزبون');
  expect(
    optionExplanation('capability', 'capability', 'unknown', 'fr'),
  ).toBeNull();
  expect(optionExplanation('kind', 'unknown', 'unknown', 'fr')).toBeNull();
  expect(
    optionExplanation('actor', 'actorKind', 'assistant', 'fr'),
  ).not.toBeNull();
});
it('covers all current static choices and scoped-record list relationships in each language', () => {
  const groups: readonly (readonly [string, string, readonly string[]])[] = [
    [
      'kind',
      'referenceKind',
      [
        'shape',
        'category',
        'zone',
        'location',
        'view',
        'proximity',
        'feature',
        'event',
      ],
    ],
    ['code', 'code', ['round', 'rectangular', 'square', 'oval']],
    [
      'initial',
      'initialPhysical',
      ['available', 'maintenance', 'out_of_service'],
    ],
    ['calendar_kind', 'calendarKind', ['weekly', 'dated']],
    ['weekday', 'weekday', ['0', '1', '2', '3', '4', '5', '6']],
    ['component', 'component', ['table', 'preparation', 'menu']],
    ['unit', 'unit', ['per_hour', 'flat', 'per_person', 'per_item']],
    ['actor', 'actorKind', ['human', 'assistant']],
    ['origin', 'origin', ['human', 'assistant', 'customer']],
    ['staff_state', 'staffState', ['active', 'suspended', 'revoked']],
    [
      'kind',
      'blockKind',
      ['closure', 'maintenance', 'preparation', 'cleaning'],
    ],
    ['target', 'blockTarget', ['branch', 'zone', 'table']],
    [
      'kind',
      'signalKind',
      [
        'customer_departure',
        'customer_cancellation_requested',
        'late_arrival',
        'expected_end_passed',
      ],
    ],
    [
      'document_kind',
      'documentKind',
      ['table', 'reservation', 'food_invoice', 'receipt'],
    ],
    ['document_action', 'documentAction', ['issue', 'rotate', 'disable']],
    [
      'visit_action',
      'documentAction',
      ['approve', 'prepare', 'ready', 'served'],
    ],
    ['mode', 'mode', ['cash', 'ccp', 'baridimob']],
    ...[
      'authorizedBranch',
      'table',
      'tableOptional',
      'zoneOptional',
      'categoryOptional',
      'event',
      'reservation',
      'reservationOptional',
      'proposal',
      'verifiedReceipt',
      'invoice',
      'occupation',
      'currency',
      'person',
      'staffFunction',
      'documentResource',
      'presenceSignal',
      'sourceOrders',
      'editOrCreate',
      'product',
    ].map((label) => [label, label, ['123']] as const),
    ['start_fold', 'fold', ['0', '1']],
  ];
  for (const locale of ['fr', 'en', 'ar'] as const)
    for (const [name, label, values] of groups)
      for (const value of values)
        expect(
          optionExplanation(name, label, value, locale),
          `${locale}/${name}/${label}/${value}`,
        ).toBeTruthy();
});
