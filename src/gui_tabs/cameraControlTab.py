import threading
import time
import tkinter as tk
import tkinter.filedialog
from tkinter import ttk

import cv2
import numpy as np
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
        self.autofocus_running = False
        self.autofocus_thread = None
        self.last_detection = None
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

        image_frame = ttk.LabelFrame(inner_frame, text="Camera View")
        image_frame.grid(row=2, column=0, padx=10, pady=5, sticky='nsew')

        analysis_frame = ttk.LabelFrame(inner_frame, text="Laser Detection")
        analysis_frame.grid(row=2, column=1, padx=10, pady=5, sticky='nsew')

        autofocus_frame = ttk.LabelFrame(inner_frame, text="Autofocus")
        autofocus_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

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

        self.stop_stream_button = tk.Button(capture_frame, text="Stop Live View", command=self.stop_stream, state="disabled")
        self.stop_stream_button.grid(row=0, column=2, padx=10, pady=5)

        self.save_image_button = tk.Button(capture_frame, text="Save Current Image", command=self.save_current_image)
        self.save_image_button.grid(row=0, column=3, padx=10, pady=5)

        self.autofocus_range = tk.DoubleVar(value=0.5)
        self.autofocus_step = tk.DoubleVar(value=0.05)
        self.autofocus_settle = tk.DoubleVar(value=0.2)
        self.autofocus_status = tk.StringVar(value="Ready")

        tk.Label(autofocus_frame, text="Z Range (+/- mm)").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        tk.Entry(autofocus_frame, textvariable=self.autofocus_range, width=8).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(autofocus_frame, text="Step Size (mm)").grid(row=0, column=2, padx=5, pady=5, sticky=tk.E)
        tk.Entry(autofocus_frame, textvariable=self.autofocus_step, width=8).grid(row=0, column=3, padx=5, pady=5)

        tk.Label(autofocus_frame, text="Settle Time (s)").grid(row=0, column=4, padx=5, pady=5, sticky=tk.E)
        tk.Entry(autofocus_frame, textvariable=self.autofocus_settle, width=8).grid(row=0, column=5, padx=5, pady=5)

        self.autofocus_button = tk.Button(autofocus_frame, text="Autofocus", command=self.start_autofocus)
        self.autofocus_button.grid(row=0, column=6, padx=10, pady=5)

        tk.Label(autofocus_frame, textvariable=self.autofocus_status).grid(
            row=1, column=0, columnspan=7, padx=5, pady=5, sticky=tk.W
        )

        self.image_label = tk.Label(image_frame, text="No image loaded", width=80, height=30)
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
        self.stream_running = True
        self.start_stream_button['state'] = 'disabled'
        self.stop_stream_button['state'] = 'normal'
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()

    def stop_stream(self):
        self.stream_running = False
        self.start_stream_button['state'] = 'normal'
        self.stop_stream_button['state'] = 'disabled'

    def _stream_loop(self):
        while self.stream_running:
            self.camera_manager.capture_frame()
            time.sleep(0.05)

    def update_live_view(self):
        if self.stream_running:
            frame = self.camera_manager.get_latest_frame()
            if frame is not None:
                self.display_frame(frame)
            self.update_status()
        self.parent.after(100, self.update_live_view)

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

    def start_autofocus(self):
        if self.autofocus_running:
            return

        try:
            scan_range = float(self.autofocus_range.get())
            step_size = float(self.autofocus_step.get())
            settle_time = float(self.autofocus_settle.get())
        except (tk.TclError, ValueError):
            self.update_autofocus_status("Autofocus settings must be numeric.")
            return

        if scan_range <= 0 or step_size <= 0 or settle_time < 0:
            self.update_autofocus_status("Use positive range/step and non-negative settle time.")
            return

        hexapod = self.get_connected_hexapod()
        if hexapod is None:
            self.update_autofocus_status("Connect the hexapod before autofocusing.")
            return

        self.autofocus_running = True
        self.autofocus_button['state'] = 'disabled'
        self.update_autofocus_status("Autofocus running...")
        self.autofocus_thread = threading.Thread(
            target=self.run_autofocus,
            args=(hexapod, scan_range, step_size, settle_time),
            daemon=True,
        )
        self.autofocus_thread.start()

    def run_autofocus(self, hexapod, scan_range, step_size, settle_time):
        positions = self.build_autofocus_positions(scan_range, step_size)
        current_position = 0.0
        best_position = None
        best_score = None
        scores = []

        try:
            self.move_hexapod_z(hexapod, positions[0] - current_position)
            current_position = positions[0]

            for position in positions:
                move_amount = position - current_position
                if move_amount != 0:
                    self.move_hexapod_z(hexapod, move_amount)
                    current_position = position

                time.sleep(settle_time)
                frame = self.camera_manager.capture_frame()
                if frame is None:
                    raise RuntimeError("No image available during autofocus.")

                score = self.calculate_sharpness(frame)
                scores.append((position, score))
                if best_score is None or score > best_score:
                    best_position = position
                    best_score = score

                self.parent.after(
                    0,
                    self.update_autofocus_status,
                    f"Autofocus: z={position:.4f} mm, sharpness={score:.2f}",
                )

            if best_position is None:
                raise RuntimeError("Autofocus did not capture any frames.")

            self.move_hexapod_z(hexapod, best_position - current_position)
            best_frame = self.camera_manager.capture_frame()
            self.parent.after(0, self.display_frame, best_frame)
            self.parent.after(0, self.write_results, self.format_autofocus_results(scores, best_position, best_score))
            self.parent.after(
                0,
                self.update_autofocus_status,
                f"Autofocus complete: best z={best_position:.4f} mm, sharpness={best_score:.2f}",
            )
        except Exception as exc:
            self.parent.after(0, self.update_autofocus_status, f"Autofocus failed: {exc}")
        finally:
            self.parent.after(0, self.finish_autofocus)

    def build_autofocus_positions(self, scan_range, step_size):
        positions = []
        position = -scan_range
        while position <= scan_range:
            positions.append(round(position, 6))
            position += step_size
        if not positions or positions[-1] < scan_range:
            positions.append(scan_range)
        return positions

    def calculate_sharpness(self, frame):
        if frame.ndim == 2:
            gray = frame
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    def get_connected_hexapod(self):
        hexapod_tab = getattr(self.main_gui, "hexapodTabObject", None)
        hexapod = getattr(hexapod_tab, "hexapod", None)
        if hexapod is None or getattr(hexapod, "ssh_API", None) is None:
            return None
        return hexapod

    def move_hexapod_z(self, hexapod, z_distance):
        hexapod.translate(np.array([0.0, 0.0, float(z_distance)]))
        self.wait_for_hexapod(hexapod)

    def wait_for_hexapod(self, hexapod, timeout=30):
        start_time = time.time()
        while not getattr(hexapod, "ready_for_commands", False):
            if time.time() - start_time > timeout:
                raise TimeoutError("Hexapod movement timed out.")
            time.sleep(0.05)

    def finish_autofocus(self):
        self.autofocus_running = False
        self.autofocus_button['state'] = 'normal'

    def update_autofocus_status(self, text):
        self.autofocus_status.set(text)

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

    def display_frame(self, frame):
        if frame is None:
            return

        if frame.ndim == 2:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        else:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        image = Image.fromarray(rgb_frame)
        image.thumbnail((760, 560), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        self.image_label.configure(image=photo, text="")
        self.image_label.image = photo

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

    def format_autofocus_results(self, scores, best_position, best_score):
        lines = ["Autofocus Results", "", "Sharpness uses variance of Laplacian.", ""]
        for position, score in scores:
            marker = "*" if position == best_position else " "
            lines.append(f"{marker} z={position:.4f} mm: {score:.2f}")
        lines.append("")
        lines.append(f"Best focus: z={best_position:.4f} mm")
        lines.append(f"Sharpness: {best_score:.2f}")
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
