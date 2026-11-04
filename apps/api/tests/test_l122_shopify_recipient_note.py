from porterchain_api.integrations.shopify_orders import map_shopify_order
from porterchain_api.schemas_merchant import AddressInput


def _payload(**addr):
    base = {"address1": "1 King St W", "city": "Toronto", "zip": "M5H 1A1"}
    base.update(addr)
    return {"id": 77, "name": "#77", "shipping_address": base, "line_items": []}


def test_buyer_contact_is_labelled_recipient():
    req = map_shopify_order(
        _payload(name="Cleo Singh", phone="4165550103"),
        pickup=AddressInput(formatted="Shop, Toronto"),
    )
    assert req.special_instructions == "Recipient: Cleo Singh, 4165550103"


def test_no_contact_no_note():
    req = map_shopify_order(_payload(), pickup=AddressInput(formatted="Shop, Toronto"))
    assert req.special_instructions is None
