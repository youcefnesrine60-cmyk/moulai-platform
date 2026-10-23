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
} from 'lucide-react';
import * as Select from '@radix-ui/react-select';
import { AccessError } from '../access/contracts';
import { useTheme } from '../theme';
import styles from './ui.module.css';

/** Display the approved original artwork unchanged on its readable light surface. */
export function Brand({
  inverse = false,
}: {
  inverse?: boolean;
}): ReactElement {
  const { t } = useTranslation();
  return (
    <div className={`${styles.brand} ${inverse ? styles.inverse : ''}`}>
      <span className={styles.brandArtwork} dir="ltr">
        <img
          className={styles.brandLogo}
          src="/brand/moulai-logo.png"
          alt="MoulAI™"
          width={1265}
          height={331}
        />
      </span>
      <span className={styles.brandTagline}>{t('brand.tagline')}</span>
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

export function LanguageControl(): ReactElement {
  const { t, i18n } = useTranslation();
  return (
    <div
      className={styles.languages}
      role="group"
      aria-label={t('preferences.language')}
    >
      <button
        lang="fr"
        aria-pressed={i18n.language === 'fr'}
        onClick={() => void i18n.changeLanguage('fr')}
      >
        FR
      </button>
      <span aria-hidden="true">/</span>
      <button
        lang="en"
        aria-pressed={i18n.language === 'en'}
        onClick={() => void i18n.changeLanguage('en')}
      >
        EN
      </button>
      <span aria-hidden="true">/</span>
      <button
        lang="ar"
        aria-pressed={i18n.language === 'ar'}
        onClick={() => void i18n.changeLanguage('ar')}
      >
        العربية
      </button>
    </div>
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
