import copy
import json
from pathlib import Path

import pytest

from rnastable.strand_reference import linear_prediction, replay_reference, reference_record

FIXTURE = Path(__file__).parent/"fixtures/strand_reference_r_export_2026-10-18.json"


def test_exported_raw_unit_coefficients_reproduce_r_predictions():
    fixture = json.loads(FIXTURE.read_text())
    # Includes nLuc, eGFP and exploratory MEV reference inputs. Fixture values
    # were produced by R pls, independently of Python's coefficient evaluator.
    for example in fixture["examples"]:
        record = example["record"]
        actual = replay_reference(fixture["model"],record)
        assert actual["predicted_half_life"] == pytest.approx(example["R_prediction"],abs=1e-12)
        assert actual["independent_validation"] is False


@pytest.mark.parametrize("mutation",["gc_fraction","missing_alo","sequence_hash","name","cohort"])
def test_reference_gate_rejects_modified_features_or_identity(mutation):
    fixture = json.loads(FIXTURE.read_text())
    record = copy.deepcopy(fixture["examples"][0]["record"])
    if mutation=="gc_fraction": record["features"]["GC"] /= 100
    if mutation=="missing_alo": record["features"].pop("alo")
    if mutation=="sequence_hash": record["input_sha256"] = "0"*64
    if mutation=="name": record["name"] = "new_candidate"
    if mutation=="cohort": record["cohort"] = "new_data"
    with pytest.raises(ValueError,match="frozen inventory"):
        replay_reference(fixture["model"],record)


def test_rnafold_substitution_and_enabled_candidate_scoring_rejected():
    fixture = json.loads(FIXTURE.read_text())
    record = fixture["examples"][0]["record"]
    record["feature_source"] = "ViennaRNA"
    with pytest.raises(ValueError,match="compatibility/calibration"):
        replay_reference(fixture["model"],record)
    fixture["model"]["new_sequence_scoring_enabled"] = True
    with pytest.raises(ValueError,match="Reference-only"):
        replay_reference(fixture["model"],record)


def test_finite_features_required_and_order_matched_by_name():
    fixture = json.loads(FIXTURE.read_text())
    component = fixture["model"]["component"]
    record = fixture["examples"][0]["record"]
    reversed_order = dict(reversed(list(record["features"].items())))
    assert linear_prediction(component,reversed_order)==pytest.approx(fixture["examples"][0]["R_prediction"])
    reversed_order["aup"] = float("nan")
    with pytest.raises(ValueError,match="Finite"):
        linear_prediction(component,reversed_order)


def test_reference_input_lengths_are_audited():
    row = {"name":"bad","sequence":"ACGU","seq_len":"4","bpp_per_pos":"[0, 0, 0]",
           "energy":"0","GC":"50","aup":"1","in_solution_half_life":"1"}
    with pytest.raises(ValueError,match="length mismatch"):
        reference_record(row,"test")
