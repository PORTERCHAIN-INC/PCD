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
        from porterchain_api.merchant_engine.shopify_tokens import (
            token_rejection_reason,
        )

        # 403 is both "missing scope" and "non-expiring token refused": keep which one.
        reason = token_rejection_reason(response.status_code, response.text)
        logger.warning(
            "shopify_graphql_http status=%s shop=%s reason=%s",
            response.status_code,
            shop,
            reason,
        )
        raise ShopifyAdminError(
            f"http_{response.status_code}" + (f":{reason}" if reason else "")
        )
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
        raise ShopifyAdminError(
            "graphql_errors" + (":" + ",".join(codes) if codes else "")
        )
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


def carrier_service_create(
    shop: str, token: str, settings: Settings, *, callback_url: str
) -> str:
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
    service = (
        block.get("carrierService")
        if isinstance(block.get("carrierService"), dict)
        else {}
    )
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
    service = (
        block.get("carrierService")
        if isinstance(block.get("carrierService"), dict)
        else {}
    )
    gid = str(service.get("id") or "")
    if not gid:
        raise ShopifyAdminError("carrier_service_missing")
    return gid


def carrier_service_find(
    shop: str,
    token: str,
    settings: Settings,
    *,
    callback_url: str,
    name: str = "PorterChain",
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
    block = (
        data.get("carrierServices")
        if isinstance(data.get("carrierServices"), dict)
        else {}
    )
    nodes = block.get("nodes") if isinstance(block.get("nodes"), list) else []
    for node in nodes:
        if not isinstance(node, dict) or not node.get("id"):
            continue
        if (
            str(node.get("callbackUrl") or "") == callback_url
            or str(node.get("name") or "") == name
        ):
            return str(node["id"])
    return None


def carrier_service_delete(
    shop: str, token: str, settings: Settings, *, service_id: str
) -> None:
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
    service = (
        block.get("fulfillmentService")
        if isinstance(block.get("fulfillmentService"), dict)
        else {}
    )
    gid = str(service.get("id") or "")
    if not gid:
        raise ShopifyAdminError("fulfillment_service_missing")
    location = (
        service.get("location") if isinstance(service.get("location"), dict) else {}
    )
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
    service = (
        block.get("fulfillmentService")
        if isinstance(block.get("fulfillmentService"), dict)
        else {}
    )
    gid = str(service.get("id") or "")
    if not gid:
        raise ShopifyAdminError("fulfillment_service_missing")
    return gid


def fulfillment_service_delete(
    shop: str, token: str, settings: Settings, *, service_id: str
) -> None:
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
                    {
                        "fulfillmentOrderId": as_gid(
                            "FulfillmentOrder", fulfillment_order_id
                        )
                    }
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
    fulfillment = (
        block.get("fulfillment") if isinstance(block.get("fulfillment"), dict) else {}
    )
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


def fulfillment_cancel(
    shop: str, token: str, settings: Settings, *, fulfillment_id: str
) -> None:
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
    delivery = (
        block.get("reverseDelivery")
        if isinstance(block.get("reverseDelivery"), dict)
        else {}
    )
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


def webhook_subscriptions_ensure(
    shop: str, token: str, settings: Settings, *, topics: list[str], uri: str
) -> list[str]:
    """Create GraphQL-only webhook subscriptions that are not already pointing at ``uri``."""
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        query PcdWebhooks($topics: [WebhookSubscriptionTopic!]) {
          webhookSubscriptions(first: 50, topics: $topics) {
            nodes { topic uri }
          }
        }
        """,
        {"topics": topics},
    )
    nodes = (
        ((data.get("webhookSubscriptions") or {}).get("nodes") or []) if data else []
    )
    have = {
        str(n.get("topic") or "")
        for n in nodes
        if isinstance(n, dict) and str(n.get("uri") or "") == uri
    }
    created: list[str] = []
    for topic in topics:
        if topic in have:
            continue
        result = admin_graphql(
            shop,
            token,
            settings,
            """
            mutation PcdWebhookCreate($topic: WebhookSubscriptionTopic!, $sub: WebhookSubscriptionInput!) {
              webhookSubscriptionCreate(topic: $topic, webhookSubscription: $sub) {
                webhookSubscription { id }
                userErrors { field message }
              }
            }
            """,
            {"topic": topic, "sub": {"uri": uri, "format": "JSON"}},
        )
        _payload(result, "webhookSubscriptionCreate")
        created.append(topic)
    return created


# --- REST Admin API replacements (GraphQL-only app) ---------------------------------

#: Privacy topics are declared in the app config (``compliance_topics``) and cannot be
#: subscribed at runtime; Shopify delivers them without a subscription.
COMPLIANCE_TOPICS = frozenset(
    {"customers/data_request", "customers/redact", "shop/redact"}
)


def webhook_topic_enum(topic: str) -> str:
    """REST-style ``orders/create`` → GraphQL ``ORDERS_CREATE`` (enums pass through)."""
    raw = (topic or "").strip()
    if "/" not in raw and raw.upper() == raw:
        return raw
    return raw.replace("/", "_").upper()


def webhook_subscriptions_sync(
    shop: str, token: str, settings: Settings, *, topics: list[str], uri: str
) -> list[str]:
    """Idempotently subscribe ``topics`` to ``uri``; return the topics that failed.

    Existing subscriptions (whether created by the old REST call or here) are listed
    by GraphQL too, so a topic already pointing at ``uri`` is left untouched.
    """
    wanted = [t for t in topics if t not in COMPLIANCE_TOPICS]
    enums = {t: webhook_topic_enum(t) for t in wanted}
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        query PcdWebhooksAll($after: String) {
          webhookSubscriptions(first: 100, after: $after) {
            nodes { topic uri }
            pageInfo { hasNextPage endCursor }
          }
        }
        """,
        {"after": None},
    )
    have: set[str] = set()
    conn = (
        data.get("webhookSubscriptions")
        if isinstance(data.get("webhookSubscriptions"), dict)
        else {}
    )
    pages = 0
    while True:
        for node in conn.get("nodes") or []:
            if isinstance(node, dict) and str(node.get("uri") or "") == uri:
                have.add(str(node.get("topic") or ""))
        info = conn.get("pageInfo") if isinstance(conn.get("pageInfo"), dict) else {}
        pages += 1
        if not info.get("hasNextPage") or not info.get("endCursor") or pages >= 10:
            break
        data = admin_graphql(
            shop,
            token,
            settings,
            """
            query PcdWebhooksAll($after: String) {
              webhookSubscriptions(first: 100, after: $after) {
                nodes { topic uri }
                pageInfo { hasNextPage endCursor }
              }
            }
            """,
            {"after": info["endCursor"]},
        )
        conn = (
            data.get("webhookSubscriptions")
            if isinstance(data.get("webhookSubscriptions"), dict)
            else {}
        )
    failed: list[str] = []
    for topic, enum in enums.items():
        if enum in have:
            continue
        try:
            result = admin_graphql(
                shop,
                token,
                settings,
                """
                mutation PcdWebhookCreate($topic: WebhookSubscriptionTopic!, $sub: WebhookSubscriptionInput!) {
                  webhookSubscriptionCreate(topic: $topic, webhookSubscription: $sub) {
                    webhookSubscription { id }
                    userErrors { field message }
                  }
                }
                """,
                {"topic": enum, "sub": {"uri": uri, "format": "JSON"}},
            )
            _payload(result, "webhookSubscriptionCreate")
            have.add(enum)
        except ShopifyAdminError as exc:
            if "already" in str(exc).lower() or "taken" in str(exc).lower():
                continue
            logger.warning("shopify_webhook_create_failed shop=%s topic=%s", shop, enum)
            failed.append(topic)
    return failed


