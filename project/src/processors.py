"""Participant-designed graphs and a shared synthetic noise convention."""
import json
from pathlib import Path
import networkx as nx
from qiskit.transpiler import CouplingMap
from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError

ROOT = Path(__file__).resolve().parents[1]


def validate_processor(config):
    expected = {"A": 5, "B": 9}
    if config["name"] not in expected or config["num_qubits"] != expected[config["name"]]:
        raise ValueError("Processor A needs 5 and B needs 9 physical qubits")
    n = config["num_qubits"]
    edges = [tuple(e) for e in config["undirected_edges"]]
    if len(set(tuple(sorted(e)) for e in edges)) != len(edges):
        raise ValueError("duplicate undirected edge")
    if any(len(e) != 2 or any(type(v) is not int or not 0 <= v < n for v in e)
           or e[0] == e[1] for e in edges):
        raise ValueError("invalid edge")
    graph = nx.Graph()
    graph.add_nodes_from(range(n))
    graph.add_edges_from(edges)
    if not nx.is_connected(graph):
        raise ValueError("graph must be connected")
    directed = [tuple(e) for e in config["directed_cx_edges"]]
    wanted = {e for a, b in edges for e in [(a, b), (b, a)]}
    if len(directed) != len(wanted) or set(directed) != wanted:
        raise ValueError("both CX directions must be specified exactly once")
    if config["basis_gates"] != ["rz", "sx", "x", "cx"]:
        raise ValueError("unsupported basis")
    if config["noise"] != {"one_qubit": 0.001, "cx": 0.005, "readout": 0.01,
                           "one_qubit_gates": ["rz", "sx", "x"]}:
        raise ValueError("official synthetic noise settings required")
    for key, val in {"optimization_level": 1, "seed_transpiler": 42,
                     "seed_simulator": 42, "shots": 4096}.items():
        if config[key] != val:
            raise ValueError(f"incorrect {key}")
    return graph


def load_processor(name, root=ROOT):
    config = json.loads((Path(root) / "processors" / f"processor_{name}.json").read_text())
    validate_processor(config)
    return config


def coupling_map(config):
    return CouplingMap(config["directed_cx_edges"])


def noise_model(config, *, gates=True, readout=True):
    """Aer depolarizing parameter lambda: (1-lambda)rho + lambda I/2**n.

    RZ is noisy here by a common synthetic convention, not a physical calibration.
    gates/readout switches are for validation; the benchmark enables both.
    """
    model = NoiseModel(basis_gates=config["basis_gates"])
    noise = config["noise"]
    if gates:
        model.add_all_qubit_quantum_error(depolarizing_error(noise["one_qubit"], 1),
                                         noise["one_qubit_gates"])
        model.add_all_qubit_quantum_error(depolarizing_error(noise["cx"], 2), ["cx"])
    if readout:
        p = noise["readout"]
        model.add_all_qubit_readout_error(ReadoutError([[1-p, p], [p, 1-p]]))
    return model
