# Catalog option groups and product options: isolation review

Review date: 2026-10-13.

Calls to `ProductRepository.get_by_id` when creating option groups and deleting
them by product were corrected to use `id=product_id`. Group reordering now
verifies that every listed group belongs to the requested product before writing
any ordering changes. Group deletion also counts unavailable options through
`ProductOptionRepository.count_by_group`.

These corrections address broken contracts and product membership.
**Authentication and tenant isolation for catalog option routes remain
incomplete in this review.** These routes are separate from the subscription
receipt-review workflow.

## Source findings

- `app/api/v1/option_group.py` constructs `OptionGroupsService` with only a
  SQLAlchemy session. It does not pass a verified owner identity. Group creation,
  updates, and deletion remain available without a `get_current_owner`
  dependency or an administrative permission requirement.
- `app/api/v1/product_option.py` constructs `ProductOptionService` in the same
  way. Securing option groups alone does not secure writes to their options.
- `app/models/option_group.py` associates each group through `product_id`; a
  group has no `restaurant_id` column. Its restaurant is determined through
  `Product.restaurant_id`, and its owner through `Restaurant.owner_id`.
- `app/repositories/option_groups_repo.py` and
  `app/repositories/product_option_repo.py` filter by group or product ID without
  enforcing an owner identity on every read and write.

## Required remediation and verification

The API, service, and repository layers must be addressed together. Administrative
operations must receive a verified identity and enforce the
`OptionGroup → Product → Restaurant → Owner` relationship in SQL queries. A group
or option must not be moved outside its tenant boundary. Public restaurant-menu
reads must remain scoped to the selected restaurant.

HTTP and PostgreSQL tests must demonstrate that creation, updates, and deletion
using another owner's identifiers are rejected before any write.

This document records the remaining work; it does not claim that authentication
or isolation has already been implemented, or certify the catalog routes as
production-ready. The manual-payment review boundary is independent and uses a
verified owner identity or the `payments.review` permission within its existing
scope.
