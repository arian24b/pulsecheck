import dataclasses
import json
import os
import re
import string
import types
import typing
from dataclasses import dataclass, field
from datetime import datetime, timedelta

EVENTS = ["down", "up", "degraded", "ssl_warn"]
# Message keys used by the code; users override any of them under `messages:` in the YAML.
MESSAGES = {
    "down": "🔴 {site} is DOWN: {error}",
    "reminder": "🔴 {site} is still DOWN after {minutes}m: {error}",
    "degraded": "🟡 {site} is slow ({ms}ms)",
    "up": "🟢 {site} is UP ({ms}ms) after {minutes}m",
    "ssl_warn": "🔒 {site}: TLS certificate expires in {days} days",
    "test": "pulsecheck test notification",
}
FIELDS = {"site", "event", "error", "ms", "minutes", "status", "tags", "days"}
DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _check_messages(m: dict[str, str]) -> None:
    for key, text in m.items():
        if key not in MESSAGES:
            raise ValueError(f"unknown message key '{key}' (valid: {', '.join(MESSAGES)})")
        bad = {f for _, f, _, _ in string.Formatter().parse(text) if f} - FIELDS
        if bad:
            raise ValueError(f"message '{key}': unknown placeholder {sorted(bad)} (valid: {sorted(FIELDS)})")


@dataclass
class Notify:
    urls: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=lambda: list(EVENTS))

    def __post_init__(self):
        bad = set(self.events) - set(EVENTS)
        if bad:
            raise ValueError(f"unknown event(s) {sorted(bad)} (valid: {', '.join(EVENTS)})")


@dataclass
class Site:
    name: str
    type: str = "http"
    url: str | None = None
    host: str | None = None
    port: int | None = None
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    expected_status: list[int] = field(default_factory=list)  # empty = any 2xx
    max_redirects: int = 5
    max_response_ms: int | None = None  # slower than this = down
    slow_ms: int | None = None  # slower than this = degraded
    timeout: int = 10
    down_after: int = 2  # consecutive failures before alerting
    interval: int = 5  # minutes
    tags: list[str] = field(default_factory=list)
    ssl_warn_days: int | None = None  # warn when the https certificate expires within this many days
    remind_every: int = 0  # minutes between repeated "still down" alerts, 0 = off
    ip_version: int | None = None  # 4 or 6: connect only over IPv4 / IPv6 (default: whatever the system picks)
    notify: Notify | None = None
    messages: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        _check_messages(self.messages)
        if self.ip_version not in (None, 4, 6):
            raise ValueError(f"{self.name}: ip_version must be 4 or 6")
        if self.type not in ("http", "tcp", "ping"):
            raise ValueError(f"{self.name}: unknown type {self.type}")
        if self.type == "http" and not self.url:
            raise ValueError(f"{self.name}: http needs url")
        if self.type in ("tcp", "ping") and not self.host:
            raise ValueError(f"{self.name}: {self.type} needs host")
        if self.type == "tcp" and not self.port:
            raise ValueError(f"{self.name}: tcp needs port")


@dataclass
class Maintenance:
    start: str  # "HH:MM" daily or "SUN 02:00" weekly, UTC
    duration: int  # minutes
    name: str = "maintenance"
    sites: list[str] = field(default_factory=list)  # empty = all

    def active(self, now: datetime, site: str) -> bool:
        if self.sites and site not in self.sites:
            return False
        parts = self.start.upper().split()
        hh, mm = map(int, parts[-1].split(":"))
        for back in range(8):
            day = now - timedelta(days=back)
            if len(parts) == 2 and DAYS[day.weekday()] != parts[0]:
                continue
            begin = day.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if begin <= now < begin + timedelta(minutes=self.duration):
                return True
        return False


@dataclass
class Otel:
    """Push check results as OpenTelemetry (OTLP/HTTP JSON) to a collector or any endpoint that accepts it."""

    endpoint: str  # base url, e.g. https://collector.example.com:4318 (/v1/metrics and /v1/logs are appended)
    headers: dict[str, str] = field(default_factory=dict)
    service_name: str = "pulsecheck"
    resource: dict[str, str] = field(default_factory=dict)  # extra resource attributes, e.g. {env: prod}
    metrics: bool = True
    logs: bool = True  # one log record per alert (down / up / degraded / ssl_warn / reminder)


