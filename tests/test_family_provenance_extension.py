"""A new development split exposes label feedback and retains prior outcomes."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def module(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "family_extension_test", root / "scripts/extend_family_provenance_dataset.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_extension_uses_first_unused_ranked_group_after_recorded_failure(module, tmp_path):
    (tmp_path / "binding.json").write_text(json.dumps({
        "supported_by_family": {"RF00024": 0, "RF00001": 2}
    }))
    previous = {"complete": True, "dataset_ready": False, "run_dir": str(tmp_path)}
    metadata = {"selection": {
        "selected_families": [
            {"family_id": "RF00024", "group": "clan:CL00004", "role": "train"},
            {"family_id": "RF00001", "group": "family:RF00001", "role": "validation"},
        ] + [{"family_id": f"RF{i:05d}", "group": f"family:RF{i:05d}", "role": "train"}
             for i in range(2, 16)],
        "ranked_groups": ["clan:CL00004", "family:RF00001", "family:RF00022"],
        "decisions": [{"family_id": "RF00022", "group": "family:RF00022",
                       "reason": "metadata_eligible"}],
    }}
    binding = json.loads((tmp_path / "binding.json").read_text())
    binding["supported_by_family"].update({f"RF{i:05d}": 1 for i in range(2, 16)})
    (tmp_path / "binding.json").write_text(json.dumps(binding))
    assert module.extension_plan(previous, metadata) == {
        "family_id": "RF00022", "group": "family:RF00022", "role": "train"
    }
    binding["supported_by_family"]["RF00024"] = 1
    (tmp_path / "binding.json").write_text(json.dumps(binding))
    with pytest.raises(ValueError, match="failure not observed"):
        module.extension_plan(previous, metadata)


def test_combine_keeps_prior_records_and_requires_support_for_new_family(module):
    families = {f"RF{i:05d}": 1 for i in range(1, 16)}
    families["RF00024"] = 0
    old = {
        "selected": [{"id": "old", "family_id": "RF00001"},
                     {"id": "validation", "family_id": "RF00002"},
                     {"id": "excluded", "family_id": "RF00024"}],
        "decisions": [{"id": "old", "family_id": "RF00001"},
                      {"id": "validation", "family_id": "RF00002"},
                      {"id": "excluded", "family_id": "RF00024"}],
        "records": [{"id": "old", "family_id": "RF00001", "role": "train",
                     "reference_status": "ok", "pairs": [[0, 3]]},
                    {"id": "excluded", "family_id": "RF00024", "role": "train",
                     "reference_status": "unsupported_reference"},
                    {"id": "validation", "family_id": "RF00002", "role": "validation",
                     "reference_status": "ok", "pairs": []}],
        "supported_by_family": families,
    }
    new = {
        "selected": [{"id": "new", "family_id": "RF00022"}],
        "decisions": [{"id": "new", "family_id": "RF00022"}],
        "records": [{"id": "new", "family_id": "RF00022", "role": "train",
                     "reference_status": "unsupported_reference"}],
        "supported_by_family": {"RF00022": 0},
    }
    policy = {"minimum_supported_training_records": 1,
              "minimum_supported_validation_records": 1,
              "minimum_supported_per_selected_family": 1}
    result = module.combine(old, new, policy)
    assert result["records"][0] == old["records"][0]
    assert "excluded" not in {r["id"] for r in result["records"]}
    assert not result["dataset_ready"]
    new["records"][0]["reference_status"] = "ok"
    new["supported_by_family"]["RF00022"] = 1
    assert module.combine(old, new, policy)["dataset_ready"]
