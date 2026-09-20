import tkinter as tk
import tkinter.filedialog
from tkinter import ttk
import numpy as np
import threading
import time
import os
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from src.measurementTiming import angle_workflow_seconds, format_duration, heatmap_seconds


def generate_scan_positions(start, end, step):
    """Generate an inclusive grid without stepping beyond the requested end."""
    if not np.all(np.isfinite([start, end, step])):
        raise ValueError("Scan positions and step size must be finite")
    if step <= 0 or end < start:
        raise ValueError("Scan step must be positive and end must not precede start")
    count = int(np.floor((end - start) / step + 1e-12))
    positions = start + np.arange(count + 1, dtype=float) * step
    if np.isclose(positions[-1], end):
        positions[-1] = end
    return positions


def generate_centered_angles(degrees_of_sweep, step_count):
    """Return physical Rz offsets centered on the cell's starting orientation."""
    if not np.isfinite(degrees_of_sweep):
        raise ValueError("Degrees of sweep must be finite")
    if step_count < 1:
        raise ValueError("Angular step count must be at least 1")
    if degrees_of_sweep < 0:
        raise ValueError("Degrees of sweep must not be negative")
    if step_count == 1:
        return np.array([0.0])
    return np.linspace(-degrees_of_sweep / 2, degrees_of_sweep / 2, step_count)


def calculate_average_amplitude_noise(data):
    """Average population amplitude deviation over every angle/frequency pair."""
    if data.empty:
        return np.nan
    amplitudes = data.groupby(
        ["Degrees of Rotation", "FrequencyIn"], dropna=False
    )["AmplitudeOut"]
    deviations = amplitudes.std(ddof=0)[amplitudes.count() >= 2]
    if deviations.empty:
        return np.nan
    return float(deviations.mean())


