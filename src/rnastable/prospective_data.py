"""Bounded metadata acquisition; this module never imports structure annotations."""

import json
import re
import urllib.request

from .reference import digest
from .sequences import validate_sequence


def family_urls(family):
    if not isinstance(family, str) or not re.fullmatch(r"RF\d{5}", family):
        raise ValueError("Expected a Rfam accession")
    base = "https://rfam.org/family/" + family
    return {
        "description": base + "?content-type=application%2Fjson",
        "sequences": base + "/alignment/fastau",
    }


def bounded_download(url, maximum_bytes, timeout=20):
    if not url.startswith("https://rfam.org/family/"):
        raise ValueError("Only official Rfam HTTPS endpoints are supported")
    request = urllib.request.Request(
        url, headers={"User-Agent": "RNA-StableAI-prospective-metadata/0.1"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if not response.geturl().startswith("https://rfam.org/"):
            raise ValueError("Rfam response redirected outside the official HTTPS host")
        content = response.read(maximum_bytes + 1)
        if len(content) > maximum_bytes:
            raise ValueError("Response exceeds bounded download size")
        if not content:
            raise ValueError("Empty Rfam response")
        return content


def validate_description(content, family):
    data = json.loads(content)
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("rfam"), dict)
        or data["rfam"].get("acc") != family
    ):
        raise ValueError("Family description accession does not match requested family")
    return data


def fastau_records(content, family):
    family_urls(family)
    records = []
    header, chunks = None, []
    seen = set()

    def store():
        if header is None:
            return
        identity = header[1:].split()[0] if header[1:].split() else ""
        if not identity or identity in seen:
            raise ValueError("Missing or duplicate FASTA sequence identity")
        seen.add(identity)
        original = "".join(chunks)
        sequence = original.upper().replace("T", "U")
        try:
            validate_sequence(sequence)
            valid = True
        except ValueError:
            valid = False
        records.append(
            {
                "id": family + ":" + identity,
                "upstream_split": "rfam_seed",
                "family_id": family,
                "sequence": sequence,
                "sequence_sha256": digest(sequence.encode()),
                "original_sequence_sha256": digest(original.encode()),
                "valid_sequence": valid,
                "normalization": "uppercase_and_T_to_U",
            }
        )

    for line in content.decode().splitlines():
        if line.startswith(">"):
            store()
            header, chunks = line, []
        elif line.strip():
            if header is None:
                raise ValueError("Sequence before FASTA header")
            chunks.append(line.strip())
    store()
    if not records:
        raise ValueError("Rfam FASTA contains no records")
    return records


def sequence_overlap(first, second, threshold=0.8):
    from .experimental_data import sequence_similarity

    # An exact upper bound on SequenceMatcher's 2*M/(len(a)+len(b)).
    if 2 * min(len(first), len(second)) < threshold * (len(first) + len(second)):
        return False
    return first == second or sequence_similarity(first, second) >= threshold


def select_metadata_panel(records, screening, cap):
    if type(cap) is not int or not 1 <= cap <= 5:
        raise ValueError("Metadata panel cap must be in 1..5")
    index = {r["id"]: r for r in records}
    if len(index) != len(records) or set(index) != {r["id"] for r in screening["rows"]}:
        raise ValueError("Panel and screening record identities differ")
    selected, decisions = [], []
    counts = {}
    for row in sorted(screening["rows"], key=lambda r: (r["family_id"], r["id"])):
        record = index[row["id"]]
        if record["sequence_sha256"] != row["sequence_sha256"]:
            raise ValueError("Screened sequence binding changed")
        reason = row["reason"]
        if reason == "metadata_candidate":
            if any(
                sequence_overlap(record["sequence"], old["sequence"])
                for old in selected
            ):
                reason = "panel_sequence_redundancy"
            elif counts.get(record["family_id"], 0) >= cap:
                reason = "fixed_family_cap"
            else:
                selected.append(record)
                counts[record["family_id"]] = counts.get(record["family_id"], 0) + 1
                reason = "selected_metadata_only"
        decisions.append({**row, "panel_reason": reason})
    return {
        "records": selected,
        "decisions": decisions,
        "counts": counts,
        "annotation_binding_complete": False,
        "test_inference_allowed": False,
    }