def shop_details(shop: str, token: str, settings: Settings) -> dict[str, Any]:
    """The store's identity and address, in the REST ``shop`` shape callers already read."""
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        query PcdShop {
          shop {
            id
            name
            email
            contactEmail
            primaryDomain { host }
            billingAddress {
              address1 address2 city province provinceCode zip countryCodeV2 latitude longitude phone
            }
          }
        }
        """,
    )
    node = data.get("shop") if isinstance(data.get("shop"), dict) else {}
    if not node:
        return {}
    addr = (
        node.get("billingAddress")
        if isinstance(node.get("billingAddress"), dict)
        else {}
    )
    gid = str(node.get("id") or "")
    return {
        "id": gid.rsplit("/", 1)[-1] if gid else None,
        "admin_graphql_api_id": gid or None,
        "name": node.get("name"),
        "email": node.get("contactEmail") or node.get("email"),
        "domain": (node.get("primaryDomain") or {}).get("host")
        if isinstance(node.get("primaryDomain"), dict)
        else None,
        "phone": addr.get("phone"),
        "address1": addr.get("address1"),
        "address2": addr.get("address2"),
        "city": addr.get("city"),
        "province": addr.get("province"),
        "province_code": addr.get("provinceCode"),
        "zip": addr.get("zip"),
        "country_code": addr.get("countryCodeV2"),
        "latitude": addr.get("latitude"),
        "longitude": addr.get("longitude"),
    }


def order_fulfillment_orders(
    shop: str, token: str, settings: Settings, *, order_id: str
) -> list[dict[str, Any]]:
    """Open fulfillment orders of one order: ``[{"id": gid, "status": ...}]``."""
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        query PcdOrderFOs($id: ID!) {
          order(id: $id) {
            fulfillmentOrders(first: 20) { nodes { id status } }
          }
        }
        """,
        {"id": as_gid("Order", order_id)},
    )
    order = data.get("order") if isinstance(data.get("order"), dict) else {}
    conn = (
        order.get("fulfillmentOrders")
        if isinstance(order.get("fulfillmentOrders"), dict)
        else {}
    )
    out: list[dict[str, Any]] = []
    for node in conn.get("nodes") or []:
        if isinstance(node, dict) and node.get("id"):
            out.append({"id": str(node["id"]), "status": node.get("status")})
    return out


