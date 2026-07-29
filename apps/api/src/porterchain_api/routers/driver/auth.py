"""driver routes — auth (cookie JWT minting retired)."""

from porterchain_api.routers.driver._deps import (
    HTTPException,
    router,
)


@router.post("/auth/login")
async def driver_login():
    """Retired — driver portal uses Clerk bearer like other portals."""
    raise HTTPException(
        status_code=410,
        detail="driver_cookie_jwt_retired",
    )


@router.post("/auth/refresh")
def driver_refresh():
    raise HTTPException(
        status_code=410,
        detail="driver_cookie_jwt_retired",
    )
