// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { ReactElement } from 'react';
import { Link } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  ArrowLeft,
  Building2,
  MapPin,
  RefreshCw,
  ShieldCheck,
  Store,
} from 'lucide-react';
import {
  identityKey,
  useAdapter,
  useLeaveReview,
  useOrganizations,
  useSession,
} from '../../app/access';
import { AccessError } from '../../shared/access/contracts';
import { localized } from '../../shared/i18n';
import {
  Badge,
  BoundaryNote,
  Button,
  ErrorPanel,
  ForwardArrow,
  LoadingPanel,
} from '../../shared/ui/primitives';
import { useSelection } from '../management/scope';
import styles from './workspace.module.css';

/** Personal organization discovery is never inferred from a global restaurant list. */
export function OrganizationsPage(): ReactElement {
  const { t } = useTranslation();
  const query = useOrganizations();
  const leave = useLeaveReview();
  if (query.isPending) return <LoadingPanel />;
  if (query.isError)
    return (
      <ErrorPanel
        error={query.error}
        retry={() => void query.refetch()}
        leave={() => void leave()}
      />
    );
  return (
    <>
      <div className={styles.titleRow}>
        <div>
          <p className="eyebrow">{t('companies.eyebrow')}</p>
          <h1>{t('companies.title')}</h1>
          <p className={styles.intro}>{t('companies.description')}</p>
        </div>
        <Button
          variant="secondary"
          onClick={() => void query.refetch()}
          disabled={query.isFetching}
        >
          <RefreshCw size={16} aria-hidden="true" />
          {t('common.refresh')}
        </Button>
      </div>
      <div className={styles.sectionHeading}>
        <h2>{t('nav.workspace')}</h2>
        <Badge tone="test">{t('review.badge')}</Badge>
      </div>
      <div className={styles.cards}>
        {query.data.map((company, index) => (
          <Link
            className={styles.companyCard}
            key={company.id}
            to={`/workspace/organizations/${company.id}/restaurants`}
            aria-label={`${t('companies.open')} · ${localized(company.name)}`}
          >
            <div
              className={`${styles.cardVisual} ${index % 2 ? styles.sand : ''}`}
            >
              <Building2 size={36} strokeWidth={1.2} aria-hidden="true" />
              <span className={styles.visualLabel}>{t('review.badge')}</span>
            </div>
            <div className={styles.cardBody}>
              <div className={styles.cardTop}>
                <Badge>{t(`role.${company.role}`)}</Badge>
                <span className={styles.location}>
                  <MapPin size={13} aria-hidden="true" />
                  {localized(company.city)}
                </span>
              </div>
              <h3>{localized(company.name)}</h3>
              <p className={styles.scope}>
                <ShieldCheck size={15} aria-hidden="true" />
                {t(`scope.${company.accessMode}`)}
              </p>
              <div className={styles.cardFooter}>
                <span>{t('companies.open')}</span>
                <ForwardArrow />
              </div>
            </div>
          </Link>
        ))}
      </div>
      <BoundaryNote />
    </>
  );
}

/** List only restaurants admitted by the selected personal membership. */
export function RestaurantsPage(): ReactElement {
  const { t } = useTranslation();
  const adapter = useAdapter();
  const session = useSession();
  const leave = useLeaveReview();
  const { organizations, company, organizationId } = useSelection();
  const query = useQuery({
    queryKey: [...identityKey(session.data), organizationId, 'restaurants'],
    queryFn: ({ signal }) => adapter.restaurants(organizationId ?? 0, signal),
    enabled: Boolean(company),
    retry: false,
  });
  if (organizations.isError)
    return (
      <ErrorPanel error={organizations.error} leave={() => void leave()} />
    );
  if (organizations.isPending) return <LoadingPanel />;
  if (!company)
    return (
      <ErrorPanel
        error={new AccessError('notFound')}
        leave={() => void leave()}
      />
    );
  if (query.isPending) return <LoadingPanel />;
  if (query.isError)
    return (
      <ErrorPanel
        error={query.error}
        retry={() => void query.refetch()}
        leave={() => void leave()}
      />
    );
  return (
    <>
      <Link className={styles.backLink} to="/workspace">
        <ArrowLeft className="directional" size={16} aria-hidden="true" />
        {t('common.back')}
      </Link>
      <div className={styles.titleRow}>
        <div>
          <p className="eyebrow">{t('restaurants.eyebrow')}</p>
          <h1>{localized(company.name)}</h1>
          <p className={styles.intro}>{t('restaurants.description')}</p>
        </div>
        <Badge>{t(`role.${company.role}`)}</Badge>
      </div>
      <div className={styles.sectionHeading}>
        <h2>{t('restaurants.count', { count: query.data.length })}</h2>
        <Badge tone="test">{t('review.badge')}</Badge>
      </div>
      {query.data.length === 0 ? (
        <section className={styles.empty}>
          <Store size={32} strokeWidth={1.4} aria-hidden="true" />
          <h2>{t('restaurants.emptyTitle')}</h2>
          <p>{t('restaurants.emptyBody')}</p>
        </section>
      ) : (
        <div className={styles.cards}>
          {query.data.map((place) => (
            <Link
              className={styles.restaurantCard}
              key={place.id}
              to={`/workspace/organizations/${company.id}/restaurants/${place.id}`}
              aria-label={`${t('restaurants.open')} · ${localized(place.name)}`}
            >
              <div className={styles.restaurantTop}>
                <span className={styles.restaurantIcon}>
                  <Store size={27} strokeWidth={1.4} aria-hidden="true" />
                </span>
                <Badge tone={place.active ? 'green' : 'neutral'}>
                  {t(place.active ? 'common.active' : 'common.inactive')}
                </Badge>
              </div>
              <h3>{localized(place.name)}</h3>
              <p className={styles.location}>
                <MapPin size={14} aria-hidden="true" />
                {localized(place.city)}
              </p>
              <div className={styles.cardFooter}>
                <span>{t('restaurants.open')}</span>
                <ForwardArrow />
              </div>
            </Link>
          ))}
        </div>
      )}
      <BoundaryNote />
    </>
  );
}
