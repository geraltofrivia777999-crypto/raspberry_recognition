import logging
from typing import Any, Dict

import requests

from raspberry.config import PiSettings

logger = logging.getLogger(__name__)


def _auth_headers(settings: PiSettings) -> dict:
    headers = {"X-Device-Id": settings.device_id}
    if settings.token:
        headers["Authorization"] = f"Bearer {settings.token}"
    return headers


def fetch_sync_payload(settings: PiSettings) -> Dict[str, Any]:
    url = f"{settings.api_base_url.rstrip('/')}/raspberry/sync"
    resp = requests.get(url, headers=_auth_headers(settings), timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_photo(settings: PiSettings, url: str) -> bytes:
    if url.startswith("http://") or url.startswith("https://"):
        full_url = url
    else:
        full_url = f"{settings.api_base_url.rstrip('/')}{url}"
    resp = requests.get(full_url, headers=_auth_headers(settings), timeout=15)
    resp.raise_for_status()
    return resp.content


def send_event(settings: PiSettings, payload: Dict[str, Any]) -> None:
    url = f"{settings.api_base_url.rstrip('/')}/raspberry/events/log"
    resp = requests.post(url, headers=_auth_headers(settings), json=payload, timeout=10)
    if resp.status_code >= 400:
        logger.warning("Failed to push event: %s %s", resp.status_code, resp.text)
