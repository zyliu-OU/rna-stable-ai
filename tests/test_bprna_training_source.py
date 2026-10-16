"""The new bpRNA source is training-only and bounded."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from acquire_bprna_training_source import CONFIG, validate_config  # noqa: E402


def test_training_source_config_keeps_evaluation_closed():
    config = validate_config(json.loads(CONFIG.read_text()))
    assert config["maximum_response_bytes"] == 60 * 1024 * 1024
    assert config["active_maximum_length_exclusive"] == 5000
    assert config["independent_test_use_authorized"] is False
    assert config["model_training_authorized_at_acquisition"] is False
    with pytest.raises(ValueError):
        validate_config({**config, "independent_test_use_authorized": True})
