"""Independent dense reference and Qiskit first-order product formula.

Qiskit strings use q3 q2 q1 q0. The rightmost bit is logical qubit zero.
"""
import numbers
import numpy as np
from scipy.linalg import expm
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp


def initial_state(bits="0000"):
    if not isinstance(bits, str) or len(bits) != 4 or set(bits) - {"0", "1"}:
        raise ValueError("initial state must be four binary digits in q3q2q1q0 order")
    state = np.zeros(16, dtype=complex)
    state[int(bits, 2)] = 1
    return state


def hamiltonian(J=1.0, g=1.0):
    if not np.isfinite([J, g]).all():
        raise ValueError("J and g must be finite")
    return SparsePauliOp.from_list([(s, -J) for s in ["IIZZ", "IZZI", "ZZII"]]
                                 + [(s, -g) for s in ["IIIX", "IIXI", "IXII", "XIII"]])


def dense_terms(J=1.0, g=1.0):
    """Construct H independently with NumPy tensor products, not Qiskit gates."""
    if not np.isfinite([J, g]).all():
        raise ValueError("J and g must be finite")
    I = np.eye(2)
    X = np.array([[0, 1], [1, 0]])
    Z = np.diag([1, -1])
    def term(operators):
        result = np.array([[1.]])
        for q in reversed(range(4)):
            result = np.kron(result, operators.get(q, I))
        return result
    hzz = -J * sum(term({q: Z, q+1: Z}) for q in range(3))
    hx = -g * sum(term({q: X}) for q in range(4))
    return hzz, hx


def exact_state(t, bits="0000", J=1.0, g=1.0):
    if not np.isfinite(t) or t < 0:
        raise ValueError("time must be finite and nonnegative")
    hzz, hx = dense_terms(J, g)
    return expm(-1j * t * (hzz + hx)) @ initial_state(bits)


def trotter_circuit(t, steps, bits="0000", J=1.0, g=1.0):
    if isinstance(steps, bool) or not isinstance(steps, numbers.Integral) or steps < 1:
        raise ValueError("steps must be a positive integer")
    if not np.isfinite([t, J, g]).all() or t < 0:
        raise ValueError("time must be nonnegative and all parameters finite")
    initial_state(bits)
    qc = QuantumCircuit(4, name=f"tfim_n{steps}_t{t:g}")
    for q, bit in enumerate(reversed(bits)):
        if bit == "1":
            qc.x(q)
    if t == 0:
        return qc
    # R_P(theta) = exp(-i theta P/2). H has NEGATIVE coefficients.
    # Gates act ZZ first then X, so U_step = exp(-i H_X dt) exp(-i H_ZZ dt).
    for _ in range(steps):
        for q in range(3):
            qc.rzz(-2 * J * t / steps, q, q+1)
        for q in range(4):
            qc.rx(-2 * g * t / steps, q)
    return qc


def z0_expectation(state):
    data = np.asarray(state, dtype=complex)
    signs = 1 - 2 * (np.arange(16) % 2)
    probabilities = np.abs(data)**2 if data.ndim == 1 else np.diag(data).real
    return float(np.dot(signs, probabilities).real)
