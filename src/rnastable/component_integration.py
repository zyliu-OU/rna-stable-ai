"""Stage 2 fixed-input contracts for the RNAfold/STRAND/RiboNN integration.

No candidate generation or biological stability/translation claims are made here.
Historical folding and optimization implementations deliberately remain untouched.
"""
from dataclasses import dataclass, asdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import time

from Bio.Seq import Seq


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class Transcript:
    """Canonical unmodified RNA; boundaries are zero-based, half-open.

    The complete supplied transcript, including any supplied poly(A), counts
    toward scope. No implicit cap, tail or nucleotide modification is added.
    Version 1 deliberately supports the standard genetic code only.
    """
    tx_id: str
    sequence: str
    cds_start: int
    cds_end: int
    provenance: str
    assay_context: str
    translation_table: int = 1

    def __post_init__(self):
        if not isinstance(self.tx_id, str) or not self.tx_id.strip() or any(c in self.tx_id for c in '\t\n\r'):
            raise ValueError("Transcript ID must be nonempty and TSV-safe")
        if not isinstance(self.sequence, str) or not 1 <= len(self.sequence) < 3000:
            raise ValueError("Complete transcript must contain 1–2,999 nucleotides")
        if set(self.sequence) - set("ACGU"):
            raise ValueError("Explicit canonical uppercase RNA required; no silent normalization")
        if (type(self.cds_start) is not int or type(self.cds_end) is not int
                or not 0 <= self.cds_start < self.cds_end <= len(self.sequence)):
            raise ValueError("Invalid zero-based half-open CDS boundaries")
        if self.translation_table != 1:
            raise ValueError("Integration v1 supports translation table 1 only")
        if not self.provenance or not self.assay_context:
            raise ValueError("Explicit provenance and assay context required")
        # cds=True enforces start/stop, complete frame, and absence of internal stops.
        Seq(self.cds).translate(table=self.translation_table, cds=True)

    @property
    def cds(self):
        return self.sequence[self.cds_start:self.cds_end]

    @property
    def sha256(self):
        return digest(self.sequence)

    @property
    def identity_sha256(self):
        # Annotation and context changes must invalidate cached records too.
        return digest(json.dumps(asdict(self), sort_keys=True))

    def ribonn_exclusion(self):
        if self.cds_start > 1381:
            return "utr5_exceeds_1381_nt"
        if len(self.sequence) - self.cds_start > 11937:
            return "cds_plus_utr3_exceeds_11937_nt"
        return None


def validate_pool(records):
    if len({r.tx_id for r in records}) != len(records):
        raise ValueError("Duplicate transcript ID")


def check_synonymous_edit(parent, candidate, protected_positions=(), max_edits=0):
    """Check a supplied pair; this function never proposes sequence edits."""
    if type(max_edits) is not int or max_edits < 0:
        raise ValueError("Invalid mutation budget")
    for p in protected_positions:
        if type(p) is not int or not 0 <= p < len(parent.sequence):
            raise ValueError("Invalid protected position")
    if ((parent.cds_start, parent.cds_end, len(parent.sequence), parent.translation_table)
            != (candidate.cds_start, candidate.cds_end, len(candidate.sequence), candidate.translation_table)):
        return False
    a, b = parent.sequence, candidate.sequence
    if a[:parent.cds_start] != b[:parent.cds_start] or a[parent.cds_end:] != b[parent.cds_end:]:
        return False
    if parent.cds[:3] != candidate.cds[:3] or parent.cds[-3:] != candidate.cds[-3:]:
        return False
    if any(a[p] != b[p] for p in protected_positions):
        return False
    return (sum(x != y for x, y in zip(a, b)) <= max_edits
            and Seq(parent.cds).translate(cds=True) == Seq(candidate.cds).translate(cds=True))


