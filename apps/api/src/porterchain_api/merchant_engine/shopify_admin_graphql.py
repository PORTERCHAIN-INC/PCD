"""One Shopify Admin GraphQL client (API version from settings).

Shopify's own words, used as-is:

- Fulfillment: a shipment of line items, plus tracking and the location.
- FulfillmentOrder: items fulfilled from the same location (deliveryMethod).
- FulfillmentService: a third-party service that creates its own Location.

Those three names attach to an existing PorterChain order. They are not a second product.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from porterchain_api.config import Settings

logger = logging.getLogger("porterchain.shopify_graphql")


class ShopifyAdminError(RuntimeError):
    """GraphQL transport or userErrors. Message is safe to log (no address or email)."""


def admin_graphql(
    shop: str,
    token: str,
    settings: Settings,
    query: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"https://{shop}/admin/api/{settings.shopify_api_version}/graphql.json"
    with httpx.Client(timeout=8.0) as client:
        response = client.post(
            url,
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
            },
            json={"query": query, "variables": variables or {}},
        )
    if response.status_code >= 400:
        from porterchain_api.merchant_engine.shopify_tokens import token_rejection_reason

        # 403 is both "missing scope" and "non-expiring token refused": keep which one.
        reason = token_rejection_reason(response.status_code, response.text)
        logger.warning(
            "shopify_graphql_http status=%s shop=%s reason=%s", response.status_code, shop, reason
        )
        raise ShopifyAdminError(f"http_{response.status_code}" + (f":{reason}" if reason else ""))
    body = response.json()
    if not isinstance(body, dict):
        raise ShopifyAdminError("graphql_body")
    if body.get("errors"):
        # Keep only Shopify's error codes (e.g. ACCESS_DENIED) so callers can tell
        # a missing scope from a bad request. Codes carry no buyer data.
        codes = sorted(
            {
                str((err.get("extensions") or {}).get("code") or "")
                for err in body["errors"]
                if isinstance(err, dict) and isinstance(err.get("extensions"), dict)
            }
            - {""}
        )
        logger.warning("shopify_graphql_errors shop=%s codes=%s", shop, ",".join(codes))
        raise ShopifyAdminError("graphql_errors" + (":" + ",".join(codes) if codes else ""))
    data = body.get("data")
    return data if isinstance(data, dict) else {}


def _payload(data: dict[str, Any], key: str) -> dict[str, Any]:
    block = data.get(key)
    if not isinstance(block, dict):
        raise ShopifyAdminError(f"missing_{key}")
    errors = block.get("userErrors") or []
    if errors:
        parts = [
            str(err.get("message") or "user_error")
            for err in errors
            if isinstance(err, dict)
        ]
        raise ShopifyAdminError("; ".join(parts) or "user_errors")
    return block


def as_gid(kind: str, value: str) -> str:
    raw = (value or "").strip()
    if raw.startswith("gid://"):
        return raw
    return f"gid://shopify/{kind}/{raw}"


def carrier_service_create(shop: str, token: str, settings: Settings, *, callback_url: str) -> str:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation CarrierCreate($input: DeliveryCarrierServiceCreateInput!) {
          carrierServiceCreate(input: $input) {
            carrierService { id }
            userErrors { field message }
          }
        }
        """,
        {
            "input": {
                "name": "PorterChain",
                "callbackUrl": callback_url,
                "supportsServiceDiscovery": True,
                "active": True,
            }
        },
    )
    block = _payload(data, "carrierServiceCreate")
    service = block.get("carrierService") if isinstance(block.get("carrierService"), dict) else {}
    gid = str(service.get("id") or "")
    if not gid:
        raise ShopifyAdminError("carrier_service_missing")
    return gid