def fulfillment_create_for_orders(
    shop: str,
    token: str,
    settings: Settings,
    *,
    fulfillment_order_ids: list[str],
    tracking: dict[str, str],
    notify_customer: bool,
) -> str:
    """One fulfillment covering several fulfillment orders (REST POST /fulfillments.json)."""
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
                    {"fulfillmentOrderId": as_gid("FulfillmentOrder", fid)}
                    for fid in fulfillment_order_ids
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
    fulfillment = (
        block.get("fulfillment") if isinstance(block.get("fulfillment"), dict) else {}
    )
    gid = str(fulfillment.get("id") or "")
    if not gid:
        raise ShopifyAdminError("fulfillment_missing")
    return gid


def fulfillment_service_find(
    shop: str, token: str, settings: Settings, *, name: str = "PorterChain"
) -> tuple[str, str | None] | None:
    """Existing PorterChain FulfillmentService on the store: ``(id, location_id)``."""
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        query PcdFs {
          shop { fulfillmentServices { id serviceName location { id } } }
        }
        """,
    )
    node = data.get("shop") if isinstance(data.get("shop"), dict) else {}
    for row in node.get("fulfillmentServices") or []:
        if (
            not isinstance(row, dict)
            or str(row.get("serviceName") or "") != name
            or not row.get("id")
        ):
            continue
        loc = row.get("location") if isinstance(row.get("location"), dict) else {}
        return str(row["id"]), (str(loc.get("id") or "") or None)
    return None


def order_mark_as_paid(
    shop: str, token: str, settings: Settings, *, order_id: str
) -> str | None:
    """Record an external capture on the order (REST transactions kind=capture)."""
    data = admin_graphql(
        shop,
        token,
        settings,
        """
        mutation PcdPaid($input: OrderMarkAsPaidInput!) {
          orderMarkAsPaid(input: $input) {
            order { id transactions(first: 20) { id kind status } }
            userErrors { field message }
          }
        }
        """,
        {"input": {"id": as_gid("Order", order_id)}},
    )
    block = _payload(data, "orderMarkAsPaid")
    order = block.get("order") if isinstance(block.get("order"), dict) else {}
    txs = (
        order.get("transactions") if isinstance(order.get("transactions"), list) else []
    )
    for tx in reversed(txs):
        if isinstance(tx, dict) and tx.get("id"):
            return str(tx["id"])
    return None
