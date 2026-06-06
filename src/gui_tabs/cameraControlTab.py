import threading
import time
import tkinter as tk
import tkinter.filedialog
from tkinter import ttk

import cv2
from PIL import Image, ImageTk

from src.cameraManager import CameraManager
from src.laserDetector import detect_red_green_lasers


class CameraControlTab:
    def __init__(self, parent, instruments, main_gui):
        self.parent = parent
        self.instruments = instruments
        self.main_gui = main_gui
        self.camera_manager = CameraManager()
        self.stream_running = False
        self.stream_thread = None
        self.last_detection = None
        self.detached_window = None
        self.detached_image_label = None
        self.setup_ui()
        self.parent.after(100, self.update_live_view)

    def setup_ui(self):
        main_frame = tk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=1)

        canvas = tk.Canvas(main_frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)

        inner_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor='nw')

        connection_frame = ttk.LabelFrame(inner_frame, text="Camera Connection")
        connection_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        capture_frame = ttk.LabelFrame(inner_frame, text="Capture Controls")
        capture_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        settings_frame = ttk.LabelFrame(inner_frame, text="Camera Settings")
        settings_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        image_frame = ttk.LabelFrame(inner_frame, text="Camera View")
        image_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        analysis_frame = ttk.LabelFrame(inner_frame, text="Laser Detection")
        analysis_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        self.status_text = tk.StringVar(value=self.camera_manager.status)
        self.status_label = tk.Label(connection_frame, textvariable=self.status_text)
        self.status_label.grid(row=0, column=0, columnspan=4, padx=10, pady=5, sticky=tk.W)

        self.connect_button = tk.Button(connection_frame, text="Connect Camera", command=self.connect_camera)
        self.connect_button.grid(row=1, column=0, padx=10, pady=5)

        self.disconnect_button = tk.Button(connection_frame, text="Disconnect", command=self.disconnect_camera)
        self.disconnect_button.grid(row=1, column=1, padx=10, pady=5)

        self.load_test_button = tk.Button(connection_frame, text="Load Test Image", command=self.load_test_image)
        self.load_test_button.grid(row=1, column=2, padx=10, pady=5)

        self.capture_button = tk.Button(capture_frame, text="Capture Frame", command=self.capture_frame)
        self.capture_button.grid(row=0, column=0, padx=10, pady=5)

        self.start_stream_button = tk.Button(capture_frame, text="Start Live View", command=self.start_stream)
        self.start_stream_button.grid(row=0, column=1, padx=10, pady=5)

        self.unattached_feed = tk.BooleanVar(value=False)
        self.unattached_feed_check = tk.Checkbutton(
            capture_frame,
            text="Unattached feed",
            variable=self.unattached_feed,
        )
        self.unattached_feed_check.grid(row=0, column=2, padx=10, pady=5)

        self.stop_stream_button = tk.Button(capture_frame, text="Stop Live View", command=self.stop_stream, state="disabled")
        self.stop_stream_button.grid(row=0, column=3, padx=10, pady=5)

        self.save_image_button = tk.Button(capture_frame, text="Save Current Image", command=self.save_current_image)
        self.save_image_button.grid(row=0, column=4, padx=10, pady=5)

        self.exposure_time = tk.DoubleVar(value=10000.0)
        self.gain = tk.DoubleVar(value=0.0)
        self.gamma = tk.DoubleVar(value=1.0)

        tk.Label(settings_frame, text="Exposure Time (us)").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        tk.Entry(settings_frame, textvariable=self.exposure_time, width=12).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(settings_frame, text="Apply Exposure", command=self.apply_exposure_time).grid(row=0, column=2, padx=10, pady=5)

        tk.Label(settings_frame, text="Gain").grid(row=0, column=3, padx=5, pady=5, sticky=tk.E)
        tk.Entry(settings_frame, textvariable=self.gain, width=12).grid(row=0, column=4, padx=5, pady=5)
        tk.Button(settings_frame, text="Apply Gain", command=self.apply_gain).grid(row=0, column=5, padx=10, pady=5)

        tk.Label(settings_frame, text="Camera Gamma").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        tk.Entry(settings_frame, textvariable=self.gamma, width=12).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(settings_frame, text="Apply Gamma", command=self.apply_gamma).grid(row=1, column=2, padx=10, pady=5)

        self.image_label = tk.Label(image_frame, text="No image loaded", bg="black", fg="white")
        self.image_label.grid(row=0, column=0, padx=10, pady=10)

        self.s_min = tk.IntVar(value=50)
        self.v_min = tk.IntVar(value=50)
        self.contour_selection = tk.IntVar(value=0)

        tk.Label(analysis_frame, text="Saturation Min").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        tk.Entry(analysis_frame, textvariable=self.s_min, width=8).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(analysis_frame, text="Value Min").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        tk.Entry(analysis_frame, textvariable=self.v_min, width=8).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(analysis_frame, text="Contour Index").grid(row=2, column=0, padx=5, pady=5, sticky=tk.E)
        tk.Entry(analysis_frame, textvariable=self.contour_selection, width=8).grid(row=2, column=1, padx=5, pady=5)

        self.detect_lasers_button = tk.Button(analysis_frame, text="Detect Red/Green Lasers", command=self.detect_lasers)
        self.detect_lasers_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        self.results_text = tk.Text(analysis_frame, height=18, width=45, font=('Arial', 10))
        self.results_text.grid(row=4, column=0, columnspan=2, padx=10, pady=10)
        self.results_text.insert('1.0', "Load or capture an image, then run detection.\n")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner_frame.bind('<Configure>', _on_frame_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def connect_camera(self):
        connected = self.camera_manager.connect_camera()
        self.update_status()
        if connected:
            self.capture_frame()

    def disconnect_camera(self):
        self.stop_stream()
        self.camera_manager.disconnect()
        self.update_status()

    def load_test_image(self):
        image_path = tk.filedialog.askopenfilename(
            title="Select Test Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"), ("All files", "*.*")]
        )
        if self.camera_manager.load_test_image(image_path):
            self.display_frame(self.camera_manager.get_latest_frame())
        self.update_status()

    def capture_frame(self):
        frame = self.camera_manager.capture_frame()
        if frame is not None:
            self.display_frame(frame)
        self.update_status()

    def start_stream(self):
        if self.stream_running:
            return
        if self.unattached_feed.get():
            self.open_detached_window()
        self.stream_running = True
        self.start_stream_button['state'] = 'disabled'
        self.stop_stream_button['state'] = 'normal'
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()

    def stop_stream(self):
        self.stream_running = False
        self.start_stream_button['state'] = 'normal'
        self.stop_stream_button['state'] = 'disabled'
        self.close_detached_window()

    def _stream_loop(self):
        while self.stream_running:
            self.camera_manager.capture_frame()
            time.sleep(0.05)

    def update_live_view(self):
        if self.stream_running:
            frame = self.camera_manager.get_latest_frame()
            if frame is not None:
                if self.detached_window is not None and self.detached_image_label is not None:
                    self.display_frame(frame, label=self.detached_image_label, max_size=self.detached_view_size())
                else:
                    self.display_frame(frame)
            self.update_status()
        self.parent.after(100, self.update_live_view)

    def open_detached_window(self):
        if self.detached_window is not None:
            self.detached_window.lift()
            return

        self.detached_window = tk.Toplevel(self.parent)
        self.detached_window.title("Camera Live Feed")
        self.detached_window.configure(bg="black")
        self.detached_image_label = tk.Label(self.detached_window, text="Waiting for camera frame...", bg="black", fg="white")
        self.detached_image_label.pack(fill=tk.BOTH, expand=True)
        self.detached_window.protocol("WM_DELETE_WINDOW", self.stop_stream)

    def close_detached_window(self):
        if self.detached_window is not None:
            try:
                self.detached_window.destroy()
            except tk.TclError:
                pass
        self.detached_window = None
        self.detached_image_label = None

    def detached_view_size(self):
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        return min(1400, screen_width - 100), min(1000, screen_height - 140)

    def detect_lasers(self):
        frame = self.camera_manager.get_latest_frame()
        if frame is None:
            self.write_results("No image available. Capture a frame or load a test image first.\n")
            return

        try:
            result = detect_red_green_lasers(
                frame,
                contour_selection=int(self.contour_selection.get()),
                s_min=int(self.s_min.get()),
                v_min=int(self.v_min.get()),
            )
        except Exception as exc:
            self.write_results(f"Detection failed: {exc}\n")
            return

        self.last_detection = result
        if result.get("annotated_image") is not None:
            self.display_frame(result["annotated_image"])
        self.write_results(self.format_detection_results(result))

    def apply_exposure_time(self):
        value = self.get_positive_setting(self.exposure_time, "Exposure time")
        if value is None:
            return
        self.apply_camera_setting(self.camera_manager.set_exposure_time, value)

    def apply_gain(self):
        value = self.get_non_negative_setting(self.gain, "Gain")
        if value is None:
            return
        self.apply_camera_setting(self.camera_manager.set_gain, value)

    def apply_gamma(self):
        value = self.get_positive_setting(self.gamma, "Camera gamma")
        if value is None:
            return
        self.apply_camera_setting(self.camera_manager.set_gamma, value)

    def apply_camera_setting(self, setter, value):
        try:
            success, message = setter(value)
        except Exception as exc:
            success = False
            message = str(exc)

        self.update_status(message)
        if not success:
            self.write_results(f"Camera setting error: {message}\n")

    def get_positive_setting(self, variable, name):
        value = self.get_numeric_setting(variable, name)
        if value is None:
            return None
        if value <= 0:
            self.update_status(f"{name} must be greater than 0")
            return None
        return value

    def get_non_negative_setting(self, variable, name):
        value = self.get_numeric_setting(variable, name)
        if value is None:
            return None
        if value < 0:
            self.update_status(f"{name} cannot be negative")
            return None
        return value

    def get_numeric_setting(self, variable, name):
        try:
            return float(variable.get())
        except (tk.TclError, ValueError):
            self.update_status(f"{name} must be numeric")
            return None

    def save_current_image(self):
        frame = self.camera_manager.get_latest_frame()
        if frame is None:
            self.update_status("No image to save")
            return

        file_path = tk.filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            title="Save Current Image",
        )
        if file_path:
            cv2.imwrite(file_path, frame)
            self.update_status(f"Saved image: {file_path}")

    def display_frame(self, frame, label=None, max_size=(960, 700)):
        if frame is None:
            return
        if label is None:
            label = self.image_label

        if frame.ndim == 2:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        else:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        image = Image.fromarray(rgb_frame)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        label.configure(image=photo, text="")
        label.image = photo

    def update_status(self, override=None):
        if override is not None:
            self.status_text.set(override)
            return

        status = self.camera_manager.status
        if self.camera_manager.error:
            status = f"{status}: {self.camera_manager.error}"
        self.status_text.set(status)

    def write_results(self, text):
        self.results_text.delete('1.0', tk.END)
        self.results_text.insert('1.0', text)

    def format_detection_results(self, result):
        lines = ["Laser Detection Results", ""]
        lines.extend(self._format_single_laser("Red", result.get("red")))
        lines.append("")
        lines.extend(self._format_single_laser("Green", result.get("green")))
        lines.append("")

        distance_px = result.get("distance_px")
        if distance_px is None:
            lines.append("Distance: unavailable")
        else:
            lines.append(f"Distance: {distance_px:.2f} px")

        return "\n".join(lines) + "\n"

    def _format_single_laser(self, name, data):
        if not data or not data.get("found"):
            message = data.get("message") if data else "No result"
            return [f"{name}: not found", f"Reason: {message}"]

        center = data["center"]
        axes = data["axes"]
        angle = data["angle"]
        return [
            f"{name}: found",
            f"Center: ({center[0]:.1f}, {center[1]:.1f}) px",
            f"Axes: ({axes[0]:.1f}, {axes[1]:.1f}) px",
            f"Angle: {angle:.1f} deg",
            f"Contours: {data.get('contour_count', 0)}",
        ]
