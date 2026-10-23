// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { Order, RestaurantWorkspace } from '../shared/business/contracts';

/** Entirely synthetic, recreated per session; never imported by normal builds. */
export function restaurantFixture(restaurantId: number): RestaurantWorkspace {
  const offset = restaurantId * 100;
  const atlas = restaurantId === 9203;
  const orders: Order[] = [
    'pending',
    'preparing',
    'ready',
    'completed',
    'cancelled',
    'confirmed',
    'delivering',
    'delivered',
  ].map((status, index) => ({
    id: offset + 60 + index,
    number: `REV-${restaurantId}-${String(index + 1).padStart(3, '0')}`,
    type:
      index % 3 === 0 ? 'dine_in' : index % 3 === 1 ? 'delivery' : 'takeaway',
    status: status as Order['status'],
    createdAt: `2026-10-22T${String(10 + index).padStart(2, '0')}:15:00Z`,
    customerName: `Client de revue ${index + 1}`,
    customerNote: index === 0 ? 'Sans piment / بدون فلفل حار' : '',
    subtotal: 190000,
    discount: 0,
    tax: 0,
    delivery: index % 3 === 1 ? 20000 : 0,
    total: index % 3 === 1 ? 210000 : 190000,
    paid: status === 'completed',
    items: [
      {
        id: offset + 80 + index,
        name: atlas
          ? 'Couscous Atlas · كسكس الأطلس'
          : 'Couscous maison · كسكس الدار',
        quantity: 2,
        unitPrice: 95000,
        total: 190000,
        options: ['Sauce à part · الصلصة منفصلة'],
      },
    ],
    history: [
      {
        status: 'pending',
        at: `2026-10-22T${String(10 + index).padStart(2, '0')}:00:00Z`,
      },
      ...(status === 'pending'
        ? []
        : [
            {
              status: status as Order['status'],
              at: `2026-10-22T${String(10 + index).padStart(2, '0')}:15:00Z`,
            },
          ]),
    ],
  }));
  return {
    reviewRevision: 1,
    profile: {
      name: atlas
        ? 'Oran · Front de mer'
        : restaurantId === 9202
          ? 'Alger · Les Jardins'
          : 'Alger · Centre',
      type: 'restaurant',
      phone: '+213555000000',
      wilaya: atlas ? 'Oran' : 'Alger',
    },
    categories: [
      { id: offset + 1, name: 'Plats maison · أطباق الدار', sortOrder: 0 },
      { id: offset + 2, name: 'Boissons · مشروبات', sortOrder: 1 },
    ],
    products: [
      {
        id: offset + 10,
        categoryId: offset + 1,
        name: atlas
          ? 'Couscous Atlas · كسكس الأطلس'
          : 'Couscous maison · كسكس الدار',
        description:
          'Légumes de saison, semoule fine. / خضار موسمية وكسكس رقيق.',
        price: 95000,
        available: true,
        sortOrder: 0,
      },
      {
        id: offset + 11,
        categoryId: offset + 1,
        name: 'Chorba · شربة',
        description: 'Recette maison. / وصفة الدار.',
        price: 45000,
        available: true,
        sortOrder: 1,
      },
      {
        id: offset + 12,
        categoryId: offset + 2,
        name: 'Citronnade · ليموناضة',
        description: '',
        price: 25000,
        available: false,
        sortOrder: 0,
      },
    ],
    groups: [
      {
        id: offset + 20,
        productId: offset + 10,
        name: 'Accompagnement · المرافقة',
        required: false,
        multipleChoice: true,
        sortOrder: 0,
      },
    ],
    options: [
      {
        id: offset + 30,
        groupId: offset + 20,
        name: 'Légumes supplémentaires · خضار إضافية',
        extraPrice: 15000,
        available: true,
        sortOrder: 0,
      },
      {
        id: offset + 31,
        groupId: offset + 20,
        name: 'Sauce à part · الصلصة منفصلة',
        extraPrice: 0,
        available: true,
        sortOrder: 1,
      },
    ],
    orders,
  };
}
