"""Comma-wrapped bpRNA headers are recovered without sequence reads."""

from io import BytesIO
import sys
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inventory_bprna_training_lengths_v2 import recover  # noqa: E402


def test_recover_comma_wrapped_length():
    data = BytesIO()
    path = "dbnFiles/bpRNA_RFAM_1.dbn"
    with ZipFile(data, "w") as archive:
        archive.writestr(path,
                         b"#Name: bpRNA_RFAM_1\n#Length: ,1200,\n#PageNumber: 2\nSEQUENCE\nSTRUCTURE\n")
    data.seek(0)
    with ZipFile(data) as archive:
        row = recover(archive, path)
    assert row["stated_length_nt"] == 1200
    assert row["header_format"] == "comma_wrapped_length"
