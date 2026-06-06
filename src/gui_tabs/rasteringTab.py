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
        self.scan_data = None  # Will be a 2D numpy array of LIA amplitudes (for heatmap)
        self.phase_data = None  # Will be a 2D numpy array of LIA phases
        self.x_positions = None
        self.y_positions = None
        self.scan_running = False
        self.scan_thread = None

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
                                         command=self.start_raster_scan)
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
                                            command=self.return_to_origin)
        self.returnOriginButton.grid(row=0, column=4, padx=10, pady=10)

        # Progress bar
        self.progressLabel = tk.Label(control_frame, text="Progress:")
        self.progressLabel.grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
        self.progressBar = ttk.Progressbar(control_frame, length=300, mode='determinate')
        self.progressBar.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky='ew')

        self.progressText = tk.StringVar(value="Ready")
        self.progressTextLabel = tk.Label(control_frame, textvariable=self.progressText)
        self.progressTextLabel.grid(row=1, column=3, columnspan=2, padx=10, pady=5)

        # === Output Section (Heatmap) ===
        self.fig = Figure(figsize=(6, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('X Position (mm)')
        self.ax.set_ylabel('Y Position (mm)')
        self.ax.set_title('LIA Magnitude Heatmap')

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

    def start_raster_scan(self):
        """Start the raster scan in a background thread."""
        params = self.validate_parameters()
        if params is None:
            return

        hexapod = self.get_hexapod()
        if hexapod is None:
            self.progressText.set("Error: Hexapod not connected")
            return

        if not hexapod.ready_for_commands:
            self.progressText.set("Error: Hexapod busy")
            return

        # Update UI state
        self.scan_running = True
        self.startScanButton['state'] = 'disabled'
        self.stopScanButton['state'] = 'normal'
        self.detectFiducialButton['state'] = 'disabled'
        self.saveDataButton['state'] = 'disabled'

        # Start scan in background thread
        self.scan_thread = threading.Thread(target=self._run_raster_scan, args=(params,))
        self.scan_thread.start()

    def _run_raster_scan(self, params):
        """Execute the snake-pattern raster scan."""
        x_start = params['x_start']
        x_end = params['x_end']
        y_start = params['y_start']
        y_end = params['y_end']
        step_size = params['step_size']
        dwell_time = params['dwell_time']

        # Generate position arrays
        self.x_positions = np.arange(x_start, x_end + step_size, step_size)
        self.y_positions = np.arange(y_start, y_end + step_size, step_size)

        n_x = len(self.x_positions)
        n_y = len(self.y_positions)
        total_points = n_x * n_y

        # Initialize data arrays
        self.scan_data = np.zeros((n_y, n_x))  # Amplitude data for heatmap
        self.phase_data = np.zeros((n_y, n_x))  # Phase data

        hexapod = self.get_hexapod()
        current_point = 0

        # Track current position for relative moves
        current_x = 0.0
        current_y = 0.0

        try:
            # First, move to the starting position
            delta_x = x_start - current_x
            delta_y = y_start - current_y
            hexapod.translate(np.array([delta_x, delta_y, 0.0]))
            while not hexapod.ready_for_commands:
                time.sleep(0.05)
            current_x = x_start
            current_y = y_start

            for j, y in enumerate(self.y_positions):
                if not self.scan_running:
                    break

                # Move to the Y position for this row (if not first row)
                if j > 0:
                    delta_y = y - current_y
                    hexapod.translate(np.array([0.0, delta_y, 0.0]))
                    while not hexapod.ready_for_commands:
                        time.sleep(0.05)
                    current_y = y

                # Snake pattern: alternate X direction on each row
                if j % 2 == 0:
                    x_range = self.x_positions
                    x_indices = range(n_x)
                else:
                    x_range = self.x_positions[::-1]
                    x_indices = range(n_x - 1, -1, -1)

                for i, x in zip(x_indices, x_range):
                    if not self.scan_running:
                        break

                    # Move hexapod to position using relative move
                    delta_x = x - current_x
                    if abs(delta_x) > 0.0001:  # Only move if there's actual displacement
                        hexapod.translate(np.array([delta_x, 0.0, 0.0]))
                        time_waiting = 0
                        while not hexapod.ready_for_commands:
                            if time_waiting > 0:
                                print(f"Waiting for hexapod to be ready... {time_waiting:.1f}s")
                            time.sleep(0.05)
                            time_waiting += 0.05
                        current_x = x

                    # Dwell and take measurement
                    time.sleep(dwell_time)
                    measurement = self.instruments.take_measurement()

                    if measurement:
                        amplitude, phase, _, _ = measurement
                        self.scan_data[j, i] = amplitude   # Amplitude for heatmap display
                        self.phase_data[j, i] = phase      # Phase stored separately
                    else:
                        self.scan_data[j, i] = 0.0
                        self.phase_data[j, i] = 0.0

                    current_point += 1
                    progress = (current_point / total_points) * 100

                    # Update UI from main thread
                    self.parent.after(0, lambda p=progress, cp=current_point, tp=total_points:
                                      self._update_progress(p, f"{cp}/{tp} points"))

                    # Periodically update heatmap
                    if current_point % 10 == 0:
                        self.parent.after(0, self._update_heatmap)

            # Return to origin if requested
            if self.returnToOrigin.get() and self.scan_running:
                hexapod.translate(np.array([-current_x, -current_y, 0.0]))
                while not hexapod.ready_for_commands:
                    time.sleep(0.05)

            # Final update
            self.parent.after(0, self._update_heatmap)
            self.parent.after(0, lambda: self._scan_complete())

        except Exception as e:
            self.parent.after(0, lambda: self.progressText.set(f"Error: {e}"))
            self.parent.after(0, lambda: self._scan_complete())

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
            im = self.ax.imshow(self.scan_data, extent=extent, origin='lower',
                               aspect='auto', cmap='hot')
            self.ax.set_xlabel('X Position (mm)')
            self.ax.set_ylabel('Y Position (mm)')
            self.ax.set_title('LIA Amplitude Heatmap')

        self.canvas_plot.draw()

    def _scan_complete(self):
        """Called when scan is complete."""
        self.scan_running = False
        self.startScanButton['state'] = 'normal'
        self.stopScanButton['state'] = 'disabled'
        self.detectFiducialButton['state'] = 'normal'
        self.saveDataButton['state'] = 'normal'
        self.progressText.set("Scan complete")

    def stop_raster_scan(self):
        """Stop the raster scan."""
        self.scan_running = False
        self.progressText.set("Stopping scan...")

        # Stop the hexapod
        hexapod = self.get_hexapod()
        if hexapod:
            hexapod.stop()

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
            data_max = np.max(self.scan_data)
            if data_max == 0:
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
        """Save scan data to a CSV file including both amplitude and phase."""
        if self.scan_data is None:
            self.progressText.set("No data to save")
            return

        file_path = tk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Scan Data"
        )

        if file_path:
            try:
                # Create a comprehensive DataFrame with all measurement data
                # Format: X_Position, Y_Position, Amplitude, Phase
                rows = []
                for j, y in enumerate(self.y_positions):
                    for i, x in enumerate(self.x_positions):
                        rows.append({
                            'X_Position': x,
                            'Y_Position': y,
                            'Amplitude': self.scan_data[j, i],
                            'Phase': self.phase_data[j, i] if self.phase_data is not None else 0.0
                        })

                df = pd.DataFrame(rows)
                df.to_csv(file_path, index=False)

                # Also save fiducial results if available
                if self.fiducial_centers:
                    results_path = file_path.replace('.csv', '_fiducial_results.txt')
                    with open(results_path, 'w') as f:
                        f.write("Fiducial Detection Results\n")
                        f.write("=" * 30 + "\n\n")
                        for i, (x, y) in enumerate(self.fiducial_centers):
                            f.write(f"Square {i+1}: X={x:.3f} mm, Y={y:.3f} mm\n")
                        if self.sample_position:
                            f.write(f"\nCorner Position: X={self.sample_position[0]:.3f} mm, Y={self.sample_position[1]:.3f} mm\n")
                        if self.sample_angle is not None:
                            f.write(f"Sample Angle: {self.sample_angle:.2f} degrees\n")

                self.progressText.set(f"Data saved to {os.path.basename(file_path)}")

            except Exception as e:
                self.progressText.set(f"Error saving: {e}")