def classify_construct_edit(parent, candidate):
    """Classify a supplied pair against the assay_definition_v3 design space.

    check_synonymous_edit holds a narrower frozen contract: identical transcript
    geometry and untouched UTRs. That contract cannot express the recorded design
    space, which opens 5' UTR, ORF and 3' UTR while requiring ORF edits to be
    synonymous, so a UTR substitution is rejected there as if it were a missense
    edit. This function separates the two questions and never proposes an edit.

    Protein invariance is the binding constraint: the encoded protein must be
    exactly the parent protein, so an in-frame indel that changes protein length
    is invalid, not merely flagged. Returns a verdict; raises only on bad input.
    """
    for r in (parent, candidate):
        if not isinstance(r, Transcript):
            raise ValueError("Both arguments must be Transcript records")
    if parent.translation_table != candidate.translation_table:
        raise ValueError("Translation table differs; no cross-table comparison")

    regions = {}
    for name, a, b in (
        ("utr5", parent.sequence[:parent.cds_start], candidate.sequence[:candidate.cds_start]),
        ("orf", parent.cds, candidate.cds),
        ("utr3", parent.sequence[parent.cds_end:], candidate.sequence[candidate.cds_end:]),
    ):
        regions[name] = {
            "parent_length_nt": len(a),
            "candidate_length_nt": len(b),
            "length_delta_nt": len(b) - len(a),
            "identical": a == b,
            # Position-wise substitutions are only defined at equal length.
            "substitutions": sum(x != y for x, y in zip(a, b)) if len(a) == len(b) else None,
        }

    parent_protein = str(Seq(parent.cds).translate(table=parent.translation_table, cds=True))
    candidate_protein = str(Seq(candidate.cds).translate(table=candidate.translation_table, cds=True))
    protein_invariant = parent_protein == candidate_protein
    orf_changed = not regions["orf"]["identical"]

    reasons = []
    if not protein_invariant:
        reasons.append("orf_edit_changes_encoded_protein")
    if orf_changed and regions["orf"]["length_delta_nt"] != 0:
        reasons.append("orf_length_changed")
    if candidate.ribonn_exclusion():
        reasons.append("candidate_" + candidate.ribonn_exclusion())

    changed = sorted(n for n, d in regions.items() if not d["identical"])
    return {
        "parent_tx_id": parent.tx_id,
        "candidate_tx_id": candidate.tx_id,
        "parent_identity_sha256": parent.identity_sha256,
        "candidate_identity_sha256": candidate.identity_sha256,
        "regions": regions,
        "regions_changed": changed,
        "protein_invariant": protein_invariant,
        "parent_protein_sha256": digest(parent_protein),
        "candidate_protein_sha256": digest(candidate_protein),
        "orf_synonymous": orf_changed and protein_invariant,
        "orf_unchanged": not orf_changed,
        "transcript_length_delta_nt": len(candidate.sequence) - len(parent.sequence),
        "valid_under_assay_v3": not reasons,
        "invalid_reasons": reasons,
        # Recorded because assay_definition_v3 warns the regions are not
        # independent in their effect on model scores.
        "model_input_coupling": {
            "strand_features_move": bool(changed),
            "ribonn_region_sizes_move": bool(
                regions["utr5"]["length_delta_nt"] or regions["orf"]["length_delta_nt"]
                or regions["utr3"]["length_delta_nt"]
            ),
            "candidate_ribonn_exclusion": candidate.ribonn_exclusion(),
        },
        "no_claim": "Edit validity is a sequence-level check and establishes no stability, translation or expression benefit.",
    }


def export_ribonn(records, path):
    """Export full-transcript input to avoid empty-UTR NaN parsing upstream."""
    validate_pool(records)
    exclusions = {}
    with Path(path).open("x", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["tx_id", "tx_sequence", "utr5_size", "cds_size"])
        for r in records:
            reason = r.ribonn_exclusion()
            if reason:
                exclusions[r.tx_id] = reason
            else:
                writer.writerow([r.tx_id, r.sequence, r.cds_start, r.cds_end-r.cds_start])
    return exclusions


