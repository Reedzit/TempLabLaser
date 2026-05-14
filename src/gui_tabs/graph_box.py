import multiprocessing as mp
import traceback
from io import BytesIO

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from PIL import Image


SUPPORTED_PLOTS = {
    "Default",
    "Candlestick",
    "TrendLive",
    "TrajectoryLive",
    "DualPanelLive",
}


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


def _apply_frequency_scale(ax, spacing_type):
    if spacing_type == "logspace":
        ax.set_xscale("log")


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

    _apply_frequency_scale(ax1, spacing_type)

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

    candle_line = "#1f3a5f"
    candle_fill = "#7ea3cc"

    for freq in frequencies:
        open_val = float(opens.loc[freq])
        close_val = float(closes.loc[freq])
        high_val = float(highs.loc[freq])
        low_val = float(lows.loc[freq])

        ax.vlines(freq, low_val, high_val, color=candle_line, linewidth=1.5, zorder=1)

        body_bottom = min(open_val, close_val)
        body_height = abs(close_val - open_val)
        if body_height == 0:
            body_height = 1e-9

        rect = plt.Rectangle(
            (freq - candle_width / 2, body_bottom),
            candle_width,
            body_height,
            facecolor=candle_fill,
            edgecolor=candle_line,
            alpha=0.7,
            zorder=2,
        )
        ax.add_patch(rect)

    wick_proxy = plt.Line2D([0], [0], color=candle_line, lw=2)
    body_proxy = plt.Rectangle((0, 0), 1, 1, facecolor=candle_fill, edgecolor=candle_line, alpha=0.7)
    ax.legend([wick_proxy, body_proxy], ["Wick: Low to High", "Body: Open to Close"], loc="upper right")

    _apply_frequency_scale(ax, spacing_type)

    ax.set_title("Candlestick Phase vs Frequency")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Phase (rad)")
    ax.grid(True)
    fig.tight_layout()

    return fig


def _render_trend_live_plot(data, spacing_type):
    fig = plt.figure(figsize=(8, 8))
    ax = fig.gca()

    grouped = data.groupby("FrequencyIn")["PhaseOut"]
    median_phase = grouped.median().sort_index()
    q1 = grouped.quantile(0.25).reindex(median_phase.index)
    q3 = grouped.quantile(0.75).reindex(median_phase.index)

    ax.plot(median_phase.index, median_phase.values, color="#1f77b4", linewidth=2, label="Median Phase")
    ax.fill_between(median_phase.index, q1.values, q3.values, color="#1f77b4", alpha=0.2, label="IQR (25-75%)")

    latest = data.iloc[-1]
    ax.scatter(
        [latest["FrequencyIn"]],
        [latest["PhaseOut"]],
        color="#d62728",
        s=80,
        marker="o",
        label="Latest Measurement",
        zorder=3,
    )

    _apply_frequency_scale(ax, spacing_type)
    ax.set_title("Live Phase Trend with IQR Band")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Phase (rad)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    return fig


def _render_trajectory_live_plot(data, spacing_type):
    fig = plt.figure(figsize=(8, 8))
    ax = fig.gca()

    points = data[["FrequencyIn", "PhaseOut"]].to_numpy()
    count = len(points)
    if count == 1:
        ax.scatter(points[:, 0], points[:, 1], color="#ff7f0e", s=90)
    else:
        for idx in range(count - 1):
            alpha = 0.15 + 0.75 * ((idx + 1) / (count - 1))
            ax.plot(
                points[idx:idx + 2, 0],
                points[idx:idx + 2, 1],
                color="#ff7f0e",
                linewidth=2,
                alpha=alpha,
            )
        ax.scatter(points[:-1, 0], points[:-1, 1], color="#ffbe7d", s=20, alpha=0.35, label="Older Measurements")
        ax.scatter(points[-1, 0], points[-1, 1], color="#d62728", s=90, label="Latest Measurement", zorder=3)

    _apply_frequency_scale(ax, spacing_type)
    ax.set_title("Live Measurement Trajectory")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Phase (rad)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    return fig


def _render_dual_panel_live_plot(data, spacing_type):
    fig, (ax_top, ax_bottom) = plt.subplots(2, 1, figsize=(8, 9), sharex=False)

    grouped = data.groupby("FrequencyIn")["PhaseOut"]
    mean_phase = grouped.mean().sort_index()
    std_phase = grouped.std().fillna(0).reindex(mean_phase.index)

    ax_top.plot(mean_phase.index, mean_phase.values, color="#1f77b4", linewidth=2, label="Mean Phase")
    ax_top.fill_between(
        mean_phase.index,
        (mean_phase - std_phase).values,
        (mean_phase + std_phase).values,
        color="#1f77b4",
        alpha=0.2,
        label="±1 Std",
    )
    _apply_frequency_scale(ax_top, spacing_type)
    ax_top.set_title("Frequency Response")
    ax_top.set_xlabel("Frequency (Hz)")
    ax_top.set_ylabel("Phase (rad)")
    ax_top.grid(True, alpha=0.3)
    ax_top.legend(loc="upper right")

    recent_count = min(40, len(data))
    recent_data = data.tail(recent_count).copy()
    recent_data["Time"] = pd.to_datetime(recent_data["Time"], errors="coerce")
    if recent_data["Time"].notna().all():
        x_vals = recent_data["Time"]
        ax_bottom.set_xlabel("Time")
    else:
        x_vals = np.arange(recent_count)
        ax_bottom.set_xlabel("Recent Sample Index")

    ax_bottom.plot(x_vals, recent_data["PhaseOut"], color="#ff7f0e", linewidth=1.8, label="Recent Phase")
    ax_bottom.scatter(x_vals.iloc[-1] if hasattr(x_vals, "iloc") else x_vals[-1], recent_data["PhaseOut"].iloc[-1],
                      color="#d62728", s=70, label="Latest")
    ax_bottom.set_title("Recent Drift / Settling")
    ax_bottom.set_ylabel("Phase (rad)")
    ax_bottom.grid(True, alpha=0.3)
    ax_bottom.legend(loc="upper right")

    fig.tight_layout()
    return fig


PLOT_RENDERERS = {
    "Default": _render_default_plot,
    "Candlestick": _render_candlestick_plot,
    "TrendLive": _render_trend_live_plot,
    "TrajectoryLive": _render_trajectory_live_plot,
    "DualPanelLive": _render_dual_panel_live_plot,
}


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
            renderer = PLOT_RENDERERS.get(selected_plot, _render_default_plot)
            fig = renderer(data, spacing_type)

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
