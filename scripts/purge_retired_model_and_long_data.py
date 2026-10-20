#!/usr/bin/env python3
"""Remove the retired learned pair model and every artifact above the length scope.

Two user decisions on 2026-10-20, recorded in gate v7:

  1. Purge the retired learned pair model entirely -- source modules, run
     artifacts, configs, driver scripts and unit tests -- accepting that the
     three native-control evidence generators that imported its shared
     constants break, and that gate v5's requirements 2, 3, 4 and 5 can no
     longer be regenerated from source.
  2. Remove all data for RNA at or above 3000 nt, after re-issuing the
     requirement 5 checks on the in-scope subset so the gate's evidence matches
     what remains.

This writes a manifest of every path it removes, with each file's sha256 and
size, BEFORE removing anything. The manifest is the audit trail: it records what
existed, so a later reader can tell the difference between "this was never run"
and "this was run and then deleted on purpose".

Nothing here is reversible from the tree. Published files remain in git history;
unpublished run artifacts do not, and most of `results/` was never published.
That asymmetry is the reason for the manifest.

Run with --dry-run first. It prints the full inventory and writes nothing.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Source modules that exist only to train, score or diagnose the learned model.
MODEL_MODULES = (
    "checkpoint_prior.py", "context_training.py", "full_pair_supervision.py",
    "hard_negative_supervision.py", "long_training_data.py", "negative_sampling.py",
    "pair_head_study.py", "pair_model.py", "pair_set_training.py",
    "penalty_development.py", "sampled_pair_supervision.py", "structure_model.py",
    "structured_pair_loss.py",
)

# Run directories belonging to the learned model. Matched by name, then filtered
# against the keep pattern so a native-control or current-pipeline run can never
# be caught by a broad word like "development".
MODEL_RUNS = re.compile(
    r"development|checkpoint_prior|sweep|helix_prior|pair_head|pair_development|"
    r"family_trial|experimental_pilot|penalty|context_|replication|budget|candidate|"
    r"endpoint|hard_negative|score_offset|length_checkpoints|training_smoke|population_")

KEEP_RUNS = re.compile(
    r"ribonn|rfam_release|design_workflow|window_|native_control|band_native|"
    r"pareto_mechanics|reference_|strand_|four_component|native_path|"
    r"long_native_controls|synonymous_window|raw_structure|bprna_five_clan|"
    r"stage2_band|band_clan|long_validation")

# Synthetic inputs above the active length scope.
LONG_DATA_GLOBS = ("data/synthetic/*5000*", "data/synthetic/*10000*")
LONG_RUNS = re.compile(r"5000|10000|above3000|over3000")
LONG_SEQUENCE = re.compile(r'"sequence"\s*:\s*"[ACGUTacgut]{3000,}"')
# checkpoint_prior_reference_extension matches the keep pattern only through the
# word "reference"; it is a learned-model run and is named here so the content
# sweep removes it rather than stripping it.
KEEP_OVERRIDES = ("checkpoint_prior",)

MAXIMUM_LENGTH_NT = 3000

# Modules the current pipeline depends on. The closure is checked against this
# set and the purge refuses to run if it ever reaches one of them, so a widening
# dependency cannot quietly take the production path with it.
CURRENT_PIPELINE_MODULES = {
    "folding", "scoring", "pair_reference", "component_integration", "transcript_assembly",
    "synonymous_window", "pareto", "multi_objective_bo", "discrete_bo", "score_records",
    "sequences", "reference", "artifacts", "native_journal", "exposures",
    "prospective_binding", "rfam_data", "strand_reference", "strand_agreement",
    "ribonn_integration", "assay_power", "annotations", "quality", "vienna_worker",
    "vienna_constraint_worker", "ensemble_worker", "energy_worker", "process_guard",
}


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(paths):
    """Record every file under the given paths before anything is removed."""
    entries, total = [], 0
    for path in sorted(paths):
        if path.is_file():
            files = [path]
        else:
            files = sorted(p for p in path.rglob("*") if p.is_file())
        size = sum(f.stat().st_size for f in files)
        total += size
        entries.append({
            "path": str(path.relative_to(ROOT)),
            "kind": "file" if path.is_file() else "directory",
            "files": len(files),
            "bytes": size,
            # Hashing every file in a 300 MB tree is slow and the per-file
            # hashes are not what an auditor needs; the count, the size and the
            # file list are. Hashes are recorded for single files only.
            "sha256": sha(path) if path.is_file() and size < (8 << 20) else None,
        })
    return entries, total


def dependent_closure(seed_stems):
    """Modules that cannot survive, because they import something being removed.

    A list of model modules is not enough: other modules import them, and
    deleting only the named ones leaves imports that cannot resolve. The closure
    is computed rather than hand-listed so nothing is missed, and it is checked
    against the modules the current pipeline needs before anything is removed.
    """
    import ast

    source = ROOT / "src/rnastable"
    modules = {p.stem: p for p in source.glob("*.py") if p.stem != "__init__"}
    local = {}
    for stem, path in modules.items():
        text = path.read_text()
        found = set(re.findall(r"from \.(\w+) import", text))
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.level == 1:
                    found.add(node.module.split(".")[0])
                elif node.module.startswith("rnastable."):
                    found.add(node.module.split(".")[1])
        local[stem] = found

    removed, changed = set(seed_stems), True
    while changed:
        changed = False
        for stem, deps in local.items():
            if stem not in removed and deps & removed:
                removed.add(stem)
                changed = True
    survivors = removed - set(seed_stems)
    collision = survivors & CURRENT_PIPELINE_MODULES
    if collision:
        raise SystemExit(
            f"Refusing to proceed: the closure includes modules the current pipeline "
            f"needs: {sorted(collision)}")
    return sorted(removed)


def model_targets():
    stems = dependent_closure({Path(name).stem for name in MODEL_MODULES})
    modules = [ROOT / "src/rnastable" / f"{stem}.py" for stem in stems]
    modules = [p for p in modules if p.exists()]

    scripts = []
    for script in sorted((ROOT / "scripts").glob("*.py")):
        if script.name == Path(__file__).name:
            continue
        text = script.read_text()
        if any(re.search(rf"rnastable\.{stem}\b", text) for stem in stems):
            scripts.append(script)

    tests = []
    for test in sorted((ROOT / "tests").glob("*.py")):
        if test.name == "conftest.py":
            continue
        text = test.read_text()
        if any(re.search(rf"rnastable\.{stem}\b", text) for stem in stems):
            tests.append(test)

    runs = [p for p in sorted((ROOT / "results").iterdir())
            if p.is_dir() and MODEL_RUNS.search(p.name) and not KEEP_RUNS.search(p.name)]

    configs = []
    for config in sorted((ROOT / "configs").glob("*.json")):
        name = config.name
        if MODEL_RUNS.search(name) and not KEEP_RUNS.search(name):
            configs.append(config)
    return {"modules": modules, "scripts": scripts, "tests": tests,
            "runs": runs, "configs": configs}


def broken_scripts():
    """Scripts that import a script or module that no longer exists.

    Second order: removing a driver leaves other drivers importing it. The
    closure is iterated until it stops growing, so a chain of three drivers is
    caught as surely as a direct importer. This purge script itself is never a
    candidate.
    """
    import ast

    source = {p.stem for p in (ROOT / "src/rnastable").glob("*.py")}
    scripts = {p.stem: p for p in (ROOT / "scripts").glob("*.py")}
    scripts.pop(Path(__file__).stem, None)
    imports = {}
    for stem, path in scripts.items():
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        wanted = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                wanted.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                wanted.add(node.module.split(".")[0])
        imports[stem] = {name for name in wanted if name in scripts or name in source
                         or (ROOT / "scripts" / f"{name}.py").exists()}
        imports[stem] |= {name for name in wanted
                          if name not in scripts and name not in source
                          and not (ROOT / "scripts" / f"{name}.py").exists()
                          and name.islower() and "_" in name}

    available = set(scripts) | source
    broken, changed = set(), True
    while changed:
        changed = False
        for stem, deps in imports.items():
            if stem in broken:
                continue
            unresolved = {d for d in deps if d not in available or d in broken}
            if unresolved:
                broken.add(stem)
                changed = True
    return {"scripts": [scripts[s] for s in sorted(broken) if s in scripts]}


def orphan_tests():
    """Tests whose subject no longer exists.

    Removing the model's driver scripts leaves tests that import them, and tests
    that read run directories that are gone. Their subject is removed, so they
    cannot be made to pass by fixing them; they are removed with it. A test is
    only matched when the module it imports is absent from BOTH src/rnastable
    and scripts, so a test of surviving code is never caught.
    """
    import ast

    available = {p.stem for p in (ROOT / "src/rnastable").glob("*.py")}
    available |= {p.stem for p in (ROOT / "scripts").glob("*.py")}
    available |= {p.stem for p in (ROOT / "tests").glob("*.py")}
    orphans = []
    for test in sorted((ROOT / "tests").glob("*.py")):
        if test.name == "conftest.py":
            continue
        try:
            tree = ast.parse(test.read_text())
        except SyntaxError:
            continue
        wanted = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                wanted.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                wanted.add(node.module.split(".")[0])
        # Tests that load their subject with importlib and an explicit path do
        # not show up as imports, so the path strings are checked as well.
        referenced = set(re.findall(r"scripts/([a-z0-9_]+)\.py", test.read_text()))
        if any(not (ROOT / "scripts" / f"{name}.py").exists() for name in referenced):
            orphans.append(test)
            continue
        local = {name for name in wanted
                 if name not in {"json", "math", "csv", "re", "sys", "os", "glob", "ast",
                                 "hashlib", "statistics", "subprocess", "shutil", "random",
                                 "pathlib", "datetime", "collections", "itertools",
                                 "tempfile", "textwrap", "importlib", "types", "typing",
                                 "pytest", "numpy", "torch", "rnastable", "Bio", "gzip",
                                 "functools", "dataclasses", "copy", "time", "warnings",
                                 "unittest", "contextlib", "io", "pickle", "struct",
                                 "botorch", "gpytorch", "scipy", "pandas", "concurrent",
                                 "zipfile", "xml", "platform", "resource", "signal"}}
        if local - available:
            orphans.append(test)
    return {"tests": orphans}


def long_content_runs():
    """Run directories that still carry a sequence at or above the length scope.

    Name matching is not enough: most long data sits in directories whose names
    say nothing about length. This finds it by content. A directory the current
    pipeline depends on is stripped instead of removed, by strip_long_records.
    """
    offenders = set()
    for path in (ROOT / "results").rglob("*.json"):
        if not path.is_file() or path.stat().st_size > 20_000_000:
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if LONG_SEQUENCE.search(text):
            offenders.add((ROOT / "results" / path.relative_to(ROOT / "results").parts[0]))
    removable = [p for p in sorted(offenders)
                 if not KEEP_RUNS.search(p.name)
                 or any(flag in p.name for flag in KEEP_OVERRIDES)]
    return {"runs": removable}


def long_targets():
    data = []
    for pattern in LONG_DATA_GLOBS:
        data.extend(sorted(ROOT.glob(pattern)))
    runs = [p for p in sorted((ROOT / "results").iterdir())
            if p.is_dir() and LONG_RUNS.search(p.name) and not KEEP_RUNS.search(p.name)]
    return {"data": data, "runs": runs}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--out", default="results/model_purge_runs")
    args = parser.parse_args(argv)
    if args.apply == args.dry_run:
        raise SystemExit("Pass exactly one of --dry-run or --apply")

    model, long_data = model_targets(), long_targets()
    groups = {f"model_{k}": v for k, v in model.items()}
    groups.update({f"long_{k}": v for k, v in long_data.items()})
    groups.update({f"longcontent_{k}": v for k, v in long_content_runs().items()})
    groups.update({f"broken_{k}": v for k, v in broken_scripts().items()})
    groups.update({f"orphan_{k}": v for k, v in orphan_tests().items()})

    manifest, grand_total = {}, 0
    for name, paths in groups.items():
        entries, total = inventory(paths)
        manifest[name] = {"count": len(entries), "bytes": total, "entries": entries}
        grand_total += total
        print(f"{name:<16} {len(entries):>4} paths  {total / 1e6:>9.1f} MB")
        for entry in entries[:6]:
            print(f"    {entry['path']}")
        if len(entries) > 6:
            print(f"    ... and {len(entries) - 6} more")
    print(f"\ntotal {grand_total / 1e6:.1f} MB across "
          f"{sum(g['count'] for g in manifest.values())} paths")

    payload = {
        "purpose": ("Inventory of the retired learned pair model and of data above the "
                    "active length scope, recorded before removal."),
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "authorized_by": ("user, 2026-10-20: purge the retired model entirely, accepting "
                          "that the three native-control evidence generators break; and "
                          "remove all data at or above 3000 nt after re-issuing the "
                          "requirement 5 checks on the in-scope subset"),
        "maximum_length_nt": MAXIMUM_LENGTH_NT,
        "applied": bool(args.apply),
        "total_bytes": grand_total,
        "groups": manifest,
        "what_this_destroys": [
            "The ability to regenerate gate v5's requirements 2, 3, 4 and 5 evidence from "
            "source. The artifacts remain; the generators do not.",
            "Every learned-model run artifact. Most of results/ was never published, so "
            "those are not recoverable from git history.",
            "The deferred-work status of material at or above 3000 nt, which "
            "docs/LENGTH_SCOPE.md previously recorded as preserved rather than deleted.",
        ],
        "what_this_preserves": [
            "Every figure the gate chain cites, because gates v4, v5 and v6 embed them as "
            "literal values rather than by reference.",
            "The handoffs and reports, which are the narrative record of the retirement.",
            "This manifest, which records what existed so a later reader can distinguish "
            "'never run' from 'run and then deliberately removed'.",
            "The native controls, the STRAND calibration, RiboNN, the design workflow and "
            "every artifact at or below the length scope.",
        ],
        "no_claim": [
            "Removing the model's artifacts does not change any measurement.",
            "The retirement decision rests on figures recorded in the gate chain, not on "
            "the artifacts removed here.",
        ],
    }

    if args.dry_run:
        print("\nDry run: nothing removed, nothing written.", file=sys.stderr)
        return 0

    out = ROOT / args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    (out / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {out}/manifest.json before removing anything", flush=True)

    removed = 0
    for name, paths in groups.items():
        for path in paths:
            if not path.exists():
                continue
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
            removed += 1
    print(f"Removed {removed} paths, {grand_total / 1e6:.1f} MB", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
