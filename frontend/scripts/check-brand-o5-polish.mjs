// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Fresh verified local browser contexts exercise resources, not the browser's unobservable tab chrome.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  launch,
  login,
  newContext,
  root,
  origin,
} from './operationalHarness.mjs';

const output = path.join(root, 'artifacts/documents-o5-polish-20261111/brand');
fs.mkdirSync(output, { recursive: true });
const browser = await launch();
const captures = [];
try {
  const context = await newContext(browser);
  const page = await context.newPage();
  await page.goto(origin + '/access');
  await page.locator('header img[alt="MoulAI™"]').waitFor();
  assert.equal(await page.title(), 'MoulAI™');
  const icons = await page
    .locator('link[rel="icon"]')
    .evaluateAll((elements) => elements.map((e) => e.getAttribute('href')));
  assert.deepEqual(icons, [
    '/brand/GateWay-transparent-v2.png',
    '/brand/GateWay-transparent-v2.ico',
  ]);
  const alpha = await page.evaluate(async () => {
    async function pixels(src) {
      const image = new Image();
      image.src = src;
      await image.decode();
      const canvas = document.createElement('canvas');
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(image, 0, 0);
      return {
        width: canvas.width,
        height: canvas.height,
        bytes: Array.from(
          ctx.getImageData(0, 0, canvas.width, canvas.height).data,
        ),
      };
    }
    const source = await pixels('/brand/GateWay.png'),
      png = await pixels('/brand/GateWay-transparent-v2.png'),
      ico = await pixels('/brand/GateWay-transparent-v2.ico');
    let removed = 0,
      interior = 0;
    for (let i = 0; i < source.bytes.length; i += 4) {
      if (png.bytes[i + 3] === 0) removed++;
      else {
        for (let k = 0; k < 4; k++)
          if (source.bytes[i + k] !== png.bytes[i + k])
            throw new Error('Interior changed');
        interior++;
      }
    }
    if (JSON.stringify(png) !== JSON.stringify(ico))
      throw new Error('ICO differs from PNG');
    return {
      width: png.width,
      height: png.height,
      removed,
      interior,
      variantsEqual: true,
    };
  });
  assert.equal(alpha.removed, 176);
  assert.equal(alpha.interior, 994);
  const darkBytes = await (
    await page.request.get(
      origin + '/brand/moulai-logo-dark-approved-20261111.png',
    )
  ).body();
  assert(
    darkBytes.equals(
      fs.readFileSync(
        path.join(root, 'assets/originals/moulai-logo-Mode-Sombre.png'),
      ),
    ),
  );
  const lightBytes = await (
    await page.request.get(origin + '/brand/moulai-logo-light01.png')
  ).body();
  assert.equal(
    crypto.createHash('sha256').update(lightBytes).digest('hex'),
    'f98556da16c7b63ad33242402c523de220d8782a246c8cd940b9d7fc75582dba',
  );

  async function capture(screen, activePage) {
    for (const locale of ['fr', 'en', 'ar']) {
      await activePage.evaluate(
        (locale) => localStorage.setItem('moulai.locale', locale),
        locale,
      );
      await activePage.reload();
      await activePage.locator('header img[alt="MoulAI™"]').waitFor();
      for (const theme of ['light', 'dark'])
        for (const [device, viewport] of Object.entries({
          desktop: { width: 1440, height: 900 },
          mobile: { width: 390, height: 844 },
        })) {
          await activePage.setViewportSize(viewport);
          await activePage.evaluate(
            (theme) => window.moulaiTheme.choose(theme),
            theme,
          );
          const logo = activePage.locator('header img[alt="MoulAI™"]');
          await logo.evaluate((image) => image.decode());
          await activePage.evaluate(() => document.fonts.ready);
          assert.equal(
            await logo.getAttribute('src'),
            theme === 'dark'
              ? '/brand/moulai-logo-dark-approved-20261111.png'
              : '/brand/moulai-logo-light01.png',
          );
          assert.equal(
            await activePage.evaluate(
              () => document.documentElement.scrollWidth > innerWidth,
            ),
            false,
          );
          assert.equal(await activePage.title(), 'MoulAI™');
          assert.equal(
            await activePage.locator('html').getAttribute('dir'),
            locale === 'ar' ? 'rtl' : 'ltr',
          );
          const file = `${screen}-${locale}-${theme}-${device}.png`;
          // Paint offscreen content-visibility sections before a full-page evidence capture.
          await activePage.evaluate(async () => {
            for (
              let y = 0;
              y < document.documentElement.scrollHeight;
              y += innerHeight
            ) {
              scrollTo(0, y);
              await new Promise((resolve) => requestAnimationFrame(resolve));
            }
            scrollTo(0, 0);
            await new Promise((resolve) =>
              requestAnimationFrame(() => requestAnimationFrame(resolve)),
            );
          });
          await activePage.screenshot({
            path: path.join(output, file),
            fullPage: true,
          });
          captures.push({ file, screen, locale, theme, device });
        }
    }
  }
  await capture('access', page);
  const staff = await login(browser, 'owner-a');
  await capture('workspace', staff);
  // Public restaurant entry shares Brand even before any visit is opened or order requested.
  await page.goto(origin + '/menu');
  await capture('public-dining', page);
  fs.writeFileSync(
    path.join(output, 'summary.json'),
    JSON.stringify(
      {
        status: 'PASS',
        captures,
        alpha,
        freshContext: true,
        title: 'MoulAI™',
        darkOriginalByteIdentical: true,
        lightOriginalUnchanged: true,
        businessWrites: 0,
        browserTabChrome:
          'NOT VERIFIED — Windows tool could not attest the URL',
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({ status: 'PASS', captures: captures.length, alpha }),
  );
} finally {
  await browser.close();
}
