// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useEffect, useId, useRef, useState, type ReactElement } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAdapter } from '../../app/access';
import {
  ReviewConflict,
  type RestaurantWorkspace,
  type ReviewCommand,
} from '../../shared/business/contracts';
import {
  categorySchema,
  groupSchema,
  noteSchema,
  optionSchema,
  parsePrice,
  priceInput,
  productSchema,
  profileSchema,
} from '../../shared/business/validation';
import { AppearanceControls, Button } from '../../shared/ui/primitives';
import { useRestaurantContext } from './scope';
import styles from './management.module.css';

export interface EditorSelection {
  readonly kind: ReviewCommand['kind'];
  readonly id: number | null;
  readonly parentId?: number;
}
const draftSchema = z.object({
  name: z.string(),
  description: z.string(),
  price: z.string(),
  categoryId: z.string(),
  productId: z.string(),
  groupId: z.string(),
  required: z.boolean(),
  multipleChoice: z.boolean(),
  available: z.boolean(),
  sortOrder: z.string(),
  phone: z.string(),
  type: z.string(),
  wilaya: z.string(),
  note: z.string(),
});
type Draft = z.infer<typeof draftSchema>;

/** Draft conversion is shared by validation and confirmation, never by network code. */
export function commandFromDraft(
  selection: EditorSelection,
  draft: Draft,
): ReviewCommand {
  const { kind, id } = selection;
  const sortOrder =
    draft.sortOrder.trim() === '' ? NaN : Number(draft.sortOrder);
  const price = parsePrice(draft.price, kind === 'option');
  if ((kind === 'product' || kind === 'option') && price === null)
    throw new z.ZodError([
      { code: 'custom', path: ['price'], message: 'Invalid decimal' },
    ]);
  switch (kind) {
    case 'profile':
      return {
        kind,
        value: profileSchema.parse({
          name: draft.name,
          type: draft.type,
          phone: draft.phone,
          wilaya: draft.wilaya,
        }),
      };
    case 'category':
      return {
        kind,
        id,
        value: categorySchema.parse({ name: draft.name, sortOrder }),
      };
    case 'product':
      return {
        kind,
        id,
        value: productSchema.parse({
          name: draft.name,
          description: draft.description,
          categoryId: Number(draft.categoryId),
          price,
          available: draft.available,
          sortOrder,
        }),
      };
    case 'group':
      return {
        kind,
        id,
        value: groupSchema.parse({
          name: draft.name,
          productId: Number(draft.productId),
          required: draft.required,
          multipleChoice: draft.multipleChoice,
          sortOrder,
        }),
      };
    case 'option':
      return {
        kind,
        id,
        value: optionSchema.parse({
          name: draft.name,
          groupId: Number(draft.groupId),
          extraPrice: price,
          available: draft.available,
          sortOrder,
        }),
      };
    case 'orderNote':
      if (id === null) throw new Error('Order selection required');
      return { kind, id, note: noteSchema.parse(draft.note) };
  }
}

