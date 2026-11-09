// MoulAI™ — actual local reads, no business writes, no provider/microphone activation.
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { assistance as originalAssistance } from '../../src/shared/i18n/assistance';
import { assistanceV2 } from '../../src/shared/i18n/assistanceV2';
const assistance = {
  fr: { ...originalAssistance.fr, ...assistanceV2.fr },
  en: { ...originalAssistance.en, ...assistanceV2.en },
  ar: { ...originalAssistance.ar, ...assistanceV2.ar },
};
import { d1Fr } from '../../src/shared/i18n/d1.fr';
import { d1En } from '../../src/shared/i18n/d1.en';
import { d1Ar } from '../../src/shared/i18n/d1.ar';
import { procedure } from '../../src/shared/dining/help/documentation';
const output = fileURLToPath(
  new URL('../../../artifacts/assistance-options-20261107', import.meta.url),
);
const root =
  '/local-d1/organizations/7000010/restaurants/7000200/branches/7000300/dining';
const resources = { fr: d1Fr, en: d1En, ar: d1Ar };
for (const locale of ['fr', 'ar'] as const)
  test(`profile choices ${locale}: selected meaning, all roles and no session change`, async ({
    page,
  }) => {
    await page.request.post('/local-d1/session', {
      data: { actor: 'owner' },
      headers: { origin: 'http://127.0.0.1:5574' },
    });
    await page.addInitScript(
      (locale) => localStorage.setItem('moulai.locale', locale),
      locale,
    );
    await page.setViewportSize({
      width: locale === 'ar' ? 390 : 1440,
      height: 1100,
    });
    await page.goto('/dining-local?branch=7000300');
    await expect(page.getByTestId('operational-board')).toBeVisible();
    await page.evaluate(() => window.moulaiTheme.choose('light'));
    const writes: string[] = [];
    await page.route('**/*', async (route) => {
      expect(new URL(route.request().url()).origin).toBe(
        'http://127.0.0.1:5574',
      );
      if (route.request().method() !== 'GET')
        writes.push(route.request().url());
      await route.continue();
    });
    const settings = page.getByTestId('session-settings');
    await settings.locator(':scope > summary').click();
    const profile = settings.locator('select[name="actor"]');
    await profile.selectOption('finance');
    const group = profile.locator('..');
    await expect(group).toContainText(
      assistanceV2[locale]['options.profile_finance'].split('. ')[0]!,
    );
    await group.locator('summary').click();
    for (const choice of [
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
    ])
      await expect(
        group.locator('dd').filter({
          hasText:
            assistanceV2[locale][
              ('options.profile_' + choice) as keyof typeof assistanceV2.fr
            ],
        }),
      ).toHaveCount(1);
    await page.screenshot({
      path: `${output}/captures/profile-details-${locale}.png`,
      fullPage: true,
    });
    await expect(
      page.locator('select[name="actor"] option:checked'),
    ).toHaveText(resources[locale]['d1.actor_finance']);
    expect(
      (await (await page.request.get('/local-d1/session')).json()).actor,
    ).toBe('owner');
    expect(writes).toEqual([]);
  });
