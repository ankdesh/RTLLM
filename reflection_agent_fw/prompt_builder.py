"""Prompt builder for zero-shot RTL generation and stage-gated reflection."""

from typing import Dict, List, Optional

SYSTEM_PROMPT: str = """You are an expert digital hardware designer specializing in synthesizable Verilog RTL.
Write clean, standard, synthesizable Verilog code adhering strictly to the required module name, port list, and functional specification.
Do not use non-synthesizable delays (#) inside the synthesizable RTL module unless specifically requested.
Always enclose your complete Verilog source code inside ```verilog ... ``` code blocks."""


class ReflectionPromptBuilder:
    """Constructs prompts for zero-shot generation and targeted reflection stages."""

    @classmethod
    def build_l0_messages(cls, prompt: str, module_name: str) -> List[Dict[str, str]]:
        """Construct messages for Level 0 (Zero-Shot initial generation).

        Args:
            prompt: Natural language specification and I/O contract.
            module_name: Required top-level module name.

        Returns:
            Chat messages list.
        """
        user_content = (
            f"{prompt}\n\n"
            f"CRITICAL REQUIREMENTS:\n"
            f"1. Top-level module name must be strictly `{module_name}`.\n"
            f"2. Output the complete Verilog module enclosed in ```verilog ... ``` code blocks.\n"
            f"3. Ensure all input/output ports match the specification exactly."
        )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    @classmethod
    def build_l1_lint_messages(
        cls,
        module_name: str,
        previous_code: str,
        lint_output: str,
    ) -> List[Dict[str, str]]:
        """Construct messages for Level 1 (Static Lint Error Reflection).

        Args:
            module_name: Required top-level module name.
            previous_code: The failing Verilog code previously generated.
            lint_output: Compiler or linter diagnostic errors.

        Returns:
            Chat messages list.
        """
        user_content = (
            f"Your previous Verilog implementation for module `{module_name}` failed static linting/compilation checks.\n\n"
            f"### Previous Implementation:\n"
            f"```verilog\n{previous_code}\n```\n\n"
            f"### Compiler / Lint Diagnostic Errors:\n"
            f"```text\n{lint_output}\n```\n\n"
            f"Please carefully diagnose the syntax, bitwidth, or declaration errors reported above, "
            f"fix them, and provide the complete corrected synthesizable Verilog module `{module_name}` "
            f"enclosed in ```verilog ... ``` blocks."
        )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    @classmethod
    def build_l2_sim_messages(
        cls,
        module_name: str,
        previous_code: str,
        sim_output: str,
        testbench_code: str,
    ) -> List[Dict[str, str]]:
        """Construct messages for Level 2 (Functional Simulation Reflection with White-Box Testbench).

        Args:
            module_name: Required top-level module name.
            previous_code: The previously generated Verilog code.
            sim_output: Testbench simulation failure log or mismatch messages.
            testbench_code: Full white-box source code of the verification testbench.

        Returns:
            Chat messages list.
        """
        user_content = (
            f"Your Verilog implementation for module `{module_name}` compiled cleanly, but failed functional simulation.\n\n"
            f"### Previous Implementation:\n"
            f"```verilog\n{previous_code}\n```\n\n"
            f"### Simulation Output & Assertion Failures:\n"
            f"```text\n{sim_output}\n```\n\n"
            f"### Testbench Source Code (White-Box Reference):\n"
            f"```verilog\n{testbench_code}\n```\n\n"
            f"Please inspect the testbench stimulus, clocking, reset polarity, and assertions above. "
            f"Identify why your RTL logic produced the mismatch or failed assertion, and provide the complete "
            f"corrected synthesizable Verilog module `{module_name}` enclosed in ```verilog ... ``` blocks."
        )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    @classmethod
    def build_iterative_repair_messages(
        cls,
        module_name: str,
        round_idx: int,
        previous_code: str,
        error_type: str,
        diagnostics: str,
        testbench_code: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Construct messages for Level 3+ iterative multi-turn repair attempts.

        Args:
            module_name: Required top-level module name.
            round_idx: Current reflection round index.
            previous_code: Code from the latest failed attempt.
            error_type: Either 'lint' or 'simulation'.
            diagnostics: Error message or output.
            testbench_code: Optional testbench code if error is simulation.

        Returns:
            Chat messages list.
        """
        tb_section = ""
        if testbench_code and error_type == "simulation":
            tb_section = f"\n\n### Testbench Reference:\n```verilog\n{testbench_code}\n```\n"

        user_content = (
            f"Iteration {round_idx}: Your previous attempt for module `{module_name}` still failed during {error_type}.\n\n"
            f"### Latest Implementation:\n"
            f"```verilog\n{previous_code}\n```\n\n"
            f"### {error_type.capitalize()} Output:\n"
            f"```text\n{diagnostics}\n```{tb_section}\n\n"
            f"Please review the failure carefully, correct the root-cause bug, and output the complete "
            f"corrected Verilog module `{module_name}` inside ```verilog ... ``` blocks."
        )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
