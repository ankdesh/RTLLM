"""Unit tests for pipeline stage instrumentation."""

from reflection_agent_fw.instrumentation import PipelineStageTracer, StageEvent


def test_stage_event_finish() -> None:
    event = StageEvent(
        stage_id="test_stage",
        stage_name="Test Stage",
        step_index=0,
        level="L0_ZERO_SHOT",
        status="RUNNING",
        start_time="2026-09-23T20:00:00",
        duration_sec=1.5,
    )
    event.finish(status="SUCCESS", outputs={"test_key": "test_val"})
    assert event.status == "SUCCESS"
    assert event.outputs["test_key"] == "test_val"
    assert event.end_time != ""

    d = event.to_dict()
    assert d["stage_id"] == "test_stage"
    assert d["status"] == "SUCCESS"
    assert d["duration_sec"] == 1.5


def test_pipeline_stage_tracer() -> None:
    tracer = PipelineStageTracer("adder_8bit")
    ev1 = tracer.record_stage(
        stage_id="prompt_prep",
        stage_name="Prompt Assembly",
        step_index=0,
        level="L0_ZERO_SHOT",
        status="SUCCESS",
        duration_sec=0.01,
        inputs={"module": "adder_8bit"},
    )
    ev2 = tracer.record_stage(
        stage_id="rtl_generation",
        stage_name="RTL Code Generation",
        step_index=0,
        level="L0_ZERO_SHOT",
        status="SUCCESS",
        duration_sec=2.45,
        metrics={"tokens": 300},
    )

    events_step_0 = tracer.get_step_events(0)
    assert len(events_step_0) == 2
    assert events_step_0[0].stage_id == "prompt_prep"
    assert events_step_0[1].stage_id == "rtl_generation"
    assert len(tracer.get_step_events(1)) == 0