/** Initialize fields from the selected, restaurant-scoped snapshot only. */
function initialDraft(
  selection: EditorSelection,
  data: RestaurantWorkspace,
): Draft {
  const values: Draft = {
    name: '',
    description: '',
    price: '',
    categoryId: String(data.categories[0]?.id ?? ''),
    productId: String(selection.parentId ?? data.products[0]?.id ?? ''),
    groupId: String(selection.parentId ?? ''),
    required: false,
    multipleChoice: false,
    available: true,
    sortOrder: '0',
    phone: '',
    type: 'restaurant',
    wilaya: '',
    note: '',
  };
  const id = selection.id;
  switch (selection.kind) {
    case 'profile':
      return { ...values, ...data.profile };
    case 'category': {
      const row = data.categories.find((item) => item.id === id);
      return row
        ? { ...values, name: row.name, sortOrder: String(row.sortOrder) }
        : values;
    }
    case 'product': {
      const row = data.products.find((item) => item.id === id);
      return row
        ? {
            ...values,
            name: row.name,
            description: row.description,
            price: priceInput(row.price),
            categoryId: String(row.categoryId),
            available: row.available,
            sortOrder: String(row.sortOrder),
          }
        : values;
    }
    case 'group': {
      const row = data.groups.find((item) => item.id === id);
      return row
        ? {
            ...values,
            name: row.name,
            productId: String(row.productId),
            required: row.required,
            multipleChoice: row.multipleChoice,
            sortOrder: String(row.sortOrder),
          }
        : values;
    }
    case 'option': {
      const row = data.options.find((item) => item.id === id);
      return row
        ? {
            ...values,
            name: row.name,
            groupId: String(row.groupId),
            price: priceInput(row.extraPrice),
            available: row.available,
            sortOrder: String(row.sortOrder),
          }
        : { ...values, price: '0.00' };
    }
    case 'orderNote':
      return {
        ...values,
        note: data.orders.find((row) => row.id === id)?.customerNote ?? '',
      };
  }
}

