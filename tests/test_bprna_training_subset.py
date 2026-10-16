"""Frozen bpRNA training subset and pair parsing stay bounded."""

from io import BytesIO
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_bprna_training_subset import (  # noqa: E402
    CONFIG, INVENTORY, dot_bracket_pairs, read_candidate, select,
)


def test_fixed_training_subset_is_header_only_and_bounded():
    rows = select(json.loads(CONFIG.read_text()), json.loads(INVENTORY.read_text()))
    assert len(rows) == 60
    assert len({row["id"] for row in rows}) == 60
    assert all(400 <= row["stated_length_nt"] <= 1024 for row in rows)
    assert {row["source_group"] for row in rows} == {"CRW", "RFAM"}


def test_crossing_pairs_are_retained_and_unbalanced_rejected():
    assert dot_bracket_pairs("([)]") == [[0, 2], [1, 3]]
    with pytest.raises(ValueError):
        dot_bracket_pairs("(()")


def test_selected_dbn_record_checks_actual_lengths():
    sequence = "G" * 200 + "C" * 200
    structure = "(" * 10 + "." * 380 + ")" * 10
    path = "dbnFiles/bpRNA_CRW_1.dbn"
    data = BytesIO()
    with ZipFile(data, "w") as archive:
        archive.writestr(path, f"#Name: bpRNA_CRW_1\n#Length: 400\n#PageNumber: 1\n{sequence}\n{structure}\n")
    data.seek(0)
    with ZipFile(data) as archive:
        record = read_candidate(archive, {"id": "bpRNA_CRW_1", "zip_path": path,
                                          "source_group": "CRW", "stated_length_nt": 400})
    assert len(record["pairs"]) == 10
    assert record["legal_canonical_pairs"] == 10
