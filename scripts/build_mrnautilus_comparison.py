"""Assemble the mRNAutilus comparison artifact from the two runs.

The runs themselves execute in an isolated environment outside this repository,
because mRNAutilus needs torch, flash-attn and its own 1.78 GB checkpoint, none
of which this project depends on or redistributes. This script takes those two
result files, re-derives this project's side from its own stored artifacts, and
writes the comparison with every limitation attached.

Usage:
    python scripts/build_mrnautilus_comparison.py THEIR_HL_JSON THEIR_POOL_JSON
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/mrnautilus_comparison_v1_2026-10-20.json"
VALIDATION = sorted(glob.glob(str(ROOT / "results/external_validation_leppek_runs/*/summary.json")))
POOL = sorted(glob.glob(str(ROOT / "results/full_transcript_design_runs/*/summary.json")))
BINS = ((1.00, 1.10), (1.10, 1.25), (1.25, 1.50), (1.50, 2.00), (2.00, math.inf))


def bin_key(lo, hi):
    return f"{lo:.2f}-{hi:.2f}" if hi != math.inf else f"above_{lo:.2f}"


def concordance(pred, meas):
    out = {}
    for lo, hi in BINS:
        pairs = conc = 0
        for i in range(len(meas)):
            for j in range(i + 1, len(meas)):
                a, b = sorted((meas[i], meas[j]))
                if a <= 0:
                    continue
                if lo <= b / a < hi:
                    pairs += 1
                    conc += (pred[i] < pred[j]) == (meas[i] < meas[j])
        out[bin_key(lo, hi)] = {"pairs": pairs,
                                "concordance": conc / pairs if pairs else None}
    return out


def spearman(xs, ys):
    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            shared = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = shared
            i = j + 1
        return out
    return statistics.correlation(ranks(xs), ranks(ys))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("their_half_life")
    parser.add_argument("their_pool")
    parser.add_argument("--out", default="results/mrnautilus_comparison_runs")
    args = parser.parse_args(argv)

    their_hl = json.loads(Path(args.their_half_life).read_text())["their_half_life_head"]
    their_pool = json.loads(Path(args.their_pool).read_text())
    rows = json.loads(Path(VALIDATION[-1]).read_text())["rows"]
    ablation = json.loads(
        Path(sorted(glob.glob(str(ROOT / "results/stability_ablation_runs/*/summary.json")))[-1]
             ).read_text())
    pool_run = json.loads(Path(POOL[-1]).read_text())

    measured = [r["measured_hours"] for r in rows]
    ours = [r["predicted_hours"] for r in rows]
    eterna = [-r["baselines"]["SUP EternaFold FULL"] / r["length_nt"] for r in rows]
    assert their_hl["n"] == len(rows) == 123, (their_hl["n"], len(rows))
    assert their_pool["hashes_matched"] == their_pool["pool_size"] == 512

    ours_conc, eterna_conc = concordance(ours, measured), concordance(eterna, measured)
    narrow = bin_key(*BINS[0])
    inverted = [k for k, v in their_hl["concordance"].items()
                if v["concordance"] is not None and v["concordance"] < 0.50]

    summary = {
        "built_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": "Compare mRNAutilus against this project's objective on sequences "
                   "this project had already scored, before changing any of this "
                   "project's code.",
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "their_checkpoint_sha256": json.loads(PROTOCOL.read_text())
            ["their_artifacts_not_redistributed"]["checkpoint_sha256"],

        "run_b_held_out_measured_records": {
            "records": len(rows),
            "source_run": str(Path(VALIDATION[-1]).relative_to(ROOT)),
            "cds_inference": "longest ATG..in-frame-stop, no internal stop; 123 of 123",
            "spearman_vs_measured": {
                "ours": spearman(ours, measured),
                "mrnautilus_halflife_head": their_hl["spearman_vs_measured"],
                "free_eternafold_per_nucleotide": spearman(eterna, measured),
            },
            "concordance_by_measured_fold_difference": {
                bin_key(lo, hi): {
                    "pairs": ours_conc[bin_key(lo, hi)]["pairs"],
                    "ours": ours_conc[bin_key(lo, hi)]["concordance"],
                    "mrnautilus": their_hl["concordance"][bin_key(lo, hi)]["concordance"],
                    "free_eternafold_per_nucleotide": eterna_conc[bin_key(lo, hi)]["concordance"],
                    "ours_ols_refit_arm": ablation["B_fine_ordering"]
                        ["pairwise_concordance_by_measured_fold_difference"]
                        [bin_key(lo, hi)]["concordance"],
                } for lo, hi in BINS
            },
            "which_arm_is_ours": (
                "'ours' is the FROZEN production calibration, the one-component PLS whose "
                "predictions this project actually emits (held-out Spearman "
                f"{ablation['frozen_pls_reference']['held_out_spearman']:+.5f}, reproduced "
                f"here as {spearman(ours, measured):+.5f}). 'ours_ols_refit_arm' is the "
                "ordinary-least-squares refit used inside stability_ablation_v1 so that "
                "ablation variants were internally comparable. The two differ slightly: in "
                "the narrowest bin the frozen calibration gives "
                f"{ours_conc[narrow]['concordance']:.4f} and the OLS refit gives "
                f"{ablation['B_fine_ordering']['narrowest_bin_concordance']:.4f}. Earlier "
                "narrative in this project quoted the 0.5007 refit figure for the narrowest "
                "bin; the frozen calibration's own figure is 0.4936. Both are at chance and "
                "no conclusion depends on which is cited, but they are different arms and "
                "are kept labelled separately here."),
            "finding": (
                "This project's objective ranks the held-out measured records better "
                f"overall (Spearman {spearman(ours, measured):+.4f} versus "
                f"{their_hl['spearman_vs_measured']:+.4f}) and is better in every bin "
                "at 1.25x and above. mRNAutilus is slightly better in the narrowest "
                f"bin ({their_hl['concordance'][narrow]['concordance']:.4f} versus "
                f"{ours_conc[narrow]['concordance']:.4f}), but both sit at chance there "
                "and the pairs are not independent, so that difference is not a result."),
            "their_head_is_non_monotonic": {
                "bins_below_chance": inverted,
                "statement": (
                    "mRNAutilus's half-life head is strongly concordant on the largest "
                    f"differences ({their_hl['concordance']['above_2.00']['concordance']:.4f} "
                    "above 2x) yet BELOW chance in the 1.25-1.50 and 1.50-2.00 bins. A "
                    "predictor that inverts on moderate differences while succeeding on "
                    "large ones is not simply weaker; it is ordering something else."),
                "most_likely_explanation": (
                    "Their head is trained on in-cell decay (Saluki) and these records "
                    "measure in-solution degradation. The two quantities agree about "
                    "which RNAs are grossly unstable and need not agree in between. "
                    "This is the out-of-domain direction declared before the run."),
            },
            "fairness": (
                "This comparison is NOT symmetric and must not be cited as mRNAutilus "
                "being worse at its own task. On this test set this project is in-domain "
                "and mRNAutilus is out-of-domain. The only sound conclusion is about "
                "in-solution stability specifically."),
        },

        "run_a_same_pool_both_methods": {
            "pool_size": their_pool["pool_size"],
            "transcript_hashes_matched": their_pool["hashes_matched"],
            "source_run": str(Path(POOL[-1]).relative_to(ROOT)),
            "their_correlation_with_our_objective": their_pool["correlation_with_our_objective"],
            "their_correlation_with_transcript_gc": their_pool["correlation_with_transcript_gc"],
            "their_spread": their_pool["their_spread"],
            "their_reference_scores": their_pool["reference"],
            "members_scoring_above_reference": their_pool["members_scoring_above_reference"],
            "finding_their_half_life_head_is_not_a_gc_readout": (
                "This project's objective correlates with transcript GC at r = +0.99 on "
                "this pool. mRNAutilus's half-life head correlates with GC at r = "
                f"{their_pool['correlation_with_transcript_gc']['halflife']:+.4f} and with "
                "this project's objective at r = "
                f"{their_pool['correlation_with_our_objective']['halflife']:+.4f}. Their "
                "stability head is therefore reading something other than base "
                "composition, and it disagrees with this project's objective in SIGN. "
                "That is the single most useful result of this comparison: it shows the "
                "GC collapse recorded in gate v12 is a property of this project's "
                "calibration, not an unavoidable fact about the design pool."),
            "but_their_translation_head_is_substantially_gc_driven": (
                "Their translation_rate head correlates with transcript GC at r = "
                f"{their_pool['correlation_with_transcript_gc']['translation_rate']:+.4f} "
                "and their ribo_seq head at r = "
                f"{their_pool['correlation_with_transcript_gc']['ribo_seq']:+.4f}. Being a "
                "learned model does not by itself escape composition confounding; it "
                "escaped on the stability head and did not on the translation head."),
            "no_resolution_claim": (
                "Their scores spread across the pool, but their outputs are on an "
                "arbitrary normalised scale and no measurement-derived error model "
                "exists for it. This project's resolution floor was derived from "
                "replicate measurement error in hours and cannot be transferred. It is "
                "therefore NOT established that mRNAutilus resolves members this "
                "project's objective leaves unresolved. Spread is not resolution."),
        },

        "what_this_changes": [
            "The GC collapse is not forced by the design pool. An independent model "
            "scores the same 512 transcripts with near-zero GC dependence, so a "
            "stability objective over this pool that is not a GC meter is reachable.",
            "Their representation is not uniformly better: it is out-of-domain for "
            "in-solution half-life and it inverts on moderate differences there, while "
            "its translation head carries the composition confound this project has "
            "been tracking.",
            "Neither method has demonstrated resolution in the narrow bin that matters "
            "for choosing among candidate designs. Both are at chance below 1.10x.",
        ],

        "no_claim": [
            "Nothing here is a measurement. No construct in the pool has been made.",
            "No claim that this project's method is better than mRNAutilus in general. "
            "It ranks in-solution half-life better on one held-out set where "
            "mRNAutilus is out-of-domain.",
            "No claim that mRNAutilus's half-life head is poor at in-cell decay, which "
            "is what it was trained for and was not tested here.",
            "No claim that mRNAutilus resolves this design pool; spread on an "
            "arbitrary scale is not resolution against measurement error.",
            "No claim that this project's objective is free of the GC collapse. It is "
            "not. The comparison shows the collapse is escapable, not escaped.",
            "mRNAutilus code and weights are not redistributed here; only URLs and "
            "hashes are pinned.",
        ],
    }

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%f") + "Z"
    out = ROOT / args.out / stamp
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (out / "their_scores_pool.json").write_text(
        json.dumps(their_pool, indent=2, sort_keys=True) + "\n")
    (out / "their_scores_held_out.json").write_text(
        json.dumps(their_hl, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out / 'summary.json'}")
    for lo, hi in BINS:
        k = bin_key(lo, hi)
        row = summary["run_b_held_out_measured_records"]["concordance_by_measured_fold_difference"][k]
        print(f"  {k:<12} pairs {row['pairs']:>5}  ours {row['ours']:.4f}  "
              f"mRNAutilus {row['mrnautilus']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
