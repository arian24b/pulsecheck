"""Vercel entrypoint (WSGI). GET /api/cron runs the checks; Vercel Cron sends `Authorization: Bearer $CRON_SECRET`."""
import asyncio
import hmac
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from pulsecheck import web  # noqa: E402


def app(environ, start_response):
    def reply(status, body):
        data = json.dumps(body).encode()
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(data)))])
        return [data]

    if environ.get("PATH_INFO") != "/api/cron":
        return reply("200 OK", {"service": "pulsecheck"})
    secret = os.environ.get("CRON_SECRET", "")
    got = environ.get("HTTP_AUTHORIZATION", "")
    if not secret or not hmac.compare_digest(got, f"Bearer {secret}"):
        return reply("401 Unauthorized", {"error": "bad or missing CRON_SECRET"})
    try:
        return reply("200 OK", asyncio.run(web.cron()))
    except Exception as e:  # surface config/state problems in the Vercel logs and to the caller
        print(f"run failed: {type(e).__name__}: {e}", file=sys.stderr)
        return reply("500 Internal Server Error", {"error": f"{type(e).__name__}: {e}"})
