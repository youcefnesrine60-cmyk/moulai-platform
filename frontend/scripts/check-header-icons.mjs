// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Read-only visual and keyboard checks against the real local review; no business write or AI request.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {
  launch,
  login,
  newContext,
  origin,
  root,
} from './operationalHarness.mjs';
const output = path.join(root, 'artifacts/header-icons-20261108');
const browser = await launch(),
  captures = [],
  checks = [];
let phase = 'access';
try {
  const access = await (await newContext(browser)).newPage();
  const owner = await login(browser, 'owner-a');
  for (const [name, page, url, ready] of [
    [
      'access',
      access,
      '/access',
      'button[aria-describedby="connection-status"]',
    ],
    [
      'workspace',
      owner,
      '/workspace/organizations/8/restaurants/6/offer',
      'select[required]',
    ],
    [
      'tables',
      owner,
      '/workspace/organizations/8/restaurants/6/tables?branch=4',
      '[data-testid="operational-board"]',
    ],
  ]) {
    for (const locale of ['fr', 'en', 'ar']) {
      await page.goto(origin + '/access');
      await page.evaluate(
        (locale) => localStorage.setItem('moulai.locale', locale),
        locale,
      );
      await page.goto(origin + url);
      await page.locator(ready).waitFor();
      await page.waitForFunction(
        (locale) => document.documentElement.lang === locale,
        locale,
      );
      for (const theme of ['light', 'dark'])
        for (const [viewport, dimensions] of Object.entries({
          desktop: { width: 1440, height: 1000 },
          mobile: { width: 390, height: 844 },
        })) {
          phase = [name, locale, theme, viewport].join('-');
          await page.setViewportSize(dimensions);
          await page.evaluate(
            (theme) => window.moulaiTheme.choose(theme),
            theme,
          );
          await page.evaluate(() => document.fonts.ready);
          const header = page.locator('header').first(),
            dock = header.locator('[data-assistance-dock]');
          await dock.waitFor();
          const buttons = dock.getByRole('button');
          assert.equal(await buttons.count(), 2);
          await dock
            .locator('img')
            .evaluateAll((images) =>
              Promise.all(images.map((image) => image.decode())),
            );
          const facts = await dock.evaluate((nav) =>
            Array.from(nav.querySelectorAll('button')).map((button) => {
              const image = button.querySelector('img'),
                b = button.getBoundingClientRect(),
                i = image.getBoundingClientRect(),
                style = getComputedStyle(button),
                is = getComputedStyle(image);
              const canvas = document.createElement('canvas');
              canvas.width = image.naturalWidth;
              canvas.height = image.naturalHeight;
              const ctx = canvas.getContext('2d');
              ctx.drawImage(image, 0, 0);
              return {
                name: button.getAttribute('aria-label'),
                text: button.textContent,
                image: image.getAttribute('src'),
                loaded: image.complete && image.naturalWidth > 0,
                width: i.width,
                height: i.height,
                clickWidth: b.width,
                clickHeight: b.height,
                background: style.backgroundColor,
                border: style.borderWidth,
                fit: is.objectFit,
                filter: is.filter,
                transform: is.transform,
                cornerAlpha: ctx.getImageData(0, 0, 1, 1).data[3],
              };
            }),
          );
          for (const fact of facts) {
            assert(fact.name);
            assert.equal(fact.text, '');
            assert(fact.loaded);
            assert.equal(fact.width, 48);
            assert.equal(fact.height, 48);
            assert(fact.clickWidth >= 48 && fact.clickHeight >= 48);
            assert.equal(fact.background, 'rgba(0, 0, 0, 0)');
            assert.equal(fact.border, '0px');
            assert.equal(fact.fit, 'contain');
            assert.equal(fact.filter, 'none');
            assert.equal(fact.transform, 'none');
            assert.equal(fact.cornerAlpha, 0);
          }
          const appearance = header.getByRole('combobox').first();
          const dockBox = await dock.boundingBox(),
            appearanceBox = await appearance.boundingBox();
          assert(
            dockBox.y + dockBox.height <= appearanceBox.y + 1,
            'Help must be above appearance controls',
          );
          assert.equal(
            await page.evaluate(
              () => document.documentElement.scrollWidth > innerWidth + 1,
            ),
            false,
          );
          const file = phase + '.png';
          await page.mouse.move(0, dimensions.height - 1);
        await page.evaluate(() => {
          if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
        });
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
          await page.screenshot({
            path: path.join(output, file),
            fullPage: false,
            animations: 'disabled',
          });
          captures.push({ file, locale, theme, viewport, screen: name, facts });
          // Focus shows a translated tooltip; opening either panel never submits the underlying form.
          const help = buttons.nth(0),
            assistant = buttons.nth(1);
          await help.hover();
          assert.equal(
            await dock.getByRole('tooltip').first().isVisible(),
            true,
          );
          await page.mouse.move(0, dimensions.height - 1);
          await page.keyboard.press('Tab');
          await help.focus();
          assert.equal(
            await help.evaluate((el) => getComputedStyle(el).outlineStyle),
            'solid',
          );
          assert.equal(
            await dock.getByRole('tooltip').first().isVisible(),
            true,
          );
          if (locale === 'fr')
            await header.screenshot({
              path: path.join(output, phase + '-focus.png'),
            });
          await help.press('Enter');
          await page.getByRole('dialog').waitFor();
          await page.keyboard.press('Escape');
          await page.getByRole('dialog').waitFor({ state: 'hidden' });
          await page.waitForFunction(
            (el) => el === document.activeElement,
            await help.elementHandle(),
          );
          await assistant.focus();
          await assistant.press('Enter');
          const dialog = page.getByRole('dialog');
          await dialog.waitFor();
          assert(await dialog.getByRole('textbox').isVisible());
          assert(
            (await dialog.innerText()).includes(
              {
                fr: 'Service IA indisponible',
                en: 'AI service unavailable',
                ar: 'خدمة الذكاء الاصطناعي غير متاحة',
              }[locale],
            ),
          );
          if (name === 'access' && locale === 'fr')
            await page.screenshot({
              path: path.join(output, phase + '-assistant.png'),
              animations: 'disabled',
            });
          await page.keyboard.press('Escape');
          await dialog.waitFor({ state: 'hidden' });
          checks.push({
            label: phase,
            status: 'PASS',
            original_alpha_and_48px: true,
            keyboard: true,
            explicit_unavailable: true,
            above_preferences: true,
          });
        }
    }
  }
  fs.writeFileSync(
    path.join(output, 'browser-results.json'),
    JSON.stringify(
      { status: 'PASS', checks, captures, AI_calls: 0, business_writes: 0 },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({
      status: 'PASS',
      checks: checks.length,
      captures: captures.length,
    }),
  );
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'failure-' + Date.now() + '.json'),
    JSON.stringify(
      {
        status: 'FAIL',
        phase,
        type: error.name,
        message: error.name === 'AssertionError' ? error.message : undefined,
        checks,
        captures,
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ status: 'FAIL', phase, type: error.name }));
  process.exitCode = 1;
} finally {
  await browser.close();
}
