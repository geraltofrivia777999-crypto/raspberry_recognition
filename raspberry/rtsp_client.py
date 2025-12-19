import logging
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class RTSPClient:
    def __init__(self, url: str, resize_width: int = 640):
        self.url = url
        self.resize_width = resize_width  # Уменьшаем разрешение для ускорения
        self.capture: Optional[cv2.VideoCapture] = None
        self.frame_counter = 0

    def connect(self) -> None:
        self.capture = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        if self.capture:
            # Настройки для ускорения RTSP
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Минимальный буфер
            self.capture.set(cv2.CAP_PROP_FPS, 15)  # Ограничить FPS
        if not self.capture or not self.capture.isOpened():
            raise RuntimeError("Unable to open RTSP stream")
        logger.info("RTSP connected: %s (resize to %dpx)", self.url, self.resize_width)

    def read_frame(self) -> Optional[Tuple[bool, bytes]]:
        if not self.capture:
            self.connect()
        assert self.capture

        # Пропускаем буферизованные кадры для уменьшения задержки
        self.capture.grab()  # Очистка буфера

        ok, frame = self.capture.read()
        if not ok:
            logger.warning("RTSP frame read failed, reconnecting")
            self.connect()
            ok, frame = self.capture.read()
        if not ok:
            return None

        # Resize для ускорения обработки и лучшего качества
        if self.resize_width and frame.shape[1] != self.resize_width:
            height, width = frame.shape[:2]
            new_height = int(height * (self.resize_width / width))
            frame = cv2.resize(frame, (self.resize_width, new_height))

        # Улучшение качества для лучшего распознавания
        # Увеличение контраста и резкости
        frame = cv2.convertScaleAbs(frame, alpha=1.1, beta=10)  # Яркость/контраст

        ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not ret:
            return None
        return True, buf.tobytes()

    def release(self) -> None:
        if self.capture:
            self.capture.release()
