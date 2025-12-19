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
        # RTSP options для стабильного подключения и уменьшения ошибок декодирования
        import os
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay"

        self.capture = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        if self.capture:
            # Настройки для ускорения RTSP и стабильности
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Минимальный буфер
            self.capture.set(cv2.CAP_PROP_FPS, 10)  # Меньше FPS = стабильнее
            # Уменьшить разрешение с камеры для снижения битрейта
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not self.capture or not self.capture.isOpened():
            raise RuntimeError("Unable to open RTSP stream")
        logger.info("RTSP connected via TCP: %s (resize to %dpx)", self.url, self.resize_width)

    def read_frame(self) -> Optional[Tuple[bool, bytes]]:
        if not self.capture:
            self.connect()
        assert self.capture

        # Пропускаем буферизованные кадры для уменьшения задержки
        self.capture.grab()  # Очистка буфера

        # Пытаемся прочитать кадр, пропускаем поврежденные
        max_attempts = 3
        for attempt in range(max_attempts):
            ok, frame = self.capture.read()
            if ok and frame is not None and frame.size > 0:
                break
            # Если кадр поврежден, пропускаем и пытаемся следующий
            if attempt < max_attempts - 1:
                self.capture.grab()
        else:
            # Все попытки неудачны - переподключаемся
            logger.warning("RTSP frame read failed after %d attempts, reconnecting", max_attempts)
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
