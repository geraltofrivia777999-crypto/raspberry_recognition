import json
from pathlib import Path
from typing import Any, Dict


def load_cache(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"embeddings": [], "users": [], "access_windows": [], "photos": []}
    return json.loads(p.read_text())


def save_cache(path: str, payload: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2))
