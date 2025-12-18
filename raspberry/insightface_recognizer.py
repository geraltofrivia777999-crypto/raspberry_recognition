import io
import logging
from typing import Optional

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from raspberry.model_registry import BaseRecognizer

logger = logging.getLogger(__name__)


class InsightFaceRecognizer(BaseRecognizer):
    """
    Face embedding generator using InsightFace library.
    Uses the buffalo_l model for face detection and recognition.
    """

    name = "insightface"

    def __init__(self, model_name: str = "buffalo_l", det_size: tuple = (640, 640)):
        """
        Initialize InsightFace recognizer.

        Args:
            model_name: Model name to use (default: buffalo_l)
            det_size: Detection size for face detection (default: (640, 640))
        """
        self.model_name = model_name
        self.det_size = det_size

        # Initialize FaceAnalysis app
        self.app = FaceAnalysis(name=model_name, providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=det_size)

        logger.info(
            "InsightFaceRecognizer loaded model %s with det_size=%s",
            model_name,
            det_size,
        )

    def embed(self, image_bytes: bytes) -> np.ndarray:
        """
        Extract face embedding from image bytes.

        Args:
            image_bytes: Image data as bytes

        Returns:
            Face embedding as numpy array (512-dimensional vector)

        Raises:
            ValueError: If no face is detected in the image
        """
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Failed to decode image")

        # Detect faces and extract embeddings
        faces = self.app.get(img)

        if len(faces) == 0:
            raise ValueError("No face detected in image")

        # Use the first detected face
        face = faces[0]

        # Get the embedding (normed_embedding is already normalized)
        embedding = face.normed_embedding

        return embedding.astype(np.float32)
