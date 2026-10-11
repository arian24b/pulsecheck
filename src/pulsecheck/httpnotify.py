"""Send alerts with plain HTTPS calls, for platforms that cannot run shoutrrr (Vercel, Cloudflare Workers).
Understands the shoutrrr URL format for a few services; everything else needs the real shoutrrr (CLI/CI/cron)."""
import base64
import json
import sys
from urllib.parse import parse_qs, unquote, urlparse

SUPPORTED = "telegram, discord, ntfy, generic"


def requests_for(url: str, text: str) -> list[dict]:
    """-> [{"url", "headers", "body"}]; raises ValueError for unsupported/invalid urls."""
    u = urlparse(url)
    q = {k: v[-1] for k, v in parse_qs(u.query).items()}
    js = {"Content-Type": "application/json"}
    if u.scheme == "telegram":
        token = unquote(u.username or "") + (":" + unquote(u.password) if u.password else "")  # bot tokens contain a colon
        chats = [c for c in q.get("chats", q.get("channels", "")).split(",") if c]
        if not token or not chats:
            raise ValueError("telegram url needs a token and ?chats=")
        return [{"url": f"https://api.telegram.org/bot{token}/sendMessage", "headers": js,
                 "body": json.dumps({"chat_id": c, "text": text})} for c in chats]
    if u.scheme == "discord":
        if not u.username or not u.hostname:
            raise ValueError("discord url must be discord://TOKEN@WEBHOOK_ID")
        return [{"url": f"https://discord.com/api/webhooks/{u.hostname}/{unquote(u.username)}", "headers": js,
                 "body": json.dumps({"content": text})}]
    if u.scheme == "ntfy":
        headers = {"Content-Type": "text/plain"}
        if u.username:
            cred = f"{unquote(u.username)}:{unquote(u.password or '')}".encode()
            headers["Authorization"] = "Basic " + base64.b64encode(cred).decode()
        scheme = q.get("scheme", "https")
        return [{"url": f"{scheme}://{u.netloc.rsplit('@', 1)[-1]}{u.path}", "headers": headers, "body": text}]
    if u.scheme == "generic":
        scheme = "http" if q.get("disabletls", "").lower() in ("yes", "true", "1") else "https"
        return [{"url": f"{scheme}://{u.netloc}{u.path}", "headers": js, "body": json.dumps({q.get("messagekey", "message"): text})}]
    raise ValueError(f"'{u.scheme}://' is not supported here (supported: {SUPPORTED}); use the CLI/CI/cron mode for all shoutrrr services")


async def send(post, urls: list[str], text: str) -> None:
    """post: async (url, headers, body) -> http status. Never raises: a failed alert must not fail the run."""
    for u in urls:
        try:
            for req in requests_for(u, text):
                status = await post(req["url"], req["headers"], req["body"])
                if status >= 400:
                    print(f"notify failed: HTTP {status} from {urlparse(req['url']).hostname}", file=sys.stderr)
        except Exception as e:
            print(f"notify failed: {type(e).__name__}: {e}", file=sys.stderr)
