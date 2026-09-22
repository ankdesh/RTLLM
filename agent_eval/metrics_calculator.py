"""Metrics calculator for computing pass@k, syntax rates, and category statistics."""

import logging
from typing import Dict, Iterable, List, Optional
from scipy.special import comb  # type: ignore[import-untyped]

from agent_eval.models import BenchmarkSummary, DesignMeta, DesignSummary, SimResult

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Computes unbiased pass@k estimators and benchmark success metrics for hardware generation."""

    @staticmethod
    def estimate_pass_at_k(num_samples: int, num_correct: int, k: int) -> float:
        """Calculate unbiased pass@k metric using hypergeometric combinations.

        Formula:
            pass@k = 1 - comb(n - c, k) / comb(n, k)

        Args:
            num_samples: Total number of trials evaluated (n).
            num_correct: Number of successful trials (c).
            k: Evaluation threshold (k <= n).

        Returns:
            Calculated pass@k probability in [0.0, 1.0].
        """
        if num_samples <= 0:
            raise ValueError(f"num_samples must be positive, got {num_samples}")
        if num_correct < 0:
            raise ValueError(f"num_correct cannot be negative, got {num_correct}")
        if k <= 0:
            raise ValueError(f"k must be positive, got {k}")
        if k > num_samples:
            logger.warning("Requested k=%d greater than total samples n=%d; returning 0.0", k, num_samples)
            return 0.0

        if num_correct == 0:
            return 0.0
        if num_samples - num_correct < k:
            return 1.0

        comb_total = comb(num_samples, k)
        if comb_total == 0:
            return 0.0

        comb_failed = comb(num_samples - num_correct, k)
        return float(1.0 - (comb_failed / comb_total))

    def compute_benchmark_summary(
        self,
        simulator_name: str,
        catalog: List[DesignMeta],
        results: Dict[str, List[SimResult]],
        k_values: Optional[Iterable[int]] = None,
    ) -> BenchmarkSummary:
        """Aggregate per-design and per-trial results into full benchmark statistics.

        Args:
            simulator_name: Name of simulator used.
            catalog: List of all 50 design metadata objects.
            results: Mapping from design_name to list of SimResult (one per trial).
            k_values: List of k thresholds for pass@k (defaults to [1, 3, 5]).

        Returns:
            BenchmarkSummary containing global, per-category, and per-design metrics.
        """
        if k_values is None:
            k_values = [1, 3, 5]

        design_summaries: Dict[str, DesignSummary] = {}
        category_data: Dict[str, Dict[str, int]] = {}

        total_syntax_pass_designs = 0
        total_func_pass_designs = 0
        max_trials = 0

        for meta in catalog:
            d_name = meta.design_name
            cat = meta.category
            subcat = meta.subcategory

            trial_list = results.get(d_name, [])
            n_trials = len(trial_list)
            if n_trials > max_trials:
                max_trials = n_trials

            syntax_succ = sum(1 for r in trial_list if r.syntax_ok)
            func_succ = sum(1 for r in trial_list if r.func_ok)

            syntax_rate = (syntax_succ / n_trials) if n_trials > 0 else 0.0
            func_rate = (func_succ / n_trials) if n_trials > 0 else 0.0

            if syntax_succ > 0:
                total_syntax_pass_designs += 1
            if func_succ > 0:
                total_func_pass_designs += 1

            design_summaries[d_name] = DesignSummary(
                design_name=d_name,
                category=cat,
                subcategory=subcat,
                total_trials=n_trials,
                syntax_successes=syntax_succ,
                func_successes=func_succ,
                syntax_rate=syntax_rate,
                func_rate=func_rate,
                trial_results=trial_list,
            )

            # Accumulate category level counts
            if cat not in category_data:
                category_data[cat] = {
                    "total_designs": 0,
                    "syntax_pass_designs": 0,
                    "func_pass_designs": 0,
                }
            category_data[cat]["total_designs"] += 1
            if syntax_succ > 0:
                category_data[cat]["syntax_pass_designs"] += 1
            if func_succ > 0:
                category_data[cat]["func_pass_designs"] += 1

        total_designs = len(catalog)
        overall_syntax_rate = (
            (total_syntax_pass_designs / total_designs) if total_designs > 0 else 0.0
        )
        overall_func_rate = (
            (total_func_pass_designs / total_designs) if total_designs > 0 else 0.0
        )

        # Calculate pass@k across all designs
        pass_at_k: Dict[str, float] = {}
        for k in k_values:
            if k <= max_trials and max_trials > 0:
                scores = [
                    self.estimate_pass_at_k(
                        num_samples=d.total_trials,
                        num_correct=d.func_successes,
                        k=k,
                    )
                    for d in design_summaries.values()
                    if d.total_trials >= k
                ]
                pass_at_k[f"pass@{k}"] = (sum(scores) / len(scores)) if scores else 0.0

        # Calculate category breakdowns
        category_breakdown: Dict[str, Dict[str, float]] = {}
        for cat, data in category_data.items():
            c_total = data["total_designs"]
            c_syntax = data["syntax_pass_designs"]
            c_func = data["func_pass_designs"]
            category_breakdown[cat] = {
                "total_designs": float(c_total),
                "syntax_pass_rate": (c_syntax / c_total) if c_total > 0 else 0.0,
                "func_pass_rate": (c_func / c_total) if c_total > 0 else 0.0,
            }

        return BenchmarkSummary(
            simulator=simulator_name,
            total_designs=total_designs,
            total_trials=max_trials,
            syntax_success_designs=total_syntax_pass_designs,
            func_success_designs=total_func_pass_designs,
            overall_syntax_pass_rate=overall_syntax_rate,
            overall_func_pass_rate=overall_func_rate,
            pass_at_k=pass_at_k,
            category_breakdown=category_breakdown,
            designs=design_summaries,
        )
