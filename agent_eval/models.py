"""Data models for RTLLM v2.1 benchmark evaluation and dataset extraction."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DesignMeta:
    """Metadata representing a single benchmark circuit design in RTLLM v2.1."""

    design_name: str
    category: str
    subcategory: str
    target_filename: str
    prompt: str
    testbench_path: str
    verified_rtl_path: str
    module_name: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert design metadata to dictionary representation."""
        return {
            "design_name": self.design_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "target_filename": self.target_filename,
            "prompt": self.prompt,
            "testbench_path": self.testbench_path,
            "verified_rtl_path": self.verified_rtl_path,
            "module_name": self.module_name,
        }


@dataclass
class SimResult:
    """Outcome of simulating or linting a single generated design file."""

    design_name: str
    trial_name: str
    syntax_ok: bool
    func_ok: bool
    timed_out: bool = False
    return_code: int = 0
    compile_output: str = ""
    sim_output: str = ""
    elapsed_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert simulation result to dictionary representation."""
        return {
            "design_name": self.design_name,
            "trial_name": self.trial_name,
            "syntax_ok": self.syntax_ok,
            "func_ok": self.func_ok,
            "timed_out": self.timed_out,
            "return_code": self.return_code,
            "compile_output": self.compile_output,
            "sim_output": self.sim_output,
            "elapsed_sec": round(self.elapsed_sec, 4),
        }


@dataclass
class DesignSummary:
    """Evaluation summary for an individual design aggregated across trials."""

    design_name: str
    category: str
    subcategory: str
    total_trials: int
    syntax_successes: int
    func_successes: int
    syntax_rate: float
    func_rate: float
    trial_results: List[SimResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert design summary to dictionary representation."""
        return {
            "design_name": self.design_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "total_trials": self.total_trials,
            "syntax_successes": self.syntax_successes,
            "func_successes": self.func_successes,
            "syntax_rate": round(self.syntax_rate, 4),
            "func_rate": round(self.func_rate, 4),
            "trials": [t.to_dict() for t in self.trial_results],
        }


@dataclass
class BenchmarkSummary:
    """Overall summary report across all benchmark designs and trials."""

    simulator: str
    total_designs: int
    total_trials: int
    syntax_success_designs: int
    func_success_designs: int
    overall_syntax_pass_rate: float
    overall_func_pass_rate: float
    pass_at_k: Dict[str, float]
    category_breakdown: Dict[str, Dict[str, float]]
    designs: Dict[str, DesignSummary]

    def to_dict(self) -> Dict[str, Any]:
        """Convert full benchmark summary to dictionary representation."""
        return {
            "simulator": self.simulator,
            "total_designs": self.total_designs,
            "total_trials": self.total_trials,
            "syntax_success_designs": self.syntax_success_designs,
            "func_success_designs": self.func_success_designs,
            "overall_syntax_pass_rate": round(self.overall_syntax_pass_rate, 4),
            "overall_func_pass_rate": round(self.overall_func_pass_rate, 4),
            "pass_at_k": {k: round(v, 4) for k, v in self.pass_at_k.items()},
            "category_breakdown": self.category_breakdown,
            "designs": {k: v.to_dict() for k, v in self.designs.items()},
        }
