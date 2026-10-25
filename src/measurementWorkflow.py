import datetime
import os
import queue
import time

import numpy as np


def create_measurement_directory(
    base_path,
    sample_name,
    beam_offset,
    beam_angle,
    timestamp=None,
):
    """Create and return the standard sample/date and measurement directories."""
    timestamp = timestamp or datetime.datetime.now()
    if sample_name == "NONE":
        sample_directory = base_path
    else:
        sample_directory = os.path.join(
            base_path,
            f"{sample_name}Date_{timestamp.strftime('%b-%d-%Y')}",
        )
    measurement_directory = os.path.join(
        sample_directory,
        (
            f"Measurement_{timestamp.strftime('%H-%M%p')}"
            f"_BO{beam_offset}um_Angle{beam_angle}deg"
        ),
    )
    os.makedirs(measurement_directory, exist_ok=True)
    return measurement_directory


def coordinate_directory(measurement_directory, x_position, y_position):
    path = os.path.join(
        measurement_directory,
        f"x_{round(float(x_position), 3)}_y_{round(float(y_position), 3)}",
    )
    os.makedirs(path, exist_ok=True)
    return path


def save_angle_sweep(measurement_directory, x_position, y_position, angle, data):
    """Persist one sweep using the same coordinate and angle naming as automation."""
    directory = coordinate_directory(measurement_directory, x_position, y_position)
    path = os.path.join(directory, f"{round(float(angle), 1)}_degrees.csv")
    data.to_csv(path, index=False)
    return path


def generate_centered_angles(degrees_of_sweep, step_count):
    """Return physical Rz offsets centered on the starting orientation."""
    if not np.isfinite(degrees_of_sweep):
        raise ValueError("Degrees of sweep must be finite")
    if step_count < 1:
        raise ValueError("Angular step count must be at least 1")
    if degrees_of_sweep < 0:
        raise ValueError("Degrees of sweep must not be negative")
    if step_count == 1:
        return np.array([0.0])
    return np.linspace(-degrees_of_sweep / 2, degrees_of_sweep / 2, step_count)


def publish_latest(target_queue, data):
    """Replace stale display data with the latest measurement frame."""
    while not target_queue.empty():
        try:
            target_queue.get_nowait()
        except queue.Empty:
            break
    target_queue.put_nowait(data.copy())


def move_and_wait(hexapod, command, cancel_event=None, allow_cancel=True, timeout=120.0):
    """Submit one motion command and wait until the controller is ready again."""
    started = time.monotonic()
    while not hexapod.ready_for_commands:
        if allow_cancel and cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Workflow cancelled")
        if time.monotonic() - started > timeout:
            raise TimeoutError("Timed out waiting for hexapod readiness")
        time.sleep(0.05)

    if allow_cancel and cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("Workflow cancelled")
    result = command()
    if result != "Success.":
        raise RuntimeError(f"Hexapod move failed: {result}")

    started = time.monotonic()
    while not hexapod.ready_for_commands:
        if time.monotonic() - started > timeout:
            raise TimeoutError("Timed out waiting for hexapod movement")
        time.sleep(0.05)


def run_angle_sweeps(
    hexapod,
    instruments,
    settings,
    angles,
    convergence_check=False,
    cancel_event=None,
    on_sweep=None,
    on_data=None,
):
    """Measure centered angles around the calibrated laser position and restore pose."""
    frames = []
    current_angle = 0.0
    workflow_error = None
    try:
        for angle_index, angle in enumerate(angles):
            if cancel_event is not None and cancel_event.is_set():
                break

            angle = float(angle)
            angle_delta = angle - current_angle
            if not np.isclose(angle_delta, 0.0):
                move_and_wait(
                    hexapod,
                    lambda delta=angle_delta: hexapod.rotateAroundLaser(
                        np.array([0.0, 0.0, delta])
                    ),
                    cancel_event=cancel_event,
                )
                current_angle = angle

            sweep = instruments.measure_frequency_sweep(
                settings,
                convergence_check=convergence_check,
                degree=angle,
                cancel_event=cancel_event,
                progress_callback=(
                    (lambda data, _completed, _total: on_data(data))
                    if on_data is not None else None
                ),
            )
            if not sweep.empty:
                frames.append(sweep)
                if on_sweep is not None:
                    on_sweep(angle_index, angle, sweep)
    except Exception as exc:
        workflow_error = exc
    finally:
        if not np.isclose(current_angle, 0.0):
            try:
                move_and_wait(
                    hexapod,
                    lambda: hexapod.rotateAroundLaser(
                        np.array([0.0, 0.0, -current_angle])
                    ),
                    cancel_event=cancel_event,
                    allow_cancel=False,
                )
            except Exception as exc:
                if workflow_error is None:
                    workflow_error = exc
                else:
                    workflow_error = RuntimeError(
                        f"{workflow_error}; orientation restore failed: {exc}"
                    )
    if workflow_error is not None:
        raise workflow_error
    return frames
