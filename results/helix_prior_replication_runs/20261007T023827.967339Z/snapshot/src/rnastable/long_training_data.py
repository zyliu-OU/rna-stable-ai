"""Bind longer CRW training annotations locally; never import holdout/test labels."""

import re
import zipfile
from pathlib import Path
from .experimental_data import parse_bpseq
from .crw_development_data import overlaps
from .reference import digest


def import_long_training(root, existing, minimum=1025, maximum=4096, cap=8):
    root = Path(root).resolve()
    if (
        type(minimum) is not int
        or type(maximum) is not int
        or not 1025 <= minimum <= maximum <= 4096
        or type(cap) is not int
        or not 1 <= cap <= 8
    ):
        raise ValueError("Invalid fixed longer-training import range/cap")
    fasta = root / "datasets_in_fasta_form/train_datasets/S-Processed-TRA.fasta"
    content = fasta.read_bytes()
    metadata = {}
    header = None
    sequence = []

    def store():
        if header and "EXT_SOURCE=Gutell Lab CRW;" in header:
            fields = dict(
                part.strip().split("=", 1)
                for part in header.lstrip("> ").split(";")
                if part.strip()
            )
            key = (fields["SSTRAND_ID"], "".join(sequence))
            if key in metadata and metadata[key] != fields:
                raise ValueError("Ambiguous long CRW sequence metadata")
            metadata[key] = fields

    for line in [*content.decode().splitlines(), ">end"]:
        if line.startswith(">"):
            store()
            header = line
            sequence = []
        else:
            sequence.append(line.strip())
    archive_path = root / "input_data.zip"
    sources = {
        str(fasta): digest(content),
        str(archive_path): digest(archive_path.read_bytes()),
    }
    records = []
    exclusions = []
    candidate_count = 0
    training_lengths = []
    known = [r for values in existing.values() for r in values]
    with zipfile.ZipFile(archive_path) as archive:
        for member in sorted(archive.namelist()):
            if not re.fullmatch(
                r"input_data/StructureData/train/CRW_[^/]+\.bpseq", member
            ):
                continue
            identity = member.replace("/", "_").removesuffix(".bpseq")
            try:
                raw = archive.read(member)
                rows = [
                    line
                    for line in raw.decode().splitlines()
                    if line.strip() and not line.startswith("#")
                ]
                training_lengths.append(len(rows))
                if not minimum <= len(rows) <= maximum:
                    raise ValueError("outside_long_training_range")
                seq, structure = parse_bpseq(raw.decode())
                if not minimum <= len(seq) <= maximum:
                    raise ValueError("outside_long_training_range")
                candidate_count += 1
                fields = metadata.get(
                    (re.search(r"CRW_\d+", Path(member).stem).group(), seq)
                )
                if fields is None:
                    raise ValueError("no_exact_sequence_metadata_binding")
                accessions = fields["EXT_ID"].split()
                if not accessions:
                    raise ValueError("missing_external_accessions")
                if len(records) >= cap:
                    raise ValueError("fixed_training_cap")
                occupied = known + records
                if any(
                    set(a.casefold() for a in accessions).intersection(
                        a.casefold() for a in r.get("external_accessions", [])
                    )
                    or overlaps(seq, r["sequence"])
                    for r in occupied
                ):
                    raise ValueError(
                        "existing_development_accession_or_sequence_overlap"
                    )
                records.append(
                    {
                        "id": identity,
                        "sequence": seq,
                        "structure": structure,
                        "reference_kind": "computational",
                        "source": "Processed comparative Gutell Lab CRW training annotation via RNA STRAND/EternaFold; "
                        + fields["EXT_ID"],
                        "external_accessions": accessions,
                        "external_id": fields["EXT_ID"],
                        "rna_type": fields["TYPE"],
                        "organism": fields["ORGANISM"],
                        "rna_strand_id": fields["SSTRAND_ID"],
                        "upstream_split": "train",
                        "bpseq_member": member,
                        "bpseq_sha256": digest(raw),
                        "conditions": "Processed comparative training annotation; no experimental assay or family/clan independence inferred.",
                    }
                )
            except ValueError as exc:
                exclusions.append({"id": identity, "reason": str(exc)})
    return records, {
        "source_sha256": sources,
        "minimum": minimum,
        "maximum": maximum,
        "cap": cap,
        "candidate_count": candidate_count,
        "selected_count": len(records),
        "exclusions": exclusions,
        "training_member_count": len(training_lengths),
        "maximum_raw_training_length": max(training_lengths, default=None),
        "availability": "selected" if records else "no_records_in_fixed_plan",
        "holdout_sources_read": False,
        "test_sources_read": False,
        "policy": "Fixed sorted-ID training-only longer annotation extension. Existing development accession/sequence separation checked; no fresh validation or test curation.",
    }
