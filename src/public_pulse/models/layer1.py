"""Layer 1 classifier -- see docs/taxonomy.md for label definitions.

Input contract: text_raw (unmodified comment text -- see
src/public_pulse/preprocessing/text_cleaning.py:get_layer1_input()).
This classifier itself is preprocessing-agnostic (it tokenizes whatever
string it is given); routing the correct text variant to it is the
cascade's responsibility (src/public_pulse/inference/cascade.py), not
this class's. INPUT_COLUMN below is metadata for documentation/tests,
not a runtime-enforced constraint on predict()'s argument.
"""

from public_pulse.models.base import BaseClassifier


class Layer1Classifier(BaseClassifier):
    LAYER_NAME = "layer1"
    INPUT_COLUMN = "text_raw"
