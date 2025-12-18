import logging
from typing import Optional, Tuple

import cv2

logger = logging.getLogger(__name__)


class RTSPClient:
    def __init__(self, url: str):
        self.url = url
        self.capture: Optional[cv2.VideoCapture] = None

    def connect(self) -> None:
        self.capture = cv2.VideoCapture(self.url)
        if not self.capture.isOpened():
            raise RuntimeError("Unable to open RTSP stream")
        logger.info("RTSP connected: %s", self.url)

    def read_frame(self) -> Optional[Tuple[bool, bytes]]:
        if not self.capture:
            self.connect()
        assert self.capture
        ok, frame = self.capture.read()
        if not ok:
            logger.warning("RTSP frame read failed, reconnecting")
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
