#!/usr/bin/env python3
"""Safely check or renew the Instagram publishing token used by Macca.

Instagram Login tokens: refresh through graph.instagram.com, then update GitHub.
Facebook Page tokens: verify the configured Page, but do NOT use IG refresh.
The existing Instagram publication and metrics workflows are unchanged.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from urllib.parse import urlencode

REPOSITORY = "PkLavc/lab"
SECRET_NAME = "INSTAGRAM_ACCESS_TOKEN"
INSTAGRAM_REFRESH = "https://graph.instagram.com/refresh_access_token"
INSTAGRAM_ME = "https://graph.instagram.com/me"
FACEBOOK_ME = "https://graph.facebook.com/v26.0/me"


class TokenError(Exception):
    """A diagnostic safe to print without disclosing credentials."""


def graph_get(url: str, token: str, params: dict[str, str] | None = None) -> dict:
    suffix = ("?" + urlencode(params)) if params else ""
    request = urllib.request.Request(
        url + suffix,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "User-Agent": "MaccaTokenMaintenance/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        raise TokenError("Meta returned HTTP " + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise TokenError("Meta request failed (" + type(exc).__name__ + ")") from None
    if not isinstance(data, dict) or data.get("error"):
        raise TokenError("Meta rejected the request")
    return data


def identify_token(token: str, expected_page_id: str) -> tuple[str, str]:
    """A Page access token must never be sent through the Instagram Login refresh API."""
    try:
        result = graph_get(INSTAGRAM_ME, token, {"fields": "user_id,username"})
        identity = str(result.get("user_id") or result.get("id") or "").strip()
        if identity:
            return "instagram_login", identity
    except TokenError:
        pass

    try:
        result = graph_get(FACEBOOK_ME, token, {"fields": "id,name"})
    except TokenError:
        raise TokenError("Token invalid or unsupported; neither Instagram nor Page identity verified") from None
    identity = str(result.get("id") or "").strip()
    if not expected_page_id:
        raise TokenError("INSTAGRAM_PAGE_ID is required to verify Facebook Page tokens")
    if identity != expected_page_id:
        raise TokenError("Facebook token does not identify the configured Page; cannot rotate safely")
    return "facebook_page", identity


def verify_github_access(credential: str) -> dict[str, str]:
    if not credential:
        raise TokenError("Set INSTAGRAM_ROTATION_GITHUB_TOKEN (Secrets: Read and write on PkLavc/lab)")
    env = os.environ.copy()
    env["GH_TOKEN"] = credential
    try:
        check = subprocess.run(
            ["gh", "api", "repos/" + REPOSITORY + "/actions/secrets/public-key", "--jq", ".key_id"],
            env=env, text=True, capture_output=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise TokenError("Could not run GitHub Secrets permission check") from None
    if check.returncode != 0 or not check.stdout.strip():
        raise TokenError("GitHub credential cannot read Secrets in PkLavc/lab; check repository selection and Secrets permissions")
    return env


def renew(token: str, expected_id: str, gh_env: dict[str, str]) -> None:
    payload = graph_get(INSTAGRAM_REFRESH, token, {"grant_type": "ig_refresh_token"})
    replacement = str(payload.get("access_token") or "").strip()
    lifetime = int(payload.get("expires_in") or 0)
    if not replacement or lifetime < 14 * 86400:
        raise TokenError("Meta did not return a usable long-lived Instagram token")
    # Mask before any diagnostic or GitHub operation.
    print("::add-mask::" + replacement, flush=True)
    new_kind, new_id = identify_token(replacement, "")
    if new_kind != "instagram_login" or new_id != expected_id:
        raise TokenError("Meta renewed token does not match the existing Instagram account")
    try:
        put = subprocess.run(
            ["gh", "secret", "set", SECRET_NAME, "--repo", REPOSITORY],
            input=replacement + "\n", env=gh_env, capture_output=True,
            text=True, timeout=45, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise TokenError("Could not write renewed token to GitHub Actions Secrets") from None
    if put.returncode:
        raise TokenError("GitHub rejected the secret update; verify Secrets:write permission")
    print("Instagram token renewed and Macca publishing secret updated; expires_in_days=" + str(lifetime // 86400))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("check", "renew"))
    args = parser.parse_args()
    token = os.getenv(SECRET_NAME, "").strip()
    if not token:
        raise TokenError("Missing INSTAGRAM_ACCESS_TOKEN in the lab repository")
    # Verify permissions even in check-only mode, without modifying anything.
    kind, identity = identify_token(token, os.getenv("INSTAGRAM_PAGE_ID", "").strip())
    github_env = verify_github_access(os.getenv("INSTAGRAM_ROTATION_GITHUB_TOKEN", "").strip())
    if kind == "facebook_page":
        print("Macca uses a verified Facebook Page token. Instagram Login refresh is inapplicable; token left unchanged.")
        return 0
    print("Macca uses an Instagram Login token; GitHub Secrets read access verified.")
    if args.action == "check":
        print("Read-only check complete. Secrets:write will be exercised on first successful renewal.")
        return 0
    renew(token, identity, github_env)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TokenError as exc:
        print("::error::Instagram token maintenance failed: " + str(exc), file=sys.stderr)
        raise SystemExit(1) from None
