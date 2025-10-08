from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Strict-Transport-Security (HSTS)
        # This tells browsers to always use HTTPS for the site.
        # max-age is set for 1 year. includeSubDomains applies it to all subdomains.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # X-Content-Type-Options
        # Prevents the browser from interpreting files as a different MIME type.
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        # Prevents the site from being rendered in an iframe, protecting against clickjacking.
        response.headers["X-Frame-Options"] = "DENY"

        # Content-Security-Policy (CSP)
        # A restrictive policy as a baseline. For a real frontend, this would need to be
        # configured to allow scripts, styles, etc., from trusted sources.
        # 'self' for resources from the same origin. 'none' as a default for others.
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self';"
        )

        return response