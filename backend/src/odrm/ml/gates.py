class GateFailureError(Exception):
    """Raised when a model fails to meet the acceptance criteria."""

    pass


GATES = {
    "ch4_conversion": {"min_r2": 0.95, "max_rmse": 0.03},
    "syngas_yield_mol_per_mol_ch4": {"min_r2": 0.95, "max_rmse": 0.15},
}


def evaluate_gates(metrics: dict[str, dict[str, float]]) -> None:
    """
    Evaluates the test metrics against the CTO-approved thresholds.
    Raises GateFailureError if any target fails.
    """
    for target, data in metrics.items():
        if target not in GATES:
            continue

        r2 = data["r2"]
        rmse = data["rmse"]
        thresholds = GATES[target]

        if r2 < thresholds["min_r2"]:
            raise GateFailureError(
                f"Target '{target}': R² of {r2:.3f} is below threshold {thresholds['min_r2']}"
            )

        if rmse > thresholds["max_rmse"]:
            raise GateFailureError(
                f"Target '{target}': RMSE of {rmse:.3f} is above threshold {thresholds['max_rmse']:.3f}"
            )
