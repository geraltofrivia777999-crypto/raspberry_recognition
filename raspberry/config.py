
from pydantic_settings import BaseSettings


class PiSettings(BaseSettings):
    api_base_url: str = "http://185.22.152.208:80"
    device_id: str = "pi-001"
    rtsp_url: str = "rtsp://user:pass@camera/stream"
    usb_device_index: int = 0
    facenet_model_path: str = "facenet.onnx"
    threshold: float = 0.6
    gpio_pin: int = 17
    gpio_pulse_ms: int = 800
    gpio_chip: str = "gpiochip0"
    sync_interval_sec: int = 300
    cache_path: str = "raspberry_cache.json"
    token: str | None = None
    model_name: str = "facenet"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
