import hashlib
import io
from abc import ABC, abstractmethod
from typing import Dict, Optional

import numpy as np
from PIL import Image


class BaseRecognizer(ABC):
    name: str = "base"

    @abstractmethod
    def embed(self, image_bytes: bytes) -> np.ndarray:
        raise NotImplementedError


class HashedRecognizer(BaseRecognizer):
    """
    Deterministic, lightweight recognizer. Replace with FaceNet/ONNX model later
    without changing the AccessController pipeline.
    """

    name = "hashed"

    def embed(self, image_bytes: bytes) -> np.ndarray:
        # Normalize image to reduce noise in hash.
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            resized = img.resize((64, 64))
            normalized = resized.tobytes()
        except Exception:
            normalized = image_bytes
        digest = hashlib.sha256(normalized).digest()
        floats = [b / 255 for b in digest]
        repeated = (floats * ((128 // len(floats)) + 1))[:128]
        return np.array(repeated, dtype=np.float32)


class RecognizerRegistry:
    def __init__(self):
        self._registry: Dict[str, BaseRecognizer] = {}
        self._default: Optional[str] = None

    def register(self, name: str, recognizer: BaseRecognizer) -> None:
        self._registry[name] = recognizer
        if not self._default:
            self._default = name

    def get(self, name: str) -> BaseRecognizer:
        if name not in self._registry:
            raise KeyError(f"Recognizer {name} is not registered")
        return self._registry[name]

    def get_default(self) -> BaseRecognizer:
        if not self._default:
            raise KeyError("No recognizer registered")
        return self._registry[self._default]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)