def carrier_service_update(
    shop: str, token: str, settings: Settings, *, service_id: str, callback_url: str
) -> str:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation CarrierUpdate($input: DeliveryCarrierServiceUpdateInput!) {
          carrierServiceUpdate(input: $input) {
            carrierService { id }
            userErrors { field message }
          }
        }
        """,
        {
            "input": {
                "id": as_gid("DeliveryCarrierService", service_id),
                "name": "PorterChain",
                "callbackUrl": callback_url,
                "supportsServiceDiscovery": True,
                "active": True,
            }
        },
    )
    block = _payload(data, "carrierServiceUpdate")
    service = block.get("carrierService") if isinstance(block.get("carrierService"), dict) else {}
    gid = str(service.get("id") or "")
    if not gid:
        raise ShopifyAdminError("carrier_service_missing")
    return gid


def carrier_service_find(
    shop: str, token: str, settings: Settings, *, callback_url: str, name: str = "PorterChain"
) -> str | None:
    """Return the store's existing PorterChain CarrierService id, if one is already there."""
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        query CarrierServices {
          carrierServices(first: 50) {
            nodes { id name callbackUrl active }
          }
        }
        """,
    )
    block = data.get("carrierServices") if isinstance(data.get("carrierServices"), dict) else {}
    nodes = block.get("nodes") if isinstance(block.get("nodes"), list) else []
    for node in nodes:
        if not isinstance(node, dict) or not node.get("id"):
            continue
        if str(node.get("callbackUrl") or "") == callback_url or str(node.get("name") or "") == name:
            return str(node["id"])
    return None


def carrier_service_delete(shop: str, token: str, settings: Settings, *, service_id: str) -> None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation CarrierDelete($id: ID!) {
          carrierServiceDelete(id: $id) {
            deletedId
            userErrors { field message }
          }
        }
        """,
        {"id": as_gid("DeliveryCarrierService", service_id)},
    )
    _payload(data, "carrierServiceDelete")


def fulfillment_service_create(
    shop: str, token: str, settings: Settings, *, callback_url: str
) -> tuple[str, str | None]:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation FsCreate(
          $name: String!
          $callbackUrl: URL!
          $trackingSupport: Boolean
          $inventoryManagement: Boolean
        ) {
          fulfillmentServiceCreate(
            name: $name
            callbackUrl: $callbackUrl
            trackingSupport: $trackingSupport
            inventoryManagement: $inventoryManagement
          ) {
            fulfillmentService { id location { id } }
            userErrors { field message }
          }
        }
        """,
        {
            "name": "PorterChain",
            "callbackUrl": callback_url,
            "trackingSupport": True,
            "inventoryManagement": False,
        },
    )
    block = _payload(data, "fulfillmentServiceCreate")
    service = block.get("fulfillmentService") if isinstance(block.get("fulfillmentService"), dict) else {}
    gid = str(service.get("id") or "")
    if not gid:
        raise ShopifyAdminError("fulfillment_service_missing")
    location = service.get("location") if isinstance(service.get("location"), dict) else {}
    location_id = str(location.get("id") or "") or None
    return gid, location_id


def fulfillment_service_update(
    shop: str, token: str, settings: Settings, *, service_id: str, callback_url: str
) -> str:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation FsUpdate($id: ID!, $callbackUrl: URL!, $name: String, $trackingSupport: Boolean) {
          fulfillmentServiceUpdate(
            id: $id
            name: $name
            callbackUrl: $callbackUrl
            trackingSupport: $trackingSupport
          ) {
            fulfillmentService { id location { id } }
            userErrors { field message }
          }
        }
        """,
        {
            "id": as_gid("FulfillmentService", service_id),
            "name": "PorterChain",
            "callbackUrl": callback_url,
            "trackingSupport": True,
        },
    )
    block = _payload(data, "fulfillmentServiceUpdate")
    service = block.get("fulfillmentService") if isinstance(block.get("fulfillmentService"), dict) else {}
    gid = str(service.get("id") or "")
    if not gid:
        raise ShopifyAdminError("fulfillment_service_missing")
    return gid


def fulfillment_service_delete(shop: str, token: str, settings: Settings, *, service_id: str) -> None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation FsDelete($id: ID!) {
          fulfillmentServiceDelete(id: $id) {
            deletedId
            userErrors { field message }
          }
        }
        """,
        {"id": as_gid("FulfillmentService", service_id)},
    )
    _payload(data, "fulfillmentServiceDelete")


def location_edit(
    shop: str,
    token: str,
    settings: Settings,
    *,
    location_id: str,
    address: dict[str, str],
) -> None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation LocEdit($id: ID!, $input: LocationEditInput!) {
          locationEdit(id: $id, input: $input) {
            location { id }
            userErrors { field message }
          }
        }
        """,
        {"id": as_gid("Location", location_id), "input": {"address": address}},
    )
    _payload(data, "locationEdit")


