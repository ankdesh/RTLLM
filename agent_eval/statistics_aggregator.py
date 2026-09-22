"""Aggregator calculating level-by-level reflection statistics, recovery deltas, and tier metrics."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent_eval.framework_adapter import FrameworkTrajectory

# Mapping of designs to Complexity Tiers defined in RTLLM_AGENTIC_GUIDE.md
TIER_MAPPING: Dict[str, int] = {
    # Tier 1: Combinational Arithmetic
    "adder_8bit": 1, "adder_16bit": 1, "adder_32bit": 1, "adder_pipe_64bit": 1, "adder_bcd": 1,
    "sub_64bit": 1, "multi_8bit": 1, "multi_16bit": 1, "multi_booth_8bit": 1, "multi_pipe_4bit": 1,
    "multi_pipe_8bit": 1, "comparator_3bit": 1, "comparator_4bit": 1, "accu": 1,
    "fixed_point_adder": 1, "fixed_point_substractor": 1, "float_multi": 1, "div_16bit": 1,
    # Tier 2: Sequential Datapaths & Shifters
    "counter_12": 2, "JC_counter": 2, "ring_counter": 2, "up_down_counter": 2,
    "right_shifter": 2, "LFSR": 2, "barrel_shifter": 2,
    # Tier 3: Finite State Machines & Timing
    "fsm": 3, "sequence_detector": 3, "traffic_light": 3, "calendar": 3, "freq_div": 3,
    "freq_divbyeven": 3, "freq_divbyodd": 3, "freq_divbyfrac": 3, "signal_generator": 3,
    "square_wave": 3, "edge_detect": 3, "pulse_detect": 3, "synchronizer": 3,
    "width_8to16": 3, "parallel2serial": 3, "serial2parallel": 3,
    # Tier 4: Complex Subsystems & Handshakes
    "asyn_fifo": 4, "LIFObuffer": 4, "alu": 4, "pe": 4, "instr_reg": 4, "ROM": 4, "RAM": 4,
    "clkgenerator": 4, "radix2_div": 4,
}


@dataclass
class TierStats:
    """Metrics for an individual circuit complexity tier."""

    tier_id: int
    tier_name: str
    total_designs: int = 0
    solved_designs: int = 0
    solve_rate: float = 0.0
    avg_rounds_to_solve: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert tier stats to dictionary."""
        return {
            "tier_id": self.tier_id,
            "tier_name": self.tier_name,
            "total_designs": self.total_designs,
            "solved_designs": self.solved_designs,
            "solve_rate": round(self.solve_rate, 4),
            "avg_rounds_to_solve": round(self.avg_rounds_to_solve, 2),
        }


