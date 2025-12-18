import logging
import time

from config import PiSettings
from pipeline import AccessController
from usb_camera_client import USBCameraClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    settings = PiSettings()
    controller = AccessController(settings)
    camera = USBCameraClient(settings.usb_device_index)

    # Обязательный первичный sync: тянем пользователей/фото, считаем эмбеддинги локально.
    while True:
        try:
            controller.refresh_from_cloud()
            logger.info("Initial sync completed")
            break
        except Exception as exc:
            logger.error("Initial sync failed, retrying in 5s: %s", exc)
            time.sleep(5)

    last_sync = time.time()
    try:
        while True:
            now = time.time()
            if now - last_sync > settings.sync_interval_sec:
                try:
                    controller.refresh_from_cloud()
                    last_sync = now
                except Exception as exc:
                    logger.warning("Sync failed, will retry later: %s", exc)
            try:
                controller.run_once(camera)
            except Exception as exc:
                logger.error("Processing failed: %s", exc)
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Stopping controller")
    finally:
        camera.release()
        controller.gpio.cleanup()


if __name__ == "__main__":
    main()
