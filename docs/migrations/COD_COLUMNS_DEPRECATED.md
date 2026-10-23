# COD columns deprecated (no cash on delivery)

Branch `fix/driver-id-and-no-cod` removes cash on delivery from every app
(driver portal, driver mobile state, merchant portal, admin, API, labels).
**No schema change ships with it.** The columns below stay in the database and
in the ORM models, but no code reads or writes them any more:

| Table       | Column                                                              | Added by                          |
| ----------- | ------------------------------------------------------------------- | --------------------------------- |
| `orders`    | `cod_amount_cents`, `cod_status` (indexed), `cod_stripe_session_id` | `o7p8q9r0s1t2_cod_stripe_connect` |
| `merchants` | `cod_enabled`                                                       | `o7p8q9r0s1t2_cod_stripe_connect` |

`merchants.stripe_connect_account_id` is **kept** (still used by Connect helpers).

## Before an approved drop migration

Run read-only on production and keep the output with the approval:

```sql
SELECT id, company_name, cod_enabled FROM merchants WHERE cod_enabled;
SELECT cod_status, count(*) FROM orders
 WHERE cod_amount_cents IS NOT NULL OR cod_status IS NOT NULL
 GROUP BY cod_status;
-- Any open COD links/payments still to settle by hand:
SELECT id, order_number, cod_amount_cents, cod_status FROM orders
 WHERE cod_status IN ('pending_collection', 'link_issued');
```

If any open rows exist, finance settles them manually first. Stripe
`checkout.session.completed` events with `metadata.purpose = "cod"` are now
logged (`legacy_cod_checkout_ignored`) and ignored, not processed.

## Later drop migration (separate, needs Ravi's approval)

```python
op.drop_index("ix_orders_cod_status", table_name="orders")
op.drop_column("orders", "cod_stripe_session_id")
op.drop_column("orders", "cod_status")
op.drop_column("orders", "cod_amount_cents")
op.drop_column("merchants", "cod_enabled")
```

Remove the model attributes and `CodStatus` in the same change. Deploy the code
from this branch first, so no running pod still maps the columns.
