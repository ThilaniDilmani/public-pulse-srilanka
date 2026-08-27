"""Label map loading/versioning per taxonomy layer."""

import json
from pathlib import Path


class LabelMap:
    def __init__(self, path: str):
        self.path = Path(path)
        self.label_to_id = json.loads(self.path.read_text())
        self.id_to_label = {v: k for k, v in self.label_to_id.items()}
