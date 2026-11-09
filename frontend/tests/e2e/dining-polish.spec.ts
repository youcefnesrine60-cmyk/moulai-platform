// MoulAI™ — paired local read-only captures; business writes are forbidden.
import { test, expect } from '@playwright/test';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import AxeBuilder from '@axe-core/playwright';
import {
  serviceFr,
  serviceEn,
  serviceAr,
} from '../../src/shared/i18n/diningService';
import { d1Fr } from '../../src/shared/i18n/d1.fr';
import { d1En } from '../../src/shared/i18n/d1.en';
import { d1Ar } from '../../src/shared/i18n/d1.ar';

const phase = process.env.MOULAI_CAPTURE_PHASE ?? 'verify';
if (!['before', 'after', 'verify'].includes(phase))
  throw new Error('Invalid capture phase');
const validating = phase !== 'before';
const output = '../artifacts/dining-polish-20261105';
const root =
  '/local-d1/organizations/7000010/restaurants/7000200/branches/7000300/dining';
const dictionaries = {
  fr: { ...d1Fr, ...serviceFr },
  en: { ...d1En, ...serviceEn },
  ar: { ...d1Ar, ...serviceAr },
};
for (const locale of ['fr', 'en', 'ar'] as const)
  for (const theme of ['light', 'dark'] as const)
    for (const width of [1440, 390])
      test(`${phase} paired ${locale} ${theme} ${width}`, async ({ page }) => {
        await mkdir(output + '/' + phase, { recursive: true });
        await page.route('**/*', async (route) => {
          const request = route.request();
          expect(new URL(request.url()).origin).toBe('http://127.0.0.1:5574');
          if (
            request.method() !== 'GET' &&
            !request.url().endsWith('/local-d1/session')
          )
            throw new Error('Business mutation forbidden in visual comparison');
          await route.continue();
        });
        await page.setViewportSize({ width, height: 1000 });
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
        await expect(page.getByTestId('active-session')).toBeVisible();
        const workspace = await (
          await page.request.get(root + '/workspace')
        ).json();
        delete workspace.server_time;
        const hash = createHash('sha256')
          .update(JSON.stringify(workspace))
          .digest('hex');
        const key = `${locale}-${theme}-${width}`;
        if (phase === 'before')
          await writeFile(
            output + '/snapshot-' + key + '.json',
            JSON.stringify({ hash }),
          );
        else if (phase === 'after')
          expect(hash).toBe(
            JSON.parse(
              await readFile(output + '/snapshot-' + key + '.json', 'utf8'),
            ).hash,
          );
        const t = (key: string) =>
          dictionaries[locale][key as keyof typeof dictionaries.fr];
        for (const section of ['planning', 'staff', 'visits']) {
          await page
            .getByRole('button', {
              name: t('d1.section_' + section),
              exact: true,
            })
            .click();
          await page.screenshot({
            path: `${output}/${phase}/${section}-${key}.png`,
            fullPage: true,
          });
          if (validating) {
            expect(await page.locator('body').innerText()).not.toMatch(
              /\bd1\.[a-zA-Z_][\w.]*/,
            );
            expect(
              await page.evaluate(
                () => document.documentElement.scrollWidth <= innerWidth,
              ),
            ).toBe(true);
            expect(
              (await new AxeBuilder({ page }).analyze()).violations,
            ).toEqual([]);
            if (section !== 'planning') {
              const heading = page.getByRole('heading', {
                name: t('d1.section_' + section),
                exact: true,
              });
              expect(
                await heading.evaluate(
                  (el) => getComputedStyle(el.parentElement!).backdropFilter,
                ),
              ).not.toBe('none');
            }
          }
        }
      });

if (validating)
  test('opening uses device clock before paint; only two manual choices', async ({
    browser,
  }) => {
    for (const [instant, zone, expected] of [
      ['2026-11-05T06:59:59Z', 'UTC', 'dark'],
      ['2026-11-05T07:00:00Z', 'UTC', 'light'],
      ['2026-11-05T18:59:59Z', 'UTC', 'light'],
      ['2026-11-05T19:00:00Z', 'UTC', 'dark'],
      ['2026-11-05T22:00:00Z', 'Asia/Tokyo', 'light'],
    ] as const) {
      const context = await browser.newContext({
        timezoneId: zone,
        colorScheme: expected === 'light' ? 'dark' : 'light',
      });
      const page = await context.newPage();
      await page.clock.setFixedTime(new Date(instant));
      await page.addInitScript(() => {
        localStorage.setItem('moulai.locale', 'fr');
        localStorage.setItem('moulai.theme', 'dark');
        delete (window as unknown as { firstTheme?: string }).firstTheme;
        new MutationObserver(() => {
          const windowWithProof = window as unknown as { firstTheme?: string };
          if (
            !windowWithProof.firstTheme &&
            document.documentElement?.dataset.theme
          )
            windowWithProof.firstTheme = document.documentElement.dataset.theme;
        }).observe(document, {
          subtree: true,
          attributes: true,
          attributeFilter: ['data-theme'],
        });
      });
      await page.goto('/access');
      await expect(page.locator('html')).toHaveAttribute(
        'data-theme',
        expected,
      );
      expect(
        await page.evaluate(
          () => (window as unknown as { firstTheme?: string }).firstTheme,
        ),
      ).toBe(expected);
      await page
        .getByRole('combobox', { name: 'Apparence', exact: true })
        .click();
      await expect(page.getByRole('option')).toHaveCount(2);
      await page
        .getByRole('option', {
          name: expected === 'light' ? 'Sombre' : 'Clair',
          exact: true,
        })
        .click();
      await expect(page.locator('html')).toHaveAttribute(
        'data-theme',
        expected === 'light' ? 'dark' : 'light',
      );
      await page.reload();
      await expect(page.locator('html')).toHaveAttribute(
        'data-theme',
        expected,
      );
      await context.close();
    }
  });

