#!/usr/bin/env python3
"""Compare supplied PDB annotation contacts with retained raw FR3D cWW graphs."""
# ruff: noqa: E402 -- standalone source bootstrap.

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rnastable.artifacts import publish, timestamp, write_artifact
from rnastable.exposures import record_exposure, read_exposure, exposure_records
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.reference_audit import require
from rnastable.sequences import validate_sequence
from prepare_structure_derived_binding import audit as audit_binding

NAME = "structure_contact_provenance"
BASE = "https://rna.bgsu.edu/rna3dhub/rest/getSequenceBasePairs"
POLICY = {
    "schema_version": 1,
    "purpose": "source_annotation_integrity_only",
    "mode": "only_nested_False",
    "maximum_bytes": 2097152,
    "timeout_seconds": 30,
    "contact_class": "cWW",
    "model_inference_authorized": False,
    "replace_frozen_references": False,
    "interpretation": "Current raw FR3D graph versus the pinned historical supplied annotation. Differences may reflect source updates or positional writer projection; do not attribute a cause without exact-version evidence. This is not a new independent test panel.",
}


def request_plan(binding):
    records = binding["binding"]["records"]
    require(
        records and all(r["reference_status"] == "ok" for r in records),
        "Complete fixed source annotations required for integrity comparison",
    )
    rows = []
    for index, record in enumerate(records):
        params = urllib.parse.urlencode(
            {
                "pdb_id": record["pdb_accession"].upper(),
                "chain": record["chain_id"],
                "only_nested": "False",
            }
        )
        rows.append(
            {
                "id": record["id"],
                "pdb_accession": record["pdb_accession"],
                "family_id": record["family_id"],
                "chain_id": record["chain_id"],
                "sequence_sha256": record["sequence_sha256"],
                "filename": f"record_{index:03d}.json",
                "url": BASE + "?" + params,
            }
        )
    require(
        len({r["url"] for r in rows}) == len(rows), "Duplicate fixed PDB-chain request"
    )
    return rows


def source_inputs(summary_path):
    """Bind source graph once; later replay does not reread latest dataset pointers."""
    summary_path = Path(summary_path).resolve()
    binding = json.loads(summary_path.read_text())
    run = Path(binding["run_dir"])
    manifests = [run / "manifest.json"]
    bm = json.loads(manifests[0].read_text())
    source_run, protocol_run = Path(bm["source_run"]), Path(bm["protocol_run"])
    manifests += [source_run / "manifest.json", protocol_run / "manifest.json"]
    inputs = {str(summary_path): digest(summary_path.read_bytes())}
    for path in manifests:
        inputs[str(path)] = digest(path.read_bytes())
        manifest = json.loads(path.read_text())
        for name, sha in manifest["snapshot_sha256"].items():
            inputs[str(path.parent / name)] = sha
        inputs.update(manifest.get("code_sha256", {}))
    return inputs


