"""Snapshot the selected upstream analysis/inference sources without executing them."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "strand": ("S00NYI/BITS_STRAND", "ea9e7de635e7cf4053c676c495b8e65717369206",
               ["README.md", "LICENSE", "Figure_Scripts_1.R", "Figure_Scripts_2.R",
                "Data/all_data_in_solution_halflife.csv", "Data/nluc_cleaned_new_final.csv",
                "Data/validate_cleaned_new_final.csv"]),
    "ribonn": ("Sanofi-Public/RiboNN", "dc896e1d1f78bf6b4e9bb7525c7852fcf25532e8",
               ["README.md", "LICENSE", "MODEL WEIGHTS LICENSE.txt", "environment.yml",
                "config/conf.yml", "src/data.py", "src/model.py", "src/predict.py",
                "src/main.py", "src/utils/helpers.py", "data/prediction_input1.txt"]),
}


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = ROOT / "results/four_component_source_runs" / stamp
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"schema_version": 1, "created_utc": stamp, "files": [],
                "scope": "Source audit only; weights not acquired; no upstream code executed"}
    for component, (repo, commit, paths) in SOURCES.items():
        for path in paths:
            # Large files require the blobs endpoint rather than inline contents.
            from urllib.parse import quote
            response = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/{quote(path)}?ref={commit}"],
                check=True, capture_output=True, text=True)
            obj = json.loads(response.stdout)
            if obj.get("encoding") == "none":
                blob = subprocess.run(["gh", "api", f"repos/{repo}/git/blobs/{obj['sha']}"],
                                      check=True, capture_output=True, text=True)
                obj.update(json.loads(blob.stdout))
            if obj.get("encoding") != "base64":
                raise RuntimeError(f"Unsupported content encoding for {repo}/{path}")
            data = base64.b64decode(obj["content"])
            target = output / component / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            manifest["files"].append({"component": component, "repository": repo,
                "commit": commit, "upstream_path": path, "git_blob_sha": obj["sha"],
                "source_url": f"https://github.com/{repo}/blob/{commit}/{quote(path)}",
                "local_path": str(target.relative_to(ROOT)), "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest()})
            # Preserve a usable partial inventory if a later download fails.
            (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(output / "manifest.json")


if __name__ == "__main__":
    main()
