import sys

import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.cameraManager import CameraManager


class PySideCameraViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.camera_manager = CameraManager()
        self.setWindowTitle("PySide6 Camera Controller")
        self.resize(1300, 900)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.setup_ui()

    def setup_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)

        controls = QHBoxLayout()
        self.connect_button = QPushButton("Connect Camera")
        self.connect_button.clicked.connect(self.connect_camera)
        controls.addWidget(self.connect_button)

        self.load_test_button = QPushButton("Load Test Image")
        self.load_test_button.clicked.connect(self.load_test_image)
        controls.addWidget(self.load_test_button)

        self.start_button = QPushButton("Start Live View")
        self.start_button.clicked.connect(self.start_live_view)
        controls.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Live View")
        self.stop_button.clicked.connect(self.stop_live_view)
        controls.addWidget(self.stop_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_camera)
        controls.addWidget(self.disconnect_button)
        layout.addLayout(controls)

        settings = QGridLayout()
        self.exposure_input = QLineEdit("10000.0")
        self.gain_input = QLineEdit("0.0")
        self.gamma_input = QLineEdit("1.0")

        settings.addWidget(QLabel("Exposure Time (us)"), 0, 0)
        settings.addWidget(self.exposure_input, 0, 1)
        exposure_button = QPushButton("Apply Exposure")
        exposure_button.clicked.connect(self.apply_exposure)
        settings.addWidget(exposure_button, 0, 2)

        settings.addWidget(QLabel("Gain"), 0, 3)
        settings.addWidget(self.gain_input, 0, 4)
        gain_button = QPushButton("Apply Gain")
        gain_button.clicked.connect(self.apply_gain)
        settings.addWidget(gain_button, 0, 5)

        settings.addWidget(QLabel("Camera Gamma"), 1, 0)
        settings.addWidget(self.gamma_input, 1, 1)
        gamma_button = QPushButton("Apply Gamma")
        gamma_button.clicked.connect(self.apply_gamma)
        settings.addWidget(gamma_button, 1, 2)
        layout.addLayout(settings)

        self.image_label = QLabel("No frame")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black; color: white;")
        layout.addWidget(self.image_label, stretch=1)

        self.status_label = QLabel("Disconnected")
        layout.addWidget(self.status_label)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        layout.addWidget(self.log)

        self.setCentralWidget(root)

    def connect_camera(self):
        if self.camera_manager.connect_camera():
            self.write_status("Camera connected")
        else:
            self.write_status(self.current_error())

    def load_test_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Test Image",
            "",
            "Image files (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;All files (*.*)",
        )
        if not path:
            return
        if self.camera_manager.load_test_image(path):
            self.write_status("Loaded test image")
            self.update_frame()
        else:
            self.write_status(self.current_error())

    def start_live_view(self):
        if not self.camera_manager.start_capture():
            self.write_status(self.current_error())
            return
        self.timer.start(16)
        self.write_status("Live view started")

    def stop_live_view(self):
        self.timer.stop()
        self.camera_manager.stop_capture()
        self.write_status("Live view stopped")

    def disconnect_camera(self):
        self.stop_live_view()
        self.camera_manager.disconnect()
        self.write_status("Disconnected")

    def apply_exposure(self):
        self.apply_setting(self.exposure_input, self.camera_manager.set_exposure_time, "Exposure time", positive=True)

    def apply_gain(self):
        self.apply_setting(self.gain_input, self.camera_manager.set_gain, "Gain", non_negative=True)

    def apply_gamma(self):
        self.apply_setting(self.gamma_input, self.camera_manager.set_gamma, "Camera gamma", positive=True)

    def apply_setting(self, field, setter, name, positive=False, non_negative=False):
        try:
            value = float(field.text())
        except ValueError:
            self.write_status(f"{name} must be numeric")
            return

        if positive and value <= 0:
            self.write_status(f"{name} must be greater than 0")
            return
        if non_negative and value < 0:
            self.write_status(f"{name} cannot be negative")
            return

        success, message = setter(value)
        self.write_status(message)
        if not success:
            self.log.append(f"Camera setting error: {message}")

    def update_frame(self):
        frame = self.camera_manager.get_latest_frame()
        if frame is None:
            self.update_diagnostics()
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame.ndim == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        height, width = rgb.shape[:2]
        rgb_format = getattr(QImage, "Format_RGB888", QImage.Format.Format_RGB888)
        image = QImage(rgb.data, width, height, width * 3, rgb_format).copy()
        pixmap = QPixmap.fromImage(image).scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.FastTransformation,
        )
        self.image_label.setPixmap(pixmap)
        self.camera_manager.mark_frame_displayed()
        self.update_diagnostics()

    def update_diagnostics(self):
        diagnostics = self.camera_manager.get_diagnostics()
        frame_age = diagnostics["frame_age_ms"]
        frame_age_text = "n/a" if frame_age is None else f"{frame_age:.0f} ms"
        self.status_label.setText(
            f"{diagnostics['status']} | "
            f"capture {diagnostics['capture_fps']:.1f} FPS | "
            f"display {diagnostics['display_fps']:.1f} FPS | "
            f"frame age {frame_age_text} | "
            f"frame {diagnostics['dimensions']}"
        )

    def current_error(self):
        if self.camera_manager.error:
            return f"{self.camera_manager.status}: {self.camera_manager.error}"
        return self.camera_manager.status

    def write_status(self, text):
        self.status_label.setText(text)
        self.log.append(text)

    def closeEvent(self, event):
        self.camera_manager.disconnect()
        event.accept()


def main():
    app = QApplication(sys.argv)
    viewer = PySideCameraViewer()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
