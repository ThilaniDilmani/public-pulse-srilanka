"""Layer 4 classifier -- see docs/taxonomy.md for label definitions.

Input contract: text_clean, identical to Layer 2 (see
src/public_pulse/preprocessing/text_cleaning.py:clean_text() -- both
layers' authoritative notebooks use byte-identical cleaning logic). See
Layer1Classifier's docstring for why routing is the cascade's job, not
this class's.
"""

from public_pulse.models.base import BaseClassifier


class Layer4Classifier(BaseClassifier):
    LAYER_NAME = "layer4"
    INPUT_COLUMN = "text_clean"