@dataclass
class BenchmarkReportData:
    """Consolidated benchmark analytics across all designs."""

    total_designs: int
    total_solved: int
    overall_solve_rate: float
    level_counts: Dict[str, int] = field(default_factory=dict)
    cumulative_pass_rates: Dict[str, float] = field(default_factory=dict)
    recovery_deltas: Dict[str, float] = field(default_factory=dict)
    tier_stats: Dict[int, TierStats] = field(default_factory=dict)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    avg_tokens_per_design: float = 0.0
    avg_tokens_per_solve: float = 0.0
    total_elapsed_sec: float = 0.0
    failure_breakdown: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report data to dictionary."""
        return {
            "total_designs": self.total_designs,
            "total_solved": self.total_solved,
            "overall_solve_rate": round(self.overall_solve_rate, 4),
            "level_counts": self.level_counts,
            "cumulative_pass_rates": {k: round(v, 4) for k, v in self.cumulative_pass_rates.items()},
            "recovery_deltas": {k: round(v, 4) for k, v in self.recovery_deltas.items()},
            "tier_stats": {t_id: stats.to_dict() for t_id, stats in self.tier_stats.items()},
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_design": round(self.avg_tokens_per_design, 1),
            "avg_tokens_per_solve": round(self.avg_tokens_per_solve, 1),
            "total_elapsed_sec": round(self.total_elapsed_sec, 2),
            "failure_breakdown": self.failure_breakdown,
        }


class BenchmarkStatisticsAggregator:
    """Computes multidimensional benchmark analytics from framework trajectories."""

    TIER_NAMES: Dict[int, str] = {
        1: "Tier 1: Combinational Arithmetic",
        2: "Tier 2: Sequential Datapaths & Shifters",
        3: "Tier 3: FSMs & Timing Circuits",
        4: "Tier 4: Complex Subsystems & Handshakes",
    }

    @classmethod
    def aggregate(cls, trajectories: List[FrameworkTrajectory]) -> BenchmarkReportData:
        """Aggregate trajectories into comprehensive benchmark statistics."""
        total = len(trajectories)
        if total == 0:
            return BenchmarkReportData(total_designs=0, total_solved=0, overall_solve_rate=0.0)

        solved_count = sum(1 for t in trajectories if t.solved)
        overall_rate = solved_count / total

        # 1. Level-by-level counts
        levels = ["L0_ZERO_SHOT", "L1_LINT", "L2_SIM", "L3_MULTI_TURN", "L4_MULTI_TURN", "L5_MULTI_TURN"]
        level_counts: Dict[str, int] = {lvl: 0 for lvl in levels}
        for t in trajectories:
            if t.solved and t.solved_level:
                # normalize level string
                matched = False
                for lvl in levels:
                    if lvl in t.solved_level or t.solved_level.startswith(lvl.split("_")[0]):
                        level_counts[lvl] += 1
                        matched = True
                        break
                if not matched:
                    level_counts["L3_MULTI_TURN"] += 1

        # 2. Cumulative pass rates
        cum_solves = 0
        cumulative_rates: Dict[str, float] = {}
        for lvl in levels:
            cum_solves += level_counts[lvl]
            cumulative_rates[lvl] = cum_solves / total

        # 3. Recovery deltas
        # Delta L0 -> L1: of designs failing L0, what % were saved by L1?
        failed_l0 = total - level_counts["L0_ZERO_SHOT"]
        delta_l0_to_l1 = (level_counts["L1_LINT"] / failed_l0) if failed_l0 > 0 else 0.0

        # Delta L1 -> L2: of designs failing L0 and L1, what % were saved by L2?
        failed_l1 = failed_l0 - level_counts["L1_LINT"]
        delta_l1_to_l2 = (level_counts["L2_SIM"] / failed_l1) if failed_l1 > 0 else 0.0

        # Delta L2 -> L3+: of designs failing up to L2, what % were saved by multi-turn L3+?
        failed_l2 = failed_l1 - level_counts["L2_SIM"]
        multi_turn_solves = sum(level_counts[lvl] for lvl in levels[3:])
        delta_l2_to_l3_plus = (multi_turn_solves / failed_l2) if failed_l2 > 0 else 0.0

        recovery_deltas = {
            "delta_l0_to_l1 (Lint Recovery)": delta_l0_to_l1,
            "delta_l1_to_l2 (Sim Recovery)": delta_l1_to_l2,
            "delta_l2_to_l3_plus (Multi-Turn Recovery)": delta_l2_to_l3_plus,
        }

        # 4. Complexity Tier Breakdown
        tier_data: Dict[int, Dict[str, Any]] = {
            i: {"total": 0, "solved": 0, "rounds_sum": 0} for i in range(1, 5)
        }
        for t in trajectories:
            tier_id = TIER_MAPPING.get(t.design_name, 1)
            tier_data[tier_id]["total"] += 1
            if t.solved:
                tier_data[tier_id]["solved"] += 1
                tier_data[tier_id]["rounds_sum"] += len(t.steps)

        tier_stats: Dict[int, TierStats] = {}
        for tier_id, d in tier_data.items():
            tot = d["total"]
            sol = d["solved"]
            rate = (sol / tot) if tot > 0 else 0.0
            avg_rounds = (d["rounds_sum"] / sol) if sol > 0 else 0.0
            tier_stats[tier_id] = TierStats(
                tier_id=tier_id,
                tier_name=cls.TIER_NAMES[tier_id],
                total_designs=tot,
                solved_designs=sol,
                solve_rate=rate,
                avg_rounds_to_solve=avg_rounds,
            )

        # 5. Token & Time Analytics
        total_p_tokens = sum(t.total_prompt_tokens for t in trajectories)
        total_c_tokens = sum(t.total_completion_tokens for t in trajectories)
        total_tok = total_p_tokens + total_c_tokens
        avg_per_design = total_tok / total
        avg_per_solve = (total_tok / solved_count) if solved_count > 0 else 0.0
        total_elapsed = sum(t.total_elapsed_sec for t in trajectories)

        # 6. Failure Taxonomy
        failure_breakdown: Dict[str, int] = {
            "Syntax / Lint Unresolved": 0,
            "Functional Mismatch": 0,
            "Timeout / Infinite Loop": 0,
        }
        for t in trajectories:
            if not t.solved:
                reason = (t.failure_reason or "").lower()
                if "timed out" in reason or "timeout" in reason:
                    failure_breakdown["Timeout / Infinite Loop"] += 1
                elif "lint_ok=false" in reason or "compilation" in reason:
                    failure_breakdown["Syntax / Lint Unresolved"] += 1
                else:
                    failure_breakdown["Functional Mismatch"] += 1

        return BenchmarkReportData(
            total_designs=total,
            total_solved=solved_count,
            overall_solve_rate=overall_rate,
            level_counts=level_counts,
            cumulative_pass_rates=cumulative_rates,
            recovery_deltas=recovery_deltas,
            tier_stats=tier_stats,
            total_prompt_tokens=total_p_tokens,
            total_completion_tokens=total_c_tokens,
            total_tokens=total_tok,
            avg_tokens_per_design=avg_per_design,
            avg_tokens_per_solve=avg_per_solve,
            total_elapsed_sec=total_elapsed,
            failure_breakdown=failure_breakdown,
        )
