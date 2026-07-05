"""Privacy-vs-utility tradeoff plot (P5 DoD; the full reporting layer lands in P7)."""

import math
from pathlib import Path

TradeoffPoint = tuple[float, float, str]  # (utility loss, attack success, label)


def plot_tradeoff(points: list[TradeoffPoint], out_path: Path) -> None:
    """Plot attack success against utility loss, one labelled point per arm.

    Non-finite points (e.g. an arm whose release produced no attackable pool)
    are skipped and listed in a footnote so they cannot be mistaken for a
    plotting bug. matplotlib is imported lazily to keep ``import trajguard``
    light.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    finite = sorted(
        (p for p in points if math.isfinite(p[0]) and math.isfinite(p[1])),
        key=lambda p: p[0],
    )
    skipped = [label for x, y, label in points if not (math.isfinite(x) and math.isfinite(y))]

    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    if finite:
        ax.plot([p[0] for p in finite], [p[1] for p in finite], marker="o")
        for x, y, label in finite:
            ax.annotate(label, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.set_xlabel("utility loss (cell JS divergence, bits)")
    ax.set_ylabel("reidentification top-1 accuracy")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Privacy vs utility")
    if skipped:
        fig.text(0.01, 0.01, "not plotted (no result): " + ", ".join(skipped), fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
