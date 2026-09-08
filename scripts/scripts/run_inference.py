#!/usr/bin/env python3
"""Batch-score unscored comments through the layer1 -> layer2 -> layer4
cascade and write results to layer_predictions. Intended to run on a
schedule, not per-request. (There is no third stage in this cascade --
see docs/taxonomy.md for why.)

Not implemented yet -- this is ETL/database-integration work (Phase 7),
downstream of the model integration built in Phase 4
(src/public_pulse/inference/cascade.py). Even once implemented, running
this for real remains blocked until a real checkpoint is accessible (see
docs/MODEL_REGISTRY.md) -- InferenceCascade.from_config() will raise
CheckpointNotFoundError until then.
"""


def main():
    raise NotImplementedError


if __name__ == "__main__":
    main()
