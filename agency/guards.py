"""Security guards for The Automaton Boardroom.

Two responsibilities live here, both about treating externally-supplied
content as untrusted:

1. Prompt-injection detection/sanitization for text a human typed in
   (`_sanitize`) before it is interpolated into any LLM prompt.
2. Validation of JSON that an LLM handed *back* to us (`validate_design_questions`)
   before we act on it (e.g. surfacing it to the user as a multiple-choice
   question), since a compromised or hallucinating model is also an untrusted
   input source.
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
_SAFE_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
_MAX_DESIGN_QUESTIONS = 5
_MIN_OPTIONS = 2
_MAX_OPTIONS = 6


def validate_design_questions(parsed: Any) -> List[Dict]:
    """Filter a parsed LLM "design questions" JSON array down to well-formed entries.

    Each valid entry must be a dict with a safe Python-identifier `id`, a
    non-empty string `question`, and an `options` list of 2-6 non-empty
    strings. Anything else is skipped (and logged) rather than trusted
    downstream, since this data is rendered directly as a UI form. The
    result is capped at 5 questions to avoid overwhelming the user.
    """
    design_questions: List[Dict] = []
    if not isinstance(parsed, list):
        return design_questions
    for item in parsed:
        options = item.get("options") if isinstance(item, dict) else None
        if (
            isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and _SAFE_IDENTIFIER_RE.match(item["id"])
            and isinstance(item.get("question"), str)
            and item["question"].strip()
            and isinstance(options, list)
            and _MIN_OPTIONS <= len(options) <= _MAX_OPTIONS
            and all(isinstance(o, str) and o.strip() for o in options)
        ):
            design_questions.append(item)
        else:
            print(f"[guards] Skipping malformed design question entry: {item}")
        if len(design_questions) >= _MAX_DESIGN_QUESTIONS:
            break
    return design_questions[:_MAX_DESIGN_QUESTIONS]
