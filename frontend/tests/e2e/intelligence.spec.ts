// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { expect, test, type Page, type TestInfo } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { fr } from '../../src/shared/i18n/fr';
import { en } from '../../src/shared/i18n/en';
import { ar } from '../../src/shared/i18n/ar';
import { intelligenceFr } from '../../src/shared/i18n/intelligence.fr';
import { intelligenceEn } from '../../src/shared/i18n/intelligence.en';
import { intelligenceAr } from '../../src/shared/i18n/intelligence.ar';
import { businessFr } from '../../src/shared/i18n/business.fr';
import { businessEn } from '../../src/shared/i18n/business.en';
import { businessAr } from '../../src/shared/i18n/business.ar';
import type { Locale, ReviewProfile } from '../../src/shared/access/contracts';
import { evidenceDirectory } from './polish-checks';

const catalogs = {
  fr: { ...fr, ...businessFr, ...intelligenceFr },
  en: { ...en, ...businessEn, ...intelligenceEn },
  ar: { ...ar, ...businessAr, ...intelligenceAr },
};
type CopyKey = keyof typeof catalogs.fr;
const base = '/workspace/organizations/9101/restaurants/9201';

/** Use the translated UI labels; merchant-authored fixture values remain verbatim. */
function copy(locale: Locale, key: CopyKey): string {
  return catalogs[locale][key];
}

/** Navigate only browser routes, without any HTTP API or identity bypass. */
async function navigate(page: Page, path: string): Promise<void> {
  await page.evaluate((destination) => {
    history.pushState(null, '', destination);
    dispatchEvent(new PopStateEvent('popstate'));
  }, path);
}

/** Enter the existing explicit synthetic review flow with the requested unchanged profile. */
async function enter(
  page: Page,
  locale: Locale,
  profile: ReviewProfile = 'owner',
): Promise<void> {
  await page.goto('/access');
  await expect(
    page.getByRole('heading', { name: copy(locale, 'access.title') }),
  ).toBeVisible();
  if (profile !== 'owner') {
    await page
      .getByRole('combobox', { name: copy(locale, 'review.profile') })
      .click();
    await page
      .getByRole('option', {
        name: copy(locale, `profile.${profile}`),
        exact: true,
      })
      .click();
  }
  await page.getByRole('button', { name: copy(locale, 'review.open') }).click();
}

/** Measure rendered overflow and WCAG checks, then retain an unmodified real browser capture. */
async function capture(
  page: Page,
  label: string,
  info: TestInfo,
): Promise<void> {
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const scan = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(scan.violations).toEqual([]);
  await info.attach(label, {
    body: JSON.stringify({ axeViolations: 0, overflow: false }),
    contentType: 'application/json',
  });
  await page.screenshot({
    path: `${evidenceDirectory(info)}/${label}.png`,
    fullPage: true,
  });
}

test.beforeEach(async ({ page }) => {
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    expect(url.hostname).toBe('127.0.0.1');
    expect(['5273', '4273']).toContain(url.port);
    expect(['GET', 'HEAD']).toContain(request.method());
    expect(url.pathname).not.toMatch(/^\/api(?:\/|$)/);
    await route.continue();
  });
  page.on('pageerror', (error) => {
    throw error;
  });
});

