import functools
import shutil
import subprocess
import sys


@functools.cache
def _docker_ok() -> bool:
    return bool(shutil.which("docker")) and subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def command(bin_: str, image: str) -> list[str]:
    """auto = docker image when docker works, else the shoutrrr binary; docker = force image; else a binary path."""
    if bin_ == "docker" or (bin_ == "auto" and _docker_ok()):
        return ["docker", "run", "--rm", image]
    return ["shoutrrr" if bin_ == "auto" else bin_]


def send(cmd: list[str], urls: list[str], message: str) -> None:
    for u in urls:
        try:
            # generous timeout: the first docker run pulls the image
            p = subprocess.run([*cmd, "send", "--url", u, "--message", message], capture_output=True, text=True, timeout=180)
            if p.returncode:
                print(f"notify failed: {p.stderr.strip() or p.stdout.strip()}", file=sys.stderr)
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"notify failed: {e}", file=sys.stderr)  # never crash a run over an alert
