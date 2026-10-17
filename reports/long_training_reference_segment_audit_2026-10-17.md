# RNA-StableAI Step 2: exact-segment overlap between added training RNAs and development references

Date: 2026-10-17 (America/Los_Angeles)  
Workspace: `/home/zyliu/Documents/rna-stable-ai`

The 17 selected long bpRNA training additions were compared by sequence with the 11 existing longer-RNA development references. The audit froze exact-segment lengths of 20, 30, and 40 nt before execution. It counted distinct identical segments for every train/reference pair; it did not use structure labels, run model inference, or assign families. Each training RNA also had 32 deterministic mononucleotide shuffles as a simple composition-preserving negative control, compared against all 11 references at 30 nt.

| Exact segment length | Training additions with at least one match to a development reference |
| ---: | ---: |
| 20 nt | 14 / 17 |
| 30 nt | 14 / 17 |
| 40 nt | 10 / 17 |

The 14 top 30-nt matches span all four development families: five training additions matched RF00177 best, three RF02540, three RF02541, and three RF02542. The largest per-record counts of distinct shared 30-mers were 132 for `bpRNA_RFAM_43068` versus an RF02542 reference, 126 for `bpRNA_RFAM_42980` versus RF02541, and 77 for `bpRNA_CRW_13049` versus RF00177. Twelve training additions shared at least 10 distinct 30-mers with their best reference. The remaining three additions had no 20-, 30-, or 40-nt exact segment in this panel; that absence does not establish different families.

The highest 30-nt overlap among all 544 shuffled training sequences was zero. This empirical control indicates the observed long exact segments are not explained by mononucleotide composition alone. It does not provide a calibrated homology probability or substitute for a family/clan assignment; ribosomal RNAs can share conserved segments across related families. The prior symmetric 0.8 whole-sequence overlap screen was not designed to exclude regional homology.

This is direct evidence of substantial sequence overlap between the new training additions and the label-informed development cohort. The cohort remains useful only for development diagnostics. It cannot serve as an independent family-separated validation set, and no checkpoint or inference calibration should be promoted from it. A new independent panel must be frozen after source-level lineage or version-pinned covariance-model mapping, with both family/clan checks and regional sequence-overlap screening. The 4,000–4,999-nt coverage gap also remains.

Canonical artifacts:

- Protocol: `results/long_training_reference_segment_audit_protocol_runs/20261017T185039.732720Z/manifest.json`
- Per-record result: `results/long_training_reference_segment_audit_runs/20261017T185041.371852Z/summary.json`
- Driver: `scripts/audit_long_training_reference_segments.py`

Verification: the frozen source and driver hashes passed audit; deterministic run replay exactly reproduced every per-record segment count and shuffled control. The driver compiled and three focused source/panel tests passed.
