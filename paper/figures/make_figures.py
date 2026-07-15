"""从已完成实验的 source data 生成统一视觉语言的投稿级论文图件。"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

# 批处理出图固定使用无界面后端，避免隔离环境依赖桌面 Tk 组件。
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from plot_style import COLORS, apply_style, label_tag, panel_label, panel_title, save_figure, soften_axis


PAPER_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = PAPER_DIR / "source_data"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def read_csv(name: str) -> list[dict[str, str]]:
    """读取小型、可版本控制的 source-data CSV，不依赖 pandas。"""

    with (SOURCE_DIR / name).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def value(row: dict[str, str], key: str) -> float:
    """把表格中的数值字段转换为浮点数，空值保留为 NaN。"""

    raw = row.get(key, "")
    return float(raw) if raw not in {"", "NA", None} else math.nan


def ordered(rows: list[dict[str, str]], names: list[str], field: str = "method") -> list[dict[str, str]]:
    """以论文叙事顺序排列方法，避免 CSV 写入顺序影响图形阅读顺序。"""

    by_name = {row[field]: row for row in rows}
    return [by_name[name] for name in names if name in by_name]


def method_color(name: str) -> str:
    """保持跨图方法颜色恒定：V-MSR/MSR 为蓝色，对照为蓝灰或中性灰。"""

    if "V-MSR" in name or name.startswith("MSR"):
        return COLORS["ours"]
    if "diagnostic" in name:
        return COLORS["violet"]
    if "Carried" in name or "Hybrid" in name:
        return COLORS["teal"]
    if "No policy" in name:
        return COLORS["neutral"]
    return COLORS["baseline"]


def box(ax: plt.Axes, x: float, y: float, width: float, height: float, title: str, body: str, color: str) -> None:
    """绘制简洁流程框；复杂解释留给双语图注而不是塞进图内。"""

    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.010,rounding_size=0.025",
        facecolor="#FFFFFF",
        edgecolor=color,
        linewidth=1.1,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height * 0.64, title, ha="center", va="center", fontsize=7.4, fontweight="semibold", color=COLORS["ink"])
    ax.text(x + width / 2, y + height * 0.32, body, ha="center", va="center", fontsize=6.2, color=COLORS["neutral"])


def arrow(ax: plt.Axes, x1: float, y1: float, x2: float, y2: float) -> None:
    """统一流程箭头的线宽和箭头比例。"""

    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=0.9,
            color=COLORS["neutral"],
        )
    )


def outcome_parts(row: dict[str, str], correct_key: str = "accuracy", unsafe_key: str = "violation", refusal_key: str = "false_refusal") -> tuple[float, float, float, float]:
    """把动作结果拆成正确、违规执行、误拒和其余错误四类互斥视觉成分。"""

    correct = value(row, correct_key)
    unsafe = value(row, unsafe_key)
    refusal = value(row, refusal_key)
    other = max(0.0, 1.0 - correct - unsafe - refusal)
    return correct, unsafe, refusal, other


def draw_outcome_signature(ax: plt.Axes, rows: list[dict[str, str]], *, label_field: str, title: str, tag: str) -> None:
    """用同一组语义颜色展示正确、安全违规、误拒和其他错误。"""

    labels = [row[label_field] for row in rows]
    y = np.arange(len(rows))
    components = [
        ("Correct", COLORS["correct"], []),
        ("Unsafe execution", COLORS["unsafe"], []),
        ("False refusal", COLORS["refusal"], []),
        ("Other error", COLORS["neutral_light"], []),
    ]
    for row in rows:
        for index, component in enumerate(outcome_parts(row)):
            components[index][2].append(component)

    left = np.zeros(len(rows))
    for label, color, widths in components:
        ax.barh(y, widths, left=left, height=0.58, color=color, edgecolor="white", linewidth=0.8, label=label, zorder=3)
        left += np.asarray(widths)

    for row_index, row in enumerate(rows):
        left_edge = 0.0
        for component, color in zip(outcome_parts(row), [COLORS["correct"], COLORS["unsafe"], COLORS["refusal"], COLORS["neutral_light"]]):
            if component >= 0.12:
                text_color = "white" if color in {COLORS["correct"], COLORS["unsafe"]} else COLORS["ink"]
                ax.text(left_edge + component / 2, row_index, f"{component:.2f}", ha="center", va="center", fontsize=6.2, color=text_color)
            left_edge += component

    ax.set_yticks(y, labels)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Episode share (%)")
    ax.invert_yaxis()
    soften_axis(ax, "x")
    panel_title(ax, title)
    label_tag(ax, tag)
    ax.legend(ncol=4, loc="lower left", bbox_to_anchor=(0.0, 1.00), handlelength=1.4, columnspacing=1.15)


def figure_1_overview() -> None:
    """图 1：用紧凑示意图建立 benchmark、方法和评估资产的共同视觉词汇。"""

    fig = plt.figure(figsize=(7.2, 4.75))
    grid = fig.add_gridspec(3, 1, height_ratios=[1.0, 1.15, 0.72], hspace=0.30)

    ax = fig.add_subplot(grid[0])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    panel_label(ax, "a", -0.02, 1.00)
    ax.text(0.02, 0.92, "Policy carriage benchmark", fontsize=8.5, fontweight="semibold", color=COLORS["ink"])
    box(ax, 0.02, 0.26, 0.18, 0.43, "Long context", "memory, history,\npolicy documents", COLORS["baseline"])
    box(ax, 0.32, 0.20, 0.27, 0.55, "Carried policy", "meaning, scope\nand object binding", COLORS["teal"])
    box(ax, 0.71, 0.26, 0.12, 0.43, "Action", "tool call", COLORS["baseline"])
    box(ax, 0.87, 0.20, 0.11, 0.55, "Outcome", "correct\nunsafe\nrefusal", COLORS["unsafe"])
    arrow(ax, 0.20, 0.48, 0.32, 0.48)
    arrow(ax, 0.59, 0.48, 0.71, 0.48)
    arrow(ax, 0.83, 0.48, 0.87, 0.48)
    chips = [
        ("preserved", COLORS["correct"]),
        ("absent", COLORS["unsafe"]),
        ("weakened", COLORS["refusal"]),
        ("misbound", COLORS["violet"]),
        ("over-included", COLORS["teal"]),
    ]
    # 状态名称刻意拉开间距，避免长标签 over-included 与相邻标签粘连。
    chip_positions = [0.19, 0.33, 0.47, 0.61, 0.78]
    for (label, color), x in zip(chips, chip_positions):
        ax.text(x, 0.08, label, ha="center", va="center", fontsize=5.1, color=color, fontweight="semibold")

    ax = fig.add_subplot(grid[1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    panel_label(ax, "b", -0.02, 1.00)
    ax.text(0.02, 0.92, "Verification-Guided Minimal Sufficient Policy Retrieval", fontsize=8.5, fontweight="semibold", color=COLORS["ink"])
    stages = [
        ("Action facts", "visible action\nevidence"),
        ("Candidate frontier", "BM25 + same-tool\nclosure"),
        ("Verify", "entailed | contradicted\n| unknown"),
        ("Resolve + prune", "provenance +\nminimal proof"),
        ("Certificate", "policy set +\ndecision floor"),
    ]
    colors = [COLORS["baseline"], COLORS["baseline"], COLORS["teal"], COLORS["ours"], COLORS["ours"]]
    starts = [0.02, 0.215, 0.41, 0.605, 0.80]
    for index, ((title, body), color, x) in enumerate(zip(stages, colors, starts)):
        box(ax, x, 0.26, 0.16, 0.43, title, body, color)
        if index < len(stages) - 1:
            arrow(ax, x + 0.16, 0.475, starts[index + 1], 0.475)
    ax.text(0.80, 0.08, "Context informs the LLM; Guard never lowers safety.", fontsize=6.1, color=COLORS["ours"])

    ax = fig.add_subplot(grid[2])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    panel_label(ax, "c", -0.02, 1.00)
    ax.text(0.02, 0.89, "Evaluation assets", fontsize=8.5, fontweight="semibold", color=COLORS["ink"])
    tracks = [
        ("300", "main benchmark", "6 domains"),
        ("90", "policy-carriage", "main evidence"),
        ("72", "verification", "challenge set"),
        ("36", "adversarial", "mechanism probe"),
        ("40", "compression", "sanity check"),
    ]
    for index, (count, title, detail) in enumerate(tracks):
        x = 0.02 + index * 0.196
        ax.add_patch(FancyBboxPatch((x, 0.18), 0.17, 0.50, boxstyle="round,pad=0.008,rounding_size=0.022", facecolor="#F7F8FA", edgecolor=COLORS["neutral_light"], linewidth=0.7))
        ax.text(x + 0.085, 0.51, count, ha="center", va="center", fontsize=11, fontweight="bold", color=COLORS["ours"])
        ax.text(x + 0.085, 0.34, title, ha="center", va="center", fontsize=6.2, color=COLORS["ink"])
        ax.text(x + 0.085, 0.24, detail, ha="center", va="center", fontsize=5.7, color=COLORS["neutral"])
    save_figure(fig, OUTPUT_DIR, "fig1_overview")


def figure_2_main_results() -> None:
    """图 2：突出 policy state 的差异化错误，并将成本与选择质量放到辅助面板。"""

    states = ordered(read_csv("carried_failure_by_state_90.csv"), ["Preserved", "Absent", "Weakened", "Misbound", "Over-included"], "policy_state")
    methods = read_csv("main_results_90.csv")
    method_order = ["No policy", "Carried policy", "All policy (clean)", "All policy (noisy)", "MSR (clean)", "MSR (noisy)", "Policy-list diagnostic"]
    methods = ordered(methods, method_order)

    fig = plt.figure(figsize=(7.2, 5.05))
    grid = fig.add_gridspec(2, 2, height_ratios=[1.20, 1.0], hspace=0.54, wspace=0.40)

    ax = fig.add_subplot(grid[0, :])
    draw_outcome_signature(ax, states, label_field="policy_state", title="Policy-carriage failures map to distinct action-error signatures", tag="English main run · n = 18 per state")
    panel_label(ax, "a", -0.055, 1.20)

    ax = fig.add_subplot(grid[1, 0])
    for row in methods:
        name = row["method"]
        x = value(row, "policy_tokens")
        y = value(row, "accuracy")
        ax.scatter(x, y, s=42, color=method_color(name), edgecolor="white", linewidth=0.8, zorder=4)
    offsets = {
        "No policy": (5, -13),
        "Carried policy": (5, 8),
        "All policy (clean)": (-68, 8),
        "All policy (noisy)": (-68, -13),
        "MSR (clean)": (5, 9),
        "MSR (noisy)": (5, -13),
        "Policy-list diagnostic": (-82, 7),
    }
    for row in methods:
        name = row["method"]
        ax.annotate(name.replace(" policy", ""), (value(row, "policy_tokens"), value(row, "accuracy")), xytext=offsets[name], textcoords="offset points", fontsize=5.8, color=method_color(name))
    ax.set_xscale("symlog", linthresh=1)
    ax.set_xlim(-0.1, 1400)
    ax.set_xticks([0, 1, 10, 100, 1000], ["0", "1", "10", "100", "1k"])
    ax.set_ylim(0.34, 1.04)
    ax.set_yticks([0.4, 0.6, 0.8, 1.0])
    ax.axhline(1.0, color=COLORS["neutral_light"], linewidth=0.7, zorder=0)
    ax.set_xlabel("Policy tokens per episode (symlog)")
    ax.set_ylabel("Decision accuracy")
    soften_axis(ax, "x")
    panel_title(ax, "Quality-cost frontier")
    label_tag(ax, "n = 90")
    panel_label(ax, "b")

    ax = fig.add_subplot(grid[1, 1])
    y = np.arange(len(methods))
    coverage = [value(row, "coverage") for row in methods]
    irrelevant = [value(row, "irrelevant_rate") for row in methods]
    for yi, cov, irr in zip(y, coverage, irrelevant):
        ax.plot([irr, cov], [yi, yi], color=COLORS["neutral_light"], linewidth=2.0, zorder=1)
    ax.scatter(coverage, y, color=COLORS["ours"], s=30, zorder=3, label="Required-policy coverage")
    ax.scatter(irrelevant, y, color=COLORS["refusal"], marker="D", s=25, zorder=3, label="Irrelevant-policy rate")
    ax.set_yticks(y, [row["method"].replace(" policy", "") for row in methods])
    ax.set_xlim(-0.04, 1.04)
    ax.set_xticks([0, 0.5, 1.0])
    ax.invert_yaxis()
    ax.set_xlabel("Rate")
    soften_axis(ax, "x")
    panel_title(ax, "Selection quality")
    label_tag(ax, "same 90 episodes")
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.00), ncol=1, handletextpad=0.4)
    panel_label(ax, "c")
    save_figure(fig, OUTPUT_DIR, "fig2_policy_carriage_main")


def figure_3_adversarial() -> None:
    """图 3：让 adversarial 结果以动作级 outcome 为主、检索机制为辅。"""

    retrieval = read_csv("vmsr_adversarial_retrieval_36.csv")
    llm_rows = ordered(
        read_csv("vmsr_adversarial_llm_36.csv"),
        ["All policy", "MSR", "Policy-list diagnostic", "V-MSR-Text Context", "V-MSR-Text Guard"],
    )
    errors = read_csv("vmsr_adversarial_errors_36.csv")
    fig = plt.figure(figsize=(7.2, 5.35))
    grid = fig.add_gridspec(2, 3, height_ratios=[1.10, 1.0], width_ratios=[1.18, 1.0, 1.03], hspace=0.60, wspace=0.43)

    ax = fig.add_subplot(grid[0, :])
    draw_outcome_signature(ax, llm_rows, label_field="method", title="Verification removes action-level errors under adversarial policy noise", tag="DeepSeek adversarial probe · n = 36")
    panel_label(ax, "a", -0.04, 1.20)

    ax = fig.add_subplot(grid[1, 0])
    for row in retrieval:
        name = row["method"]
        size = 28 + 130 * value(row, "irrelevant_rate")
        ax.scatter(value(row, "policy_tokens"), value(row, "coverage"), s=size, color=method_color(name), alpha=0.90, edgecolor="white", linewidth=0.65, zorder=3)
    annotation_rows = {
        "All policy": (-37, -13),
        "BM25 top-3": (-20, -16),
        "MSR": (-8, 9),
        "V-MSR-Text": (4, -16),
    }
    for row in retrieval:
        name = row["method"]
        if name in annotation_rows:
            ax.annotate(name, (value(row, "policy_tokens"), value(row, "coverage")), xytext=annotation_rows[name], textcoords="offset points", fontsize=5.7, color=method_color(name))
    ax.set_xlim(0, 420)
    ax.set_ylim(0.62, 1.035)
    ax.set_yticks([0.7, 0.8, 0.9, 1.0])
    ax.set_xlabel("Policy tokens")
    ax.set_ylabel("Required-policy coverage")
    soften_axis(ax, "both")
    panel_title(ax, "Retrieval efficiency")
    label_tag(ax, "marker area = irrelevant rate")
    panel_label(ax, "b")

    method_order = ["All policy", "MSR", "Policy-list diagnostic", "V-MSR Context", "V-MSR Guard"]
    challenge_order = ["Authority\nshadowing", "Crowded\npredicates", "Unknown\nevidence"]
    raw_challenges = ["Authority shadowing", "Crowded predicates", "Unknown evidence"]
    by_pair = {(row["method"], row["challenge"]): row for row in errors}
    matrix = np.array(
        [[1 - value(by_pair[(method, challenge)], "correct") / value(by_pair[(method, challenge)], "episodes") for challenge in raw_challenges] for method in method_order]
    )
    ax = fig.add_subplot(grid[1, 1])
    cmap = LinearSegmentedColormap.from_list("risk", ["#FFFFFF", "#F5D7D3", COLORS["unsafe"]])
    ax.imshow(matrix, vmin=0, vmax=0.5, cmap=cmap, aspect="auto")
    ax.set_xticks(range(3), challenge_order)
    ax.set_yticks(range(len(method_order)), [name.replace("Policy-list diagnostic", "Policy-list\ndiagnostic") for name in method_order])
    for yi in range(matrix.shape[0]):
        for xi in range(matrix.shape[1]):
            rate = matrix[yi, xi]
            ax.text(xi, yi, f"{rate:.2f}", ha="center", va="center", fontsize=6.1, color="white" if rate >= 0.35 else COLORS["ink"])
    ax.tick_params(axis="both", length=0)
    ax.set_frame_on(False)
    panel_title(ax, "Failure-error matrix")
    label_tag(ax, "12 episodes per column")
    panel_label(ax, "c")

    ax = fig.add_subplot(grid[1, 2])
    unknown_rows = [by_pair[(method, "Unknown evidence")] for method in method_order]
    y = np.arange(len(method_order))
    correct = [value(row, "correct") for row in unknown_rows]
    unsafe = [value(row, "unsafe_allow") for row in unknown_rows]
    ax.barh(y, correct, color=COLORS["correct"], height=0.62, label="Correct")
    ax.barh(y, unsafe, left=correct, color=COLORS["unsafe"], height=0.62, label="Unsafe allow")
    ax.set_yticks(y, [name.replace("Policy-list diagnostic", "Policy-list\ndiagnostic") for name in method_order])
    ax.set_xlim(0, 12)
    ax.set_xticks([0, 3, 6, 9, 12])
    ax.invert_yaxis()
    ax.set_xlabel("Episodes")
    soften_axis(ax, "x")
    panel_title(ax, "Unknown evidence")
    label_tag(ax, "n = 12")
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.00), ncol=2, handletextpad=0.4)
    panel_label(ax, "d")
    save_figure(fig, OUTPUT_DIR, "fig3_vmsr_adversarial")


def figure_s1_compression() -> None:
    """补充图 S1：保持 sanity check 的小样本边界，同时提升可读性。"""

    rows = read_csv("compression_sanity_40.csv")
    fig = plt.figure(figsize=(7.2, 3.35))
    grid = fig.add_gridspec(1, 2, width_ratios=[1.22, 0.88], wspace=0.45)

    ax = fig.add_subplot(grid[0])
    states = [
        ("preserved", "Preserved", COLORS["correct"]),
        ("absent", "Absent", COLORS["unsafe"]),
        ("weakened", "Weakened", COLORS["refusal"]),
        ("misbound", "Misbound", COLORS["violet"]),
        ("over_included", "Over-included", COLORS["teal"]),
    ]
    y = np.arange(len(rows))
    left = np.zeros(len(rows))
    for key, label, color in states:
        widths = [value(row, key) for row in rows]
        ax.barh(y, widths, left=left, height=0.60, color=color, edgecolor="white", linewidth=0.75, label=label)
        left += np.asarray(widths)
    ax.set_yticks(y, [row["method"] for row in rows])
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.5, 1.0])
    ax.invert_yaxis()
    ax.set_xlabel("Policy-state proportion")
    soften_axis(ax, "x")
    panel_title(ax, "Policy states after compression")
    # 双行图例需要额外标题留白，避免补充图在窄版面下发生遮挡。
    ax.set_title("Policy states after compression", loc="left", pad=48)
    label_tag(ax, "8 seeds per method", y=1.38)
    ax.legend(ncol=3, loc="lower left", bbox_to_anchor=(0.0, 1.00), columnspacing=1.0, handlelength=1.25)
    panel_label(ax, "a", y=1.38)

    ax = fig.add_subplot(grid[1])
    y = np.arange(len(rows))
    metric_specs = [
        ("accuracy", "Accuracy", COLORS["ours"], "o"),
        ("violation", "Unsafe execution", COLORS["unsafe"], "s"),
        ("false_refusal", "False refusal", COLORS["refusal"], "D"),
    ]
    for key, label, color, marker in metric_specs:
        ax.scatter([value(row, key) for row in rows], y, s=31, color=color, marker=marker, edgecolor="white", linewidth=0.45, label=label, zorder=3)
    ax.set_yticks(y, [row["method"] for row in rows])
    ax.set_xlim(-0.04, 1.04)
    ax.set_xticks([0, 0.5, 1.0])
    ax.invert_yaxis()
    ax.set_xlabel("Episode rate")
    soften_axis(ax, "x")
    panel_title(ax, "Downstream action outcomes")
    ax.set_title("Downstream action outcomes", loc="left", pad=48)
    label_tag(ax, "small-sample sanity check", y=1.38)
    ax.legend(ncol=1, loc="lower left", bbox_to_anchor=(0.0, 1.00), handletextpad=0.4)
    panel_label(ax, "b", y=1.38)
    save_figure(fig, OUTPUT_DIR, "figS1_compression_sanity")


def figure_s2_challenge() -> None:
    """补充图 S2：将 Text/Struct 结果改为更直接的成组比较。"""

    rows = ordered(
        [row for row in read_csv("vmsr_challenge_72.csv") if row["mode"] == "context"],
        ["Struct Context clean", "Struct Context noisy", "Text Context clean", "Text Context noisy"],
    )
    fig = plt.figure(figsize=(7.2, 3.30))
    grid = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.0, 0.85], wspace=0.48)
    labels = [row["method"].replace(" Context", "") for row in rows]
    y = np.arange(len(rows))
    representation_colors = [COLORS["baseline"] if row["representation"] == "struct" else COLORS["ours"] for row in rows]

    ax = fig.add_subplot(grid[0])
    ax.barh(y - 0.14, [value(row, "accuracy") for row in rows], height=0.26, color=representation_colors, label="Accuracy")
    ax.barh(y + 0.14, [value(row, "false_refusal") for row in rows], height=0.26, color=COLORS["refusal"], label="False refusal")
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 1.04)
    ax.set_xticks([0, 0.5, 1.0])
    ax.invert_yaxis()
    ax.set_xlabel("Episode rate")
    soften_axis(ax, "x")
    panel_title(ax, "Action outcomes")
    label_tag(ax, "challenge set · n = 72")
    ax.legend(ncol=2, loc="lower left", bbox_to_anchor=(0.0, 1.00), handletextpad=0.4)
    panel_label(ax, "a")

    ax = fig.add_subplot(grid[1])
    ax.barh(y - 0.14, [value(row, "stability") for row in rows], height=0.26, color=representation_colors, label="Decision stability")
    ax.barh(y + 0.14, [value(row, "unknown_escalation") for row in rows], height=0.26, color=COLORS["violet"], label="Unknown escalation")
    ax.set_yticks(y, [""] * len(y))
    ax.set_xlim(0, 1.04)
    ax.set_xticks([0, 0.5, 1.0])
    ax.invert_yaxis()
    ax.set_xlabel("Episode rate")
    soften_axis(ax, "x")
    panel_title(ax, "Certificate behavior")
    ax.legend(ncol=1, loc="lower left", bbox_to_anchor=(0.0, 1.00), handletextpad=0.4)
    panel_label(ax, "b")

    ax = fig.add_subplot(grid[2])
    bars = ax.barh(y, [value(row, "policy_tokens") for row in rows], height=0.56, color=representation_colors)
    ax.set_yticks(y, [""] * len(y))
    ax.set_xlim(0, 45)
    ax.set_xticks([0, 20, 40])
    ax.invert_yaxis()
    ax.set_xlabel("Policy tokens")
    soften_axis(ax, "x")
    panel_title(ax, "Context cost")
    for bar, row in zip(bars, rows):
        ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2, f"{value(row, 'policy_tokens'):.1f}", va="center", fontsize=6.2, color=COLORS["ink"])
    panel_label(ax, "c")
    save_figure(fig, OUTPUT_DIR, "figS2_vmsr_challenge")


def main() -> None:
    """生成全部主图和补充图；入口只读取本地 CSV，不调用 LLM 或网络。"""

    apply_style()
    figure_1_overview()
    figure_2_main_results()
    figure_3_adversarial()
    figure_s1_compression()
    figure_s2_challenge()
    print(f"figures=5 output={OUTPUT_DIR}")


if __name__ == "__main__":
    main()
