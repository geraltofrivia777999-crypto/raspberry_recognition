import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ExitButton:
    """
    Exit button handler using gpiod.
    Monitors a GPIO pin connected to an exit button.
    When button is pressed, triggers the door unlock mechanism.
    """

    def __init__(
        self,
        pin: int,
        on_press: Callable[[], None],
        chip: str = "gpiochip0",
        consumer: str = "exit-button",
        debounce_ms: int = 200,
    ):
        """
        Initialize exit button handler.

        Args:
            pin: GPIO pin number for exit button
            on_press: Callback function to call when button is pressed
            chip: GPIO chip name (default: gpiochip0)
            consumer: Consumer name for GPIO line
            debounce_ms: Debounce delay in milliseconds
        """
        self.pin = pin
        self.on_press = on_press
        self.chip_name = chip
        self.consumer = consumer
        self.debounce_ms = debounce_ms
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.mode = "none"
        self.line_request = None
        self._last_press_time = 0.0

    def start(self) -> None:
        """Start monitoring the exit button in a background thread"""
        if self.running:
            logger.warning("Exit button already running")
            return

        # Try to initialize GPIO
        if not self._init_gpio():
            logger.warning("Exit button GPIO not available, button will not work")
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_button, daemon=True)
        self.thread.start()
        logger.info("Exit button started on GPIO pin %s", self.pin)

    def stop(self) -> None:
        """Stop monitoring the exit button"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self._cleanup_gpio()
        logger.info("Exit button stopped")

    def _init_gpio(self) -> bool:
        """Initialize GPIO for exit button (input with pull-up)"""
        try:
            import gpiod  # type: ignore
        except ImportError:
            logger.warning("gpiod not available for exit button")
            return False

        # Try gpiod v2 API
        if hasattr(gpiod, "LineSettings") and hasattr(gpiod, "line"):
            try:
                # Try different chip paths
                chip = None
                for path in (f"/dev/{self.chip_name}", self.chip_name, "/dev/gpiochip0", "gpiochip0"):
                    try:
                        chip = gpiod.Chip(path)
                        break
                    except (FileNotFoundError, PermissionError, OSError):
                        continue

                if chip is None:
                    logger.error("Cannot open GPIO chip for exit button")
                    return False

                # Configure as INPUT with PULL_UP (button connects to GND)
                line_config = {
                    self.pin: gpiod.LineSettings(
                        direction=gpiod.line.Direction.INPUT,
                        bias=gpiod.line.Bias.PULL_UP,  # Pull-up resistor
                    )
                }

                request = chip.request_lines(
                    consumer=self.consumer,
                    config=line_config,
                )

                self.line_request = request
                self.mode = "v2"
                logger.info("Exit button GPIO initialized on pin %s", self.pin)
                return True

            except Exception as exc:
                logger.error("Failed to initialize exit button GPIO: %s", exc)
                return False

        logger.error("gpiod v2 API not found for exit button")
        return False

    def _monitor_button(self) -> None:
        """Monitor button state in a loop (runs in background thread)"""
        import gpiod  # type: ignore

        logger.info("Exit button monitoring started")

        while self.running:
            try:
                if self.mode == "v2" and self.line_request:
                    # Read button state (LOW = pressed, HIGH = released)
                    value = self.line_request.get_value(self.pin)

                    # Button pressed (connected to GND, so value is INACTIVE/0)
                    if value == gpiod.line.Value.INACTIVE:
                        current_time = time.time()

                        # Debounce: ignore if pressed too soon after last press
                        if current_time - self._last_press_time > (self.debounce_ms / 1000):
                            logger.info("🔘 Exit button pressed!")
                            self._last_press_time = current_time

                            # Call the callback (trigger door unlock)
                            try:
                                self.on_press()
                            except Exception as exc:
                                logger.error("Error in exit button callback: %s", exc)

                            # Wait a bit to avoid multiple triggers
                            time.sleep(self.debounce_ms / 1000)

                # Small delay to avoid CPU spinning
                time.sleep(0.05)  # Check button every 50ms

            except Exception as exc:
                logger.error("Error monitoring exit button: %s", exc)
                time.sleep(0.5)

        logger.info("Exit button monitoring stopped")

    def _cleanup_gpio(self) -> None:
        """Cleanup GPIO resources"""
        try:
            if self.mode == "v2" and self.line_request:
                try:
                    self.line_request.release()
                except Exception:
                    try:
                        self.line_request.close()
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("Exit button GPIO cleanup failed: %s", exc)
