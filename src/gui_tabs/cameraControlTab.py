import threading
import time
import tkinter as tk
import tkinter.filedialog
from tkinter import ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from src.cameraManager import CameraManager
from src.compositingManager import CompositingManager
from src.laserDetector import detect_red_green_lasers


class CameraControlTab:
    def __init__(self, parent, instruments, main_gui):
        self.parent = parent
        self.instruments = instruments
        self.main_gui = main_gui
        self.camera_manager = CameraManager()
        self.compositing_manager = CompositingManager()
        self.stream_running = False
        self.autofocus_running = False
        self.autofocus_thread = None
        self.focus_laser_running = False
        self.focus_laser_thread = None
        self.axis_identification_running = False
        self.axis_identification_thread = None
        self.composite_running = False
        self.composite_thread = None
        self.composite_interval_seconds = 0.30
        self.last_detection = None
        self.detached_window = None
        self.detached_image_label = None
        self.last_status_update = 0.0
        self.last_diagnostics_update = 0.0
        self.setup_ui()
        self.parent.after(33, self.update_live_view)

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

        autofocus_frame = ttk.LabelFrame(inner_frame, text="Autofocus")
        autofocus_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        compositing_frame = ttk.LabelFrame(inner_frame, text="Image Compositing")
        compositing_frame.grid(row=7, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        axis_identification_frame = ttk.LabelFrame(inner_frame, text="Axis Difference Identification")
        axis_identification_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

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

        self.autofocus_range = tk.DoubleVar(value=0.5)
        self.autofocus_step = tk.DoubleVar(value=0.05)
        self.autofocus_settle = tk.DoubleVar(value=0.2)
        self.autofocus_status = tk.StringVar(value="Ready")

        self.axis_step = tk.DoubleVar(value=0.02)
        self.axis_repeats = tk.IntVar(value=3)
        self.axis_settle = tk.DoubleVar(value=0.2)
        self.axis_min_tracks = tk.IntVar(value=20)
        self.axis_status = tk.StringVar(value="Ready")

        self.exposure_time = tk.DoubleVar(value=100000.0)
        self.gain = tk.DoubleVar(value=0.0)
        self.gamma = tk.DoubleVar(value=1.0)
        self.target_capture_fps = tk.DoubleVar(value=self.camera_manager.target_capture_fps)

        tk.Label(settings_frame, text="Exposure Time (us, 12-100000)").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        tk.Entry(settings_frame, textvariable=self.exposure_time, width=12).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(settings_frame, text="Apply Exposure", command=self.apply_exposure_time).grid(row=0, column=2, padx=10, pady=5)

        tk.Label(settings_frame, text="Gain (0-24)").grid(row=0, column=3, padx=5, pady=5, sticky=tk.E)
        tk.Entry(settings_frame, textvariable=self.gain, width=12).grid(row=0, column=4, padx=5, pady=5)
        tk.Button(settings_frame, text="Apply Gain", command=self.apply_gain).grid(row=0, column=5, padx=10, pady=5)

        tk.Label(settings_frame, text="Camera Gamma (0-4)").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        tk.Entry(settings_frame, textvariable=self.gamma, width=12).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(settings_frame, text="Apply Gamma", command=self.apply_gamma).grid(row=1, column=2, padx=10, pady=5)

        tk.Label(settings_frame, text="Preview FPS").grid(row=1, column=3, padx=5, pady=5, sticky=tk.E)
        tk.Entry(settings_frame, textvariable=self.target_capture_fps, width=12).grid(row=1, column=4, padx=5, pady=5)
        tk.Button(settings_frame, text="Apply FPS", command=self.apply_target_capture_fps).grid(row=1, column=5, padx=10, pady=5)

        self.diagnostics_text = tk.StringVar(value=self.empty_diagnostics_text())
        tk.Label(settings_frame, textvariable=self.diagnostics_text, font=("Courier", 10), width=120, anchor=tk.W).grid(
            row=2, column=0, columnspan=6, padx=5, pady=5, sticky=tk.W
        )

        tk.Label(autofocus_frame, text="Z Range (+/- mm)").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        tk.Entry(autofocus_frame, textvariable=self.autofocus_range, width=8).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(autofocus_frame, text="Step Size (mm)").grid(row=0, column=2, padx=5, pady=5, sticky=tk.E)
        tk.Entry(autofocus_frame, textvariable=self.autofocus_step, width=8).grid(row=0, column=3, padx=5, pady=5)

        tk.Label(autofocus_frame, text="Settle Time (s)").grid(row=0, column=4, padx=5, pady=5, sticky=tk.E)
        tk.Entry(autofocus_frame, textvariable=self.autofocus_settle, width=8).grid(row=0, column=5, padx=5, pady=5)

        self.autofocus_button = tk.Button(autofocus_frame, text="Autofocus", command=self.start_autofocus)
        self.autofocus_button.grid(row=0, column=6, padx=10, pady=5)

        self.focus_laser_button = tk.Button(autofocus_frame, text="Focus Laser", command=self.start_focus_laser)
        self.focus_laser_button.grid(row=0, column=7, padx=10, pady=5)

        tk.Label(autofocus_frame, textvariable=self.autofocus_status).grid(
            row=1, column=0, columnspan=8, padx=5, pady=5, sticky=tk.W
        )

        tk.Label(axis_identification_frame, text="Step Size (mm)").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        tk.Entry(axis_identification_frame, textvariable=self.axis_step, width=8).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(axis_identification_frame, text="Repeats/Direction").grid(row=0, column=2, padx=5, pady=5, sticky=tk.E)
        tk.Entry(axis_identification_frame, textvariable=self.axis_repeats, width=8).grid(row=0, column=3, padx=5, pady=5)

        tk.Label(axis_identification_frame, text="Settle Time (s)").grid(row=0, column=4, padx=5, pady=5, sticky=tk.E)
        tk.Entry(axis_identification_frame, textvariable=self.axis_settle, width=8).grid(row=0, column=5, padx=5, pady=5)

        tk.Label(axis_identification_frame, text="Min Tracks").grid(row=0, column=6, padx=5, pady=5, sticky=tk.E)
        tk.Entry(axis_identification_frame, textvariable=self.axis_min_tracks, width=8).grid(row=0, column=7, padx=5, pady=5)

        self.axis_identification_button = tk.Button(
            axis_identification_frame,
            text="Identify Axis Difference",
            command=self.start_axis_identification,
        )
        self.axis_identification_button.grid(row=1, column=0, columnspan=2, padx=10, pady=5)

        self.stop_axis_identification_button = tk.Button(
            axis_identification_frame,
            text="Stop Axis ID",
            command=self.stop_axis_identification,
            state="disabled",
        )
        self.stop_axis_identification_button.grid(row=1, column=2, padx=10, pady=5)

        tk.Label(axis_identification_frame, textvariable=self.axis_status).grid(
            row=1, column=3, columnspan=5, padx=5, pady=5, sticky=tk.W
        )

        self.axis_results_text = tk.Text(axis_identification_frame, height=12, width=80, font=('Arial', 10))
        self.axis_results_text.grid(row=2, column=0, columnspan=8, padx=10, pady=10, sticky='nsew')
        self.axis_results_text.insert('1.0', "Run axis identification to calibrate camera pixels/mm from hexapod X/Y moves.\n")

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

        self.composite_interval = tk.DoubleVar(value=0.30)
        self.min_registration_response = tk.DoubleVar(value=self.compositing_manager.min_registration_response)

        tk.Label(compositing_frame, text="Capture Interval (s)").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        tk.Entry(compositing_frame, textvariable=self.composite_interval, width=8).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(compositing_frame, text="Min Reg. Response").grid(row=0, column=2, padx=5, pady=5, sticky=tk.E)
        tk.Entry(compositing_frame, textvariable=self.min_registration_response, width=8).grid(row=0, column=3, padx=5, pady=5)

        self.add_current_tile_button = tk.Button(compositing_frame, text="Add Current Frame", command=self.add_current_frame_to_mosaic)
        self.add_current_tile_button.grid(row=1, column=0, padx=10, pady=5)

        self.capture_tile_button = tk.Button(compositing_frame, text="Capture + Add Tile", command=self.capture_and_add_tile)
        self.capture_tile_button.grid(row=1, column=1, padx=10, pady=5)

        self.start_composite_button = tk.Button(compositing_frame, text="Start Live Composite", command=self.start_live_composite)
        self.start_composite_button.grid(row=1, column=2, padx=10, pady=5)

        self.stop_composite_button = tk.Button(compositing_frame, text="Stop Composite", command=self.stop_live_composite, state="disabled")
        self.stop_composite_button.grid(row=1, column=3, padx=10, pady=5)

        self.reset_mosaic_button = tk.Button(compositing_frame, text="Reset Mosaic", command=self.reset_mosaic)
        self.reset_mosaic_button.grid(row=1, column=4, padx=10, pady=5)

        self.save_mosaic_button = tk.Button(compositing_frame, text="Save Mosaic", command=self.save_mosaic)
        self.save_mosaic_button.grid(row=1, column=5, padx=10, pady=5)

        self.mosaic_label = tk.Label(compositing_frame, text="No mosaic", width=80, height=26)
        self.mosaic_label.grid(row=2, column=0, columnspan=4, padx=10, pady=10)

        self.compositing_status = tk.Text(compositing_frame, height=8, width=45, font=('Arial', 10))
        self.compositing_status.grid(row=2, column=4, columnspan=2, padx=10, pady=10, sticky='nsew')
        self.write_compositing_status("Ready. Add frames to build an image-derived mosaic.\n")

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
        self.stop_axis_identification()
        self.stop_live_composite()
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
        if not self.camera_manager.start_capture():
            self.update_status()
            self.close_detached_window()
            return
        self.stream_running = True
        self.start_stream_button['state'] = 'disabled'
        self.stop_stream_button['state'] = 'normal'

    def stop_stream(self):
        self.stream_running = False
        self.camera_manager.stop_capture()
        if hasattr(self, 'start_stream_button'):
            self.start_stream_button['state'] = 'normal'
        if hasattr(self, 'stop_stream_button'):
            self.stop_stream_button['state'] = 'disabled'
        self.close_detached_window()

    def update_live_view(self):
        delay_ms = 250
        if self.stream_running:
            frame = self.camera_manager.get_latest_frame()
            if frame is not None:
                if self.detached_window is not None and self.detached_image_label is not None:
                    self.display_frame(frame, label=self.detached_image_label, max_size=self.detached_view_size())
                else:
                    self.display_frame(frame)
                self.camera_manager.mark_frame_displayed()
            self.update_status_throttled()
            delay_ms = 33
        self.update_diagnostics()
        self.update_mosaic_preview()
        self.parent.after(delay_ms, self.update_live_view)

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

    def add_current_frame_to_mosaic(self):
        frame = self.camera_manager.get_latest_frame()
        if frame is None:
            self.write_compositing_status("No current frame available. Capture or load an image first.\n")
            return
        self.add_frame_to_mosaic(frame, {"source": "current_frame"})
        self.update_mosaic_preview()

    def capture_and_add_tile(self):
        frame = self.camera_manager.capture_frame()
        self.update_status()
        if frame is None:
            self.write_compositing_status("No frame available from camera source.\n")
            return
        self.display_frame(frame)
        self.add_frame_to_mosaic(frame, {"source": "camera_capture"})
        self.update_mosaic_preview()

    def add_frame_to_mosaic(self, frame, metadata=None):
        self.update_compositing_settings()
        accepted = self._add_frame_to_mosaic(frame, metadata)
        self.write_compositing_status(self.format_compositing_status(self.compositing_manager.get_status()))
        return accepted

    def _add_frame_to_mosaic(self, frame, metadata=None):
        try:
            return self.compositing_manager.add_frame(frame, metadata)
        except Exception as exc:
            self.compositing_manager.status = "Failed to add tile"
            self.compositing_manager.error = str(exc)
            return False

    def update_compositing_settings(self):
        self.composite_interval_seconds = max(0.05, float(self.composite_interval.get()))
        self.compositing_manager.min_registration_response = float(self.min_registration_response.get())

    def start_live_composite(self):
        if self.composite_running:
            return
        self.update_compositing_settings()
        self.composite_running = True
        self.start_composite_button['state'] = 'disabled'
        self.stop_composite_button['state'] = 'normal'
        self.composite_thread = threading.Thread(target=self._composite_loop, daemon=True)
        self.composite_thread.start()

    def stop_live_composite(self):
        self.composite_running = False
        if hasattr(self, 'start_composite_button'):
            self.start_composite_button['state'] = 'normal'
        if hasattr(self, 'stop_composite_button'):
            self.stop_composite_button['state'] = 'disabled'

    def _composite_loop(self):
        while self.composite_running:
            if self.stream_running:
                frame = self.camera_manager.get_latest_frame()
            else:
                frame = self.camera_manager.capture_frame()
            if frame is not None:
                self._add_frame_to_mosaic(frame, {"source": "live_composite"})
            time.sleep(self.composite_interval_seconds)

    def reset_mosaic(self):
        self.compositing_manager.reset_session()
        self.mosaic_label.configure(image="", text="No mosaic")
        self.mosaic_label.image = None
        self.write_compositing_status("Mosaic reset.\n")

    def save_mosaic(self):
        file_path = tk.filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("TIFF files", "*.tif"), ("All files", "*.*")],
            title="Save Mosaic",
        )
        if not file_path:
            return
        if self.compositing_manager.save_mosaic(file_path):
            self.write_compositing_status(f"Saved mosaic to {file_path}\n")
        else:
            self.write_compositing_status(self.format_compositing_status(self.compositing_manager.get_status()))

    def update_mosaic_preview(self):
        mosaic = self.compositing_manager.get_mosaic_preview(max_size=(760, 420))
        if mosaic is not None:
            self.display_image_in_label(self.mosaic_label, mosaic)
        if self.composite_running:
            self.write_compositing_status(self.format_compositing_status(self.compositing_manager.get_status()))

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
        if self.autofocus_running or self.focus_laser_running or self.axis_identification_running:
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
        self.set_focus_buttons_enabled(False)
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

    def start_focus_laser(self):
        if self.autofocus_running or self.focus_laser_running or self.axis_identification_running:
            return

        try:
            scan_range = float(self.autofocus_range.get())
            step_size = float(self.autofocus_step.get())
            settle_time = float(self.autofocus_settle.get())
        except (tk.TclError, ValueError):
            self.update_autofocus_status("Focus laser settings must be numeric.")
            return

        if scan_range <= 0 or step_size <= 0 or settle_time < 0:
            self.update_autofocus_status("Use positive range/step and non-negative settle time.")
            return

        hexapod = self.get_connected_hexapod()
        if hexapod is None:
            self.update_autofocus_status("Connect the hexapod before focusing the laser.")
            return

        self.focus_laser_running = True
        self.set_focus_buttons_enabled(False)
        self.update_autofocus_status("Focus laser scan running...")
        self.focus_laser_thread = threading.Thread(
            target=self.run_focus_laser,
            args=(hexapod, scan_range, step_size, settle_time),
            daemon=True,
        )
        self.focus_laser_thread.start()

    def run_focus_laser(self, hexapod, scan_range, step_size, settle_time):
        positions = self.build_autofocus_positions(scan_range, step_size)
        current_position = 0.0
        best_position = None
        best_focus_score = None
        measurements = []

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
                    raise RuntimeError("No image available during laser focus scan.")

                measurement = self.calculate_laser_blob_metric(frame)
                measurement["position"] = position
                measurements.append(measurement)

                if measurement["found"]:
                    beam_size = measurement["beam_size_px"]
                    axis_difference = measurement["axis_difference_px"]
                    focus_score = measurement["focus_score"]
                    if best_focus_score is None or focus_score < best_focus_score:
                        best_position = position
                        best_focus_score = focus_score
                    self.parent.after(
                        0,
                        self.update_autofocus_status,
                        (
                            f"Focus laser: z={position:.4f} mm, beam={beam_size:.2f} px, "
                            f"axis diff={axis_difference:.2f} px, score={focus_score:.2f}"
                        ),
                    )
                    self.parent.after(0, self.display_frame, measurement["annotated_image"])
                else:
                    self.parent.after(
                        0,
                        self.update_autofocus_status,
                        f"Focus laser: z={position:.4f} mm, beam not detected",
                    )

            if best_position is None:
                raise RuntimeError("Laser beam was not detected at any scan position.")

            self.move_hexapod_z(hexapod, best_position - current_position)
            best_frame = self.camera_manager.capture_frame()
            best_measurement = self.calculate_laser_blob_metric(best_frame) if best_frame is not None else None

            if best_measurement and best_measurement["found"]:
                self.parent.after(0, self.display_frame, best_measurement["annotated_image"])
            elif best_frame is not None:
                self.parent.after(0, self.display_frame, best_frame)

            self.parent.after(0, self.write_results, self.format_focus_laser_results(measurements, best_position, best_focus_score))
            self.parent.after(
                0,
                self.update_autofocus_status,
                f"Focus laser complete: best z={best_position:.4f} mm, score={best_focus_score:.2f}",
            )
        except Exception as exc:
            self.parent.after(0, self.update_autofocus_status, f"Focus laser failed: {exc}")
        finally:
            self.parent.after(0, self.finish_focus_laser)

    def start_axis_identification(self):
        if self.autofocus_running or self.focus_laser_running or self.axis_identification_running:
            return

        try:
            step_size = float(self.axis_step.get())
            repeats = int(self.axis_repeats.get())
            settle_time = float(self.axis_settle.get())
            min_tracks = int(self.axis_min_tracks.get())
        except (tk.TclError, ValueError):
            self.update_axis_status("Axis ID settings must be numeric.")
            return

        if step_size <= 0 or repeats <= 0 or settle_time < 0 or min_tracks <= 0:
            self.update_axis_status("Use positive step/repeats/tracks and non-negative settle time.")
            return

        hexapod = self.get_connected_hexapod()
        if hexapod is None:
            self.update_axis_status("Connect the hexapod before running axis identification.")
            return
        if not getattr(hexapod, "ready_for_commands", False):
            self.update_axis_status("Hexapod is busy.")
            return
        if self.camera_manager.capture_frame() is None:
            self.update_axis_status("No image available. Connect camera or load a test image first.")
            return

        self.axis_identification_running = True
        self.set_focus_buttons_enabled(False)
        self.set_axis_identification_buttons_enabled(False)
        self.update_axis_status("Axis identification running...")
        self.axis_identification_thread = threading.Thread(
            target=self.run_axis_identification,
            args=(hexapod, step_size, repeats, settle_time, min_tracks),
            daemon=True,
        )
        self.axis_identification_thread.start()

    def stop_axis_identification(self):
        self.axis_identification_running = False
        if hasattr(self, 'axis_status'):
            self.update_axis_status("Stopping axis identification...")

    def run_axis_identification(self, hexapod, step_size, repeats, settle_time, min_tracks):
        samples = []
        latest_annotation = None
        axes = [
            ("X", np.array([1.0, 0.0, 0.0])),
            ("Y", np.array([0.0, 1.0, 0.0])),
        ]

        try:
            for axis_name, axis_vector in axes:
                for direction in (1.0, -1.0):
                    for repeat_index in range(repeats):
                        if not self.axis_identification_running:
                            raise RuntimeError("Axis identification stopped.")

                        label = f"{axis_name}{'+' if direction > 0 else '-'} repeat {repeat_index + 1}/{repeats}"
                        self.parent.after(0, self.update_axis_status, f"Capturing baseline: {label}")
                        baseline = self.camera_manager.capture_frame()
                        if baseline is None:
                            raise RuntimeError("No baseline image available during axis identification.")

                        movement = axis_vector * direction * step_size
                        self.parent.after(0, self.update_axis_status, f"Moving hexapod: {label}")
                        moved = False
                        try:
                            self.move_hexapod_xy(hexapod, movement[0], movement[1])
                            moved = True
                            time.sleep(settle_time)

                            moved_frame = self.camera_manager.capture_frame()
                            if moved_frame is None:
                                raise RuntimeError("No moved image available during axis identification.")

                            measurement = self.estimate_feature_motion(baseline, moved_frame, min_tracks)
                            if measurement["valid"]:
                                equivalent_vector = measurement["mean_vector_px"] * direction
                                measurement.update({
                                    "axis": axis_name,
                                    "direction": direction,
                                    "repeat": repeat_index + 1,
                                    "equivalent_vector_px": equivalent_vector,
                                })
                                samples.append(measurement)
                                latest_annotation = self.annotate_axis_identification_frame(
                                    moved_frame,
                                    measurement,
                                    equivalent_vector,
                                    axis_name,
                                    direction,
                                )
                                self.parent.after(0, self.display_frame, latest_annotation)
                                self.parent.after(
                                    0,
                                    self.update_axis_status,
                                    (
                                        f"Accepted {label}: dx={equivalent_vector[0]:.2f}px, "
                                        f"dy={equivalent_vector[1]:.2f}px, tracks={measurement['track_count']}"
                                    ),
                                )
                            else:
                                measurement.update({"axis": axis_name, "direction": direction, "repeat": repeat_index + 1})
                                samples.append(measurement)
                                self.parent.after(0, self.update_axis_status, f"Rejected {label}: {measurement['reason']}")
                        finally:
                            if moved:
                                self.move_hexapod_xy(hexapod, -movement[0], -movement[1])
                                time.sleep(settle_time)

            results = self.calculate_axis_identification_results(samples, step_size)
            self.parent.after(0, self.write_axis_results, self.format_axis_identification_results(results))
            if latest_annotation is not None:
                self.parent.after(0, self.display_frame, latest_annotation)
            self.parent.after(0, self.update_axis_status, "Axis identification complete.")
        except Exception as exc:
            self.parent.after(0, self.write_axis_results, self.format_axis_identification_failure(samples, step_size, exc))
            self.parent.after(0, self.update_axis_status, f"Axis identification failed: {exc}")
        finally:
            self.parent.after(0, self.finish_axis_identification)

    def estimate_feature_motion(self, baseline, moved_frame, min_tracks):
        baseline_gray = self.prepare_tracking_image(baseline)
        moved_gray = self.prepare_tracking_image(moved_frame)
        if baseline_gray.shape != moved_gray.shape:
            return {"valid": False, "reason": "Frame size changed", "track_count": 0}

        points = cv2.goodFeaturesToTrack(
            baseline_gray,
            maxCorners=300,
            qualityLevel=0.01,
            minDistance=8,
            blockSize=7,
        )
        if points is None or len(points) < min_tracks:
            count = 0 if points is None else len(points)
            return {"valid": False, "reason": f"Only {count} features detected", "track_count": count}

        next_points, status, errors = cv2.calcOpticalFlowPyrLK(
            baseline_gray,
            moved_gray,
            points,
            None,
            winSize=(21, 21),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
        )
        if next_points is None or status is None:
            return {"valid": False, "reason": "Optical flow failed", "track_count": 0}

        good_mask = status.reshape(-1).astype(bool)
        if errors is not None:
            flow_errors = errors.reshape(-1)
            finite_errors = np.isfinite(flow_errors)
            if np.any(good_mask & finite_errors):
                median_error = np.median(flow_errors[good_mask & finite_errors])
                good_mask &= finite_errors & (flow_errors <= max(20.0, median_error * 4.0))

        previous = points.reshape(-1, 2)[good_mask]
        current = next_points.reshape(-1, 2)[good_mask]
        if len(previous) < min_tracks:
            return {"valid": False, "reason": f"Only {len(previous)} tracks survived LK", "track_count": len(previous)}

        displacements = current - previous
        median_vector = np.median(displacements, axis=0)
        residuals = np.linalg.norm(displacements - median_vector, axis=1)
        median_residual = float(np.median(residuals))
        mad_residual = float(np.median(np.abs(residuals - median_residual)))
        residual_limit = max(2.0, median_residual + 3.0 * max(mad_residual, 1e-6))
        inlier_mask = residuals <= residual_limit

        previous = previous[inlier_mask]
        current = current[inlier_mask]
        displacements = displacements[inlier_mask]
        if len(displacements) < min_tracks:
            return {"valid": False, "reason": f"Only {len(displacements)} inlier tracks", "track_count": len(displacements)}

        mean_vector = np.mean(displacements, axis=0)
        std_vector = np.std(displacements, axis=0)
        magnitude = float(np.linalg.norm(mean_vector))
        if magnitude < 0.05:
            return {"valid": False, "reason": "Measured image motion was too small", "track_count": len(displacements)}

        return {
            "valid": True,
            "reason": "accepted",
            "track_count": int(len(displacements)),
            "mean_vector_px": mean_vector.astype(float),
            "std_vector_px": std_vector.astype(float),
            "previous_points": previous,
            "current_points": current,
        }

    def prepare_tracking_image(self, frame):
        if frame.ndim == 2:
            gray = frame
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if gray.dtype == np.uint8:
            return gray
        return cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    def calculate_axis_identification_results(self, samples, step_size):
        results = {
            "step_size": step_size,
            "samples": samples,
            "axes": {},
            "calibration_matrix": None,
            "accepted_count": sum(1 for sample in samples if sample.get("valid")),
            "rejected_count": sum(1 for sample in samples if not sample.get("valid")),
        }

        for axis_name in ("X", "Y"):
            axis_samples = [sample for sample in samples if sample.get("valid") and sample.get("axis") == axis_name]
            if axis_samples:
                vectors = np.array([sample["equivalent_vector_px"] for sample in axis_samples], dtype=float)
                mean_vector = np.mean(vectors, axis=0)
                std_vector = np.std(vectors, axis=0)
                px_per_mm = mean_vector / step_size
                angle_deg = float(np.degrees(np.arctan2(mean_vector[1], mean_vector[0])))
                results["axes"][axis_name] = {
                    "valid": True,
                    "sample_count": len(axis_samples),
                    "mean_vector_px": mean_vector,
                    "std_vector_px": std_vector,
                    "px_per_mm": px_per_mm,
                    "magnitude_px": float(np.linalg.norm(mean_vector)),
                    "magnitude_px_per_mm": float(np.linalg.norm(px_per_mm)),
                    "angle_deg": angle_deg,
                    "track_count_mean": float(np.mean([sample["track_count"] for sample in axis_samples])),
                }
            else:
                results["axes"][axis_name] = {"valid": False, "sample_count": 0}

        x_axis = results["axes"].get("X", {})
        y_axis = results["axes"].get("Y", {})
        if x_axis.get("valid") and y_axis.get("valid"):
            x_vector = x_axis["mean_vector_px"]
            y_vector = y_axis["mean_vector_px"]
            dot = float(np.dot(x_vector, y_vector))
            denom = float(np.linalg.norm(x_vector) * np.linalg.norm(y_vector))
            if denom > 0:
                axis_angle = float(np.degrees(np.arccos(np.clip(dot / denom, -1.0, 1.0))))
            else:
                axis_angle = None
            results["axis_angle_deg"] = axis_angle
            results["orthogonality_error_deg"] = None if axis_angle is None else axis_angle - 90.0
            results["camera_y_phase_relative_to_image_y_deg"] = self.normalize_angle(y_axis["angle_deg"] - 90.0)
            results["calibration_matrix"] = np.column_stack((x_axis["px_per_mm"], y_axis["px_per_mm"]))
        return results

    def annotate_axis_identification_frame(self, frame, measurement, equivalent_vector, axis_name, direction):
        annotated = frame.copy()
        if annotated.ndim == 2:
            annotated = cv2.cvtColor(annotated, cv2.COLOR_GRAY2BGR)

        previous = measurement.get("previous_points", [])
        current = measurement.get("current_points", [])
        for start, end in zip(previous[:75], current[:75]):
            start_point = (int(round(start[0])), int(round(start[1])))
            end_point = (int(round(end[0])), int(round(end[1])))
            cv2.arrowedLine(annotated, start_point, end_point, (0, 255, 255), 1, tipLength=0.3)

        height, width = annotated.shape[:2]
        origin = (width // 2, height // 2)
        display_vector = equivalent_vector * 10.0
        end = (int(round(origin[0] + display_vector[0])), int(round(origin[1] + display_vector[1])))
        cv2.arrowedLine(annotated, origin, end, (0, 0, 255), 3, tipLength=0.25)
        cv2.putText(
            annotated,
            f"Hex {axis_name}{'+' if direction > 0 else '-'} -> +{axis_name}: ({equivalent_vector[0]:.2f}, {equivalent_vector[1]:.2f}) px",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
        return annotated

    def format_axis_identification_results(self, results):
        lines = [
            "Axis Difference Identification Results",
            "",
            f"Step size: {results['step_size']:.6f} mm",
            f"Accepted samples: {results['accepted_count']}",
            f"Rejected samples: {results['rejected_count']}",
            "",
        ]

        for axis_name in ("X", "Y"):
            axis = results["axes"].get(axis_name, {})
            if not axis.get("valid"):
                lines.append(f"Hexapod +{axis_name}: unavailable")
                continue
            vector = axis["mean_vector_px"]
            std_vector = axis["std_vector_px"]
            px_per_mm = axis["px_per_mm"]
            lines.extend([
                f"Hexapod +{axis_name} -> Camera vector:",
                f"  mean: dx={vector[0]:.3f} px, dy={vector[1]:.3f} px ({axis['magnitude_px']:.3f} px/step)",
                f"  std:  dx={std_vector[0]:.3f} px, dy={std_vector[1]:.3f} px",
                f"  scale: dx={px_per_mm[0]:.3f} px/mm, dy={px_per_mm[1]:.3f} px/mm ({axis['magnitude_px_per_mm']:.3f} px/mm)",
                f"  angle relative to image +X: {axis['angle_deg']:.2f} deg",
                f"  samples: {axis['sample_count']}, mean tracks: {axis['track_count_mean']:.1f}",
                "",
            ])

        if results.get("axis_angle_deg") is not None:
            lines.append(f"Measured angle between hexapod X/Y camera vectors: {results['axis_angle_deg']:.2f} deg")
            lines.append(f"Orthogonality error: {results['orthogonality_error_deg']:.2f} deg")
            lines.append(f"Camera_X vs Hexapod_X phase: {results['axes']['X']['angle_deg']:.2f} deg")
            lines.append(
                "Camera_Y vs Hexapod_Y phase: "
                f"{results['camera_y_phase_relative_to_image_y_deg']:.2f} deg relative to image +Y"
            )
            lines.append("")

        matrix = results.get("calibration_matrix")
        if matrix is not None:
            lines.extend([
                "Calibration matrix (camera px = matrix @ hexapod mm):",
                f"  [{matrix[0, 0]: .6f}  {matrix[0, 1]: .6f}]",
                f"  [{matrix[1, 0]: .6f}  {matrix[1, 1]: .6f}]",
                "",
            ])

        rejected = [sample for sample in results["samples"] if not sample.get("valid")]
        if rejected:
            lines.append("Rejected samples:")
            for sample in rejected:
                direction = "+" if sample.get("direction", 1) > 0 else "-"
                lines.append(
                    f"  {sample.get('axis', '?')}{direction} repeat {sample.get('repeat', '?')}: "
                    f"{sample.get('reason', 'unknown')}"
                )
        return "\n".join(lines) + "\n"

    def format_axis_identification_failure(self, samples, step_size, exc):
        partial = self.calculate_axis_identification_results(samples, step_size)
        return f"Axis identification failed: {exc}\n\n" + self.format_axis_identification_results(partial)

    def normalize_angle(self, angle_deg):
        return (angle_deg + 180.0) % 360.0 - 180.0

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

    def calculate_laser_blob_metric(self, frame):
        if frame is None:
            return {"found": False, "reason": "No frame", "annotated_image": None}

        if frame.ndim == 2:
            gray = frame
            annotated = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            annotated = frame.copy()

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        max_intensity = int(np.max(blurred))
        if max_intensity <= 0:
            return {
                "found": False,
                "reason": "Frame has no signal",
                "annotated_image": annotated,
            }

        otsu_threshold, _ = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        threshold_value = int(max(otsu_threshold, max_intensity * 0.35))
        _, mask = cv2.threshold(blurred, threshold_value, 255, cv2.THRESH_BINARY)

        kernel = np.ones((3, 3), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return {
                "found": False,
                "reason": "No blob found",
                "annotated_image": annotated,
            }

        contour = max(contours, key=cv2.contourArea)
        contour_area = float(cv2.contourArea(contour))
        if contour_area < 5.0:
            return {
                "found": False,
                "reason": "Blob too small",
                "annotated_image": annotated,
            }

        cv2.drawContours(annotated, [contour], -1, (255, 0, 0), 1)
        if len(contour) >= 5:
            ellipse = cv2.fitEllipse(contour)
            center, axes, _ = ellipse
            beam_size = float(np.sqrt(max(axes[0], 1e-6) * max(axes[1], 1e-6)))
            axis_difference = float(abs(axes[0] - axes[1]))
            cv2.ellipse(annotated, ellipse, (0, 255, 0), 2)
            cv2.circle(annotated, (int(center[0]), int(center[1])), 3, (0, 255, 255), -1)
        else:
            x, y, w, h = cv2.boundingRect(contour)
            center = (x + w / 2.0, y + h / 2.0)
            axes = (float(w), float(h))
            beam_size = float(np.sqrt(max(w, 1) * max(h, 1)))
            axis_difference = float(abs(w - h))
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(annotated, (int(center[0]), int(center[1])), 3, (0, 255, 255), -1)

        focus_score = 0.5 * beam_size + 0.5 * axis_difference

        return {
            "found": True,
            "beam_size_px": beam_size,
            "axis_difference_px": axis_difference,
            "focus_score": focus_score,
            "center": center,
            "axes": axes,
            "contour_area_px": contour_area,
            "annotated_image": annotated,
        }

    def get_connected_hexapod(self):
        hexapod_tab = getattr(self.main_gui, "hexapodTabObject", None)
        hexapod = getattr(hexapod_tab, "hexapod", None)
        if hexapod is None or getattr(hexapod, "ssh_API", None) is None:
            return None
        return hexapod

    def move_hexapod_z(self, hexapod, z_distance):
        hexapod.translate(np.array([0.0, 0.0, float(z_distance)]))
        self.wait_for_hexapod(hexapod)

    def move_hexapod_xy(self, hexapod, x_distance, y_distance):
        hexapod.translate(np.array([float(x_distance), float(y_distance), 0.0]))
        self.wait_for_hexapod(hexapod)

    def wait_for_hexapod(self, hexapod, timeout=30):
        start_time = time.time()
        while not getattr(hexapod, "ready_for_commands", False):
            if time.time() - start_time > timeout:
                raise TimeoutError("Hexapod movement timed out.")
            time.sleep(0.05)

    def finish_autofocus(self):
        self.autofocus_running = False
        if not self.focus_laser_running and not self.axis_identification_running:
            self.set_focus_buttons_enabled(True)

    def finish_focus_laser(self):
        self.focus_laser_running = False
        if not self.autofocus_running and not self.axis_identification_running:
            self.set_focus_buttons_enabled(True)

    def finish_axis_identification(self):
        self.axis_identification_running = False
        if not self.autofocus_running and not self.focus_laser_running:
            self.set_focus_buttons_enabled(True)
        self.set_axis_identification_buttons_enabled(True)

    def update_autofocus_status(self, text):
        self.autofocus_status.set(text)

    def update_axis_status(self, text):
        self.axis_status.set(text)

    def set_focus_buttons_enabled(self, enabled):
        state = 'normal' if enabled else 'disabled'
        self.autofocus_button['state'] = state
        self.focus_laser_button['state'] = state

    def set_axis_identification_buttons_enabled(self, enabled):
        self.axis_identification_button['state'] = 'normal' if enabled else 'disabled'
        self.stop_axis_identification_button['state'] = 'disabled' if enabled else 'normal'

    def apply_exposure_time(self):
        value = self.get_ranged_setting(self.exposure_time, "Exposure time", 12, 100000)
        if value is None:
            return
        self.apply_camera_setting(self.camera_manager.set_exposure_time, value)

    def apply_gain(self):
        value = self.get_ranged_setting(self.gain, "Gain", 0, 24)
        if value is None:
            return
        self.apply_camera_setting(self.camera_manager.set_gain, value)

    def apply_gamma(self):
        value = self.get_ranged_setting(self.gamma, "Camera gamma", 0, 4)
        if value is None:
            return
        self.apply_camera_setting(self.camera_manager.set_gamma, value)

    def apply_target_capture_fps(self):
        value = self.get_positive_setting(self.target_capture_fps, "Preview FPS")
        if value is None:
            return
        success, message = self.camera_manager.set_target_capture_fps(value)
        self.update_status(message)
        if not success:
            self.write_results(f"Camera setting error: {message}\n")

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

    def get_ranged_setting(self, variable, name, minimum, maximum):
        value = self.get_numeric_setting(variable, name)
        if value is None:
            return None
        if value < minimum or value > maximum:
            self.update_status(f"{name} must be between {minimum} and {maximum}")
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

    def display_image_in_label(self, label, frame):
        if frame is None:
            return
        self.display_frame(frame, label=label, max_size=(760, 420))

    def display_frame(self, frame, label=None, max_size=(960, 700)):
        if frame is None:
            return
        if label is None:
            label = self.image_label

        preview_frame = self.resize_for_display(frame, max_size)
        if preview_frame.ndim == 2:
            rgb_frame = cv2.cvtColor(preview_frame, cv2.COLOR_GRAY2RGB)
        else:
            rgb_frame = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb_frame)
        photo = ImageTk.PhotoImage(image)
        label.configure(image=photo, text="")
        label.image = photo

    def resize_for_display(self, frame, max_size):
        max_width, max_height = max_size
        height, width = frame.shape[:2]
        scale = min(max_width / width, max_height / height, 1.0)
        if scale == 1.0:
            return frame
        new_size = (int(width * scale), int(height * scale))
        return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)

    def update_status(self, override=None):
        if override is not None:
            self.status_text.set(override)
            return

        status = self.camera_manager.status
        if self.camera_manager.error:
            status = f"{status}: {self.camera_manager.error}"
        self.status_text.set(status)

    def update_status_throttled(self):
        now = time.perf_counter()
        if now - self.last_status_update >= 0.5:
            self.update_status()
            self.last_status_update = now

    def update_diagnostics(self):
        now = time.perf_counter()
        if now - self.last_diagnostics_update < 0.25:
            return
        self.last_diagnostics_update = now
        diagnostics = self.camera_manager.get_diagnostics()
        frame_age = diagnostics["frame_age_ms"]
        if frame_age is None:
            frame_age_text = "n/a"
        else:
            frame_age_text = f"{frame_age:6.0f} ms"
        self.diagnostics_text.set(
            f"Diagnostics: capture {diagnostics['capture_fps']:5.1f} FPS | "
            f"display {diagnostics['display_fps']:5.1f} FPS | "
            f"frame age {frame_age_text:>9} | "
            f"frame {diagnostics['dimensions']:<16} | "
            f"capture total {diagnostics['capture_timing_ms']['total']:6.1f} ms"
        )

    def empty_diagnostics_text(self):
        return (
            "Diagnostics: capture   0.0 FPS | display   0.0 FPS | "
            "frame age       n/a | frame No frame         | capture total    0.0 ms"
        )

    def write_results(self, text):
        self.results_text.delete('1.0', tk.END)
        self.results_text.insert('1.0', text)

    def write_compositing_status(self, text):
        self.compositing_status.delete('1.0', tk.END)
        self.compositing_status.insert('1.0', text)

    def write_axis_results(self, text):
        self.axis_results_text.delete('1.0', tk.END)
        self.axis_results_text.insert('1.0', text)

    def format_compositing_status(self, status):
        lines = [
            f"Status: {status['status']}",
            f"Tiles: {status['tile_count']}",
        ]
        if status.get("mosaic_shape") is not None:
            shape = status["mosaic_shape"]
            lines.append(f"Mosaic: {shape[1]} x {shape[0]} px")
        if status.get("registration") is not None:
            registration = status["registration"]
            lines.extend([
                f"Last shift: ({registration['shift_x_px']:.2f}, {registration['shift_y_px']:.2f}) px",
                f"Response: {registration['response']:.3f}",
            ])
        if status.get("error"):
            lines.append(f"Error: {status['error']}")
        return "\n".join(lines) + "\n"

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

    def format_focus_laser_results(self, measurements, best_position, best_focus_score):
        lines = [
            "Focus Laser Results",
            "",
            "Score = 0.5*beam size + 0.5*axis difference (smaller is better).",
            "",
        ]
        for measurement in measurements:
            position = measurement["position"]
            if measurement["found"]:
                marker = "*" if position == best_position else " "
                lines.append(
                    f"{marker} z={position:.4f} mm: "
                    f"beam={measurement['beam_size_px']:.2f} px, "
                    f"axis diff={measurement['axis_difference_px']:.2f} px, "
                    f"score={measurement['focus_score']:.2f}"
                )
            else:
                lines.append(f"  z={position:.4f} mm: no beam ({measurement.get('reason', 'unknown')})")
        lines.append("")
        lines.append(f"Best laser focus: z={best_position:.4f} mm")
        lines.append(f"Focus score: {best_focus_score:.2f}")
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
