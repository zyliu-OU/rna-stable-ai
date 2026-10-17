"""Longer validation selection stays fixed before contact labels are read."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_long_validation_family import checked_config, select_candidates  # noqa: E402


def test_candidate_screen_respects_prior_exposure_and_length_before_labels():
    config = {"schema_version": 1,
              "stage": "longer_family_development_validation_screen",
              "families": ["RF02001", "RF02462", "RF02540", "RF02541"],
              "minimum_length_nt": 400, "maximum_length_nt": 4999,
              "sequence_similarity_threshold": 0.8,
              "candidate_cap_per_family": 3,
              "minimum_complete_per_family": 2, "minimum_complete_total": 6,
              "replace_failed_families": False, "development_validation_only": True,
              "model_inference_authorized_at_screen": False,
              "independent_test_claim": False}
    exposed = [{"sequence": "A" * 400, "family_id": "RF00010"}]
    checked_config(config, exposed)
    alignments = {"RF02001": {"sequences": {
        "a": "A" * 400, "b": "G" * 200 + "C" * 200,
        "c": "A" * 399, "d": "C" * 200 + "G" * 200}}}
    selected, decisions = select_candidates(alignments, config, exposed)
    assert [row["id"] for row in selected] == ["RF02001:b", "RF02001:d"]
    assert [row["reason"] for row in decisions] == [
        "prior_exposure_overlap", "selected_before_pair_parsing",
        "outside_length_scope", "selected_before_pair_parsing"]
    assert all("pairs" not in row for row in selected)
