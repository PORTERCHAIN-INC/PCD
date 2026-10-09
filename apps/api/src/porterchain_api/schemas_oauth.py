"""OAuth 2.0 request/response schemas."""

from pydantic import BaseModel, Field


class OAuthClientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(min_length=1)
    environment: str = Field(default="sandbox", pattern="^(sandbox|production)$")
    redirect_uris: list[str] = Field(default_factory=list)


class OAuthAuthorizeRequest(BaseModel):
    client_id: str
    redirect_uri: str
    scope: str | None = None
    state: str | None = None


class OAuthAuthorizeResponse(BaseModel):
    code: str
    state: str | None = None
    expires_in: int = 300


class OAuthTokenRequest(BaseModel):
    grant_type: str
    client_id: str
    client_secret: str
    scope: str | None = None
    code: str | None = None
    redirect_uri: str | None = None


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
