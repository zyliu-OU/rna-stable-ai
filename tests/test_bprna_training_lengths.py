"""bpRNA header-only length inventory guards training/test boundaries."""

from io import BytesIO
import sys
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inventory_bprna_training_lengths import header_from, inventory, length_band  # noqa: E402


def test_length_bands_keep_5000_deferred():
    assert [length_band(n) for n in (399, 400, 1024, 1025, 4999, 5000)] == [
        "1_399", "400_1024", "400_1024", "1025_4999",
        "1025_4999", "5000_plus_deferred"]


def test_inventory_reads_only_three_header_lines():
    data = BytesIO()
    with ZipFile(data, "w") as archive:
        archive.writestr("dbnFiles/bpRNA_CRW_1.dbn",
                         b"#Name: bpRNA_CRW_1\n#Length:  1500 \n#PageNumber: 2\nSEQUENCE\nSTRUCTURE\n")
    data.seek(0)
    with ZipFile(data) as archive:
        row = header_from(archive, archive.infolist()[0])
        result = inventory(archive)
    assert row["stated_length_nt"] == 1500
    assert result["length_band_counts"] == {"1025_4999": 1}
    assert result["eligible_400_4999_metadata_count"] == 1
