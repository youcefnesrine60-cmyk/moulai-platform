// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const originals = new URL('../brand-sources/gateway/', import.meta.url);
const destination = new URL('../public/brand/gateway/', import.meta.url);
const sources = [
  {
    theme: 'dark',
    file: 'moulai-fond-dark.png',
    sha256: '672001c4347c9056139d05aa3113a45a56d0922579fc96ee0c3733ca59fd40e4',
  },
  {
    theme: 'light',
    file: 'moulai-fond-Leight.png',
    sha256: '3ccd82e3c7d3411cdd0ec6fe0ed41d5bdfe99911f6955d4defd43023bd19d8d5',
  },
];
process.env.PLAYWRIGHT_BROWSERS_PATH ??= fileURLToPath(
  new URL('../../artifacts/frontend-tooling/browsers', import.meta.url),
);
const { chromium } = await import('@playwright/test');

/** Fingerprint originals and encoded outputs without changing the approved PNGs. */
function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

/** Encode the complete composition: no crop, overlay, filter or generated artwork. */
async function encode(page, bytes, width) {
  return page.evaluate(
    async ({ data, width: target }) => {
      const input = Uint8Array.from(atob(data), (character) =>
        character.charCodeAt(0),
      );
      const image = await createImageBitmap(
        new Blob([input], { type: 'image/png' }),
      );
      if (image.width !== 1672 || image.height !== 941)
        throw new Error('Unexpected approved Gateway dimensions.');
      const canvas = document.createElement('canvas');
      canvas.width = target;
      canvas.height = Math.round((image.height * target) / image.width);
      const context = canvas.getContext('2d');
      if (!context) throw new Error('Canvas encoding is unavailable.');
      context.imageSmoothingEnabled = true;
      context.imageSmoothingQuality = 'high';
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      image.close();
      return {
        uri: canvas.toDataURL('image/webp', 0.92),
        width: canvas.width,
        height: canvas.height,
      };
    },
    { data: bytes.toString('base64'), width },
  );
}

/** Rebuild only derivative files after attesting both immutable source images. */
async function prepare() {
  const inputs = await Promise.all(
    sources.map(async (source) => {
      const bytes = await readFile(new URL(source.file, originals));
      assert.equal(
        sha256(bytes),
        source.sha256,
        'Approved original hash mismatch.',
      );
      return { ...source, bytes };
    }),
  );
  await mkdir(destination, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const manifest = [];
  try {
    const page = await browser.newPage();
    await page.route('**/*', (route) => route.abort());
    for (const source of inputs) {
      const variants = [];
      for (const width of [640, 1024, 1672]) {
        const encoded = await encode(page, source.bytes, width);
        assert(encoded.uri.startsWith('data:image/webp;base64,'));
        const bytes = Buffer.from(encoded.uri.split(',')[1], 'base64');
        const file = `${source.theme}-${width}.webp`;
        await writeFile(new URL(file, destination), bytes);
        variants.push({
          file,
          width: encoded.width,
          height: encoded.height,
          bytes: bytes.length,
          sha256: sha256(bytes),
        });
      }
      assert.equal(
        sha256(await readFile(new URL(source.file, originals))),
        source.sha256,
      );
      manifest.push({
        theme: source.theme,
        original: source.file,
        originalSha256: source.sha256,
        originalBytes: source.bytes.length,
        width: 1672,
        height: 941,
        encoding: 'WebP quality 0.92; full-frame proportional resize',
        variants,
      });
    }
  } finally {
    await browser.close();
  }
  await writeFile(
    new URL('manifest.json', originals),
    JSON.stringify({ sources: manifest }, null, 2) + '\n',
  );
  console.info(JSON.stringify(manifest));
}

await prepare();
