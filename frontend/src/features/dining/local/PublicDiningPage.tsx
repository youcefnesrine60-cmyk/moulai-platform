// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'react-router';
import { flushSync } from 'react-dom';
import { InvoiceDocument } from './InvoiceDocument';
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
import { cartSubtotal } from '../../../shared/dining/cartPresentation';
import { ExactAmount } from '../../../shared/ui/ExactAmount';
import {
  useUnsavedChanges,
  useViewChange,
} from '../../../shared/ui/UnsavedChanges';

/** Browser-only public reader: staff cookies never become a visitor's authority. */
function PublicDiningContent({
  operational: requestedOperational = false,
}: {
  operational?: boolean;
}) {
  const operational =
    import.meta.env.MODE === 'staging' || requestedOperational;
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
            await api.invoice(reference, visitSecret(reference), locale),
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
  }, [reference, verify, currency, locale]);
  /** Re-read validity and settlement facts before printing; never replay a business operation. */
  const printInvoice = async () => {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    setInvoiceError(false);
    try {
      const current = ownInvoice.parse(
        await api.invoice(reference, visitSecret(reference), locale),
      );
      flushSync(() => setInvoice(current));
      if ('balance' in current) window.print();
      else setInvoiceError(true);
    } catch {
      setInvoiceError(true);
    } finally {
      locked.current = false;
      setBusy(false);
    }
  };
  const entries =
    menu?.products
      .filter((row) => row.orderable && Number(cart[row.product_id]) > 0)
      .map((row) => ({
        product_id: row.product_id,
        quantity: Number(cart[row.product_id]),
      })) ?? [];
  const subtotal = menu ? cartSubtotal(menu, cart) : null;
  useUnsavedChanges(Object.values(cart).some((value) => Number(value) !== 0));
  const changeView = useViewChange();
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
        <section className={styles.card}>
          <h1>{t(verify ? 'd1.documentVerify' : 'd1.publicMenu')}</h1>
          <p>
            {t(
              operational ? 'integration.publicNotice' : 'd1.publicLocalNotice',
            )}
          </p>
          {busy && <p role="status">{t('quality.processing')}</p>}
          {error && (
            <p role="alert">
              {t('d1.publicUnavailable')} {t('quality.uncertain')}
            </p>
          )}
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
                    const next = e.target.value;
                    changeView(() => {
                      setCurrency(next);
                      setMenu(null);
                      setVisit(null);
                      setCart({});
                      orderKey.current = freshVisitSecret();
                    });
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
        </section>
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
                  <section
                    aria-label={t('quality.cart')}
                    className={styles.card}
                  >
                    <h3>{t('quality.cart')}</h3>
                    <p>{t('quality.cartReview')}</p>
                    <ul>
                      {entries.map((entry) => (
                        <li key={entry.product_id}>
                          {
                            menu.products.find(
                              (product) =>
                                product.product_id === entry.product_id,
                            )?.name
                          }{' '}
                          · {entry.quantity}
                        </li>
                      ))}
                    </ul>
                    {subtotal !== null && (
                      <p>
                        {t('quality.subtotal')}:{' '}
                        <ExactAmount
                          value={subtotal}
                          currency={menu.currency}
                        />
                      </p>
                    )}
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
                  </section>
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
        {invoiceError && (
          <p role="alert" className={`${styles.banner} ${styles.error}`}>
            {t('d1.invoiceUnavailable')}
          </p>
        )}
        {invoice && 'balance' in invoice && (
          <section
            className={styles.card}
            data-testid="own-invoice"
            data-print-invoice
          >
            <img
              className={styles.printBrand}
              src="/brand/moulai-logo-light01.png"
              alt="MoulAI™"
              width={2172}
              height={724}
              loading="lazy"
            />
            <h2>
              {t('d1.invoice')} <bdi dir="ltr">#{invoice.invoice_id}</bdi>
            </h2>
            <p>{t('quality.syntheticDocument')}</p>
            {menu && (
              <p>
                <bdi>{menu.restaurant}</bdi> · <bdi>{menu.branch}</bdi> ·{' '}
                {t('d1.table')} <bdi>{menu.table.code}</bdi>
              </p>
            )}
            {invoice.finalized_at && (
              <p>
                {t('quality.finalizedAt')}:{' '}
                <bdi>
                  <time dateTime={invoice.finalized_at}>
                    {new Date(invoice.finalized_at).toLocaleString(
                      i18n.language,
                      { timeZone: 'UTC' },
                    )}
                  </time>
                </bdi>
              </p>
            )}
            {invoice.lines && (
              <div
                className={styles.invoiceLines}
                role="region"
                aria-label={t('d1.invoice')}
                tabIndex={0}
              >
                <table>
                  <caption>{t('documents.lines')}</caption>
                  <thead>
                    <tr>
                      {[
                        'd1.description',
                        'd1.quantity',
                        'quality.unitPrice',
                        'd1.amount',
                      ].map((key) => (
                        <th scope="col" key={key}>
                          {t(key)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {invoice.lines.map((line, index) => (
                      <tr key={index}>
                        <td>{line.description}</td>
                        <td>
                          <ExactAmount value={line.quantity} />
                        </td>
                        <td>
                          <ExactAmount
                            value={line.unit_price}
                            currency={invoice.currency}
                          />
                        </td>
                        <td>
                          <ExactAmount
                            value={line.amount}
                            currency={invoice.currency}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p>
              {t('d1.invoiceTotal')}:{' '}
              <ExactAmount value={invoice.total} currency={invoice.currency} />
            </p>
            <section
              aria-label={t('documents.settlement')}
              className={styles.settlementSummary}
            >
              <h3>{t('documents.settlement')}</h3>
              <p>{t('documents.frozenHelp')}</p>
              {invoice.settlement_as_of && (
                <p>
                  {t('documents.consultedAt')}:{' '}
                  <bdi>
                    <time dateTime={invoice.settlement_as_of}>
                      {new Date(invoice.settlement_as_of).toLocaleString(
                        i18n.language,
                        { timeZone: 'UTC' },
                      )}
                    </time>
                  </bdi>
                </p>
              )}
              <p>
                {t('d1.advance')}:{' '}
                <ExactAmount
                  value={invoice.advance}
                  currency={invoice.currency}
                />
              </p>
              <p>
                {t('d1.recordedPayment')}:{' '}
                <ExactAmount value={invoice.paid} currency={invoice.currency} />
              </p>
              <p>
                {t('d1.balance')}:{' '}
                <ExactAmount
                  value={invoice.balance}
                  currency={invoice.currency}
                />
              </p>
            </section>
            <InvoiceDocument document={invoice.document} />
            <Button
              type="button"
              variant="secondary"
              disabled={busy}
              onClick={() => void printInvoice()}
              data-print-control
            >
              {t(
                invoice.lines && invoice.finalized_at
                  ? 'quality.printDetailedInvoice'
                  : 'quality.printInvoice',
              )}
            </Button>
            {(!invoice.lines || !invoice.finalized_at) && (
              <p>{t('quality.invoiceSummary')}</p>
            )}
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
