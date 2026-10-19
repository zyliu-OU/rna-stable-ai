"""Stage 2 band coverage census: availability of validation references by band.

Counts what exists. Measures no accuracy. A family or clan already present in
the frozen selection contributes pseudo-replicates, not independent evidence,
so every count is reported by family and by clan as well as by record.
"""


def band_of(length, bands):
    """Name the band a length falls in, or None when outside every band."""
    if type(length) is not int or length < 1:
        raise ValueError("Positive integer length required")
    for band in bands:
        if band["minimum_inclusive"] <= length < band["maximum_exclusive"]:
            return band["name"]
    return None


def classify(decision, taxonomy):
    """Map a frozen selection decision onto support and exposure flags."""
    if decision not in taxonomy:
        raise ValueError(f"Unknown selection decision: {decision}")
    entry = taxonomy[decision]
    return {"decision": decision, "reference_supported": entry["reference_supported"],
            "exposed": entry["exposed"]}


def eligible(record):
    """Available for band expansion: reference-supported and not exposed."""
    return record["reference_supported"] is True and record["exposed"] is False


def clan_of(family, clan_map):
    """Clan from the pinned map, or None when the family is unmapped locally."""
    return clan_map.get(family)


def baseline_lineage(selected, clan_map):
    """Families and clans already represented by the in-scope selection."""
    families = sorted({record["family_id"] for record in selected})
    clans = sorted({clan_of(record["family_id"], clan_map) for record in selected}
                   - {None})
    unresolved = sorted({record["family_id"] for record in selected
                         if clan_of(record["family_id"], clan_map) is None})
    return {"families": families, "clans": clans, "clan_unresolved_families": unresolved}


def band_census(records, baseline, clan_map):
    """Per-decision, per-family and per-clan census of one band's records.

    `records` carry name, family_id, decision, reference_supported, exposed.
    """
    by_decision = {}
    for record in records:
        by_decision.setdefault(record["decision"], 0)
        by_decision[record["decision"]] += 1
    available = [record for record in records if eligible(record)]
    families = sorted({record["family_id"] for record in available})
    clans = sorted({clan_of(f, clan_map) for f in families}-{None})
    unresolved = sorted({f for f in families if clan_of(f, clan_map) is None})
    new_families = sorted(set(families)-set(baseline["families"]))
    new_clans = sorted(set(clans)-set(baseline["clans"]))
    # A family whose clan is unknown cannot be credited as a new clan.
    blocked_new_clan = {}
    for record in records:
        family = record["family_id"]
        clan = clan_of(family, clan_map)
        if clan is not None and clan not in baseline["clans"] and not eligible(record):
            blocked_new_clan.setdefault(clan, {"family": family, "records": 0, "reasons": {}})
            blocked_new_clan[clan]["records"] += 1
            reasons = blocked_new_clan[clan]["reasons"]
            reasons.setdefault(record["decision"], 0)
            reasons[record["decision"]] += 1
    all_families = sorted({record["family_id"] for record in records})
    return {"records": len(records), "by_decision": dict(sorted(by_decision.items())),
            "band_families": all_families,
            "band_clans": sorted({clan_of(f, clan_map) for f in all_families}-{None}),
            "band_clan_unresolved_families":
                sorted(f for f in all_families if clan_of(f, clan_map) is None),
            "eligible_records": len(available),
            "eligible_families": families, "eligible_clans": clans,
            "eligible_clan_unresolved_families": unresolved,
            "new_families_available": new_families,
            "new_clans_available": new_clans,
            "eligible_records_by_family":
                {f: sum(1 for r in available if r["family_id"] == f) for f in families},
            "new_clan_opportunities_blocked": blocked_new_clan,
            "family_expansion_possible": bool(new_families),
            "clan_expansion_possible": bool(new_clans)}


def resolution_verdict(census):
    """Whether the band's sparsity is resolvable from the censused material."""
    if census["clan_expansion_possible"]:
        state = "resolvable_at_clan_level_from_local_material"
    elif census["family_expansion_possible"]:
        state = "resolvable_at_family_level_only_clan_coverage_unchanged"
    elif census["eligible_records"]:
        state = "additional_records_available_but_no_new_family_or_clan"
    else:
        state = "no_eligible_band_material_available"
    return {"state": state,
            "family_expansion_possible": census["family_expansion_possible"],
            "clan_expansion_possible": census["clan_expansion_possible"],
            "eligible_records": census["eligible_records"],
            "note": "Availability only. Expanding the selection requires an explicit gate "
                    "review and new inference; neither is performed or implied here."}


def requirement_status(requirements, assignments):
    """Bind each gate requirement to a status, evidence and blockers."""
    vocabulary = ("satisfied", "partially_satisfied", "not_satisfied", "blocked_on_acquisition")
    rows = []
    for requirement in requirements:
        if requirement not in assignments:
            raise ValueError(f"No status assigned for requirement: {requirement}")
        entry = assignments[requirement]
        if entry["status"] not in vocabulary:
            raise ValueError(f"Invalid status for {requirement}: {entry['status']}")
        if entry["status"] == "satisfied":
            raise ValueError("A census may not mark a gate requirement satisfied")
        if not entry.get("evidence"):
            raise ValueError(f"Requirement status needs evidence: {requirement}")
        if not entry.get("blockers"):
            raise ValueError(f"Unsatisfied requirement needs blockers: {requirement}")
        rows.append({"requirement": requirement, **entry})
    if len(rows) != len(requirements):
        raise ValueError("Every gate requirement must receive a status")
    return rows
