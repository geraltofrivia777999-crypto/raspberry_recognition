
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class PiSettings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        protected_namespaces=()  # Отключаем защиту namespace для model_
    )

    api_base_url: str = "http://185.22.152.208:80"
    device_id: str = "pi-001"
    rtsp_url: str = "rtsp://user:pass@camera/stream"
    usb_device_index: int = 0
    facenet_model_path: str = "facenet.onnx"
    insightface_model_name: str = "buffalo_l"
    insightface_det_size: tuple = (640, 640)  # Увеличен для лучшей точности (особенно для RTSP)
    threshold: float = 0.6
    gpio_pin: int = 17
    gpio_pulse_ms: int = 800
    gpio_chip: str = "gpiochip0"
    sync_interval_sec: int = 300
    cache_path: str = "raspberry_cache.json"
    token: str | None = None
    model_name: str = "insightface"
    access_cooldown_sec: float = 5.0  # Cooldown между срабатываниями (секунды)
    local_users_dir: str = "local_users"  # Папка с локальными фото админов

    # Exit Button Configuration
    exit_button_enabled: bool = True  # Включить кнопку выхода
    exit_button_pin: int = 27  # GPIO пин для кнопки выхода
    exit_button_debounce_ms: int = 200  # Задержка anti-bounce (мс)

    # Performance optimization
    rtsp_frame_skip: int = 5  # Обрабатывать каждый N-й кадр для RTSP (1 = все кадры, 5 = каждый 5-й)
    rtsp_threshold: float = 0.5  # Порог для RTSP (с улучшенной обработкой можем снизить)
