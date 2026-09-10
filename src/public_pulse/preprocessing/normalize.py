"""Deprecated -- superseded by text_cleaning.py (Phase 3).

This module previously held unimplemented placeholder functions
(`normalize_text`, `handle_codeswitch`) whose docstrings described
behavior -- e.g. "repeated characters" collapsing -- that does not
actually match the authoritative training notebooks' real cleaning
function. Nothing in this repository imported this module (verified
before this change), so it is safe to retire without breaking anything.

Use `public_pulse.preprocessing.text_cleaning` instead:
    - clean_text()          -- Layer 2 / Layer 4 input (text_clean)
    - get_layer1_input()     -- Layer 1 input (text_raw, unmodified)
    - build_text_variants()  -- both, for ETL to persist per comment

This file is kept (rather than deleted) only so a stale import produces
a clear ImportError-free redirect instead of a silent 404-style failure.
"""

from public_pulse.preprocessing.text_cleaning import (  # noqa: F401
    build_text_variants,
    clean_text,
    get_layer1_input,
)
