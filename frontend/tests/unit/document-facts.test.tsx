// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import i18n from '../../src/shared/i18n';
import {
  CopyDocumentFact,
  DocumentDate,
  readableDocumentDate,
} from '../../src/shared/ui/DocumentFacts';
import { brandArtwork } from '../../src/shared/ui/brandArtwork';

describe('retained facts remain exact while their labels become readable', () => {
  it.each(['fr', 'en', 'ar'])(
    '%s formats fractional UTC facts and retains the exact source',
    async (locale) => {
      await i18n.changeLanguage(locale);
      const value = '2026-11-11T04:15:32.123456+00:00';
      const label = readableDocumentDate(value, locale);
      expect(label).toContain('UTC');
      expect(label).not.toContain('.123456');
      render(<DocumentDate value={value} />);
      expect(screen.getByText(label!).closest('time')).toHaveAttribute(
        'datetime',
        value,
      );
    },
  );
  it('interprets historical naive service values as UTC, never the device zone', () => {
    expect(readableDocumentDate('2026-11-11T00:00:00', 'fr')).toBe(
      readableDocumentDate('2026-11-11T00:00:00Z', 'fr'),
    );
    expect(readableDocumentDate('2026-11-11T02:00:00+02:00', 'fr')).toBe(
      readableDocumentDate('2026-11-11T00:00:00Z', 'fr'),
    );
    expect(readableDocumentDate('not-a-date', 'fr')).toBeNull();
    expect(readableDocumentDate('2026-11-11', 'fr')).toBeNull();
  });
  it('copies the entire reference including the URL fragment only on request', async () => {
    await i18n.changeLanguage('fr');
    const user = userEvent.setup();
    const write = vi
      .spyOn(navigator.clipboard, 'writeText')
      .mockResolvedValue();
    const value =
      'https://127.0.0.1:5180/verify-saas-document#' + 'a'.repeat(43);
    render(<CopyDocumentFact value={value} label="QR" />);
    expect(write).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button'));
    expect(write).toHaveBeenCalledExactlyOnceWith(value);
    expect(screen.getByRole('status')).toHaveTextContent('Copié');
  });
  it('reports a rejected clipboard instead of claiming a copy', async () => {
    await i18n.changeLanguage('fr');
    const user = userEvent.setup();
    vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(
      new Error('denied'),
    );
    render(<CopyDocumentFact value={'a'.repeat(43)} label="Référence" />);
    await user.click(screen.getByRole('button'));
    expect(screen.getByRole('status')).toHaveTextContent('Copie indisponible');
  });
  it('changes only the dark approved screen artwork without changing layout proportions', () => {
    expect(brandArtwork.light.src).toBe('/brand/moulai-logo-light01.png');
    expect(brandArtwork.dark.src).toBe(
      '/brand/moulai-logo-dark-approved-20261111.png',
    );
    for (const artwork of Object.values(brandArtwork))
      expect(artwork.width / artwork.height).toBeCloseTo(3, 1);
  });
});
