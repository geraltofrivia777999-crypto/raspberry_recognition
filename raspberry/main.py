import logging
import time

from config import PiSettings
from pipeline import AccessController
from rtsp_client import RTSPClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    settings = PiSettings()
    controller = AccessController(settings)
    rtsp = RTSPClient(settings.rtsp_url)
    try:
        controller.refresh_from_cloud()
    except Exception as exc:
        logger.warning("Initial sync failed, using cache if present: %s", exc)

    last_sync = time.time()
    try:
        while True:
            now = time.time()
            if now - last_sync > settings.sync_interval_sec:
                try:
                    controller.refresh_from_cloud()
                    last_sync = now
                except Exception as exc:
                    logger.warning("Sync failed: %s", exc)
            try:
                controller.run_once(rtsp)
            except Exception as exc:
                logger.error("Processing failed: %s", exc)
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Stopping controller")
    finally:
        rtsp.release()
        controller.gpio.cleanup()


if __name__ == "__main__":
    main()
