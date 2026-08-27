"""Runs the full 4-layer cascade: layer1 -> layer2 -> layer3 -> layer4.

Loads all four checkpoints once, applies early-exit when Layer 1
predicts NOISE/SPAM.
"""


class InferenceCascade:
    def __init__(self):
        raise NotImplementedError

    def predict(self, text: str) -> dict:
        raise NotImplementedError
