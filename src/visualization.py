"""Readable static figures generated exclusively from benchmark exports."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

COLORS = {"A": "#2166ac", "B": "#d6604d"}
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 130, "savefig.dpi": 170})


def save(fig, path):
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def topology(config, path):
    graph = nx.Graph()
    graph.add_nodes_from(range(config["num_qubits"]))
    graph.add_edges_from(config["undirected_edges"])
    positions = {int(k): v for k, v in config["positions"].items()}
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    nx.draw_networkx(graph, positions, ax=ax, node_color=COLORS[config["name"]],
                     font_color="white", node_size=850, width=2, font_weight="bold")
    ax.set_title(f"Processor {config['name']}: {config['topology']}\n"
                 f"{config['num_qubits']} physical qubits | {len(graph.edges)} undirected links")
    ax.text(.5, -.03, "Every link supports CX in both directions", transform=ax.transAxes, ha="center")
    ax.margins(.2)
    ax.axis("off")
    save(fig, path)


def plot_benchmarks(frame, folder):
    folder = Path(folder)
    primary = frame[frame.layout_mode == "optimized"]
    summary = frame[frame.time > 0].groupby(["processor", "layout_mode", "steps"]).mean(numeric_only=True).reset_index()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.7), sharey=True, layout="constrained")
    for ax, n in zip(axes, [1, 2, 4]):
        part = primary[primary.steps == n]
        a = part[part.processor == "A"]
        ax.plot(a.time, a.exact_z0, color="black", lw=2, label="Exact")
        ax.plot(a.time, a.ideal_z0, "--", color="#777777", label="Ideal Trotter")
        for processor, marker in [("A", "o"), ("B", "s")]:
            sub = part[part.processor == processor]
            ax.plot(sub.time, sub.expected_readout_z0, color=COLORS[processor],
                    linestyle="-" if processor == "A" else ":", label=f"{processor}: expected noisy")
            # Small horizontal offsets separate coincident sampled error bars visually.
            offset = -.012 if processor == "A" else .012
            ax.errorbar(sub.time + offset, sub.measured_z0,
                        yerr=[sub.measured_z0-sub.wilson95_low, sub.wilson95_high-sub.measured_z0],
                        fmt=marker, ms=3, capsize=2, color=COLORS[processor], alpha=.8,
                        label=f"{processor}: sampled 95% CI")
        ax.set(title=f"n = {n}", xlabel="Evolution time t", ylim=(-1.12, 1.12))
        ax.grid(alpha=.18)
    axes[0].set_ylabel("Logical Z0 expectation")
    axes[2].legend(fontsize=8, loc="lower left")
    fig.suptitle("Optimized placement | noisy includes gate and readout errors\n"
                 "4096 shots; Wilson intervals; markers offset by 0.012 for visibility", fontsize=12)
    save(fig, folder / "z0_time_evolution.png")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), layout="constrained")
    for processor in ["A", "B"]:
        sub = summary[(summary.processor == processor) & (summary.layout_mode == "optimized")]
        style = "o-" if processor == "A" else "s--"
        for ax, column in zip(axes, ["total_expected_error", "noisy_fidelity_to_trotter", "noisy_fidelity_to_exact"]):
            ax.plot(sub.steps, sub[column], style, color=COLORS[processor], label=processor,
                    ms=7 if processor == "A" else 4)
    base = summary[(summary.processor == "A") & (summary.layout_mode == "optimized")]
    axes[0].plot(base.steps, base.trotter_error, "k:", label="Ideal Trotter error")
    axes[2].plot(base.steps, base.algorithm_fidelity, "k:", label="Algorithm fidelity")
    for ax, title in zip(axes, ["Expected absolute Z0 error", "Noise-only fidelity", "Fidelity to exact state"]):
        ax.set(title=title, xlabel="Trotter steps n", xticks=[1, 2, 4])
        ax.legend(fontsize=9)
        ax.grid(alpha=.18)
    fig.suptitle("Optimized placement | arithmetic means over t = 0.25, ..., 2.00\n"
                 "A and B curves overlap to numerical precision", fontsize=12)
    save(fig, folder / "error_vs_trotter_steps.png")

    fig, axes = plt.subplots(2, 3, figsize=(13, 7), layout="constrained")
    for row, layout in enumerate(["optimized", "fixed"]):
        for ax, column, title in zip(axes[row], ["depth", "cx_count", "routing_swaps"],
                                     ["Native depth", "CX count", "Audited routing SWAPs"]):
            for processor in ["A", "B"]:
                sub = summary[(summary.processor == processor) & (summary.layout_mode == layout)]
                ax.plot(sub.steps, sub[column], "o-" if processor == "A" else "s--",
                        color=COLORS[processor], label=processor, ms=7 if processor == "A" else 4)
            ax.set(title=f"{layout.capitalize()}: {title}", xlabel="Trotter steps n", xticks=[1, 2, 4])
            if column == "routing_swaps":
                top = max(1, int(summary[summary.layout_mode == layout][column].max()))
                ax.set(ylim=(-.1, top+.2), yticks=list(range(top+1)))
            ax.grid(alpha=.18)
            ax.legend()
    fig.suptitle("Circuit resources | means over positive times; excludes saves and measurements")
    save(fig, folder / "depth_cx_swap_comparison.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    for ax, column, title in zip(axes, ["total_expected_error", "noisy_fidelity_to_exact"],
                                ["Expected absolute Z0 error", "Pre-readout fidelity to exact state"]):
        for processor in ["A", "B"]:
            for layout, linestyle, marker in [("optimized", "-", "o"), ("fixed", "--", "s")]:
                sub = summary[(summary.processor == processor) & (summary.layout_mode == layout)]
                ax.plot(sub.steps, sub[column], linestyle=linestyle, marker=marker,
                        color=COLORS[processor], label=f"{processor} / {layout}",
                        ms=7 if layout == "optimized" else 4)
        ax.set(title=title, xlabel="Trotter steps n", xticks=[1, 2, 4])
        ax.grid(alpha=.18)
        ax.legend(fontsize=9)
    fig.suptitle("Layout sensitivity | fixed means initial logical placement [0, 1, 2, 3]\n"
                 "Means over eight positive times; coincident curves overlap", fontsize=11)
    save(fig, folder / "layout_sensitivity.png")
