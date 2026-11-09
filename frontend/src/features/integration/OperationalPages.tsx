// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — genuine authenticated projections; unconnected features stay explicitly unavailable.
import { useMemo } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAdapter, identityKey, useSession } from '../../app/access';
import { useSelection } from '../management/scope';
import { AccessError } from '../../shared/access/contracts';
import { localized } from '../../shared/i18n';
import { ErrorPanel, LoadingPanel } from '../../shared/ui/primitives';
import { webRequest } from '../../shared/access/operational';
import { LocalDiningClient } from '../../shared/dining/local/client';
import { PersonalInvitations } from '../dining/local/StaffForms';
import styles from '../management/management.module.css';

export function OperationalRestaurantFrame() {
  const { t } = useTranslation(),
    adapter = useAdapter(),
    session = useSession(),
    selection = useSelection(),
    location = useLocation();
  const query = useQuery({
    queryKey: [
      ...identityKey(session.data),
      selection.organizationId,
      selection.restaurantId,
      'operational-restaurant',
    ],
    queryFn: ({ signal }) =>
      adapter.restaurant(
        selection.organizationId ?? 0,
        selection.restaurantId ?? 0,
        signal,
      ),
    enabled: Boolean(selection.company && selection.restaurantId),
    retry: false,
  });
  if (selection.organizations.isPending) return <LoadingPanel />;
  if (selection.organizations.isError)
    return <ErrorPanel error={selection.organizations.error} />;
  if (!selection.company || !selection.restaurantId)
    return <ErrorPanel error={new AccessError('notFound')} />;
  if (query.isPending) return <LoadingPanel />;
  if (query.isError)
    return (
      <ErrorPanel error={query.error} retry={() => void query.refetch()} />
    );
  const root = `/workspace/organizations/${selection.company.id}/restaurants/${query.data.id}`;
  return (
    <>
      <section className={styles.context}>
        <strong>
          <bdi>{localized(selection.company.name)}</bdi> /{' '}
          <bdi>{localized(query.data.name)}</bdi>
        </strong>
        <span>{t('role.' + selection.company.role)}</span>
        <Link
          to={`/workspace/organizations/${selection.company.id}/restaurants`}
        >
          {t('business.changeRestaurant')}
        </Link>
      </section>
      <nav className={styles.tabs}>
        <NavLink to={root} end>
          {t('business.overview')}
        </NavLink>
        <NavLink to={root + '/tables'}>{t('dining.title')}</NavLink>
        {selection.company.permissions.includes('tenant.billing.read') && (
          <NavLink to={root + '/offer'}>{t('offer.title')}</NavLink>
        )}
        <Link to="/workspace/invitations">{t('integration.invitations')}</Link>
      </nav>
      {[root + '/tables', root + '/offer'].includes(location.pathname) ? (
        <Outlet key={root} />
      ) : (
        <section className={styles.context}>
          <h1>{t('integration.title')}</h1>
          <p>{t('integration.scope')}</p>
          <Link to={root + '/tables'}>{t('integration.openDining')}</Link>
        </section>
      )}
    </>
  );
}
export function OperationalPlatformPage() {
  const { t } = useTranslation(),
    session = useSession();
  const query = useQuery({
    queryKey: [...identityKey(session.data), 'platform-access'],
    queryFn: ({ signal }) => webRequest('/platform/access', signal),
    retry: false,
  });
  if (query.isPending) return <LoadingPanel />;
  if (query.isError) return <ErrorPanel error={query.error} />;
  return (
    <section className={styles.context}>
      <h1>{t('nav.platformArea')}</h1>
      <p>{t('integration.adminScope')}</p>
      <p>{t('integration.notice')}</p>
      {session.data?.platformPermissions.includes('payments.review') && (
        <p>
          <Link to="/platform/saas-payments">{t('o3.paymentReview')}</Link>
        </p>
      )}
      {session.data?.platformPermissions.includes(
        'subscriptions.pricing.manage',
      ) && <Link to="/platform/pricing">{t('pricing.campaigns')}</Link>}
      {session.data?.platformPermissions.includes(
        'tenant.billing_country.manage',
      ) && (
        <p>
          <Link to="/platform/billing-countries">{t('o3.reviewTitle')}</Link>
        </p>
      )}
    </section>
  );
}
export function OperationalInvitationsPage() {
  const { t } = useTranslation();
  const client = useMemo(() => new LocalDiningClient(true), []);
  return (
    <>
      <h1>{t('integration.invitations')}</h1>
      <PersonalInvitations api={client} />
    </>
  );
}
