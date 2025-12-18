"""
Small helper to debug sync/photos fetching on Raspberry.
Usage: python raspberry/debug_sync.py --server http://host:8000 --limit 2
"""

import argparse
import sys

from raspberry.config import PiSettings
from raspberry.sync_client import fetch_photo, fetch_sync_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", help="Backend base URL (overrides api_base_url from settings)")
    parser.add_argument("--limit", type=int, default=3, help="How many photos to try downloading")
    args = parser.parse_args()

    settings = PiSettings()
    if args.server:
        settings.api_base_url = args.server

    print(f"Fetching sync payload from {settings.api_base_url}")
    payload = fetch_sync_payload(settings)
    photos = payload.get("photos", [])
    print(f"Photos in payload: {len(photos)}")
    if not photos:
        return 0
    for photo in photos[: args.limit]:
        url = photo.get("url")
        filename = photo.get("filename")
        print(f"Downloading {filename} from {url} ... ", end="", flush=True)
        try:
            buf = fetch_photo(settings, url)
            print(f"ok ({len(buf)} bytes)")
        except Exception as exc:
            print(f"FAILED: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
