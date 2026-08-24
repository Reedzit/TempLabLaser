import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .centerFinder import CenterFinderError, HexapodCenterFinder, SearchCancelled
from .powerMeterManager import PowerMeterManager


class PowerMeterConnection:
    def __init__(self):
        self.connected = False
        self.power_meter_manager = PowerMeterManager()
        self._read_lock = threading.Lock()

    def connect(self):
        self.connected = self.power_meter_manager.connect()
        return self.connected

    def disconnect(self):
        if self.connected:
            self.power_meter_manager.disconnect()
            self.connected = False

    def read_power(self):
        if not self.connected:
            raise RuntimeError("Power meter not connected.")
        with self._read_lock:
            power = self.power_meter_manager.read_power()
        if power is None:
            raise RuntimeError("Failed to read power from the power meter.")
        return float(power)


class CenterFinderGUI(tk.Toplevel):
    def __init__(self, parent=None, hexapod=None):
        super().__init__(parent)
        self.title("Hexapod Center Finder")
        self.geometry("800x650")

        self.hexapod = hexapod
        self.power_meter = None
        self._plot_running = False
        self._search_running = False
        self._plot_thread = None
        self._search_thread = None
        self._cancel_event = threading.Event()
        self._closing = False
        self._times = []
        self._powers = []
        self._start_time = time.monotonic()

        self.pm_status = tk.StringVar(value="Power meter: disconnected")
        self.hp_status = tk.StringVar()
        self.search_status = tk.StringVar(value="Ready")
        self.result = tk.StringVar(value="Laser position: not found")
        self.dimensions = tk.StringVar(value="Hole axes: not measured")
        self.threshold = tk.StringVar(value="1e-6")
        self.coarse_step_size = tk.StringVar(value="1.0")
        self.step_size = tk.StringVar(value="0.1")
        self.max_travel = tk.StringVar(value="30")
        self.samples = tk.StringVar(value="3")
        self.settle_time = tk.StringVar(value="0.1")

        self._build_ui()
        self._update_hexapod_status()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        connection_frame = ttk.LabelFrame(self, text="Connections", padding=8)
        connection_frame.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.connect_pm_button = ttk.Button(
            connection_frame, text="Connect Power Meter", command=self.connect_power_meter
        )
        self.connect_pm_button.grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ttk.Label(connection_frame, textvariable=self.pm_status).grid(row=0, column=1, sticky=tk.W)
        ttk.Label(connection_frame, textvariable=self.hp_status).grid(row=1, column=1, sticky=tk.W)

        settings = ttk.LabelFrame(self, text="Center Search", padding=8)
        settings.pack(fill=tk.X, padx=8, pady=4)
        fields = (
            ("Sensing threshold (W)", self.threshold),
            ("Rough step size (mm)", self.coarse_step_size),
            ("Fine step size (mm)", self.step_size),
            ("Maximum travel (mm)", self.max_travel),
            ("Samples per point", self.samples),
            ("Settle time (s)", self.settle_time),
        )
        for index, (label, variable) in enumerate(fields):
            ttk.Label(settings, text=label).grid(row=index // 3 * 2, column=index % 3, sticky=tk.W, padx=4)
            ttk.Entry(settings, textvariable=variable, width=18).grid(
                row=index // 3 * 2 + 1, column=index % 3, sticky=tk.W, padx=4, pady=(0, 6)
            )

        controls = ttk.Frame(settings)
        controls.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(4, 0))
        self.start_button = ttk.Button(
            controls, text="Find Center", command=self.start_search, state=tk.DISABLED
        )
        self.start_button.pack(side=tk.LEFT, padx=4)
        self.cancel_button = ttk.Button(
            controls, text="Cancel", command=self.cancel_search, state=tk.DISABLED
        )
        self.cancel_button.pack(side=tk.LEFT, padx=4)
        self.plot_button = ttk.Button(controls, text="Start Plot", command=self.toggle_plotting)
        self.plot_button.pack(side=tk.LEFT, padx=4)

        ttk.Label(settings, textvariable=self.search_status).grid(
            row=5, column=0, columnspan=3, sticky=tk.W, padx=4, pady=(8, 0)
        )
        ttk.Label(settings, textvariable=self.result).grid(
            row=6, column=0, columnspan=3, sticky=tk.W, padx=4
        )
        ttk.Label(settings, textvariable=self.dimensions).grid(
            row=7, column=0, columnspan=3, sticky=tk.W, padx=4
        )

        self.fig = Figure(figsize=(7.5, 3.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Power Meter Readings")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Power (W)")
        (self.line,) = self.ax.plot([], [], lw=1.5)
        self.ax.grid(True, alpha=0.3)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def connect_power_meter(self):
        try:
            power_meter = PowerMeterConnection()
            if not power_meter.connect():
                raise ConnectionError("The VISA instrument could not be opened.")
            self.power_meter = power_meter
            self.pm_status.set("Power meter: connected")
            self.connect_pm_button.configure(state=tk.DISABLED)
            self.start_plotting()
        except Exception as exc:
            self.pm_status.set("Power meter: connection failed")
            messagebox.showerror("Connection Error", f"Power meter connection failed:\n{exc}", parent=self)

    def start_search(self):
        if self._search_running:
            return
        if self.power_meter is None or not self.power_meter.connected:
            messagebox.showwarning("Not Connected", "Connect the power meter first.", parent=self)
            return
        if self.hexapod is None or getattr(self.hexapod, "ssh_API", None) is None:
            messagebox.showwarning(
                "Not Connected", "Connect the hexapod from the Hexapod Automation tab first.", parent=self
            )
            return
        if not getattr(self.hexapod, "ready_for_commands", False):
            messagebox.showwarning("Hexapod Busy", "Wait for the current hexapod command to finish.", parent=self)
            return
        try:
            settings = {
                "threshold": float(self.threshold.get()),
                "coarse_step_size": float(self.coarse_step_size.get()),
                "step_size": float(self.step_size.get()),
                "max_travel": float(self.max_travel.get()),
                "samples": int(self.samples.get()),
                "settle_time": float(self.settle_time.get()),
            }
            if settings["settle_time"] < 0:
                raise ValueError("Settle time cannot be negative.")
        except ValueError as exc:
            messagebox.showerror("Invalid Settings", str(exc), parent=self)
            return

        self.stop_plotting()
        self._cancel_event.clear()
        self._search_running = True
        self.start_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.plot_button.configure(state=tk.DISABLED)
        self.search_status.set("Starting center search")
        self._search_thread = threading.Thread(
            target=self._run_search, args=(settings,), daemon=True
        )
        self._search_thread.start()

    def _run_search(self, settings):
        try:
            finder = HexapodCenterFinder(
                self.hexapod,
                self.power_meter,
                cancel_event=self._cancel_event,
                status_callback=self._post_status,
                sample_callback=self._record_power,
                **settings,
            )
            position = finder.find_center()
            self.after(0, self.result.set, f"Laser position: {position}")
            self.after(
                0,
                self.dimensions.set,
                f"Hole axes: major {finder.major_axis:.3f} mm, "
                f"minor {finder.minor_axis:.3f} mm",
            )
        except SearchCancelled as exc:
            self._post_status(str(exc))
        except (CenterFinderError, TimeoutError, OSError, ValueError) as exc:
            self._post_status(f"Search failed: {exc}")
            if not self._closing:
                self.after(0, self._show_search_error, str(exc))
        except Exception as exc:
            self._post_status(f"Search failed: {exc}")
            if not self._closing:
                self.after(0, self._show_search_error, str(exc))
        finally:
            if not self._closing:
                self.after(0, self._finish_search)

    def cancel_search(self):
        if self._search_running:
            self.search_status.set("Cancelling after the current movement")
            self._cancel_event.set()
            self.cancel_button.configure(state=tk.DISABLED)

    def _finish_search(self):
        self._search_running = False
        self.cancel_button.configure(state=tk.DISABLED)
        self.plot_button.configure(state=tk.NORMAL)

    def _show_search_error(self, message):
        messagebox.showerror("Center Search Failed", message, parent=self)

    def toggle_plotting(self):
        if self._plot_running:
            self.stop_plotting()
        else:
            self.start_plotting()

    def start_plotting(self):
        if self.power_meter is None or not self.power_meter.connected:
            messagebox.showwarning("Not Connected", "Connect the power meter first.", parent=self)
            return
        if self._plot_running or self._search_running:
            return
        self._plot_running = True
        self.plot_button.configure(text="Stop Plot")
        self._plot_thread = threading.Thread(target=self._acquisition_loop, daemon=True)
        self._plot_thread.start()

    def stop_plotting(self):
        self._plot_running = False
        self.plot_button.configure(text="Start Plot")

    def _acquisition_loop(self):
        while self._plot_running and not self._closing:
            try:
                self._record_power(self.power_meter.read_power())
                time.sleep(0.1)
            except Exception as exc:
                self._plot_running = False
                self._post_status(f"Power meter read failed: {exc}")

    def _record_power(self, power):
        self._times.append(time.monotonic() - self._start_time)
        self._powers.append(power)
        if len(self._times) > 600:
            del self._times[:-600]
            del self._powers[:-600]
        if not self._closing:
            self.after(0, self._update_plot)

    def _update_plot(self):
        self.line.set_data(self._times, self._powers)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

    def _post_status(self, message):
        if not self._closing:
            self.after(0, self.search_status.set, message)

    def _update_hexapod_status(self):
        connected = self.hexapod is not None and getattr(self.hexapod, "ssh_API", None) is not None
        ready = connected and getattr(self.hexapod, "ready_for_commands", False)
        status = "ready" if ready else "busy" if connected else "disconnected"
        self.hp_status.set(f"Hexapod: {status}")
        if not self._search_running:
            self.start_button.configure(state=tk.NORMAL if ready else tk.DISABLED)
        if not self._closing:
            self.after(100, self._update_hexapod_status)

    def _on_close(self):
        self._closing = True
        self._plot_running = False
        self._cancel_event.set()
        self._finish_close()

    def _finish_close(self):
        threads = (self._plot_thread, self._search_thread)
        if any(thread is not None and thread.is_alive() for thread in threads):
            self.after(50, self._finish_close)
            return
        if self.power_meter is not None and self.power_meter.connected:
            self.power_meter.disconnect()
        self.destroy()


def launch_center_finder_popup(parent=None, hexapod=None):
    return CenterFinderGUI(parent, hexapod)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    popup = launch_center_finder_popup(root)
    popup.mainloop()
