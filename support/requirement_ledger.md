# Requirement ledger and design decisions

Authority: user request and organizer clarifications; supplied QFF Phase 1 Master Guide (pages 1-3, 5, 7). Original planning files remain unchanged in the separate `PS_S3_Codex_Plan/` directory. No plan document is presented as a benchmark result.

| Requirement | Implementation decision / evidence target |
|---|---|
| Exactly PS-S3, four-spin TFIM | `project/src/problem.py`; independent NumPy/SciPy reference |
| A exactly 5, B exactly 9 qubits | Generated JSON, validated connected graphs |
| Architecture is participant designed | A line, B square grid; both bidirectional; justified before simulation |
| Basis rz/sx/x/cx, level 1, seed 42 | Shared JSON settings; preset pipeline with explicit SABRE trial counts |
| Depolarization .001/.005; readout .01 | All rz/sx/x receive 1q channel, cx receives 2q; identical A/B |
| 4096 shots; simulator seed 42 | Paired density-matrix Aer simulations on the same compiled native circuit |
| n=1,2,4 | All nine times in [0,2]; primary 0000, 0101 in correctness tests |
| Track final layout | Explicit physical density permutation and logical classical measurement register |
| SWAP audit before decomposition | Read-only post-routing checkpoint, complete operations and pass trace |
| Error and fidelity separation | Signed and absolute components; pre-readout density fidelities; finite-shot intervals |
| Required project tree | Only required named source modules; helper tests/scripts outside `project/` |
| Honest verification | Tests, fresh notebook, export checks, figure review and ZIP checks recorded after execution |
| No external submission | Local artifacts only; team details pending human input |

Defaults explicitly requested: J=g=1, open boundary, hbar=1, ZZ then X, times 0,.25,...,2, optimized primary and fixed [0,1,2,3] sensitivity. Official PDF mandates do not dictate these particular graph choices or a noise crossover.

Architecture candidates considered: line, branching tree, hub/star, ring with chords, square grid, heavy-hex family. Reject the star as the primary A because it lacks a four-node path and would build a routing disadvantage into this chain benchmark. The line is a minimal connected control. Choose B's planar 3x3 grid for transparent nearest-neighbor geometry and alternate paths, not to guarantee an advantage. A ring also embeds the chain, so chords are unnecessary for this experiment. Neither the guide's illustrative graph nor this grid is asserted to be a literal physical IBM device.

Graph limitations: the line/grid comparison changes qubit count, edge count and degree together. A chain is too small to use B's extra connectivity under a good layout. Fixed row-major labels make [0,1,2,3] a path on A but not B; that control demonstrates placement sensitivity and is not a fair best-layout hardware ranking. Uniform per-gate noise omits the physical engineering cost of grid degree, crosstalk, idle errors and calibration variation.

Compiler interpretation: optimization level remains 1; layout and routing stages are explicitly SABRE, with 20 trials and seed 42 to remove CPU-count-dependent trial defaults. A read-only analysis pass observes post-routing/pre-translation operations. The selected heuristic layout is called optimized in the requested comparison, but is not certified globally optimal.

No conflicts remain between the supplied guide and the user's clarifications. Optional Bell-state equation images in the guide are illustrative and unrelated to this TFIM task; the assets directory is preserved without irrelevant images.
