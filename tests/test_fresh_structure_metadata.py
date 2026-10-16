"""The acquisition plan must use only unresolved metadata families."""

import pytest

from scripts.acquire_fresh_structure_metadata import planned_families


def test_planned_families_uses_only_unresolved_mapped_families():
    rows = [{"family_id": f"RF{i:05d}", "status": "clan_unresolved"}
            for i in range(1, 93)]
    rows.append({"family_id": "RF00999", "status": "exposed_family"})
    inventory = {"stage": "metadata_only_inventory",
                 "annotation_labels_read": False,
                 "model_inference_authorized": False,
                 "families": rows}
    assert planned_families(inventory) == [f"RF{i:05d}" for i in range(1, 93)]
    inventory["annotation_labels_read"] = True
    with pytest.raises(ValueError):
        planned_families(inventory)
