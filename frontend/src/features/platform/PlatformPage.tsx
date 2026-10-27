// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { ReactElement } from 'react';
import { ClipboardCheck, CreditCard, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { useSession } from '../../app/access';
import { Badge } from '../../shared/ui/primitives';
import styles from '../workspace/workspace.module.css';

/** No membership or cross-company view is inferred from platform administration. */
export function PlatformPage(): ReactElement {
  const { t } = useTranslation();
  const session = useSession();
  const cards = [
    ['admins.manage', 'nav.requests', 'platform.card.requests', ClipboardCheck],
    ['payments.review', 'nav.receipts', 'platform.card.receipts', CreditCard],
    ['admins.manage', 'nav.audit', 'platform.card.audit', ShieldCheck],
  ] as const;
  return (
    <>
      <p className="eyebrow">{t('platform.eyebrow')}</p>
      <h1>{t('platform.title')}</h1>
      <p className={styles.intro}>{t('platform.description')}</p>
      <p className={styles.intro}>{t('office.platformIntro')}</p>
      <div className={styles.sectionHeading}>
        <h2>{t('nav.platformArea')}</h2>
        <Badge tone="test">{t('review.badge')}</Badge>
      </div>
      <div className={styles.moduleGrid}>
        {cards
          .filter(([permission]) =>
            session.data?.platformPermissions.includes(permission),
          )
          .map(([, title, description, Icon]) => (
            <section className={styles.moduleCard} key={title}>
              <Icon size={26} strokeWidth={1.4} aria-hidden="true" />
              <h3>{t(title)}</h3>
              <p>{t(description)}</p>
              <Link to={`/platform/${title.split('.')[1]}`}>
                {t('office.details')}
              </Link>
            </section>
          ))}
      </div>
    </>
  );
}
