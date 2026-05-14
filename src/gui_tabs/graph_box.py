import multiprocessing as mp
import traceback
from io import BytesIO

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from PIL import Image


SUPPORTED_PLOTS = {"Default", "Candlestick"}


def _prepare_data(payload):
    if isinstance(payload, dict):
        data = payload.get("data")
        spacing = payload.get("spacing", "linspace")
        if data is None:
            raise ValueError("Missing dataframe in plot payload")
        return data, spacing

    if isinstance(payload, str):
        data = pd.read_pickle(payload)
        spacing = payload.split("_")[-1].split(".")[0]
        return data, spacing

    raise ValueError(f"Unsupported plot payload type: {type(payload)}")


def _figure_to_image(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    image = Image.open(buf).copy()
    buf.close()
    return image


def _render_default_plot(data, spacing_type):
    fig = plt.figure(figsize=(8, 8))
    ax1 = fig.gca()
    ax2 = ax1.twinx()

    last_measurements = data.groupby("FrequencyIn").last()
    mean_phases = data.groupby("FrequencyIn")["PhaseOut"].mean()

    last_scatter = ax1.scatter(
        last_measurements.index,
        last_measurements["PhaseOut"],
        marker="o",
        s=100,
        c="red",
        alpha=0.75,
    )
    mean_scatter = ax1.scatter(
        mean_phases.index,
        mean_phases,
        marker="o",
        s=100,
        c="blue",
        alpha=0.5,
    )

    ax1.legend(
        [last_scatter, mean_scatter],
        ["Red: Most Recent Phase", "Blue: Average Phase"],
        loc="upper right",
    )
    ax1.set_xlabel("Frequency (Hz)")
    ax1.set_ylabel("Phase (rad)", color="blue")
    ax2.set_ylabel("Diffusivity", color="green")

    if spacing_type == "logspace":
        ax1.set_xscale("log")

    ax1.set_title("Phase and Diffusivity vs Frequency")
    ax1.grid(True)
    ax1.tick_params(axis="y", labelcolor="blue")
    ax2.tick_params(axis="y", labelcolor="green")
    fig.tight_layout()

    return fig


def _render_candlestick_plot(data, spacing_type):
    fig = plt.figure(figsize=(8, 8))
    ax = fig.gca()

    if "Convergence" in data.columns:
        converged_data = data[data["Convergence"] == True]
        if converged_data.empty:
            ax.set_title("No converged points yet")
            ax.set_xlabel("Frequency (Hz)")
            ax.set_ylabel("Phase (rad)")
            ax.grid(True)
            return fig
    else:
        converged_data = data

    grouped = converged_data.groupby("FrequencyIn")["PhaseOut"]

    opens = grouped.first()
    closes = grouped.last()
    highs = grouped.max()
    lows = grouped.min()

    frequencies = opens.index.to_numpy(dtype=float)
    if len(frequencies) == 0:
        ax.set_title("No data available")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Phase (rad)")
        ax.grid(True)
        return fig

    if len(frequencies) > 1:
        widths = np.diff(np.sort(frequencies)) * 0.6
        candle_width = float(np.min(widths))
    else:
        candle_width = max(abs(frequencies[0]) * 0.05, 1.0)

    up_color = "#2ca02c"
    down_color = "#d62728"

    for freq in frequencies:
        open_val = float(opens.loc[freq])
        close_val = float(closes.loc[freq])
        high_val = float(highs.loc[freq])
        low_val = float(lows.loc[freq])

        color = up_color if close_val >= open_val else down_color

        ax.vlines(freq, low_val, high_val, color=color, linewidth=1.5, zorder=1)

        body_bottom = min(open_val, close_val)
        body_height = abs(close_val - open_val)
        if body_height == 0:
            body_height = 1e-9

        rect = plt.Rectangle(
            (freq - candle_width / 2, body_bottom),
            candle_width,
            body_height,
            facecolor=color,
            edgecolor=color,
            alpha=0.7,
            zorder=2,
        )
        ax.add_patch(rect)

    up_proxy = plt.Line2D([0], [0], color=up_color, lw=6)
    down_proxy = plt.Line2D([0], [0], color=down_color, lw=6)
    ax.legend(
        [up_proxy, down_proxy],
        ["Green: Close >= Open", "Red: Close < Open"],
        loc="upper right",
    )

    if spacing_type == "logspace":
        ax.set_xscale("log")

    ax.set_title("Candlestick Phase vs Frequency")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Phase (rad)")
    ax.grid(True)
    fig.tight_layout()

    return fig


def plotting_process(data_queue, plot_queue, plot_code="Default"):
    print("Starting plotting process")
    selected_plot = plot_code if plot_code in SUPPORTED_PLOTS else "Default"

    while True:
        try:
            payload = data_queue.get()
            if payload is None:
                print("Received exit signal")
                break

            data, spacing_type = _prepare_data(payload)
            if selected_plot == "Candlestick":
                fig = _render_candlestick_plot(data, spacing_type)
            else:
                fig = _render_default_plot(data, spacing_type)

            image = _figure_to_image(fig)
            plot_queue.put_nowait(image)
            plt.close(fig)
        except Exception as e:
            print(f"Error in plotting process: {e}")
            print(traceback.format_exc())


class GraphBox:
    def __init__(self, distance, plot_code):
        self.laser_distance = distance
        self.amplitude_data = []
        self.phase_data = []
        self.step_data = []
        self.frequency_data = []
        self.diffusivity_estimates = []

        self.data_queue = mp.Queue()
        self.plot_output = mp.Queue()

        self.plot_process = mp.Process(
            target=plotting_process,
            args=(self.data_queue, self.plot_output, plot_code),
            daemon=True,
        )
        self.plot_process.start()

    def queue_plot_update(self, data, spacing_type):
        self.data_queue.put_nowait({"data": data, "spacing": spacing_type})

    def close_plotting_process(self):
        self.data_queue.put(None)

    @staticmethod
    def clear_graph():
        return

    def update_graph(self, data):
        self.queue_plot_update(data, "linspace")

    def instantaneous_diffusivity(self):
        try:
            delta_frequency = abs(self.frequency_data[-1] - self.frequency_data[-2])
        except IndexError:
            delta_frequency = 1
        delta_x = self.laser_distance * float(np.sqrt(np.pi * delta_frequency))
        try:
            delta_y = self.phase_data[-1] - self.phase_data[-2]
        except IndexError:
            delta_y = 1
        slope = delta_y / delta_x
        print(1 / slope ** 2)
        return (1 / slope ** 2) * 1000000

    def __del__(self):
        if hasattr(self, "data_queue"):
            self.data_queue.put(None)
        if hasattr(self, "plot_process"):
            self.plot_process.join(timeout=1.0)
            if self.plot_process.is_alive():
                self.plot_process.terminate()