class RasteringTab:
    """
    Tab for rastering the sample to detect fiducial markers.

    The fiducial is made up of 3 squares in an L-shape (right angle).
    - Areas where the fiducial is etched WILL reflect (high LIA magnitude)
    - Areas where the fiducial space is (unetched) will NOT reflect (low/zero LIA magnitude)

    This tab performs a snake-pattern raster scan and records LIA magnitude
    to build a 2D heatmap for fiducial detection.
    """

    # Default safe ranges for hexapod X/Y movement (mm)
    X_MIN = -25.0
    X_MAX = 25.0
    Y_MIN = -25.0
    Y_MAX = 25.0

    def __init__(self, parent, instruments, main_gui):
        self.parent = parent
        self.instruments = instruments
        self.main_gui = main_gui
        self.hexapod = None

        # Raster scan data
        self.scan_data = None  # Average amplitude noise at each grid cell
        self.phase_data = None
        self.raw_measurements = []
        self.cell_summaries = []
        self.x_positions = None
        self.y_positions = None
        self.scan_running = False
        self.scan_thread = None
        self.cancel_event = threading.Event()

        # Fiducial detection results
        self.fiducial_centers = []  # List of (x, y) centers for the 3 squares
        self.sample_angle = None
        self.sample_position = None

        self.setup_ui()

    def setup_ui(self):
        rastering_tab = self.parent

        # Create a main frame to hold the canvas for scrolling
        main_frame = tk.Frame(rastering_tab)
        main_frame.pack(fill=tk.BOTH, expand=1)

        # Create a canvas
        canvas = tk.Canvas(main_frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        # Add a scrollbar to the canvas
        scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure the canvas
        canvas.configure(yscrollcommand=scrollbar.set)

        # Create a frame inside the canvas to hold the widgets
        inner_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor='nw')

        # Create main frames
        params_frame = ttk.LabelFrame(inner_frame, text="Scan Parameters")
        params_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        control_frame = ttk.LabelFrame(inner_frame, text="Scan Control")
        control_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        output_frame = ttk.LabelFrame(inner_frame, text="Scan Output")
        output_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        results_frame = ttk.LabelFrame(inner_frame, text="Fiducial Detection Results")
        results_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        # === Scan Parameters Section ===
        # X range
        self.xStartLabel = tk.Label(params_frame, text="X Start (mm):")
        self.xStartLabel.grid(row=0, column=0, padx=10, pady=5, sticky=tk.E)
        self.xStartInput = tk.Entry(params_frame, width=10)
        self.xStartInput.insert(0, "-5.0")
        self.xStartInput.grid(row=0, column=1, padx=5, pady=5)

        self.xEndLabel = tk.Label(params_frame, text="X End (mm):")
        self.xEndLabel.grid(row=0, column=2, padx=10, pady=5, sticky=tk.E)
        self.xEndInput = tk.Entry(params_frame, width=10)
        self.xEndInput.insert(0, "5.0")
        self.xEndInput.grid(row=0, column=3, padx=5, pady=5)

        # Y range
        self.yStartLabel = tk.Label(params_frame, text="Y Start (mm):")
        self.yStartLabel.grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
        self.yStartInput = tk.Entry(params_frame, width=10)
        self.yStartInput.insert(0, "-5.0")
        self.yStartInput.grid(row=1, column=1, padx=5, pady=5)

        self.yEndLabel = tk.Label(params_frame, text="Y End (mm):")
        self.yEndLabel.grid(row=1, column=2, padx=10, pady=5, sticky=tk.E)
        self.yEndInput = tk.Entry(params_frame, width=10)
        self.yEndInput.insert(0, "5.0")
        self.yEndInput.grid(row=1, column=3, padx=5, pady=5)

        # Step size
        self.stepSizeLabel = tk.Label(params_frame, text="Step Size (mm):")
        self.stepSizeLabel.grid(row=2, column=0, padx=10, pady=5, sticky=tk.E)
        self.stepSizeInput = tk.Entry(params_frame, width=10)
        self.stepSizeInput.insert(0, "0.1")
        self.stepSizeInput.grid(row=2, column=1, padx=5, pady=5)

        # Dwell time
        self.dwellTimeLabel = tk.Label(params_frame, text="Dwell Time (s):")
        self.dwellTimeLabel.grid(row=2, column=2, padx=10, pady=5, sticky=tk.E)
        self.dwellTimeInput = tk.Entry(params_frame, width=10)
        self.dwellTimeInput.insert(0, "0.1")
        self.dwellTimeInput.grid(row=2, column=3, padx=5, pady=5)

        # Threshold for fiducial detection
        self.thresholdLabel = tk.Label(params_frame, text="Detection Threshold:")
        self.thresholdLabel.grid(row=3, column=0, padx=10, pady=5, sticky=tk.E)
        self.thresholdInput = tk.Entry(params_frame, width=10)
        self.thresholdInput.insert(0, "0.5")
        self.thresholdInput.grid(row=3, column=1, padx=5, pady=5)

        self.thresholdInfoLabel = tk.Label(params_frame, text="(fraction of max signal)", font=('Arial', 8))
        self.thresholdInfoLabel.grid(row=3, column=2, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # Return to origin checkbox
        self.returnToOrigin = tk.BooleanVar(value=True)
        self.returnToOriginCheck = tk.Checkbutton(params_frame, text="Return to origin after scan",
                                                   variable=self.returnToOrigin)
        self.returnToOriginCheck.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky=tk.W)

        # === Control Section ===
        self.startScanButton = tk.Button(control_frame, text="Start Raster Scan",
                                         command=self.start_raster_scan, state="disabled")
        self.startScanButton.grid(row=0, column=0, padx=10, pady=10)

        self.stopScanButton = tk.Button(control_frame, text="Stop Scan",
                                        command=self.stop_raster_scan, state="disabled")
        self.stopScanButton.grid(row=0, column=1, padx=10, pady=10)

        self.detectFiducialButton = tk.Button(control_frame, text="Detect Fiducial",
                                              command=self.detect_fiducial, state="disabled")
        self.detectFiducialButton.grid(row=0, column=2, padx=10, pady=10)

        self.saveDataButton = tk.Button(control_frame, text="Save Scan Data",
                                        command=self.save_scan_data, state="disabled")
        self.saveDataButton.grid(row=0, column=3, padx=10, pady=10)

        self.returnOriginButton = tk.Button(control_frame, text="Return to Origin",
                                            command=self.return_to_origin, state="disabled")
        self.returnOriginButton.grid(row=0, column=4, padx=10, pady=10)

        # Progress bar
        self.progressLabel = tk.Label(control_frame, text="Progress:")
        self.progressLabel.grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
        self.progressBar = ttk.Progressbar(control_frame, length=300, mode='determinate')
        self.progressBar.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky='ew')

        self.progressText = tk.StringVar(value="Ready")
        self.progressTextLabel = tk.Label(control_frame, textvariable=self.progressText)
        self.progressTextLabel.grid(row=1, column=3, columnspan=2, padx=10, pady=5)

        self.measurementEstimate = tk.Label(control_frame, text="Estimated time: calculating...")
        self.measurementEstimate.grid(
            row=2, column=0, columnspan=5, padx=10, pady=(2, 8), sticky=tk.W
        )

        # === Output Section (Heatmap) ===
        self.fig = Figure(figsize=(6, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('X Position (mm)')
        self.ax.set_ylabel('Y Position (mm)')
        self.ax.set_title('Average Amplitude Noise Heatmap')

        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=output_frame)
        self.canvas_plot.draw()
        self.canvas_plot.get_tk_widget().grid(row=0, column=0, padx=10, pady=10)

        # === Results Section ===
        self.resultsText = tk.Text(results_frame, height=8, width=60, font=('Arial', 10))
        self.resultsText.grid(row=0, column=0, padx=10, pady=10)
        self.resultsText.insert('1.0', "No fiducial detected yet.\nRun a scan and click 'Detect Fiducial'.\n")

        # Configure grid weights
        inner_frame.grid_columnconfigure(0, weight=1)
        inner_frame.grid_columnconfigure(1, weight=1)

        # Update scroll region when the size of the frame changes
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner_frame.bind('<Configure>', _on_frame_configure)
        for entry in (
            self.xStartInput, self.xEndInput, self.yStartInput, self.yEndInput,
            self.stepSizeInput,
        ):
            entry.bind("<KeyRelease>", lambda _event: self.update_measurement_estimate())
        self.parent.after(0, self.update_measurement_estimate)

        # Bind mouse wheel to scroll
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def return_to_origin(self):
        """Move hexapod back to origin (0, 0, 0)."""
        hexapod = self.get_hexapod()
        if hexapod is None:
            self.progressText.set("Error: Hexapod not connected")
            return

        if not hexapod.ready_for_commands:
            self.progressText.set("Error: Hexapod busy")
            return

        self.progressText.set("Returning to origin...")

        def do_return():
            try:
                # Get current position from hexapod status
                hexapod.getState()
                if hexapod.status_dict:
                    current_x = hexapod.status_dict.get("s_mtp_tx", 0)
                    current_y = hexapod.status_dict.get("s_mtp_ty", 0)

                    # Move to origin
                    hexapod.translate(np.array([-current_x, -current_y, 0.0]))
                    while not hexapod.ready_for_commands:
                        time.sleep(0.05)

                    self.parent.after(0, lambda: self.progressText.set("Returned to origin"))
                else:
                    self.parent.after(0, lambda: self.progressText.set("Could not get hexapod position"))
            except Exception as e:
                self.parent.after(0, lambda: self.progressText.set(f"Error: {e}"))

        threading.Thread(target=do_return).start()

    def update_measurement_estimate(self):
        try:
            x_start = float(self.xStartInput.get())
            x_end = float(self.xEndInput.get())
            y_start = float(self.yStartInput.get())
            y_end = float(self.yEndInput.get())
            step = float(self.stepSizeInput.get())
            angles = int(self.main_gui.hexapodTabObject.stepCount.get())
            sweep_seconds = self.main_gui.laserTabObject.estimate_frequency_sweep_seconds()
            x_count = len(generate_scan_positions(x_start, x_end, step))
            y_count = len(generate_scan_positions(y_start, y_end, step))
            rotation_seconds = angle_workflow_seconds(angles, sweep_seconds)
            estimate = heatmap_seconds(x_count * y_count, rotation_seconds)
            self.measurementEstimate.configure(
                text=f"Estimated heatmap time: {format_duration(estimate)}"
            )
        except (AttributeError, TypeError, ValueError, tk.TclError):
            self.measurementEstimate.configure(
                text="Estimated heatmap time: enter valid settings"
            )

    def validate_parameters(self):
        """Validate scan parameters and return them if valid."""
        try:
            x_start = float(self.xStartInput.get())
            x_end = float(self.xEndInput.get())
            y_start = float(self.yStartInput.get())
            y_end = float(self.yEndInput.get())
            step_size = float(self.stepSizeInput.get())
            dwell_time = float(self.dwellTimeInput.get())
            threshold = float(self.thresholdInput.get())

            values = [x_start, x_end, y_start, y_end, step_size, dwell_time, threshold]
            if not np.all(np.isfinite(values)):
                raise ValueError("Scan parameters must be finite numbers")

            # Check ranges
            if x_start < self.X_MIN or x_end > self.X_MAX:
                raise ValueError(f"X range must be between {self.X_MIN} and {self.X_MAX} mm")
            if y_start < self.Y_MIN or y_end > self.Y_MAX:
                raise ValueError(f"Y range must be between {self.Y_MIN} and {self.Y_MAX} mm")
            if x_start >= x_end:
                raise ValueError("X Start must be less than X End")
            if y_start >= y_end:
                raise ValueError("Y Start must be less than Y End")
            if step_size <= 0:
                raise ValueError("Step size must be positive")
            if dwell_time <= 0:
                raise ValueError("Dwell time must be positive")
            if threshold < 0 or threshold > 1:
                raise ValueError("Threshold must be between 0 and 1")

            return {
                'x_start': x_start,
                'x_end': x_end,
                'y_start': y_start,
                'y_end': y_end,
                'step_size': step_size,
                'dwell_time': dwell_time,
                'threshold': threshold
            }
        except ValueError as e:
            self.progressText.set(f"Error: {e}")
            return None

    def get_hexapod(self):
        """Get hexapod reference from main GUI."""
        if self.hexapod is None:
            # Try to get hexapod from the hexapod tab
            if hasattr(self.main_gui, 'hexapodTabObject') and self.main_gui.hexapodTabObject.hexapod:
                self.hexapod = self.main_gui.hexapodTabObject.hexapod
        return self.hexapod

    def update_hexapod_command_controls(self, ready):
        command_state = tk.NORMAL if ready and not self.scan_running else tk.DISABLED
        self.startScanButton.configure(state=command_state)
        self.returnOriginButton.configure(state=command_state)

    def start_raster_scan(self):
        """Start the raster scan in a background thread."""
        params = self.validate_parameters()
        if params is None:
            return

        try:
            laser_tab = self.main_gui.laserTabObject
            hexapod_tab = self.main_gui.hexapodTabObject
            params["laser_settings"] = laser_tab.collect_measurement_settings()
            params["wait_for_convergence"] = bool(laser_tab.wait_for_convergence.get())
            params["angles"] = generate_centered_angles(
                float(hexapod_tab.degrees_of_sweep.get()),
                int(hexapod_tab.stepCount.get()),
            )
            params["return_to_origin"] = bool(self.returnToOrigin.get())
        except (AttributeError, TypeError, ValueError) as exc:
            self.progressText.set(f"Error: {exc}")
            return

        hexapod = self.get_hexapod()
        if hexapod is None:
            self.progressText.set("Error: Hexapod not connected")
            return

        if not hexapod.ready_for_commands:
            self.progressText.set("Error: Hexapod busy")
            return
        if getattr(hexapod, "laser_position", None) is None:
            self.progressText.set("Error: Calibrate the laser position before angular rastering")
            return
        automation_tab = getattr(self.main_gui, "automationTabObject", None)
        automation_manager = getattr(automation_tab, "manager", None)
        if automation_manager is not None and getattr(automation_manager, "running", False):
            self.progressText.set("Error: Rotation automation is already running")
            return
        if not self.instruments.workflow_lock.acquire(blocking=False):
            self.progressText.set("Error: Instruments are in use by another workflow")
            return
        params["workflow_lock_acquired"] = True

        # Update UI state
        self.cancel_event.clear()
        self.fiducial_centers = []
        self.sample_angle = None
        self.sample_position = None
        self.scan_running = True
        self.startScanButton['state'] = 'disabled'
        self.stopScanButton['state'] = 'normal'
        self.detectFiducialButton['state'] = 'disabled'
        self.saveDataButton['state'] = 'disabled'

        # Start scan in background thread
        try:
            self.scan_thread = threading.Thread(target=self._run_raster_scan, args=(params,))
            self.scan_thread.start()
        except Exception:
            self.instruments.workflow_lock.release()
            self.scan_running = False
            raise

    def _run_raster_scan(self, params):
        """Run an angular frequency sweep at every cell in a snake-pattern grid."""
        x_start = params['x_start']
        x_end = params['x_end']
        y_start = params['y_start']
        y_end = params['y_end']
        step_size = params['step_size']
        dwell_time = params['dwell_time']
        angles = params["angles"]
        laser_settings = params["laser_settings"]
        convergence_check = params["wait_for_convergence"]

        self.x_positions = generate_scan_positions(x_start, x_end, step_size)
        self.y_positions = generate_scan_positions(y_start, y_end, step_size)

        n_x = len(self.x_positions)
        n_y = len(self.y_positions)
        total_cells = n_x * n_y
        total_sweeps = total_cells * len(angles)

        self.scan_data = np.full((n_y, n_x), np.nan)
        self.phase_data = None
        self.raw_measurements = []
        self.cell_summaries = []

        hexapod = self.get_hexapod()
        completed_sweeps = 0

        current_x = 0.0
        current_y = 0.0
        final_status = "Scan complete"

        try:
            self._move_and_wait(lambda: hexapod.translate(np.array([x_start, y_start, 0.0])))
            current_x = x_start
            current_y = y_start

            for j, y in enumerate(self.y_positions):
                if self.cancel_event.is_set():
                    break

                if j > 0:
                    delta_y = y - current_y
                    self._move_and_wait(lambda dy=delta_y: hexapod.translate(np.array([0.0, dy, 0.0])))
                    current_y = y

                if j % 2 == 0:
                    x_range = self.x_positions
                    x_indices = range(n_x)
                else:
                    x_range = self.x_positions[::-1]
                    x_indices = range(n_x - 1, -1, -1)

                for i, x in zip(x_indices, x_range):
                    if self.cancel_event.is_set():
                        break

                    delta_x = x - current_x
                    if not np.isclose(delta_x, 0.0):
                        self._move_and_wait(lambda dx=delta_x: hexapod.translate(np.array([dx, 0.0, 0.0])))
                        current_x = x

                    if self.cancel_event.wait(dwell_time):
                        break

                    cell_frames = []
                    current_angle = 0.0
                    cell_error = None
                    try:
                        for angle_index, angle in enumerate(angles):
                            if self.cancel_event.is_set():
                                break
                            angle_delta = float(angle - current_angle)
                            if not np.isclose(angle_delta, 0.0):
                                self._move_and_wait(
                                    lambda delta=angle_delta: hexapod.rotateAroundLaser(
                                        np.array([0.0, 0.0, delta])
                                    )
                                )
                                current_angle = float(angle)

                            sweep = self.instruments.measure_frequency_sweep(
                                laser_settings,
                                convergence_check=convergence_check,
                                degree=float(angle),
                                cancel_event=self.cancel_event,
                            )
                            if not sweep.empty:
                                sweep = sweep.copy()
                                sweep.insert(0, "RasterRow", j)
                                sweep.insert(1, "RasterColumn", i)
                                sweep.insert(2, "X_Position", float(x))
                                sweep.insert(3, "Y_Position", float(y))
                                sweep.insert(4, "AngleIndex", angle_index)
                                cell_frames.append(sweep)
                                self.raw_measurements.append(sweep)

                            completed_sweeps += 1
                            progress = completed_sweeps / total_sweeps * 100
                            text = (
                                f"Cell {len(self.cell_summaries) + 1}/{total_cells}, "
                                f"angle {angle_index + 1}/{len(angles)}"
                            )
                            self.parent.after(
                                0,
                                lambda p=progress, message=text: self._update_progress(p, message),
                            )
                    except Exception as exc:
                        cell_error = exc
                    finally:
                        if not np.isclose(current_angle, 0.0):
                            try:
                                self._move_and_wait(
                                    lambda: hexapod.rotateAroundLaser(
                                        np.array([0.0, 0.0, -current_angle])
                                    ),
                                    allow_cancel=False,
                                )
                            except Exception as exc:
                                if cell_error is None:
                                    cell_error = exc
                                else:
                                    cell_error = RuntimeError(
                                        f"{cell_error}; orientation restore failed: {exc}"
                                    )

                    if cell_frames:
                        cell_data = pd.concat(cell_frames, ignore_index=True)
                        average_noise = calculate_average_amplitude_noise(cell_data)
                        self.scan_data[j, i] = average_noise
                        self.cell_summaries.append({
                            "RasterRow": j,
                            "RasterColumn": i,
                            "X_Position": float(x),
                            "Y_Position": float(y),
                            "AverageAmplitudeNoise": average_noise,
                            "AngleCount": int(cell_data["Degrees of Rotation"].nunique()),
                            "FrequencyCount": int(cell_data["FrequencyIn"].nunique()),
                            "SampleCount": len(cell_data),
                            "Status": (
                                "failed" if cell_error is not None
                                else "cancelled" if self.cancel_event.is_set()
                                else "completed"
                            ),
                        })
                        self.parent.after(0, self._update_heatmap)
                    if cell_error is not None:
                        raise cell_error

            if self.cancel_event.is_set():
                final_status = "Scan cancelled"
        except InterruptedError:
            final_status = "Scan cancelled"
        except Exception as exc:
            final_status = f"Scan failed: {exc}"
        finally:
            if params["return_to_origin"] and (not np.isclose(current_x, 0.0) or not np.isclose(current_y, 0.0)):
                try:
                    self._move_and_wait(
                        lambda: hexapod.translate(np.array([-current_x, -current_y, 0.0])),
                        allow_cancel=False,
                    )
                except Exception as exc:
                    final_status = f"{final_status}; return failed: {exc}"
            if params.get("workflow_lock_acquired"):
                self.instruments.workflow_lock.release()
            self.parent.after(0, self._update_heatmap)
            self.parent.after(0, lambda status=final_status: self._scan_complete(status))

    def _move_and_wait(self, command, allow_cancel=True, timeout=120.0):
        """Submit one motion command and wait for the controller to become ready."""
        started = time.monotonic()
        while not self.get_hexapod().ready_for_commands:
            if allow_cancel and self.cancel_event.is_set():
                raise InterruptedError("Scan cancelled")
            if time.monotonic() - started > timeout:
                raise TimeoutError("Timed out waiting for hexapod readiness")
            time.sleep(0.05)
        if allow_cancel and self.cancel_event.is_set():
            raise InterruptedError("Scan cancelled")
        result = command()
        if result != "Success.":
            raise RuntimeError(f"Hexapod move failed: {result}")
        started = time.monotonic()
        while not self.get_hexapod().ready_for_commands:
            if time.monotonic() - started > timeout:
                raise TimeoutError("Timed out waiting for hexapod movement")
            time.sleep(0.05)

    def _update_progress(self, progress, text):
        """Update progress bar and text."""
        self.progressBar['value'] = progress
        self.progressText.set(text)

    def _update_heatmap(self):
        """Update the heatmap display."""
        if self.scan_data is None:
            return

        self.ax.clear()

        # Create heatmap
        if self.x_positions is not None and self.y_positions is not None:
            extent = [self.x_positions[0], self.x_positions[-1],
                      self.y_positions[0], self.y_positions[-1]]
            masked_data = np.ma.masked_invalid(self.scan_data)
            im = self.ax.imshow(masked_data, extent=extent, origin='lower',
                               aspect='auto', cmap='hot')
            self.ax.set_xlabel('X Position (mm)')
            self.ax.set_ylabel('Y Position (mm)')
            self.ax.set_title('Average Amplitude Noise Across Frequencies and Angles')

        self.canvas_plot.draw()

    def _scan_complete(self, status="Scan complete"):
        """Called when scan is complete."""
        self.scan_running = False
        hexapod = self.get_hexapod()
        ready = hexapod is not None and getattr(hexapod, "ready_for_commands", False)
        self.startScanButton['state'] = 'normal' if ready else 'disabled'
        self.returnOriginButton['state'] = 'normal' if ready else 'disabled'
        self.stopScanButton['state'] = 'disabled'
        has_data = bool(self.cell_summaries or self.raw_measurements)
        complete_map = status == "Scan complete" and np.isfinite(self.scan_data).any()
        self.detectFiducialButton['state'] = 'normal' if complete_map else 'disabled'
        self.saveDataButton['state'] = 'normal' if has_data else 'disabled'
        self.progressText.set(status)

    def stop_raster_scan(self):
        """Stop the raster scan."""
        self.cancel_event.set()
        self.progressText.set("Stopping scan...")

        # Accepted moves are allowed to settle so the workflow can restore a known pose.

    def detect_fiducial(self):
        """
        Detect the fiducial marker from the scan data.

        The fiducial consists of 3 squares arranged in an L-shape (right angle).
        High LIA magnitude = etched area (reflective)
        Low LIA magnitude = unetched area (non-reflective)

        Algorithm:
        1. Threshold the image to create binary mask
        2. Find connected components (the 3 squares)
        3. Calculate centroids of each square
        4. Determine the corner square and calculate sample angle
        """
        if self.scan_data is None:
            self.resultsText.delete('1.0', tk.END)
            self.resultsText.insert('1.0', "No scan data available. Run a scan first.\n")
            return

        try:
            threshold = float(self.thresholdInput.get())

            # Normalize data
            data_max = np.nanmax(self.scan_data)
            if not np.isfinite(data_max) or data_max == 0:
                self.resultsText.delete('1.0', tk.END)
                self.resultsText.insert('1.0', "Error: No signal detected in scan data.\n")
                return

            normalized_data = self.scan_data / data_max

            # Create binary mask (high signal = fiducial squares)
            binary_mask = normalized_data > threshold

            # Find connected components using simple flood fill
            labeled, num_features = self._label_connected_components(binary_mask)

            if num_features < 3:
                self.resultsText.delete('1.0', tk.END)
                self.resultsText.insert('1.0',
                    f"Warning: Found {num_features} regions, expected 3.\n"
                    f"Try adjusting the threshold value.\n")
                if num_features == 0:
                    return

            # Calculate centroids for each component
            centroids = []
            for label in range(1, num_features + 1):
                component_mask = labeled == label
                y_indices, x_indices = np.where(component_mask)

                if len(x_indices) > 0:
                    # Convert pixel indices to mm coordinates
                    x_center = np.mean(x_indices)
                    y_center = np.mean(y_indices)

                    x_mm = self.x_positions[0] + x_center * (self.x_positions[-1] - self.x_positions[0]) / (len(self.x_positions) - 1)
                    y_mm = self.y_positions[0] + y_center * (self.y_positions[-1] - self.y_positions[0]) / (len(self.y_positions) - 1)

                    centroids.append((x_mm, y_mm, len(x_indices)))  # x, y, area in pixels

            # Sort by area to identify the squares
            centroids.sort(key=lambda c: c[2], reverse=True)

            # Take top 3 centroids (if available)
            self.fiducial_centers = [(c[0], c[1]) for c in centroids[:min(3, len(centroids))]]

            # Calculate sample angle and position from the L-shape
            if len(self.fiducial_centers) >= 3:
                self._calculate_sample_orientation()

            # Update results display
            self._display_results()

            # Update heatmap with detected fiducial markers
            self._update_heatmap_with_fiducials()

        except Exception as e:
            self.resultsText.delete('1.0', tk.END)
            self.resultsText.insert('1.0', f"Error during fiducial detection: {e}\n")

    def _label_connected_components(self, binary_mask):
        """Simple connected component labeling using flood fill."""
        labeled = np.zeros_like(binary_mask, dtype=int)
        current_label = 0

        def flood_fill(start_y, start_x, label):
            stack = [(start_y, start_x)]
            while stack:
                y, x = stack.pop()
                if (0 <= y < binary_mask.shape[0] and
                    0 <= x < binary_mask.shape[1] and
                    binary_mask[y, x] and
                    labeled[y, x] == 0):
                    labeled[y, x] = label
                    stack.extend([(y+1, x), (y-1, x), (y, x+1), (y, x-1)])

        for y in range(binary_mask.shape[0]):
            for x in range(binary_mask.shape[1]):
                if binary_mask[y, x] and labeled[y, x] == 0:
                    current_label += 1
                    flood_fill(y, x, current_label)

        return labeled, current_label

    def _calculate_sample_orientation(self):
        """
        Calculate sample position and angle from the 3 fiducial squares.

        The L-shape has one corner square and two end squares.
        The corner square is the one closest to the other two.
        """
        if len(self.fiducial_centers) < 3:
            return

        # Find distances between all pairs
        p1, p2, p3 = self.fiducial_centers[:3]

        d12 = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
        d13 = np.sqrt((p1[0] - p3[0])**2 + (p1[1] - p3[1])**2)
        d23 = np.sqrt((p2[0] - p3[0])**2 + (p2[1] - p3[1])**2)

        # The corner square is the one with smallest sum of distances to others
        sum1 = d12 + d13
        sum2 = d12 + d23
        sum3 = d13 + d23

        if sum1 <= sum2 and sum1 <= sum3:
            corner = p1
            end1, end2 = p2, p3
        elif sum2 <= sum1 and sum2 <= sum3:
            corner = p2
            end1, end2 = p1, p3
        else:
            corner = p3
            end1, end2 = p1, p2

        # Calculate angle from the corner to the two ends
        angle1 = np.arctan2(end1[1] - corner[1], end1[0] - corner[0])
        angle2 = np.arctan2(end2[1] - corner[1], end2[0] - corner[0])

        # Sample orientation is the average angle (one arm of the L)
        # We'll use the arm that's more horizontal as reference
        if abs(np.cos(angle1)) > abs(np.cos(angle2)):
            self.sample_angle = np.degrees(angle1)
        else:
            self.sample_angle = np.degrees(angle2)

        # Sample position is the corner of the L
        self.sample_position = corner

    def _display_results(self):
        """Display fiducial detection results."""
        self.resultsText.delete('1.0', tk.END)

        result_str = "=== Fiducial Detection Results ===\n\n"

        result_str += f"Number of squares detected: {len(self.fiducial_centers)}\n\n"

        for i, (x, y) in enumerate(self.fiducial_centers):
            result_str += f"Square {i+1} center: X={x:.3f} mm, Y={y:.3f} mm\n"

        result_str += "\n"

        if self.sample_position:
            result_str += f"Sample corner position: X={self.sample_position[0]:.3f} mm, Y={self.sample_position[1]:.3f} mm\n"

        if self.sample_angle is not None:
            result_str += f"Sample angle: {self.sample_angle:.2f} degrees\n"

        self.resultsText.insert('1.0', result_str)

    def _update_heatmap_with_fiducials(self):
        """Update heatmap to show detected fiducial centers."""
        self._update_heatmap()

        # Plot fiducial centers
        for i, (x, y) in enumerate(self.fiducial_centers):
            self.ax.plot(x, y, 'b+', markersize=15, markeredgewidth=2)
            self.ax.annotate(f'{i+1}', (x, y), textcoords="offset points",
                            xytext=(5, 5), fontsize=10, color='blue')

        # Draw lines connecting the L-shape if we have 3 points
        if len(self.fiducial_centers) >= 3 and self.sample_position:
            corner = self.sample_position
            for (x, y) in self.fiducial_centers:
                if (x, y) != corner:
                    self.ax.plot([corner[0], x], [corner[1], y], 'g--', linewidth=2)

        self.canvas_plot.draw()

    def save_scan_data(self):
        """Save the heatmap summary and every raw frequency-sweep sample."""
        if not self.cell_summaries and not self.raw_measurements:
            self.progressText.set("No data to save")
            return

        file_path = tk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Scan Data"
        )

        if file_path:
            try:
                summary = pd.DataFrame(self.cell_summaries)
                summary.to_csv(file_path, index=False)

                base_path, extension = os.path.splitext(file_path)
                raw_path = f"{base_path}_raw{extension or '.csv'}"
                raw = pd.concat(self.raw_measurements, ignore_index=True)
                raw.to_csv(raw_path, index=False)

                # Also save fiducial results if available
                if self.fiducial_centers:
                    results_path = f"{base_path}_fiducial_results.txt"
                    with open(results_path, 'w') as f:
                        f.write("Fiducial Detection Results\n")
                        f.write("=" * 30 + "\n\n")
                        for i, (x, y) in enumerate(self.fiducial_centers):
                            f.write(f"Square {i+1}: X={x:.3f} mm, Y={y:.3f} mm\n")
                        if self.sample_position:
                            f.write(f"\nCorner Position: X={self.sample_position[0]:.3f} mm, Y={self.sample_position[1]:.3f} mm\n")
                        if self.sample_angle is not None:
                            f.write(f"Sample Angle: {self.sample_angle:.2f} degrees\n")

                self.progressText.set(
                    f"Saved {os.path.basename(file_path)} and {os.path.basename(raw_path)}"
                )

            except Exception as e:
                self.progressText.set(f"Error saving: {e}")