@dataclass
class Config:
    state_file: str = "pulsecheck.db"
    shoutrrr_bin: str = "auto"  # auto | docker | path to a shoutrrr binary
    shoutrrr_image: str = "nickfedor/shoutrrr:0.21.2"
    notify: Notify = field(default_factory=Notify)
    messages: dict[str, str] = field(default_factory=dict)
    maintenance: list[Maintenance] = field(default_factory=list)
    otel: Otel | None = None
    sites: list[Site] = field(default_factory=list)

    def __post_init__(self):
        _check_messages(self.messages)
        names = [s.name for s in self.sites]
        if len(set(names)) != len(names):
            raise ValueError("duplicate site names")


def _coerce(tp, v, where):
    origin, args = typing.get_origin(tp), typing.get_args(tp)
    if origin in (typing.Union, types.UnionType):  # X | None
        return None if v is None else _coerce(next(a for a in args if a is not type(None)), v, where)
    if origin is list:
        if not isinstance(v, list):
            raise ValueError(f"{where}: expected a list")
        return [_coerce(args[0], x, f"{where}[{i}]") for i, x in enumerate(v)]
    if origin is dict:
        if not isinstance(v, dict):
            raise ValueError(f"{where}: expected a mapping")
        return {str(k): _coerce(args[1], x, f"{where}.{k}") for k, x in v.items()}
    if dataclasses.is_dataclass(tp):
        return build(tp, v, where)
    if tp is int:
        if isinstance(v, bool) or not (isinstance(v, int) or (isinstance(v, str) and v.strip().lstrip("-").isdigit())):
            raise ValueError(f"{where}: expected a number, got {v!r}")
        return int(v)
    if tp is str:
        if isinstance(v, (dict, list)) or v is None:
            raise ValueError(f"{where}: expected text, got {v!r}")
        return str(v)
    return v


def build(cls, data, where="config"):
    """dict -> dataclass with type checks and a clear error for unknown or missing keys."""
    if not isinstance(data, dict):
        raise ValueError(f"{where}: expected a mapping")
    fields = {f.name for f in dataclasses.fields(cls)}
    if set(data) - fields:
        raise ValueError(f"{where}: unknown key(s) {sorted(set(data) - fields)}")
    hints = typing.get_type_hints(cls)
    try:
        return cls(**{k: _coerce(hints[k], v, f"{where}.{k}") for k, v in data.items()})
    except TypeError as e:  # a required field is missing
        raise ValueError(f"{where}: {e}") from None


def from_dict(raw: dict) -> Config:
    raw = dict(raw)
    defaults = raw.pop("defaults", {}) or {}
    raw["sites"] = [{**defaults, **s} for s in raw.get("sites") or []]
    if not raw["sites"]:
        raise ValueError("no sites defined")
    return build(Config, raw)


def _expand(v, env):
    if isinstance(v, str):

        def sub(m):
            if m[1] not in env:
                raise ValueError(f"env var {m[1]} is not set")
            return env[m[1]]

        return re.sub(r"\$\{(\w+)\}", sub, v)
    if isinstance(v, list):
        return [_expand(i, env) for i in v]
    if isinstance(v, dict):
        return {k: _expand(i, env) for k, i in v.items()}
    return v


def env_names(text: str) -> set[str]:
    return set(re.findall(r"\$\{(\w+)\}", text))


def parse(text: str):
    """JSON (what the Cloudflare Worker ships, no YAML library needed) or YAML."""
    if text.lstrip().startswith("{"):
        try:
            return json.loads(text)
        except ValueError:
            pass
    from ruamel.yaml import YAML  # lazy: not installed inside the Worker

    return YAML(typ="safe").load(text)


def load(path: str, env=None) -> Config:
    with open(path) as f:
        return loads(f.read(), os.environ if env is None else env)


def loads(text: str, env) -> Config:
    return from_dict(_expand(parse(text), env))


def render(cfg: Config, s: Site | None, key: str, **fields) -> str:
    """Pick the template for `key` (site > global > built-in) and fill it in."""
    text = {**MESSAGES, **cfg.messages, **(s.messages if s else {})}[key]
    base = {"site": "", "event": key, "error": "", "ms": 0, "minutes": 0, "status": "", "tags": "", "days": ""}
    return text.format_map({**base, **fields})
