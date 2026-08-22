"""Render LLD series as PNG charts (for Telegram photo messages)."""

import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


METRIC_LABELS = {
    "F0": "F0, semitones",
    "Loudness": "Loudness",
    "Jitter": "Jitter",
}


def render_lld_chart(lld: dict, duration_sec: float) -> bytes:
    """Render LLD series (F0/Loudness/Jitter) as a stacked PNG chart.

    Time axis spans duration_sec (same scaling as the web UI).
    None values become gaps in the line.
    """
    metrics = [m for m in ("F0", "Loudness", "Jitter") if lld.get(m)]
    if not metrics:
        raise ValueError("No LLD series to plot")

    n = len(metrics)
    fig, axes = plt.subplots(n, 1, figsize=(10, 2.4 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, key in zip(axes, metrics):
        series = np.array([np.nan if v is None else v for v in lld[key]], dtype=float)
        t = np.linspace(0.0, float(duration_sec), num=len(series))
        ax.plot(t, series, linewidth=1.2)
        ax.set_ylabel(METRIC_LABELS[key], fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.margins(x=0)

    axes[-1].set_xlabel("Time, s", fontsize=9)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return buf.getvalue()
