import logging
from typing import Optional, Tuple

import cv2

logger = logging.getLogger(__name__)


class USBCameraClient:
    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.capture: Optional[cv2.VideoCapture] = None

    def connect(self) -> None:
        self.capture = cv2.VideoCapture(self.device_index)
        if not self.capture.isOpened():
            raise RuntimeError(f"Unable to open USB camera at index {self.device_index}")
        logger.info("USB camera connected: index=%s", self.device_index)

    def read_frame(self) -> Optional[Tuple[bool, bytes]]:
        if not self.capture:
            self.connect()
        assert self.capture
        ok, frame = self.capture.read()
        if not ok:
            logger.warning("USB camera frame read failed, reconnecting")
            self.connect()
            ok, frame = self.capture.read()
        if not ok:
            return None
        ret, buf = cv2.imencode(".jpg", frame)
        if not ret:
            return None
        return True, buf.tobytes()

    def release(self) -> None:
        if self.capture:
            self.capture.release()
