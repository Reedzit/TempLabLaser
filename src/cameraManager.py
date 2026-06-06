import os
import threading
import time

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
        self.latest_frame_time = None
        self.status = "Disconnected"
        self.error = None
        self.low_latency_notes = []
        self.capture_running = False
        self.capture_thread = None
        self.capture_fps = 0.0
        self.display_fps = 0.0
        self.frame_count = 0
        self.display_count = 0
        self._capture_fps_window_start = time.perf_counter()
        self._display_fps_window_start = time.perf_counter()
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
            self.configure_low_latency()
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
            self.latest_frame_time = time.perf_counter()

        self.status = f"Loaded test image: {os.path.basename(image_path)}"
        self.error = None
        return True

    def start_capture(self):
        if self.capture_running:
            return True
        if self.camera is None and self.test_image is None:
            self.status = "No camera or test image"
            self.error = "Connect a camera or load a test image before streaming"
            return False

        self.capture_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        return True

    def stop_capture(self):
        self.capture_running = False

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
                self.latest_frame_time = time.perf_counter()
                self._record_capture_locked()
        return frame

    def get_latest_frame(self):
        with self._lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def mark_frame_displayed(self):
        with self._lock:
            self.display_count += 1
            now = time.perf_counter()
            elapsed = now - self._display_fps_window_start
            if elapsed >= 1.0:
                self.display_fps = self.display_count / elapsed
                self.display_count = 0
                self._display_fps_window_start = now

    def get_diagnostics(self):
        with self._lock:
            frame_shape = self.latest_frame.shape if self.latest_frame is not None else None
            frame_age_ms = None
            if self.latest_frame_time is not None:
                frame_age_ms = (time.perf_counter() - self.latest_frame_time) * 1000

            if frame_shape is None:
                dimensions = "No frame"
            elif len(frame_shape) == 2:
                dimensions = f"{frame_shape[1]}x{frame_shape[0]}"
            else:
                dimensions = f"{frame_shape[1]}x{frame_shape[0]}x{frame_shape[2]}"

            return {
                "capture_fps": self.capture_fps,
                "display_fps": self.display_fps,
                "frame_age_ms": frame_age_ms,
                "dimensions": dimensions,
                "status": self.status,
                "error": self.error,
                "low_latency_notes": list(self.low_latency_notes),
            }

    def set_exposure_time(self, exposure_time):
        return self._set_camera_feature(("ExposureTime", "ExposureTimeRaw"), exposure_time, "exposure time")

    def set_gain(self, gain):
        return self._set_camera_feature(("Gain", "GainRaw"), gain, "gain")

    def set_gamma(self, gamma):
        result = self._set_camera_feature(("Gamma",), gamma, "gamma")
        if result[0]:
            return result

        # Some Daheng cameras require GammaEnable before Gamma is writable.
        enabled = self._set_camera_feature(("GammaEnable",), True, "gamma enable")
        if not enabled[0]:
            return result
        return self._set_camera_feature(("Gamma",), gamma, "gamma")

    def disconnect(self):
        self.stop_capture()
        try:
            if self.camera is not None:
                self.camera.stream_off()
                self.camera.close_device()
        except Exception as exc:
            self.error = str(exc)
        finally:
            self.camera = None
            self.status = "Disconnected"

    def configure_low_latency(self):
        self.low_latency_notes = []
        attempts = (
            (("AcquisitionMode",), "Continuous", "acquisition mode"),
            (("TriggerMode",), "Off", "trigger mode"),
            (("StreamBufferHandlingMode",), "NewestOnly", "stream buffer handling"),
            (("StreamBufferCountMode",), "Manual", "stream buffer count mode"),
            (("StreamBufferCountManual", "StreamBufferCount"), 1, "stream buffer count"),
        )

        for feature_names, value, display_name in attempts:
            success, message = self._set_camera_feature(feature_names, value, display_name, require_camera=True)
            if success:
                self.low_latency_notes.append(message)

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

    def _capture_loop(self):
        while self.capture_running:
            frame = self.capture_frame()
            if frame is None:
                time.sleep(0.02)
            elif self.test_image is not None and self.camera is None:
                time.sleep(0.03)

    def _set_camera_feature(self, feature_names, value, display_name, require_camera=True):
        if self.camera is None:
            self.status = f"Cannot set {display_name}"
            self.error = "No camera is connected"
            return False, self.error

        last_error = None
        for feature_name in feature_names:
            try:
                feature = getattr(self.camera, feature_name)
            except AttributeError as exc:
                last_error = str(exc)
                continue

            try:
                if hasattr(feature, "set"):
                    feature.set(value)
                elif hasattr(feature, "set_value"):
                    feature.set_value(value)
                elif callable(feature):
                    feature(value)
                else:
                    setattr(self.camera, feature_name, value)
                self.status = f"Set {display_name} to {value}"
                self.error = None
                return True, self.status
            except Exception as exc:
                last_error = str(exc)

        message = f"Camera does not support setting {display_name}"
        if last_error:
            message = f"{message}: {last_error}"
        self.status = f"Failed to set {display_name}"
        self.error = message
        return False, message

    def _record_capture_locked(self):
        self.frame_count += 1
        now = time.perf_counter()
        elapsed = now - self._capture_fps_window_start
        if elapsed >= 1.0:
            self.capture_fps = self.frame_count / elapsed
            self.frame_count = 0
            self._capture_fps_window_start = now

    def __del__(self):
        self.disconnect()
