"""Unit and property tests for pass@k and benchmark metric calculations."""

import pytest
from agent_eval.metrics_calculator import MetricsCalculator


def test_pass_at_k_basic() -> None:
    """Validate pass@k calculations against edge cases and known values."""
    calc = MetricsCalculator()

    # Zero successes -> 0.0
    assert calc.estimate_pass_at_k(num_samples=10, num_correct=0, k=1) == 0.0
    assert calc.estimate_pass_at_k(num_samples=5, num_correct=0, k=3) == 0.0

    # All successes -> 1.0
    assert calc.estimate_pass_at_k(num_samples=5, num_correct=5, k=1) == 1.0
    assert calc.estimate_pass_at_k(num_samples=5, num_correct=5, k=3) == 1.0

    # Pass@1 is identical to c / n
    for c in range(1, 6):
        assert pytest.approx(calc.estimate_pass_at_k(num_samples=5, num_correct=c, k=1)) == c / 5.0

    # Remaining failures fewer than k implies at least one success in sample
    # n=5, c=3 -> n-c=2. If k=3, any sample of 3 MUST contain at least one success -> 1.0
    assert calc.estimate_pass_at_k(num_samples=5, num_correct=3, k=3) == 1.0


def test_pass_at_k_validation_errors() -> None:
    """Validate error raising on improper inputs."""
    calc = MetricsCalculator()

    with pytest.raises(ValueError):
        calc.estimate_pass_at_k(num_samples=0, num_correct=0, k=1)

    with pytest.raises(ValueError):
        calc.estimate_pass_at_k(num_samples=5, num_correct=-1, k=1)

    with pytest.raises(ValueError):
        calc.estimate_pass_at_k(num_samples=5, num_correct=2, k=0)