for (const width of [1440, 390])
  for (const locale of ['fr', 'en', 'ar'] as const)
    for (const theme of ['light', 'dark'] as const)
      test(`${width}px ${locale}/${theme}: six scoped intelligence views, filters and timeline`, async ({
        page,
      }, info) => {
        test.setTimeout(150000);
        await page.setViewportSize({
          width,
          height: width === 390 ? 844 : 1000,
        });
        await page.addInitScript(
          ({ locale, theme }) => {
            localStorage.setItem('moulai.locale', locale);
            localStorage.setItem('moulai.theme', theme);
          },
          { locale, theme },
        );
        await enter(page, locale);
        await navigate(page, `${base}/agents`);
        await expect(
          page.getByRole('heading', {
            name: copy(locale, 'nav.agents'),
            level: 1,
          }),
        ).toBeVisible();
        await expect(page.locator('html')).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        await expect(page.locator('[data-gateway]')).toHaveAttribute(
          'data-gateway',
          theme,
        );
        await expect(page.locator('header img')).toHaveAttribute(
          'src',
          `/brand/moulai-logo-${theme}01.png`,
        );
        const prefix = `${width}-${locale}-${theme}`;
        await capture(page, `${prefix}-agents`, info);
        const search = page.getByRole('searchbox', {
          name: copy(locale, 'intelligence.search'),
        });
        await search.fill('Service');
        await expect(
          page.getByRole('heading', { name: 'Accueil · IA-REV-9201' }),
        ).toHaveCount(0);
        await expect(
          page.getByRole('heading', { name: 'Service · IA-REV-9201' }),
        ).toBeVisible();
        await search.fill('');
        await page
          .getByRole('link', {
            name: `${copy(locale, 'intelligence.openAgent')} · Accueil · IA-REV-9201`,
          })
          .click();
        await expect(
          page.getByRole('heading', {
            name: 'Accueil · IA-REV-9201',
            level: 1,
          }),
        ).toBeVisible();
        await capture(page, `${prefix}-agent`, info);
        const tabs = page.getByRole('navigation', {
          name: copy(locale, 'restaurant.context'),
        });
        await tabs
          .getByRole('link', {
            name: copy(locale, 'nav.channels'),
            exact: true,
          })
          .click();
        await expect(
          page.getByRole('heading', {
            name: copy(locale, 'nav.channels'),
            level: 1,
          }),
        ).toBeVisible();
        await page
          .getByRole('combobox', {
            name: copy(locale, 'intelligence.channelType'),
            exact: true,
          })
          .selectOption('telegram');
        await expect(
          page.getByRole('heading', { name: 'Canal web de revue 9201' }),
        ).toHaveCount(0);
        await expect(
          page.getByRole('heading', { name: 'Canal Telegram de revue 9201' }),
        ).toBeVisible();
        await page
          .getByRole('combobox', {
            name: copy(locale, 'intelligence.channelType'),
            exact: true,
          })
          .selectOption('all');
        await capture(page, `${prefix}-channels`, info);
        await page
          .getByRole('link', {
            name: `${copy(locale, 'intelligence.openChannel')} · Canal web de revue 9201`,
          })
          .click();
        await expect(
          page.getByRole('heading', {
            name: 'Canal web de revue 9201',
            level: 1,
          }),
        ).toBeVisible();
        await expect(
          page.getByText(copy(locale, 'intelligence.channelBoundary'), {
            exact: true,
          }),
        ).toBeVisible();
        await capture(page, `${prefix}-channel`, info);
        await tabs
          .getByRole('link', {
            name: copy(locale, 'nav.conversations'),
            exact: true,
          })
          .click();
        await expect(
          page.getByRole('heading', {
            name: copy(locale, 'nav.conversations'),
            level: 1,
          }),
        ).toBeVisible();
        const status = page.getByRole('combobox', {
          name: copy(locale, 'intelligence.status'),
          exact: true,
        });
        await status.selectOption('closed');
        await expect(
          page.getByRole('heading', { name: 'Visiteur de revue 2' }),
        ).toBeVisible();
        await expect(
          page.getByRole('heading', { name: 'Visiteur de revue 1' }),
        ).toHaveCount(0);
        await status.selectOption('all');
        await expect(
          page.getByRole('heading', { name: 'Visiteur de revue 1' }),
        ).toBeVisible();
        await page
          .getByRole('button', {
            name: copy(locale, 'intelligence.next'),
            exact: true,
          })
          .click();
        await expect(
          page.getByRole('heading', { name: 'Visiteur de revue 6' }),
        ).toBeVisible();
        await page
          .getByRole('button', {
            name: copy(locale, 'intelligence.previous'),
            exact: true,
          })
          .click();
        await expect(
          page.getByRole('heading', { name: 'Visiteur de revue 1' }),
        ).toBeVisible();
        await capture(page, `${prefix}-conversations`, info);
        await page
          .getByRole('link', {
            name: `${copy(locale, 'intelligence.openConversation')} · Visiteur de revue 1`,
          })
          .click();
        const timeline = page.getByRole('list', {
          name: copy(locale, 'intelligence.messages'),
        });
        await expect(timeline.getByRole('listitem')).toHaveCount(5);
        await expect(timeline).toContainText(
          '<script>contenu de test affiché comme texte</script>',
        );
        await expect(
          timeline.locator('script,img,audio,video,iframe'),
        ).toHaveCount(0);
        const times = await timeline
          .locator('time')
          .evaluateAll((nodes) =>
            nodes.map((node) => node.getAttribute('datetime')!),
          );
        expect(times).toEqual([...times].sort());
        await capture(page, `${prefix}-conversation`, info);
        await page
          .getByRole('button', {
            name: copy(locale, 'intelligence.next'),
            exact: true,
          })
          .click();
        await expect(timeline).toContainText(
          copy(locale, 'intelligence.mediaBoundary'),
        );
        await expect(timeline.locator('img,audio,video,a')).toHaveCount(0);
        await navigate(page, `${base}/conversations/920122`);
        await expect(
          page.getByText(copy(locale, 'intelligence.emptyMessages'), {
            exact: true,
          }),
        ).toBeVisible();
      });

test('Owner sees each explicit company separately and foreign child identifiers are refused', async ({
  page,
}) => {
  await enter(page, 'fr');
  for (const suffix of [
    'agents/920301',
    'channels/920311',
    'conversations/920321',
  ]) {
    await navigate(page, `${base}/${suffix}`);
    await expect(
      page.getByRole('heading', { name: copy('fr', 'state.notFound.title') }),
    ).toBeVisible();
    await expect(
      page.getByText(/IA-REV-9203|synthetic-visitor-9203/),
    ).toHaveCount(0);
  }
  await navigate(page, '/workspace/organizations/9102/restaurants/9203/agents');
  await expect(
    page.getByRole('heading', { name: 'Accueil · IA-REV-9203' }),
  ).toBeVisible();
  await expect(page.getByText(/IA-REV-9201/)).toHaveCount(0);
  await navigate(page, '/workspace/organizations/9101/restaurants/9202/agents');
  await expect(
    page.getByRole('heading', { name: copy('fr', 'nav.agents'), level: 1 }),
  ).toBeVisible();
  await expect(page.getByText(/IA-REV-9203|IA-REV-9201/)).toHaveCount(0);
});

