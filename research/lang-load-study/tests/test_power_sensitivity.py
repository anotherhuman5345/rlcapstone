"""The sensitivity tool must stay explicitly simulated and reproducible."""
import pytest

from analysis.power_sensitivity import simulate_power


def test_power_sensitivity_is_seeded_and_explicitly_simulated():
    a = simulate_power(20, 12, seed=7)
    assert a == simulate_power(20, 12, seed=7)
    assert a["simulation_only"] is True
    assert 0 <= a["detection_rate"] <= 1
    assert a["repetitions"] == 12


def test_power_sensitivity_rejects_invalid_parameters():
    with pytest.raises(ValueError):
        simulate_power(2, 100)
    with pytest.raises(ValueError):
        simulate_power(20, 100, stop_low=70)
    with pytest.raises(ValueError):
        simulate_power(20, 100, l2_percent=-110)


def test_zero_effect_does_not_always_register_as_significant():
    result = simulate_power(20, 100, l2_percent=0, seed=8)
    assert result["detection_rate"] < 0.2  # coarse check, no fixed power target
