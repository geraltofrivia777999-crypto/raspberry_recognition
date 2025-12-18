import argparse
import logging
from datetime import datetime

import requests

from config import PiSettings
from usb_camera_client import USBCameraClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def capture_frame(device_index: int) -> bytes:
    camera = USBCameraClient(device_index)
    try:
        frame = camera.read_frame()
        if not frame:
            raise RuntimeError("No frame captured from USB camera")
        _, frame_bytes = frame
        return frame_bytes
    finally:
        camera.release()


def send_to_server(api_base_url: str, device_id: str, person_name: str, frame_bytes: bytes) -> dict:
    url = api_base_url.rstrip("/") + "/raspberry/upload-capture"
    data = {"person_name": person_name, "captured_at": datetime.utcnow().isoformat()}
    headers = {"X-Device-Id": device_id}
    files = {"image": ("capture.jpg", frame_bytes, "image/jpeg")}
    response = requests.post(url, data=data, files=files, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Test uploader: capture a single USB frame and push to server.")
    parser.add_argument("--name", default="test-user", help="Person name to attach to the capture.")
    parser.add_argument("--server", dest="server", help="API base URL of the backend.")
    parser.add_argument("--device-id", dest="device_id", help="Device id header value.")
    parser.add_argument("--camera-index", dest="camera_index", type=int, help="USB camera index.")
    args = parser.parse_args()

    settings = PiSettings()
    api_base_url = args.server or settings.api_base_url
    device_id = args.device_id or settings.device_id
    camera_index = args.camera_index if args.camera_index is not None else settings.usb_device_index

    logger.info("Capturing frame from USB camera index=%s", camera_index)
    frame_bytes = capture_frame(camera_index)
    logger.info("Captured %s bytes, sending to %s", len(frame_bytes), api_base_url)

    payload = send_to_server(api_base_url, device_id, args.name, frame_bytes)
    logger.info("Server response: %s", payload)
    print(payload)


if __name__ == "__main__":
    main()
