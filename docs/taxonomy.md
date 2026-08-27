# Public Pulse — 4-Layer Classification Taxonomy

## Layer 1 -- Utility / Gatekeeper
`layer1_utility_label`: VALID, NOISE, SPAM

## Layer 2 -- Macro Topic
`layer2_topic_label`: TOPIC_ECON, TOPIC_GOV, TOPIC_SERV, TOPIC_LAW, TOPIC_FOR, TOPIC_MEDIA

## Layer 3 -- Fine-Grained Sub-Issue
`layer3_subissue_label`: e.g. SUB_ECON_FUEL, SUB_GOV_CORRUPT (evolves during annotation)

## Layer 4 -- Pragmatic Stance & Sarcasm
`layer4_stance_label`: STANCE_CRIT_DIR, STANCE_CRIT_SARC, STANCE_SUPP, STANCE_NEUT, NULL
Auxiliary: `is_sarcastic` (resolve overlap with STANCE_CRIT_SARC before annotation begins)
