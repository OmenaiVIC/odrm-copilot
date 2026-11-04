import pytest
from odrm.ml.gates import evaluate_gates, GateFailureError

def test_gates_pass():
    """Test that a good model passes the gates."""
    # Good metrics
    metrics = {
        "ch4_conversion": {"r2": 0.98, "rmse": 0.02},
        "syngas_yield_mol_per_mol_ch4": {"r2": 0.97, "rmse": 0.10}
    }
    
    # Should not raise an exception
    evaluate_gates(metrics)

def test_gates_fail_r2():
    """Test that a low R2 fails the gate."""
    metrics = {
        "ch4_conversion": {"r2": 0.85, "rmse": 0.01}, # R2 is too low
        "syngas_yield_mol_per_mol_ch4": {"r2": 0.97, "rmse": 0.10}
    }
    
    with pytest.raises(GateFailureError, match="R² of 0.850 is below threshold 0.95"):
        evaluate_gates(metrics)

def test_gates_fail_rmse():
    """Test that a high RMSE fails the gate."""
    metrics = {
        "ch4_conversion": {"r2": 0.98, "rmse": 0.05}, # RMSE is too high (max 0.03)
        "syngas_yield_mol_per_mol_ch4": {"r2": 0.97, "rmse": 0.10}
    }
    
    with pytest.raises(GateFailureError, match="RMSE of 0.050 is above threshold 0.030"):
        evaluate_gates(metrics)