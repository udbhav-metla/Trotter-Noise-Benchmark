# Trotter Error vs Synthetic Device Noise

**An Architectural Study of Quantum Simulation Accuracy**
Qiskit Fall Fest Phase 1 · **PS-S3 — Noise Accumulation in Trotter Circuits**

Increasing the number of Trotter steps improves the approximation of quantum dynamics, but also adds gates that can introduce noise. This project studies that tradeoff by simulating a four-spin transverse-field Ising model on two synthetic processor topologies: a five-qubit line and a nine-qubit square grid.

The benchmark compares exact evolution, ideal Trotter circuits, and noisy circuit execution. It measures observable error, state fidelity, circuit depth, CX count, and routing overhead across **108 configurations**, with **216 paired ideal/noisy sampled runs**.

## Physical model

The system is an open-boundary transverse-field Ising chain:

$$
H = -J\sum_{i=0}^{2} Z_i Z_{i+1} - g\sum_{i=0}^{3} X_i,
\qquad J = g = 1,\quad \hbar = 1.
$$

Evolution starts from $|0000\rangle$. First-order Trotter circuits apply the ZZ interaction block followed by the X-field block at each step. The benchmark uses **1, 2, and 4 Trotter steps** at nine evolution times from **0 to 2**, spaced by **0.25**.

An independently constructed dense Hamiltonian and SciPy matrix exponential provide the exact reference. The main observable is $\langle Z_0\rangle$; full-state fidelities provide a complementary measure of accuracy.

## Processor designs and settings

| Processor | Physical qubits | Connectivity |
| --- | ---: | --- |
| A | 5 | Linear chain with 4 links |
| B | 9 | Row-major 3 × 3 square grid with 12 links |

Both designs support CX gates in either direction along each link. They use the same native gate set and noise parameters so the comparison can examine connectivity and placement. These are synthetic processor models, not calibrated hardware backends.

| Setting | Value |
| --- | --- |
| Native gates | `rz`, `sx`, `x`, `cx` |
| Single-qubit depolarizing parameter | 0.001 after each `rz`, `sx`, or `x` |
| CX depolarizing parameter | 0.005 |
| Symmetric readout error | 0.01 |
| Shots per sampled circuit | 4,096 |
| Transpiler optimization level | 1 |
| Transpiler and simulator seeds | 42 |
| Placement modes | Optimized SABRE and fixed `[0, 1, 2, 3]` |
| SABRE settings | 20 trials and 3 layout iterations |
| Simulation method | Qiskit Aer density matrix |

Each ideal/noisy pair uses the same compiled native circuit. Final layouts determine logical measurement mappings and reduced-state ordering. Routing SWAPs are counted after routing and before native-gate translation. State fidelities are evaluated before readout noise.

The exported metrics distinguish Trotter error, gate-noise shifts, readout shifts, and sampling error. Signed contributions can cancel, so their absolute values should not be added to estimate total error. Sampled results include standard errors and Wilson 95% confidence intervals.

## Results

With optimized placement, both processors embed the four-spin chain without routing SWAPs and produce equivalent expected observable errors. The table below averages over positive evolution times; $t=0$ is excluded.

| Trotter steps | Circuit depth | CX gates | Mean Trotter error in Z₀ | Mean total expected error in Z₀ | Mean noisy fidelity to exact state |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 14 | 6 | 0.474071 | 0.464080 | 0.400257 |
| 2 | 25 | 12 | 0.105239 | 0.109397 | 0.536621 |
| 4 | 47 | 24 | 0.009643 | 0.022500 | 0.787998 |

**Four Trotter steps give the lowest mean expected observable error among the tested settings.** Although additional gates increase noise, the improvement in the Trotter approximation outweighs that cost over this range. No aggregate error crossover is observed for 1, 2, and 4 steps.

Fixed placement adds routing overhead on Processor B: 2, 2, and 4 SWAPs for the three step counts. At four steps, its mean expected observable error rises to **0.023254**, and its mean noisy fidelity to the exact state falls to **0.756093**. The fidelity change shows why a single observable does not capture every effect of circuit noise.

![Observable error and state fidelity across Trotter step counts](results/figures/error_vs_trotter_steps.png)

The [full report](report.md) explains the derivation, routing analysis, error decomposition, and architectural comparison. Numerical results are available in the [complete benchmark table](results/tables/benchmark_results.csv) and [summary table](results/tables/summary.csv).

## Running the project

The recorded environment uses Python 3.12.14, Qiskit 2.5.2, and Qiskit Aer 0.17.2 on Windows. Dependencies are pinned in [requirements.txt](requirements.txt). No external dataset or quantum service credentials are required.

From the repository root, create and activate an environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Linux or macOS, use `source .venv/bin/activate` to activate the environment.

Run the complete benchmark:

```powershell
python -c "from src.metrics import run_benchmark; run_benchmark()"
```

For the notebook workflow, open [main.ipynb](main.ipynb) in VS Code or a Jupyter notebook frontend, select the project environment, and run all cells. Notebook frontend software is installed separately. Rerunning the benchmark replaces the generated data, tables, and figures.

## Repository structure

```text
Qskit_Online/
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

| Location | Contents |
| --- | --- |
| `main.ipynb` | Notebook for running and exploring the study |
| `src/` | Hamiltonian construction, processor models, routing, metrics, and plotting |
| `processors/` | Connectivity and noise specifications for both processors |
| `data/raw/` | Experiment configuration, sampled counts, routing audits, research sources, and 108 compiled QPY circuits |
| `data/processed/` | Hamiltonian, exact reference states, observable reference table, and logical density matrices |
| `results/tables/` | 108 benchmark rows and 12 summary rows, with CSV and JSON summaries |
| `results/figures/` | Six figures covering processor topology, dynamics, accuracy, circuit resources, and placement |
| `report.md` | Detailed methods, analysis, references, and limitations |
| `assets/` | Directory for supporting equation images |

## Scope and limitations

The study uses one primary initial state, two processor graphs, one compiler seed, and three Trotter step counts. Its results do not establish a universal optimal step count or isolate qubit count from connectivity. Fixed-placement results also depend on physical-qubit labels.

The noise model includes gate depolarization and readout errors, but omits thermal relaxation, idle errors, and crosstalk. Extra grid connections carry no additional calibration cost in this model. Conclusions therefore apply to the specified synthetic experiment rather than physical hardware performance.
