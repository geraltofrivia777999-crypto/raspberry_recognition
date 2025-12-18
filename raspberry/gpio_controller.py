import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class GPIOController:
    """
    Minimal GPIO driver using libgpiod.
    Prefers gpiod v2 API (request_lines); falls back to v1 (Chip/get_line).
    If gpiod is missing/unavailable, actions are only logged.
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

        # Prefer v2 API (gpiod>=2) if present (LineSettings + request_lines signature like in your working code).
        if hasattr(gpiod, "LineSettings") and hasattr(gpiod, "line"):
            try:
                chip = None
                for name in (self.chip_name, f"/dev/{self.chip_name}", "0"):
                    try:
                        chip = gpiod.Chip(name)
                        break
                    except Exception:
                        continue
                if chip is None:
                    raise FileNotFoundError(f"Cannot open gpio chip {self.chip_name}")
                line_settings = {self.pin: gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT)}
                request = chip.request_lines(
                    consumer=self.consumer,
                    config=line_settings,
                )
                self.line_request = request
                self.mode = "v2"
                try:
                    chip_name = chip.name
                except Exception:
                    chip_name = self.chip_name
                logger.info("GPIO initialized via gpiod v2 on %s pin %s", chip_name, self.pin)
                return
            except Exception as exc:
                logger.warning("Failed to init gpiod v2 API: %s", exc)

        # Fallback to v1 API.
        try:
            import gpiod  # type: ignore

            chip = gpiod.Chip(self.chip_name, gpiod.Chip.OPEN_BY_NAME)
            line = chip.get_line(self.pin)
            line.request(consumer=self.consumer, type=gpiod.LINE_REQ_DIR_OUT)
            self.line = line
            self.mode = "v1"
            logger.info("GPIO initialized via gpiod v1 on %s pin %s", self.chip_name, self.pin)
        except Exception as exc:
            logger.error("Failed to init gpiod v1 API: %s. GPIO actions will be logged only.", exc)
            self.mode = "none"

    def trigger(self) -> None:
        if self.mode == "v2" and self.line_request:
            try:
                import gpiod  # type: ignore

                self.line_request.set_value(self.pin, gpiod.line.Value.ACTIVE)
                time.sleep(self.pulse_ms / 1000)
                self.line_request.set_value(self.pin, gpiod.line.Value.INACTIVE)
            except Exception as exc:
                logger.error("GPIO trigger failed (v2): %s", exc)
        elif self.mode == "v1" and self.line:
            try:
                self.line.set_value(1)
                time.sleep(self.pulse_ms / 1000)
                self.line.set_value(0)
            except Exception as exc:
                logger.error("GPIO trigger failed (v1): %s", exc)
        else:
            logger.info("GPIO trigger simulated on %s pin %s for %sms", self.chip_name, self.pin, self.pulse_ms)

    def cleanup(self) -> None:
        try:
            if self.mode == "v1" and self.line:
                self.line.release()
            if self.mode == "v2" and self.line_request:
                try:
                    self.line_request.release()
                except Exception:
                    # gpiod v2 requests also have a close() method
                    try:
                        self.line_request.close()
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("GPIO cleanup failed: %s", exc)
