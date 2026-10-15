"""Bind a fixed metadata panel to complete, unmodified comparative annotations."""

import json
from pathlib import Path
import re

from .prospective_data import sequence_overlap, validate_description
from .reference import digest
from .reference_audit import require
from .scoring import base_pairs

GAPS = set(".-_~")
BRACKETS = dict(zip("(<[{", ")>]}"))


def parse_stockholm(content, family):
    text = content.decode()
    require(
        text.startswith("# STOCKHOLM 1.0") and text.rstrip().endswith("//"),
        "Incomplete Stockholm",
    )
    require(
        sum(line.strip() == "//" for line in text.splitlines()) == 1,
        "Expected one Stockholm family",
    )
    sequences, annotations, consensus = {}, {}, []
    for line in text.splitlines():
        if line.startswith("#=GF "):
            _, key, value = line.split(maxsplit=2)
            annotations.setdefault(key, []).append(value)
        elif line.startswith("#=GC SS_cons"):
            fields = line.split()
            require(len(fields) == 3, "Invalid consensus annotation")
            consensus.append(fields[2])
        elif line.strip() and not line.startswith("#") and line.strip() != "//":
            fields = line.split()
            require(len(fields) == 2, "Malformed alignment sequence")
            identity, fragment = fields
            sequences[identity] = sequences.get(identity, "") + fragment
    require(annotations.get("AC") == [family], "Stockholm family differs")
    ss = "".join(consensus)
    require(
        sequences and ss and len(ss) <= 10000,
        "Missing or oversized alignment/consensus",
    )
    require(
        all(len(seq) == len(ss) for seq in sequences.values()),
        "Alignment/consensus width differs",
    )
    return {"sequences": sequences, "consensus": ss, "annotations": annotations}


def wuss_pairs(consensus):
    stack, letters, pairs = [], {}, []
    for index, char in enumerate(consensus):
        if char in BRACKETS:
            stack.append((index, char))
        elif char in BRACKETS.values():
            require(
                stack and BRACKETS[stack[-1][1]] == char,
                "Unbalanced or crossing nested WUSS brackets",
            )
            pairs.append((stack.pop()[0], index))
        elif "A" <= char <= "Z":
            letters.setdefault(char, []).append(index)
        elif "a" <= char <= "z":
            require(letters.get(char.upper()), "Unbalanced WUSS pseudoknot")
            pairs.append((letters[char.upper()].pop(), index))
        else:
            require(char in "_-,:.~", "Unknown WUSS symbol")
    require(not stack and not any(letters.values()), "Unbalanced WUSS annotation")
    return sorted(pairs), any(char.isalpha() for char in consensus)


def bind_record(record, alignment):
    identity = record["id"].split(":", 1)[1]
    require(
        identity in alignment["sequences"], "Selected sequence absent from alignment"
    )
    aligned = alignment["sequences"][identity]
    sequence = "".join(c for c in aligned if c not in GAPS).upper().replace("T", "U")
    require(
        sequence == record["sequence"]
        and digest(sequence.encode()) == record["sequence_sha256"],
        "Alignment sequence differs from fixed metadata",
    )
    pairs, pseudoknot = wuss_pairs(alignment["consensus"])
    coordinates = {}
    for column, char in enumerate(aligned):
        if char not in GAPS:
            coordinates[column] = len(coordinates)
    missing = sum(i not in coordinates or j not in coordinates for i, j in pairs)
    result = {
        **record,
        "sequence_bound": True,
        "consensus_pairs": len(pairs),
        "missing_paired_columns": missing,
        "pseudoknot_present": pseudoknot,
        "alignment_sequence_sha256": digest(aligned.encode()),
        "consensus_sha256": digest(alignment["consensus"].encode()),
        "structure_source": "; ".join(alignment["annotations"].get("SS", [])),
        "reference_kind": "computational",
        "source": "Rfam seed consensus mapped without deleting any annotated contact; "
        + record["family_id"],
    }
    if pseudoknot or missing:
        return {
            **result,
            "reference_status": "unsupported_reference",
            "error": "pseudoknot_not_supported"
            if pseudoknot
            else "missing_annotated_paired_column",
        }
    mapped = {(coordinates[i], coordinates[j]) for i, j in pairs}
    chars = ["."] * len(sequence)
    for i, j in mapped:
        chars[i], chars[j] = "(", ")"
    structure = "".join(chars)
    require(base_pairs(structure) == mapped, "Mapped contacts cross or change identity")
    return {**result, "reference_status": "ok", "structure": structure}


def clan_from_description(content, family, release):
    data = validate_description(content, family)["rfam"]
    require(data["release"]["number"] == release, "Family provenance release differs")
    require(
        isinstance(data.get("clan"), dict) and "acc" in data["clan"],
        "Missing clan provenance",
    )
    clan = data["clan"]["acc"]
    require(
        clan is None or isinstance(clan, str) and re.fullmatch(r"CL\d{5}", clan),
        "Invalid clan accession",
    )
    return clan


def bind_pair_reference(record, alignment):
    """Return every WUSS contact, including crossing pairs, for a complete sequence."""
    from .pair_reference import validate_pairs

    identity = record["id"].split(":", 1)[1]
    require(
        identity in alignment["sequences"], "Selected sequence absent from alignment"
    )
    aligned = alignment["sequences"][identity]
    sequence = "".join(c for c in aligned if c not in GAPS).upper().replace("T", "U")
    require(
        sequence == record["sequence"]
        and digest(sequence.encode()) == record["sequence_sha256"],
        "Alignment sequence differs from fixed metadata",
    )
    coordinates = {}
    for column, char in enumerate(aligned):
        if char not in GAPS:
            coordinates[column] = len(coordinates)
    pairs, pseudoknot = wuss_pairs(alignment["consensus"])
    require(
        all(i in coordinates and j in coordinates for i, j in pairs),
        "Missing annotated paired column; incomplete references cannot be scored",
    )
    mapped = [[coordinates[i], coordinates[j]] for i, j in pairs]
    validate_pairs(mapped, len(sequence))
    return {
        "id": record["id"],
        "sequence": sequence,
        "pairs": mapped,
        "family_id": record["family_id"],
        "reference_kind": "computational",
        "source": "Complete Rfam WUSS consensus contacts, including letter pairs; "
        + record["family_id"],
        "pseudoknot_annotation_present": pseudoknot,
        "alignment_sequence_sha256": digest(aligned.encode()),
        "consensus_sha256": digest(alignment["consensus"].encode()),
    }


