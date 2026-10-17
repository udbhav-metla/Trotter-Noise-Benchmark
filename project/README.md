# Trotter Error vs Synthetic Device Noise

**An Architectural Study of Quantum Simulation Accuracy**
Qiskit Fall Fest Phase 1: **PS-S3 - Noise Accumulation in Trotter Circuits**

Completed local benchmark: 108 cases, 216 paired ideal/noisy Aer sampled runs, exact SciPy references, and a freshly executed notebook. Processor A is a five-qubit line; B is a nine-qubit square grid. Both implement the same four-spin open-boundary TFIM. No external dataset, credentials or processor download is needed.

## Setup and execution

Tested with Python 3.12.14, Qiskit 2.5.2 and Aer 0.17.2 on Windows. From this `project/` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
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
km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
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

| processor | layout_mode | steps | total_expected_error |
| --- | --- | --- | --- |
| A | fixed | 4 | 0.022500 |
| A | optimized | 4 | 0.022500 |
| B | fixed | 4 | 0.023254 |
| B | optimized | 4 | 0.022500 |

Optimized A/B maximum pointwise expected-error difference: 7.01e-16. See [report.md](report.md) for fidelity, routing, architecture reasoning and limitations. A chain can embed on a line, so extra connectivity need not improve this workload.

![Error and fidelity across tested steps](results/figures/error_vs_trotter_steps.png)

## Evidence and checks

- `data/raw/experiment_config.json`: exact settings, graph configs and executed environment.
- `data/raw/counts.json`: all ideal/noisy 4096-shot histograms.
- `data/raw/routing_audit.json` and `data/raw/circuits/`: pass traces, pre-translation operations, layouts, QPY native circuits and hashes.
- `data/raw/research_sources.json`: official/primary sources, access dates and design uses.
- `data/processed/`: Hamiltonian, exact states/reference table, and all logical ideal/noisy density matrices.
- `results/tables/`: 108-row metrics and 12-row positive-time summaries.
- `results/figures/`: six figures covering topology, dynamics, accuracy, resources and placement.

Verification: **27 passed in 4.13s**; fresh notebook **6 code cells**, no errors; CLI/notebook counts and benchmark CSV byte-identical on the tested environment. Finite-shot SE and Wilson intervals are exported. Summary tables exclude t=0. See separate verification support for tests, logs and commands.

## Limitations and submission checklist

The clean ZIP was also extracted into a different directory and its full 108-case grid rerun successfully, producing byte-identical benchmark CSV and raw counts. All six figures were visually inspected for readable labels, legends and axes.

One primary initial state, two chosen graphs, one compiler seed, and three n values cannot establish a universal optimum or pure qubit-count effect. Fixed placement depends on labels. Extra grid links have no calibration/crosstalk cost in this model. No quantum advantage or hardware-performance claim is made.

- [x] Local implementation, exact reference, complete A/B grid and exports.
- [x] Physics/routing/noise tests and fresh notebook execution.
- [ ] Team adds actual member names (not supplied) and reviews scientific conclusions.
- [ ] Team reviews AI-assistance attribution and event rules.
- [ ] Team submits the repository URL to the event portal when ready.

Source repository: https://github.com/udbhav-metla/Qskit_Online. No event-portal submission has been made. The supplied guide states October 14, 2026, 23:59 IST and https://qffsrmap2026.com/learning/hackathon; that recorded deadline is historical, not a claim about current submission availability. Codex assisted research, implementation, validation and documentation; no team identity has been invented.
