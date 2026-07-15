"""绘制单面板 Figure 2：策略携带状态对应的动作错误类型。"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

# 只生成静态投稿图，避免依赖本地图形界面。
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from plot_style import COLORS, apply_style, save_figure, soften_axis


PAPER_DIR = Path(__file__).resolve().parents[1]
SOURCE_FILE = PAPER_DIR / "source_data" / "figure2_policy_error_matrix_deepseek.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


STATE_LABELS = {
    "Preserved": "Preserved\n(control)",
    "Absent": "Absent",
    "Weakened": "Weakened",
    "Misbound": "Misbound",
    "Over-included": "Over-included",
}


OUTCOMES = (
    ("Correct", "correct", "correct"),
    ("Unsafe\nallow", "unsafe_allow", "unsafe"),
    ("Under-blocked\nconfirmation", "under_blocked_confirmation", "under_blocked"),
    ("False\nrefusal", "false_refusal", "refusal"),
)


def read_rows() -> list[dict[str, int | str]]:
    """读取经过聚合的五行 source data，避免图件脚本接触原始 episode。"""

    with SOURCE_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = []
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "policy_state": row["policy_state"],
                    **{key: int(row[key]) for key in row if key != "policy_state"},
                }
            )
    return rows


def draw() -> None:
    """使用气泡矩阵突出“策略状态到错误类型”的直接对应关系。"""

    apply_style()
    rows = read_rows()
    y_positions = np.arange(len(rows))
    fig, axis = plt.subplots(figsize=(7.2, 3.55))

    for x_position, (label, field, color_key) in enumerate(OUTCOMES):
        for y_position, row in enumerate(rows):
            share = float(row[field]) / float(row["episodes"])
            if share == 0:
                continue
            # 面积而非半径与比例线性对应，避免中等比例被视觉夸大。
            size = 3800 * share
            axis.scatter(
                x_position,
                y_position,
                s=size,
                color=COLORS[color_key],
                edgecolor="white",
                linewidth=1.1,
                zorder=3,
            )
            if share >= 0.10:
                text_color = "white" if color_key in {"correct", "unsafe"} else COLORS["ink"]
                axis.text(
                    x_position,
                    y_position,
                    f"{share:.0%}",
                    ha="center",
                    va="center",
                    fontsize=7.0,
                    fontweight="semibold",
                    color=text_color,
                    zorder=4,
                )

    axis.set_xticks(range(len(OUTCOMES)), [label for label, _, _ in OUTCOMES])
    axis.xaxis.tick_top()
    for tick, (_, _, color_key) in zip(axis.get_xticklabels(), OUTCOMES):
        tick.set_color(COLORS[color_key])
        tick.set_fontweight("semibold")
    axis.set_yticks(y_positions, [STATE_LABELS[str(row["policy_state"])] for row in rows])
    axis.invert_yaxis()
    axis.set_xlim(-0.55, len(OUTCOMES) - 0.45)
    axis.set_ylim(len(rows) - 0.45, -0.65)
    axis.set_ylabel("Policy-carriage state")
    axis.set_xlabel("")
    axis.grid(color=COLORS["neutral_light"], linewidth=0.65, zorder=0)
    soften_axis(axis)
    axis.spines["left"].set_visible(False)
    axis.spines["bottom"].set_visible(False)
    axis.spines["top"].set_visible(False)
    axis.tick_params(axis="y", length=0)
    axis.tick_params(axis="x", length=0, pad=8)

    axis.text(
        0.0,
        1.20,
        "Policy-carriage failures produce distinct action-error signatures",
        transform=axis.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.6,
        fontweight="semibold",
        color=COLORS["ink"],
    )
    axis.text(
        1.0,
        1.20,
        "DeepSeek | n = 60 per state",
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.5,
        color=COLORS["neutral"],
    )
    fig.subplots_adjust(left=0.18, right=0.985, bottom=0.12, top=0.78)
    save_figure(fig, OUTPUT_DIR, "fig2_policy_error_matrix_preview")


if __name__ == "__main__":
    draw()
