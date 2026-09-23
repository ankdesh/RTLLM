"""reflection_agent_fw: Standalone stage-gated reflection agent framework for RTL generation."""

from reflection_agent_fw.instrumentation import PipelineStageTracer, StageEvent
from reflection_agent_fw.llm_client import OpenAICompatibleClient
from reflection_agent_fw.problem import RTLProblem
from reflection_agent_fw.result import SolveResult, SolveStep
from reflection_agent_fw.solver import ReflectionAgentSolver
from reflection_agent_fw.tools import RTLToolEnvironment

__all__ = [
    "OpenAICompatibleClient",
    "PipelineStageTracer",
    "RTLProblem",
    "SolveResult",
    "SolveStep",
    "StageEvent",
    "ReflectionAgentSolver",
    "RTLToolEnvironment",
]

