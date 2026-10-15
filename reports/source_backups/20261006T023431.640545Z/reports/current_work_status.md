# RNA-StableAI current work status

Workspace: `/home/zyliu/Documents/rna-stable-ai`

The family-disjoint comparative trial completed and passed its audit: 24 training /
23 validation / 9 test records; 10 CPU epochs, selected epoch 9. Mean test pair F1:
trained 0.0912, initial 0.0374, ViennaRNA and LinearFold 0.8794. All 45 predictions
and 18 native folds were measured. The full suite passed 265 tests.

The test RF00008 family is now recorded as exposed, including durable test-start
protection for incomplete runs. The exposure registry contains 125 records. Old
pair-development, experimental-pilot and equal-budget outputs remain intact and
audited. Processed comparative labels, one family per split, unresolved prior PDB
family/tool-training overlap and a 256 nt architecture limit constrain interpretation.

See `reports/family_trial_development_checkpoint.md` for exact commands and
`reports/current_work_status.json` for retained fingerprints and earlier studies.
Next: improve the model using development data only and obtain a larger verified
family/clan cohort before freezing a fresh test. Scalable long-RNA modeling remains
pending.
