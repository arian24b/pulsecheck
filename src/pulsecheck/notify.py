import subprocess
import sys


def send(bin_: str, urls: list[str], message: str) -> None:
    for u in urls:
        try:
            p = subprocess.run([bin_, "send", "--url", u, "--message", message], capture_output=True, text=True, timeout=60)
            if p.returncode:
                print(f"notify failed: {p.stderr.strip() or p.stdout.strip()}", file=sys.stderr)
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"notify failed: {e}", file=sys.stderr)  # never crash a run over an alert


def message(site: str, event: str, r, downtime_s: float) -> str:
    if event == "down":
        return f"🔴 {site} is DOWN: {r.error}"
    if event == "degraded":
        return f"🟡 {site} is slow ({r.ms}ms)"
    return f"🟢 {site} is UP ({r.ms}ms) after {int(downtime_s // 60)}m"
