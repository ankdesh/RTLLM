"""Standalone Command Line Interface for reflection_agent_fw."""

import argparse
import json
import logging
import sys
from pathlib import Path

from reflection_agent_fw.llm_client import OpenAICompatibleClient
from reflection_agent_fw.problem import RTLProblem
from reflection_agent_fw.solver import ReflectionAgentSolver
from reflection_agent_fw.tools import RTLToolEnvironment

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reflection_agent_fw")


def build_arg_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for standalone problem solving."""
    parser = argparse.ArgumentParser(
        prog="reflection_agent_fw",
        description="Solve a single RTL Verilog design problem via stage-gated reflection.",
    )
    parser.add_argument("--name", type=str, default="custom_design", help="Problem name identifier.")
    parser.add_argument("--module", type=str, required=True, help="Expected top-level Verilog module name.")
    parser.add_argument("--prompt", type=str, help="Problem prompt / specification string.")
    parser.add_argument("--prompt-file", type=Path, help="Path to text file containing problem specification.")
    parser.add_argument("--tb", type=Path, required=True, help="Path to self-checking testbench.v file.")
    parser.add_argument("--model", type=str, default="gpt-4o", help="OpenAI-compatible model name.")
    parser.add_argument("--base-url", type=str, default=None, help="OpenAI-compatible base API URL.")
    parser.add_argument("--api-key", type=str, default=None, help="OpenAI API key (or use OPENAI_API_KEY).")
    parser.add_argument("--max-rounds", type=int, default=5, help="Maximum reflection attempts budget.")
    parser.add_argument("--temperature", type=float, default=0.2, help="LLM sampling temperature.")
    parser.add_argument("--output-v", type=Path, default=None, help="Filepath to write final Verilog RTL.")
    parser.add_argument("--output-json", type=Path, default=None, help="Filepath to write solve trajectory JSON.")
    return parser


def main() -> int:
    """Entry point for standalone reflection agent CLI."""
    parser = build_arg_parser()
    args = parser.parse_args()

    # Read prompt
    if args.prompt_file:
        prompt_text = args.prompt_file.read_text(encoding="utf-8")
    elif args.prompt:
        prompt_text = args.prompt
    else:
        logger.error("Either --prompt or --prompt-file must be provided.")
        return 1

    # Read testbench
    if not args.tb.is_file():
        logger.error("Testbench file not found: %s", args.tb)
        return 1
    tb_code = args.tb.read_text(encoding="utf-8")

    problem = RTLProblem(
        name=args.name,
        module_name=args.module,
        prompt=prompt_text,
        testbench_code=tb_code,
        target_filename=f"{args.module}.v",
        max_reflection_rounds=args.max_rounds,
        temperature=args.temperature,
    )

    client = OpenAICompatibleClient(
        model=args.model,
        api_key=args.api_key,
        base_url=args.base_url,
    )
    tools = RTLToolEnvironment()
    solver = ReflectionAgentSolver(llm_client=client, tool_env=tools)

    logger.info("Starting reflection solver on problem: %s (max_rounds=%d)...", problem.name, args.max_rounds)
    result = solver.solve(problem)

    # Output results
    if result.solved:
        logger.info("SUCCESS: Problem '%s' solved at %s in %.2fs!", problem.name, result.solved_level, result.total_elapsed_sec)
    else:
        logger.warning("FAILED: Problem '%s' was not solved within %d rounds.", problem.name, args.max_rounds)

    if args.output_v and result.final_code:
        args.output_v.parent.mkdir(parents=True, exist_ok=True)
        args.output_v.write_text(result.final_code, encoding="utf-8")
        logger.info("Saved final RTL to %s", args.output_v)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        logger.info("Saved trajectory report to %s", args.output_json)

    return 0 if result.solved else 1


if __name__ == "__main__":
    sys.exit(main())
