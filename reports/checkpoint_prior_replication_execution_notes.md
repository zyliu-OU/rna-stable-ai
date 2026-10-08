# Checkpoint prior replication execution notes

The component plan runs native experiment arms sequentially. Source-audit replay
and the project test suite also ran during portions of this batch. These jobs
can contend for CPU and memory; recorded wall times describe this execution
and are not isolated throughput comparisons or evidence of equal runtime.

Native cost counts cover the journaled experiment requests only. Native wall
seconds sum recorded subprocess wall times, including reported timeouts.
Completed scorer-call counts and scorer wall seconds include resume attempts
and exclude model setup, audit replays, and bookkeeping. Per-pool ranking wall
times additionally include scorer accounting writes. Interrupted requests and
incomplete execution attempts retain the explicitly unknown-cost distinction.

Full-suite launch noted: 2026-10-06T18:05:33.167115-07:00.