for (const locale of ['fr', 'en', 'ar'] as const)
  for (const theme of ['light', 'dark'] as const)
    for (const width of [1440, 390])
      test(`${locale}/${theme}/${width}: session, header, element help and natural guide`, async ({
        page,
      }) => {
        await mkdir(output + '/captures', { recursive: true });
        const errors: string[] = [];
        page.on('pageerror', (error) => errors.push(error.message));
        await page.route('**/*', async (route) => {
          expect(new URL(route.request().url()).origin).toBe(
            'http://127.0.0.1:5574',
          );
          expect(route.request().method()).toBe('GET');
          await route.continue();
        });
        await page.setViewportSize({ width, height: 1100 });
        await page.addInitScript(
          (locale) => localStorage.setItem('moulai.locale', locale),
          locale,
        );
        expect(
          (
            await page.request.post('/local-d1/session', {
              data: { actor: 'owner' },
              headers: { origin: 'http://127.0.0.1:5574' },
            })
          ).status(),
        ).toBe(200);
        await page.goto('/dining-local?branch=7000300');
        await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
        await expect(page.getByTestId('operational-board')).toBeVisible();
        const hash = async () => {
          const data = await (
            await page.request.get(root + '/workspace')
          ).json();
          delete data.server_time;
          return createHash('sha256')
            .update(JSON.stringify(data))
            .digest('hex');
        };
        const before = await hash();
        const a = assistance[locale],
          t = (key: string) =>
            resources[locale][('d1.' + key) as keyof typeof d1Fr];
        const settings = page.getByTestId('session-settings');
        await settings.locator(':scope > summary').click();
        const select = settings.locator('select[name="actor"]'),
          open = page.getByTestId('session-open'),
          close = page.getByTestId('session-close');
        const rectangles = await Promise.all(
          [select, open, close].map((node) => node.boundingBox()),
        );
        const [s, o, c] = rectangles;
        if (width === 1440) {
          expect(Math.abs(s!.y - o!.y)).toBeLessThan(2);
          expect(Math.abs(o!.y - c!.y)).toBeLessThan(2);
          expect(Math.abs(s!.height - o!.height)).toBeLessThan(2);
          expect(Math.abs(o!.height - c!.height)).toBeLessThan(2);
        } else {
          expect(o!.y).toBeGreaterThan(s!.y + s!.height);
          expect(c!.y).toBeGreaterThan(o!.y + o!.height);
        }
        const header = page.locator('main > header'),
          controls = page.getByTestId('header-controls'),
          dock = controls.locator('[data-assistance-dock]'),
          lang = controls.getByRole('combobox').first();
        const hb = (await header.boundingBox())!,
          db = (await dock.boundingBox())!,
          lb = (await lang.boundingBox())!,
          brand = (await header.locator('img').boundingBox())!;
        expect(db.y).toBeGreaterThanOrEqual(hb.y);
        expect(db.y + db.height).toBeLessThanOrEqual(lb.y + 1);
        expect(
          await dock.evaluate((node) => getComputedStyle(node).position),
        ).toBe('static');
        expect(brand.width / brand.height).toBeCloseTo(3, 1);
        expect(
          await header
            .locator('img')
            .evaluate((node) => getComputedStyle(node).filter),
        ).toBe('none');
        expect(
          brand.x + brand.width <= db.x ||
            db.x + db.width <= brand.x ||
            brand.y + brand.height <= db.y ||
            db.y + db.height <= brand.y,
        ).toBe(true);
        if (width === 1440) {
          const title = page.locator('aside nav > p');
          expect(
            await title
              .locator('bdi')
              .evaluate((n) => getComputedStyle(n).fontSize),
          ).toBe('24px');
          expect(
            await title
              .locator('bdi')
              .evaluate((n) => getComputedStyle(n).fontWeight),
          ).toBe('700');
          expect(
            await title
              .locator('span')
              .evaluate((n) => getComputedStyle(n).fontSize),
          ).toBe('14px');
        }
        await page.evaluate(() => scrollTo(0, 0));
        await page.screenshot({
          path: `${output}/captures/session-${locale}-${theme}-${width}.png`,
        });
        await page
          .getByRole('button', {
            name: t('section_configuration'),
            exact: true,
          })
          .click();
        const form = page.locator('form[data-operation="reference"]');
        await form.locator('..').locator(':scope > summary').click();
        const input = form.locator('[name="code"]');
        await input.fill('DRAFT-NEVER-SAVED');
        const saveHelp = form.getByRole('button', {
          name: a['element.explainNamed'].replace('{{name}}', t('save')),
          exact: true,
        });
        await saveHelp.focus();
        await page.keyboard.press('Enter');
        const dialog = page.getByRole('dialog'),
          box = page.getByTestId('element-explanation');
        await expect(box).toContainText(a['element.kind_button']);
        await expect(box).toContainText(a['element.rule.reference']);
        await expect(box).not.toContainText(a['help.optional']);
        await expect(box).not.toContainText(a['help.required']);
        await expect(dialog).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        await page.screenshot({
          path: `${output}/captures/button-help-${locale}-${theme}-${width}.png`,
        });
        expect(
          (
            await new AxeBuilder({ page })
              .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
              .analyze()
          ).violations,
        ).toEqual([]);
        await page.keyboard.press('Escape');
        await expect(input).toHaveValue('DRAFT-NEVER-SAVED');
        await expect(saveHelp).toBeFocused();
        await input.focus();
        await dock
          .getByRole('button', { name: a['help.open'], exact: true })
          .click();
        await dialog
          .getByRole('button', { name: a['help.fieldHelp'], exact: true })
          .click();
        await expect(box).toContainText(a['element.kind_button']); // explicit selection stays the save button, never inferred from new input focus
        await dialog
          .getByRole('combobox', { name: a['help.topic'], exact: true })
          .selectOption('orders');
        await expect(dialog.locator('article')).toContainText(
          procedure('orders').copy[locale].title,
        );
        expect(await dialog.locator('article').innerText()).not.toMatch(
          /orders\.(approve|prepare|complete)|finance\.read|invoices\./,
        );
        await page.screenshot({
          path: `${output}/captures/orders-guide-${locale}-${theme}-${width}.png`,
        });
        await page
          .getByRole('button', { name: a['help.close'], exact: true })
          .click();
        await dock
          .getByRole('button', { name: a['help.assistant'], exact: true })
          .click();
        await expect(page.getByTestId('assistant-conversation')).toContainText(
          a['assist.unavailable']!,
        );
        const question = dialog.getByRole('textbox');
        await question.fill('Why can I not seat this customer?');
        await dialog
          .getByRole('button', { name: a['assist.send']!, exact: true })
          .click();
        await expect(
          dialog.getByText('Why can I not seat this customer?', {
            exact: true,
          }),
        ).toBeVisible();
        await expect(
          dialog.getByRole('button', { name: a['voice.listen'], exact: true }),
        ).toBeDisabled();
        await expect(
          dialog.getByRole('button', { name: a['voice.mic'], exact: true }),
        ).toBeDisabled();
        await question.fill('DRAFT-QUESTION');
        await page.screenshot({
          path: `${output}/captures/pending-${locale}-${theme}-${width}.png`,
        });
        await page.keyboard.press('Escape');
        await expect(input).toHaveValue('DRAFT-NEVER-SAVED');
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        expect(await hash()).toBe(before);
        expect(errors).toEqual([]);
        await writeFile(
          `${output}/evidence-${locale}-${theme}-${width}.json`,
          JSON.stringify(
            {
              locale,
              theme,
              width,
              sessionGeometry: rectangles,
              unchangedJournalAndWorkspace: true,
              noBusinessWrite: true,
              noExternalRequest: true,
              noProviderCall: true,
              draftPreserved: true,
              axeViolations: 0,
            },
            null,
            2,
          ),
        );
      });
