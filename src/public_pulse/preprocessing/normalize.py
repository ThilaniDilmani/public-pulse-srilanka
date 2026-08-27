"""Text normalization for Sinhala / Singlish / English code-switched comments."""


def normalize_text(text: str) -> str:
    """Normalize whitespace, repeated characters, and encoding issues."""
    raise NotImplementedError


def handle_codeswitch(text: str) -> str:
    """Apply any Sinhala/Singlish-specific normalization rules."""
    raise NotImplementedError
