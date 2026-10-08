# RNA-StableAI current work status

Updated 2026-10-05 (America/Los_Angeles). Workspace: `/home/zyliu/Documents/rna-stable-ai`.

The first authorized processed-PDB evaluation and CPU neural training pilot is
complete and audited. **233 tests passed.** Data: 41 train / 12 validation / 16 test;
20 epochs, validation-selected epoch 6. Test pair F1: trained CNN 0.0675;
ViennaRNA and LinearFold both 0.9438. The neural baseline is weak and shows overfitting.
This short processed cohort does not establish long-RNA accuracy or biological stability.

Details: `reports/experimental_training_checkpoint.md`.
Exact hashes, run paths and pending work: `reports/current_work_status.json`.
Original long-study summary/manifest hashes remain unchanged. Development is local.
