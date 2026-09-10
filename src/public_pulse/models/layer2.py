"""Layer 2 classifier -- see docs/taxonomy.md for label definitions.

Input contract: text_clean (see
src/public_pulse/preprocessing/text_cleaning.py:clean_text()). See
Layer1Classifier's docstring for why routing is the cascade's job, not
this class's.
"""

from public_pulse.models.base import BaseClassifier


class Layer2Classifier(BaseClassifier):
    LAYER_NAME = "layer2"
    INPUT_COLUMN = "text_clean"