def freeze(binding_path):
    binding = audit_binding(binding_path)
    plan = request_plan(binding)
    run = ROOT / "results" / (NAME + "_protocol_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "binding.json", binding)
    atomic_json(run / "plan.json", plan)
    atomic_json(run / "policy.json", POLICY)
    # Preserve exact driver bytes before any response can lead to development changes.
    (run / "driver.py").write_bytes(Path(__file__).read_bytes())
    manifest = {
        "run_dir": str(run),
        "input_sha256": source_inputs(Path(binding["run_dir"]) / "summary.json"),
        "snapshot_sha256": {p.name: digest(p.read_bytes()) for p in run.iterdir()},
        "code_sha256": {str(Path(__file__)): digest(Path(__file__).read_bytes())},
    }
    atomic_json(run / "manifest.json", manifest)
    audit_protocol(run / "manifest.json")
    write_artifact(
        ROOT / "results" / (NAME + "_protocol.json"),
        json.dumps(manifest, indent=2) + "\n",
    )
    print(
        "Frozen raw-contact integrity protocol: " + str(run / "manifest.json"),
        flush=True,
    )
    return manifest


def audit_protocol(path):
    manifest = json.loads(Path(path).read_text())
    run = Path(manifest["run_dir"])
    require(
        manifest == json.loads((run / "manifest.json").read_text()),
        "Raw-contact protocol differs",
    )
    require(
        set(manifest["snapshot_sha256"])
        == {"binding.json", "plan.json", "policy.json", "driver.py"},
        "Raw-contact protocol snapshot differs",
    )
    for field in ("input_sha256", "code_sha256"):
        for name, sha in manifest[field].items():
            require(
                digest(Path(name).read_bytes()) == sha,
                "Raw-contact input/code changed: " + name,
            )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha, "Raw-contact snapshot changed"
        )
    require(
        json.loads((run / "policy.json").read_text()) == POLICY,
        "Raw-contact policy differs",
    )
    binding = json.loads((run / "binding.json").read_text())
    require(
        json.loads((run / "plan.json").read_text()) == request_plan(binding),
        "Raw-contact requests differ from frozen panel",
    )
    return manifest


def download(url):
    require(url.startswith(BASE + "?"), "Unexpected raw-contact URL")
    request = urllib.request.Request(
        url, headers={"User-Agent": "RNA-StableAI/source-integrity"}
    )
    with urllib.request.urlopen(request, timeout=POLICY["timeout_seconds"]) as response:
        require(response.geturl() == url, "Raw-contact request redirected")
        raw = response.read(POLICY["maximum_bytes"] + 1)
    require(len(raw) <= POLICY["maximum_bytes"], "Raw-contact byte bound exceeded")
    return raw


def sequence_from_response(raw):
    data = json.loads(raw)
    require(
        isinstance(data, dict) and isinstance(data.get("sequence"), str),
        "Raw-contact sequence schema differs",
    )
    sequence = data["sequence"].upper().replace("T", "U")
    validate_sequence(sequence)
    return sequence, data


def compare(raw, record):
    sequence, data = sequence_from_response(raw)
    result = {
        "id": record["id"],
        "sequence_bound": sequence == record["sequence"],
        "source_sequence_sha256": digest(sequence.encode()),
        "status": "sequence_mismatch",
        "reference_replaced": False,
    }
    if not result["sequence_bound"]:
        return result
    require(
        isinstance(data.get("annotations"), list), "Raw-contact annotations missing"
    )
    pairs, raw_cww_rows, other = set(), 0, 0
    for item in data["annotations"]:
        require(
            isinstance(item, dict) and isinstance(item.get("bp"), str),
            "Malformed raw contact",
        )
        if item["bp"] != "cWW":
            other += 1
            continue
        raw_cww_rows += 1
        coordinates = []
        for key in ("seq_id1", "seq_id2"):
            value = item.get(key)
            require(
                (type(value) is int or isinstance(value, str) and value.isdigit())
                and 1 <= int(value) <= len(sequence),
                "Invalid one-based raw-contact coordinate",
            )
            coordinates.append(int(value) - 1)
        require(
            coordinates[0] != coordinates[1], "Raw contact pairs a nucleotide to itself"
        )
        pairs.add(tuple(sorted(coordinates)))
    original = {tuple(pair) for pair in record["pairs"]}
    degree = Counter(i for pair in pairs for i in pair)
    missing, extra = original - pairs, pairs - original
    result.update(
        status="ok",
        raw_cww_rows=raw_cww_rows,
        raw_unique_cww_contacts=len(pairs),
        other_annotation_rows=other,
        repeated_or_reverse_cww_rows=raw_cww_rows - len(pairs),
        raw_nucleotides_with_multiple_cww_partners=sorted(
            i for i, count in degree.items() if count > 1
        ),
        supplied_contacts=len(original),
        supplied_contacts_absent_from_current_raw=[list(p) for p in sorted(missing)],
        current_raw_contacts_absent_from_supplied=[list(p) for p in sorted(extra)],
        exact_contact_set_match=not missing and not extra,
        raw_cww_pairs=[list(pair) for pair in sorted(pairs)],
    )
    return result


