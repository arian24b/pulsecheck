"""Send alerts with plain HTTPS calls, for platforms that cannot run shoutrrr (Vercel, Cloudflare Workers).
Understands the shoutrrr URL format for a few services; everything else needs the real shoutrrr (CLI/CI/cron)."""

import base64
import json
import sys
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse


class Unsupported(ValueError):
    """The url scheme has no built-in HTTP implementation."""


SUPPORTED = "telegram, discord, slack, ntfy, gotify, pushover, mattermost, rocketchat, googlechat, zulip, bark, generic"


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
        return [
            {"url": f"https://api.telegram.org/bot{token}/sendMessage", "headers": js, "body": json.dumps({"chat_id": c, "text": text})}
            for c in chats
        ]
    if u.scheme == "discord":
        if not u.username or not u.hostname:
            raise ValueError("discord url must be discord://TOKEN@WEBHOOK_ID")
        return [
            {
                "url": f"https://discord.com/api/webhooks/{u.hostname}/{unquote(u.username)}",
                "headers": js,
                "body": json.dumps({"content": text}),
            }
        ]
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
    if u.scheme == "slack":
        tok = unquote(u.username or "")
        if tok == "hook" and u.hostname == "webhook":  # slack://hook:T..-B..-XXXX@webhook
            return [
                {
                    "url": "https://hooks.slack.com/services/" + unquote(u.password or "").replace("-", "/"),
                    "headers": js,
                    "body": json.dumps({"text": text}),
                }
            ]
        if tok and u.password and u.hostname:  # slack://xoxb:TOKEN@CHANNEL_ID
            return [
                {
                    "url": "https://slack.com/api/chat.postMessage",
                    "headers": {**js, "Authorization": f"Bearer {tok}-{unquote(u.password)}"},
                    "body": json.dumps({"channel": u.hostname.upper(), "text": text}),
                }
            ]
        raise ValueError("slack url must be slack://hook:T-B-X@webhook or slack://xoxb:TOKEN@CHANNEL")
    if u.scheme == "gotify":
        path = u.path.strip("/").split("/")
        scheme = "http" if q.get("disabletls", "").lower() in ("yes", "true", "1") else "https"
        prefix = "/".join(path[:-1])
        return [
            {
                "url": f"{scheme}://{u.netloc}/{prefix + '/' if prefix else ''}message?token={quote(path[-1])}",
                "headers": js,
                "body": json.dumps({"message": text, "priority": int(q.get("priority", 0))}),
            }
        ]
    if u.scheme == "pushover":
        body = {"token": unquote(u.password or ""), "user": u.hostname or "", "message": text}
        if q.get("devices"):
            body["device"] = q["devices"]
        if q.get("priority"):
            body["priority"] = q["priority"]
        return [
            {
                "url": "https://api.pushover.net/1/messages.json",
                "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                "body": urlencode(body),
            }
        ]
    if u.scheme in ("mattermost", "rocketchat"):
        scheme = "http" if q.get("disabletls", "").lower() in ("yes", "true", "1") else "https"
        parts = [p for p in u.path.split("/") if p]
        if u.scheme == "mattermost":
            hook, channel = "/".join(parts[:1]), parts[1] if len(parts) > 1 else q.get("channel")
        else:
            hook, channel = "/".join(parts[:2]), parts[2] if len(parts) > 2 else q.get("channel")
        if not hook or (u.scheme == "rocketchat" and len(parts) < 2):
            raise ValueError(f"{u.scheme} url needs the webhook token(s) in the path")
        body = {"text": text}
        if u.username:
            body["username"] = unquote(u.username)
        if channel:
            body["channel"] = channel if channel[0] in "#@" else "#" + channel
        return [{"url": f"{scheme}://{u.netloc.rsplit('@', 1)[-1]}/hooks/{hook}", "headers": js, "body": json.dumps(body)}]
    if u.scheme == "googlechat":
        return [{"url": f"https://{u.netloc}{u.path}?{u.query}", "headers": js, "body": json.dumps({"text": text})}]
    if u.scheme == "zulip":
        if not (u.username and u.password and u.hostname):
            raise ValueError("zulip url must be zulip://BOTMAIL:BOTKEY@HOST/?stream=S&topic=T")
        cred = f"{unquote(u.username)}:{unquote(u.password)}".encode()
        body = urlencode({"type": "stream", "to": q.get("stream", ""), "topic": q.get("topic", "pulsecheck"), "content": text})
        return [
            {
                "url": f"https://{u.netloc.rsplit('@', 1)[-1]}/api/v1/messages",
                "headers": {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": "Basic " + base64.b64encode(cred).decode(),
                },
                "body": body,
            }
        ]
    if u.scheme == "bark":
        key = unquote(u.password or "")
        if not key:
            raise ValueError("bark url must be bark://:DEVICEKEY@HOST/")
        scheme = "http" if q.get("scheme") == "http" else "https"
        return [
            {
                "url": f"{scheme}://{u.netloc.rsplit('@', 1)[-1]}{u.path.rstrip('/')}/push",
                "headers": js,
                "body": json.dumps({"device_key": key, "body": text}),
            }
        ]
    raise Unsupported(f"'{u.scheme}://' is not supported here (supported: {SUPPORTED}); use the CLI/CI/cron mode for all shoutrrr services")


async def send(post, urls: list[str], text: str, fallback=None) -> None:
    """post: async (url, headers, body) -> http status; fallback: async (url, text) for schemes handled elsewhere
    (the real shoutrrr). Never raises: a failed alert must not fail the run."""
    for u in urls:
        try:
            try:
                reqs = requests_for(u, text)
            except Unsupported:
                if fallback is None:
                    raise
                await fallback(u, text)
                continue
            for req in reqs:
                status = await post(req["url"], req["headers"], req["body"])
                if status >= 400:
                    print(f"notify failed: HTTP {status} from {urlparse(req['url']).hostname}", file=sys.stderr)
        except Exception as e:
            print(f"notify failed: {type(e).__name__}: {e}", file=sys.stderr)
