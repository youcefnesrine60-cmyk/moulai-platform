// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useState, type ReactElement } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useTranslation } from 'react-i18next';
import { Link, NavLink, Outlet, useLocation, useParams } from 'react-router';
import {
  BookOpen,
  Building2,
  ChartNoAxesCombined,
  ChevronRight,
  ClipboardList,
  CreditCard,
  LayoutGrid,
  LogOut,
  Menu,
  MessagesSquare,
  ShieldCheck,
  Store,
  X,
} from 'lucide-react';
import {
  useAdapter,
  useLeaveReview,
  useOrganizations,
  useSession,
} from './access';
import { Brand, AppearanceControls } from '../shared/ui/primitives';
import styles from './shell.module.css';

/** Shared navigation with distinct platform and company affordances. */
export function Sidebar({
  platform,
  close,
}: {
  platform: boolean;
  close: () => void;
}): ReactElement {
  const { t } = useTranslation();
  const { organizationId, restaurantId } = useParams();
  const organizations = useOrganizations();
  const session = useSession();
  const current = organizations.data?.find(
    (row) => row.id === Number(organizationId),
  );
  const leave = useLeaveReview();
  const operations = [
    ['tenant.catalog.read', 'nav.catalogue', BookOpen],
    ['tenant.orders.read', 'nav.orders', ClipboardList],
    ['tenant.agents.read', 'nav.agents', MessagesSquare],
    ['tenant.agents.read', 'nav.channels', MessagesSquare],
    ['tenant.conversations.read', 'nav.conversations', MessagesSquare],
    ['tenant.reports.read', 'nav.reports', ChartNoAxesCombined],
    ['tenant.billing.read', 'nav.billing', CreditCard],
  ] as const;
  const platformOperations = [
    ['admins.manage', 'nav.requests', ClipboardList],
    ['payments.review', 'nav.receipts', CreditCard],
    ['admins.manage', 'nav.audit', ShieldCheck],
  ] as const;
  return (
    <div className={styles.sidebarInterior}>
      <div className={styles.areaLabel}>
        {t(platform ? 'nav.platformArea' : 'nav.tenantArea')}
      </div>
      <nav aria-label={t(platform ? 'nav.platformArea' : 'nav.tenantArea')}>
        <p className={styles.sectionLabel}>{t('nav.context')}</p>
        <NavLink
          to={platform ? '/platform' : '/workspace'}
          end
          className={({ isActive }) =>
            `${styles.navLink} ${isActive ? styles.navActive : ''}`
          }
          onClick={close}
        >
          <LayoutGrid size={19} aria-hidden="true" />
          {t(platform ? 'nav.platform' : 'nav.workspace')}
        </NavLink>
        {!platform && current && (
          <NavLink
            to={`/workspace/organizations/${current.id}/restaurants`}
            className={({ isActive }) =>
              `${styles.navLink} ${isActive ? styles.navActive : ''}`
            }
            onClick={close}
          >
            <Store size={19} aria-hidden="true" />
            {t('nav.restaurants')}
          </NavLink>
        )}
        {(platform || current) && (
          <p className={styles.sectionLabel}>{t('nav.management')}</p>
        )}
        {!platform &&
          operations
            .filter(([permission]) => current?.permissions.includes(permission))
            .map(([, label, Icon]) =>
              restaurantId &&
              (label === 'nav.catalogue' ||
                label === 'nav.orders' ||
                label === 'nav.agents' ||
                label === 'nav.channels' ||
                label === 'nav.conversations' ||
                label === 'nav.reports' ||
                label === 'nav.billing') ? (
                <NavLink
                  key={label}
                  to={`/workspace/organizations/${current?.id}/restaurants/${restaurantId}/${{ 'nav.catalogue': 'catalogue', 'nav.orders': 'orders', 'nav.agents': 'agents', 'nav.channels': 'channels', 'nav.conversations': 'conversations', 'nav.reports': 'reports', 'nav.billing': 'billing' }[label]}`}
                  className={({ isActive }) =>
                    `${styles.navLink} ${isActive ? styles.navActive : ''}`
                  }
                  onClick={close}
                >
                  <Icon size={18} aria-hidden="true" />
                  {t(label)}
                </NavLink>
              ) : (
                <div key={label} className={styles.unavailableItem}>
                  <Icon size={18} aria-hidden="true" />
                  <span>{t(label)}</span>
                  <small>{t('common.soon')}</small>
                </div>
              ),
            )}
        {platform &&
          platformOperations
            .filter(([permission]) =>
              session.data?.platformPermissions.includes(permission),
            )
            .map(([, label, Icon]) => (
              <NavLink
                key={label}
                to={`/platform/${label.split('.')[1]}`}
                className={({ isActive }) =>
                  `${styles.navLink} ${isActive ? styles.navActive : ''}`
                }
                onClick={close}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{t(label)}</span>
              </NavLink>
            ))}
      </nav>
      <div className={styles.sidebarBottom}>
        <p className={styles.scopeNote}>
          <ShieldCheck size={18} aria-hidden="true" />
          {t('nav.boundary')}
        </p>
        <button className={styles.signout} onClick={() => void leave()}>
          <LogOut size={18} aria-hidden="true" />
          {t('nav.signout')}
        </button>
      </div>
    </div>
  );
}

