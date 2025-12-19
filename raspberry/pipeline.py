import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

import cache
import sync_client
from config import PiSettings
from gpio_controller import GPIOController
from model_registry import RecognizerRegistry, HashedRecognizer, cosine_similarity
from rtsp_client import RTSPClient

logger = logging.getLogger(__name__)


class AccessController:
    def __init__(self, settings: PiSettings):
        self.settings = settings
        self.recognizer_registry = RecognizerRegistry()

        # Cooldown mechanism to prevent multiple triggers
        self.last_trigger_time = 0.0
        self.cooldown_period = settings.access_cooldown_sec  # Период между срабатываниями

        # Consecutive trigger tracking to prevent repeated openings
        self.consecutive_triggers = 0
        self.max_consecutive_triggers = 3  # Maximum consecutive triggers allowed
        self.last_no_face_time = 0.0  # Track when we last saw no face

        # Register InsightFace recognizer
        try:
            from insightface_recognizer import InsightFaceRecognizer

            self.recognizer_registry.register(
                "insightface",
                InsightFaceRecognizer(
                    model_name=settings.insightface_model_name,
                    det_size=settings.insightface_det_size
                )
            )
        except Exception as exc:
            logger.warning("InsightFace not available on Pi: %s", exc)

        # Register FaceNet recognizer as fallback
        try:
            from facenet_recognizer import FaceNetRecognizer

            self.recognizer_registry.register("facenet", FaceNetRecognizer(settings.facenet_model_path))
        except Exception as exc:
            logger.warning("FaceNet not available on Pi: %s", exc)

        # Register hashed recognizer as last resort
        self.recognizer_registry.register("hashed", HashedRecognizer())

        try:
            self.recognizer = self.recognizer_registry.get(settings.model_name)
        except KeyError:
            logger.warning("Recognizer %s not found, using default", settings.model_name)
            self.recognizer = self.recognizer_registry.get_default()
        self.gpio = GPIOController(settings.gpio_pin, settings.gpio_pulse_ms, settings.gpio_chip)
        self.cache = cache.load_cache(settings.cache_path)

        # Load local users (admin photos) for offline access
        self._load_local_users()

    def refresh_from_cloud(self) -> None:
        payload = sync_client.fetch_sync_payload(self.settings)
        embeddings = self._build_embeddings_from_photos(payload.get("photos", []))
        payload["embeddings"] = embeddings
        self.cache = payload
        cache.save_cache(self.settings.cache_path, payload)
        config = payload.get("config", {})
        self.settings.threshold = float(config.get("threshold", self.settings.threshold))
        self.settings.gpio_pin = int(config.get("gpio_pin", self.settings.gpio_pin))
        self.settings.gpio_pulse_ms = int(config.get("gpio_pulse_ms", self.settings.gpio_pulse_ms))
        self.settings.sync_interval_sec = int(config.get("sync_interval_sec", self.settings.sync_interval_sec))
        logger.info(
            "Cache refreshed: %s photos -> %s embeddings, %s users",
            len(payload.get("photos", [])),
            len(payload.get("embeddings", [])),
            len(payload.get("users", [])),
        )

        # Reload local users after cloud refresh
        self._load_local_users()

    def _load_local_users(self) -> None:
        """
        Load local user photos from local_users/ directory for offline access.
        These users will always be recognized even without internet connection.
        """
        local_dir = Path(self.settings.local_users_dir)
        if not local_dir.exists():
            logger.info("Local users directory not found: %s", local_dir)
            return

        # Supported image formats
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
        local_photos = [f for f in local_dir.iterdir() if f.suffix.lower() in image_extensions]

        if not local_photos:
            logger.info("No local user photos found in %s", local_dir)
            return

        logger.info("Loading %s local user photos from %s", len(local_photos), local_dir)

        for photo_path in local_photos:
            try:
                # Read photo file
                img_bytes = photo_path.read_bytes()

                # Generate embedding
                vector = self.recognizer.embed(img_bytes)

                # Use filename (without extension) as person name
                person_name = photo_path.stem

                # Add to cache embeddings (check if not already exists)
                existing = any(
                    e.get("person_name") == person_name and e.get("is_local")
                    for e in self.cache.get("embeddings", [])
                )

                if not existing:
                    self.cache.setdefault("embeddings", []).append({
                        "user_id": None,  # Local users don't have server user_id
                        "person_name": person_name,
                        "vector": vector.tolist(),
                        "model_name": getattr(self.recognizer, "name", "unknown"),
                        "filename": photo_path.name,
                        "is_local": True,  # Mark as local user
                    })
                    logger.info("✓ Loaded local user: %s from %s", person_name, photo_path.name)
                else:
                    logger.debug("Local user %s already in cache", person_name)

            except Exception as exc:
                logger.error("Failed to load local photo %s: %s", photo_path, exc)

    def _build_embeddings_from_photos(self, photos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        embeddings: List[Dict[str, Any]] = []
        for photo in photos:
            try:
                img_bytes = sync_client.fetch_photo(self.settings, photo["url"])
                vector = self.recognizer.embed(img_bytes)
                embeddings.append(
                    {
                        "user_id": photo.get("user_id"),
                        "person_name": photo.get("person_name"),
                        "vector": vector.tolist(),
                        "model_name": getattr(self.recognizer, "name", "unknown"),
                        "filename": photo.get("filename"),
                    }
                )
            except Exception as exc:
                logger.error(
                    "Failed to build embedding for photo %s (user_id=%s, url=%s): %s",
                    photo.get("filename"),
                    photo.get("user_id"),
                    photo.get("url"),
                    exc,
                )
        return embeddings

    def _best_match(self, embedding: np.ndarray) -> Tuple[Optional[Dict[str, Any]], float]:
        best_score = 0.0
        best: Optional[Dict[str, Any]] = None
        expected_dim = int(embedding.shape[0]) if hasattr(embedding, "shape") else len(embedding)
        current_model = getattr(self.recognizer, "name", None)
        for emb in self.cache.get("embeddings", []):
            if current_model and emb.get("model_name") and emb["model_name"] != current_model:
                # Skip embeddings produced by a different model (e.g., hashed 128-dim vs FaceNet 512-dim).
                continue
            ref = np.array(emb["vector"], dtype=np.float32)
            if ref.shape[0] != expected_dim:
                logger.debug(
                    "Skipping embedding id=%s due to dim mismatch: %s vs %s",
                    emb.get("id"),
                    ref.shape[0],
                    expected_dim,
                )
                continue
            score = cosine_similarity(embedding, ref)
            if score > best_score:
                best_score = score
                best = emb
        return best, best_score

    def _is_within_schedule(self, user_id: int, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        day = now.weekday()
        current_time = now.time()
        windows = [w for w in self.cache.get("access_windows", []) if w["user_id"] == user_id]
        if not windows:
            return True
        for window in windows:
            if window["day_of_week"] != day:
                continue
            try:
                from datetime import time as _time

                start = _time.fromisoformat(str(window["start_time"]))
                end = _time.fromisoformat(str(window["end_time"]))
            except Exception:
                continue
            if start <= current_time <= end:
                return True
        return False

    def process_frame(self, frame_bytes: bytes) -> Dict[str, Any]:
        import time as _time
        start_time = _time.time()

        # First check if there's a face in the frame (fast check)
        # This prevents processing empty frames and false positives
        has_face = False
        if hasattr(self.recognizer, 'has_face'):
            has_face = self.recognizer.has_face(frame_bytes)
        else:
            # Fallback for recognizers without has_face method
            has_face = True

        # Reset consecutive triggers if no face detected for more than 2 seconds
        current_time = time.time()
        if not has_face:
            self.last_no_face_time = current_time
            if current_time - self.last_trigger_time > 2.0:
                if self.consecutive_triggers > 0:
                    logger.debug("No face detected - resetting consecutive triggers counter")
                    self.consecutive_triggers = 0
            return {"allowed": False, "score": 0.0, "user_identifier": None, "triggered": False, "no_face": True}

        # If we've had too many consecutive triggers, wait for reset
        if self.consecutive_triggers >= self.max_consecutive_triggers:
            logger.debug("Max consecutive triggers reached (%d), ignoring frame", self.max_consecutive_triggers)
            return {"allowed": False, "score": 0.0, "user_identifier": None, "triggered": False, "max_triggers": True}

        embedding = self.recognizer.embed(frame_bytes)
        match, score = self._best_match(embedding)

        processing_time = _time.time() - start_time

        allowed = match is not None and score >= self.settings.threshold
        user_identifier = None

        if match and allowed:
            user = None
            if match.get("user_id") is not None:
                user = next((u for u in self.cache.get("users", []) if u["id"] == match["user_id"]), None)
            user_identifier = user["identifier"] if user else match.get("person_name")

            # Check expiration only for server users (not local users)
            if not match.get("is_local"):
                expires_at = user.get("expires_at") if user else None
                if expires_at:
                    try:
                        from datetime import datetime as _dt
                        if _dt.fromisoformat(str(expires_at)) < _dt.utcnow():
                            allowed = False
                    except Exception:
                        pass
                if allowed and user:
                    allowed = self._is_within_schedule(match["user_id"])

        # Apply cooldown: only trigger if enough time has passed since last trigger
        if allowed:
            if current_time - self.last_trigger_time < self.cooldown_period:
                # Still in cooldown period
                logger.debug(
                    "Access granted for %s but in cooldown (%.1fs remaining)",
                    user_identifier,
                    self.cooldown_period - (current_time - self.last_trigger_time)
                )
                # Don't trigger GPIO, but still return success
                return {"allowed": True, "score": score, "user_identifier": user_identifier, "triggered": False}
            else:
                # Cooldown expired, trigger GPIO
                self.gpio.trigger()
                self.last_trigger_time = current_time
                self.consecutive_triggers += 1
                logger.info(
                    "✓ Access granted for %s (score=%.3f, processed in %.2fs, consecutive=%d)",
                    user_identifier, score, processing_time, self.consecutive_triggers
                )
        else:
            # Логируем только если есть совпадение но скор низкий
            if match:
                logger.debug("Access denied: score %.3f < threshold %.3f (processed in %.2fs)", score, self.settings.threshold, processing_time)

        status = "success" if allowed else "denied"
        event_payload = {
            "user_identifier": user_identifier,
            "status": status,
            "message": f"score={score:.3f}",
            "device_id": self.settings.device_id,
            "confidence": score,
        }
        try:
            # Only send events for server users (not local users)
            if not match or not match.get("is_local"):
                sync_client.send_event(self.settings, event_payload)
        except Exception as exc:
            logger.warning("Failed to push event: %s", exc)
        return {"allowed": allowed, "score": score, "user_identifier": user_identifier, "triggered": allowed}

    def run_once(self, rtsp_client: RTSPClient) -> Dict[str, Any]:
        frame = rtsp_client.read_frame()
        if not frame:
            logger.warning("No frame received")
            return {"allowed": False, "score": 0.0}
        _, frame_bytes = frame
        return self.process_frame(frame_bytes)