test('table customer print exports', async ({ page }) => {
  await mkdir(output + '/' + phase, { recursive: true });
  expect(
    (
      await page.request.post('/local-d1/session', {
        data: { actor: 'owner' },
        headers: { origin: 'http://127.0.0.1:5574' },
      })
    ).status(),
  ).toBe(200);
  const state = await (await page.request.get(root + '/workspace')).json();
  const table = state.tables.find(
    (table: { code: string }) => table.code === 'T1',
  );
  const link = state.public_links.find(
    (link: { kind: string; active: boolean; table_id: number }) =>
      link.kind === 'table' && link.active && link.table_id === table.id,
  );
  const identity = {
    code: table.code,
    floor: table.floor_label,
    room: table.room_label,
    zone: state.references.find(
      (ref: { id: number }) => ref.id === table.zone_id,
    ),
    location: state.references.find(
      (ref: { id: number }) => ref.id === table.location_id,
    ),
  };
  if (phase === 'before')
    await writeFile(output + '/print-identity.json', JSON.stringify(identity));
  else if (phase === 'after') {
    const prior = JSON.parse(
      await readFile(output + '/print-identity.json', 'utf8'),
    );
    // The new disposable run retains the same displayed identification; creation timestamps differ.
    delete identity.zone.created_at;
    delete identity.location.created_at;
    delete prior.zone.created_at;
    delete prior.location.created_at;
    expect(identity).toEqual(prior);
  }
  const manifest = [];
  for (const locale of ['fr', 'en', 'ar']) {
    await page.setViewportSize({ width: 560, height: 794 });
    await page.goto(
      root + '/public-links/' + link.id + '/print?locale=' + locale,
    );
    await expect(page.locator('svg')).toBeVisible();
    await expect(page.locator('html')).toHaveAttribute(
      'dir',
      locale === 'ar' ? 'rtl' : 'ltr',
    );
    if (validating) {
      await expect(page.locator('img')).toHaveAttribute(
        'src',
        /^data:image\/png;base64,/,
      );
      await expect(page.locator('body')).not.toContainText('SHA-256');
      await expect(page.locator('body')).not.toContainText(link.reference);
      await expect(page.locator('.instruction')).toBeVisible();
    }
    await page
      .locator('svg')
      .screenshot({ path: `${output}/${phase}/qr-${locale}.png` });
    await page.emulateMedia({ media: 'print' });
    const box = (await page.locator('svg').boundingBox())!;
    const url = await page.locator('a').getAttribute('href');
    const pageMargin = validating ? (10 * 96) / 25.4 : 0;
    await page.pdf({
      path: `${output}/${phase}/table-${locale}.pdf`,
      width: '560px',
      height: '794px',
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
      printBackground: true,
      preferCSSPageSize: false,
    });
    await page.screenshot({
      path: `${output}/${phase}/print-${locale}.png`,
      fullPage: true,
    });
    manifest.push({
      image: `qr-${locale}.png`,
      expected_url: url,
      locale,
      source: 'actual local print route screenshot',
    });
    manifest.push({
      image: `pdf-${locale}-1.png`,
      expected_url: url,
      locale,
      crop: [box.x, box.y + pageMargin, box.width, box.height],
      page_margin_css_px: pageMargin,
      source: 'actual route PDF raster 96 DPI',
    });
    await page.emulateMedia({ media: 'screen' });
  }
  await writeFile(
    `${output}/${phase}/qr-image-manifest.json`,
    JSON.stringify(manifest, null, 2),
  );
});

if (validating)
  test('glass affects backgrounds only and technical reference copies explicitly', async ({
    page,
    context,
  }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    expect(
      (
        await page.request.post('/local-d1/session', {
          data: { actor: 'owner' },
          headers: { origin: 'http://127.0.0.1:5574' },
        })
      ).status(),
    ).toBe(200);
    await page.addInitScript(() => localStorage.setItem('moulai.locale', 'fr'));
    await page.goto('/dining-local?branch=7000300');
    await expect(page.getByTestId('active-session')).toBeVisible();
    for (const theme of ['light', 'dark'] as const) {
      await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
      const panels = page
        .locator('main > header, main > section')
        .filter({ has: page.locator('h1, img') });
      expect(await panels.count()).toBeGreaterThanOrEqual(2);
      for (const panel of await panels.all()) {
        const style = await panel.evaluate((el) => ({
          background: getComputedStyle(el).backgroundColor,
          opacity: getComputedStyle(el).opacity,
          blur: getComputedStyle(el).backdropFilter,
        }));
        const alpha = Number(
          style.background.match(/\/\s*([\d.]+)/)?.[1] ??
            style.background.match(
              /rgba\([^,]+,[^,]+,[^,]+,\s*([\d.]+)/,
            )?.[1] ??
            1,
        );
        expect(alpha).toBeLessThanOrEqual(0.4);
        expect(style.opacity).toBe('1');
        expect(style.blur).not.toBe('none');
      }
      await expect(page.locator('main img').first()).toHaveCSS('opacity', '1');
    }
    await page
      .getByRole('button', {
        name: serviceFr['d1.section_visits'],
        exact: true,
      })
      .click();
    const article = page
      .locator('article')
      .filter({ has: page.getByText('T1', { exact: false }) })
      .first();
    const details = article.locator('details').first();
    await expect(details).not.toHaveAttribute('open', '');
    await details.locator('summary').click();
    await details
      .getByRole('button', { name: d1Fr['d1.copyReference'], exact: true })
      .click();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toMatch(
      /^DOC-/,
    );
  });
