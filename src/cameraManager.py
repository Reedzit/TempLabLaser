import os
import threading

import cv2

try:
    import gxipy
except Exception:
    gxipy = None


class CameraManager:
    """Small wrapper for camera capture with a test-image fallback."""

    def __init__(self):
        self.device_manager = None
        self.camera = None
        self.test_image_path = None
        self.test_image = None
        self.latest_frame = None
        self.status = "Disconnected"
        self.error = None
        self._lock = threading.Lock()

    def connect_camera(self, device_index=1):
        if gxipy is None:
            self.status = "Daheng SDK not installed"
            self.error = "gxipy is not available"
            return False

        try:
            self.device_manager = gxipy.DeviceManager()
            device_num, _ = self.device_manager.update_device_list()
            if device_num == 0:
                self.status = "No camera found"
                self.error = "No Daheng camera devices were detected"
                return False

            self.camera = self.device_manager.open_device_by_index(device_index)
            self.camera.stream_on()
            self.status = "Camera connected"
            self.error = None
            return True
        except Exception as exc:
            self.camera = None
            self.status = "Camera connection failed"
            self.error = str(exc)
            return False

    def load_test_image(self, image_path):
        if not image_path:
            self.status = "No test image selected"
            return False

        image = cv2.imread(image_path)
        if image is None:
            self.status = "Test image load failed"
            self.error = f"Could not read image: {image_path}"
            return False

        with self._lock:
            self.test_image_path = image_path
            self.test_image = image
            self.latest_frame = image.copy()

        self.status = f"Loaded test image: {os.path.basename(image_path)}"
        self.error = None
        return True

    def capture_frame(self):
        if self.camera is not None:
            frame = self._capture_camera_frame()
        elif self.test_image is not None:
            frame = self.test_image.copy()
        else:
            self.status = "No camera or test image"
            return None

        if frame is not None:
            with self._lock:
                self.latest_frame = frame.copy()
        return frame

    def get_latest_frame(self):
        with self._lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def disconnect(self):
        try:
            if self.camera is not None:
                self.camera.stream_off()
                self.camera.close_device()
        except Exception as exc:
            self.error = str(exc)
        finally:
            self.camera = None
            self.status = "Disconnected"

    def _capture_camera_frame(self):
        try:
            raw_image = self.camera.data_stream[0].get_image()
            if raw_image is None:
                self.status = "No camera image received"
                return None

            if hasattr(raw_image, "convert"):
                raw_image = raw_image.convert("RGB")

            frame = raw_image.get_numpy_array()
            if frame is None:
                self.status = "Empty camera image"
                return None

            if frame.ndim == 3 and frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            self.status = "Streaming"
            self.error = None
            return frame
        except Exception as exc:
            self.status = "Camera capture failed"
            self.error = str(exc)
            return None

    def __del__(self):
        self.disconnect()
