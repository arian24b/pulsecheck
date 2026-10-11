import os
import re
from datetime import datetime, timedelta

from ruamel.yaml import YAML
from pydantic import BaseModel, model_validator

EVENTS = ["down", "up", "degraded"]
DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


class Notify(BaseModel):
    urls: list[str] = []
    events: list[str] = EVENTS


class Site(BaseModel):
    name: str
    type: str = "http"
    url: str | None = None
    host: str | None = None
    port: int | None = None
    method: str = "GET"
    headers: dict[str, str] = {}
    body: str | None = None
    expected_status: list[int] = []  # empty = any 2xx
    max_redirects: int = 5
    max_response_ms: int | None = None  # slower than this = down
    slow_ms: int | None = None  # slower than this = degraded
    timeout: int = 10
    down_after: int = 2  # consecutive failures before alerting
    interval: int = 5  # minutes
    notify: Notify | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.type not in ("http", "tcp", "ping"):
            raise ValueError(f"{self.name}: unknown type {self.type}")
        if self.type == "http" and not self.url:
            raise ValueError(f"{self.name}: http needs url")
        if self.type in ("tcp", "ping") and not self.host:
            raise ValueError(f"{self.name}: {self.type} needs host")
        if self.type == "tcp" and not self.port:
            raise ValueError(f"{self.name}: tcp needs port")
        return self


class Maintenance(BaseModel):
    name: str = "maintenance"
    start: str  # "HH:MM" daily or "SUN 02:00" weekly, UTC
    duration: int  # minutes
    sites: list[str] = []  # empty = all

    def active(self, now: datetime, site: str) -> bool:
        if self.sites and site not in self.sites:
            return False
        parts = self.start.upper().split()
        hh, mm = map(int, parts[-1].split(":"))
        for back in (0, 1, 2, 3, 4, 5, 6, 7):
            day = now - timedelta(days=back)
            if len(parts) == 2 and DAYS[day.weekday()] != parts[0]:
                continue
            begin = day.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if begin <= now < begin + timedelta(minutes=self.duration):
                return True
        return False


class Config(BaseModel):
    state_file: str = "pulsecheck.db"
    shoutrrr_bin: str = "shoutrrr"
    notify: Notify = Notify()
    defaults: dict = {}
    maintenance: list[Maintenance] = []
    sites: list[Site]


def _expand(v):
    if isinstance(v, str):
        def sub(m):
            if m[1] not in os.environ:
                raise ValueError(f"env var {m[1]} is not set")
            return os.environ[m[1]]
        return re.sub(r"\$\{(\w+)\}", sub, v)
    if isinstance(v, list):
        return [_expand(i) for i in v]
    if isinstance(v, dict):
        return {k: _expand(i) for k, i in v.items()}
    return v


def load(path: str) -> Config:
    raw = _expand(YAML(typ="safe").load(open(path)))
    d = raw.get("defaults", {})
    raw["sites"] = [{**d, **s} for s in raw.get("sites", [])]
    cfg = Config(**raw)
    names = [s.name for s in cfg.sites]
    if len(set(names)) != len(names):
        raise ValueError("duplicate site names")
    return cfg
