"""Run Mongo browser QA against an isolated, temporary Docker MongoDB."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from time import sleep
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
MONGO_IMAGE = "mongo:8.0"


def _run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, check=False, **kwargs)


def _npx_command() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"


def _mongo_uri(container_name: str) -> str:
    result = _run(["docker", "port", container_name, "27017/tcp"], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("Unable to read the temporary MongoDB port.")
    address = result.stdout.strip().splitlines()[0]
    host, separator, port = address.rpartition(":")
    if not host or not separator or not port.isdigit():
        raise RuntimeError("Temporary MongoDB returned an invalid host port.")
    return f"mongodb://127.0.0.1:{port}"


def _wait_until_ready(container_name: str) -> None:
    for _ in range(30):
        result = _run(
            ["docker", "exec", container_name, "mongosh", "--quiet", "--eval", "db.runCommand({ ping: 1 }).ok"],
            capture_output=True,
        )
        if result.returncode == 0 and result.stdout.strip() == "1":
            return
        sleep(1)
    raise RuntimeError("Temporary MongoDB did not become ready within 30 seconds.")


def main() -> int:
    container_name = f"945-mongo-qa-{uuid4().hex}"
    started = _run(
        ["docker", "run", "--detach", "--name", container_name, "-p", "127.0.0.1::27017", MONGO_IMAGE],
        capture_output=True,
    )
    if started.returncode != 0:
        print(started.stderr.strip() or "Unable to start temporary MongoDB.", file=sys.stderr)
        return 1

    try:
        _wait_until_ready(container_name)
        environment = os.environ | {"945_MONGODB_URI": _mongo_uri(container_name)}
        completed = _run(
            [_npx_command(), "playwright", "test", "--config=playwright.mongo.config.ts"],
            cwd=ROOT,
            env=environment,
        )
        return completed.returncode
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        _run(["docker", "rm", "--force", container_name], capture_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
