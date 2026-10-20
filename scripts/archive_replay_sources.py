#!/usr/bin/env python3
"""Preserve exact recorded Python source hashes without editing studies or Git."""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import timestamp, write_artifact
from rnastable.native_journal import atomic_json
from rnastable.reference_audit import require

NAME = "replay_source_archive"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def files(root, directories, pattern):
    """Inventory files by basename glob, hidden ones included, ignore files disregarded.

    Deliberately pure Python: the inventory must not depend on an external search
    binary being installed, because a missing binary would silently reduce the
    recovered source set rather than fail loudly.
    """
    found = set()
    for d in directories:
        base = root / d
        if not base.is_dir():
            continue
        for p in base.rglob(pattern):
            if ".git" in p.parts or not p.is_file():
                continue
            found.add(p)
    return sorted(found)


def bindings(root, manifest_paths=None):
    required, manifests = {}, {}
    external = []
    paths = (
        files(root, ["results"], "manifest.json")
        if manifest_paths is None
        else sorted(Path(p) for p in manifest_paths)
    )
    for p in paths:
        raw = p.read_bytes()
        data = json.loads(raw)
        code = data.get("code_sha256")
        if not isinstance(code, dict):
            continue
        manifests[str(p)] = sha(raw)
        for name, expected in code.items():
            path = Path(name)
            if not path.is_absolute():
                path = root / path
            path = Path(os.path.normpath(path))
            if path.suffix != ".py":
                continue
            require(
                isinstance(expected, str)
                and len(expected) == 64
                and all(c in "0123456789abcdef" for c in expected),
                "Invalid recorded source hash",
            )
            if not path.is_relative_to(root.resolve()):
                external.append(
                    {"path": str(path), "sha256": expected, "manifest": str(p)}
                )
                continue
            key = (str(path), expected)
            required.setdefault(key, []).append(str(p))
    return required, manifests, external


def save_blob(directory, raw):
    expected = sha(raw)
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / (expected + ".py")
    if p.exists():
        require(
            p.read_bytes() == raw, "Retained source blob changed; refusing overwrite"
        )
    else:
        with p.open("xb") as f:
            f.write(raw)
    return str(p)


def indexed_sources(root):
    # Read only: no index/config changes, checkout, commit or network.
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z", "--", "src", "scripts"],
        cwd=root,
        capture_output=True,
    )
    require(result.returncode == 0, "Cannot read staged source inventory")
    objects = {}
    for item in result.stdout.split(b"\0"):
        if not item:
            continue
        metadata, name = item.split(b"\t", 1)
        mode, oid, stage = metadata.split()
        path = name.decode()
        if stage == b"0" and mode in (b"100644", b"100755") and path.endswith(".py"):
            objects.setdefault(oid.decode(), []).append(path)
    for oid, names in sorted(objects.items()):
        result = subprocess.run(
            ["git", "cat-file", "blob", oid], cwd=root, capture_output=True
        )
        require(result.returncode == 0, "Cannot read staged source blob")
        yield result.stdout, {"kind": "git_index", "object_id": oid, "paths": names}


def published_history_sources(root):
    """Search existing local publication history; never fetch or change a checkout."""
    exports = root / "exports"
    for marker in sorted(exports.glob("*/rna-stable-ai/.git")):
        repository = marker.parent
        require(
            repository.resolve().is_relative_to(root.resolve()),
            "Publication checkout redirects outside workspace",
        )
        result = subprocess.run(
            ["git", "rev-list", "--objects", "--all", "--", "src", "scripts"],
            cwd=repository,
            capture_output=True,
        )
        require(result.returncode == 0, "Cannot read local publication history")
        objects = {}
        for line in result.stdout.splitlines():
            oid, separator, raw_name = line.partition(b" ")
            if not separator:
                continue
            name = raw_name.decode()
            if name.endswith(".py"):
                objects.setdefault(oid.decode(), []).append(name)
        for oid, names in sorted(objects.items()):
            result = subprocess.run(
                ["git", "cat-file", "blob", oid], cwd=repository, capture_output=True
            )
            if result.returncode == 0:
                yield (
                    result.stdout,
                    {
                        "kind": "local_publication_history",
                        "repository": str(repository),
                        "object_id": oid,
                        "paths": names,
                    },
                )


