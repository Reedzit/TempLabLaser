def format_duration(seconds):
    """Format an estimate as seconds or hours/minutes for display."""
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def frequency_sweep_seconds(step_count, time_per_step):
    return max(0, int(step_count)) * max(0, float(time_per_step))


def angle_workflow_seconds(angle_count, sweep_seconds):
    return max(0, int(angle_count)) * (2.0 + max(0, float(sweep_seconds)))


def heatmap_seconds(cell_count, rotation_seconds):
    return max(0, int(cell_count)) * (2.0 + max(0, float(rotation_seconds)))
