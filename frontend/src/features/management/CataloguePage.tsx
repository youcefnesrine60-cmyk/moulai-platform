// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useState, type ReactElement } from 'react';
import { useTranslation } from 'react-i18next';
import { BookOpen, Plus } from 'lucide-react';
import { AccessError } from '../../shared/access/contracts';
import { Badge, Button, ErrorPanel } from '../../shared/ui/primitives';
import { ReviewEditor, type EditorSelection } from './ReviewEditor';
import {
  EmptyResults,
  useBusinessFormatting,
  useRestaurantContext,
} from './scope';
import styles from './management.module.css';

type CatalogueSection = 'products' | 'categories' | 'options';

/** Existing categories/products/options contracts projected through one scoped adapter. */
export function CataloguePage(): ReactElement {
  const { t } = useTranslation();
  const { data, company } = useRestaurantContext();
  const { money } = useBusinessFormatting();
  const [section, setSection] = useState<CatalogueSection>('products');
  const [category, setCategory] = useState('all');
  const [product, setProduct] = useState('all');
  const [search, setSearch] = useState('');
  const [availability, setAvailability] = useState('all');
  const [editor, setEditor] = useState<EditorSelection | null>(null);
  const [saved, setSaved] = useState(false);
  if (!company.permissions.includes('tenant.catalog.read'))
    return <ErrorPanel error={new AccessError('noAccess')} />;
  const editable = company.permissions.includes('tenant.catalog.manage');
  const sortedCategories = [...data.categories].sort(
    (a, b) => a.sortOrder - b.sortOrder || a.id - b.id,
  );
  const products = [...data.products]
    .filter(
      (row) =>
        (category === 'all' || row.categoryId === Number(category)) &&
        row.name
          .toLocaleLowerCase()
          .includes(search.trim().toLocaleLowerCase()) &&
        (availability === 'all' ||
          row.available === (availability === 'available')),
    )
    .sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id);
  const groups = [...data.groups]
    .filter((row) => product === 'all' || row.productId === Number(product))
    .sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id);
  const edit = (selection: EditorSelection): void => {
    setSaved(false);
    setEditor(selection);
  };
  const clear = (): void => {
    setSearch('');
    setCategory('all');
    setAvailability('all');
    setProduct('all');
  };
  return (
    <>
      <div className={styles.titleRow}>
        <div>
          <p className="eyebrow">{t('nav.catalogue')}</p>
          <h1>{t('business.catalogue')}</h1>
          <p className={styles.intro}>{t('business.catalogueIntro')}</p>
        </div>
        <Badge tone="test">{t('review.badge')}</Badge>
      </div>
      {!editable && <p className={styles.notice}>{t('business.readOnly')}</p>}
      {saved && (
        <p role="status" className={styles.success}>
          {t('business.saved')}
        </p>
      )}
      <div
        className={styles.subnav}
        role="group"
        aria-label={t('nav.catalogue')}
      >
        {(['products', 'categories', 'options'] as const).map((value) => (
          <button
            key={value}
            aria-pressed={section === value}
            onClick={() => setSection(value)}
          >
            {t(`business.${value}`)}
          </button>
        ))}
      </div>
      {section === 'products' && (
        <>
          <div className={styles.toolbar}>
            <label className={styles.field}>
              {t('business.search')}
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                maxLength={255}
              />
            </label>
            <label className={styles.field}>
              {t('business.category')}
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
              >
                <option value="all">{t('business.allCategories')}</option>
                {sortedCategories.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
            <label className={styles.field}>
              {t('business.available')}
              <select
                value={availability}
                onChange={(event) => setAvailability(event.target.value)}
              >
                <option value="all">{t('business.allProducts')}</option>
                <option value="available">{t('business.available')}</option>
                <option value="unavailable">{t('business.unavailable')}</option>
              </select>
            </label>
            {editable && (
              <Button
                onClick={() => edit({ kind: 'product', id: null })}
                disabled={data.categories.length === 0}
              >
                <Plus size={16} aria-hidden="true" />
                {t('business.addProduct')}
              </Button>
            )}
          </div>
          {editable && !data.categories.length && (
            <p className={styles.notice}>{t('business.noCategories')}</p>
          )}
          <p className={styles.muted} role="status">
            {t('business.results', { count: products.length })}
          </p>
          {products.length === 0 ? (
            <EmptyResults clear={clear} />
          ) : (
            <div className={styles.products}>
              {products.map((row) => (
                <article className={styles.panel} key={row.id}>
                  <div className={styles.productVisual}>
                    <BookOpen size={30} strokeWidth={1.2} aria-hidden="true" />
                    <Badge tone={row.available ? 'green' : 'neutral'}>
                      {t(
                        row.available
                          ? 'business.available'
                          : 'business.unavailable',
                      )}
                    </Badge>
                  </div>
                  <p className={styles.muted}>
                    {
                      data.categories.find((item) => item.id === row.categoryId)
                        ?.name
                    }
                  </p>
                  <h2 className={styles.productTitle}>{row.name}</h2>
                  {row.description && (
                    <p className={styles.muted}>{row.description}</p>
                  )}
                  <div className={styles.cardBottom}>
                    <bdi className={styles.price}>{money(row.price)}</bdi>
                    {editable && (
                      <Button
                        variant="secondary"
                        aria-label={`${t('business.editProduct')} · ${row.name}`}
                        onClick={() => edit({ kind: 'product', id: row.id })}
                      >
                        {t('business.edit')}
                      </Button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
          <p className={styles.muted}>{t('business.editAvailability')}</p>
        </>
      )}
      {section === 'categories' && (
        <>
          <div className={styles.titleRow}>
            <h2>{t('business.categories')}</h2>
            {editable && (
              <Button onClick={() => edit({ kind: 'category', id: null })}>
                <Plus size={16} aria-hidden="true" />
                {t('business.addCategory')}
              </Button>
            )}
          </div>
          {sortedCategories.length === 0 ? (
            <EmptyResults />
          ) : (
            <section className={styles.panel}>
              {sortedCategories.map((row) => (
                <div className={styles.row} key={row.id}>
                  <div>
                    <h3 className={styles.productTitle}>{row.name}</h3>
                    <p className={styles.muted}>
                      {t('business.sortOrder')} · {row.sortOrder}
                    </p>
                  </div>
                  {editable && (
                    <Button
                      variant="secondary"
                      aria-label={`${t('business.editCategory')} · ${row.name}`}
                      onClick={() => edit({ kind: 'category', id: row.id })}
                    >
                      {t('business.edit')}
                    </Button>
                  )}
                </div>
              ))}
            </section>
          )}
        </>
      )}
      {section === 'options' && (
        <>
          <div className={styles.toolbar}>
            <label className={styles.field}>
              {t('business.product')}
              <select
                value={product}
                onChange={(event) => setProduct(event.target.value)}
              >
                <option value="all">{t('business.allProducts')}</option>
                {data.products.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
            {editable && (
              <Button
                disabled={!data.products.length}
                onClick={() =>
                  edit({
                    kind: 'group',
                    id: null,
                    ...(product !== 'all' ? { parentId: Number(product) } : {}),
                  })
                }
              >
                <Plus size={16} aria-hidden="true" />
                {t('business.addGroup')}
              </Button>
            )}
          </div>
          {editable && !data.products.length && (
            <p className={styles.notice}>{t('business.noProducts')}</p>
          )}
          {groups.length === 0 ? (
            <EmptyResults clear={clear} />
          ) : (
            <div className={styles.stack}>
              {groups.map((group) => (
                <section className={styles.panel} key={group.id}>
                  <div className={styles.titleRow}>
                    <div>
                      <p className={styles.muted}>
                        {
                          data.products.find(
                            (row) => row.id === group.productId,
                          )?.name
                        }
                      </p>
                      <h2>{group.name}</h2>
                      <div className={styles.actions}>
                        <Badge>
                          {t(
                            group.required
                              ? 'business.required'
                              : 'business.optional',
                          )}
                        </Badge>
                        <Badge>
                          {t(
                            group.multipleChoice
                              ? 'business.multiple'
                              : 'business.single',
                          )}
                        </Badge>
                      </div>
                    </div>
                    {editable && (
                      <div className={styles.actions}>
                        <Button
                          variant="secondary"
                          aria-label={`${t('business.editGroup')} · ${group.name}`}
                          onClick={() => edit({ kind: 'group', id: group.id })}
                        >
                          {t('business.edit')}
                        </Button>
                        <Button
                          variant="secondary"
                          aria-label={`${t('business.addOption')} · ${group.name}`}
                          onClick={() =>
                            edit({
                              kind: 'option',
                              id: null,
                              parentId: group.id,
                            })
                          }
                        >
                          {t('business.addOption')}
                        </Button>
                      </div>
                    )}
                  </div>
                  {!data.options.some((row) => row.groupId === group.id) && (
                    <p className={styles.muted}>{t('business.noOptions')}</p>
                  )}
                  {[...data.options]
                    .filter((row) => row.groupId === group.id)
                    .sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id)
                    .map((option) => (
                      <div key={option.id} className={styles.row}>
                        <div>
                          <p>{option.name}</p>
                          <p className={styles.muted}>
                            <bdi>{money(option.extraPrice)}</bdi> ·{' '}
                            {t(
                              option.available
                                ? 'business.available'
                                : 'business.unavailable',
                            )}
                          </p>
                        </div>
                        {editable && (
                          <Button
                            variant="secondary"
                            aria-label={`${t('business.editOption')} · ${option.name}`}
                            onClick={() =>
                              edit({ kind: 'option', id: option.id })
                            }
                          >
                            {t('business.edit')}
                          </Button>
                        )}
                      </div>
                    ))}
                </section>
              ))}
            </div>
          )}
        </>
      )}
      {editor && (
        <ReviewEditor
          selection={editor}
          close={() => setEditor(null)}
          saved={() => setSaved(true)}
        />
      )}
    </>
  );
}
