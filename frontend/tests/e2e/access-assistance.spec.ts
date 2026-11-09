// MoulAI™ — real browser surfaces, synthetic access states, no provider or business writes.
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { assistance } from '../../src/shared/i18n/assistance';
import { assistanceV2 } from '../../src/shared/i18n/assistanceV2';
import { scenarioExplanation } from '../../src/shared/access/help';
import { fr } from '../../src/shared/i18n/fr';
import { en } from '../../src/shared/i18n/en';
import { ar } from '../../src/shared/i18n/ar';
const output = fileURLToPath(
  new URL('../../../artifacts/assistance-options-20261107', import.meta.url),
);
const resource = { fr, en, ar };
for (const locale of ['fr', 'en', 'ar'] as const)
  for (const theme of ['light', 'dark'] as const)
    for (const width of [1440, 390])
      test(`access ${locale}/${theme}/${width}: documentation, options and unavailable chat`, async ({
        page,
      }) => {
        await mkdir(output + '/captures', { recursive: true });
        const errors: string[] = [];
        page.on('pageerror', (error) => errors.push(error.message));
        await page.route('**/*', async (route) => {
          expect(new URL(route.request().url()).origin).toBe(
            'http://127.0.0.1:5173',
          );
          expect(route.request().method()).toBe('GET');
          await route.continue();
        });
        await page.setViewportSize({ width, height: 1100 });
        await page.addInitScript(
          (locale) => localStorage.setItem('moulai.locale', locale),
          locale,
        );
        await page.goto('http://127.0.0.1:5173/access');
        await page.evaluate((theme) => window.moulaiTheme.choose(theme), theme);
        const a = assistance[locale],
          v = assistanceV2[locale],
          r = resource[locale];
        const profile = page.getByRole('combobox', {
          name: r['review.profile'],
          exact: true,
        });
        await expect(profile).toBeVisible();
        await profile.focus();
        await page.keyboard.press('Space');
        await page
          .getByRole('option', { name: r['profile.empty'], exact: true })
          .click();
        await expect(page.locator('#review-choice')).toContainText(
          scenarioExplanation('empty', locale)!,
        );
        await page.locator('#review-choice summary').click();
        await expect(page.locator('#review-choice')).toContainText(
          scenarioExplanation('unlinked', locale)!,
        );
        await page.screenshot({
          path: `${output}/captures/access-options-${locale}-${theme}-${width}.png`,
        });
        await page.locator('#review-choice summary').click();
        const header = page.locator('header'),
          dock = header.locator('[data-assistance-dock]');
        const hb = (await header.boundingBox())!,
          db = (await dock.boundingBox())!;
        const appearance = (await header
          .getByRole('combobox')
          .first()
          .boundingBox())!;
        expect(db.y).toBeGreaterThanOrEqual(hb.y);
        expect(db.y + db.height).toBeLessThanOrEqual(appearance.y + 1);
        await dock
          .getByRole('button', { name: a['help.open'], exact: true })
          .focus();
        await page.keyboard.press('Enter');
        const dialog = page.getByRole('dialog');
        await expect(dialog).toHaveAttribute(
          'dir',
          locale === 'ar' ? 'rtl' : 'ltr',
        );
        expect(
          (
            await new AxeBuilder({ page })
              .include('[data-assistance-panel]')
              .analyze()
          ).violations,
        ).toEqual([]);
        await page.screenshot({
          path: `${output}/captures/access-guide-${locale}-${theme}-${width}.png`,
        });
        await page.keyboard.press('Escape');
        await expect(profile).toContainText(r['profile.empty']);
        await dock
          .getByRole('button', { name: a['help.assistant'], exact: true })
          .click();
        await expect(dialog.getByRole('textbox')).toBeVisible();
        await dialog
          .getByRole('textbox')
          .fill('Why is there no establishment?');
        await dialog
          .getByRole('button', { name: v['assist.send']!, exact: true })
          .click();
        await expect(dialog).toContainText(v['assist.notSent']!);
        await expect(
          dialog.getByRole('button', { name: a['voice.listen'], exact: true }),
        ).toBeDisabled();
        await dialog.getByRole('textbox').fill('Unsaved question');
        await page.screenshot({
          path: `${output}/captures/access-assistant-${locale}-${theme}-${width}.png`,
        });
        await page.keyboard.press('Escape');
        await expect(profile).toContainText(r['profile.empty']);
        await dock
          .getByRole('button', { name: a['help.assistant'], exact: true })
          .click();
        await expect(dialog.getByRole('textbox')).toHaveValue(
          'Unsaved question',
        );
        await expect(
          dialog.getByText('Why is there no establishment?', { exact: true }),
        ).toBeVisible();
        expect(
          (
            await new AxeBuilder({ page })
              .include('[data-assistance-panel]')
              .analyze()
          ).violations,
        ).toEqual([]);
        await page.keyboard.press('Escape');
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        expect(errors).toEqual([]);
        await writeFile(
          `${output}/access-${locale}-${theme}-${width}.json`,
          JSON.stringify({
            locale,
            theme,
            width,
            noExternalRequest: true,
            noBusinessWrite: true,
            draftPreserved: true,
            axeViolations: 0,
          }),
        );
      });