def join_ribonn_predictions(records, rows, score_column, expected_folds):
    """Audit identity and the upstream one-row-per-transcript-per-fold output.

    Upstream averages top-k checkpoints within each fold. We require an explicit
    complete fold inventory before averaging folds, preventing silent row loss.
    Rows must carry tx_sequence so sequence identity is verified, not inferred.
    """
    validate_pool(records)
    expected_folds = set(expected_folds)
    if not expected_folds or any(type(x) is not int for x in expected_folds):
        raise ValueError("Explicit integer fold inventory required")
    by_id = {r.tx_id: r for r in records}
    scores = {r.tx_id: {} for r in records}
    for row in rows:
        rid = row["tx_id"]
        if rid not in by_id:
            raise ValueError(f"Unknown RiboNN output ID: {rid}")
        r = by_id[rid]
        if r.ribonn_exclusion():
            raise ValueError(f"Excluded record returned a prediction: {rid}")
        if not isinstance(row["tx_sequence"], str) or row["tx_sequence"].replace("T", "U") != r.sequence:
            raise ValueError(f"Sequence mismatch: {rid}")
        raw_fold = row["fold"]
        fold = int(raw_fold)
        if str(fold) != str(raw_fold) or fold not in expected_folds or fold in scores[rid]:
            raise ValueError(f"Unexpected or duplicate fold: {rid}")
        score = float(row[score_column])
        if not math.isfinite(score):
            raise ValueError(f"Nonfinite RiboNN score: {rid}")
        scores[rid][fold] = score
    output = []
    for r in records:
        reason = r.ribonn_exclusion()
        if reason:
            output.append({"tx_id": r.tx_id, "input_sha256": r.sha256,
                           "status": "excluded", "reason": reason})
            continue
        if set(scores[r.tx_id]) != expected_folds:
            raise ValueError(f"Missing RiboNN fold predictions: {r.tx_id}")
        output.append({"tx_id": r.tx_id, "input_sha256": r.sha256, "status": "ok",
                       "score_column": score_column, "fold_scores": scores[r.tx_id],
                       "mean_score": sum(scores[r.tx_id].values())/len(expected_folds),
                       "interpretation": "released task score; cell-free calibration pending"})
    return output


def strand_alo(paired_probability):
    """Released R rule: bound values outside (0,1), then mean natural log odds.

    This reproduces an arithmetic rule, not provenance of feature extraction.
    Positive values below 1e-10 are NOT clipped by the R script. Released input
    data contain values slightly above one; retain and report those separately.
    This arithmetic helper reproduces R's bounding rule and is not a probability
    validator. Newly computed ViennaRNA probabilities are validated by the worker.
    """
    values = list(paired_probability)
    if not values or any(not math.isfinite(x) for x in values):
        raise ValueError("Finite positional values required")
    values = [1e-10 if x <= 0 else (1-1e-10 if x >= 1 else x) for x in values]
    return sum(math.log(x/(1-x)) for x in values)/len(values)


def fold_fixed_input(record, timeout=120, temperature=37.0):
    """Run ensemble folding in a fresh worker, bounding wall time and globals."""
    payload = {"sequence": record.sequence, "temperature": temperature}
    start = time.perf_counter()
    try:
        process = subprocess.run([sys.executable, "-m", "rnastable.ensemble_worker"],
                                 input=json.dumps(payload), text=True, capture_output=True,
                                 timeout=timeout, check=True)
        result = json.loads(process.stdout)
    except subprocess.TimeoutExpired:
        result = {"status": "excluded", "reason": "rnafold_timeout", "timeout_seconds": timeout}
    except subprocess.CalledProcessError as exc:
        result = {"status": "error", "reason": "rnafold_worker_failed", "stderr": exc.stderr}
    result.update({"tx_id": record.tx_id, "input_sha256": record.sha256,
                   "identity_sha256": record.identity_sha256,
                   "subprocess_wall_seconds": time.perf_counter()-start})
    return result
