"""按简洁分组柱状风格绘制 Figure 2 的策略状态错误率预览。"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

# 批量出图固定使用无界面后端，保证 Windows 和服务器环境可复现。
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from plot_style import COLORS, apply_style, save_figure


PAPER_DIR = Path(__file__).resolve().parents[1]
SOURCE_FILE = PAPER_DIR / "source_data" / "figure2_policy_error_matrix_deepseek.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


STATES = ("Preserved", "Absent", "Weakened", "Misbound", "Over-included")
ERRORS = (
    ("Unsafe allow", "unsafe_allow", "unsafe"),
    ("Under-blocked confirmation", "under_blocked_confirmation", "under_blocked"),
    ("False refusal", "false_refusal", "refusal"),
)


def read_rows() -> dict[str, dict[str, int]]:
    """读取五个策略状态的聚合计数，图件不访问原始 episode。"""

    with SOURCE_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            row["policy_state"]: {
                key: int(value) for key, value in row.items() if key != "policy_state"
            }
            for row in csv.DictReader(handle)
        }


def draw() -> None:
    """仅展示错误率，使状态到错误类型的映射成为唯一视觉结论。"""

    apply_style()
    rows = read_rows()
    positions = np.arange(len(STATES))
    width = 0.19
    offsets = (-width, 0.0, width)

    fig, axis = plt.subplots(figsize=(7.2, 3.45))
    for offset, (label, field, color_key) in zip(offsets, ERRORS):
        rates = np.asarray(
            [100.0 * rows[state][field] / rows[state]["episodes"] for state in STATES]
        )
        bars = axis.bar(
            positions + offset,
            rates,
            width=width,
            color=COLORS[color_key],
            edgecolor=COLORS[color_key],
            linewidth=0.7,
            label=label,
            zorder=3,
        )
        # 仅为非零柱标数，避免控制组的三个零值制造视觉噪声。
        for bar, rate in zip(bars, rates):
            if rate > 0:
                axis.text(
                    bar.get_x() + bar.get_width() / 2,
                    rate + 2.0,
                    f"{rate:.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=7.0,
                    color=COLORS["ink"],
                )

    axis.set_xticks(
        positions,
        ["Preserved\n(control)", "Absent", "Weakened", "Misbound", "Over-included"],
    )
    axis.set_ylim(0, 112)
    axis.set_yticks(np.arange(0, 101, 20))
    axis.set_ylabel("Action-error rate (%)")

    # 仿照参考图保留细外框与上侧刻度，但不用网格干扰柱高比较。
    for spine in axis.spines.values():
        spine.set_visible(True)
        spine.set_color(COLORS["ink"])
        spine.set_linewidth(0.75)
    axis.tick_params(
        axis="both",
        direction="in",
        top=True,
        right=True,
        labeltop=False,
        labelright=False,
        length=4.0,
        color=COLORS["neutral"],
    )
    axis.tick_params(axis="x", pad=10)
    axis.legend(
        ncol=3,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.05),
        frameon=False,
        handlelength=1.0,
        handletextpad=0.45,
        columnspacing=2.0,
    )
    axis.text(
        1.0,
        1.19,
        "DeepSeek | carried policy | n = 60 per state",
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.5,
        color=COLORS["neutral"],
    )
    fig.subplots_adjust(left=0.12, right=0.985, bottom=0.21, top=0.82)
    save_figure(fig, OUTPUT_DIR, "fig2_error_bars_preview")


if __name__ == "__main__":
    draw()
