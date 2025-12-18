import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class GPIOController:
    """
    Minimal GPIO driver using libgpiod.
    Prefers gpiod v2 API (request_lines); falls back to v1 (Chip/get_line).
    If gpiod is missing/unavailable, actions are only logged.

    Logic: GPIO17 is HIGH by default (door locked),
    and goes LOW when face is recognized (door unlocked).
    """

    def __init__(self, pin: int, pulse_ms: int, chip: str = "gpiochip0", consumer: str = "face-access"):
        self.pin = pin
        self.pulse_ms = pulse_ms
        self.chip_name = chip
        self.consumer = consumer
        self.mode: str = "none"
        self.line = None
        self.line_request = None
        self._init_gpio()

    def _init_gpio(self) -> None:
        try:
            import gpiod  # type: ignore
        except Exception as exc:
            logger.warning("gpiod not available: %s. GPIO actions will be logged only.", exc)
            return

        # Try gpiod v2 API (gpiod>=2.0)
        if hasattr(gpiod, "LineSettings") and hasattr(gpiod, "line"):
            try:
                # Try different chip paths
                chip = None
                chip_path = None
                for path in (f"/dev/{self.chip_name}", self.chip_name, "/dev/gpiochip0", "gpiochip0"):
                    try:
                        chip = gpiod.Chip(path)
                        chip_path = path
                        logger.debug("Opened GPIO chip at %s", path)
                        break
                    except (FileNotFoundError, PermissionError, OSError) as e:
                        logger.debug("Failed to open %s: %s", path, e)
                        continue

                if chip is None:
                    raise PermissionError(
                        f"Cannot open GPIO chip {self.chip_name}. "
                        f"Try: sudo usermod -a -G gpio $USER && sudo chmod 666 /dev/gpiochip0"
                    )

                # Configure the line as output
                line_config = {self.pin: gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT)}
                request = chip.request_lines(
                    consumer=self.consumer,
                    config=line_config,
                )
                self.line_request = request
                self.mode = "v2"

                # Set initial state to HIGH (door locked)
                try:
                    self.line_request.set_value(self.pin, gpiod.line.Value.ACTIVE)
                except Exception as exc:
                    logger.warning("Failed to set initial HIGH state (v2): %s", exc)

                logger.info("GPIO initialized via gpiod v2 on %s pin %s (initial state: HIGH)", chip_path, self.pin)
                return
            except PermissionError as exc:
                logger.error("GPIO permission denied: %s", exc)
                self.mode = "none"
                return
            except Exception as exc:
                logger.warning("Failed to init gpiod v2 API: %s", exc)
                # Don't try v1 fallback if v2 exists but failed - v1 won't work either
                self.mode = "none"
                return

        # No gpiod v2 available
        logger.error("gpiod v2 API not found. Please install: pip install gpiod")
        self.mode = "none"

    def trigger(self) -> None:
        """
        Trigger door unlock: set GPIO to LOW (door unlocked),
        wait for pulse_ms, then set back to HIGH (door locked).
        """
        if self.mode == "v2" and self.line_request:
            try:
                import gpiod  # type: ignore

                # Set to LOW (door unlocked)
                self.line_request.set_value(self.pin, gpiod.line.Value.INACTIVE)
                time.sleep(self.pulse_ms / 1000)
                # Set back to HIGH (door locked)
                self.line_request.set_value(self.pin, gpiod.line.Value.ACTIVE)
            except Exception as exc:
                logger.error("GPIO trigger failed (v2): %s", exc)
        elif self.mode == "v1" and self.line:
            try:
                # Set to LOW (door unlocked)
                self.line.set_value(0)
                time.sleep(self.pulse_ms / 1000)
                # Set back to HIGH (door locked)
                self.line.set_value(1)
            except Exception as exc:
                logger.error("GPIO trigger failed (v1): %s", exc)
        else:
            logger.info("GPIO trigger simulated: LOW for %sms on pin %s, then back to HIGH", self.pulse_ms, self.pin)

    def cleanup(self) -> None:
        """
        Cleanup GPIO resources. Ensures pin is set to HIGH (door locked) before releasing.
        """
        try:
            if self.mode == "v2" and self.line_request:
                try:
                    import gpiod  # type: ignore
                    # Ensure door is locked before cleanup
                    self.line_request.set_value(self.pin, gpiod.line.Value.ACTIVE)
                except Exception:
                    pass
                try:
                    self.line_request.release()
                except Exception:
                    # gpiod v2 requests also have a close() method
                    try:
                        self.line_request.close()
                    except Exception:
                        pass
            if self.mode == "v1" and self.line:
                try:
                    # Ensure door is locked before cleanup
                    self.line.set_value(1)
                except Exception:
                    pass
                self.line.release()
        except Exception as exc:
            logger.warning("GPIO cleanup failed: %s", exc)