def build(root):
    required, manifests, external = bindings(root)
    wanted = {expected for _, expected in required}
    located, current_bundle = {}, {}
    directory = root / "results" / (NAME + "_blobs")
    candidates = files(
        root,
        [
            "src",
            "scripts",
            "results",
            "exports",
            "reports/source_snapshots",
            "reports/source_backups",
            "archive",
        ],
        "*.py",
    )
    for p in candidates:
        require(
            p.resolve().is_relative_to(root.resolve()),
            "Source candidate redirects outside workspace",
        )
        raw = p.read_bytes()
        expected = sha(raw)
        relative = p.relative_to(root)
        current = relative.parts[0] in ("src", "scripts")
        if current:
            current_bundle[str(relative)] = {
                "sha256": expected,
                "blob": save_blob(directory, raw),
            }
        if expected in wanted:
            located.setdefault(
                expected,
                {
                    "blob": save_blob(directory, raw),
                    "origin": {
                        "kind": "current_file" if current else "saved_snapshot",
                        "path": str(p),
                    },
                },
            )
    for raw, origin in indexed_sources(root):
        expected = sha(raw)
        if expected in wanted and expected not in located:
            located[expected] = {"blob": save_blob(directory, raw), "origin": origin}
    for raw, origin in published_history_sources(root):
        expected = sha(raw)
        if expected in wanted and expected not in located:
            located[expected] = {"blob": save_blob(directory, raw), "origin": origin}
    rows = [
        {
            "path": path,
            "sha256": expected,
            "manifests": refs,
            "status": "available"
            if expected in located
            else "missing_historical_bytes",
            **located.get(expected, {}),
        }
        for (path, expected), refs in sorted(required.items())
    ]
    run = root / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "workspace": str(root),
        "manifest_sha256": manifests,
        "required_python_bindings": len(rows),
        "available_python_bindings": sum(r["status"] == "available" for r in rows),
        "missing_python_bindings": sum(r["status"] != "available" for r in rows),
        "current_python_files": len(current_bundle),
        "current_bundle": current_bundle,
        "rows": rows,
        "external_python_bindings": external,
        "policy": "Exact-byte Python source availability only. Includes completed and failed recorded plans. Does not prove historical execution, transitive dependency closure, full training replay or library/native environment availability. Missing source is not reconstructed from behavior or waived.",
    }
    atomic_json(run / "summary.json", summary)
    write_artifact(
        root / "results" / (NAME + "_summary.json"),
        json.dumps(summary, indent=2) + "\n",
    )
    report = [
        "# Recorded Python source archive",
        "",
        summary["policy"],
        "",
        f"Available:{summary['available_python_bindings']}/{len(rows)} recorded bindings. Missing:{summary['missing_python_bindings']}. Current files preserved:{len(current_bundle)}.",
        "",
        "| Source | Required SHA256 | Status | Origin |",
        "|---|---|---|---|",
    ]
    report.extend(
        "| "
        + " | ".join(
            (r["path"], r["sha256"], r["status"], str(r.get("origin", "unavailable")))
        )
        + " |"
        for r in rows
    )
    write_artifact(root / "reports" / (NAME + "_report.md"), "\n".join(report) + "\n")
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text())
        and summary["complete"] is True,
        "Archive summary differs",
    )
    for p, expected in summary["manifest_sha256"].items():
        require(
            sha(Path(p).read_bytes()) == expected, "Recorded study manifest changed"
        )
    required, manifests, external = bindings(
        Path(summary["workspace"]), summary["manifest_sha256"]
    )
    recorded = {(r["path"], r["sha256"]): r for r in summary["rows"]}
    require(
        len(recorded) == len(summary["rows"])
        and set(recorded) == set(required)
        and all(recorded[key]["manifests"] == refs for key, refs in required.items())
        and manifests == summary["manifest_sha256"]
        and external == summary["external_python_bindings"],
        "Archived binding inventory differs from original manifests",
    )
    for name in summary["current_bundle"]:
        path = Path(name)
        require(
            not path.is_absolute()
            and ".." not in path.parts
            and path.parts[0] in ("src", "scripts")
            and path.suffix == ".py",
            "Invalid current source tree mapping",
        )
    for row in [
        *summary["current_bundle"].values(),
        *[r for r in summary["rows"] if r["status"] == "available"],
    ]:
        p = Path(row["blob"])
        require(
            p.parent.resolve()
            == (Path(summary["workspace"]) / "results" / (NAME + "_blobs")).resolve()
            and p.name == row["sha256"] + ".py"
            and sha(p.read_bytes()) == row["sha256"],
            "Archived Python bytes changed",
        )
    require(
        len(summary["rows"]) == summary["required_python_bindings"]
        and sum(r["status"] == "available" for r in summary["rows"])
        == summary["available_python_bindings"]
        and sum(r["status"] == "missing_historical_bytes" for r in summary["rows"])
        == summary["missing_python_bindings"]
        and len(summary["current_bundle"]) == summary["current_python_files"],
        "Source archive denominators differ",
    )
    print(
        f"Source archive audit passed:{summary['available_python_bindings']}/{summary['required_python_bindings']} exact Python bindings; {summary['missing_python_bindings']} missing versions remain explicit."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        return audit(ROOT / "results" / (NAME + "_summary.json"))
    summary = build(ROOT)
    print(
        f"Archived:{summary['available_python_bindings']}/{summary['required_python_bindings']} recorded Python bindings; current bundle:{summary['current_python_files']} files."
    )
    return summary


if __name__ == "__main__":
    main()
