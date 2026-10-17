"""Paired Aer simulations, error accounting, and complete local export pipeline."""
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import numpy as np
import pandas as pd
from qiskit import ClassicalRegister, qpy
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from .problem import exact_state, trotter_circuit, dense_terms, z0_expectation
from .processors import ROOT, load_processor, noise_model
from .routing import compile_circuit


def dump_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def circuit_metrics(circuit, audit):
    counts = circuit.count_ops()
    return {"depth": circuit.depth(), "cx_count": counts.get("cx", 0),
            "one_qubit_count": sum(counts.get(g, 0) for g in ["rz", "sx", "x"]),
            "routing_swaps": audit["routing_checkpoint"]["routing_swaps"],
            "final_basis_swaps": counts.get("swap", 0)}


def logical_density(sorted_physical_density, mapping):
    """Reorder saved ascending physical qubits into logical q3q2q1q0 order.

    Explicit index permutation avoids relying on Aer accepting unordered saves.
    Ancillas were traced out by save_density_matrix(sorted(mapping)).
    """
    positions = {p: i for i, p in enumerate(sorted(mapping))}
    indices = [sum(((logical >> q) & 1) << positions[mapping[q]] for q in range(4))
               for logical in range(16)]
    rho = np.asarray(sorted_physical_density, dtype=complex)
    return rho[np.ix_(indices, indices)]


def sampled_z0(counts):
    shots = sum(counts.values())
    return sum((1 if int(bits.replace(" ", ""), 2) % 2 == 0 else -1) * n
               for bits, n in counts.items()) / shots


def shot_uncertainty(z, shots):
    # Plug-in SE and a Wilson interval; Wilson remains meaningful at +/-1.
    se = float(np.sqrt(max(0., 1-z*z) / shots))
    p, k = (1+z)/2, 1.959963984540054
    denominator = 1 + k*k/shots
    center = (p + k*k/(2*shots)) / denominator
    half = k * np.sqrt(p*(1-p)/shots + k*k/(4*shots*shots)) / denominator
    return se, float(2*(center-half)-1), float(2*(center+half)-1)


def simulate_compiled(circuit, mapping, config, model=None):
    diagnostic = circuit.copy()
    diagnostic.save_density_matrix(sorted(mapping), label="rho")
    diagnostic.add_register(ClassicalRegister(4, "logical"))
    for logical, physical in enumerate(mapping):
        diagnostic.measure(physical, logical)
    simulator = AerSimulator(method="density_matrix", noise_model=model,
                             max_parallel_threads=1, max_parallel_experiments=1)
    result = simulator.run(diagnostic, shots=config["shots"],
                           seed_simulator=config["seed_simulator"]).result()
    if not result.success:
        raise RuntimeError(str(result))
    rho = logical_density(result.data(0)["rho"], mapping)
    counts = {k: int(v) for k, v in result.get_counts(0).items()}
    if sum(counts.values()) != config["shots"]:
        raise AssertionError("shot total mismatch")
    if not np.allclose(rho, rho.conj().T, atol=1e-10) or not np.isclose(np.trace(rho), 1):
        raise AssertionError("invalid density matrix")
    if np.linalg.eigvalsh(rho).min() < -1e-9:
        raise AssertionError("density matrix is not positive semidefinite")
    return rho, counts


def pure_fidelity(psi, rho):
    value = float(np.vdot(psi, rho @ psi).real)
    if not -1e-8 <= value <= 1+1e-8:
        raise AssertionError("fidelity outside physical range")
    return float(np.clip(value, 0, 1))


def accuracy_metrics(exact, ideal, ideal_rho, noisy_rho, ideal_counts, noisy_counts, config):
    ze, zi, zg = map(z0_expectation, [exact, ideal, noisy_rho])
    zr = (1 - 2 * config["noise"]["readout"]) * zg
    zs, zis = sampled_z0(noisy_counts), sampled_z0(ideal_counts)
    se, lo, hi = shot_uncertainty(zs, config["shots"])
    ise, ilo, ihi = shot_uncertainty(zis, config["shots"])
    compilation = pure_fidelity(ideal, ideal_rho)
    if compilation < 1 - 1e-8:
        raise AssertionError(f"logical state changed during compilation: {compilation}")
    return {"exact_z0": ze, "ideal_z0": zi, "ideal_sampled_z0": zis,
            "gate_noisy_z0": zg, "expected_readout_z0": zr, "measured_z0": zs,
            "standard_error": se, "wilson95_low": lo, "wilson95_high": hi,
            "ideal_standard_error": ise, "ideal_wilson95_low": ilo, "ideal_wilson95_high": ihi,
            "expected_standard_error": float(np.sqrt(max(0, 1-zr*zr)/config["shots"])),
            "trotter_error": abs(zi-ze), "gate_noise_shift": abs(zg-zi),
            "readout_shift": abs(zr-zg), "sampling_shift": abs(zs-zr),
            "total_expected_error": abs(zr-ze), "total_sampled_error": abs(zs-ze),
            "signed_trotter_error": zi-ze, "signed_gate_noise_shift": zg-zi,
            "signed_readout_shift": zr-zg, "signed_sampling_shift": zs-zr,
            "algorithm_fidelity": float(np.clip(abs(np.vdot(exact, ideal))**2, 0, 1)),
            "noisy_fidelity_to_trotter": pure_fidelity(ideal, noisy_rho),
            "noisy_fidelity_to_exact": pure_fidelity(exact, noisy_rho),
            "compiled_ideal_fidelity": compilation}


