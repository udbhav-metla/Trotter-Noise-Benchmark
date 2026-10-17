"""Level-1 compilation with an explicit pre-translation SWAP audit."""
from qiskit.transpiler import AnalysisPass, PassManager
from qiskit.transpiler.passes import SabreLayout, SabreSwap
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from .processors import coupling_map


class RoutingCheckpoint(AnalysisPass):
    """Read-only post-routing checkpoint: does not change the compiler DAG."""
    def __init__(self, audit):
        super().__init__()
        self.audit = audit

    def run(self, dag):
        operations = []
        for node in dag.topological_op_nodes():
            operations.append({"gate": node.op.name,
                               "qubits": [dag.find_bit(q).index for q in node.qargs],
                               "params": [float(p) for p in node.op.params]})
        self.audit["routing_checkpoint"] = {
            "stage": "post_routing_before_translation", "num_qubits": dag.num_qubits(),
            "depth": dag.depth(), "operations": operations,
            "routing_swaps": sum(o["gate"] == "swap" for o in operations),
            "global_phase": float(dag.global_phase)}


def validate_compiled(circuit, config):
    if circuit.num_qubits != config["num_qubits"]:
        raise AssertionError("physical budget mismatch")
    edges = set(map(tuple, config["directed_cx_edges"]))
    for instruction in circuit.data:
        name = instruction.operation.name
        if name not in config["basis_gates"]:
            raise AssertionError(f"non-native operation {name}")
        if name == "cx" and tuple(circuit.find_bit(q).index for q in instruction.qubits) not in edges:
            raise AssertionError("CX outside directed coupling map")


def compile_circuit(circuit, config, layout_mode="optimized"):
    if layout_mode not in ["optimized", "fixed"]:
        raise ValueError("layout_mode must be optimized or fixed")
    if circuit.count_ops().get("swap", 0):
        raise ValueError("source SWAPs would confound routing-only SWAP counts")
    cmap = coupling_map(config)
    audit = {"passes": [], "source_swaps": 0, "layout_mode": layout_mode,
             "sabre_trials": {"layout_trials": 20, "swap_trials": 20, "max_iterations": 3}}
    pm = generate_preset_pass_manager(
        optimization_level=config["optimization_level"], basis_gates=config["basis_gates"],
        coupling_map=cmap, seed_transpiler=config["seed_transpiler"],
        initial_layout=[0, 1, 2, 3] if layout_mode == "fixed" else None,
        layout_method="sabre", routing_method="sabre")
    if layout_mode == "optimized":
        # Fix trial counts, which otherwise depend on host CPU count.
        # SabreLayout also applies its selected routing; the checkpoint follows it.
        pm.layout = PassManager(SabreLayout(cmap, seed=config["seed_transpiler"],
                                          max_iterations=3, swap_trials=20, layout_trials=20))
    pm.routing = PassManager(SabreSwap(cmap, heuristic="decay", seed=config["seed_transpiler"], trials=20))
    pm.post_routing = PassManager(RoutingCheckpoint(audit))
    def callback(**kwargs):
        dag = kwargs["dag"]
        audit["passes"].append({"index": kwargs["count"], "pass": type(kwargs["pass_"]).__name__,
                                 "ops": dict(dag.count_ops()), "depth": dag.depth()})
    compiled = pm.run(circuit, callback=callback)
    validate_compiled(compiled, config)
    mapping = list(compiled.layout.final_index_layout(filter_ancillas=True))
    if len(mapping) != 4 or len(set(mapping)) != 4:
        raise AssertionError("invalid final logical mapping")
    audit["initial_logical_to_physical"] = list(compiled.layout.initial_index_layout(filter_ancillas=True))
    audit["final_logical_to_physical"] = mapping
    audit["final_ops"] = dict(compiled.count_ops())
    if "routing_checkpoint" not in audit:
        raise AssertionError("routing checkpoint did not run")
    return compiled, mapping, audit
