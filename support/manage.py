"""Supporting reproduction commands; deliberately outside required project tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / "project"
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("RAYON_NUM_THREADS", "1")


def initialize():
    import nbformat as nb
    for folder in ["processors", "data/raw", "data/processed", "results/tables", "results/figures",
                   "assets/qff_phase1_latex_images"]:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    common = {"basis_gates": ["rz", "sx", "x", "cx"],
              "noise": {"one_qubit": .001, "cx": .005, "readout": .01,
                        "one_qubit_gates": ["rz", "sx", "x"]},
              "optimization_level": 1, "seed_transpiler": 42, "seed_simulator": 42, "shots": 4096,
              "direction": "bidirectional: every undirected edge is listed in both CX directions"}
    designs = [
        ("A", 5, "Five-qubit linear chain", [(i, i+1) for i in range(4)],
         {i: [i, 0] for i in range(5)},
         "Minimal connected nearest-neighbor baseline. Contains the four-spin path natively; avoids an artificially routing-constrained star."),
        ("B", 9, "3 x 3 square grid", [(3*r+c, 3*r+c+1) for r in range(3) for c in range(2)]
         + [(3*r+c, 3*(r+1)+c) for r in range(2) for c in range(3)],
         {i: [i%3, -(i//3)] for i in range(9)},
         "Planar nearest-neighbor alternative with cycles and multiple four-node paths. Extra links may help general routing but need not improve this chain. This is not heavy-hex.")]
    for name, n, topology, edges, positions, reason in designs:
        config = {**common, "name": name, "num_qubits": n, "topology": topology,
                  "undirected_edges": edges, "directed_cx_edges": [e for a, b in edges for e in [(a,b), (b,a)]],
                  "positions": positions, "justification": reason,
                  "fixed_initial_layout": [0, 1, 2, 3]}
        (ROOT / "processors" / f"processor_{name}.json").write_text(json.dumps(config, indent=2)+"\n")
    sources = [
        ("IBM coupling maps", "https://quantum.cloud.ibm.com/docs/en/guides/represent-quantum-computers", "Directed coupling constraints; logical versus physical qubits."),
        ("IBM CouplingMap API", "https://quantum.cloud.ibm.com/docs/en/api/qiskit/2.3/qiskit.transpiler.CouplingMap", "Line/grid alternatives; heavy-hex construction is a different family. Versioned 2.3 search result consulted; implementation inspected/tested on installed version."),
        ("IBM heavy-hex lattice", "https://www.ibm.com/quantum/blog/heavy-hex-lattice", "Physical connectivity trades off with device engineering; dense connectivity is not automatically better hardware."),
        ("Li, Ding, Xie: SABRE", "https://arxiv.org/abs/1809.02573", "Primary mapping research motivates heuristic layout and routing; no claim of globally optimal placement."),
        ("IBM compiler API", "https://quantum.cloud.ibm.com/docs/en/api/qiskit/compiler", "Native basis, seed, level, direction and callback settings."),
        ("IBM staged pass manager", "https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.StagedPassManager", "Post-routing hook before translation; analysis checkpoint is read-only."),
        ("IBM SabreLayout", "https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.passes.SabreLayout", "Explicit trial counts avoid CPU-dependent defaults; this pass can apply routing before the routing stage."),
        ("IBM SabreSwap", "https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.passes.SabreSwap", "Seeded decay heuristic with 20 routing trials."),
        ("IBM TranspileLayout", "https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.TranspileLayout", "final_index_layout maps original logical qubits to final output positions."),
        ("IBM bit ordering", "https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering", "Little-endian state indices and q3q2q1q0 display."),
        ("Aer noise models", "https://qiskit.github.io/qiskit-aer/tutorials/3_building_noise_models.html", "Shared gate noise and symmetric readout assignment channel."),
        ("Aer depolarizing channel", "https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.depolarizing_error.html", "lambda in (1-lambda)rho + lambda I/2^n; not calibrated decoherence."),
        ("Aer reduced density save", "https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.library.save_density_matrix.html", "Save selected qubits before measurement, then explicitly permute into logical order."),
        ("SciPy expm", "https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.expm.html", "Dense independent matrix exponential reference.")]
    (ROOT / "data/raw/research_sources.json").write_text(json.dumps([
        {"title": title, "url": url, "access_date": "2026-10-13", "use": use,
         "version_note": "Web latest unless URL versioned; exact executed package versions in experiment_config.json."}
        for title, url, use in sources], indent=2)+"\n")
    cells = [
        nb.v4.new_markdown_cell("# PS-S3: Trotter Error vs Synthetic Device Noise\n"
            "An Architectural Study of Quantum Simulation Accuracy\n\n"
            "Four logical spins; participant-designed A (5-qubit line) and B (9-qubit grid). "
            "This notebook regenerates the full 108-case grid and all benchmark plots. "
            "Use the pinned environment and run all cells from a fresh kernel. "
            "Reusable physics, compilation, simulation and plotting live in `src/`."),
        nb.v4.new_code_cell("from pathlib import Path\nimport json\nimport numpy as np\n"
            "from IPython.display import display, Image\n"
            "from src.problem import hamiltonian, dense_terms, exact_state, trotter_circuit\n"
            "from src.processors import ROOT, load_processor\nfrom src.metrics import run_benchmark, environment\n"
            "print(json.dumps(environment(), indent=2))"),
        nb.v4.new_markdown_cell("## Physics and conventions\n"
            r"$H=-\sum_{i=0}^2 Z_iZ_{i+1}-\sum_{i=0}^3X_i$, $J=g=1$, $\hbar=1$. "
            "Primary state: |0000>. Qiskit label IIIZ is Z0. "
            r"$R_P(\theta)=e^{-i\theta P/2}$ gives RX/RZZ angles $-2\Delta t$. "
            "Apply ZZ gates first, then X: "
            r"$U_n(t)=[e^{-iH_Xt/n}e^{-iH_{ZZ}t/n}]^n$. "
            "The exact reference uses independent NumPy tensor products and SciPy expm."),
        nb.v4.new_code_cell("hzz, hx = dense_terms()\nassert np.allclose(hamiltonian().to_matrix(), hzz+hx)\n"
            "display(hamiltonian())\nprint(trotter_circuit(0.5, 1).draw(output='text'))"),
        nb.v4.new_markdown_cell("## Architectures and controlled settings\n"
            "A is a five-node line; B a row-major 3x3 grid. Every link supports both CX directions. "
            "Both contain a four-node path. Optimized means SABRE heuristic placement, not a proof of optimality. "
            "Fixed placement [0,1,2,3] is label-dependent and not an architecture ranking. "
            "Noise: depolarizing lambda=.001 after every rz/sx/x, .005 after cx; readout=.01. "
            "Level 1, transpiler and simulator seed 42, 4096 shots; n=1,2,4; nine times from 0 to 2."),
        nb.v4.new_code_cell("for name in ['A', 'B']:\n    cfg = load_processor(name)\n"
            "    print(name, cfg['num_qubits'], cfg['undirected_edges'])"),
        nb.v4.new_markdown_cell("## Paired ideal/noisy experiment and exports\n"
            "Each pair uses the same compiled circuit. The post-routing checkpoint counts SWAPs before "
            "native decomposition. Sorted physical outputs are reduced and reordered to logical qubits "
            "using the final layout. Every case checks ideal compilation fidelity and shot totals. "
            "The density is saved before measurement; readout affects counts, not state fidelity."),
        nb.v4.new_code_cell("results, summary = run_benchmark()\nassert len(results) == 108\n"
            "print('Minimum compiled ideal fidelity:', results.compiled_ideal_fidelity.min())\n"
            "display(summary.round(6))"),
        nb.v4.new_markdown_cell("## Topologies, accuracy and resource costs\n"
            "Summary means exclude t=0. Error bars show finite-shot Wilson 95% intervals only. "
            "Signed error components can cancel: absolute component sizes must not be added."),
        nb.v4.new_code_cell("for name in ['processor_A_topology', 'processor_B_topology', 'z0_time_evolution',\n"
            "             'error_vs_trotter_steps', 'depth_cx_swap_comparison', 'layout_sensitivity']:\n"
            "    display(Image(filename=str(ROOT / 'results/figures' / (name + '.png'))))"),
        nb.v4.new_markdown_cell("## Results and bounded conclusions\n"
            "Select the best n only among 1,2,4 for mean expected absolute Z0 error over positive times. "
            "Fidelity is a separate metric. These are synthetic channels, one compiler seed and two chosen graphs; "
            "there is no calibrated hardware model, universal optimum, or guaranteed B advantage."),
        nb.v4.new_code_cell("best = summary.loc[summary.groupby(['processor', 'layout_mode']).total_expected_error.idxmin(),\n"
            "                   ['processor', 'layout_mode', 'steps', 'total_expected_error']]\n"
            "display(best)\nprint('Raw counts, routing audits, compiled circuits, states, CSV tables and figures regenerated.')")]
    notebook = nb.v4.new_notebook(cells=cells, metadata={"kernelspec": {
        "name": "python3", "display_name": "Python 3 (project environment)", "language": "python"}})
    nb.write(notebook, ROOT / "main.ipynb")
    (ROOT / "assets/qff_phase1_latex_images/.gitkeep").write_text("")
    print("Created processor inputs, source notes, and notebook.")


def static_check():
    import ast
    paths = list((ROOT / "src").glob("*.py")) + list((BASE / "support").rglob("*.py"))
    for path in paths:
        ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    print(f"Python syntax parsed successfully for {len(paths)} source/support files.")


def installation_status():
    import importlib.metadata as metadata
    installed = {d.metadata["Name"].lower(): d.version for d in metadata.distributions()}
    names = ["numpy", "scipy", "qiskit", "qiskit-aer", "pandas", "matplotlib", "nbclient", "ipykernel"]
    print(json.dumps({n: installed.get(n, "not installed yet") for n in names}, indent=2))


def inspect_results():
    import pandas as pd
    frame = pd.read_csv(ROOT / "results/tables/benchmark_results.csv")
    summary = pd.read_csv(ROOT / "results/tables/summary.csv")
    print(summary.to_string(index=False))
    print("Minimum compilation fidelity:", frame.compiled_ideal_fidelity.min())
    print("Largest shot standard error:", frame.standard_error.max())
    print("All rows:", len(frame))


def pin():
    from src.metrics import environment
    env = environment()
    (ROOT / "requirements.txt").write_text("# Tested Python " + env["python"] + "\n" +
        "\n".join(f"{name}=={version}" for name, version in env["packages"].items())+"\n")
    # Full environment record supplements portable direct dependency pins.
    frozen = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
    (BASE / "support/environment-freeze.txt").write_text(frozen)
    print(json.dumps(env, indent=2))


def test():
    result = subprocess.run([sys.executable, "-m", "pytest", str(BASE / "support/tests"), "-q"],
                            cwd=ROOT, capture_output=True, text=True)
    (BASE / "support/test_output.txt").write_text(result.stdout + result.stderr)
    print(result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit(result.returncode)


def notebook():
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client import KernelManager
    before = {p: (ROOT / p).read_bytes() for p in ["results/tables/benchmark_results.csv", "data/raw/counts.json"]}
    book = nbformat.read(ROOT / "main.ipynb", as_version=4)
    km = KernelManager(kernel_name="python3")
    km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    client = NotebookClient(book, timeout=600, km=km, resources={"metadata": {"path": str(ROOT)}})
    try:
        client.execute()
    finally:
        if km.has_kernel:
            km.shutdown_kernel(now=True)
    nbformat.write(book, ROOT / "main.ipynb")
    comparisons = {p: (ROOT / p).read_bytes() == content for p, content in before.items()}
    if not all(comparisons.values()):
        raise AssertionError(f"Fresh-kernel rerun changed numerical exports: {comparisons}")
    status = {"fresh_kernel": True, "code_cells_executed": sum(c.cell_type == "code" for c in book.cells),
              "reproducibility_byte_equal": comparisons, "errors": 0}
    (BASE / "support/notebook_verification.json").write_text(json.dumps(status, indent=2)+"\n")
    print(json.dumps(status, indent=2))


def render_guide():
    import pymupdf
    doc = pymupdf.open(BASE / "PS_S3_Codex_Plan/QFF_Phase_1_Master_Guide.pdf")
    out = BASE / "support/guide_preview"
    out.mkdir(exist_ok=True)
    for i in [1, 2, 4, 6]:
        doc[i].get_pixmap(matrix=pymupdf.Matrix(1.2, 1.2)).save(out / f"page_{i+1}.png")
    print("Rendered relevant guide pages 2, 3, 5 and 7.")


def documents():
    import pandas as pd
    from src.metrics import environment
    frame = pd.read_csv(ROOT / "results/tables/benchmark_results.csv")
    summary = pd.read_csv(ROOT / "results/tables/summary.csv")
    env = environment()
    verified = json.loads((BASE / "support/notebook_verification.json").read_text())
    portability_note = ""
    if (BASE / "support/portability_verification.json").exists():
        portability_note = ("The clean ZIP was extracted into a different local directory and the full 108-case grid "
                            "rerun successfully, producing byte-identical benchmark CSV and raw counts. "
                            "This verifies paths within the tested environment, not cross-platform equivalence.")
    tests = (BASE / "support/test_output.txt").read_text().strip().splitlines()[-1]
    def table(df, columns):
        lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"]*len(columns)) + " |"]
        for _, row in df.iterrows():
            cells = [f"{row[c]:.6f}" if isinstance(row[c], float) else str(row[c]) for c in columns]
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)
    primary = summary[summary.layout_mode == "optimized"]
    a_primary = primary[primary.processor == "A"].set_index("steps")
    b_fixed = summary[(summary.processor == "B") & (summary.layout_mode == "fixed")].set_index("steps")
    best = summary.loc[summary.groupby(["processor", "layout_mode"]).total_expected_error.idxmin()]
    numerical = ["depth", "cx_count", "routing_swaps", "total_expected_error", "noisy_fidelity_to_exact"]
    a = frame[frame.processor == "A"].set_index(["layout_mode", "steps", "time"])
    b = frame[frame.processor == "B"].set_index(["layout_mode", "steps", "time"])
    differences = (a.loc["optimized", numerical] - b.loc["optimized", numerical]).abs().max()
    cancellation = frame.copy()
    cancellation["component_sum"] = cancellation.trotter_error + cancellation.gate_noise_shift + cancellation.readout_shift
    cancellation["cancellation"] = cancellation.component_sum - cancellation.total_expected_error
    example = cancellation.loc[cancellation.cancellation.idxmax()]
    findings = table(primary, ["processor", "steps", "depth", "cx_count", "routing_swaps",
                                 "total_expected_error", "algorithm_fidelity", "noisy_fidelity_to_trotter",
                                 "noisy_fidelity_to_exact"])
    best_table = table(best, ["processor", "layout_mode", "steps", "total_expected_error"])
    source_list = json.loads((ROOT / "data/raw/research_sources.json").read_text())
    references = "\n".join(f"- [{s['title']}]({s['url']}): {s['use']}" for s in source_list)
    report = f'''# PS-S3 - Architectural analysis

## Question and evidence

How does first-order Trotter approximation interact with synthetic device noise on a five-qubit line (A) and nine-qubit square grid (B)? The executed baseline contains 108 cases and 216 paired ideal/noisy sampled runs. Primary results use SABRE placement; fixed placement is a sensitivity control. All observations below derive from `results/tables/benchmark_results.csv` and its positive-time summary, with raw counts, routing audits and density matrices retained.

## Model and derivation

Four logical spins, open boundary, J=g=1 and hbar=1:

$$H=-J(Z_0Z_1+Z_1Z_2+Z_2Z_3)-g(X_0+X_1+X_2+X_3).$$

The primary state is |0000>; correctness tests also use |0101> (X on q0 and q2) and a deliberately asymmetric state. Pauli strings are q3q2q1q0: Z0 is IIIZ. The exact state is SciPy `expm(-1j*t*H) @ psi0`, with H constructed independently from NumPy tensor products. Its equality to the Qiskit SparsePauliOp matrix is tested.

Because RX(theta)=exp(-i theta X/2) and RZZ(theta)=exp(-i theta ZZ/2), the negative Hamiltonian coefficients require angles -2g*t/n and -2J*t/n. Applying ZZ then X gives `[exp(-i H_X*t/n) exp(-i H_ZZ*t/n)]**n` in matrix order. The independent full-unitary product test detects both sign and ordering errors. At t=0 no evolution gates are inserted.

## Architecture selection before results

A: nodes 0..4, links (0,1),(1,2),(2,3),(3,4). B: row-major nodes 0..8 on a 3x3 grid; horizontal links (0,1),(1,2),(3,4),(4,5),(6,7),(7,8), vertical links (0,3),(1,4),(2,5),(3,6),(4,7),(5,8). Every link is explicitly listed in both CX directions in JSON.

The line is a minimal connected nearest-neighbor control, with four edges and maximum degree two. The grid has twelve edges and maximum degree four, with alternate paths and cycles. Both contain the four-spin path. These designs were selected before numerical evaluation to allow a legitimate null result.

The planning pack's star was considered but rejected for primary A: it has no four-node simple path, which would build a disadvantage into this chain experiment. A branching tree or ring also supports a path; ring chords are not necessary for the present task. The grid offers a simple planar alternative with transparent numbering. It is not heavy-hex, not an IBM backend, and not calibrated hardware. IBM's heavy-hex discussion motivates acknowledging the engineering costs omitted by a uniform-noise graph model; it does not establish this grid as physically superior.

![Processor A](results/figures/processor_A_topology.png)
![Processor B](results/figures/processor_B_topology.png)

## Controls, compilation and audit

The two processors share basis rz/sx/x/cx, level 1, transpiler seed 42, simulator seed 42, and 4096 shots. A depolarizing channel with Aer parameter lambda=.001 follows **every rz, sx and x**; lambda=.005 follows CX. The channel is `(1-lambda)*rho + lambda*I/2**k`. Symmetric readout bit flips have p=.01. No idle, T1/T2, crosstalk or calibration model is used. Noisy RZ is an explicit common synthetic convention.

The preset level-1 pipeline uses SABRE layout and routing. Trial counts are fixed at 20 (layout and swap), with three layout iterations and routing decay heuristic, to avoid CPU-count-dependent trial defaults. Optimized means heuristic-selected placement, not certified global optimality. Fixed means initial logical-to-physical [0,1,2,3]. On the row-major grid, that set is not already the logical chain, so this control is label dependent.

`RoutingCheckpoint`, a read-only analysis pass, records the full physical operation stream after routing and before translation. Counts refer to SWAP instructions at this checkpoint, including routing applied by SabreLayout. Source circuits have no SWAPs. The pass trace and checkpoint operations are preserved per case; replay tests compare checkpoint and final native states. Final native SWAP counts are separately reported and are not routing counts. CX/3 is never used to infer SWAPs. These audited SWAPs count inserted operations before later simplification, not a guarantee of exactly three surviving CX per SWAP.

Each ideal/noisy pair starts with the same native circuit; QPY files and hashes are retained. Diagnostic saves and measurements are appended afterward and excluded from depth and gate counts. `final_index_layout` determines measurement targets and the saved physical subset. The subset is saved in ascending physical order, ancillas traced out, and density indices explicitly permuted into logical order. Every baseline case checks compilation fidelity; the minimum observed value is **{frame.compiled_ideal_fidelity.min():.12f}**.

## Error and fidelity definitions

Let ze be exact Z0, zi ideal Trotter Z0, zg pre-readout gate-noisy Z0, zr=.98*zg the expected readout value, and zs the sampled value. Exports include absolute and signed differences for zi-ze, zg-zi, zr-zg and zs-zr. Total expected error is |zr-ze| and total sampled error is |zs-ze|. Signed terms telescope; absolute components need not add.

For example, case `{example.case_id}` has absolute component sum {example.component_sum:.6f}, while total expected error is {example.total_expected_error:.6f}: cancellation matters. This is not error mitigation.

For N=4096, the plug-in standard error is sqrt((1-zs^2)/N). A Wilson 95% interval is also exported and plotted because the plug-in SE vanishes at an all-identical sample. The ideal sample has its own uncertainty columns. Intervals describe shot uncertainty, not systematic uncertainty or independent-run confidence in architecture rankings. Resetting seed 42 per case may correlate sampling differences; no significance claim is made from small sampled gaps.

Algorithm fidelity is |<exact|Trotter>|^2. Noise-only fidelity is <Trotter|rho_gate|Trotter>. Fidelity to exact is <exact|rho_gate|exact>. All three are pre-readout simulator state diagnostics, not measured hardware fidelities or products of per-gate success probabilities.

## Verified results

Arithmetic means below use the eight positive times 0.25,0.5,...,2.0, separately by processor and n. t=0 remains in raw exports but is excluded from aggregates.

{findings}

Maximum absolute A/B difference in the optimized pointwise comparison: depth {differences['depth']:.3g}, CX {differences['cx_count']:.3g}, audited SWAPs {differences['routing_swaps']:.3g}, expected error {differences['total_expected_error']:.3g}, and fidelity to exact {differences['noisy_fidelity_to_exact']:.3g}. Interpret numerical differences near floating-point precision as ties.

Best n **only among tested values**, minimizing mean expected absolute Z0 error over positive times:

{best_table}

The trade-off is visible without forcing a crossover: from n=1 to n=4, mean noise-only fidelity drops from {a_primary.loc[1, 'noisy_fidelity_to_trotter']:.6f} to {a_primary.loc[4, 'noisy_fidelity_to_trotter']:.6f}, but algorithm fidelity rises from {a_primary.loc[1, 'algorithm_fidelity']:.6f} to {a_primary.loc[4, 'algorithm_fidelity']:.6f}. The approximation improvement wins over the added gate noise within the tested range: mean expected error decreases {a_primary.loc[1, 'total_expected_error']:.6f} -> {a_primary.loc[2, 'total_expected_error']:.6f} -> {a_primary.loc[4, 'total_expected_error']:.6f}. No aggregate noise crossover appears among n=1,2,4. This does not imply pointwise monotonic improvement at every time or beyond n=4.

At n=4, fixed B has {b_fixed.loc[4, 'routing_swaps']:.0f} audited SWAPs and {b_fixed.loc[4, 'cx_count']:.0f} CX gates, versus zero SWAPs and {a_primary.loc[4, 'cx_count']:.0f} CX for optimized placement. Its mean fidelity to exact falls to {b_fixed.loc[4, 'noisy_fidelity_to_exact']:.6f}, versus {a_primary.loc[4, 'noisy_fidelity_to_exact']:.6f} optimized. Mean Z0 error changes only from {a_primary.loc[4, 'total_expected_error']:.6f} to {b_fixed.loc[4, 'total_expected_error']:.6f}. The small single-observable change does not capture the full state degradation; n=1 and n=2 fixed-B Z0 means even coincide with optimized values at displayed precision despite lower fidelities.

The larger processor is not guaranteed to win. This path-shaped workload can fit the line without routing; B's spare qubits and alternate routes may be unused. Fixed-placement results illustrate the cost of an unsuitable placement, not intrinsic inferiority of the grid.

![Dynamics and shot uncertainty](results/figures/z0_time_evolution.png)
![Error and fidelity](results/figures/error_vs_trotter_steps.png)
![Native resources and audited routing](results/figures/depth_cx_swap_comparison.png)
![Layout sensitivity](results/figures/layout_sensitivity.png)

Full fixed-placement means:

{table(summary[summary.layout_mode == 'fixed'], ['processor', 'steps', 'depth', 'cx_count', 'routing_swaps', 'total_expected_error', 'noisy_fidelity_to_exact'])}

## Validation and reproducibility

Test outcome: **{tests}**. Fresh-kernel notebook: **{verified['code_cells_executed']} code cells**, zero execution errors. Independent CLI and notebook reruns produced byte-identical benchmark CSV and raw counts on this environment. Tests cover Hermiticity, full unitary sign/order, both basis initial states, Z0 endianness, small-time convergence, invalid inputs, graph/noise parity, native edges, routed mapping and asymmetric states, audit replay, density validity, readout-only/zero-noise behavior, uncertainty and export completeness.

Executed environment: Python {env['python']}, Qiskit {env['packages']['qiskit']}, Aer {env['packages']['qiskit-aer']}. Exact direct dependencies are pinned in requirements.txt. Full installed environment, tests and reproduction commands are in the separate verification support archive. Seeds and trial counts reduce stochastic variability, but cross-version or cross-platform bitwise identity is not promised. The notebook reruns the full experiment rather than relying on hidden state.

## Limitations and next steps

{portability_note}

Only two chosen graphs, one compiler seed, three n values, one time window, J=g=1 and the 0000 primary state are benchmarked. The 0101 state is a correctness control, not a second full benchmark. Qubit count, degree and edge count change together, so causal effects of qubit budget alone cannot be isolated. Fixed labels are intentionally held constant and can favor a topology. No claim is made that more steps always worsen accuracy, that state fidelity and Z0 error rank n identically, or that a universal crossover has been found. A future study could add independently selected graphs, seeds and state sensitivities while preserving official rates; it is outside this completed Phase 1 scope.

## Sources and attribution

Official requirements: user-supplied QFF Phase 1 Master Guide, pages 1-3, 5 and 7, read on 2026-10-13. Research URLs were consulted on 2026-10-13; API behavior was additionally tested against installed versions. The topology choice and mathematical derivation are this project's design decisions.

{references}

AI assistance: OpenAI Codex assisted implementation, research, testing and documentation. The team must review the code, understand the conclusions, and follow event attribution rules. Actual team names have not been supplied. Source repository: https://github.com/udbhav-metla/Qskit_Online. No event-portal submission has been made.
'''
    (ROOT / "report.md").write_text(report, encoding="utf-8")
    readme = f'''# Trotter Error vs Synthetic Device Noise

**An Architectural Study of Quantum Simulation Accuracy**
Qiskit Fall Fest Phase 1: **PS-S3 - Noise Accumulation in Trotter Circuits**

Completed local benchmark: 108 cases, 216 paired ideal/noisy Aer sampled runs, exact SciPy references, and a freshly executed notebook. Processor A is a five-qubit line; B is a nine-qubit square grid. Both implement the same four-spin open-boundary TFIM. No external dataset, credentials or processor download is needed.

## Setup and execution

Tested with Python {env['python']}, Qiskit {env['packages']['qiskit']} and Aer {env['packages']['qiskit-aer']} on Windows. From this `project/` directory:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
python -c "from src.metrics import run_benchmark; run_benchmark()"
```

On Linux/macOS use `source .venv/bin/activate`. Python 3.12 is recommended; other platforms were not executed in this study. In VS Code or your notebook frontend, open `main.ipynb`, select this virtual environment as the kernel, restart it and Run All. Notebook UI software is separate from the pinned execution dependencies.

Headless fresh-kernel execution from `project/`, using the active Python environment without global kernel registration:

```python
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
book = nbformat.read("main.ipynb", as_version=4)
km = KernelManager(kernel_name="python3")
km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{{connection_file}}"]
NotebookClient(book, timeout=600, km=km).execute()
nbformat.write(book, "main.ipynb")
```

Save that block as a temporary Python file and run it in the activated environment, or use the supporting `manage.py notebook` command when the separate support archive is extracted beside `project/`. Reruns overwrite generated benchmark outputs. The notebook imports all scientific implementation from src.

## Required structure (official PDF order)

```text
project/
├── README.md
├── main.ipynb
├── requirements.txt
├── data/
│   ├── raw/
│   └── processed/
├── processors/
│   ├── processor_A.json
│   └── processor_B.json
├── src/
│   ├── __init__.py
│   ├── problem.py
│   ├── processors.py
│   ├── routing.py
│   ├── metrics.py
│   └── visualization.py
├── results/
│   ├── tables/
│   └── figures/
├── report.md
└── assets/
    └── qff_phase1_latex_images/
```

Planning documents and supporting tests/scripts are outside this required tree and outside the clean project ZIP. The optional equation-assets directory is retained.

## Method and settings

H=-sum ZZ - sum X, J=g=1, hbar=1, initial |0000>. First-order ZZ-then-X gates use negative angles -2*t/n; n=1,2,4. Nine times: 0,.25,...,2. The independent dense reference uses SciPy expm. Logical Z0 is IIIZ and classical bit zero is the rightmost sampled bit. |0101> and an asymmetric state check mapping correctness.

Native basis rz/sx/x/cx; identical synthetic depolarizing parameters .001 after every rz/sx/x, .005 after cx; symmetric readout .01. Level 1, both seeds 42, 4096 shots. SABRE optimized placement is primary; fixed [0,1,2,3] is a sensitivity control. Explicit SABRE trial counts are 20, with three layout iterations. Both CX directions are listed in each processor JSON. These are synthetic models, not calibrated physical decoherence.

SWAP counts come from a full post-routing/pre-translation audit, not final literal SWAPs or CX/3. Final layouts control logical measurements and reduced-state ordering. The same compiled circuit is used for each ideal/noisy pair. State fidelities are pre-readout. Signed errors can cancel; absolute error components are not additive.

## Results

Best tested n for mean expected absolute Z0 error, averaging t>0:

{best_table}

Optimized A/B maximum pointwise expected-error difference: {differences['total_expected_error']:.3g}. See [report.md](report.md) for fidelity, routing, architecture reasoning and limitations. A chain can embed on a line, so extra connectivity need not improve this workload.

![Error and fidelity across tested steps](results/figures/error_vs_trotter_steps.png)

## Evidence and checks

- `data/raw/experiment_config.json`: exact settings, graph configs and executed environment.
- `data/raw/counts.json`: all ideal/noisy 4096-shot histograms.
- `data/raw/routing_audit.json` and `data/raw/circuits/`: pass traces, pre-translation operations, layouts, QPY native circuits and hashes.
- `data/raw/research_sources.json`: official/primary sources, access dates and design uses.
- `data/processed/`: Hamiltonian, exact states/reference table, and all logical ideal/noisy density matrices.
- `results/tables/`: 108-row metrics and 12-row positive-time summaries.
- `results/figures/`: six figures covering topology, dynamics, accuracy, resources and placement.

Verification: **{tests}**; fresh notebook **{verified['code_cells_executed']} code cells**, no errors; CLI/notebook counts and benchmark CSV byte-identical on the tested environment. Finite-shot SE and Wilson intervals are exported. Summary tables exclude t=0. See separate verification support for tests, logs and commands.

## Limitations and submission checklist

{portability_note}

One primary initial state, two chosen graphs, one compiler seed, and three n values cannot establish a universal optimum or pure qubit-count effect. Fixed placement depends on labels. Extra grid links have no calibration/crosstalk cost in this model. No quantum advantage or hardware-performance claim is made.

- [x] Local implementation, exact reference, complete A/B grid and exports.
- [x] Physics/routing/noise tests and fresh notebook execution.
- [ ] Team adds actual member names (not supplied) and reviews scientific conclusions.
- [ ] Team reviews AI-assistance attribution and event rules.
- [ ] Team submits the repository URL to the event portal when ready.

Source repository: https://github.com/udbhav-metla/Qskit_Online. No event-portal submission has been made. The supplied guide states October 14, 2026, 23:59 IST and https://qffsrmap2026.com/learning/hackathon; that recorded deadline is historical, not a claim about current submission availability. Codex assisted research, implementation, validation and documentation; no team identity has been invented.
'''
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print("Wrote README and report from executed results and verification records.")


def package():
    forbidden = {"__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".venv"}
    included = sorted(p for p in ROOT.rglob("*") if p.is_file() and not forbidden.intersection(p.parts))
    manifest = {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in included}
    (BASE / "support/project_sha256.json").write_text(json.dumps(manifest, indent=2)+"\n")
    destination = BASE / "PS_S3_Phase1_Project.zip"
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder in ["project/", "project/assets/qff_phase1_latex_images/"]:
            archive.writestr(folder, "")
        for path in included:
            archive.write(path, "project/"+path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert len([x for x in archive.namelist() if not x.endswith("/")]) == len(included)
    support_zip = BASE / "PS_S3_Verification_Support.zip"
    with zipfile.ZipFile(support_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((BASE / "support").rglob("*")):
            if path.is_file() and not forbidden.intersection(path.parts) and "guide_preview" not in path.parts:
                archive.write(path, "support/"+path.relative_to(BASE / "support").as_posix())
    print(f"Packaged {len(included)} project files, {destination.stat().st_size:,} bytes; ZIP CRC check passed.")
    print("Verification support packaged separately.")


def portability():
    import tempfile
    target = Path(tempfile.mkdtemp(prefix="relocation_check_", dir=BASE)).resolve()
    if not target.is_relative_to(BASE.resolve()):
        raise RuntimeError("Relocation target outside project workspace")
    with zipfile.ZipFile(BASE / "PS_S3_Phase1_Project.zip") as archive:
        for entry in archive.namelist():
            if not (target / entry).resolve().is_relative_to(target):
                raise RuntimeError("Unsafe archive path")
        archive.extractall(target)
    program = "from src.metrics import run_benchmark; run_benchmark(progress=False)"
    result = subprocess.run([sys.executable, "-c", program], cwd=target / "project",
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    outputs = ["results/tables/benchmark_results.csv", "data/raw/counts.json"]
    equal = {p: (ROOT / p).read_bytes() == (target / "project" / p).read_bytes() for p in outputs}
    if not all(equal.values()):
        raise AssertionError(f"Relocated run differed: {equal}")
    status = {"clean_zip_extracted": True, "different_directory_full_grid": True,
              "byte_equal_outputs": equal, "cases": 108}
    (BASE / "support/portability_verification.json").write_text(json.dumps(status, indent=2)+"\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["portability", "inspect", "installation-status", "static", "init", "pin", "test", "run", "notebook", "render-guide", "documents", "package"])
    args = parser.parse_args()
    if args.command == "run":
        from src.metrics import run_benchmark
        run_benchmark()
    else:
        {"portability": portability, "inspect": inspect_results, "installation-status": installation_status, "static": static_check, "init": initialize, "pin": pin, "test": test, "notebook": notebook,
         "render-guide": render_guide, "documents": documents, "package": package}[args.command]()
