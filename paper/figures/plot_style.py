"""论文绘图公共样式：统一投稿级排版、颜色语义和多格式导出。"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from PIL import Image


# 全文固定采用 Okabe-Ito 相近的色盲友好语义色；方法和错误类型不得跨图改色。
COLORS = {
    "method_no_policy": "#9E9E9E",
    "method_carried": "#CC79A7",
    "method_all_clean": "#0072B2",
    "method_msr_clean": "#009E73",
    "method_all_noisy": "#D55E00",
    "method_msr_noisy": "#E69F00",
    "method_oracle": "#333333",
    "correct": "#0072B2",
    "unsafe": "#D55E00",
    "refusal": "#E69F00",
    "under_blocked": "#CC79A7",
    "wrong_revision": "#A6761D",
    "other_wrong": "#999999",
    "heat_low": "#F2F2F2",
    "heat_mid": "#9ECAE1",
    "heat_high": "#08519C",
    "neutral": "#7F7F7F",
    "neutral_light": "#D9D9D9",
    "ink": "#333333",
    # 兼容既有图件脚本；新脚本应优先使用上方的显式语义名称。
    "ours": "#009E73",
    "ours_soft": "#BFE3D7",
    "baseline": "#0072B2",
    "baseline_soft": "#C6DBEF",
    "violet": "#CC79A7",
    "teal": "#009E73",
    "paper": "#FFFFFF",
}


def apply_style() -> None:
    """设置双栏期刊尺寸下仍清晰的字体、轴线和可编辑矢量文字。"""

    mpl.rcParams.update(
        {
            # 正文、坐标与图例统一使用 Times New Roman，和论文排版保持一致。
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif", "serif"],
            "font.size": 7.4,
            "axes.titlesize": 8.4,
            "axes.titleweight": "semibold",
            "axes.labelsize": 7.5,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
            "legend.fontsize": 6.5,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.25,
            "patch.linewidth": 0.65,
            "xtick.major.width": 0.75,
            "ytick.major.width": 0.75,
            "xtick.major.size": 2.8,
            "ytick.major.size": 2.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "figure.facecolor": COLORS["paper"],
            "savefig.facecolor": COLORS["paper"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def panel_label(ax: plt.Axes, label: str, x: float = -0.09, y: float = 1.20) -> None:
    """添加位置稳定的小写面板标记，保持整篇论文的一致性。"""

    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        fontsize=9.5,
        fontweight="bold",
        color=COLORS["ink"],
        ha="left",
        va="bottom",
    )


def panel_title(ax: plt.Axes, title: str, subtitle: str = "") -> None:
    """用紧凑标题交代每个面板的问题与样本范围。"""

    text = title if not subtitle else f"{title}\n{subtitle}"
    # 图例统一停靠在坐标轴上缘，标题抬高一层，避免二者争夺同一条视觉基线。
    ax.set_title(text, loc="left", pad=25)


def soften_axis(ax: plt.Axes, grid: str | None = None) -> None:
    """弱化辅助元素，让数据和直接标注成为视觉主体。"""

    ax.spines["left"].set_color(COLORS["ink"])
    ax.spines["bottom"].set_color(COLORS["ink"])
    if grid:
        ax.grid(axis=grid, color=COLORS["neutral_light"], linewidth=0.65, zorder=0)
    ax.tick_params(colors=COLORS["ink"])


def label_tag(ax: plt.Axes, text: str, x: float = 0.98, y: float = 1.20) -> None:
    """在标题右侧放置浅色样本量或数据集标签。"""

    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.2,
        color=COLORS["neutral"],
        bbox={"boxstyle": "round,pad=0.22", "facecolor": "#F5F6F8", "edgecolor": "none"},
    )


def save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    """导出可编辑矢量图、审稿预览图和无透明通道的 RGB TIFF。"""

    output_dir.mkdir(parents=True, exist_ok=True)
    common = {"bbox_inches": "tight", "pad_inches": 0.035, "facecolor": "white"}
    fig.savefig(output_dir / f"{stem}.svg", **common)
    fig.savefig(output_dir / f"{stem}.pdf", **common)
    fig.savefig(output_dir / f"{stem}.png", dpi=360, **common)
    tiff_path = output_dir / f"{stem}.tiff"
    fig.savefig(tiff_path, dpi=600, pil_kwargs={"compression": "tiff_lzw"}, **common)
    # 投稿系统通常要求 RGB TIFF；显式转换可避免透明通道触发预检失败。
    with Image.open(tiff_path) as image:
        image.convert("RGB").save(tiff_path, compression="tiff_lzw", dpi=(600, 600))
    plt.close(fig)
