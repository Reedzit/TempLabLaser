import json
import os
import threading
from datetime import datetime

import cv2
import numpy as np


class CompositingManager:
    """Build a live image mosaic from camera frames using image registration.

    Hardware coordinates can be stored as metadata, but mosaic placement is
    intentionally driven by image-to-image registration so it is independent of
    camera/hexapod coordinate orientation.
    """

    def __init__(self, min_registration_response=0.15, feather_pixels=40):
        self.min_registration_response = min_registration_response
        self.feather_pixels = feather_pixels
        self.status = "No compositing session started"
        self.error = None
        self.tiles = []
        self.mosaic = None
        self.coverage = None
        self.last_registration = None
        self._lock = threading.Lock()

    def reset_session(self):
        with self._lock:
            self.status = "Compositing session reset"
            self.error = None
            self.tiles = []
            self.mosaic = None
            self.coverage = None
            self.last_registration = None

    def add_frame(self, frame, metadata=None):
        if frame is None:
            self.status = "No frame to composite"
            return False

        clean_frame = self._prepare_frame(frame)
        gray = self._to_registration_image(clean_frame)
        metadata = metadata or {}

        with self._lock:
            if not self.tiles:
                tile = self._make_tile(clean_frame, gray, np.array([0.0, 0.0]), 1.0, metadata)
                self.tiles.append(tile)
                self._rebuild_mosaic_locked()
                self.status = "Added first tile"
                self.error = None
                return True

            previous = self.tiles[-1]
            if previous["gray"].shape != gray.shape:
                self.status = "Frame rejected"
                self.error = "Frame size changed during compositing"
                return False

            shift, response = self._estimate_shift(previous["gray"], gray)
            self.last_registration = {
                "shift_x_px": float(shift[0]),
                "shift_y_px": float(shift[1]),
                "response": float(response),
            }

            if response < self.min_registration_response:
                self.status = "Frame rejected: low registration confidence"
                self.error = f"Registration response {response:.3f} below threshold"
                return False

            position = previous["position"] - np.array(shift, dtype=float)
            tile = self._make_tile(clean_frame, gray, position, response, metadata)
            self.tiles.append(tile)
            self._rebuild_mosaic_locked()
            self.status = f"Added tile {len(self.tiles)}"
            self.error = None
            return True

    def get_mosaic_preview(self, max_size=(760, 560)):
        with self._lock:
            if self.mosaic is None:
                return None
            preview = self.mosaic.copy()

        if max_size is None:
            return preview

        return self._fit_to_size(preview, max_size)

    def get_latest_tile(self, max_size=(380, 280)):
        with self._lock:
            if not self.tiles:
                return None
            frame = self.tiles[-1]["frame"].copy()

        if max_size is None:
            return frame

        return self._fit_to_size(frame, max_size)

    def get_status(self):
        with self._lock:
            registration = None if self.last_registration is None else dict(self.last_registration)
            return {
                "status": self.status,
                "error": self.error,
                "tile_count": len(self.tiles),
                "registration": registration,
                "mosaic_shape": None if self.mosaic is None else self.mosaic.shape,
            }

    def save_mosaic(self, output_path):
        with self._lock:
            if self.mosaic is None:
                self.status = "No mosaic to save"
                return False
            mosaic = self.mosaic.copy()
            manifest = self._build_manifest_locked()

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        ok = cv2.imwrite(output_path, mosaic)
        if not ok:
            self.status = "Mosaic save failed"
            self.error = output_path
            return False

        manifest_path = os.path.splitext(output_path)[0] + "_manifest.json"
        with open(manifest_path, "w") as handle:
            json.dump(manifest, handle, indent=2)

        self.status = f"Saved mosaic: {os.path.basename(output_path)}"
        self.error = None
        return True

    def generate_spiral_offsets(self, max_rings=5, step_mm=0.195):
        offsets = [(0.0, 0.0)]
        x = 0
        y = 0
        directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        direction_index = 0
        leg_length = 1

        while max(abs(x), abs(y)) < max_rings:
            for _ in range(2):
                dx, dy = directions[direction_index % 4]
                for _ in range(leg_length):
                    x += dx
                    y += dy
                    if max(abs(x), abs(y)) > max_rings:
                        return offsets
                    offsets.append((x * step_mm, y * step_mm))
                direction_index += 1
            leg_length += 1

        return offsets

    def _make_tile(self, frame, gray, position, response, metadata):
        return {
            "frame": frame,
            "gray": gray,
            "position": position,
            "response": float(response),
            "metadata": dict(metadata),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

    def _rebuild_mosaic_locked(self):
        min_x = min(tile["position"][0] for tile in self.tiles)
        min_y = min(tile["position"][1] for tile in self.tiles)
        max_x = max(tile["position"][0] + tile["frame"].shape[1] for tile in self.tiles)
        max_y = max(tile["position"][1] + tile["frame"].shape[0] for tile in self.tiles)

        padding = 20
        width = int(np.ceil(max_x - min_x)) + padding * 2
        height = int(np.ceil(max_y - min_y)) + padding * 2
        accumulator = np.zeros((height, width, 3), dtype=np.float32)
        weights = np.zeros((height, width, 1), dtype=np.float32)

        for tile in self.tiles:
            frame = self._as_bgr(tile["frame"]).astype(np.float32)
            frame_height, frame_width = frame.shape[:2]
            x0 = int(round(tile["position"][0] - min_x)) + padding
            y0 = int(round(tile["position"][1] - min_y)) + padding
            x1 = x0 + frame_width
            y1 = y0 + frame_height
            mask = self._make_feather_mask(frame_height, frame_width)

            accumulator[y0:y1, x0:x1] += frame * mask
            weights[y0:y1, x0:x1] += mask

        valid = weights[:, :, 0] > 0
        mosaic = np.zeros_like(accumulator, dtype=np.uint8)
        accumulator[valid] /= weights[valid]
        mosaic[valid] = np.clip(accumulator[valid], 0, 255).astype(np.uint8)

        self.mosaic = mosaic
        self.coverage = weights[:, :, 0]

    def _build_manifest_locked(self):
        return {
            "created": datetime.now().isoformat(timespec="seconds"),
            "tile_count": len(self.tiles),
            "min_registration_response": self.min_registration_response,
            "tiles": [
                {
                    "index": index,
                    "position_px": [float(tile["position"][0]), float(tile["position"][1])],
                    "registration_response": tile["response"],
                    "timestamp": tile["timestamp"],
                    "metadata": tile["metadata"],
                }
                for index, tile in enumerate(self.tiles)
            ],
        }

    def _estimate_shift(self, reference_gray, new_gray):
        window = cv2.createHanningWindow(
            (reference_gray.shape[1], reference_gray.shape[0]),
            cv2.CV_32F,
        )
        shift, response = cv2.phaseCorrelate(reference_gray, new_gray, window)
        return shift, response

    def _prepare_frame(self, frame):
        if frame.ndim == 2:
            return frame.copy()
        if frame.ndim == 3 and frame.shape[2] in (3, 4):
            return frame[:, :, :3].copy()
        raise ValueError("Unsupported frame shape")

    def _to_registration_image(self, frame):
        if frame.ndim == 2:
            gray = frame
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        gray = gray.astype(np.float32)
        gray -= float(np.mean(gray))
        std = float(np.std(gray))
        if std > 1e-6:
            gray /= std
        return gray

    def _as_bgr(self, frame):
        if frame.ndim == 2:
            return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        return frame

    def _make_feather_mask(self, height, width):
        feather = max(1, min(self.feather_pixels, height // 2, width // 2))
        y_distance = np.minimum(np.arange(height), np.arange(height)[::-1])[:, None]
        x_distance = np.minimum(np.arange(width), np.arange(width)[::-1])[None, :]
        edge_distance = np.minimum(x_distance, y_distance).astype(np.float32)
        mask = np.clip(edge_distance / feather, 0.05, 1.0)
        return mask[:, :, None]

    def _fit_to_size(self, image, max_size):
        max_width, max_height = max_size
        height, width = image.shape[:2]
        scale = min(max_width / width, max_height / height, 1.0)
        if scale >= 1.0:
            return image
        return cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
