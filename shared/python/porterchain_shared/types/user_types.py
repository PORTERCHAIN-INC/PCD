"""Platform user types — distinct from Clerk org membership."""

from enum import StrEnum


class UserType(StrEnum):
    VISITOR = "visitor"
    CUSTOMER = "customer"
    MERCHANT = "merchant"
    DRIVER = "driver"
    ADMIN = "admin"
    DISPATCHER = "dispatcher"
    SUPPORT = "support"
    SALES = "sales"
