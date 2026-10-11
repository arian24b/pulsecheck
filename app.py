"""Vercel entrypoint (WSGI).
GET /api/cron    runs the checks (Vercel Cron sends `Authorization: Bearer $CRON_SECRET`); ?force=1 ignores intervals, ?tag=x filters
GET /api/status  current state of every site; ?format=json|text|md, ?tag=x. Same secret.
"""

import asyncio
import hmac
import json
import os
import sys
from urllib.parse import parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from pulsecheck import engine, web  # noqa: E402


def app(environ, start_response):
    def reply(status, body, ctype="application/json"):
        data = (body if isinstance(body, str) else json.dumps(body)).encode()
        start_response(status, [("Content-Type", ctype), ("Content-Length", str(len(data)))])
        return [data]

    path = environ.get("PATH_INFO")
    if path not in ("/api/cron", "/api/status"):
        return reply("200 OK", {"service": "pulsecheck"})
    secret = os.environ.get("CRON_SECRET", "")
    got = environ.get("HTTP_AUTHORIZATION", "")
    if not secret or not hmac.compare_digest(got, f"Bearer {secret}"):
        return reply("401 Unauthorized", {"error": "bad or missing CRON_SECRET"})
    q = parse_qs(environ.get("QUERY_STRING", ""))
    tag = (q.get("tag") or [None])[0]
    try:
        if path == "/api/cron":
            return reply("200 OK", asyncio.run(web.cron(tag=tag, force=q.get("force") == ["1"])))
        rows = asyncio.run(web.status(tag=tag))
        fmt = (q.get("format") or ["json"])[0]
        if fmt in ("md", "text"):
            return reply("200 OK", engine.format_status(rows, fmt == "md"), "text/plain; charset=utf-8")
        return reply("200 OK", rows)
    except Exception as e:  # surface config/state problems in the Vercel logs and to the caller
        print(f"run failed: {type(e).__name__}: {e}", file=sys.stderr)
        return reply("500 Internal Server Error", {"error": f"{type(e).__name__}: {e}"})
