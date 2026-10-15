#!/usr/bin/env python3
"""Acquire hash-bound provenance and annotation files for an already frozen panel."""

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import publish, timestamp
from rnastable.native_journal import atomic_json
from rnastable.prospective_data import bounded_download, validate_description
from rnastable.reference import digest
from rnastable.reference_audit import require
from prepare_prospective_family_panel import audit_acquisition


def source_plan(acquisition):
    run = Path(acquisition["run_dir"])
    exposed = json.loads((run / "exposure.json").read_text())
    old_families = sorted({r["family_id"] for r in exposed if r.get("family_id")})
    families = sorted(acquisition["families_downloaded"])
    require(
        acquisition["sources_complete"] is True
        and len(acquisition["metadata_panel"]["records"]) > 0,
        "Successful nonempty metadata acquisition required",
    )
    require(len(old_families) <= 20, "Provenance download family bound exceeded")
    for family in families + old_families:
        require(
            re.fullmatch(r"RF\d{5}", family) is not None,
            "Expected Rfam family accession",
        )
    rows = []
    for family in families:
        rows.append(
            {
                "family_id": family,
                "resource": "pdb_mapping",
                "filename": family + "_pdb_mapping.json",
                "url": f"https://rfam.org/family/{family}/structures?content-type=application%2Fjson",
            }
        )
    for family in old_families:
        rows.append(
            {
                "family_id": family,
                "resource": "exposed_family_description",
                "filename": family + "_description.json",
                "url": f"https://rfam.org/family/{family}?content-type=application%2Fjson",
            }
        )
    for family in families:
        rows.append(
            {
                "family_id": family,
                "resource": "stockholm",
                "filename": family + ".sto",
                "url": f"https://rfam.org/family/{family}/alignment/stockholm",
            }
        )
    releases = set()
    for family in families:
        data = validate_description(
            (run / (family + "_description.json")).read_bytes(), family
        )
        releases.add(data["rfam"]["release"]["number"])
    require(len(releases) == 1, "Metadata families have inconsistent releases")
    return rows, next(iter(releases))


def validate_source(content, row, release):
    if row["resource"] == "exposed_family_description":
        data = validate_description(content, row["family_id"])
        require(
            data["rfam"]["release"]["number"] == release,
            "Family description release changed",
        )
    elif row["resource"] == "pdb_mapping":
        data = json.loads(content)
        require(
            isinstance(data, (dict, list)), "Expected structured PDB mapping response"
        )
    else:
        text = content.decode()
        require(
            text.startswith("# STOCKHOLM 1.0") and text.rstrip().endswith("//"),
            "Incomplete Stockholm response",
        )
        accessions = re.findall(
            r"^#=GF\s+AC\s+(RF\d{5})(?:\.\d+)?\s*$", text, re.MULTILINE
        )
        require(accessions == [row["family_id"]], "Stockholm accession binding differs")
    # This validates file envelopes only, not reference pairs or provenance clearance.


