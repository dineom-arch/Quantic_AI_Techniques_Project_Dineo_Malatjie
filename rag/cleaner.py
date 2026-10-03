"""Deterministic Markdown cleaning without substantive rewriting."""

import re


def clean_markdown(text: str) -> str:
    """Normalize whitespace while preserving all substantive wording."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.splitlines())
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()

