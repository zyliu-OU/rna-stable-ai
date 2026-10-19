"""Availability of clan-separated 2000-2999 nt validation references.

Counts what exists upstream and says whether a named gate requirement is
achievable from the surveyed sources. It measures no accuracy and it may not
amend a requirement: recording that something is unachievable is a finding,
changing the requirement is a gate review.
"""
import gzip
import re
import sys

GAPS = str.maketrans("", "", "-._~")
FAMILY = re.compile(r"RF\d{5}")
CLAN = re.compile(r"CL\d{5}")


def parse_clan_membership(path):
    """Family to clan from the Rfam clan_membership dump."""
    mapping = {}
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2 and CLAN.fullmatch(parts[0]) and FAMILY.fullmatch(parts[1]):
                if mapping.setdefault(parts[1], parts[0]) != parts[0]:
                    raise ValueError(f"Conflicting clan for {parts[1]}")
    if not mapping:
        raise ValueError("No clan memberships parsed")
    return mapping


def parse_family_metadata(path):
    """Accession to id and consensus length, counting unparsable rows.

    clen is located by position from the end of the row because the dump's
    free-text columns are not safely splittable.
    """
    families, skipped = {}, 0
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if not parts or not FAMILY.fullmatch(parts[0]):
                skipped += 1
                continue
            try:
                families[parts[0]] = {"id": parts[1], "clen": int(parts[-6])}
            except (ValueError, IndexError):
                skipped += 1
    if not families:
        raise ValueError("No families parsed")
    return families, skipped


def validate_consensus_lengths(families, expected, tolerance):
    """Confirm the clen column against independently known family sizes."""
    if tolerance < 0:
        raise ValueError("Tolerance must be non-negative")
    checks = []
    for accession, size in sorted(expected.items()):
        family = families.get(accession)
        if family is None:
            raise ValueError(f"Validation family absent from metadata: {accession}")
        difference = family["clen"]-int(size)
        if abs(difference) > tolerance:
            raise ValueError(
                f"clen validation failed for {accession}: parsed {family['clen']}, expected {size}")
        checks.append({"family": accession, "id": family["id"],
                       "parsed_clen": family["clen"], "expected": int(size),
                       "difference": difference})
    return checks


def scan_seed_band(path, band):
    """Ungapped band-length sequences per family across all seed alignments."""
    low, high = band["minimum_inclusive"], band["maximum_exclusive"]
    found = {}
    accession, rows = None, {}

    def flush():
        if accession is None:
            return
        for name, sequence in rows.items():
            length = len(sequence.translate(GAPS))
            if low <= length < high:
                found.setdefault(accession, []).append({"name": name, "length_nt": length})

    with gzip.open(path, "rt", encoding="latin-1", errors="replace") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith("# STOCKHOLM"):
                flush()
                accession, rows = None, {}
                continue
            if line.startswith("#=GF AC"):
                accession = line.split()[-1]
                continue
            if line.startswith("#") or line.startswith("//") or not line.strip():
                continue
            parts = line.split()
            if len(parts) == 2:
                rows[parts[0]] = rows.get(parts[0], "")+parts[1]
    flush()
    return {k: sorted(v, key=lambda r: -r["length_nt"]) for k, v in found.items()}


def classify_description(label, ribosomal_keywords, generic_patterns):
    """Textual class of an RCSB description: evidence, not a clan assignment."""
    low = label.lower()
    if any(word in low for word in ribosomal_keywords):
        return "ribosomal"
    if any(pattern in low for pattern in generic_patterns):
        return "generically_named"
    return "other"


def summarize_rcsb(response, ribosomal_keywords, generic_patterns, facet="descriptions"):
    """Band-length experimental RNA entities by description class."""
    facets = [f for f in response.get("facets", []) if f.get("name") == facet]
    if not facets:
        raise ValueError(f"RCSB response carries no {facet} facet")
    classes = {}
    for bucket in facets[0].get("buckets", []):
        kind = classify_description(bucket["label"], ribosomal_keywords, generic_patterns)
        entry = classes.setdefault(kind, {"descriptions": 0, "entities": 0, "labels": []})
        entry["descriptions"] += 1
        entry["entities"] += bucket["population"]
        entry["labels"].append({"label": bucket["label"], "entities": bucket["population"]})
    for entry in classes.values():
        entry["labels"].sort(key=lambda row: -row["entities"])
    total = response.get("total_count")
    classified = sum(e["entities"] for e in classes.values())
    return {"total_band_entities": total,
            "entities_in_facet": classified,
            "facet_covers_all": total == classified,
            "by_class": classes,
            "new_clan_leads": classes.get("other", {"entities": 0})["entities"],
            "unresolved_generic_entities": classes.get("generically_named", {"entities": 0})["entities"],
            "note": "Descriptions carry no Rfam clan. Only the 'other' class could contain a "
                    "new-clan lead, and each would need individual family assignment."}


def rfam_band_availability(seed_band, clan_map, baseline, locally_held):
    """Band seed sequences outside the baseline clans, minus what is already local."""
    baseline = set(baseline)
    per_family, outside = {}, {}
    for accession, rows in sorted(seed_band.items()):
        clan = clan_map.get(accession)
        per_family[accession] = {"clan_id": clan, "band_sequences": len(rows),
                                 "outside_baseline": clan is not None and clan not in baseline,
                                 "clan_unresolved": clan is None}
        if clan is not None and clan not in baseline:
            fresh = [r for r in rows if r["name"] not in locally_held]
            outside[accession] = {"clan_id": clan, "band_sequences": len(rows),
                                  "already_held_locally": len(rows)-len(fresh),
                                  "newly_available": fresh}
    newly = sum(len(v["newly_available"]) for v in outside.values())
    return {"band_families": per_family,
            "families_outside_baseline": outside,
            "band_sequences_total": sum(len(v) for v in seed_band.values()),
            "band_sequences_outside_baseline": sum(v["band_sequences"] for v in outside.values()),
            "newly_available_outside_baseline": newly,
            "clan_unresolved_families": sorted(a for a, v in per_family.items() if v["clan_unresolved"])}


def achievability_verdict(rfam, rcsb, requirement):
    """Whether the requirement is achievable from the surveyed sources."""
    newly = rfam["newly_available_outside_baseline"]
    leads = rcsb["new_clan_leads"]
    if newly > 0:
        state = "resolvable"
    elif leads > 0:
        state = "not_resolvable_from_surveyed_sources_unresolved_leads_present"
    else:
        state = "not_resolvable_from_surveyed_sources"
    return {"gate_requirement": requirement, "state": state,
            "rfam_newly_available_outside_baseline": newly,
            "rcsb_non_ribosomal_non_generic_entities": leads,
            "rcsb_unresolved_generic_entities": rcsb["unresolved_generic_entities"],
            "achievable_from_surveyed_sources": newly > 0,
            "requirement_satisfied": False,
            "gate_amended": False,
            "scope_of_verdict": "Rfam seed alignments and RCSB experimental polymer entities as "
                                "queried. Rfam full alignments were not surveyed.",
            "note": "Availability only. A census cannot satisfy or amend a gate requirement; "
                    "narrowing the requirement is a gate review decision."}


def main():  # pragma: no cover - convenience for ad-hoc inspection
    print("This module is a library; run scripts/audit_band_clan_availability.py", file=sys.stderr)
    return 1
