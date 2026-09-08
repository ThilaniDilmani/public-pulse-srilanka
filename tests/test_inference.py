"""Integration-flavored sanity checks tying the Phase 4 factory and
cascade together (unit coverage for each lives in test_models.py and
test_cascade.py respectively -- this file only checks they agree with
each other and with the Phase 1 taxonomy contract end-to-end).

No real model loading here either -- see test_models.py for why that
remains blocked (ACCESS_UNAVAILABLE checkpoints, per Phase 2).
"""

from public_pulse.inference.cascade import InferenceCascade


class TestFromConfigCascadeMatchesTaxonomyContract:
    def test_layer1_label_map_matches_taxonomy(self):
        cascade = InferenceCascade.from_config()
        assert set(cascade.layer1.label_map.label_to_id.keys()) == {"VALID", "NOISE"}

    def test_layer2_label_map_matches_taxonomy(self):
        cascade = InferenceCascade.from_config()
        assert set(cascade.layer2.label_map.label_to_id.keys()) == {
            "TOPIC_ECON_SERV", "TOPIC_FOR", "TOPIC_GOV", "TOPIC_LAW", "TOPIC_MEDIA",
        }

    def test_layer4_label_map_matches_taxonomy(self):
        cascade = InferenceCascade.from_config()
        assert set(cascade.layer4.label_map.label_to_id.keys()) == {
            "STANCE_CRIT", "STANCE_NEUT", "STANCE_SUPP",
        }

    def test_no_layer_in_the_cascade_is_named_layer3(self):
        cascade = InferenceCascade.from_config()
        layer_names = {cascade.layer1.LAYER_NAME, cascade.layer2.LAYER_NAME, cascade.layer4.LAYER_NAME}
        assert "layer3" not in layer_names
        assert layer_names == {"layer1", "layer2", "layer4"}
