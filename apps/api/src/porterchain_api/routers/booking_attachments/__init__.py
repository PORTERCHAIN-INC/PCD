"""Booking attachments — one feature, four audiences (merchant, customer, driver, staff)."""

from fastapi import APIRouter

from porterchain_api.routers.booking_attachments import customer, driver, merchant

router = APIRouter()
router.include_router(merchant.router)
router.include_router(customer.router)
router.include_router(driver.router)
