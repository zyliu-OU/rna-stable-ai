# RNA-StableAI current work status

Workspace: `/home/zyliu/Documents/rna-stable-ai`
Canonical checkpoint:`RNA-StableAI_HANDOFF_2026-10-05_V14.md`.

Continuous development authorized; save handoff+stop on observable GPT-6 usage exhaustion.
No limit signal received; quota unavailable. Completed long explicit FASTA overrides and
checkpoint-ranked native search pilot. Last fullsuite363 passed in166.80s.

Same exposed synthetic1000 nt input,3 ranking policies,8 native proposals each/33 total
native folds. Selected Vienna deltas:random -11.0,compatibility -8.4,neural prior -18.5
kcal/mol; neural adds128 proxy calls. Exact pools/logits/constraints/folds/selections/
exposure/cost replay passed. One input/seed, no test accuracy or generalization claim.

Next:atomic native journaling and resumable orchestration before more synthetic inputs.
Old optimizer/budget implementations retained. RF00008/RF00017 consumed; new independent
longer experimental data remains pending. Reports are local and no publication occurred.
