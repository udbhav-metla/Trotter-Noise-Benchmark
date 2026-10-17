"""Independent physics, routing, noise and export contract checks."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scipy.linalg import expm
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, Operator

ROOT = Path(__file__).resolve().parents[2] / "project"
sys.path.insert(0, str(ROOT))
from src.problem import hamiltonian, dense_terms, initial_state, exact_state, trotter_circuit, z0_expectation
from src.processors import load_processor, validate_processor, noise_model
from src.routing import compile_circuit, validate_compiled
from src.metrics import simulate_compiled, pure_fidelity, sampled_z0, shot_uncertainty


def test_hamiltonian():
    hzz, hx = dense_terms()
    h = hamiltonian().to_matrix()
    assert h.shape == (16, 16)
    np.testing.assert_allclose(h, h.conj().T)
    np.testing.assert_allclose(h, hzz + hx)
    assert len(hamiltonian()) == 7


@pytest.mark.parametrize("bits", ["0000", "0101"])
def test_matrix_product_signs_order_and_convergence(bits):
    hzz, hx = dense_terms()
    for n in [1, 2, 4]:
        t = .37
        u = np.linalg.matrix_power(expm(-1j*hx*t/n) @ expm(-1j*hzz*t/n), n)
        # Full unitary catches errors hidden by the primary basis state's first ZZ layer.
        circuit = trotter_circuit(t, n)
        np.testing.assert_allclose(Operator(circuit).data, u, atol=1e-12)
        state = Statevector.from_instruction(trotter_circuit(t, n, bits)).data
        np.testing.assert_allclose(state, u @ initial_state(bits), atol=1e-12)
        np.testing.assert_allclose(Statevector.from_instruction(trotter_circuit(0, n, bits)).data,
                                   initial_state(bits), atol=1e-12)
        np.testing.assert_allclose(exact_state(0, bits), initial_state(bits))
    assert np.isclose(np.linalg.norm(exact_state(2, bits)), 1)
    exact = exact_state(.1, bits)
    errors = [1-abs(np.vdot(exact, Statevector.from_instruction(trotter_circuit(.1, n, bits)).data))**2
              for n in [1, 2, 4]]
    assert errors[0] > errors[1] > errors[2] > 0


def test_endianness():
    assert z0_expectation(initial_state("0001")) == -1
    assert z0_expectation(initial_state("1000")) == 1


@pytest.mark.parametrize("args", [(-1, 1), (np.nan, 1), (.1, 0), (.1, 1.5), (.1, True)])
def test_invalid_circuit_inputs(args):
    with pytest.raises(ValueError):
        trotter_circuit(*args)


@pytest.mark.parametrize("bits", ["010", "00000", "abcd", "0020"])
def test_invalid_bits(bits):
    with pytest.raises(ValueError):
        initial_state(bits)


def test_graph_noise_parity_and_rejections():
    a, b = load_processor("A"), load_processor("B")
    for cfg in [a, b]:
        graph = validate_processor(cfg)
        assert len(graph) == cfg["num_qubits"]
    assert a["noise"] == b["noise"]
    def channel_spec(config):
        model = noise_model(config).to_dict()
        for error in model["errors"]:
            error.pop("id", None)  # Aer assigns random object IDs; compare the actual channels.
        return model
    assert channel_spec(a) == channel_spec(b)
    for mutate in [lambda c: c["undirected_edges"].append([0, 1]),
                   lambda c: c["directed_cx_edges"].pop(),
                   lambda c: c["noise"].update(cx=.01),
                   lambda c: c.update(num_qubits=6)]:
        cfg = copy.deepcopy(a)
        mutate(cfg)
        with pytest.raises(ValueError):
            validate_processor(cfg)


@pytest.mark.parametrize("processor", ["A", "B"])
@pytest.mark.parametrize("layout", ["optimized", "fixed"])
@pytest.mark.parametrize("bits", ["0000", "0101"])
def test_compilation_preserves_logical_state(processor, layout, bits):
    cfg = load_processor(processor)
    circuit = trotter_circuit(.73, 4, bits)
    compiled, mapping, audit = compile_circuit(circuit, cfg, layout)
    validate_compiled(compiled, cfg)
    rho, counts = simulate_compiled(compiled, mapping, cfg)
    psi = Statevector.from_instruction(circuit).data
    assert pure_fidelity(psi, rho) > 1-1e-10
    assert sum(counts.values()) == 4096
    assert audit["routing_checkpoint"]["routing_swaps"] == sum(
        op["gate"] == "swap" for op in audit["routing_checkpoint"]["operations"])
    assert audit["final_ops"].get("swap", 0) == 0
    if processor == "B" and layout == "fixed":
        assert audit["routing_checkpoint"]["routing_swaps"] > 0
    # Replay the pre-translation circuit, including its phase, to validate the audit.
    checkpoint = audit["routing_checkpoint"]
    replay = QuantumCircuit(checkpoint["num_qubits"])
    replay.global_phase = checkpoint["global_phase"]
    for op in checkpoint["operations"]:
        getattr(replay, op["gate"])(*op["params"], *op["qubits"])
    np.testing.assert_allclose(Statevector.from_instruction(replay).data,
                               Statevector.from_instruction(compiled).data, atol=1e-10)


def test_nontrivial_mapping_with_asymmetric_state():
    cfg = load_processor("B")
    source = QuantumCircuit(4)
    for q in range(4):
        source.ry(.2 + .31*q, q)
        source.rz(.17*q, q)
    source.cx(0, 3)
    source.cx(1, 2)
    source.cx(0, 2)
    compiled, mapping, audit = compile_circuit(source, cfg, "fixed")
    assert mapping != [0, 1, 2, 3]
    rho, counts = simulate_compiled(compiled, mapping, cfg)
    psi = Statevector.from_instruction(source).data
    assert pure_fidelity(psi, rho) > 1-1e-10
    assert abs(sampled_z0(counts) - z0_expectation(psi)) < .06


def test_zero_and_readout_only_noise():
    cfg = load_processor("A")
    source = trotter_circuit(.4, 2, "0101")
    compiled, mapping, _ = compile_circuit(source, cfg)
    rho, _ = simulate_compiled(compiled, mapping, cfg, noise_model(cfg, gates=False, readout=False))
    assert pure_fidelity(Statevector.from_instruction(source).data, rho) > 1-1e-10
    zero, mapping, _ = compile_circuit(trotter_circuit(0, 1), cfg)
    rho, counts = simulate_compiled(zero, mapping, cfg, noise_model(cfg, gates=False))
    assert z0_expectation(rho) == pytest.approx(1)
    assert abs(sampled_z0(counts)-.98) < 6*np.sqrt((1-.98**2)/4096)
    # Readout acts only on classical counts: gate density must be identical.
    rg, _ = simulate_compiled(compiled, compiled.layout.final_index_layout(), cfg,
                               noise_model(cfg, readout=False))
    rr, _ = simulate_compiled(compiled, compiled.layout.final_index_layout(), cfg, noise_model(cfg))
    np.testing.assert_allclose(rg, rr, atol=1e-12)


def test_uncertainty_boundaries():
    se, lo, hi = shot_uncertainty(1, 4096)
    assert se == 0 and lo < 1 and hi == pytest.approx(1)
    assert shot_uncertainty(0, 4096)[0] == 1/64


def test_known_depolarizing_attenuation():
    cfg = load_processor("A")
    circuit = QuantumCircuit(5)
    circuit.x(0)
    rho, _ = simulate_compiled(circuit, [0, 1, 2, 3], cfg, noise_model(cfg, readout=False))
    assert z0_expectation(rho) == pytest.approx(-.999, abs=1e-12)
    circuit.cx(0, 1)
    rho, _ = simulate_compiled(circuit, [0, 1, 2, 3], cfg, noise_model(cfg, readout=False))
    assert z0_expectation(rho) == pytest.approx(-.999 * .995, abs=1e-12)
    assert set(noise_model(cfg).noise_instructions) == {"rz", "sx", "x", "cx", "measure"}


def test_export_completeness():
    path = ROOT / "results/tables/benchmark_results.csv"
    if not path.exists():
        pytest.skip("benchmark export gate runs after complete grid")
    frame = pd.read_csv(path)
    counts = json.loads((ROOT / "data/raw/counts.json").read_text())
    audits = json.loads((ROOT / "data/raw/routing_audit.json").read_text())
    assert len(frame) == frame.case_id.nunique() == 108
    assert not frame.isna().any().any()
    assert set(frame.case_id) == set(counts) == set(audits)
    matrices = np.load(ROOT / "data/processed/logical_density_matrices.npz")
    assert len(matrices.files) == 216
    for row in frame.itertuples():
        assert sum(counts[row.case_id]["ideal"].values()) == 4096
        assert sum(counts[row.case_id]["noisy"].values()) == 4096
        assert row.compiled_ideal_fidelity > 1-1e-8
        assert sampled_z0(counts[row.case_id]["noisy"]) == pytest.approx(row.measured_z0)
        assert z0_expectation(matrices[row.case_id + "_gate_noisy"]) == pytest.approx(row.gate_noisy_z0)
        saved = ROOT / "data/raw/circuits" / f"{row.case_id}.qpy"
        assert hashlib.sha256(saved.read_bytes()).hexdigest() == audits[row.case_id]["native_circuit_sha256"]
        signed = row.signed_trotter_error + row.signed_gate_noise_shift + row.signed_readout_shift
        assert abs(signed) == pytest.approx(row.total_expected_error)
        assert abs(signed + row.signed_sampling_shift) == pytest.approx(row.total_sampled_error)
    summary = pd.read_csv(ROOT / "results/tables/summary.csv")
    assert len(summary) == 12
    for column in ["total_expected_error", "noisy_fidelity_to_exact"]:
        expected = frame[frame.time > 0].groupby(["processor", "layout_mode", "steps"])[column].mean().values
        np.testing.assert_allclose(summary[column], expected)
    for filename in ["processor_A_topology", "processor_B_topology", "z0_time_evolution",
                     "error_vs_trotter_steps", "depth_cx_swap_comparison", "layout_sensitivity"]:
        assert (ROOT / "results/figures" / f"{filename}.png").stat().st_size > 10000
