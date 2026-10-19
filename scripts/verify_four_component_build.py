"""Verify the completed integration run and its frozen source/inputs, without fitting."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from rnastable.component_integration import Transcript

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    artifact_map = json.loads((run/"artifacts.json").read_text())
    for relative, expected in artifact_map.items():
        path = run/relative
        if not path.resolve().is_relative_to(run) or sha(path) != expected:
            raise ValueError(f"Artifact identity mismatch: {relative}")
    identity = json.loads((run/"identity.json").read_text())
    for relative, expected in identity["implementation"].items():
        if sha(run/"source"/relative) != expected:
            raise ValueError(f"Frozen implementation mismatch: {relative}")
    records = []
    for obj in json.loads((run/"fixed_inputs.json").read_text()):
        r = Transcript(**{k:v for k,v in obj.items() if k not in ("input_sha256", "identity_sha256")})
        if obj["input_sha256"] != r.sha256 or obj["identity_sha256"] != r.identity_sha256:
            raise ValueError("Transcript identity mismatch")
        result = json.loads((run/f"rnafold_{r.tx_id}.json").read_text())
        if result["identity_sha256"] != r.identity_sha256 or result["input_sha256"] != r.sha256:
            raise ValueError("Folding result identity mismatch")
        records.append(r)
    summary = json.loads((run/"summary.json").read_text())
    for row in summary["folding"]+summary["optimizer"]:
        # Original run paths may differ when verifying an explicit copied replay.
        if sha(run/Path(row["path"]).name) != row["sha256"]:
            raise ValueError("Summary artifact checksum mismatch")
    if summary["stage3_ready"] or summary["combined_pipeline_complete"]:
        raise ValueError("Integration milestone cannot claim a complete biological pipeline")
    print(json.dumps({"artifacts_verified": len(artifact_map), "transcripts_verified": len(records),
                      "summary_sha256": sha(run/"summary.json"), "checks": "artifact and identity audit only; no inference or retraining"}, indent=2))


if __name__ == "__main__":
    main()
