"""HTTP client utilities."""

import json
import urllib.request
from typing import Any


def fetch_json(url: str) -> dict[str, Any]:
    """Fetch JSON from a URL.

    Args:
        url: The URL to fetch.

    Returns:
        Parsed JSON as a dictionary.

    Raises:
        URLError: If the request fails.
        JSONDecodeError: If response isn't valid JSON.
    """
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read()
        return json.loads(data)


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON to a URL.

    Args:
        url: The URL to post to.
        payload: Data to send as JSON.

    Returns:
        Parsed JSON response.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read())
