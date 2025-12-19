import logging
import time

from config import PiSettings
from pipeline import AccessController
from rtsp_client import RTSPClient
from exit_button import ExitButton

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    settings = PiSettings()
    controller = AccessController(settings)
    rtsp = RTSPClient(settings.rtsp_url)

    # Initialize exit button (if enabled)
    exit_button = None
    if settings.exit_button_enabled:
        def on_button_press():
            """Callback when exit button is pressed"""
            logger.info("🔘 Exit button pressed - opening door")
            controller.gpio.trigger()

        exit_button = ExitButton(
            pin=settings.exit_button_pin,
            on_press=on_button_press,
            debounce_ms=settings.exit_button_debounce_ms,
        )
        exit_button.start()

    try:
        controller.refresh_from_cloud()
    except Exception as exc:
        logger.warning("Initial sync failed, using cache if present: %s", exc)

    last_sync = time.time()
    frame_counter = 0  # Счетчик кадров для пропуска

    try:
        while True:
            now = time.time()
            if now - last_sync > settings.sync_interval_sec:
                try:
                    controller.refresh_from_cloud()
                    last_sync = now
                except Exception as exc:
                    logger.warning("Sync failed: %s", exc)

            # Пропускаем кадры для ускорения RTSP обработки
            frame_counter += 1
            if frame_counter >= settings.rtsp_frame_skip:
                frame_counter = 0
                try:
                    # Используем RTSP threshold вместо обычного
                    original_threshold = controller.settings.threshold
                    controller.settings.threshold = settings.rtsp_threshold

                    result = controller.run_once(rtsp)

                    # Восстанавливаем оригинальный threshold
                    controller.settings.threshold = original_threshold

                    # If access was granted and door was triggered, clear buffer to prevent processing old frames
                    if result.get("triggered"):
                        logger.debug("Door triggered - clearing RTSP buffer to prevent repeated openings")
                        rtsp.clear_buffer(num_frames=15)  # Clear more frames for RTSP due to latency
                        frame_counter = 0  # Reset frame counter
                        time.sleep(1.0)  # Give extra time for person to move away
                except Exception as exc:
                    logger.error("Processing failed: %s", exc)

            time.sleep(0.05)  # Уменьшили с 0.1 до 0.05 для более частого чтения RTSP
    except KeyboardInterrupt:
        logger.info("Stopping controller")
    finally:
        if exit_button:
            exit_button.stop()
        rtsp.release()
        controller.gpio.cleanup()


if __name__ == "__main__":
    main()
