# Exact Python source archive

The completed archive preserves257 of267 recorded workspace Python path/hash
bindings and all163 Python files in its captured current source bundle. Ten older
versions remain unavailable. Missing versions are explicit rows in
`results/replay_source_archive_summary.json`; they are not reconstructed or
substituted with current code.

Two historical versions were recovered from literal source writer bodies in
RNA-workspace tool records. Only exact SHA-256 matches were retained. Session
transcripts and user messages are not published. Availability of source bytes
does not establish that those bytes were executed.

The content-addressed blobs are under `results/replay_source_archive_blobs/`.
The run inventory binds the original study manifests. Historical evidence keeps
original absolute paths; audit on the original workspace, or rerun pipelines to
produce artifacts on another host. This archive is not a complete portable
training environment, dependency lock or proof of all historical executions.

```bash
cd /home/zyliu/Documents/rna-stable-ai
.venv/bin/python scripts/archive_replay_sources.py --verify
```

New archival passes append runs and refuse to overwrite different blob bytes.
Do not edit historical manifests to make missing code appear reproducible.
