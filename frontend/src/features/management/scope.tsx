// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { ReactElement } from 'react';
import {
  Link,
  NavLink,
  Outlet,
  useOutletContext,
  useParams,
} from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Building2, Store } from 'lucide-react';
import {
  identityKey,
  useAdapter,
  useLeaveReview,
  useOrganizations,
  useSession,
} from '../../app/access';
import {
  AccessError,
  type OrganizationView,
  type RestaurantView,
} from '../../shared/access/contracts';
import type {
  RestaurantScope,
  RestaurantWorkspace,
} from '../../shared/business/contracts';
import { localized } from '../../shared/i18n';
import {
  Badge,
  Button,
  ErrorPanel,
  LoadingPanel,
} from '../../shared/ui/primitives';
import styles from './management.module.css';

export interface RestaurantContext {
  readonly scope: RestaurantScope;
  readonly company: OrganizationView;
  readonly restaurant: RestaurantView;
  readonly data: RestaurantWorkspace;
  readonly basePath: string;
  readonly queryKey: readonly (string | number)[];
}

/** Never fall back to the first company or restaurant on malformed selection. */
export function positiveId(value: string | undefined): number | null {
  if (!value || !/^\d+$/.test(value)) return null;
  const id = Number(value);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

/** Membership discovery reuses the existing identity-qualified query. */
export function useSelection() {
  const params = useParams();
  const organizations = useOrganizations();
  const organizationId = positiveId(params.organizationId);
  return {
    organizations,
    organizationId,
    company: organizations.data?.find((row) => row.id === organizationId),
    restaurantId: positiveId(params.restaurantId),
  };
}

/** Scope every child read/cache to the verified review identity and both selections. */
export function RestaurantFrame(): ReactElement {
  const { t } = useTranslation();
  const adapter = useAdapter();
  const session = useSession();
  const leave = useLeaveReview();
  const { organizations, organizationId, restaurantId, company } =
    useSelection();
  const scope = {
    organizationId: organizationId ?? 0,
    restaurantId: restaurantId ?? 0,
  };
  const prefix = [
    ...identityKey(session.data),
    scope.organizationId,
    'restaurant',
    scope.restaurantId,
  ];
  const restaurant = useQuery({
    queryKey: prefix,
    queryFn: ({ signal }) =>
      adapter.restaurant(scope.organizationId, scope.restaurantId, signal),
    enabled: Boolean(company && restaurantId),
  });
  const queryKey = [...prefix, 'workspace'];
  const workspace = useQuery({
    queryKey,
    queryFn: ({ signal }) => adapter.workspace(scope, signal),
    enabled: Boolean(company && restaurant.data),
  });
  if (organizations.isError)
    return (
      <ErrorPanel error={organizations.error} leave={() => void leave()} />
    );
  if (organizations.isPending) return <LoadingPanel />;
  if (!company || !restaurantId)
    return (
      <ErrorPanel
        error={new AccessError('notFound')}
        leave={() => void leave()}
      />
    );
  if (restaurant.isError || workspace.isError)
    return (
      <ErrorPanel
        error={restaurant.error ?? workspace.error}
        retry={() => {
          void restaurant.refetch();
          void workspace.refetch();
        }}
        leave={() => void leave()}
      />
    );
  if (restaurant.isPending || workspace.isPending) return <LoadingPanel />;
  const basePath = `/workspace/organizations/${company.id}/restaurants/${restaurantId}`;
  const context: RestaurantContext = {
    scope,
    company,
    restaurant: restaurant.data,
    data: workspace.data,
    basePath,
    queryKey,
  };
  return (
    <>
      <section className={styles.context} aria-label={t('business.context')}>
        <div className={styles.contextNames}>
          <span>
            <Building2 size={16} aria-hidden="true" />
            {localized(company.name)}
          </span>
          <span>
            <Store size={16} aria-hidden="true" />
            {localized(restaurant.data.name)}
          </span>
        </div>
        <div className={styles.actions}>
          <Badge>{t(`role.${company.role}`)}</Badge>
          <Button
            variant="quiet"
            disabled={workspace.isFetching}
            onClick={() => void workspace.refetch()}
          >
            {t('common.refresh')}
          </Button>
          <Link
            to={`/workspace/organizations/${company.id}/restaurants`}
            className={styles.textLink}
          >
            {t('business.changeRestaurant')}
          </Link>
        </div>
      </section>
      <nav className={styles.tabs} aria-label={t('restaurant.context')}>
        <NavLink to={basePath} end>
          {t('business.overview')}
        </NavLink>
        {company.permissions.includes('tenant.catalog.read') && (
          <NavLink to={`${basePath}/catalogue`}>{t('nav.catalogue')}</NavLink>
        )}
        {company.permissions.includes('tenant.orders.read') && (
          <NavLink to={`${basePath}/orders`}>{t('nav.orders')}</NavLink>
        )}
        {company.permissions.includes('tenant.agents.read') && (
          <>
            <NavLink to={`${basePath}/agents`}>{t('nav.agents')}</NavLink>
            <NavLink to={`${basePath}/channels`}>{t('nav.channels')}</NavLink>
          </>
        )}
        {company.permissions.includes('tenant.conversations.read') && (
          <NavLink to={`${basePath}/conversations`}>
            {t('nav.conversations')}
          </NavLink>
        )}
        {company.permissions.includes('tenant.reports.read') && (
          <NavLink to={`${basePath}/reports`}>{t('nav.reports')}</NavLink>
        )}
        {company.permissions.includes('tenant.billing.read') && (
          <NavLink to={`${basePath}/billing`}>{t('nav.billing')}</NavLink>
        )}
      </nav>
      <Outlet key={basePath} context={context} />
      <p className={styles.integrationNote}>{t('business.reviewOnly')}</p>
    </>
  );
}

/** Available only below the explicitly admitted restaurant frame. */
export function useRestaurantContext(): RestaurantContext {
  return useOutletContext<RestaurantContext>();
}

/** Stable, locale-aware amount/date presentation without recomputing order totals. */
export function useBusinessFormatting(): {
  money: (amount: number) => string;
  date: (value: string) => string;
} {
  const { i18n } = useTranslation();
  const locale =
    i18n.language === 'ar'
      ? 'ar-DZ'
      : i18n.language === 'en'
        ? 'en-DZ'
        : 'fr-DZ';
  return {
    money: (amount) =>
      new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: 'DZD',
      }).format(amount / 100),
    date: (value) =>
      new Intl.DateTimeFormat(locale, {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(value)),
  };
}

/** Shared empty state applies equally to filtered lists and unconfigured catalogues. */
export function EmptyResults({ clear }: { clear?: () => void }): ReactElement {
  const { t } = useTranslation();
  return (
    <section className={styles.empty}>
      <Store size={30} aria-hidden="true" />
      <h2>{t('business.noResults')}</h2>
      <p>{t('business.noResultsHelp')}</p>
      {clear && (
        <Button variant="secondary" onClick={clear}>
          {t('business.clearFilters')}
        </Button>
      )}
    </section>
  );
}