/** Radix handles focus trapping, escape, restoration and RTL drawer interaction. */
export function Shell({
  platform = false,
}: {
  platform?: boolean;
}): ReactElement {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const adapter = useAdapter();
  const atWorkspace = location.pathname === '/workspace';
  return (
    <div className={styles.frame}>
      <a className={styles.skip} href="#main-content">
        {t('nav.skip')}
      </a>
      <aside className={styles.desktopSidebar}>
        <Sidebar platform={platform} close={() => setOpen(false)} />
      </aside>
      <div className={styles.body}>
        {adapter.mode === 'synthetic' && (
          <div className={styles.reviewBanner}>{t('review.banner')}</div>
        )}
        <header className={styles.header}>
          <div className={styles.breadcrumb}>
            <Dialog.Root open={open} onOpenChange={setOpen}>
              <Dialog.Trigger
                className={styles.menuButton}
                aria-label={t('nav.menu')}
              >
                <Menu size={23} />
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className={styles.overlay} />
                <Dialog.Content className={styles.drawer}>
                  <Dialog.Title className="sr-only">
                    {t('nav.menuDescription')}
                  </Dialog.Title>
                  <Dialog.Description className="sr-only">
                    {t(platform ? 'nav.platformArea' : 'nav.tenantArea')}
                  </Dialog.Description>
                  <Dialog.Close
                    className={styles.closeButton}
                    aria-label={t('nav.close')}
                  >
                    <X size={21} />
                  </Dialog.Close>
                  <Sidebar platform={platform} close={() => setOpen(false)} />
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
            {platform ? (
              <ShieldCheck size={17} aria-hidden="true" />
            ) : (
              <Building2 size={17} aria-hidden="true" />
            )}
            <Link to={platform ? '/platform' : '/workspace'}>
              {t(platform ? 'nav.platformArea' : 'nav.tenantArea')}
            </Link>
            {!platform && (
              <>
                <ChevronRight
                  className="directional"
                  size={14}
                  aria-hidden="true"
                />
                <span>
                  {t(
                    atWorkspace
                      ? 'nav.workspace'
                      : location.pathname.includes('/catalogue')
                        ? 'nav.catalogue'
                        : location.pathname.includes('/orders')
                          ? 'nav.orders'
                          : location.pathname.includes('/agents')
                            ? 'nav.agents'
                            : location.pathname.includes('/channels')
                              ? 'nav.channels'
                              : location.pathname.includes('/conversations')
                                ? 'nav.conversations'
                                : location.pathname.includes('/reports')
                                  ? 'nav.reports'
                                  : location.pathname.includes('/billing')
                                    ? 'nav.billing'
                                    : 'nav.restaurants',
                  )}
                </span>
              </>
            )}
          </div>
          <Brand />
          <div className={styles.headerActions}>
            <AppearanceControls />
            <span
              className={styles.accountIcon}
              role="img"
              aria-label={t('nav.account')}
            >
              <ShieldCheck size={20} aria-hidden="true" />
            </span>
          </div>
        </header>
        <main id="main-content" className={styles.content} tabIndex={-1}>
          <Outlet />
        </main>
        <footer className={styles.footer}>
          <span dir="ltr">MoulAI™</span>
          <span>{t('access.privacy')}</span>
        </footer>
      </div>
    </div>
  );
}
