"""Instrumentation primitives and tracer for tracking pipeline stage execution."""

import datetime
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StageEvent:
    """Detailed telemetry record for an individual pipeline execution stage."""

    stage_id: str
    stage_name: str
    step_index: int
    level: str
    status: str  # "SUCCESS", "FAILURE", "SKIPPED", "RUNNING"
    start_time: str
    end_time: str = ""
    duration_sec: float = 0.0
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def finish(self, status: str, outputs: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None) -> None:
        """Mark stage event as finished, recording completion timestamp and duration."""
        self.status = status
        self.end_time = datetime.datetime.now().isoformat()
        if outputs:
            self.outputs.update(outputs)
        if error_message:
            self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Serialize stage event to dictionary."""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "step_index": self.step_index,
            "level": self.level,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_sec": round(self.duration_sec, 4),
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metrics": self.metrics,
            "error_message": self.error_message,
        }


class PipelineStageTracer:
    """Manages the recording and collection of pipeline stage events for an RTL run."""

    def __init__(self, problem_name: str) -> None:
        """Initialize tracer for a given problem."""
        self.problem_name = problem_name
        self.events: List[StageEvent] = []

    def record_stage(
        self,
        stage_id: str,
        stage_name: str,
        step_index: int,
        level: str,
        status: str,
        duration_sec: float,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> StageEvent:
        """Record an executed stage event with full telemetry."""
        now = datetime.datetime.now().isoformat()
        event = StageEvent(
            stage_id=stage_id,
            stage_name=stage_name,
            step_index=step_index,
            level=level,
            status=status,
            start_time=now,
            end_time=now,
            duration_sec=duration_sec,
            inputs=inputs or {},
            outputs=outputs or {},
            metrics=metrics or {},
            error_message=error_message,
        )
        self.events.append(event)
        return event

    def get_step_events(self, step_index: int) -> List[StageEvent]:
        """Retrieve all events recorded for a specific reflection step index."""
        return [e for e in self.events if e.step_index == step_index]