/** One accessible edit/confirm dialog for all existing-contract review operations. */
export function ReviewEditor({
  selection,
  close,
  saved,
}: {
  selection: EditorSelection;
  close: () => void;
  saved: () => void;
}): ReactElement {
  const { t } = useTranslation();
  const { data, scope, queryKey } = useRestaurantContext();
  const adapter = useAdapter();
  const client = useQueryClient();
  const [revision] = useState(data.reviewRevision);
  const [confirmation, setConfirmation] = useState<ReviewCommand | null>(null);
  const originFocus = useRef(document.activeElement);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  const fieldPrefix = useId();
  const validation = draftSchema.superRefine((value, context) => {
    try {
      commandFromDraft(selection, value);
    } catch (error) {
      if (error instanceof z.ZodError)
        for (const issue of error.issues)
          context.addIssue({
            code: 'custom',
            path: issue.path.length ? issue.path : ['note'],
            message: 'business.invalid',
          });
      else
        context.addIssue({
          code: 'custom',
          path: ['note'],
          message: 'business.invalid',
        });
    }
  });
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Draft>({
    defaultValues: initialDraft(selection, data),
    resolver: zodResolver(validation),
    shouldFocusError: true,
  });
  const mutation = useMutation({
    mutationFn: async (command: ReviewCommand) => {
      const controller = new AbortController();
      request.current = controller;
      try {
        await adapter.saveReview(scope, revision, command, controller.signal);
      } finally {
        request.current = null;
      }
    },
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey });
      if (selection.kind === 'profile')
        await client.invalidateQueries({ queryKey: queryKey.slice(0, 4) });
      saved();
      close();
    },
  });
  const titleKey =
    selection.kind === 'profile'
      ? 'business.editProfile'
      : selection.kind === 'orderNote'
        ? 'business.editNote'
        : `business.${selection.id === null ? 'add' : 'edit'}${selection.kind[0]?.toUpperCase()}${selection.kind.slice(1)}`;
  const labels: Record<keyof Draft, string> = {
    name: 'business.name',
    description: 'business.description',
    price:
      selection.kind === 'option' ? 'business.extraPrice' : 'business.price',
    categoryId: 'business.category',
    productId: 'business.product',
    groupId: 'business.group',
    required: 'business.required',
    multipleChoice: 'business.multiple',
    available: 'business.available',
    sortOrder: 'business.sortOrder',
    phone: 'business.phone',
    type: 'business.type',
    wilaya: 'business.wilaya',
    note: 'business.note',
  };
  const input = (
    field: keyof Draft,
    type = 'text',
    maxLength?: number,
  ): ReactElement => (
    <label className={styles.field} key={field}>
      <span id={`${fieldPrefix}-${field}-label`}>{t(labels[field])}</span>
      <input
        {...register(field)}
        type={type}
        {...(maxLength ? { maxLength } : {})}
        inputMode={
          field === 'price'
            ? 'decimal'
            : field === 'sortOrder'
              ? 'numeric'
              : undefined
        }
        aria-labelledby={`${fieldPrefix}-${field}-label`}
        aria-invalid={Boolean(errors[field])}
        aria-describedby={errors[field] ? `${fieldPrefix}-${field}` : undefined}
        dir={field === 'price' || field === 'phone' ? 'ltr' : undefined}
      />
      {errors[field] && (
        <span id={`${fieldPrefix}-${field}`} className={styles.fieldError}>
          {t('business.invalid')}
        </span>
      )}
    </label>
  );
  const select = (
    field: 'categoryId' | 'productId' | 'type',
    options: readonly { id: string; name: string }[],
    disabled = false,
  ): ReactElement => (
    <label className={styles.field}>
      <span id={`${fieldPrefix}-${field}-label`}>{t(labels[field])}</span>
      <select
        {...register(field)}
        disabled={disabled}
        aria-labelledby={`${fieldPrefix}-${field}-label`}
        aria-invalid={Boolean(errors[field])}
        aria-describedby={errors[field] ? `${fieldPrefix}-${field}` : undefined}
      >
        {options.map((row) => (
          <option key={row.id} value={row.id}>
            {row.name}
          </option>
        ))}
      </select>
      {errors[field] && (
        <span id={`${fieldPrefix}-${field}`} className={styles.fieldError}>
          {t('business.invalid')}
        </span>
      )}
    </label>
  );
  const check = (
    field: 'required' | 'multipleChoice' | 'available',
  ): ReactElement => (
    <label className={styles.check}>
      <input type="checkbox" {...register(field)} />
      {t(labels[field])}
    </label>
  );
  const textarea = (
    field: 'description' | 'note',
    maxLength: number,
  ): ReactElement => (
    <label className={styles.field}>
      <span id={`${fieldPrefix}-${field}-label`}>{t(labels[field])}</span>
      <textarea
        {...register(field)}
        maxLength={maxLength}
        rows={4}
        aria-labelledby={`${fieldPrefix}-${field}-label`}
        aria-invalid={Boolean(errors[field])}
        aria-describedby={errors[field] ? `${fieldPrefix}-${field}` : undefined}
      />
      {errors[field] && (
        <span id={`${fieldPrefix}-${field}`} className={styles.fieldError}>
          {t('business.invalid')}
        </span>
      )}
    </label>
  );
  const showValue = (
    field: string,
    value: string | number | boolean,
  ): string => {
    if (typeof value === 'boolean')
      return t(value ? 'business.yes' : 'business.no');
    if (field === 'price' || field === 'extraPrice')
      return `${priceInput(Number(value))} DZD`;
    if (field === 'categoryId')
      return (
        data.categories.find((row) => row.id === value)?.name ??
        t('business.emptyValue')
      );
    if (field === 'productId')
      return (
        data.products.find((row) => row.id === value)?.name ??
        t('business.emptyValue')
      );
    if (field === 'groupId')
      return (
        data.groups.find((row) => row.id === value)?.name ??
        t('business.emptyValue')
      );
    if (field === 'type') return t(`business.establishment.${value}`);
    return String(value) || t('business.emptyValue');
  };
  const confirmationValues = confirmation
    ? confirmation.kind === 'orderNote'
      ? { note: confirmation.note }
      : confirmation.value
    : {};
  return (
    <Dialog.Root
      open
      onOpenChange={(open) => {
        if (!open && !mutation.isPending) close();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content
          className={styles.dialog}
          onEscapeKeyDown={(event) => {
            if (mutation.isPending) event.preventDefault();
          }}
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            if (
              originFocus.current instanceof HTMLElement &&
              originFocus.current.isConnected
            )
              originFocus.current.focus();
          }}
        >
          <Dialog.Title>
            {t(confirmation ? 'business.confirmTitle' : titleKey)}
          </Dialog.Title>
          <Dialog.Description className={styles.dialogDescription}>
            {t(confirmation ? 'business.confirmHelp' : 'business.reviewOnly')}
          </Dialog.Description>
          <div className={styles.dialogPreferences}>
            <AppearanceControls />
          </div>
          <Dialog.Close
            className={styles.dialogClose}
            disabled={mutation.isPending}
            aria-label={t('business.close')}
          >
            <X size={20} aria-hidden="true" />
          </Dialog.Close>
          {mutation.isError && (
            <p role="alert" className={styles.fieldError}>
              {t(
                mutation.error instanceof ReviewConflict
                  ? 'business.conflict'
                  : 'business.saveError',
              )}
            </p>
          )}
          {confirmation ? (
            <>
              <p className={styles.notice}>{data.profile.name}</p>
              <dl className={`${styles.definition} ${styles.confirmation}`}>
                {Object.entries(confirmationValues).map(([field, value]) => (
                  <div key={field} style={{ display: 'contents' }}>
                    <dt>
                      {t(
                        field === 'extraPrice'
                          ? 'business.extraPrice'
                          : (labels[field as keyof Draft] ??
                              `business.${field}`),
                      )}
                    </dt>
                    <dd>{showValue(field, value)}</dd>
                  </div>
                ))}
              </dl>
              <div className={styles.formActions}>
                <Button
                  variant="secondary"
                  disabled={mutation.isPending}
                  onClick={() => {
                    mutation.reset();
                    setConfirmation(null);
                  }}
                >
                  {t('business.backEdit')}
                </Button>
                <Button
                  disabled={mutation.isPending || mutation.isError}
                  onClick={() => mutation.mutate(confirmation)}
                >
                  {t(mutation.isPending ? 'business.saving' : 'business.apply')}
                </Button>
              </div>
            </>
          ) : (
            <form
              className={styles.form}
              noValidate
              onSubmit={handleSubmit((value) =>
                setConfirmation(commandFromDraft(selection, value)),
              )}
            >
              {selection.kind !== 'orderNote' && input('name', 'text', 255)}
              {selection.kind === 'profile' && (
                <>
                  {select(
                    'type',
                    [
                      'restaurant',
                      'cafe',
                      'fast_food',
                      'bakery',
                      'pizza',
                      'other',
                    ].map((id) => ({
                      id,
                      name: t(`business.establishment.${id}`),
                    })),
                  )}
                  {input('phone', 'tel', 20)}
                  {input('wilaya', 'text', 100)}
                </>
              )}
              {selection.kind === 'product' && (
                <>
                  {select(
                    'categoryId',
                    data.categories.map((row) => ({
                      id: String(row.id),
                      name: row.name,
                    })),
                  )}
                  {textarea('description', 5000)}
                </>
              )}
              {selection.kind === 'group' && (
                <>
                  {select(
                    'productId',
                    data.products.map((row) => ({
                      id: String(row.id),
                      name: row.name,
                    })),
                    selection.id !== null,
                  )}
                  {check('required')}
                  {check('multipleChoice')}
                </>
              )}
              {(selection.kind === 'product' ||
                selection.kind === 'option') && (
                <>
                  {input('price')}
                  <p className={styles.fieldHelp}>{t('business.priceHelp')}</p>
                  {(selection.kind === 'option' || selection.id !== null) &&
                    check('available')}
                </>
              )}
              {selection.kind !== 'profile' &&
                selection.kind !== 'orderNote' &&
                input('sortOrder', 'number')}
              {selection.kind === 'orderNote' && textarea('note', 2000)}
              <div className={styles.formActions}>
                <Button type="button" variant="secondary" onClick={close}>
                  {t('business.cancel')}
                </Button>
                <Button type="submit">{t('business.confirm')}</Button>
              </div>
            </form>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
