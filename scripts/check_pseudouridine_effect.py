#!/usr/bin/env python3
"""Is a uridine modification's effect constant across constructs?

Every ranking claim this project makes about the collaborator's panel rests on
one unverified assumption: that because every uridine is N1-methylpseudouridine
and the modification is constant across the panel, it shifts every construct by
the same factor and leaves the ORDER unchanged. If the effect instead depends on
sequence, predictions made on the unmodified sequence do not order the modified
molecules.

Leppek et al. 2022 measured six constructs both unmodified and
pseudouridine-modified, twice over, by two independent readouts: in-solution
half-life, and luciferase protein output in a 3 x 2 factorial of three 5'UTRs by
two CDSs. That is small, but it is the only evidence available and the
alternative is none.

The modification here is pseudouridine, NOT N1-methylpseudouridine. Those are
different nucleosides. A construct-dependent effect is evidence that a uridine
modification's effect CAN depend on sequence; it is not a measurement of m1-psi.

Criteria are declared in `configs/pseudouridine_effect_check_v1_2026-10-20.json`,
including the disclosure that they were written after the raw values were visible
during inspection, which is a weaker guarantee than the half-life validation.
The source workbook is not redistributed; its hash is verified before any row is
read.
"""
# ruff: noqa: E402 -- Local CLI source bootstrap.

import argparse
import hashlib
import json
import math
import statistics
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/pseudouridine_effect_check_v1_2026-10-20.json"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def read_sheet(path, sheet):
    """Read one sheet with the standard library only; untrusted third-party data."""
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        targets = {r.get("Id"): r.get("Target") for r in
                   ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        member = None
        for entry in workbook.iter(f"{NS}sheet"):
            if entry.get("name") == sheet:
                member = "xl/" + targets[entry.get(f"{REL}id")].lstrip("/").replace("xl/", "")
        if member is None:
            raise SystemExit(f"Sheet {sheet!r} not found")
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).iter(f"{NS}si"):
                shared.append("".join(t.text or "" for t in item.iter(f"{NS}t")))

        def value(cell):
            node = cell.find(f"{NS}v")
            text = node.text if node is not None else ""
            if cell.get("t") == "s" and text:
                text = shared[int(text)]
            return text or ""

        rows = []
        for row in ET.fromstring(archive.read(member)).iter(f"{NS}row"):
            slots = {}
            for cell in row.iter(f"{NS}c"):
                column = "".join(ch for ch in (cell.get("r") or "") if ch.isalpha())
                slots[column] = value(cell)
            rows.append([slots[k] for k in sorted(slots, key=lambda k: (len(k), k))])
    header = rows[0]
    return [dict(zip(header, r)) for r in rows[1:] if any(r)]


def dispersion_verdict(effects, uncertainties, rule):
    """Compare the spread of the effect against the noise on the effect."""
    between = statistics.stdev(effects) if len(effects) > 1 else 0.0
    within = statistics.median(uncertainties) if uncertainties else None
    ratio = (between / within) if within else None
    if ratio is None:
        verdict = "undetermined"
    elif ratio <= 1.0:
        verdict = "consistent_with_constant"
    elif ratio <= 2.0:
        verdict = "ambiguous"
    else:
        verdict = "construct_dependent"
    return {
        "between_construct_sd": between,
        "median_within_construct_uncertainty": within,
        "dispersion_ratio": ratio,
        "verdict": verdict,
        "decision_rule": rule,
    }


