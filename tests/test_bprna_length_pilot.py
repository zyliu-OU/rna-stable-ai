"""The longer-training pilot keeps its comparison development-only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_bprna_length_pilot import expected_summary  # noqa: E402


def test_summary_never_claims_independent_accuracy():
    train = [{"sequence": "A" * 400} for _ in range(88)]
    validation = [{"sequence": "A" * 200} for _ in range(22)]
    training = {"selected_validation_full_pair_f1": 0.5, "selected_epoch": 2}
    control = {"training": {"selected_validation_full_pair_f1": 0.4}}
    result = expected_summary(Path("/tmp/example"), b"manifest", train,
                              validation, training, control)
    assert result["development_f1_difference"] > 0
    assert result["new_longer_train_records"] == 27
    assert result["test_evaluated"] is False
    assert result["independent_accuracy_claim"] is False
    assert result["model_defaults_changed"] is False
