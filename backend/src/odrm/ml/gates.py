class GateFailureError(Exception):
    """Raised when a model fails to meet the acceptance criteria."""
    pass

# CTO-approved thresholds from SPRINT_2_PLAN.md
GATES = {
    "ch4_conversion": {
        "min_r2": 0.95,
        "max_rmse": 0.03
    },
    "syngas_yield_mol_per_mol_ch4": {
        "min_r2": 0.95,
        "max_rmse": 0.15
    }
}

def evaluate_gates(metrics: dict) -> None:
    """
    Evaluates the test metrics against the CTO-approved thresholds.
    Raises GateFailureError if any target fails.
    """
    for target, thresholds in GATES.items():
        if target not in metrics:
            raise GateFailureError(f"Missing metrics for target: {target}")
            
        r2 = metrics[target]["r2"]
        rmse = metrics[target]["rmse"]
        
        if r2 < thresholds["min_r2"]:
            raise GateFailureError(
                f"Target '{target}': R² of {r2:.3f} is below threshold {thresholds['min_r2']}"
            )
            
        if rmse > thresholds["max_rmse"]:
            raise GateFailureError(
                f"Target '{target}': RMSE of {rmse:.3f} is above threshold {thresholds['max_rmse']:.3f}"
            )