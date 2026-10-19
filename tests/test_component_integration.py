import csv
from dataclasses import replace
import json
import math

import pytest
from Bio.Data.CodonTable import TranslationError

from rnastable.component_integration import (
    Transcript, check_synonymous_edit, export_ribonn, fold_fixed_input,
    join_ribonn_predictions, strand_alo,
)


def transcript(rid="parent", cds="AUGGCUUAA", utr5="GGG", utr3="CCC"):
    return Transcript(rid, utr5+cds+utr3, len(utr5), len(utr5)+len(cds),
                      "unit-test synthetic", "no biological measurements")


@pytest.mark.parametrize("cds", ["AUGGCU", "AUGUGAUAA", "AUGGCUAUAA"])
def test_reject_incomplete_internal_stop_and_out_of_frame(cds):
    with pytest.raises(TranslationError):
        transcript(cds=cds)


def test_annotation_and_identity_guards():
    a = transcript()
    assert a.sha256 == replace(a, assay_context="different assay").sha256
    assert a.identity_sha256 != replace(a, assay_context="different assay").identity_sha256
    with pytest.raises(ValueError):
        replace(a, sequence=a.sequence.replace("U", "T"))
    with pytest.raises(ValueError):
        replace(a, cds_start=True)
    with pytest.raises(ValueError):
        transcript(utr5="A"*3000)


def test_synonymous_edit_preserves_annotated_protein_and_utrs():
    parent = transcript()
    synonymous = transcript("syn", "AUGGCCUAA")
    missense = transcript("wrong", "AUGGACUAA")
    assert check_synonymous_edit(parent, synonymous, max_edits=1)
    assert not check_synonymous_edit(parent, synonymous, max_edits=0)
    assert not check_synonymous_edit(parent, synonymous, protected_positions=[8], max_edits=1)
    assert not check_synonymous_edit(parent, missense, max_edits=2)
    assert not check_synonymous_edit(parent, transcript("utr", utr5="CCC"), max_edits=3)
    assert not check_synonymous_edit(parent, transcript("stop", "AUGGCUUGA"), max_edits=2)


def test_empty_utr_export_and_upstream_domain_exclusion(tmp_path):
    a, b = transcript(utr5="", utr3=""), transcript("excluded", utr5="A"*1382)
    p = tmp_path/"input.tsv"
    assert export_ribonn([a,b], p) == {"excluded": "utr5_exceeds_1381_nt"}
    rows = list(csv.DictReader(p.open(), delimiter="\t"))
    assert rows[0] == {"tx_id": "parent", "tx_sequence": a.sequence, "utr5_size": "0", "cds_size": "9"}
    with pytest.raises(FileExistsError):
        export_ribonn([a], p)
    with pytest.raises(ValueError):
        export_ribonn([a,a], tmp_path/"duplicate.tsv")


def prediction(r, fold, score):
    return {"tx_id": r.tx_id, "tx_sequence": r.sequence.replace("U", "T"),
            "fold": str(fold), "task": str(score)}


def test_join_shuffled_fold_rows_by_identity():
    a, b, excluded = transcript(), transcript("b", "AUGGCCUAA"), transcript("excluded", utr5="A"*1382)
    rows = [prediction(b,1,9), prediction(a,0,1), prediction(b,0,5), prediction(a,1,3)]
    output = join_ribonn_predictions([a,b,excluded], rows, "task", [0,1])
    assert [r.get("mean_score") for r in output] == [2,7,None]
    assert output[2]["status"] == "excluded"


@pytest.mark.parametrize("problem", ["missing", "duplicate", "unknown", "sequence", "nonfinite", "fold"])
def test_join_rejects_corrupt_outputs(problem):
    a = transcript()
    rows = [prediction(a,0,1), prediction(a,1,3)]
    if problem == "missing": rows.pop()
    if problem == "duplicate": rows.append(rows[0])
    if problem == "unknown": rows[0]["tx_id"] = "other"
    if problem == "sequence": rows[0]["tx_sequence"] = "A"*len(a.sequence)
    if problem == "nonfinite": rows[0]["task"] = "nan"
    if problem == "fold": rows[0]["fold"] = "2"
    with pytest.raises(ValueError):
        join_ribonn_predictions([a], rows, "task", [0,1])


def test_alo_matches_endpoint_only_rule():
    assert strand_alo([0.2,0.8]) == pytest.approx(0)
    assert math.isfinite(strand_alo([0,1]))
    assert strand_alo([1.0005]) == strand_alo([1])
    assert strand_alo([1e-15]) == pytest.approx(math.log(1e-15/(1-1e-15)))
    with pytest.raises(ValueError):
        strand_alo([float("nan")])


def test_partition_function_probability_and_energy_invariants():
    result = fold_fixed_input(transcript())
    assert result["status"] == "ok"
    assert result["ensemble_free_energy_kcal_mol"] <= result["mfe_kcal_mol"]+1e-5
    assert len(result["paired_probability_per_position"]) == 15
    for p,u in zip(result["paired_probability_per_position"], result["unpaired_probability_per_position"]):
        assert 0 <= p <= 1
        assert p+u == pytest.approx(1)
    assert result["feature_candidates"]["aup"] == pytest.approx(
        sum(result["unpaired_probability_per_position"])/15)
    json.dumps(result, allow_nan=False)