def download(acquisition_path):
    acquisition = audit_acquisition(acquisition_path)
    source = Path(acquisition["run_dir"])
    plan, release = source_plan(acquisition)
    run = ROOT / "results/prospective_evidence_runs" / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "acquisition.json", acquisition)
    atomic_json(run / "plan.json", {"requests": plan, "rfam_release": release})
    attempts = [{**row, "status": "not_started"} for row in plan]
    atomic_json(run / "attempts.json", attempts)
    for attempt in attempts:
        if attempt["resource"] == "stockholm" and any(
            a["status"] != "ok" for a in attempts if a["resource"] != "stockholm"
        ):
            attempt.update(reason="provenance_sources_unavailable")
            atomic_json(run / "attempts.json", attempts)
            continue
        attempt["status"] = "started"
        atomic_json(run / "attempts.json", attempts)
        try:
            raw = bounded_download(attempt["url"], 10 * 1024 * 1024)
            (run / attempt["filename"]).write_bytes(raw)
            attempt["sha256"] = digest(raw)
            validate_source(raw, attempt, release)
            attempt["status"] = "ok"
        except (OSError, ValueError, KeyError) as exc:
            attempt.update(status="error", error=type(exc).__name__ + ": " + str(exc))
        atomic_json(run / "attempts.json", attempts)
        print(
            f"{attempt['family_id']} {attempt['resource']}: {attempt['status']}",
            flush=True,
        )
    files = {"acquisition.json", "plan.json", "attempts.json"} | {
        a["filename"] for a in attempts if "sha256" in a
    }
    manifest = {
        "run_dir": str(run),
        "acquisition_run": str(source),
        "snapshot_sha256": {
            name: digest((run / name).read_bytes()) for name in sorted(files)
        },
        "policy": "Fixed previously selected metadata panel. File envelope verification only; no reference pairs parsed, no re-selection, fitting or inference. PDB/clan overlap and exact annotation binding still require offline validation.",
    }
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "sources_complete": all(a["status"] == "ok" for a in attempts),
        "planned_requests": len(attempts),
        "successful_requests": sum(a["status"] == "ok" for a in attempts),
        "selected_metadata_records": len(acquisition["metadata_panel"]["records"]),
        "rfam_release": release,
        "reference_pairs_parsed": False,
        "test_inference_allowed": False,
    }
    atomic_json(run / "summary.json", summary)
    report = [
        "# Prospective annotation and provenance file acquisition",
        "",
        manifest["policy"],
        "",
        f"Evidence acquisition complete: {summary['sources_complete']}. Verified files: {summary['successful_requests']}/{summary['planned_requests']}. Selected metadata records: {summary['selected_metadata_records']}.",
        "",
        "| Family | Resource | Status | Detail |",
        "|---|---|---|---|",
    ]
    for a in attempts:
        report.append(
            f"| {a['family_id']} | {a['resource']} | {a['status']} | {a.get('error', a.get('reason', ''))} |"
        )
    report += [
        "",
        "Successful downloads are not a completed evaluation. Offline provenance and annotation binding remain required.",
        "",
    ]
    rows = [
        {
            key: a.get(key)
            for key in ("family_id", "resource", "status", "error", "reason", "url")
        }
        for a in attempts
    ]
    publish(
        ROOT, "prospective_evidence", summary, rows, list(rows[0]), "\n".join(report)
    )
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Retained evidence summary differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(digest(raw) == summary["manifest_sha256"], "Evidence manifest changed")
    manifest = json.loads(raw)
    require(manifest["run_dir"] == str(run), "Evidence directory differs")
    attempts = json.loads((run / "attempts.json").read_text())
    expected_files = {"acquisition.json", "plan.json", "attempts.json"} | {
        a["filename"] for a in attempts if "sha256" in a
    }
    require(
        set(manifest["snapshot_sha256"]) == expected_files,
        "Evidence snapshot inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            Path(name).name == name and digest((run / name).read_bytes()) == sha,
            "Evidence snapshot changed: " + name,
        )
    source = audit_acquisition(Path(manifest["acquisition_run"]) / "summary.json")
    require(
        source == json.loads((run / "acquisition.json").read_text()),
        "Evidence source acquisition differs",
    )
    plan, release = source_plan(source)
    require(
        json.loads((run / "plan.json").read_text())
        == {"requests": plan, "rfam_release": release},
        "Evidence source plan differs",
    )
    require(
        [{key: a[key] for key in row} for a, row in zip(attempts, plan)] == plan
        and len(attempts) == len(plan),
        "Evidence attempts differ from plan",
    )
    for attempt in attempts:
        require(
            attempt["status"] in ("ok", "error", "not_started"),
            "Unknown evidence request state",
        )
        if "sha256" in attempt:
            require(
                digest((run / attempt["filename"]).read_bytes()) == attempt["sha256"],
                "Evidence response changed",
            )
        if attempt["status"] == "ok":
            validate_source((run / attempt["filename"]).read_bytes(), attempt, release)
    expected = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest(raw),
        "sources_complete": all(a["status"] == "ok" for a in attempts),
        "planned_requests": len(plan),
        "successful_requests": sum(a["status"] == "ok" for a in attempts),
        "selected_metadata_records": len(source["metadata_panel"]["records"]),
        "rfam_release": release,
        "reference_pairs_parsed": False,
        "test_inference_allowed": False,
    }
    require(summary == expected, "Evidence acquisition accounting differs")
    print(
        "Prospective evidence audit passed: request/file hashes, source panel and envelopes; no network or inference."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument(
        "--acquisition",
        type=Path,
        default=ROOT / "results/prospective_family_acquisition_summary.json",
    )
    args = parser.parse_args()
    if args.verify:
        return audit(ROOT / "results/prospective_evidence_summary.json")
    return download(args.acquisition)


if __name__ == "__main__":
    main()
