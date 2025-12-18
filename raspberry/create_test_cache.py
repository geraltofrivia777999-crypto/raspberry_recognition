#!/usr/bin/env python3
"""
Create a test cache file for offline testing.
This allows you to test face recognition and GPIO without server connection.
"""
import json
import sys
from pathlib import Path

def create_test_cache():
    """Create a minimal test cache file"""

    # Minimal cache structure
    cache = {
        "users": [
            {
                "id": 1,
                "identifier": "test_user",
                "expires_at": None
            }
        ],
        "photos": [
            {
                "id": 1,
                "user_id": 1,
                "person_name": "test_user",
                "filename": "test.jpg",
                "url": "http://example.com/test.jpg"
            }
        ],
        "embeddings": [
            {
                "user_id": 1,
                "person_name": "test_user",
                "model_name": "insightface",
                "filename": "test.jpg",
                # Random 512-dim vector (will not match any real face)
                "vector": [0.0] * 512
            }
        ],
        "access_windows": [],
        "config": {
            "threshold": 0.6,
            "gpio_pin": 17,
            "gpio_pulse_ms": 800,
            "sync_interval_sec": 300
        }
    }

    # Save to file
    cache_path = Path(__file__).parent / "raspberry_cache.json"
    cache_path.write_text(json.dumps(cache, indent=2))

    print(f"✓ Test cache created at: {cache_path}")
    print(f"  - Users: {len(cache['users'])}")
    print(f"  - Embeddings: {len(cache['embeddings'])}")
    print("")
    print("Note: This cache contains dummy data and won't recognize real faces.")
    print("It's only for testing GPIO and camera functionality.")
    print("")
    print("To use real face recognition, you need to connect to the server.")

    return 0

if __name__ == "__main__":
    sys.exit(create_test_cache())
