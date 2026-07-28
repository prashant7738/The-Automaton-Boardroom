"""Security guards for The Automaton Boardroom.

Two responsibilities live here, both about treating externally-supplied
content as untrusted:

1. Prompt-injection detection/sanitization for text a human typed in
   (`_sanitize`) before it is interpolated into any LLM prompt.
2. Validation of JSON that an LLM handed *back* to us (`validate_required_inputs`)
   before we act on it (e.g. surfacing it to the user or using it as a variable
   name), since a compromised or hallucinating model is also an untrusted input
   source.
"""
import re
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Prompt injection guard
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = [
    # (all |previous |above |prior )* uses * instead of ? so that stacked
    # qualifiers ("all prior", "all previous above", etc.) are still caught.
    r'ignore (all |previous |above |prior )*(instructions?|rules?|prompts?)',
    r'disregard (all |previous |above |prior )*(instructions?|rules?|prompts?)',
    r'forget (all |previous |above |prior )*(instructions?|rules?|prompts?)',
    r'you are now',
    r'new (persona|role|identity)',
    r'system prompt',
    r'jailbreak',
]
_INJECTION_RE = re.compile('|'.join(_INJECTION_PATTERNS), re.IGNORECASE)


def _sanitize(text: str) -> str:
    """Wrap user-supplied text so it cannot override system instructions."""
    if not isinstance(text, str):
        text = str(text)
    if _INJECTION_RE.search(text):
        raise ValueError(
            "Potentially malicious instruction detected in user input. "
            "Please rephrase your request without override commands."
        )
    # Wrap in XML-style delimiters so the LLM treats it as data, not instructions
    return f"<user_input>\n{text}\n</user_input>"


# ---------------------------------------------------------------------------
# Untrusted LLM-output validation
# ---------------------------------------------------------------------------
_ALLOWED_INPUT_TYPES = {"int", "float", "str"}
_SAFE_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def validate_required_inputs(parsed: Any) -> List[Dict]:
    """Filter a parsed LLM "required inputs" JSON array down to well-formed entries.

    Each valid entry must be a dict with a safe Python-identifier `name`,
    a `type` in {int, float, str}, and a string `description`. Anything else
    is skipped (and logged) rather than trusted downstream, since this data
    ultimately becomes a variable name written into generated code.
    """
    required_inputs: List[Dict] = []
    if not isinstance(parsed, list):
        return required_inputs
    for item in parsed:
        if (
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and item.get("type") in _ALLOWED_INPUT_TYPES
            and isinstance(item.get("description"), str)
            and _SAFE_IDENTIFIER_RE.match(item["name"])
        ):
            required_inputs.append(item)
        else:
            print(f"[guards] Skipping malformed input entry: {item}")
    return required_inputs