def half_life_arm(workbook, rule):
    rows = read_sheet(workbook, "Fig_S8b")
    paired = defaultdict(dict)
    for row in rows:
        name = row["Sample"]
        state = row["Nucleotide"]
        paired[name][state] = (float(row["half-life"]), float(row["half-life_err"]))
    constructs = []
    for name, states in paired.items():
        if {"Unmodified", "PSU"} - set(states):
            continue
        (u, ue), (p, pe) = states["Unmodified"], states["PSU"]
        log2fc = math.log2(p / u)
        # Propagated in log2 space: sd(log2 x) = sd(x) / (x ln2).
        uncertainty = math.sqrt((pe / (p * math.log(2))) ** 2 + (ue / (u * math.log(2))) ** 2)
        constructs.append({
            "construct": name, "unmodified_hours": u, "psu_hours": p,
            "fold_change": p / u, "log2_fold_change": log2fc,
            "log2_fold_change_uncertainty": uncertainty,
        })
    constructs.sort(key=lambda c: c["fold_change"])
    effects = [c["log2_fold_change"] for c in constructs]
    return {
        "readout": "in_solution_half_life_hours",
        "n_constructs": len(constructs),
        "fold_change_range": [constructs[0]["fold_change"], constructs[-1]["fold_change"]],
        "fold_change_spread": constructs[-1]["fold_change"] / constructs[0]["fold_change"],
        "mean_fold_change": statistics.fmean(c["fold_change"] for c in constructs),
        "all_same_direction": all(c["fold_change"] > 1 for c in constructs)
                              or all(c["fold_change"] < 1 for c in constructs),
        "dispersion": dispersion_verdict(
            effects, [c["log2_fold_change_uncertainty"] for c in constructs], rule),
        "constructs": constructs,
    }