def analyze(run, binding, attempts):
    records = {r["id"]: r for r in binding["binding"]["records"]}
    outcomes = []
    for attempt in attempts:
        if attempt["status"] != "ok":
            outcomes.append(
                {
                    "id": attempt["id"],
                    "status": "source_unavailable",
                    "error": attempt.get("error", ""),
                    "reference_replaced": False,
                }
            )
            continue
        try:
            outcomes.append(
                compare(
                    (run / attempt["filename"]).read_bytes(), records[attempt["id"]]
                )
            )
        except (ValueError, KeyError, TypeError) as exc:
            outcomes.append(
                {
                    "id": attempt["id"],
                    "status": "unsupported_source_schema",
                    "error": str(exc),
                    "reference_replaced": False,
                }
            )
    return outcomes


def acquire(protocol_path):
    protocol = audit_protocol(protocol_path)
    directory = Path(protocol["run_dir"])
    binding = json.loads((directory / "binding.json").read_text())
    plan = json.loads((directory / "plan.json").read_text())
    run = ROOT / "results" / (NAME + "_runs") / timestamp()
    run.mkdir(parents=True, exist_ok=False)
    atomic_json(run / "protocol.json", protocol)
    attempts = [{**row, "status": "not_started"} for row in plan]
    atomic_json(run / "attempts.json", attempts)
    for attempt in attempts:
        attempt["status"] = "started"
        atomic_json(run / "attempts.json", attempts)
        try:
            raw = download(attempt["url"])
            (run / attempt["filename"]).write_bytes(raw)
            attempt.update(sha256=digest(raw), status="ok")
        except (OSError, ValueError) as exc:
            attempt.update(status="error", error=type(exc).__name__ + ": " + str(exc))
        atomic_json(run / "attempts.json", attempts)
        print(attempt["id"] + ": " + attempt["status"], flush=True)
    # Even mismatched valid response sequences are recorded before contact parsing.
    exposed = []
    for attempt in attempts:
        if attempt["status"] == "ok":
            try:
                sequence, _ = sequence_from_response(
                    (run / attempt["filename"]).read_bytes()
                )
                exposed.append(
                    {
                        "sequence": sequence,
                        "family_id": attempt["family_id"],
                        "pdb_accession": attempt["pdb_accession"],
                    }
                )
            except (ValueError, KeyError, TypeError):
                pass
    event = record_exposure(run, "validation_started", exposed) if exposed else None
    outcomes = analyze(run, binding, attempts)
    manifest = {
        "run_dir": str(run),
        "protocol_run": str(directory),
        "exposure_event": event,
        "snapshot_sha256": {
            str(p.relative_to(run)): digest(p.read_bytes())
            for p in run.rglob("*")
            if p.is_file()
        },
    }
    atomic_json(run / "manifest.json", manifest)
    summary = {
        "complete": True,
        "run_dir": str(run),
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "planned_requests": len(plan),
        "successful_requests": sum(a["status"] == "ok" for a in attempts),
        "outcomes": outcomes,
        "inference_performed": False,
        "references_replaced": False,
        "policy": POLICY,
    }
    atomic_json(run / "summary.json", summary)
    audit(run / "summary.json")
    rows = [
        {
            key: row.get(key)
            for key in (
                "id",
                "status",
                "sequence_bound",
                "exact_contact_set_match",
                "raw_unique_cww_contacts",
                "supplied_contacts",
            )
        }
        for row in outcomes
    ]
    report = [
        "# Raw FR3D contact provenance audit",
        "",
        POLICY["interpretation"],
        "",
        "| Record | Status | Sequence matches | Contact sets match |",
        "|---|---|---|---|",
    ]
    report += [
        f"| {r['id']} | {r['status']} | {r['sequence_bound']} | {r['exact_contact_set_match']} |"
        for r in rows
    ]
    report += [
        "",
        "All source failures and mismatches remain explicit. No reference replaced, prediction, model selection, or native fold.",
        "",
    ]
    publish(ROOT, NAME, summary, rows, list(rows[0]), "\n".join(report))
    return summary


