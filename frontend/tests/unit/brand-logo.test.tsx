// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { act, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BrandLogo } from '../../src/shared/ui/BrandLogo';
import { brandArtwork } from '../../src/shared/ui/brandArtwork';

describe('approved surface-aware artwork with an explicit print source', () => {
  for (const theme of ['light', 'dark'] as const)
    it(`${theme} uses the matching screen original and the light original for paper`, () => {
      window.moulaiTheme.choose(theme);
      render(<BrandLogo />);
      const image = screen.getByRole('img', { name: 'MoulAI™' });
      expect(image).toHaveAttribute('src', brandArtwork[theme].src);
      expect(image).toHaveAttribute('width', String(brandArtwork[theme].width));
      expect(image).toHaveAttribute(
        'height',
        String(brandArtwork[theme].height),
      );
      const paper = image.closest('picture')?.querySelector('source');
      expect(paper).toHaveAttribute('media', 'print');
      expect(paper).toHaveAttribute('srcset', brandArtwork.light.src);
      expect(paper).toHaveAttribute('width', String(brandArtwork.light.width));
      expect(image).not.toHaveAttribute('style');
      expect(screen.getAllByRole('img')).toHaveLength(1);
    });
  it('switches both ways without a reload, image remount or loss of a neighbouring draft', () => {
    window.moulaiTheme.choose('light');
    render(
      <>
        <BrandLogo />
        <input aria-label="Draft" defaultValue="Retained draft" />
      </>,
    );
    const image = screen.getByRole('img');
    for (const theme of ['dark', 'light', 'dark'] as const) {
      act(() => window.moulaiTheme.choose(theme));
      expect(screen.getByRole('img')).toBe(image);
      expect(image).toHaveAttribute('src', brandArtwork[theme].src);
      expect(screen.getByLabelText('Draft')).toHaveValue('Retained draft');
    }
  });
  it('keeps an explicitly white preview light even inside a dark application', () => {
    window.moulaiTheme.choose('dark');
    render(<BrandLogo surface="light" />);
    expect(screen.getByRole('img')).toHaveAttribute(
      'src',
      brandArtwork.light.src,
    );
  });
});
