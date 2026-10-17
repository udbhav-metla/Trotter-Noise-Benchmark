# Execution record

Local execution date: 2026-10-13 (Asia/Calcutta).

## Requirements and research

Read the user's pasted request, master plan, START_HERE, AGENTS, all eight numbered documents, and all seven pages of the supplied official PDF. Confirmed PS-S3, A/B only, graph-design freedom, exact qubit budgets, official shared noise/compiler settings, and required hierarchy. No dataset or processor files were downloaded. Primary technical sources and access dates are exported in the project.

Selected A=line and B=3x3 grid before benchmark execution. The rationale and assumptions are in `requirement_ledger.md`. Planning material remains separate and unchanged.

## Environment preparation

Windows sandbox startup failed before file reads (`permission path cannot be represented losslessly`). User-approved commands outside that sandbox were used for execution. Python 3.12.14's bundled runtime created a project-local virtual environment. Initial package downloads failed from network timeouts. Pip was upgraded inside that environment to 26.2.1 for resumable downloads; no global Python packages were changed.

## Static validation

Command: `python support/manage.py static`.

Observed: all eight Python source/support files parsed successfully. This is a syntax check, not a claim of numerical correctness.

## Environment verified

Installation completed in the isolated environment. `python -m pip check` reported "No broken requirements found." `python support/manage.py pin` recorded the tested versions in project/requirements.txt and the full environment in environment-freeze.txt. Qiskit 2.5.2 and Aer 0.17.2 imported successfully.

## Physics, graph, routing and noise validation

Command: `python support/manage.py test`.

The initial run found one test-comparison issue: Aer includes randomized object IDs in noise-model serialization. The test was corrected to omit only the IDs while comparing the complete channel definitions. No rates or scientific implementation were altered. The pre-benchmark outcome was 26 passed, with the export gate appropriately skipped before data existed.

Verified full-unitary product signs/order against independent SciPy exponentials, 0000/0101 time-zero behavior and small-time convergence, Z0 endianness, graph constraints, identical channels, explicit CX edges, asymmetric routed-state preservation, post-routing audit replay, known .999 and .995 depolarizing attenuation, readout-only behavior and finite-shot interval calculations.

## Complete benchmark

Command: `python support/manage.py run`.

Completed 108 cases and 216 paired sampled simulations. All per-case density, logical-state, native-edge and shot-total assertions passed. Minimum compiled ideal fidelity: 0.9999999999999984. Every ideal/noisy count total is 4096. Exported all native QPY circuits, their hashes, pass traces and routing checkpoints, ideal/noisy logical density matrices, independent exact references, CSV/JSON summaries and six plots.

## Fresh-kernel notebook

Command: `python support/manage.py notebook`.

Six code cells executed successfully with zero cell errors. The notebook re-ran all 108 cases. Both benchmark_results.csv and counts.json were byte-identical to the CLI run. After figure-label improvements, the latest notebook was again executed successfully with the same comparisons passing. The kernel was explicitly shut down after each run.

Jupyter emitted a transport warning about unencrypted TCP; this was a local kernel started by the local kernel manager, not a public notebook server. It did not cause cell errors. No numerical runtime warning was reported by the final test suite.

## Export and visual verification

Final command: `python support/manage.py test`.

Outcome: **27 passed in 4.13s**, no skips. Export checks include the unique 108-row grid, all counts, all 216 saved density matrices, recomputed Z0 values, every QPY hash, signed-error identities and positive-time summaries. The six figures were viewed directly, checking titles, labels, legends, intervals and clipping. The final three revised figures were inspected again. Overlapping A/B curves are explicitly labeled; SWAP axes use integer ticks.

Official guide pages 2, 3, 5 and 7 were rendered and visually checked in addition to text extraction of all seven pages.

## Documentation and packaging

Commands: `python support/manage.py documents`, then `python support/manage.py package`.

README and report were generated from the observed results and actual verification records. The clean project archive contains 138 files with the required hierarchy, excluding virtual environments, caches, planning material and helper scripts. The ZIP CRC check passed. Tests, scripts, logs and checksums are packaged separately as verification support.

## Relocated execution

Command: `python support/manage.py portability`.

Extracted the clean project ZIP into a new directory under the workspace and executed the entire 108-case grid there. Benchmark CSV and raw counts matched the originals byte for byte. No hard-coded project path was needed. The scientific results are portable within this tested environment; other operating systems and dependency versions have not been executed.

No unresolved execution blocker remains. Human work remains: supply actual team details, review/attribute AI assistance under event rules, and publish/submit when authorized. Nothing was published or submitted.

## Reverification for repository upload - 2026-10-17

The user authorized uploading to https://github.com/udbhav-metla/Qskit_Online. The existing main branch contained only its initial README. The required project/ hierarchy will remain intact, with supporting verification material in the separate support/ directory.

Fresh pytest result: **27 passed in 13.03s**. `pip check` again reported no broken requirements. A notebook attempt stalled inside the execution sandbox; its identified processes were stopped and the notebook was rerun outside the sandbox. The successful fresh-kernel run executed all six code cells with zero errors and regenerated byte-identical benchmark CSV and raw counts.

The required-file audit checks every mandatory file and directory, notebook schema/execution, 108 native circuit exports, six figures, and byte-for-byte archive consistency. Optional equation images are not required. Team member details remain unsupplied, and no event-portal submission is authorized by this upload request.
