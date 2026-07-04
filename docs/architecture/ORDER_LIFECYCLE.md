# Order Lifecycle

> **Source:** `domain/states.py`, `booking_engine/order_transitions.py`, `fleetbase_engine/webhook_processor.py`

## OrderState Enum

Defined in `apps/api/src/porterchain_api/domain/states.py`:

`BOOKED` → `DISPATCH_READY` → `DRIVER_ASSIGNED` → `DRIVER_ACCEPTED` → `DRIVER_EN_ROUTE` → `AT_PICKUP` → `PICKED_UP` → `IN_TRANSIT` → `AT_DESTINATION` → `DELIVERED` → `POD_COMPLETED` → `INVOICED` → `CLOSED`

Exception states: `DRIVER_REJECTED`, `FAILED`, `CANCELLED`, `RETURN_TO_SENDER`, `DAMAGED`, `LOST`, `CLAIM_OPEN`, `REFUNDED`

## Enforcement

- `can_transition_order()` — validates against `ORDER_TRANSITIONS` map
- `transition_order_state()` — writes `OrderEvent` + `DomainEvent` rows
- `transition_to_dispatch_ready()` — emits `order.dispatch_requested` then `order.dispatch_ready`

## Transition Sources

| Source              | Mechanism                                                                      |
| ------------------- | ------------------------------------------------------------------------------ |
| Retail confirmation | `BookingConfirmationService` → `BOOKED` → `DISPATCH_READY`                     |
| Merchant booking    | `MerchantBookingService` → same                                                |
| Admin assign        | `AdminOperationsService.assign_driver()` → `DRIVER_ASSIGNED`                   |
| Fleetbase webhooks  | `WebhookProcessor` + `StatusTranslator`                                        |
| Driver app          | `porterchain_driver` stop actions → events                                     |
| Merchant cancel     | `MerchantOrdersService.cancel_order()` → `CANCELLED` + direct Fleetbase cancel |

## Metadata

- `order_source`: WEBSITE, MERCHANT, CSV, API, ADMIN, PHONE, PARTNER
- `order_type`: INSTANT, CONTRACT, RECURRING, EXPRESS, SCHEDULED

## Diagram

```mermaid
stateDiagram-v2
  [*] --> BOOKED
  BOOKED --> DISPATCH_READY: transition_to_dispatch_ready
  BOOKED --> CANCELLED
  DISPATCH_READY --> DRIVER_ASSIGNED: admin assign / Fleetbase webhook
  DISPATCH_READY --> CANCELLED
  DRIVER_ASSIGNED --> DRIVER_ACCEPTED
  DRIVER_ASSIGNED --> DRIVER_REJECTED
  DRIVER_ASSIGNED --> CANCELLED
  DRIVER_REJECTED --> DRIVER_ASSIGNED: reassign
  DRIVER_REJECTED --> DISPATCH_READY
  DRIVER_ACCEPTED --> DRIVER_EN_ROUTE
  DRIVER_ACCEPTED --> CANCELLED
  DRIVER_EN_ROUTE --> AT_PICKUP
  DRIVER_EN_ROUTE --> FAILED
  AT_PICKUP --> PICKED_UP
  AT_PICKUP --> FAILED
  PICKED_UP --> IN_TRANSIT
  PICKED_UP --> FAILED
  IN_TRANSIT --> AT_DESTINATION
  IN_TRANSIT --> FAILED
  AT_DESTINATION --> DELIVERED
  AT_DESTINATION --> FAILED
  DELIVERED --> POD_COMPLETED
  DELIVERED --> DAMAGED
  DELIVERED --> FAILED
  POD_COMPLETED --> INVOICED
  INVOICED --> CLOSED
  FAILED --> DISPATCH_READY: retry
  FAILED --> RETURN_TO_SENDER
  FAILED --> CANCELLED
  DAMAGED --> CLAIM_OPEN
  LOST --> CLAIM_OPEN
  CLAIM_OPEN --> REFUNDED
  CLAIM_OPEN --> CLOSED
  RETURN_TO_SENDER --> CLOSED
  RETURN_TO_SENDER --> CLAIM_OPEN
  CANCELLED --> [*]
  CLOSED --> [*]
  REFUNDED --> [*]
```

## PlantUML

See [plantuml/order_lifecycle.puml](./plantuml/order_lifecycle.puml)
