import io
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort
from PIL import Image

from raspberry.model_registry import BaseRecognizer

logger = logging.getLogger(__name__)


class FaceNetRecognizer(BaseRecognizer):
    """
    Face embedding generator using an ONNX FaceNet model.
    Expects an input compatible with facenet-pytorch (3x160x160, fixed_image_standardization).
    """

    name = "facenet"

    def __init__(self, model_path: str, providers: Optional[list[str]] = None):
        resolved = self._resolve_model_path(model_path)
        self.model_path = resolved
        # На Raspberry чаще всего доступен только CPUExecutionProvider
        provider_list = providers or ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(
            str(resolved),
            providers=provider_list,
        )
        self.input_name = self.session.get_inputs()[0].name
        logger.info(
            "FaceNetRecognizer loaded ONNX model from %s (providers=%s)",
            resolved,
            provider_list,
        )

    @staticmethod
    def _resolve_model_path(model_path: str) -> Path:
        candidates = [
            Path(model_path),
            Path(__file__).resolve().parent / model_path,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"FaceNet ONNX model not found. Tried: {[str(c) for c in candidates]}")

    def _preprocess(self, image_bytes: bytes) -> np.ndarray:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((160, 160))
        arr = np.asarray(img).astype(np.float32)
        # fixed_image_standardization: (x - 127.5) / 128
        arr = (arr - 127.5) / 128.0
        arr = np.transpose(arr, (2, 0, 1))  # HWC -> CHW
        arr = np.expand_dims(arr, 0)  # NCHW
        return arr

    def embed(self, image_bytes: bytes) -> np.ndarray:
        tensor = self._preprocess(image_bytes)
        outputs = self.session.run(None, {self.input_name: tensor})
        embedding = outputs[0]
        return np.squeeze(embedding, axis=0).astype(np.float32)
