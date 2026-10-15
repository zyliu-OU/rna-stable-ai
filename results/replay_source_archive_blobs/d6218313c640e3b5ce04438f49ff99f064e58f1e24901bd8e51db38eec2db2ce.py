"""Screen family metadata and sequences before importing any new structure labels."""

from collections import Counter
import re

from .prospective_data import sequence_overlap
from .reference import digest, text_field
from .sequences import validate_sequence

METADATA_FILES = {
    "train": "train_datasets/S-Processed-TRA.fasta",
    "holdout": "holdout_datasets/S-Processed-VAL.fasta",
    "test": "test_datasets/S-Processed-TES.fasta",
}


def metadata_records(contents):
    """Parse only FASTA metadata/sequences; never access BPSEQ or an archive."""
    if set(contents) != set(METADATA_FILES):
        raise ValueError("Require train/holdout/test metadata inventories")
    records = []
    seen = set()
    for split in METADATA_FILES:
        header, sequence = None, []

        def store():
            if header is None or "EXT_SOURCE=Rfam Database;" not in header:
                return
            fields = dict(
                part.strip().split("=", 1)
                for part in header.lstrip("> ").split(";")
                if part.strip()
            )
            family = fields.get("EXT_ID", "").split()
            if not family or not re.fullmatch(r"RF\d{5}", family[0]):
                raise ValueError("Malformed upstream Rfam accession")
            identity = text_field(fields.get("SSTRAND_ID"), "RNA STRAND ID")
            raw = "".join(sequence)
            sequence_sha = digest(raw.encode())
            # Upstream can repeat a strand ID for different processed fragments.
            key = (split, identity, sequence_sha)
            if key in seen:
                raise ValueError("Duplicate metadata identity")
            seen.add(key)
            # Invalid/ambiguous sequences remain visible in the denominator.
            try:
                validate_sequence(raw)
                valid = True
            except ValueError:
                valid = False
            records.append(
                {
                    "id": split + ":" + identity + ":" + sequence_sha,
                    "upstream_split": split,
                    "family_id": family[0],
                    "sequence": raw,
                    "sequence_sha256": sequence_sha,
                    "valid_sequence": valid,
                }
            )

        for line in contents[split].decode().splitlines():
            if line.startswith(">"):
                store()
                header, sequence = line, []
            elif line.strip():
                if header is None:
                    raise ValueError("Sequence before FASTA header")
                sequence.append(line.strip())
        store()
    return records


def screen_families(records, exposed, minimum=20, maximum=1024):
    if (
        type(minimum) is not int
        or type(maximum) is not int
        or not 1 <= minimum <= maximum <= 1024
    ):
        raise ValueError("Screening lengths must be within the exact decoder bound")
    if not isinstance(exposed, list):
        raise ValueError("Exposure ledger must be a list")
    for row in exposed:
        validate_sequence(row["sequence"])
        text_field(row.get("source"), "exposure source")
        if "family_id" in row:
            text_field(row["family_id"], "exposure family")
    exposed_families = {row["family_id"] for row in exposed if "family_id" in row}
    sequences = sorted({row["sequence"] for row in exposed})
    rows = []
    for record in sorted(records, key=lambda r: r["id"]):
        if record["family_id"] in exposed_families:
            reason = "prior_family_exposure"
        elif not record["valid_sequence"]:
            reason = "invalid_sequence"
        elif not minimum <= len(record["sequence"]) <= maximum:
            reason = "outside_fixed_length_range"
        elif any(sequence_overlap(record["sequence"], seq) for seq in sequences):
            reason = "prior_sequence_exposure"
        else:
            reason = "metadata_candidate"
        rows.append(
            {
                key: record[key]
                for key in ("id", "upstream_split", "family_id", "sequence_sha256")
            }
            | {"length": len(record["sequence"]), "reason": reason}
        )
    families = []
    for family in sorted({r["family_id"] for r in rows}):
        subset = [r for r in rows if r["family_id"] == family]
        families.append(
            {
                "family_id": family,
                "metadata_records": len(subset),
                "metadata_candidates": sum(
                    r["reason"] == "metadata_candidate" for r in subset
                ),
                "upstream_split_counts": dict(
                    sorted(Counter(r["upstream_split"] for r in subset).items())
                ),
                "reason_counts": dict(
                    sorted(Counter(r["reason"] for r in subset).items())
                ),
            }
        )
    return {
        "complete": True,
        "minimum_length": minimum,
        "maximum_length": maximum,
        "exposure_records_checked": len(exposed),
        "exposure_records_without_family_id": sum(
            "family_id" not in r for r in exposed
        ),
        "exposed_families": sorted(exposed_families),
        "metadata_records": len(rows),
        "metadata_candidates": sum(r["reason"] == "metadata_candidate" for r in rows),
        "families": families,
        "rows": rows,
        "new_structure_labels_read": False,
        "inference_performed": False,
        "test_evaluated": False,
        "family_independence_established": False,
        "interpretation": "Metadata candidates require exact annotation binding and a frozen exposure-aware plan before evaluation. Unknown training-family/clan provenance and legacy tool training remain unresolved. Sequence screening uses the symmetric SequenceMatcher 0.8 heuristic, not alignment identity.",
    }
