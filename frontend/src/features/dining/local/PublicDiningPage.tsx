// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'react-router';
import { BrandCanvas } from '../../../shared/ui/BrandCanvas';
import {
  AppearanceControls,
  Brand,
  Button,
} from '../../../shared/ui/primitives';
import {
  PublicDiningClient,
  visitSecret,
  publicId,
  freshVisitSecret,
  type PublicMenu,
  type OwnVisit,
  type Verification,
} from '../../../shared/dining/local/publicClient';
import styles from './local.module.css';
import { LocalDiningClient } from '../../../shared/dining/local/client';
import { ownInvoice } from '../../../shared/dining/local/settlement';

/** Browser-only public reader: staff cookies never become a visitor's authority. */
function PublicDiningContent({
  operational = false,
}: {
  operational?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const api = useMemo(
    () => new PublicDiningClient(new LocalDiningClient(operational)),
    [operational],
  );
  const [menu, setMenu] = useState<PublicMenu | null>(null),
    [visit, setVisit] = useState<OwnVisit | null>(null),
    [verified, setVerified] = useState<Verification | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(false),
    [party, setParty] = useState(''),
    [currency, setCurrency] = useState('');
  const [cart, setCart] = useState<Record<number, string>>({});
  const [invoice, setInvoice] = useState<ReturnType<
    typeof ownInvoice.parse
  > | null>(null);
  const [invoiceError, setInvoiceError] = useState(false);
  const orderKey = useRef(freshVisitSecret()),
    locked = useRef(false);
  const verify = location.pathname === '/verify-document';
  const reference = location.hash.slice(1);
  const locale = ['fr', 'en', 'ar'].includes(i18n.language)
    ? (i18n.language as 'fr' | 'en' | 'ar')
    : 'fr';
  const load = async () => {
    publicId(reference);
    if (verify) {
      setVerified(await api.verify(reference));
      return;
    }
    const current = await api.menu(reference, currency || undefined);
    setMenu(current);
    const currentVisit = await api.visit(reference, visitSecret(reference));
    setVisit(currentVisit);
    setInvoice(null);
    setInvoiceError(false);
    if (operational && ['active', 'ended'].includes(currentVisit.status)) {
      try {
        setInvoice(
          ownInvoice.parse(
            await api.invoice(reference, visitSecret(reference)),
          ),
        );
      } catch {
        setInvoiceError(true);
      }
    }
  };
  const run = async (work: () => Promise<void>) => {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    setError(false);
    try {
      await work();
    } catch {
      setError(true);
      setMenu(null);
      setVisit(null);
      setVerified(null);
    } finally {
      locked.current = false;
      setBusy(false);
    }
  };
  useEffect(() => {
    const value = new URLSearchParams(location.search).get('locale');
    if (value && ['fr', 'en', 'ar'].includes(value))
      void i18n.changeLanguage(value);
    void run(load);
  }, [reference, verify, currency]);
  const entries =
    menu?.products
      .filter((row) => row.orderable && Number(cart[row.product_id]) > 0)
      .map((row) => ({
        product_id: row.product_id,
        quantity: Number(cart[row.product_id]),
      })) ?? [];
  return (
    <BrandCanvas>
      <main
        id="main-content"
        className={`${styles.page} ${styles.publicPage}`}
        style={{ maxWidth: 900, marginInline: 'auto' }}
      >
        <header className={styles.header}>
          <div className={styles.compactBrand}>
            <Brand />
          </div>
          <AppearanceControls />
        </header>
        <h1>{t(verify ? 'd1.documentVerify' : 'd1.publicMenu')}</h1>
        <p>
          {t(operational ? 'integration.publicNotice' : 'd1.publicLocalNotice')}
        </p>
        {error && <p role="alert">{t('d1.publicUnavailable')}</p>}
        <div className={styles.row}>
          <Button disabled={busy} onClick={() => void run(load)}>
            {t('d1.refresh')}
          </Button>
          {!verify && menu && (
            <label>
              {t('d1.currency')}
              <select
                aria-label={t('d1.currency')}
                value={menu.currency ?? ''}
                disabled={busy}
                onChange={(e) => {
                  setCurrency(e.target.value);
                  setMenu(null);
                  setVisit(null);
                  setCart({});
                  orderKey.current = freshVisitSecret();
                }}
              >
                <option value="">{t('d1.choose')}</option>
                {menu.currencies.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        {verified && (
          <section className={styles.card}>
            <h2>{t('d1.documentStatus_' + verified.status)}</h2>
            {verified.reference && (
              <p>
                <bdi>{verified.reference}</bdi> · {t('d1.documentVersion')}{' '}
                {verified.version}
              </p>
            )}
            <p>{t('d1.publicReadOnly')}</p>
          </section>
        )}
        {menu && (
          <>
            <section className={styles.card}>
              <h2>
                {menu.restaurant} · {menu.branch} · {t('d1.table')}{' '}
                {menu.table.code}
              </h2>
              <p>
                {[
                  menu.table.floor,
                  menu.table.room,
                  menu.table.zone[locale],
                  menu.table.location[locale],
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
              {menu.table.physical_state && (
                <p>
                  {t('d1.physicalNow')}:{' '}
                  {t('d1.state_' + menu.table.physical_state)}
                </p>
              )}
              <p>{t('d1.scanNoAuthority')}</p>
            </section>
            <section className={styles.grid} aria-label={t('d1.publicMenu')}>
              {menu.products.map((product) => (
                <article className={styles.card} key={product.product_id}>
                  <h3>{product.name}</h3>
                  <p>
                    {product.unit_price === null ? (
                      t(
                        menu.currency === null
                          ? 'd1.chooseMenuCurrency'
                          : 'd1.publicPriceMissing',
                      )
                    ) : (
                      <>
                        <bdi>
                          {product.unit_price} {menu.currency}
                        </bdi>
                      </>
                    )}
                  </p>
                  <label>
                    {t('d1.quantity')}
                    <input
                      aria-label={product.name + ' — ' + t('d1.quantity')}
                      type="number"
                      min={0}
                      max={100}
                      step={1}
                      value={cart[product.product_id] ?? '0'}
                      disabled={
                        busy || !product.orderable || visit?.status !== 'active'
                      }
                      onChange={(e) => {
                        setCart((current) => ({
                          ...current,
                          [product.product_id]: e.target.value,
                        }));
                        orderKey.current = freshVisitSecret();
                      }}
                    />
                  </label>
                </article>
              ))}
            </section>
            {visit && (
              <section className={styles.card}>
                <h2>{t('d1.visitStatus_' + visit.status)}</h2>
                {visit.status === 'not_signalled' && (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      void run(async () => {
                        await api.signal(
                          reference,
                          visitSecret(reference),
                          Number(party),
                        );
                        await load();
                      });
                    }}
                  >
                    <label>
                      {t('d1.partySize')}
                      <input
                        type="number"
                        min={1}
                        max={1000}
                        step={1}
                        required
                        value={party}
                        onChange={(e) => setParty(e.target.value)}
                      />
                    </label>
                    <Button type="submit" disabled={busy}>
                      {t('d1.signalPresence')}
                    </Button>
                  </form>
                )}
                {visit.status === 'active' && (
                  <Button
                    disabled={
                      busy ||
                      !entries.length ||
                      entries.some(
                        (row) =>
                          !Number.isInteger(row.quantity) ||
                          row.quantity < 1 ||
                          row.quantity > 100,
                      )
                    }
                    onClick={() =>
                      void run(async () => {
                        await api.order(
                          reference,
                          visitSecret(reference),
                          menu,
                          orderKey.current,
                          entries,
                        );
                        await load();
                        setCart({});
                        orderKey.current = freshVisitSecret();
                      })
                    }
                  >
                    {t('d1.requestFood')}
                  </Button>
                )}
                {visit.orders.map((order) => (
                  <article key={order.order_id}>
                    <h3>
                      #{order.order_id} — {t('d1.orderStatus_' + order.status)}
                    </h3>
                    <p>
                      <bdi>
                        {order.total} {order.currency}
                      </bdi>
                    </p>
                    <ul>
                      {order.lines.map((line) => (
                        <li key={line.order_item_id}>
                          {line.description} · {line.quantity}
                        </li>
                      ))}
                    </ul>
                  </article>
                ))}
              </section>
            )}
          </>
        )}
        {invoiceError && <p role="alert">{t('d1.invoiceUnavailable')}</p>}
        {invoice && 'balance' in invoice && (
          <section className={styles.card} data-testid="own-invoice">
            <h2>
              {t('d1.invoice')} #{invoice.invoice_id}
            </h2>
            <p>
              {t('d1.invoiceTotal')}:{' '}
              <bdi>
                {invoice.total} {invoice.currency}
              </bdi>
            </p>
            <p>
              {t('d1.advance')}:{' '}
              <bdi>
                {invoice.advance} {invoice.currency}
              </bdi>
            </p>
            <p>
              {t('d1.recordedPayment')}:{' '}
              <bdi>
                {invoice.paid} {invoice.currency}
              </bdi>
            </p>
            <p>
              {t('d1.balance')}:{' '}
              <bdi>
                {invoice.balance} {invoice.currency}
              </bdi>
            </p>
          </section>
        )}
      </main>
    </BrandCanvas>
  );
}

/** A changed public target discards the previous table's visible state and pending read results. */
export function PublicDiningPage() {
  const location = useLocation();
  return <PublicDiningContent key={location.pathname + location.hash} />;
}

/** Same public contract and visitor proof, routed through the integrated local origin. */
export function IntegratedPublicDiningPage() {
  const location = useLocation();
  return (
    <PublicDiningContent operational key={location.pathname + location.hash} />
  );
}
