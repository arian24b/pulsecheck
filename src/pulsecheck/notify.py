import functools
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request


@functools.cache
def _docker_ok() -> bool:
    return bool(shutil.which("docker")) and subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def command(bin_: str, image: str) -> list[str]:
    """auto = docker image when docker works, else the shoutrrr binary; docker = force image; else a binary path."""
    if bin_ == "docker" or (bin_ == "auto" and _docker_ok()):
        return ["docker", "run", "--rm", image]
    return ["shoutrrr" if bin_ == "auto" else bin_]


def send_one(cmd: list[str], url: str, message: str) -> tuple[bool, str]:
    """Send one alert with shoutrrr. Returns (ok, detail); never raises."""
    try:
        # generous timeout: the first docker run pulls the image
        p = subprocess.run([*cmd, "send", "--url", url, "--message", message], capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    return p.returncode == 0, (p.stderr.strip() or p.stdout.strip())


def send(cmd: list[str], urls: list[str], message: str) -> None:
    for u in urls:
        ok, detail = send_one(cmd, u, message)
        if not ok:
            print(f"notify failed: {detail}", file=sys.stderr)  # never crash a run over an alert


def verify(cmd: list[str], url: str) -> tuple[bool, str]:
    """Ask shoutrrr whether the url is valid for its service (no message is sent)."""
    try:
        p = subprocess.run([*cmd, "verify", "--url", url], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    return p.returncode == 0, (p.stderr.strip() or p.stdout.strip()).splitlines()[0] if (p.stderr or p.stdout).strip() else ""


SHOUTRRR_VERSION = "0.21.2"


def download_shoutrrr(dest: str = "/tmp/pulsecheck-bin", version: str = SHOUTRRR_VERSION) -> str:
    """Fetch the shoutrrr binary from its GitHub release (sha256 checked against the release's checksums.txt).
    For places that have neither Docker nor an installed binary, such as Vercel functions. Cached in `dest`."""
    path = os.path.join(dest, "shoutrrr")
    if os.access(path, os.X_OK):
        return path
    arch = {"x86_64": "amd64", "aarch64": "arm64v8", "arm64": "arm64v8"}.get(platform.machine())
    if arch is None:
        raise RuntimeError(f"no shoutrrr build for {platform.machine()}")
    base = f"https://github.com/nicholas-fedor/shoutrrr/releases/download/v{version}/"
    name = f"shoutrrr_linux_{arch}_{version}.tar.gz"
    data = urllib.request.urlopen(base + name, timeout=60).read()
    sums = urllib.request.urlopen(base + "checksums.txt", timeout=30).read().decode()
    expected = next((line.split()[0] for line in sums.splitlines() if line.endswith(name)), None)
    if expected is None or hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError("shoutrrr download failed its checksum")
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(fileobj=__import__("io").BytesIO(data)) as tf, open(path, "wb") as out:
        out.write(tf.extractfile("shoutrrr").read())
    os.chmod(path, 0o755)
    return path