def assigned_fulfillment_orders(
    shop: str,
    token: str,
    settings: Settings,
    *,
    assignment_status: str,
) -> list[dict[str, Any]]:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        query Assigned($assignmentStatus: FulfillmentOrderAssignmentStatus!) {
          assignedFulfillmentOrders(first: 20, assignmentStatus: $assignmentStatus) {
            edges {
              node {
                id
                status
                requestStatus
                deliveryMethod { methodType }
                destination {
                  address1
                  address2
                  city
                  province
                  zip
                  countryCode
                  phone
                  firstName
                  lastName
                }
                lineItems(first: 30) {
                  edges {
                    node {
                      id
                      remainingQuantity
                      sku
                      lineItem { title sku }
                    }
                  }
                }
                order {
                  id
                  name
                  legacyResourceId
                  shippingLines(first: 5) {
                    edges { node { code title } }
                  }
                }
              }
            }
          }
        }
        """,
        {"assignmentStatus": assignment_status},
    )
    conn = data.get("assignedFulfillmentOrders")
    edges = conn.get("edges") if isinstance(conn, dict) else None
    nodes: list[dict[str, Any]] = []
    if isinstance(edges, list):
        for edge in edges:
            node = edge.get("node") if isinstance(edge, dict) else None
            if isinstance(node, dict):
                nodes.append(node)
    return nodes


def accept_fulfillment_request(
    shop: str,
    token: str,
    settings: Settings,
    *,
    fulfillment_order_id: str,
    message: str,
    estimated_shipped_at: str | None,
) -> None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation Accept($id: ID!, $message: String, $estimatedShippedAt: DateTime) {
          fulfillmentOrderAcceptFulfillmentRequest(
            id: $id
            message: $message
            estimatedShippedAt: $estimatedShippedAt
          ) {
            fulfillmentOrder { id }
            userErrors { field message }
          }
        }
        """,
        {
            "id": fulfillment_order_id,
            "message": message,
            "estimatedShippedAt": estimated_shipped_at,
        },
    )
    _payload(data, "fulfillmentOrderAcceptFulfillmentRequest")


def reject_fulfillment_request(
    shop: str,
    token: str,
    settings: Settings,
    *,
    fulfillment_order_id: str,
    message: str,
) -> None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation Reject($id: ID!, $message: String) {
          fulfillmentOrderRejectFulfillmentRequest(id: $id, message: $message) {
            fulfillmentOrder { id }
            userErrors { field message }
          }
        }
        """,
        {"id": fulfillment_order_id, "message": message},
    )
    _payload(data, "fulfillmentOrderRejectFulfillmentRequest")


def accept_cancellation_request(
    shop: str, token: str, settings: Settings, *, fulfillment_order_id: str, message: str
) -> None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation AcceptCancel($id: ID!, $message: String) {
          fulfillmentOrderAcceptCancellationRequest(id: $id, message: $message) {
            fulfillmentOrder { id }
            userErrors { field message }
          }
        }
        """,
        {"id": fulfillment_order_id, "message": message},
    )
    _payload(data, "fulfillmentOrderAcceptCancellationRequest")


def reject_cancellation_request(
    shop: str, token: str, settings: Settings, *, fulfillment_order_id: str, message: str
) -> None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation RejectCancel($id: ID!, $message: String) {
          fulfillmentOrderRejectCancellationRequest(id: $id, message: $message) {
            fulfillmentOrder { id }
            userErrors { field message }
          }
        }
        """,
        {"id": fulfillment_order_id, "message": message},
    )
    _payload(data, "fulfillmentOrderRejectCancellationRequest")


def fulfillment_create(
    shop: str,
    token: str,
    settings: Settings,
    *,
    fulfillment_order_id: str,
    tracking: dict[str, str],
    notify_customer: bool,
) -> str:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation Fulfill($fulfillment: FulfillmentInput!) {
          fulfillmentCreate(fulfillment: $fulfillment) {
            fulfillment { id }
            userErrors { field message }
          }
        }
        """,
        {
            "fulfillment": {
                "lineItemsByFulfillmentOrder": [
                    {"fulfillmentOrderId": as_gid("FulfillmentOrder", fulfillment_order_id)}
                ],
                "trackingInfo": {
                    "company": tracking.get("company") or "PorterChain",
                    "number": tracking.get("number") or "",
                    "url": tracking.get("url") or "",
                },
                "notifyCustomer": notify_customer,
            }
        },
    )
    block = _payload(data, "fulfillmentCreate")
    fulfillment = block.get("fulfillment") if isinstance(block.get("fulfillment"), dict) else {}
    gid = str(fulfillment.get("id") or "")
    if not gid:
        raise ShopifyAdminError("fulfillment_missing")
    return gid


