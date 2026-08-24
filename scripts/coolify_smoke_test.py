#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch(url: str):
    request = Request(url, headers={"User-Agent": "ModelVillage-UAT-Smoke/1.0"})
    with urlopen(request, timeout=12, context=ssl.create_default_context()) as response:
        return response.status, dict(response.headers.items()), response.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url", help="Example: https://modelvillage.example.org")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    if not base.startswith("https://"):
        print("FAIL: production base URL must use https://")
        return 2

    checks = [
        ("Liveness", "/healthz", "application/json"),
        ("Readiness", "/readyz", "application/json"),
        ("Login", "/login", "text/html"),
        ("Manifest", "/manifest.json", "json"),
        ("Service worker", "/sw.js", "javascript"),
    ]

    failures = 0
    for label, path, expected_type in checks:
        try:
            status, headers, body = fetch(base + path)
            content_type = headers.get("Content-Type", "")
            ok = status == 200 and expected_type in content_type
            print(f"{'PASS' if ok else 'FAIL'} {label}: HTTP {status}, {content_type}")
            if not ok:
                failures += 1
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"FAIL {label}: {exc}")
            failures += 1

    try:
        status, headers, _body = fetch(base + "/login")
        required = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "Referrer-Policy": None,
            "Content-Security-Policy": None,
        }
        missing = []
        for key, expected in required.items():
            value = headers.get(key)
            if value is None or (expected is not None and value != expected):
                missing.append(key)
        if missing:
            print("FAIL Security headers: " + ", ".join(missing))
            failures += 1
        else:
            print("PASS Security headers")
    except Exception as exc:
        print(f"FAIL Security headers: {exc}")
        failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
