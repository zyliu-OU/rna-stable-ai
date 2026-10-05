# Constrained CPU mutation search

Minimize LinearFold-V reported approximate energy per nucleotide at fixed sequence length; no biological stability claim.

Input: `mixed_1000_seed1729` (1000 nt); seed 2718; attempted steps 48; accepted 21.

Search status: completed. Mutation count: 40/40. GC fraction: 0.5960. Constraints passed: True.

Noncoding mode preserves every nucleotide count by swaps. Protein-preserving mode supports full codons in frame 0 using standard genetic code 1 and preserves GC count. Protected positions use one-based coordinates.

LinearFold energy change: -37.5 kcal/mol.
ViennaRNA energy change: -30.5 kcal/mol. Improvement independently confirmed by ViennaRNA: True.

Selected output: `/home/zyliu/Documents/rna-stable-ai/results/optimization_runs/20261005T022718.353006Z/selected.fasta`; source: finalist; reason: confirmed_improvement; changed positions: 40.

Proposed finalist retained for evidence: `/home/zyliu/Documents/rna-stable-ai/results/optimization_runs/20261005T022718.353006Z/finalist.fasta`

Use selected.fasta as the output. An unconfirmed, unchanged or worsened finalist returns the original input. Failed search/validation also returns the input; unknown reference energy stays unknown. Candidate energy deltas and mutation counts above describe the retained search finalist.

Negative changes mean lower computed folding energy. ViennaRNA input/finalist folds run on CPU with a separate timeout. A failed validation remains unknown, not successful. Search trajectories and failed folds are retained. No training or experimental biological validation was performed.

Sources: [LinearFold](https://github.com/LinearFold/LinearFold), [ViennaRNA MFE](https://viennarna.readthedocs.io/en/latest/mfe/global.html), [Biopython codon tables](https://biopython.org/docs/latest/api/Bio.Data.html).
