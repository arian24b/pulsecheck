"""OpenTelemetry export without the SDK: OTLP/HTTP with JSON encoding (https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding).
Metrics: pulsecheck.up (1/0), pulsecheck.response_time (ms), pulsecheck.http.status_code, pulsecheck.ssl.days_remaining.
Logs: one record per alert. Works from the CLI, Vercel and Cloudflare because the HTTP call is injected."""

import json
import sys

SEVERITY = {"down": (17, "ERROR"), "reminder": (17, "ERROR"), "ssl_warn": (13, "WARN"), "degraded": (13, "WARN"), "up": (9, "INFO")}


def _attr(key, value):
    return {"key": key, "value": {"stringValue": str(value)}}


def _resource(o):
    return {"attributes": [_attr("service.name", o.service_name), *(_attr(k, v) for k, v in o.resource.items())]}


def metrics_payload(o, records: list[dict], now: float) -> dict:
    ts = str(int(now * 1e9))
    series: dict[str, tuple[str, list]] = {}

    def point(name, unit, rec, value):
        attrs = [_attr("site", rec["site"]), _attr("type", rec["type"]), _attr("state", rec["state"]), _attr("tags", ",".join(rec["tags"]))]
        series.setdefault(name, (unit, []))[1].append({"attributes": attrs, "timeUnixNano": ts, "asInt": str(int(value))})

    for r in records:
        point("pulsecheck.up", "1", r, r["state"] != "down")
        if r["ok"]:
            point("pulsecheck.response_time", "ms", r, r["ms"])
        if r["http_status"] is not None:
            point("pulsecheck.http.status_code", "1", r, r["http_status"])
        if r["ssl_days"] is not None:
            point("pulsecheck.ssl.days_remaining", "d", r, r["ssl_days"])
    metrics = [{"name": n, "unit": u, "gauge": {"dataPoints": pts}} for n, (u, pts) in series.items()]
    return {"resourceMetrics": [{"resource": _resource(o), "scopeMetrics": [{"scope": {"name": "pulsecheck"}, "metrics": metrics}]}]}


def logs_payload(o, events: list[dict], now: float) -> dict:
    ts = str(int(now * 1e9))
    recs = []
    for e in events:
        num, text = SEVERITY.get(e["event"], (9, "INFO"))
        recs.append(
            {
                "timeUnixNano": ts,
                "observedTimeUnixNano": ts,
                "severityNumber": num,
                "severityText": text,
                "body": {"stringValue": e["message"]},
                "attributes": [_attr("site", e["site"]), _attr("event", e["event"]), _attr("state", e["state"])],
            }
        )
    return {"resourceLogs": [{"resource": _resource(o), "scopeLogs": [{"scope": {"name": "pulsecheck"}, "logRecords": recs}]}]}


async def push(post, o, records: list[dict], events: list[dict], now: float) -> bool:
    """post: async (url, headers, body) -> status. Never raises: telemetry must not break a check run. True if all calls worked."""
    base = o.endpoint.rstrip("/")
    jobs, ok = [], True
    if o.metrics and records:
        jobs.append(("/v1/metrics", metrics_payload(o, records, now)))
    if o.logs and events:
        jobs.append(("/v1/logs", logs_payload(o, events, now)))
    for path, payload in jobs:
        try:
            status = await post(base + path, {"Content-Type": "application/json", **o.headers}, json.dumps(payload))
            if status >= 300:
                ok = False
                print(f"otel export failed: HTTP {status} from {path}", file=sys.stderr)
        except Exception as e:
            ok = False
            print(f"otel export failed: {type(e).__name__}: {e}", file=sys.stderr)
    return ok
