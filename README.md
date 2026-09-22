```

  _____    _______   _        _        __  __      __      __  ___        __ 
 |  __ \  |__   __| | |      | |      |  \/  |     \ \    / / |__ \      /_ |
 | |__) |    | |    | |      | |      | \  / |      \ \  / /     ) |      | |
 |  _  /     | |    | |      | |      | |\/| |       \ \/ /     / /       | |
 | | \ \     | |    | |____  | |____  | |  | |        \  /     / /_   _   | |
 |_|  \_\    |_|    |______| |______| |_|  |_|         \/     |____| (_)  |_|
                                                                             
                                                                                                                                                    
                                                                                                                                                                                                 
```
***
***Version 2.1***

We have released RTLLM v2.1 already. We sincerely thank users for pointing out issues encountered when using RTLLM, and apologize for the confusion caused.
1. Corrected several design descriptions and testbenches.
2. Updated the affected designs for consistency.
3. Added modernized, open-source agent evaluation suite (`agent_eval/`) supporting Icarus Verilog, Verilator, pass@k metrics, and JSON/JSONL dataset extraction.
4. Added comprehensive agentic utilization guide: [`RTLLM_AGENTIC_GUIDE.md`](./RTLLM_AGENTIC_GUIDE.md) and project constitution [`GEMINI.md`](./GEMINI.md).

--15 Aug. 2026
***

## Modern Agentic Evaluation Suite (Open-Source)

RTLLM v2.1 includes a high-throughput, license-free evaluation engine replacing legacy proprietary Synopsys VCS workflows:

- **Icarus Verilog (`iverilog` + `vvp`)**: Event-driven behavioral simulator for full functional testbenches.
- **Verilator 5 (`verilator-cli`)**: Sub-10ms static linting (`--lint-only`) and compiled timing simulation.
- **Multithreading**: Evaluate all 50 designs across 5 trials in under 2 seconds.
- **Standardized Datasets**: Export all 50 circuit specifications to structured JSON and JSONL.

### Quickstart

```bash
# 1. Environment setup with uv
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 2. Export benchmark dataset for LLM pipelines
uv run python agent_eval/export_dataset.py

# 3. Evaluate generated designs with pass@k calculation
uv run python agent_eval/run_eval.py --model-dir _chatgpt4 --simulator iverilog --threads 8

# 4. Fast static linting with Verilator
uv run python agent_eval/run_eval.py --model-dir _chatgpt4/t1 --simulator verilator --lint-only
```

---

## Autonomous Reflection Agent Framework (`reflection_agent_fw`)

RTLLM includes a completely decoupled, standalone agent framework (`reflection_agent_fw/`) that solves individual RTL problems using a bounded **Stage-Gated Reflection Loop**:
- **Level 0 (Zero-Shot)**: Initial RTL generation directly from design specification.
- **Level 1 (Lint Reflection)**: Feedback loop repairing compilation/syntax errors using `verilator-cli --lint-only`.
- **Level 2 (Simulation Reflection)**: White-box testbench reflection feeding simulation error logs + full `testbench.v` code.
- **Level 3–5 (Iterative Multi-Turn Repair)**: Multi-turn self-debugging with bounded tries.
- **Early Stopping**: Bails out immediately upon functional verification pass.

### Standalone Single-Problem CLI
Solve any individual RTL problem independently:
```bash
uv run python -m reflection_agent_fw.cli \
  --name adder_8bit \
  --module adder_8bit \
  --prompt-file Arithmetic/Adder/adder_8bit/design_description.txt \
  --tb Arithmetic/Adder/adder_8bit/testbench.v \
  --model gpt-4o-mini \
  --max-rounds 3 \
  --output-v my_adder.v \
  --output-json trajectory.json
```

---

## Multi-Framework Benchmarking & Model Comparison

Benchmark agent frameworks (e.g. `reflection_agent_fw`, `zero_shot`, or custom adapters) across RTLLM's 50 benchmark designs and 4 circuit complexity tiers:

