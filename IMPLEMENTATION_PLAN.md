# Implementation Plan: RTLLM v2.1 Setup & Multi-Paradigm Agentic Utilization

This implementation plan defines the complete setup, toolchain integration, dataset extraction, modernized batch evaluation engine, and utilization guide for benchmarking agentic Verilog generation setups on **RTLLM v2.1**.

---

## 1. Background & Architecture of RTLLM v2.1

RTLLM v2.1 consists of **50 designs** categorized into 4 core functional domains:
1. **Arithmetic Modules** (20 designs): Adders (`adder_8bit`, `adder_16bit`, `adder_32bit`, `adder_pipe_64bit`, `adder_bcd`), Subtractors (`sub_64bit`), Multipliers (`multi_8bit`, `multi_16bit`, `multi_booth_8bit`, `multi_pipe_4bit`, `multi_pipe_8bit`), Dividers (`div_16bit`, `radix2_div`), Comparators (`comparator_3bit`, `comparator_4bit`), Accumulator (`accu`), Fixed/Float units (`fixed_point_adder`, `fixed_point_substractor`, `float_multi`).
2. **Memory Modules** (5 designs): `asyn_fifo`, `LIFObuffer`, `right_shifter`, `LFSR`, `barrel_shifter`.
3. **Control Modules** (6 designs): FSMs (`fsm`, `sequence_detector`), Counters (`counter_12`, `JC_counter`, `ring_counter`, `up_down_counter`).
4. **Miscellaneous Modules** (19 designs): Signal generation (`signal_generator`, `square_wave`), RISC-V components (`clkgenerator`, `instr_reg`, `ROM`, `RAM`, `alu`, `pe`), Frequency dividers (`freq_div`, `freq_divbyeven`, `freq_divbyodd`, `freq_divbyfrac`), and practical interface units (`calendar`, `traffic_light`, `width_8to16`, `synchronizer`, `edge_detect`, `pulse_detect`, `parallel2serial`, `serial2parallel`).

Each design folder contains:
- `design_description.txt`: The natural language specification with module name and I/O port contracts.
- `testbench.v`: Self-checking Verilog testbench printing pass/failure status.
- `verified_<design>.v`: Ground truth human reference RTL.
- `makefile`: Legacy compilation script hardcoded for commercial Synopsys VCS.

---

## 2. Open-Source Simulation & Tooling Strategy

The original RTLLM repository relies exclusively on proprietary Synopsys VCS. For accessible, zero-sudo, license-free agent testing, we establish a dual open-source simulator workflow:

1. **Icarus Verilog (`iverilog` + `vvp`)**:
   - **Role**: Primary event-driven functional simulator.
   - **Advantage**: Full native support for standard Verilog testbench delay semantics (`#10;`), non-synthesizable tasks, and `$display` checks. Out-of-the-box compatibility with all 50 RTLLM testbenches.
   - **Deployment**: Standalone Conda/micromamba environment (zero root/sudo required).

2. **Verilator 5 (`verilator-cli`)**:
   - **Role**: Ultra-fast static linting and cycle-accurate compiled simulation.
   - **Advantage**: Can be installed directly in seconds via `uv pip install verilator` inside a `uv venv`.
   - **Use Case**: Sub-10ms static linting (`--lint-only`) enables agents to self-check syntax errors in real-time loops before running simulation. Also supports compiled simulation with `--binary --timing -Wno-fatal`.

---

## 3. Key Components to Build

### Component 1: Dataset Exporter Utility (`agent_eval/export_dataset.py`)
- **Purpose**: Crawl the RTLLM v2.1 directory tree and aggregate all 50 designs into unified datasets:
  - `rtllm_v2_1_dataset.json` (Structured JSON array)
  - `rtllm_v2_1_dataset.jsonl` (Line-delimited JSON for LLM/agent pipelines)
- **Extracted Fields**:
  - `design_name`: Unique design key (e.g., `adder_8bit`).
  - `category`: Domain class (`Arithmetic`, `Memory`, `Control`, `Miscellaneous`).
  - `subcategory`: Functional group (e.g., `Adder`, `FIFO`, `RISC-V`).
  - `target_filename`: Required generated file name (e.g., `adder_8bit.v`).
  - `prompt`: Clean, full prompt text from `design_description.txt`.
  - `testbench_path`: Relative path to `testbench.v`.
  - `verified_rtl_path`: Relative path to gold RTL.

### Component 2: Modernized Batch Evaluation Runner CLI (`agent_eval/run_eval.py`)
- **Purpose**: Modernized, multi-threaded replacement for `auto_run.py`.
- **Capabilities**:
  - **Simulator Backend Selection**: `--simulator iverilog` (default) or `--simulator verilator`.
  - **Parallelism**: `--threads N` (multiprocessing pool to evaluate all 50 designs in seconds).
  - **Timeout Protection**: Per-test timeout (default 8s) to prevent agent-generated infinite loops from hanging the run.
  - **Metrics**:
    - Syntax Success Rate (% of designs compiling cleanly).
    - Functional Success Rate (% of designs passing 100% of testbench vectors).
    - Unbiased Pass@k calculation ($k \in \{1, 3, 5\}$) using:
      $$\text{pass}@k = 1 - \frac{\binom{n - c}{k}}{\binom{n}{k}}$$
  - **Structured Reporting**: Exports detailed `eval_results.json` and prints ANSI terminal summary tables with category breakdowns.

### Component 3: Comprehensive Utilization Guide (`RTLLM_AGENTIC_GUIDE.md`)
A complete, practical manual explaining how to utilize the benchmark in different ways:
- **Way 1: Black-Box Batch Evaluation**: Exporting prompts $\to$ agent generates files into `t1/`, `t2/`, ... $\to$ running `run_eval.py` to calculate pass@1 and pass@k.
- **Way 2: Compiler-in-the-Loop Internal Tooling**: Equipping agents with `verilator-cli --lint-only` as an internal tool call so agents catch and fix syntax errors before returning final code.
- **Way 3: Iterative Self-Debugging & Reflection Loop**: Feeding simulation error outputs (mismatch values, failed assertions) back into the agent's context and measuring convergence across $N$ iterations.
- **Way 4: Circuit Complexity Tiering**: Evaluating agents progressively across 4 difficulty tiers:
  - *Tier 1: Combinational Arithmetic* (Adders, subtractors, comparators)
  - *Tier 2: Sequential Counters & Shifters* (Counters, LFSR, barrel shifter)
  - *Tier 3: Finite State Machines & Timing* (FSMs, sequence detector, traffic light)
  - *Tier 4: Complex Subsystems & Handshaking* (Async FIFO, LIFO, RISC-V ALU/PE)
- **Way 5: Multi-Agent Collaborative Pipelines**: Role-based agent teams (Specification Analyst $\to$ RTL Architect $\to$ Verification Engineer).
- **Practical Gotchas**: Module naming conventions, `$random` testbench constraints, and clock/reset initialization.

---

## 4. Verification Plan

### Automated Verification
1. **Dataset Export Verification**:
   - Run `export_dataset.py` and verify all 50 designs are cataloged with non-empty prompts and valid filepaths.
2. **Batch Runner Verification**:
   - Run `run_eval.py` on the included `_chatgpt4/` baseline directory with `--simulator iverilog`.
   - Validate that syntax pass, functional pass, and pass@k are calculated without errors.
   - Run single-design verification with `--simulator verilator`.
3. **Guide Validation**:
   - Verify all paths, commands, and code snippets in `RTLLM_AGENTIC_GUIDE.md` are accurate and directly executable.
