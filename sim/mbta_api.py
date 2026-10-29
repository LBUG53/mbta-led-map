"""Minimal MBTA V3 API client (stdlib only).

The API key comes from the MBTA_API_KEY environment variable, loaded from
.env if it isn't already set. The key is sent as the x-api-key header, never
in the URL, so it can't leak into logs or error messages.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from . import ROOT

BASE = "https://api-v3.mbta.com"


def load_env(path=os.path.join(ROOT, ".env")):
    """Load KEY=VALUE lines from .env into os.environ (without overriding)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def api_key():
    """The MBTA API key from the environment or .env ('' if there is none). Never print the result."""
    load_env()
    return os.environ.get("MBTA_API_KEY", "")


class ApiError(Exception):
    """A request to the MBTA API failed. The message never includes request headers."""
    pass


def get(path, params=None, timeout=15):
    """GET a JSON:API resource. Returns (parsed_json, rate_limit_remaining)."""
    url = BASE + urllib.parse.quote(path, safe="/")  # stop IDs can contain spaces
    if params:
        url += "?" + urllib.parse.urlencode(params, safe="[],")
    headers = {"Accept": "application/vnd.api+json"}
    key = api_key()
    if key:
        headers["x-api-key"] = key
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body, resp.headers.get("x-ratelimit-remaining")
    except urllib.error.HTTPError as e:
        # Message deliberately excludes request headers.
        raise ApiError(f"HTTP {e.code} for {path}") from None
    except urllib.error.URLError as e:
        raise ApiError(f"Network error for {path}: {e.reason}") from None
