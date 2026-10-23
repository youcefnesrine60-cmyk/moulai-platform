// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { AccessError } from '../shared/access/contracts';
import type {
  ManagementAdapter,
  RestaurantScope,
  RestaurantWorkspace,
} from '../shared/business/contracts';
import {
  lockedOrderStatuses,
  ReviewConflict,
} from '../shared/business/contracts';
import {
  categorySchema,
  groupSchema,
  noteSchema,
  optionSchema,
  productSchema,
  profileSchema,
} from '../shared/business/validation';
import { restaurantFixture } from './restaurantFixtures';

/** Reuse the personal-grant authority supplied by the existing review adapter. */
export function createManagementAdapter(
  authorize: (scope: RestaurantScope, permission: string) => void,
  wait: (signal: AbortSignal) => Promise<void>,
): ManagementAdapter & {
  reset(): void;
  restaurantName(id: number): string | null;
} {
  const workspaces = new Map<number, RestaurantWorkspace>();
  const renamed = new Map<number, string>();
  let generation = 0;
  let nextId = 9900000;
  const get = (scope: RestaurantScope): RestaurantWorkspace => {
    const existing = workspaces.get(scope.restaurantId);
    if (existing) return existing;
    const created = restaurantFixture(scope.restaurantId);
    workspaces.set(scope.restaurantId, created);
    return created;
  };
  const ready = async (
    scope: RestaurantScope,
    signal: AbortSignal,
    permission: string,
  ): Promise<void> => {
    const started = generation;
    authorize(scope, permission);
    await wait(signal);
    if (started !== generation) throw new AccessError('noAccess');
    authorize(scope, permission);
  };
  return {
    reset() {
      generation += 1;
      workspaces.clear();
      renamed.clear();
      nextId = 9900000;
    },
    restaurantName(id) {
      return renamed.get(id) ?? null;
    },
    async workspace(scope, signal) {
      await ready(scope, signal, 'tenant.restaurants.read');
      authorize(scope, 'tenant.catalog.read');
      authorize(scope, 'tenant.orders.read');
      return structuredClone(get(scope));
    },
    async saveReview(scope, revision, command, signal) {
      const permission =
        command.kind === 'profile'
          ? 'tenant.restaurants.update'
          : command.kind === 'orderNote'
            ? 'tenant.orders.manage'
            : 'tenant.catalog.manage';
      await ready(scope, signal, permission);
      const before = get(scope);
      if (before.reviewRevision !== revision) throw new ReviewConflict();
      const requireRow = (present: boolean): void => {
        if (!present) throw new AccessError('notFound');
      };
      // Validate all references against this restaurant before mutating its snapshot.
      let after = before;
      switch (command.kind) {
        case 'profile':
          after = { ...before, profile: profileSchema.parse(command.value) };
          break;
        case 'category': {
          const value = categorySchema.parse(command.value);
          requireRow(
            command.id === null ||
              before.categories.some((row) => row.id === command.id),
          );
          after = {
            ...before,
            categories:
              command.id === null
                ? [...before.categories, { ...value, id: nextId++ }]
                : before.categories.map((row) =>
                    row.id === command.id ? { ...value, id: row.id } : row,
                  ),
          };
          break;
        }
        case 'product': {
          const value = productSchema.parse(command.value);
          if (command.id === null && !value.available)
            throw new AccessError('noAccess');
          requireRow(
            before.categories.some((row) => row.id === value.categoryId),
          );
          requireRow(
            command.id === null ||
              before.products.some((row) => row.id === command.id),
          );
          after = {
            ...before,
            products:
              command.id === null
                ? [...before.products, { ...value, id: nextId++ }]
                : before.products.map((row) =>
                    row.id === command.id ? { ...value, id: row.id } : row,
                  ),
          };
          break;
        }
        case 'group': {
          const value = groupSchema.parse(command.value);
          requireRow(before.products.some((row) => row.id === value.productId));
          requireRow(
            command.id === null ||
              before.groups.some(
                (row) =>
                  row.id === command.id && row.productId === value.productId,
              ),
          );
          after = {
            ...before,
            groups:
              command.id === null
                ? [...before.groups, { ...value, id: nextId++ }]
                : before.groups.map((row) =>
                    row.id === command.id ? { ...value, id: row.id } : row,
                  ),
          };
          break;
        }
        case 'option': {
          const value = optionSchema.parse(command.value);
          requireRow(before.groups.some((row) => row.id === value.groupId));
          requireRow(
            command.id === null ||
              before.options.some(
                (row) => row.id === command.id && row.groupId === value.groupId,
              ),
          );
          after = {
            ...before,
            options:
              command.id === null
                ? [...before.options, { ...value, id: nextId++ }]
                : before.options.map((row) =>
                    row.id === command.id ? { ...value, id: row.id } : row,
                  ),
          };
          break;
        }
        case 'orderNote': {
          const target = before.orders.find((row) => row.id === command.id);
          requireRow(Boolean(target));
          if (target && lockedOrderStatuses.includes(target.status))
            throw new AccessError('noAccess');
          const note = noteSchema.parse(command.note);
          after = {
            ...before,
            orders: before.orders.map((row) =>
              row.id === command.id ? { ...row, customerNote: note } : row,
            ),
          };
          break;
        }
        default:
          throw new AccessError('noAccess');
      }
      workspaces.set(scope.restaurantId, {
        ...after,
        reviewRevision: before.reviewRevision + 1,
      });
      if (command.kind === 'profile')
        renamed.set(scope.restaurantId, after.profile.name);
    },
  };
}
