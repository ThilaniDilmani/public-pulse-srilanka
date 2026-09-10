"""Exceptions for model integration.

Phase 4 requires that a missing/misconfigured checkpoint be
distinguishable from an inference failure, and from a missing Python
dependency. Three distinct, non-overlapping exception types exist for
exactly that reason -- callers (and tests) should never need to inspect
an error string to know which situation occurred.
"""


class ModelIntegrationError(Exception):
    """Base class for all model-integration errors."""


class MissingDependencyError(ModelIntegrationError):
    """Raised when torch/transformers (or another required ML package) is
    not importable in the current environment. This is an environment
    problem, not a configuration or checkpoint problem -- the checkpoint
    path may be perfectly correct.
    """


class CheckpointNotFoundError(ModelIntegrationError):
    """Raised when the configured checkpoint path does not exist on disk.

    This is a configuration/deployment problem: the code and its
    dependencies are fine, but nothing has been placed at the path the
    config points to. This is exactly the situation Phase 2 established
    for all three layers (checkpoints exist on Google Drive but are not
    accessible from this environment) -- this exception is the concrete,
    catchable form of that finding.
    """


class ModelLoadError(ModelIntegrationError):
    """Raised when a checkpoint path exists but the artifact at it could
    not be loaded as a valid classification model, or does not match the
    expected contract (e.g. wrong number of output labels). This is an
    artifact-integrity problem, distinct from both of the above.
    """