def audit(path):
    summary = json.loads(Path(path).read_text())
    run = Path(summary["run_dir"])
    require(
        summary == json.loads((run / "summary.json").read_text()),
        "Raw-contact summary differs",
    )
    raw = (run / "manifest.json").read_bytes()
    require(digest(raw) == summary["manifest_sha256"], "Raw-contact manifest changed")
    manifest = json.loads(raw)
    require(manifest["run_dir"] == str(run), "Raw-contact run identity differs")
    protocol = audit_protocol(Path(manifest["protocol_run"]) / "manifest.json")
    require(
        protocol == json.loads((run / "protocol.json").read_text()),
        "Raw-contact protocol binding differs",
    )
    directory = Path(protocol["run_dir"])
    binding = json.loads((directory / "binding.json").read_text())
    plan = request_plan(binding)
    attempts = json.loads((run / "attempts.json").read_text())
    require(
        len(attempts) == len(plan)
        and all(
            all(attempt.get(k) == value for k, value in entry.items())
            and attempt["status"] in ("ok", "error")
            for attempt, entry in zip(attempts, plan, strict=True)
        ),
        "Raw-contact request inventory differs",
    )
    expected = {"protocol.json", "attempts.json"} | {
        a["filename"] for a in attempts if "sha256" in a
    }
    for a in attempts:
        if a["status"] == "ok":
            require(
                "sha256" in a
                and digest((run / a["filename"]).read_bytes()) == a["sha256"],
                "Raw-contact response changed",
            )
    exposed = []
    for a in attempts:
        if a["status"] == "ok":
            try:
                sequence, _ = sequence_from_response((run / a["filename"]).read_bytes())
                exposed.append(
                    {
                        "sequence": sequence,
                        "family_id": a["family_id"],
                        "pdb_accession": a["pdb_accession"],
                    }
                )
            except (ValueError, KeyError, TypeError):
                pass
    event = manifest["exposure_event"]
    require(bool(event) == bool(exposed), "Raw-contact exposure inventory differs")
    if event:
        path = Path(event["path"])
        expected.add(str(path.relative_to(run)))
        require(
            digest(path.read_bytes()) == event["sha256"]
            and read_exposure(path)["records"]
            == exposure_records(exposed, str(run) + " validation_started"),
            "Raw-contact source exposure differs",
        )
    require(
        set(manifest["snapshot_sha256"]) == expected,
        "Raw-contact retained-file inventory differs",
    )
    for name, sha in manifest["snapshot_sha256"].items():
        require(
            digest((run / name).read_bytes()) == sha, "Raw-contact snapshot changed"
        )
    require(
        summary
        == {
            "complete": True,
            "run_dir": str(run),
            "manifest_sha256": digest(raw),
            "planned_requests": len(plan),
            "successful_requests": sum(a["status"] == "ok" for a in attempts),
            "outcomes": analyze(run, binding, attempts),
            "inference_performed": False,
            "references_replaced": False,
            "policy": POLICY,
        },
        "Raw-contact replay differs",
    )
    print(
        "Raw-contact provenance replay passed; no network, prediction or replacement."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--binding",
        type=Path,
        default=ROOT / "results/structure_derived_binding_summary.json",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--verify", type=Path)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "results/structure_contact_provenance_protocol.json",
    )
    args = parser.parse_args()
    if args.verify:
        audit(args.verify)
    elif args.acquire:
        acquire(args.protocol)
    else:
        freeze(args.binding)


if __name__ == "__main__":
    main()
