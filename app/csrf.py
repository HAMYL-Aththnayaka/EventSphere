import secrets

from starlette.responses import JSONResponse


SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class CSRFMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        session = scope["session"]
        session.setdefault("csrf_token", secrets.token_urlsafe(32))

        if scope["method"].upper() not in SAFE_METHODS:
            headers = dict(scope.get("headers", []))
            submitted_token = headers.get(b"x-csrf-token", b"").decode()

            if not secrets.compare_digest(
                submitted_token,
                session["csrf_token"]
            ):
                response = JSONResponse(
                    {"detail": "Invalid or missing CSRF token."},
                    status_code=403
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
