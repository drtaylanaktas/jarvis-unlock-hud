"""Shared config loader + Google API service builder (with token refresh)."""
from __future__ import annotations
import os
import time

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

_HERE = os.path.dirname(os.path.abspath(__file__))
CRED_PATH = os.path.join(_HERE, "credentials.json")
TOKEN_PATH = os.path.join(_HERE, "token.json")
_CONFIG_PATH = os.path.join(_HERE, "config.toml")
_EXAMPLE_PATH = os.path.join(_HERE, "config.example.toml")

_cfg_cache: dict | None = None


def load_config() -> dict:
    global _cfg_cache
    if _cfg_cache is None:
        path = _CONFIG_PATH if os.path.exists(_CONFIG_PATH) else _EXAMPLE_PATH
        with open(path, "rb") as f:
            _cfg_cache = tomllib.load(f)
    return _cfg_cache


def _credentials() -> Credentials:
    cfg = load_config()
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError("Not authorized with Google. Run: python core/google_auth.py")
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, cfg["google"]["scopes"])
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def service(api: str, version: str):
    """Build a Google API client (e.g. service('gmail', 'v1'))."""
    # static_discovery=True uses the bundled discovery doc (no network fetch).
    return build(api, version, credentials=_credentials(),
                 cache_discovery=False, static_discovery=True)


def with_retries(fn, *args, attempts: int = 3, **kwargs):
    """Run a sync Google call with retries (transient DNS/network hiccups)."""
    last = None
    for i in range(attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.6 * (i + 1))
    raise last
