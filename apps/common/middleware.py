import time


class RequestLoggingMiddleware:
    """
    Logs every HTTP request with:
      [CollabDocs] METHOD /path/  →  STATUS  (Xms)

    Registered first in settings.MIDDLEWARE so it wraps all other layers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ── Before view ──────────────────────────────────────────────────
        start_time = time.monotonic()

        response = self.get_response(request)

        # ── After view ───────────────────────────────────────────────────
        duration_ms = (time.monotonic() - start_time) * 1000

        # Colour-code status for readability in the terminal
        status_code = response.status_code
        if 200 <= status_code < 300:
            status_str = f"\033[92m{status_code}\033[0m"   # green
        elif 300 <= status_code < 400:
            status_str = f"\033[94m{status_code}\033[0m"   # blue
        elif 400 <= status_code < 500:
            status_str = f"\033[93m{status_code}\033[0m"   # yellow
        else:
            status_str = f"\033[91m{status_code}\033[0m"   # red

        print(
            f"[CollabDocs] {request.method:<7} {request.get_full_path():<50} "
            f"→  {status_str}  ({duration_ms:.1f}ms)"
        )

        return response
