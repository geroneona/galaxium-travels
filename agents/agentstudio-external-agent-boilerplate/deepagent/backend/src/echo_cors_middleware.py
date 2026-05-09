from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class EchoCORSMiddleware(BaseHTTPMiddleware):
    """Echo back `Origin` when allowed; handle simple preflight responses."""

    def __init__(
        self,
        app,
        allowed_origins=None,
        allow_credentials=True,
        allow_methods=("*",),
        allow_headers=("*",),
    ):
        super().__init__(app)
        self.allowed = set(allowed_origins or [])
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method == "OPTIONS":
            resp = Response(status_code=204)
            if origin and ("*" in self.allowed or origin in self.allowed):
                resp.headers["Access-Control-Allow-Origin"] = (
                    origin if origin != "*" else "*"
                )
                if self.allow_credentials:
                    resp.headers["Access-Control-Allow-Credentials"] = "true"
                resp.headers["Access-Control-Allow-Methods"] = ",".join(
                    self.allow_methods
                )
                resp.headers["Access-Control-Allow-Headers"] = ",".join(
                    self.allow_headers
                )
            return resp

        response = await call_next(request)
        if origin and ("*" in self.allowed or origin in self.allowed):
            response.headers["Access-Control-Allow-Origin"] = (
                origin if origin != "*" else "*"
            )
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = ",".join(
                self.allow_methods
            )
            response.headers["Access-Control-Allow-Headers"] = ",".join(
                self.allow_headers
            )
        return response
