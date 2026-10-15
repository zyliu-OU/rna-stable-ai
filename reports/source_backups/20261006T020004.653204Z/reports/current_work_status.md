# RNA-StableAI current work status

Updated 2026-10-05 (America/Los_Angeles). Workspace: `/home/zyliu/Documents/rna-stable-ai`.

Pair-scoring model and explicit family-plan/replay tools implemented. Ten-epoch
CPU development run audited: 41 training / 12 validation, selected epoch 10,
validation pair F1 **0.5411** (initial model **0.1488**).
**257 tests passed.** This is reused development validation; the new model has
no test input/evaluation. Prior measured pilot/study hashes are unchanged.

A real family-separated study still needs verified family metadata and fresh data.
Pair scoring/decoding is bounded to 256 nt. No long-RNA or biological-stability claim.
Read `reports/pair_development_checkpoint.md` and `reports/current_work_status.json`
for evidence, hashes, exact paths and pending work. Development remains local.