test('explicit unknown and fixed element explanations never submit business data', async ({
  page,
}) => {
  await page.request.post('/local-d1/session', {
    data: { actor: 'owner' },
    headers: { origin: 'http://127.0.0.1:5574' },
  });
  await page.goto('/dining-local?branch=7000300');
  await expect(page.getByTestId('operational-board')).toBeVisible();
  const writes: string[] = [];
  await page.route('**/local-d1/**', async (route) => {
    if (route.request().method() !== 'GET') writes.push(route.request().url());
    await route.continue();
  });
  await page.evaluate(() => localStorage.setItem('moulai.locale', 'fr'));
  await page.reload();
  await expect(page.getByTestId('operational-board')).toBeVisible();
  await page
    .getByRole('button', {
      name: d1Fr['d1.section_configuration'],
      exact: true,
    })
    .click();
  const reference = page.locator('form[data-operation="reference"]');
  await reference.locator('..').locator(':scope > summary').click();
  await reference.locator('[name="reference_edit"]').selectOption({ index: 1 });
  const code = reference.locator('[name="code"]');
  await expect(code).toBeDisabled();
  await reference
    .getByRole('button', {
      name: assistance.fr['element.explainNamed'].replace(
        '{{name}}',
        d1Fr['d1.code'],
      ),
      exact: true,
    })
    .click();
  await expect(page.getByTestId('element-explanation')).toContainText(
    assistance.fr['element.fixedReference'],
  );
  await page.keyboard.press('Escape');
  const table = page.locator('form[data-operation="table"]');
  await table.locator('..').locator(':scope > summary').click();
  await table
    .getByRole('button', {
      name: assistance.fr['element.explainNamed'].replace(
        '{{name}}',
        d1Fr['d1.description'],
      ),
      exact: true,
    })
    .click();
  await expect(page.getByTestId('element-explanation')).toContainText(
    assistance.fr['element.unavailable'],
  );
  expect(writes).toEqual([]);
});

for (const [locale, theme, width] of [
  ['fr', 'light', 1440],
  ['ar', 'dark', 390],
] as const)
  test('surface accessibility ' + locale + ' ' + theme, async ({ page }) => {
    await page.setViewportSize({ width, height: 1100 });
    await page.addInitScript(
      (locale) => localStorage.setItem('moulai.locale', locale),
      locale,
    );
    await page.request.post('/local-d1/session', {
      data: { actor: 'owner' },
      headers: { origin: 'http://127.0.0.1:5574' },
    });
    await page.route('**/*', async (route) => {
      expect(new URL(route.request().url()).origin).toBe(
        'http://127.0.0.1:5574',
      );
      expect(route.request().method()).toBe('GET');
      await route.continue();
    });
    await page.goto('/dining-local?branch=7000300');
    await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
    await expect(page.getByTestId('operational-board')).toBeVisible();
    const settings = page.getByTestId('session-settings');
    await settings.locator(':scope > summary').click();
    const a = assistance[locale];
    const help = page
      .locator('[data-assistance-dock]')
      .getByRole('button', { name: a['help.open'], exact: true });
    await help.hover();
    await settings
      .getByRole('button', {
        name: a['element.explainNamed'].replace(
          '{{name}}',
          resources[locale]['d1.testProfile'],
        ),
        exact: true,
      })
      .focus();
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
          .analyze()
      ).violations,
    ).toEqual([]);
    await page.screenshot({
      path: `${output}/captures/surface-focus-${locale}-${theme}-${width}.png`,
    });
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('element-explanation')).toContainText(
      a['element.rule.profile'],
    );
    await page.keyboard.press('Escape');
    await expect(settings.locator('select[name="actor"]')).toHaveValue('owner');
  });
