"""Utility for extracting pure Verilog source code from LLM chat completions."""

import re
from typing import List, Optional, Tuple

FENCE_PATTERN: re.Pattern = re.compile(
    r"```(?:verilog|systemverilog|v)?\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)
MODULE_PATTERN: re.Pattern = re.compile(
    r"(module\s+([a-zA-Z_0-9]+)\b.*?endmodule)",
    re.DOTALL,
)


class VerilogCodeExtractor:
    """Robust extractor that isolates Verilog RTL modules from markdown or conversational text."""

    @classmethod
    def extract(cls, raw_text: str, expected_module: Optional[str] = None) -> str:
        """Extract cleanest Verilog code matching expected module name or markdown fences.

        Args:
            raw_text: Raw textual output from an LLM.
            expected_module: Optional module name that must be present.

        Returns:
            Extracted Verilog source code string.
        """
        if not raw_text:
            return ""

        # 1. Search for markdown code blocks
        fenced_blocks: List[str] = [str(b) for b in FENCE_PATTERN.findall(raw_text)]
        if fenced_blocks:
            # If expected_module is given, find block containing that module
            if expected_module:
                for block in fenced_blocks:
                    if re.search(rf"\bmodule\s+{re.escape(expected_module)}\b", block):
                        return str(block.strip())
            # Otherwise return the largest fenced block
            longest_block: str = max(fenced_blocks, key=len)
            return str(longest_block.strip())

        # 2. Search for direct module ... endmodule declarations
        module_matches = MODULE_PATTERN.findall(raw_text)
        if module_matches:
            typed_matches: List[Tuple[str, str]] = [(str(m[0]), str(m[1])) for m in module_matches]
            if expected_module:
                for full_code, mod_name in typed_matches:
                    if mod_name == expected_module:
                        return str(full_code.strip())
            # Return the first or largest module
            longest_mod: str = max((m[0] for m in typed_matches), key=len)
            return str(longest_mod.strip())

        # 3. Fallback: if text already starts with module or timescale, return raw
        trimmed = raw_text.strip()
        if "module " in trimmed and "endmodule" in trimmed:
            start_idx = trimmed.find("module ")
            end_idx = trimmed.rfind("endmodule") + len("endmodule")
            return str(trimmed[start_idx:end_idx].strip())

        return str(trimmed)
