"""Request ID middleware tests."""

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from porterchain_api.platform.middleware import REQUEST_ID_HEADER, RequestIdMiddleware


async def _ping(request):
    return PlainTextResponse(getattr(request.state, "request_id", ""))


def test_request_id_generated_when_missing() -> None:
    app = Starlette(routes=[Route("/ping", _ping)])
    app.add_middleware(RequestIdMiddleware)
    client = TestClient(app)
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.headers.get(REQUEST_ID_HEADER)


def test_request_id_preserved_from_client() -> None:
    app = Starlette(routes=[Route("/ping", _ping)])
    app.add_middleware(RequestIdMiddleware)
    client = TestClient(app)
    response = client.get("/ping", headers={REQUEST_ID_HEADER: "client-req-99"})
    assert response.headers.get(REQUEST_ID_HEADER) == "client-req-99"