def protein_arm(workbook, rule):
    rows = read_sheet(workbook, "Fig_4a")
    cells = defaultdict(list)
    meta = {}
    for row in rows:
        if not row.get("Nluc") or not row.get("Fluc"):
            continue
        nluc, fluc = float(row["Nluc"]), float(row["Fluc"])
        if nluc <= 0 or fluc <= 0:
            continue
        cells[(row["ID"], row["Time"], row["PSU"])].append(math.log2(nluc / fluc))
        meta[row["ID"]] = {"utr5": row["5UTR"], "cds": row["CDS"]}
    ids = sorted({key[0] for key in cells})
    paired_ids = [i for i in ids
                  if all((i, t, s) in cells for t in ("6h", "24h") for s in ("Unmod", "PSU"))]
    arms = {}
    for timepoint in ("6h", "24h"):
        constructs = []
        for identifier in paired_ids:
            unmod = cells[(identifier, timepoint, "Unmod")]
            psu = cells[(identifier, timepoint, "PSU")]
            effect = statistics.fmean(psu) - statistics.fmean(unmod)
            # Standard error of a difference of two means.
            uncertainty = math.sqrt(
                (statistics.stdev(psu) ** 2 / len(psu) if len(psu) > 1 else 0)
                + (statistics.stdev(unmod) ** 2 / len(unmod) if len(unmod) > 1 else 0))
            constructs.append({
                "id": identifier, "utr5": meta[identifier]["utr5"],
                "cds": meta[identifier]["cds"],
                "replicates": {"unmodified": len(unmod), "psu": len(psu)},
                "log2_effect": effect, "log2_effect_standard_error": uncertainty,
                "fold_change": 2 ** effect,
            })
        constructs.sort(key=lambda c: c["fold_change"])
        by_utr = defaultdict(list)
        by_cds = defaultdict(list)
        for c in constructs:
            by_utr[c["utr5"]].append(c["log2_effect"])
            by_cds[c["cds"]].append(c["log2_effect"])
        arms[timepoint] = {
            "n_constructs": len(constructs),
            "fold_change_range": [constructs[0]["fold_change"], constructs[-1]["fold_change"]],
            "fold_change_spread": constructs[-1]["fold_change"] / constructs[0]["fold_change"],
            "mean_fold_change": statistics.fmean(c["fold_change"] for c in constructs),
            "all_same_direction": all(c["fold_change"] > 1 for c in constructs)
                                  or all(c["fold_change"] < 1 for c in constructs),
            "dispersion": dispersion_verdict(
                [c["log2_effect"] for c in constructs],
                [c["log2_effect_standard_error"] for c in constructs], rule),
            "factorial": {
                "by_utr5": {k: statistics.fmean(v) for k, v in sorted(by_utr.items())},
                "by_cds": {k: statistics.fmean(v) for k, v in sorted(by_cds.items())},
            },
            "constructs": constructs,
        }
    return {"readout": "protein_output_log2_nluc_over_fluc", "timepoints": arms}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--out", default="results/pseudouridine_effect_runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    protocol = json.loads(PROTOCOL.read_text())
    digest = hashlib.sha256(Path(args.workbook).read_bytes()).hexdigest()
    if digest != protocol["source"]["file_sha256"]:
        raise SystemExit(f"Workbook hash mismatch\n  expected {protocol['source']['file_sha256']}"
                         f"\n  observed {digest}")
    print(f"workbook hash verified: {digest[:16]}…", flush=True)
    rule = protocol["declared_criteria"]["decision_rule"]

    half_life = half_life_arm(args.workbook, rule)
    protein = protein_arm(args.workbook, rule)

    verdicts = [half_life["dispersion"]["verdict"]] + [
        arm["dispersion"]["verdict"] for arm in protein["timepoints"].values()]
    agreement = len(set(verdicts)) == 1

    payload = {
        "purpose": protocol["purpose"],
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "workbook_hash_verified": True,
        "modification_identity": protocol["modification_identity"],
        "disclosure_about_declaration_order": protocol["disclosure_about_declaration_order"],
        "in_solution_half_life": half_life,
        "protein_output": protein,
        "verdicts": {"half_life": half_life["dispersion"]["verdict"],
                     **{f"protein_{t}": a["dispersion"]["verdict"]
                        for t, a in protein["timepoints"].items()}},
        "readouts_agree": agreement,
        "consequence_for_this_project": (
            protocol["why_this_matters"]["consequence_if_the_effect_is_construct_dependent"]
            if "construct_dependent" in verdicts else
            "The ranking argument is not contradicted by this evidence for pseudouridine. "
            "It remains untested for N1-methylpseudouridine."),
        "what_this_cannot_establish": protocol["what_this_cannot_establish"],
        "no_claim": [
            "This tests pseudouridine, NOT N1-methylpseudouridine. They are different "
            "nucleosides and no quantitative statement about m1-psi follows.",
            "Six constructs support no significance claim and none is made.",
            "A dispersion ratio is a description of six numbers against their own error bars.",
            "Nothing here says the predictions are correct, only whether a modification would "
            "preserve their order.",
        ],
    }

    def show(label, block):
        d = block["dispersion"]
        print(f"\n=== {label} ===")
        print(f"  n={block['n_constructs']}  fold change "
              f"{block['fold_change_range'][0]:.3f} .. {block['fold_change_range'][1]:.3f}  "
              f"(spread {block['fold_change_spread']:.2f}x, mean {block['mean_fold_change']:.3f}x, "
              f"same direction {block['all_same_direction']})")
        print(f"  between-construct SD {d['between_construct_sd']:.4f}  "
              f"median uncertainty {d['median_within_construct_uncertainty']:.4f}  "
              f"ratio {d['dispersion_ratio']:.2f}  -> {d['verdict'].upper()}")

    show("in-solution half-life", half_life)
    for timepoint, arm in protein["timepoints"].items():
        show(f"protein output, {timepoint}", arm)
        print("  by 5'UTR: " + "  ".join(
            f"{k[:18]} {v:+.3f}" for k, v in arm["factorial"]["by_utr5"].items()))
        print("  by CDS  : " + "  ".join(
            f"{k} {v:+.3f}" for k, v in arm["factorial"]["by_cds"].items()))
    print(f"\nreadouts agree: {agreement}   verdicts: {payload['verdicts']}")

    if args.dry_run:
        print("\nDry run: nothing written.", file=sys.stderr)
        return 0
    out = ROOT / args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\nWrote {out}/summary.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
