# Batch audit fix

The folding results were valid. The verifier previously required an outer
log_command record, while documented rerun commands invoked the runner directly.

The runner now saves durable native events per attempt, referenced by final
driver status. The verifier audits native traces without an outer wrapper.
Legacy runs use saved outer output or clearly labeled saved component CLI
intervals; absent parent events are not fabricated.

118 tests passed, including incomplete/duplicate/failed/over-limit native traces,
direct legacy logs and native auditing without an outer command log. A real
direct4-cell CPU regression passed raw folding and native concurrency audits.
The original user16-cell study passed using component CLI interval evidence,
with parent startup/teardown explicitly marked unavailable. Its longfold
artifacts were not modified or recomputed.

```bash
.venv/bin/python scripts/verify_batch_study.py
```
