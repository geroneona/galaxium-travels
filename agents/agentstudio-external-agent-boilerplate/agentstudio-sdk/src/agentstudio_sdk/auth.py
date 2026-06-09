"""Authentication helpers for agentstudio boilerplates.

Provides a small `Authenticator` utility and a Starlette middleware that
enforces bearer-token authentication only when the env var
`A2A_BEARER_TOKEN` is set. This keeps auth optional for local development
while enabling a single-token protected endpoint for deployed agents.
"""

from __future__ import annotations

import os
from typing import Optional, Mapping, Iterable

import httpx

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .logger import get_logger

logger = get_logger(__name__)

# Module-level defaults
DEFAULT_HTTP_AUTH_SCHEME = "HTTPAuthSecurityScheme"


class Authenticator:
    """Simple bearer-token authenticator.

    The constructor accepts a list of authentication scheme names that the
    authenticator should provide according to the A2A spec:
      - APIKeySecurityScheme
      - HTTPAuthSecurityScheme
      - OAuth2SecurityScheme
      - OpenIdConnectSecurityScheme
    Currentl only `HTTPAuthSecurityScheme` is implemented.
    """

    A2A_BEARER_ENV = "A2A_BEARER_TOKEN"
    KEYCLOAK_ISSUER_URL_ENV = "KEYCLOAK_ISSUER_URL"
    KEYCLOAK_URL_ENV = "KEYCLOAK_URL"
    KEYCLOAK_JWKS_ENV = "KEYCLOAK_JWKS_URL"
    KEYCLOAK_USERINFO_URL_ENV = "KEYCLOAK_USERINFO_URL"
    KEYCLOAK_AUDIENCE_ENV = "KEYCLOAK_AUDIENCE"

    def __init__(self, schemes: list[str] = None) -> None:
        # Use the default scheme only when the caller did not provide any
        # `schemes` (i.e. `schemes is None`). If the caller passes an empty
        # iterable we respect it as the explicit choice of no schemes.
        self.schemes = (
            [DEFAULT_HTTP_AUTH_SCHEME] if schemes is None else schemes
        )

        # Defer reading any scheme-specific env vars until validation time
        # so that the Authenticator is agnostic to which schemes are used.
        self._bearer_token = None
        self._keycloak_issuer: Optional[str] = None
        self._keycloak_jwks_url: Optional[str] = None
        self._keycloak_userinfo_url: Optional[str] = None
        self._keycloak_audience: Optional[str] = None
        self._keycloak_jwk_client = None
        if "HTTPAuthSecurityScheme" in self.schemes:
            self._bearer_token = os.environ.get(self.A2A_BEARER_ENV, None)
            issuer_raw = os.environ.get(
                self.KEYCLOAK_ISSUER_URL_ENV
            ) or os.environ.get(self.KEYCLOAK_URL_ENV)
            if issuer_raw:
                self._keycloak_issuer = issuer_raw.rstrip("/")
                self._keycloak_jwks_url = (
                    os.environ.get(self.KEYCLOAK_JWKS_ENV)
                    or f"{self._keycloak_issuer}/protocol/openid-connect/certs"
                )
                self._keycloak_userinfo_url = (
                    os.environ.get(self.KEYCLOAK_USERINFO_URL_ENV)
                    or f"{self._keycloak_issuer}/protocol/openid-connect/userinfo"
                )
                self._keycloak_audience = (
                    os.environ.get(self.KEYCLOAK_AUDIENCE_ENV) or None
                )
            if self._bearer_token is None:
                logger.warning(
                    (
                        "HTTPAuthSecurityScheme enabled but %s env var not set -"
                        " requests will be authenticated automatically"
                    ),
                    self.A2A_BEARER_ENV,
                )
            if self._bearer_token is None and self._keycloak_issuer is None:
                logger.warning(
                    (
                        "HTTPAuthSecurityScheme enabled but neither %s nor %s/%s are set - "
                        "requests will be authenticated automatically"
                    ),
                    self.A2A_BEARER_ENV,
                    self.KEYCLOAK_ISSUER_URL_ENV,
                    self.KEYCLOAK_URL_ENV,
                )

    def is_enabled(self) -> bool:
        return (
            self._bearer_token is not None or self._keycloak_issuer is not None
        )

    def _validate_keycloak_token(self, token: str) -> bool:
        if self._keycloak_issuer is None or self._keycloak_jwks_url is None:
            return False
        try:
            import jwt
            from jwt import PyJWKClient

            if self._keycloak_jwk_client is None:
                self._keycloak_jwk_client = PyJWKClient(self._keycloak_jwks_url)

            signing_key = self._keycloak_jwk_client.get_signing_key_from_jwt(
                token
            )
            decode_kwargs = {
                "algorithms": [
                    "RS256",
                    "RS384",
                    "RS512",
                    "ES256",
                    "ES384",
                    "ES512",
                ],
                "issuer": self._keycloak_issuer,
                "options": {"verify_aud": bool(self._keycloak_audience)},
            }
            if self._keycloak_audience:
                decode_kwargs["audience"] = self._keycloak_audience

            jwt.decode(token, signing_key.key, **decode_kwargs)
            return True
        except Exception as exc:
            logger.info(
                "Keycloak JWT validation failed, trying userinfo fallback: %s",
                exc,
            )
            return self._validate_keycloak_token_via_userinfo(token)

    def _validate_keycloak_token_via_userinfo(self, token: str) -> bool:
        if self._keycloak_userinfo_url is None:
            return False
        try:
            response = httpx.get(
                self._keycloak_userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            if response.status_code != 200:
                logger.info(
                    "Keycloak userinfo validation failed with status %s",
                    response.status_code,
                )
                return False
            payload = response.json()
            return isinstance(payload, dict) and bool(payload.get("sub"))
        except Exception as exc:
            logger.info("Keycloak userinfo validation failed: %s", exc)
            return False

    def validate(self, headers: Optional[Mapping[str, str]]) -> bool:
        """Validate incoming request headers against supported schemes.

        `headers` is the complete request headers mapping. The method will
        iterate configured `self.schemes` and attempt to validate using each
        scheme until one succeeds. Currently the only implemented scheme is
        `HTTPAuthSecurityScheme` which checks `Authorization: Bearer <token>`.

        Returns True when auth is disabled or when any supported scheme
        validates successfully.
        """
        for scheme in self.schemes:
            if scheme == "HTTPAuthSecurityScheme":
                # Only execute HTTP auth-specific logic when the scheme is requested.
                if self._bearer_token is None and self._keycloak_issuer is None:
                    return True  # Auth disabled when token is not set
                authv = (
                    headers.get("authorization", None)
                    or headers.get("Authorization", None)
                    or ""
                )
                if not authv:
                    continue
                parts = authv.split(" ", 1)
                if len(parts) != 2:
                    continue
                sch, token = parts
                if sch.lower() == "bearer" and token == self._bearer_token:
                    return True
                if sch.lower() == "bearer" and self._validate_keycloak_token(
                    token
                ):
                    return True
            else:
                logger.info(
                    "Authenticator: unknown scheme '%s' - skipping", scheme
                )
        return False


class AuthenticatorMiddleware(BaseHTTPMiddleware):
    """Starlette middleware enforcing bearer auth for messaging endpoints.

    By default the middleware checks requests whose path endswith
    `/message:send` (REST mapping) and rejects requests with 401 when the
    configured token is missing or invalid. When the env var is not set the
    middleware is a no-op (always allows requests).
    """

    def __init__(
        self,
        app,
        schemes: Optional[Iterable[str]] = None,
        authenticator: Optional[Authenticator] = None,
    ):
        super().__init__(app)
        if authenticator is not None:
            self.auth = authenticator
        else:
            self.auth = Authenticator(schemes=schemes)

    _PUBLIC_PATHS = {
        "/.well-known/agent-card.json",
        "/.well-known/agent.json",
        "/health",
        "/ready",
    }

    @classmethod
    def _is_public_path(cls, path: str) -> bool:
        if path in cls._PUBLIC_PATHS:
            return True
        # Keep discovery and health sub-paths public too.
        return (
            path.startswith("/.well-known/")
            or path.startswith("/health/")
            or path.startswith("/ready/")
        )

    async def dispatch(self, request: Request, call_next):
        # Allow CORS preflight requests through so CORS middleware can respond
        # without being blocked by authentication.
        if request.method and request.method.upper() == "OPTIONS":
            return await call_next(request)

        # Keep discovery and health checks public.
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # For all other requests, validate the Authorization header when
        # auth is enabled.
        if not self.auth.validate(request.headers):
            logger.info(
                "Authentication failed for request path %s", request.url.path
            )
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        return await call_next(request)
