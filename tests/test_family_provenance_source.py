"""The source builder keeps fixed selected records even when labels fail binding."""

import importlib.util
from difflib import SequenceMatcher
import json
from pathlib import Path
import random

from rnastable.prospective_data import sequence_overlap


def load_builder(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "family_source_test", root / "scripts/prepare_family_provenance_dataset.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unsupported_first_record_is_not_replaced_by_later_valid_record(
    monkeypatch, tmp_path
):
    builder = load_builder(monkeypatch)
    protocol_dir = tmp_path / "protocol"
    run = tmp_path / "run"
    protocol_dir.mkdir()
    run.mkdir()
    config = {
        "future_binding": {
            "minimum_length": 1,
            "maximum_length": 1024,
            "train_candidate_cap_per_family": 1,
            "validation_candidate_cap_per_family": 1,
            "minimum_supported_training_records": 1,
            "minimum_supported_validation_records": 1,
            "minimum_supported_per_selected_family": 1,
            "sequence_similarity_threshold": 0.8,
        }
    }
    (protocol_dir / "config.json").write_text(json.dumps(config))
    (protocol_dir / "exposure.json").write_text("[]")
    (run / "RF00001.sto").write_text(
        "# STOCKHOLM 1.0\n#=GF AC RF00001\n"
        "a --ACGU\nb ACGUGG\n#=GC SS_cons <<..>>\n//\n"
    )
    attempt = {"family_id": "RF00001", "role": "train", "group": "family:RF00001",
               "filename": "RF00001.sto"}
    binding = builder.select_and_bind(run, {"run_dir": str(protocol_dir)}, [attempt])
    assert len(binding["selected"]) == 1
    assert binding["selected"][0]["id"] == "RF00001:a"
    assert binding["records"][0]["reference_status"] == "unsupported_reference"
    assert binding["decisions"][1]["reason"] == "fixed_family_cap"
    assert not binding["dataset_ready"]
    assert not binding["model_training_performed"]


def test_lcs_prefilter_preserves_directed_sequence_overlap(monkeypatch):
    builder = load_builder(monkeypatch)
    rng = random.Random(1729)
    sequences = ["".join(rng.choices("ACGU", k=rng.randrange(4, 80))) for _ in range(60)]
    sequences += [sequences[0], sequences[1][::-1], sequences[2] + "ACGU"]
    for first, second in zip(sequences, reversed(sequences), strict=True):
        matched = max(
            sum(block.size for block in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
            for a, b in ((first, second), (second, first))
        )
        assert builder.lcs_length(first, second) >= matched
        assert builder.overlap(first, second, 0.8) == sequence_overlap(first, second, 0.8)
