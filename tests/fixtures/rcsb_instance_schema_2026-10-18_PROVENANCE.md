# RCSB instance schema test fixture

Byte-identical copy of the official schema retrieved October 18, 2026 from
https://data.rcsb.org/rest/v1/schema/polymer_entity_instance .
The original retained local artifact is
`results/rcsb_instance_schema_2026-10-18.json`.

SHA-256: `5fab5922db0ddc09ebf26f592f17009b95f8b04ff4270c395e32ab32cd98c915`.

This schema contains field definitions, not RNA sequences or contact labels.
`test_rcsb_long_source_survey.py` checks the corrected container-identifier and
modeled-residue-count field names against these retained official bytes without
a network request or a dependency on the ignored local results directory.
