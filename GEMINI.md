# RTLLM Project Constitution (GEMINI.md)

This document establishes the architecture, coding principles, dependency management, simulation standards, and verification guidelines for the RTLLM repository.

---

## 1. Core Architectural Principles

- **Modular & Interface-Driven**:
  - `reflection_agent_fw/`: Completely decoupled, standalone agent framework solving one RTL problem at a time through stage-gated reflection (L0 -> L1 -> L2 -> L3..L5) with bounded tries and white-box testbench reflection.
  - `agent_eval/`: Overarching evaluation & benchmarking harness. Coordinates batch evaluation over the 50 RTLLM benchmark designs across 4 circuit complexity tiers.
  - Extensible framework adapters implement `BaseAgentAdapter` (`agent_eval/framework_adapter.py`) so multiple agent frameworks can be compared under identical benchmark conditions.
  - New simulators must implement `BaseSimulator` (`agent_eval/simulator_interface.py`).
  - Strict enforcement of **one primary class per file**.
- **Zero-Pollution Execution**:
  - Simulators execute inside isolated temporary directories (`tempfile.TemporaryDirectory`).
  - Never mutate, overwrite, or overwrite makefiles or source files inside benchmark design folders.
- **Fail Explicitly and Early**:
  - Do not allow simulation timeouts, missing files, or syntax faults to silently pass or defer to later stages.
  - Use typed exceptions and structured logging.
- **Static Type Hinting**:
  - All Python code must strictly pass `mypy` static type checks (`uv run mypy agent_eval`).

---

## 2. Environment & Toolchain Standards

- **Virtual Environment Management**:
  - Always prefer `uv` and `uv venv` for fast, deterministic setup.
  - Dependencies are declared in `pyproject.toml`.
- **Open-Source Hardware Toolchain**:
  - **Icarus Verilog (`iverilog` & `vvp`)**: Primary event-driven behavioral simulator for standard Verilog testbenches. Located via PATH or Conda EDA (`/home/ankdesh/.gemini/antigravity/scratch/conda_eda/bin`).
  - **Verilator 5 (`verilator-cli`)**: Static linter and compiled simulator installed via `uv pip install verilator`.

---

## 3. Benchmark Dataset Integrity

- Benchmark specifications comprise exactly 50 canonical circuit designs across 4 domains:
  1. `Arithmetic` (19 designs)
  2. `Control` (6 designs)
  3. `Memory` (5 designs)
  4. `Miscellaneous` (20 designs)
- Each design directory must contain:
  - `design_description.txt`: Specification and port contract.
  - `testbench.v`: Self-checking testbench containing the standard pass assertion (`Your Design Passed`).
  - `verified_<design>.v`: Ground truth reference RTL.
- Standardized datasets (`rtllm_v2_1_dataset.json` and `.jsonl`) are regenerated using:
  ```bash
  uv run python agent_eval/export_dataset.py
  ```

---

## 4. Evaluation & Metric Conventions

- **Pass@k Estimator**:
  - Evaluated using unbiased hypergeometric combination formula:
    $$\text{pass}@k = \mathbb{E}\left[ 1 - \frac{\binom{n - c}{k}}{\binom{n}{k}} \right]$$
  - Handled by `MetricsCalculator` (`agent_eval/metrics_calculator.py`).
- **Parallel Batch Runner**:
  - Coordinated by `EvaluationRunner` (`agent_eval/eval_runner.py`) using thread-safe process execution.

---

## 5. Testing & Verification Requirements

- **Continuous Testing**:
  - All unit and integration tests under `tests/` must be run using:
    ```bash
    uv run pytest tests/ -v
    uv run mypy agent_eval reflection_agent_fw tests
    ```
  - Before committing changes, ensure end-to-end evaluation passes against baseline `_chatgpt4`.