def environment():
    names = ["qiskit", "qiskit-aer", "numpy", "scipy", "pandas", "matplotlib", "networkx",
             "nbformat", "nbclient", "ipykernel", "pytest"]
    return {"python": platform.python_version(), "platform": platform.platform(),
            "packages": {name: importlib.metadata.version(name) for name in names}}


def run_benchmark(root=ROOT, progress=True):
    root = Path(root)
    for folder in ["data/raw/circuits", "data/processed", "results/tables", "results/figures",
                   "assets/qff_phase1_latex_images"]:
        (root / folder).mkdir(parents=True, exist_ok=True)
    configs = [load_processor(name, root) for name in ["A", "B"]]
    times, steps = np.linspace(0, 2, 9), [1, 2, 4]
    metadata = {"problem": "PS-S3", "J": 1., "g": 1., "initial_state": "0000",
                "times": times.tolist(), "steps": steps, "layouts": ["optimized", "fixed"],
                "processors": configs, "environment": environment(),
                "convention": "Noise after every rz/sx/x and cx; no idle or thermal noise. Save before measurement.",
                "summary": "Arithmetic means over eight positive times, separately for each processor/layout/n.",
                "compiler": "Preset level 1, SABRE; optimized layout uses 20 layout/swap trials, 3 iterations; seed 42."}
    dump_json(root / "data/raw/experiment_config.json", metadata)
    hzz, hx = dense_terms()
    np.save(root / "data/processed/hamiltonian.npy", hzz+hx)
    exacts = [exact_state(float(t)) for t in times]
    np.save(root / "data/processed/exact_states.npy", np.array(exacts))
    pd.DataFrame({"time": times, "exact_z0": [z0_expectation(s) for s in exacts]}).to_csv(
        root / "data/processed/exact_reference.csv", index=False)
    rows, counts, audits, states = [], {}, {}, {}
    for config in configs:
        for layout in metadata["layouts"]:
            for n in steps:
                for t, exact in zip(times, exacts):
                    key = f"{config['name']}_{layout}_n{n}_t{t:.2f}"
                    source = trotter_circuit(float(t), n)
                    ideal = np.asarray(Statevector.from_instruction(source).data)
                    compiled, mapping, audit = compile_circuit(source, config, layout)
                    circuit_path = root / "data/raw/circuits" / f"{key}.qpy"
                    with circuit_path.open("wb") as stream:
                        qpy.dump(compiled, stream)
                    audit["native_circuit_sha256"] = hashlib.sha256(circuit_path.read_bytes()).hexdigest()
                    irho, icounts = simulate_compiled(compiled, mapping, config)
                    nrho, ncounts = simulate_compiled(compiled, mapping, config, noise_model(config))
                    row = {"case_id": key, "processor": config["name"], "layout_mode": layout,
                           "time": float(t), "steps": n, "initial_state": "0000", "J": 1., "g": 1.,
                           "shots": config["shots"], "logical_to_physical": json.dumps(mapping),
                           **circuit_metrics(compiled, audit),
                           **accuracy_metrics(exact, ideal, irho, nrho, icounts, ncounts, config)}
                    rows.append(row)
                    counts[key] = {"ideal": icounts, "noisy": ncounts}
                    audits[key] = audit
                    states[key + "_ideal"] = irho
                    states[key + "_gate_noisy"] = nrho
                if progress:
                    print(f"Completed {config['name']} / {layout} / n={n}: {len(rows)}/108", flush=True)
    frame = pd.DataFrame(rows)
    if len(frame) != 108 or frame.case_id.nunique() != 108 or frame.isna().any().any():
        raise AssertionError("incomplete grid")
    frame.to_csv(root / "results/tables/benchmark_results.csv", index=False)
    columns = ["depth", "cx_count", "one_qubit_count", "routing_swaps", "trotter_error",
               "gate_noise_shift", "readout_shift", "total_expected_error", "total_sampled_error",
               "algorithm_fidelity", "noisy_fidelity_to_trotter", "noisy_fidelity_to_exact"]
    summary = frame[frame.time > 0].groupby(["processor", "layout_mode", "steps"])[columns].mean().reset_index()
    summary.to_csv(root / "results/tables/summary.csv", index=False)
    dump_json(root / "results/tables/summary.json", {"environment": environment(),
               "aggregation": metadata["summary"], "rows": summary.to_dict(orient="records")})
    dump_json(root / "data/raw/counts.json", counts)
    dump_json(root / "data/raw/routing_audit.json", audits)
    np.savez_compressed(root / "data/processed/logical_density_matrices.npz", **states)
    from .visualization import plot_benchmarks, topology
    for config in configs:
        topology(config, root / "results/figures" / f"processor_{config['name']}_topology.png")
    plot_benchmarks(frame, root / "results/figures")
    return frame, summary