```bash
# 1. Run reflection agent benchmark on RTLLM designs (resumable with atomic checkpoints)
uv run python agent_eval/run_framework_eval.py \
  --framework reflection_agent_fw \
  --model gpt-4o-mini \
  --workers 4 \
  --max-rounds 5 \
  --output-dir runs/

# 2. Run zero-shot baseline for comparison
uv run python agent_eval/run_framework_eval.py \
  --framework zero_shot \
  --model gpt-4o-mini \
  --workers 4 \
  --output-dir runs/

# 3. Compare frameworks and models side-by-side
uv run python agent_eval/compare_frameworks.py \
  runs/reflection_agent_fw_gpt-4o-mini_* \
  runs/zero_shot_gpt-4o-mini_* \
  --output comparison_report.md
```

For detailed agent orchestration patterns, compiler-in-the-loop tooling, reflection loops, and circuit complexity tiers, see [**RTLLM Agentic Guide**](./RTLLM_AGENTIC_GUIDE.md).

***
# RTLLM: An Open-Source Benchmark for Design RTL Generation with Large Language Model


Yao Lu, Shang Liu, Qijun Zhang, and Zhiyao Xie, "RTLLM: An Open-Source Benchmark for Design RTL Generation with Large Language Model," Asia and South Pacific Design Automation Conference (ASP-DAC) 2024.[[paper]](https://arxiv.org/pdf/2308.05345.pdf)

_**Note**: In our paper, the results are obtained based on RTLLM V1.0._

## 1. Documents

RTL Generation with Large Language Model Benchmark for generating design RTL with natural language (under construction). This repository contains a total of 29 designs. Each design has its own folder, which includes several files:

1. Design Description (**design_description.txt**):
    
    This file provides a natural language description of the design.

2. Testbench (**testbench.v**): 

    This file contains the testbench code used to simulate and test the design on Synopsys VCS.
   ```
   vcs testbench.v ../*.v
   ```

3. Designer RTL (**verified_verilog.v**): 
    
    This file contains the Verilog code that has been verified and confirmed to be functionally correct.

5. LLM Generated Verilog (**LLM_generated_verilog.v**): 
    
    This file contains the Verilog code generated by LLM. Just so you know, this code may not be verified and should be used with caution.

Please refer to the respective folders for each design to access the files mentioned above.

## 2. Run Makefile [^2]
[^2]: We have recently provided an automated Python script (auto_run.py) that you can use as a one-click compilation for all designs after simple modification. Before running it, replace the generated Verilog path in auto_run.py with your own path that contains t1, t2, ... folders.

You can run makefile to test the functionality of the code.

Step 1. Replace #DESIGN_NAME# with the design name you need to test.
```
TEST_DESIGN = #DESIGN_NAME#
```
Step 2. Compile the Verilog file.

```
make vcs
```
Step 3. Functionality test
```
make sim
```
Step 4. View the results
```
===========Your Design Passed===========
or
===========Error===========
or
===========Test completed with */N failures===========
```
Step 5. Clear output files
```
make clean
```

## 3. Workflow
  
**Fig.1** Complete RTL generation and evaluation workflow using this benchmark, including three straightforward stages.

- In stage 1, users feed each natural language description 𝓛 into their target LLM 𝓕, generating the design RTL 𝒱 = 𝓕(𝓛). If an LLM solution requires additional prompt techniques 𝓟, it will switch the natural language description 𝓛 to actual input prompts 𝓛𝓟, with the output design RTL being 𝒱 = 𝓕(𝓛𝓟). If necessary, additional human engineers' efforts can also be introduced, generating 𝒱 = ℍ(𝓕(𝓛𝓟)).

- In stage 2, the framework will test the functionality of the generated design RTL 𝒱 using our provided testbench 𝒯.

- In stage 3, the generated design RTL 𝒱 is synthesized into a netlist to analyze the design qualities regarding PPA values. They will be compared with the design qualities of the provided reference designs 𝒱ₕ.
  
<img src="_pic/bench.png" width="700px">

Fig.1: The workflow of adopting RTLLM for completely automated design RTL generation and evaluation. The user only needs to provide their LLM as input. It evaluates whether each generated design satisfies the syntax goal, functionality goal, and quality goal.

---

- **Description** (_design_description.txt_) denoted as 𝒱: A natural language description of the target design's functionality. The criteria is, that a human designer can write a correct design RTL 𝒱 after reading the description 𝓛. This description 𝓛 also includes an explicit indication of the module name, all input and output (I/O) signals with signal name and width. These pre-defined modules and I/O signal information enable automatic functionality verification with our provided testbench.
- **Testbench** (_testbench.v_) denoted as 𝒯: A testbench with multiple test cases, each with input values and correct output values. The testbench corresponds to the pre-defined module name and I/O signals in 𝓛. It can be applied to verify the correctness of design functionality.
- **Correct Design** (_designer_RTL.v_) denoted as 𝒱ₕ: A reference design Verilog hand-crafted by human designers. By comparing with this reference design 𝒱ₕ, we can quantitatively evaluate the design qualities of the automatically generated design 𝒱. Also, these correct designs have all passed our proposed testbenches.

## 4. Experiments

**Fig.2** summarizes the quantitative evaluation of both syntax and functionality correctness of all five evaluated LLMs using RTLLM. 

- Syntax Correctness: Number of generated design RTLs 𝒱 with correct syntax, out of the five trials.
- Functionality Correctness: A success ✅ as long as there is one generated RTL successfully passing the testbench 𝒯, out of the ones already with correct syntax.
  
<img src="_pic/update_Syntax_and_Functionality_Verification.png" width="800px">

Fig.2: The Syntax and Functionality Correctness Verification for Different LLMs.
 
---
 
**Fig.3** summarizes the design qualities of generated design RTL from different LLMs[^3]. These quality values are measured on each post-synthesis netlist. We report the worst negative slack (WNS) as the timing metric. It also presents the qualities of our designer-generated reference design 𝒱ₕ in RTLLM. All these reference designs are functionally correct.

[^3]: The worst LLM StarCoder is not presented due to space limitations.

<img src="_pic/DC_Results.png" width="800px">

Fig.3: The Design Qualities of Gate-Level Netlist, Synthesized with Design Compiler.

## RTLLM-2.0
Shang Liu, Yao Lu, Wenji Fang, Mengming Li, and Zhiyao Xie, "OpenLLM-RTL: Open Dataset and Benchmark for LLM-Aided Design RTL Generation(Invited)", IEEE/ACM International Conference on Computer Aided Design (ICCAD), 2024.[[paper]](https://zhiyaoxie.com/files/ICCAD24_OpenLLM.pdf)

The benchmark RTLLM-2.0 dataset is meticulously categorized into
four primary module classes: Arithmetic Modules, Memory Modules,
Control Modules, and Miscellaneous Modules. Each class encompasses
a variety of functional units pertinent to diverse computational
and control tasks, as delineated in **Fig.4**.

<img src="_pic/RTLLM2.png" width="800px">

Fig.4: RTLLM-2.0 benchmark description. The benchmark includes 50 designs across various applications, with bold designs
representing newly added designs relative to RTLLM.

## Citation
If RTLLM could help your project, please cite our work:

```
@inproceedings{lu2024rtllm,
  author={Lu, Yao and Liu, Shang and Zhang, Qijun and Xie, Zhiyao},
  booktitle={2024 29th Asia and South Pacific Design Automation Conference (ASP-DAC)}, 
  title={RTLLM: An Open-Source Benchmark for Design RTL Generation with Large Language Model}, 
  year={2024},
  pages={722-727},
  organization={IEEE}
  }

@inproceedings{liu2024openllm,
  title={OpenLLM-RTL: Open Dataset and Benchmark for LLM-Aided Design RTL Generation(Invited)},
  author={Liu, Shang and Lu, Yao and Fang, Wenji and Li, Mengming and Xie, Zhiyao},
  booktitle={Proceedings of 2024 IEEE/ACM International Conference on Computer-Aided Design (ICCAD)},
  year={2024},
  organization={ACM}
}

```
