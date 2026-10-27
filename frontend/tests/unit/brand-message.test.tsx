// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { act, render, screen, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it } from 'vitest';
import { Providers, createQueryClient } from '../../src/app/Providers';
import { routes } from '../../src/app/router';
import { disconnectedAdapter } from '../../src/shared/access/disconnected';
import i18n from '../../src/shared/i18n';
import previous from '../../brand-sources/archive/presentation-before-20261024/logo-manifest.json' with { type: 'json' };
import recent from '../../brand-sources/archive/presentation-before-20261025/logo-manifest.json' with { type: 'json' };

// These acceptance strings are the user's approved copy, independent of the catalogs.
const approved = {
  fr: [
    'Pour chaque activité, son propre MoulAI.',
    'Une intelligence qui travaille pour vous.',
    "Ce n'est pas un simple logiciel, mais un nouveau membre de votre équipe.",
    'Répond aux clients',
    'Prend les rendez-vous',
    'Suit les commandes',
    'Travaille 24h/24',
  ],
  en: [
    'For every business, its own MoulAI.',
    'Intelligence that works for you.',
    'Not just software, but a new member of your team.',
    'Responds to customers',
    'Books appointments',
    'Tracks orders',
    'Works around the clock',
  ],
  ar: [
    'لكل نشاط «مولاي» الخاص به',
    'ذكاء يعمل من أجلك',
    'ليس برنامجًا، بل عضو جديد في فريق العمل:',
    'يرد على العملاء',
    'يحجز المواعيد',
    'يتابع الطلبات',
    'يعمل على مدار الساعة',
  ],
} as const;

/** Mount the public route with the actual disconnected adapter and shared providers. */
async function mount(): Promise<void> {
  render(
    <Providers adapter={disconnectedAdapter} client={createQueryClient()}>
      <RouterProvider
        router={createMemoryRouter(routes, { initialEntries: ['/access'] })}
      />
    </Providers>,
  );
  await screen.findByRole('heading', { name: i18n.t('access.title') });
}

describe('approved frontend signature and planned Agent-as-a-Service copy', () => {
  for (const locale of ['fr', 'en', 'ar'] as const)
    for (const theme of ['light', 'dark'] as const)
      it(`${locale}/${theme} displays the exact localized message and honest integration boundary`, async () => {
        await i18n.changeLanguage(locale);
        window.moulaiTheme.choose(theme);
        await mount();
        expect(screen.getByText(approved[locale][0])).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        const section = screen.getByRole('region', {
          name: 'Agent-as-a-Service',
        });
        for (const text of approved[locale].slice(1))
          expect(within(section).getByText(text)).toBeInTheDocument();
        expect(section).toHaveAccessibleDescription(
          i18n.t('access.serviceVision'),
        );
        expect(section.querySelector('img')).toBeNull();
        expect(within(section).getAllByRole('listitem')).toHaveLength(4);
        for (const item of within(section).getAllByRole('listitem'))
          expect(item.querySelector('svg')).toHaveAttribute(
            'aria-hidden',
            'true',
          );
        expect(
          screen.getByRole('button', { name: i18n.t('access.signin') }),
        ).toBeDisabled();
        expect(
          screen.queryByRole('button', { name: i18n.t('review.open') }),
        ).toBeNull();
        expect(document.documentElement).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        const logo = screen.getByAltText('MoulAI™');
        expect(logo).toHaveAttribute(
          'src',
          `/brand/moulai-logo-${theme}01.png`,
        );
        expect(logo).toHaveAttribute('width', '2172');
        expect(logo).toHaveAttribute('height', '724');
        for (const other of ['fr', 'en', 'ar'] as const)
          if (other !== locale)
            for (const text of approved[other])
              expect(screen.queryByText(text)).not.toBeInTheDocument();
      });

  it('updates copy in place without replacing the access form or showing the old signature', async () => {
    await i18n.changeLanguage('fr');
    await mount();
    const login = screen.getByRole('button', { name: i18n.t('access.signin') });
    for (const locale of ['en', 'ar', 'fr'] as const) {
      await act(() => i18n.changeLanguage(locale));
      expect(
        screen.getByRole('button', { name: i18n.t('access.signin') }),
      ).toBe(login);
      expect(screen.getByText(approved[locale][0])).toBeVisible();
      expect(screen.getByText(approved[locale][1])).toBeVisible();
    }
    for (const text of [
      'L’espace de vos restaurants',
      'Your restaurant workspace',
      'مساحة مطاعمك',
    ])
      expect(screen.queryByText(text)).not.toBeInTheDocument();
  });

  it('retains previous presentation PNGs byte-for-byte outside the public asset directory', () => {
    for (const [directory, manifest] of [
      ['presentation-before-20261024', previous],
      ['presentation-before-20261025', recent],
    ] as const)
      for (const source of manifest.sources) {
        const bytes = readFileSync(
          `brand-sources/archive/${directory}/${source.file}`,
        );
        expect(createHash('sha256').update(bytes).digest('hex')).toBe(
          source.sha256,
        );
        expect(existsSync(`public/brand/${source.file}`)).toBe(false);
      }
  });
});
