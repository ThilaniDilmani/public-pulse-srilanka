"""Shared base classifier contract used by all four layer models."""


class BaseClassifier:
    def __init__(self, checkpoint_path: str, label_map_path: str):
        raise NotImplementedError

    def predict(self, text: str):
        raise NotImplementedError

    def predict_batch(self, texts: list[str]):
        raise NotImplementedError
