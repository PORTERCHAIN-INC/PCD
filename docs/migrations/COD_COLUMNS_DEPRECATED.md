# COD and Stripe Connect columns — dropped

Cash on delivery is not offered anywhere, and merchants pay by Interac only
(Stripe card checkout stays for retail and guest customers). Migration
`dm4nocod0004_drop_cod_and_stripe_connect_columns` drops the dead columns:

| Table       | Column                                                              | Added by                          |
| ----------- | ------------------------------------------------------------------- | --------------------------------- |
| `orders`    | `cod_amount_cents`, `cod_status` (indexed), `cod_stripe_session_id` | `o7p8q9r0s1t2_cod_stripe_connect` |
| `merchants` | `cod_enabled`, `stripe_connect_account_id`                          | `o7p8q9r0s1t2_cod_stripe_connect` |

The ORM attributes are removed in the same change. The API still rejects a
`cod_amount_cents` field on merchant bookings with
`422 cash_on_delivery_not_supported` (input guard, no column behind it), and
Stripe `checkout.session.completed` events with `metadata.purpose = "cod"` are
logged (`legacy_cod_checkout_ignored`) and ignored.

## Data safety

- Before the drop, every set value is copied to `legacy_external_refs`
  (`source = 'dm4_cod_columns'`, `entity` = table, `entity_id` = row id,
  `field` = column). The migration prints the count per column.
- Any order with an open COD collection (`cod_status` in
  `pending_collection` / `link_issued`) is printed by order number so finance
  can settle it by hand.
- `alembic downgrade dm3custody0003` re-adds the columns (same types, the
  `cod_enabled` default, `ix_orders_cod_status`) and restores every archived value.

## Before running on production (read-only, keep the output)

```sql
SELECT id, company_name, cod_enabled, stripe_connect_account_id FROM merchants
 WHERE cod_enabled OR stripe_connect_account_id IS NOT NULL;
SELECT cod_status, count(*) FROM orders
 WHERE cod_amount_cents IS NOT NULL OR cod_status IS NOT NULL
 GROUP BY cod_status;
```

Deploy code that no longer maps the columns before (or with) the migration, so
no running pod still selects them.