def fulfillment_tracking_update(
    shop: str,
    token: str,
    settings: Settings,
    *,
    fulfillment_id: str,
    tracking: dict[str, str],
    notify_customer: bool,
) -> None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation Track($fulfillmentId: ID!, $trackingInfoInput: FulfillmentTrackingInput!, $notifyCustomer: Boolean) {
          fulfillmentTrackingInfoUpdate(
            fulfillmentId: $fulfillmentId
            trackingInfoInput: $trackingInfoInput
            notifyCustomer: $notifyCustomer
          ) {
            fulfillment { id }
            userErrors { field message }
          }
        }
        """,
        {
            "fulfillmentId": as_gid("Fulfillment", fulfillment_id),
            "notifyCustomer": notify_customer,
            "trackingInfoInput": {
                "company": tracking.get("company") or "PorterChain",
                "number": tracking.get("number") or "",
                "url": tracking.get("url") or "",
            },
        },
    )
    _payload(data, "fulfillmentTrackingInfoUpdate")


def fulfillment_event_create(
    shop: str,
    token: str,
    settings: Settings,
    *,
    fulfillment_id: str,
    status: str,
    happened_at: str | None = None,
    message: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> None:
    event: dict[str, Any] = {
        "fulfillmentId": as_gid("Fulfillment", fulfillment_id),
        "status": status,
    }
    if happened_at:
        event["happenedAt"] = happened_at
    if message:
        event["message"] = message
    if latitude is not None:
        event["latitude"] = latitude
    if longitude is not None:
        event["longitude"] = longitude
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation Ev($fulfillmentEvent: FulfillmentEventInput!) {
          fulfillmentEventCreate(fulfillmentEvent: $fulfillmentEvent) {
            fulfillmentEvent { id status }
            userErrors { field message }
          }
        }
        """,
        {"fulfillmentEvent": event},
    )
    _payload(data, "fulfillmentEventCreate")


def fulfillment_cancel(shop: str, token: str, settings: Settings, *, fulfillment_id: str) -> None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation Cancel($id: ID!) {
          fulfillmentCancel(id: $id) {
            fulfillment { id }
            userErrors { field message }
          }
        }
        """,
        {"id": as_gid("Fulfillment", fulfillment_id)},
    )
    _payload(data, "fulfillmentCancel")


def fulfillment_order_close(
    shop: str, token: str, settings: Settings, *, fulfillment_order_id: str, message: str
) -> None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation Close($id: ID!, $message: String) {
          fulfillmentOrderClose(id: $id, message: $message) {
            fulfillmentOrder { id }
            userErrors { field message }
          }
        }
        """,
        {"id": fulfillment_order_id, "message": message},
    )
    _payload(data, "fulfillmentOrderClose")


def reverse_delivery_create(
    shop: str,
    token: str,
    settings: Settings,
    *,
    reverse_fulfillment_order_id: str,
    tracking: dict[str, str],
) -> str | None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation Rev($reverseFulfillmentOrderId: ID!, $trackingInput: ReverseDeliveryTrackingInput) {
          reverseDeliveryCreateWithShipping(
            reverseFulfillmentOrderId: $reverseFulfillmentOrderId
            trackingInput: $trackingInput
          ) {
            reverseDelivery { id }
            userErrors { field message }
          }
        }
        """,
        {
            "reverseFulfillmentOrderId": reverse_fulfillment_order_id,
            "trackingInput": {
                "number": tracking.get("number") or "",
                "url": tracking.get("url") or "",
            },
        },
    )
    block = _payload(data, "reverseDeliveryCreateWithShipping")
    delivery = block.get("reverseDelivery") if isinstance(block.get("reverseDelivery"), dict) else {}
    return str(delivery.get("id") or "") or None


def reverse_delivery_shipping_update(
    shop: str,
    token: str,
    settings: Settings,
    *,
    reverse_delivery_id: str,
    tracking: dict[str, str],
) -> None:
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation RevUp($reverseDeliveryId: ID!, $trackingInput: ReverseDeliveryTrackingInput!) {
          reverseDeliveryShippingUpdate(
            reverseDeliveryId: $reverseDeliveryId
            trackingInput: $trackingInput
          ) {
            reverseDelivery { id }
            userErrors { field message }
          }
        }
        """,
        {
            "reverseDeliveryId": reverse_delivery_id,
            "trackingInput": {
                "number": tracking.get("number") or "",
                "url": tracking.get("url") or "",
            },
        },
    )
    _payload(data, "reverseDeliveryShippingUpdate")