for (const profile of ['manager', 'employee', 'admin'] as const)
  test(`${profile}: existing resource grants and tenant/platform separation`, async ({
    page,
  }) => {
    await enter(page, 'fr', profile);
    if (profile === 'manager') {
      await navigate(page, `${base}/agents/920101`);
      await expect(
        page.getByRole('button', {
          name: copy('fr', 'intelligence.configure'),
        }),
      ).toBeVisible();
      await navigate(
        page,
        '/workspace/organizations/9101/restaurants/9202/agents',
      );
      await expect(
        page.getByRole('heading', { name: copy('fr', 'state.notFound.title') }),
      ).toBeVisible();
      await navigate(
        page,
        '/workspace/organizations/9102/restaurants/9203/conversations',
      );
    } else {
      await navigate(
        page,
        `/workspace/organizations/9101/restaurants/${profile === 'employee' ? 9202 : 9201}/agents`,
      );
    }
    await expect(
      page.getByRole('heading', {
        name: copy(
          'fr',
          profile === 'manager'
            ? 'state.notFound.title'
            : 'state.noAccess.title',
        ),
      }),
    ).toBeVisible();
    await expect(
      page.getByText(/IA-REV-9201|IA-REV-9203|synthetic-visitor/),
    ).toHaveCount(0);
  });

test('Keyboard form, validation, confirmation, locale/System preference and scope purge', async ({
  page,
}, info) => {
  test.setTimeout(90000);
  await page.emulateMedia({ colorScheme: 'light' });
  await enter(page, 'fr');
  await navigate(page, `${base}/agents/920101`);
  const configure = page.getByRole('button', {
    name: copy('fr', 'intelligence.configure'),
  });
  await configure.focus();
  await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog');
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
  await expect(configure).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(dialog).toBeVisible();
  const name = dialog.getByRole('textbox', {
    name: copy('fr', 'intelligence.name'),
    exact: true,
  });
  await name.fill('');
  await dialog
    .getByRole('button', {
      name: copy('fr', 'intelligence.preview'),
      exact: true,
    })
    .click();
  await expect(name).toHaveAttribute('aria-invalid', 'true');
  await expect(name).toBeFocused();
  await name.fill('Agent de revue — مسودة');
  await dialog
    .getByRole('combobox', { name: copy('fr', 'preferences.language') })
    .click();
  await page.getByRole('option', { name: 'العربية — AR', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(
    dialog.getByRole('textbox', {
      name: copy('ar', 'intelligence.name'),
      exact: true,
    }),
  ).toHaveValue('Agent de revue — مسودة');
  await dialog
    .getByRole('combobox', { name: copy('ar', 'preferences.theme') })
    .click();
  await page
    .getByRole('option', { name: copy('ar', 'theme.system'), exact: true })
    .click();
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page.locator('[data-gateway]')).toHaveAttribute(
    'data-gateway',
    'dark',
  );
  await capture(page, '1440-ar-dark-agent-form', info);
  await dialog
    .getByRole('button', {
      name: copy('ar', 'intelligence.preview'),
      exact: true,
    })
    .click();
  await expect(
    dialog.getByRole('heading', {
      name: copy('ar', 'intelligence.confirmTitle'),
    }),
  ).toBeVisible();
  await capture(page, '1440-ar-dark-agent-confirmation', info);
  await dialog
    .getByRole('button', {
      name: copy('ar', 'intelligence.applyReview'),
      exact: true,
    })
    .click();
  await expect(
    page.getByRole('heading', { name: 'Agent de revue — مسودة', level: 1 }),
  ).toBeVisible();
  await navigate(page, `${base}/catalogue`);
  await expect(
    page.getByRole('heading', {
      name: copy('ar', 'business.catalogue'),
      level: 1,
    }),
  ).toBeVisible();
  await navigate(page, `${base}/agents/920101`);
  await expect(
    page.getByRole('heading', { name: 'Accueil · IA-REV-9201', level: 1 }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Agent de revue — مسودة' }),
  ).toHaveCount(0);
});

test('Normal build is disconnected and does not admit the intelligence review', async ({
  page,
}) => {
  await page.goto(`http://127.0.0.1:4273${base}/agents`);
  await expect(
    page.getByRole('heading', { name: copy('fr', 'access.title') }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: copy('fr', 'access.signin') }),
  ).toBeDisabled();
  await expect(
    page.getByRole('button', { name: copy('fr', 'review.open') }),
  ).toHaveCount(0);
  await expect(page.getByText(/IA-REV-|synthetic-visitor-/)).toHaveCount(0);
});