def pdb_accessions(content, family):
    data = json.loads(content)
    require(
        isinstance(data, dict) and isinstance(data.get("mapping"), list),
        "Unsupported PDB mapping schema",
    )
    accessions = set()
    for row in data["mapping"]:
        require(
            isinstance(row, dict) and row.get("rfam_acc") == family,
            "PDB mapping family differs",
        )
        identity = row.get("pdb_id")
        require(
            isinstance(identity, str)
            and re.fullmatch(r"[0-9][A-Za-z0-9]{3}", identity),
            "Invalid PDB mapping accession",
        )
        accessions.add(identity.casefold())
    return sorted(accessions)


def build_binding(
    evidence_run, acquisition, exposures, reference_format="dot_bracket_v1"
):
    require(
        reference_format in ("dot_bracket_v1", "pair_set_zero_based_v1"),
        "Unknown prospective reference format",
    )
    run = Path(evidence_run)
    source = Path(acquisition["run_dir"])
    plan = json.loads((run / "plan.json").read_text())
    release = plan["rfam_release"]
    old_families = sorted({r["family_id"] for r in exposures if r.get("family_id")})
    require(
        not set(acquisition["families_downloaded"]).intersection(old_families),
        "Prospective panel families already exposed",
    )
    old_clans = {
        family: clan_from_description(
            (run / (family + "_description.json")).read_bytes(), family, release
        )
        for family in old_families
    }
    exposed_pdb = {
        r["pdb_accession"].casefold() for r in exposures if r.get("pdb_accession")
    }
    families, records = [], []
    for family in sorted(acquisition["families_downloaded"]):
        clan = clan_from_description(
            (source / (family + "_description.json")).read_bytes(), family, release
        )
        mapping = pdb_accessions(
            (run / (family + "_pdb_mapping.json")).read_bytes(), family
        )
        overlaps = sorted(set(mapping) & exposed_pdb)
        clan_overlap = sorted(
            f for f, old in old_clans.items() if clan is not None and clan == old
        )
        selected = [
            r
            for r in acquisition["metadata_panel"]["records"]
            if r["family_id"] == family
        ]
        alignment = parse_stockholm((run / (family + ".sto")).read_bytes(), family)
        require(
            alignment["annotations"].get("CL", []) == ([] if clan is None else [clan]),
            "Stockholm and description clan differ",
        )
        family_records = []
        for record in selected:
            try:
                bound = bind_record(record, alignment)
                if reference_format == "pair_set_zero_based_v1":
                    if bound["missing_paired_columns"]:
                        bound.update(
                            reference_status="unsupported_reference",
                            error="missing_annotated_paired_column",
                        )
                    else:
                        bound.update(
                            bind_pair_reference(record, alignment),
                            reference_status="ok",
                        )
                        bound.pop("structure", None)
                        bound.pop("error", None)
            except ValueError as exc:
                bound = {
                    **record,
                    "sequence_bound": False,
                    "reference_status": "binding_error",
                    "error": str(exc),
                }
            if overlaps or clan_overlap or family in old_families:
                bound.update(
                    reference_status="provenance_rejected",
                    error="known_family_clan_or_pdb_overlap",
                )
            family_records.append(bound)
        records.extend(family_records)
        families.append(
            {
                "family_id": family,
                "clan": clan,
                "mapped_pdb_accessions": len(mapping),
                "pdb_overlap": overlaps,
                "clan_overlap": clan_overlap,
                "planned_records": len(selected),
                "supported_references": sum(
                    r["reference_status"] == "ok" for r in family_records
                ),
            }
        )
    # Recheck the exact selected panel against the ledger used for final planning.
    require(
        not any(
            sequence_overlap(r["sequence"], old["sequence"])
            for r in records
            for old in exposures
        ),
        "Selected panel now overlaps exposed sequences",
    )
    require(
        len(records) == len(acquisition["metadata_panel"]["records"]),
        "Fixed panel denominator changed",
    )
    result = {
        "records": records,
        "families": families,
        "exposed_family_clans": old_clans,
        "planned_records": len(records),
        "supported_references": sum(r["reference_status"] == "ok" for r in records),
        "sequence_bindings_complete": all(r["sequence_bound"] for r in records),
        "known_provenance_overlap": any(
            f["pdb_overlap"] or f["clan_overlap"] or f["family_id"] in old_families
            for f in families
        ),
        "exposure_records_checked": len(exposures),
        "exposures_without_family_id": sum(not r.get("family_id") for r in exposures),
        "independence_certified": False,
        "limitations": [
            "Source-bound checks exclude known family/clan/PDB and heuristic sequence overlap; unknown training-family and legacy tool-training provenance remain unresolved.",
            "References are conserved comparative consensus annotations, not direct per-sequence experimental measurements.",
            "Unsupported records remain in planned denominators with unknown metrics; no pseudoknot/contact deletion or replacement.",
        ],
    }
    if reference_format == "pair_set_zero_based_v1":
        result["reference_format"] = reference_format
    return result
