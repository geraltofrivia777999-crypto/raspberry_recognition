import logging
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class RTSPClient:
    def __init__(self, url: str, resize_width: int = 800):
        self.url = url
        self.resize_width = resize_width  # Увеличено для лучшего качества
        self.capture: Optional[cv2.VideoCapture] = None
        self.frame_counter = 0

    def connect(self) -> None:
        self.capture = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        if self.capture:
            # Оптимизация для баланса скорости и качества
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Минимальный буфер для низкой задержки
            self.capture.set(cv2.CAP_PROP_FPS, 10)  # Меньше FPS = лучшее качество каждого кадра
            # Запросить максимально возможное разрешение от камеры
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        if not self.capture or not self.capture.isOpened():
            raise RuntimeError("Unable to open RTSP stream")
        logger.info("RTSP connected: %s (processing at %dpx width)", self.url, self.resize_width)

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

        # Resize для лучшего качества
        if self.resize_width and frame.shape[1] != self.resize_width:
            height, width = frame.shape[:2]
            new_height = int(height * (self.resize_width / width))
            frame = cv2.resize(frame, (self.resize_width, new_height), interpolation=cv2.INTER_CUBIC)

        # Улучшение качества для лучшего распознавания RTSP
        # 1. Денойзинг для удаления артефактов сжатия
        frame = cv2.fastNlMeansDenoisingColored(frame, None, 3, 3, 7, 21)

        # 2. CLAHE для улучшения контраста
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        frame = cv2.merge([l, a, b])
        frame = cv2.cvtColor(frame, cv2.COLOR_LAB2BGR)

        # 3. Увеличение резкости (unsharp mask)
        gaussian = cv2.GaussianBlur(frame, (0, 0), 2.0)
        frame = cv2.addWeighted(frame, 1.5, gaussian, -0.5, 0)

        ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 98])
        if not ret:
            return None
        return True, buf.tobytes()

    def clear_buffer(self, num_frames: int = 10) -> None:
        """
        Clear buffered frames by reading and discarding them.
        This helps prevent processing old frames after recognition.

        Args:
            num_frames: Number of frames to discard (default: 10)
        """
        if not self.capture:
            return

        logger.debug("Clearing RTSP buffer (%d frames)", num_frames)
        for _ in range(num_frames):
            self.capture.grab()  # Read and discard frame

    def release(self) -> None:
        if self.capture:
            self.capture.release()
