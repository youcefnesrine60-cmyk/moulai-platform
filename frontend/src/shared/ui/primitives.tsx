// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { ButtonHTMLAttributes, ReactElement, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  ArrowRight,
  LoaderCircle,
  ShieldCheck,
  Sun,
  Moon,
  Check,
  ChevronDown,
} from 'lucide-react';
import * as Select from '@radix-ui/react-select';
import { AccessError } from '../access/contracts';
import { useTheme } from '../theme';
import styles from './ui.module.css';

/** Use the supplied transparent theme-specific artwork without altering its pixels. */
export function Brand({
  inverse = false,
  prominent = false,
}: {
  inverse?: boolean;
  prominent?: boolean;
}): ReactElement {
  const { t, i18n } = useTranslation();
  const { theme } = useTheme();
  return (
    <div
      className={`${styles.brand} ${inverse ? styles.inverse : ''} ${prominent ? styles.prominent : ''}`}
      data-brand-size={prominent ? 'prominent' : 'compact'}
    >
      <span className={styles.brandArtwork} dir="ltr">
        <img
          className={styles.brandLogo}
          key={theme}
          src={`/brand/moulai-logo-${theme}01.png`}
          alt="MoulAI™"
          width={2172}
          height={724}
        />
      </span>
      <span className={styles.brandTagline} dir={i18n.dir()}>
        {t('brand.tagline')}
      </span>
    </div>
  );
}

/** Shared visible focus, touch target and native disabled semantics. */
export function Button({
  children,
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'quiet';
  children: ReactNode;
}): ReactElement {
  return (
    <button
      className={`${styles.button} ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function ForwardArrow(): ReactElement {
  return <ArrowRight className="directional" size={17} aria-hidden="true" />;
}

/** Reuse i18next preferences through the same accessible selector family as themes. */
export function LanguageControl(): ReactElement {
  const { t, i18n } = useTranslation();
  const locale =
    i18n.language === 'ar' || i18n.language === 'en' ? i18n.language : 'fr';
  return (
    <Select.Root
      value={locale}
      onValueChange={(value) => {
        if (value === 'fr' || value === 'en' || value === 'ar')
          void i18n.changeLanguage(value);
      }}
    >
      <Select.Trigger
        className={`${styles.themeTrigger} ${styles.languageTrigger}`}
        aria-label={t('preferences.language')}
      >
        <Select.Value>
          <span dir="ltr">{locale.toUpperCase()}</span>
        </Select.Value>
        <Select.Icon>
          <ChevronDown size={14} aria-hidden="true" />
        </Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content
          className={styles.themeMenu}
          position="popper"
          sideOffset={6}
        >
          <Select.Viewport>
            {(
              [
                ['fr', 'Français — FR'],
                ['en', 'English — EN'],
                ['ar', 'العربية — AR'],
              ] as const
            ).map(([value, label]) => (
              <Select.Item
                key={value}
                value={value}
                className={styles.themeItem}
              >
                <Select.ItemText>
                  <span lang={value} dir={value === 'ar' ? 'rtl' : 'ltr'}>
                    {label}
                  </span>
                </Select.ItemText>
                <Select.ItemIndicator>
                  <Check size={16} aria-hidden="true" />
                </Select.ItemIndicator>
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}

/** One direction-aware accessible theme selector uses the pre-paint store. */
export function ThemeControl(): ReactElement {
  const { t } = useTranslation();
  const { theme, preference, choose } = useTheme();
  const Icon = theme === 'dark' ? Moon : Sun;
  return (
    <Select.Root
      value={preference}
      onValueChange={(value) => {
        if (value === 'light' || value === 'dark' || value === 'system')
          choose(value);
      }}
    >
      <Select.Trigger
        className={styles.themeTrigger}
        aria-label={t('preferences.theme')}
        title={`${t('preferences.theme')} · ${t(`theme.${preference}`)}`}
      >
        <Select.Value>
          <Icon size={19} aria-hidden="true" />
          <span className="sr-only">{t(`theme.${preference}`)}</span>
        </Select.Value>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content
          className={styles.themeMenu}
          position="popper"
          sideOffset={6}
        >
          <Select.Viewport>
            {(['light', 'dark', 'system'] as const).map((value) => (
              <Select.Item
                key={value}
                value={value}
                className={styles.themeItem}
              >
                <Select.ItemText>{t(`theme.${value}`)}</Select.ItemText>
                <Select.ItemIndicator>
                  <Check size={16} aria-hidden="true" />
                </Select.ItemIndicator>
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}

/** Stable controls change preferences without replacing providers, sessions or drafts. */
export function AppearanceControls(): ReactElement {
  return (
    <div className={styles.appearance}>
      <LanguageControl />
      <ThemeControl />
    </div>
  );
}

export function Badge({
  children,
  tone = 'neutral',
}: {
  children: ReactNode;
  tone?: 'neutral' | 'green' | 'test';
}): ReactElement {
  return <span className={`${styles.badge} ${styles[tone]}`}>{children}</span>;
}

/** Reusable pending state remains announced, including on company switches. */
export function LoadingPanel(): ReactElement {
  const { t } = useTranslation();
  return (
    <section className={styles.state} role="status" aria-live="polite">
      <LoaderCircle className={styles.spinner} size={28} aria-hidden="true" />
      <h1>{t('common.loading')}</h1>
      <p>{t('common.loadingDescription')}</p>
    </section>
  );
}

/** Generic access errors do not disclose foreign company or restaurant details. */
export function ErrorPanel({
  error,
  retry,
  leave,
}: {
  error: unknown;
  retry?: () => void;
  leave?: () => void;
}): ReactElement {
  const { t } = useTranslation();
  const code = error instanceof AccessError ? error.code : 'temporary';
  return (
    <section className={styles.state} role="alert">
      <span className={styles.stateIcon}>
        <AlertCircle size={28} aria-hidden="true" />
      </span>
      <h1>{t(`state.${code}.title`)}</h1>
      <p>{t(`state.${code}.body`)}</p>
      <div className={styles.stateActions}>
        {retry && (
          <Button variant="secondary" onClick={retry}>
            {t('common.retry')}
          </Button>
        )}
        {leave && <Button onClick={leave}>{t('common.changeProfile')}</Button>}
      </div>
    </section>
  );
}

export function BoundaryNote(): ReactElement {
  const { t } = useTranslation();
  return (
    <aside className={styles.boundary}>
      <ShieldCheck size={22} aria-hidden="true" />
      <div>
        <strong>{t('companies.footerTitle')}</strong>
        <p>{t('companies.footerBody')}</p>
      </div>
    </aside>
  );
}
