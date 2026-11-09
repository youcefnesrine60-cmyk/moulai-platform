// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { ar } from './ar';
import { fr } from './fr';
import { en } from './en';
import { businessFr } from './business.fr';
import { businessAr } from './business.ar';
import { businessEn } from './business.en';
import { intelligenceFr } from './intelligence.fr';
import { intelligenceEn } from './intelligence.en';
import { intelligenceAr } from './intelligence.ar';
import { officeFr } from './office.fr';
import { officeEn } from './office.en';
import { officeAr } from './office.ar';
import { diningFr } from './dining.fr';
import { diningEn } from './dining.en';
import { diningAr } from './dining.ar';
import { d1Fr } from './d1.fr';
import { d1En } from './d1.en';
import { d1Ar } from './d1.ar';
import { diningOpsFr } from './diningOps.fr';
import { diningOpsEn } from './diningOps.en';
import { diningOpsAr } from './diningOps.ar';
import { recovery } from './recovery';
import { serviceFr, serviceEn, serviceAr } from './diningService';
import { assistance } from './assistance';
import { assistanceV2 } from './assistanceV2';
import { integration } from './integration';
import { o3 } from './o3';
import { followup } from './followup';
import type { Locale, LocalizedLabel } from '../access/contracts';

/** Store only a language preference; identities and tenant data stay in memory. */
function initialLanguage(): Locale {
  try {
    const stored = localStorage.getItem('moulai.locale');
    return stored === 'ar' || stored === 'en' ? stored : 'fr';
  } catch {
    return 'fr';
  }
}

await i18n.use(initReactI18next).init({
  resources: {
    fr: {
      translation: {
        ...fr,
        ...businessFr,
        ...intelligenceFr,
        ...officeFr,
        ...diningFr,
        ...d1Fr,
        ...diningOpsFr,
        ...recovery.fr,
        ...serviceFr,
        ...assistance.fr,
        ...assistanceV2.fr,
        ...integration.fr,
        ...o3.fr,
        ...followup.fr,
      },
    },
    ar: {
      translation: {
        ...ar,
        ...businessAr,
        ...intelligenceAr,
        ...officeAr,
        ...diningAr,
        ...d1Ar,
        ...diningOpsAr,
        ...recovery.ar,
        ...serviceAr,
        ...assistance.ar,
        ...assistanceV2.ar,
        ...integration.ar,
        ...o3.ar,
        ...followup.ar,
      },
    },
    en: {
      translation: {
        ...en,
        ...businessEn,
        ...intelligenceEn,
        ...officeEn,
        ...diningEn,
        ...d1En,
        ...diningOpsEn,
        ...recovery.en,
        ...serviceEn,
        ...assistance.en,
        ...assistanceV2.en,
        ...integration.en,
        ...o3.en,
        ...followup.en,
      },
    },
  },
  lng: initialLanguage(),
  fallbackLng: 'fr',
  supportedLngs: ['fr', 'en', 'ar'],
  keySeparator: false,
  interpolation: { escapeValue: false },
});

/** Match semantic document direction as well as Radix's interaction direction. */
export function applyLocale(language: string): void {
  const locale = language === 'ar' || language === 'en' ? language : 'fr';
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === 'ar' ? 'rtl' : 'ltr';
  document.title = i18n.t('app.title', { lng: locale });
  try {
    localStorage.setItem('moulai.locale', locale);
  } catch {
    /* Private browsing may deny storage. */
  }
}

/** Read a localized view label without changing resource identifiers. */
export function localized(value: LocalizedLabel): string {
  return value[
    i18n.language === 'ar' || i18n.language === 'en' ? i18n.language : 'fr'
  ];
}

applyLocale(i18n.language);
i18n.on('languageChanged', applyLocale);
export default i18n;
