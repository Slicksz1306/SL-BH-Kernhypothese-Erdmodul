"""Numerical policy ONLY for normalized symmetric transport-matrix checks.

Matrices are divided by their maximum absolute entry. 1e-12 absolute plus
1e-10 relative is a conservative binary64 roundoff envelope (not measurement
uncertainty). Eigenvalues inside the envelope are unresolved, NOT repaired or
certified positive. Mass constraints and ledger sums instead use exact rationals.
"""
MATRIX_ATOL = 1e-12
MATRIX_RTOL = 1e-10


def matrix_threshold() -> float:
    return MATRIX_ATOL + MATRIX_RTOL
