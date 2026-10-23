// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useState, type ReactElement } from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { BookOpen, ClipboardList, Pencil, Store } from 'lucide-react';
import { localized } from '../../shared/i18n';
import { Badge, Button, ForwardArrow } from '../../shared/ui/primitives';
import { ReviewEditor } from './ReviewEditor';
import { useRestaurantContext } from './scope';
import styles from './management.module.css';

/** Restaurant management excludes ownership, activation and any external effects. */
export function RestaurantProfilePage(): ReactElement {
  const { t } = useTranslation();
  const { company, restaurant, data, basePath } = useRestaurantContext();
  const [editing, setEditing] = useState(false);
  const [saved, setSaved] = useState(false);
  const editable = company.permissions.includes('tenant.restaurants.update');
  return (
    <>
      <div className={styles.titleRow}>
        <div>
          <p className="eyebrow">{t('business.overview')}</p>
          <h1>{localized(restaurant.name)}</h1>
          <p className={styles.intro}>{t('business.profileHelp')}</p>
        </div>
        {editable && (
          <Button
            variant="secondary"
            onClick={() => {
              setSaved(false);
              setEditing(true);
            }}
          >
            <Pencil size={16} aria-hidden="true" />
            {t('business.editProfile')}
          </Button>
        )}
      </div>
      {!editable && <p className={styles.notice}>{t('business.readOnly')}</p>}
      {saved && (
        <p role="status" className={styles.success}>
          {t('business.saved')}
        </p>
      )}
      <div className={styles.grid}>
        <section className={styles.panel}>
          <h2>
            <Store size={19} aria-hidden="true" /> {t('business.overview')}
          </h2>
          <dl className={styles.definition}>
            <dt>{t('business.name')}</dt>
            <dd>{data.profile.name}</dd>
            <dt>{t('business.type')}</dt>
            <dd>{t(`business.establishment.${data.profile.type}`)}</dd>
            <dt>{t('business.phone')}</dt>
            <dd>
              <bdi>{data.profile.phone}</bdi>
            </dd>
            <dt>{t('business.wilaya')}</dt>
            <dd>{data.profile.wilaya || t('business.emptyValue')}</dd>
          </dl>
          <div className={styles.cardBottom}>
            <Badge tone={restaurant.active ? 'green' : 'neutral'}>
              {t(restaurant.active ? 'common.active' : 'common.inactive')}
            </Badge>
            <Badge tone="test">{t('review.badge')}</Badge>
          </div>
        </section>
        <section className={styles.panel}>
          <h2>{t('nav.management')}</h2>
          {company.permissions.includes('tenant.catalog.read') && (
            <Link to={`${basePath}/catalogue`} className={styles.row}>
              <span>
                <BookOpen size={20} aria-hidden="true" /> {t('nav.catalogue')}
              </span>
              <ForwardArrow />
            </Link>
          )}
          {company.permissions.includes('tenant.orders.read') && (
            <Link to={`${basePath}/orders`} className={styles.row}>
              <span>
                <ClipboardList size={20} aria-hidden="true" /> {t('nav.orders')}
              </span>
              <ForwardArrow />
            </Link>
          )}
        </section>
      </div>
      {editing && (
        <ReviewEditor
          selection={{ kind: 'profile', id: null }}
          close={() => setEditing(false)}
          saved={() => setSaved(true)}
        />
      )}
    </>
  );
}
