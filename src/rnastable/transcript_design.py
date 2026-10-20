"""Whole-transcript design: synonymous codons plus redesigned UTR composition.

`synonymous_window` holds the earlier domain, where the UTRs were fixed at the
collaborator's supplied sequences and only a window of codons could change. That
domain was measured to be too small to matter: its widest predicted stability
difference from the reference was 1.0617-fold, below even the 1.10-fold floor at
which the objective was measured to order at chance.

This module widens the domain to the whole transcript while holding every length
fixed, so composition is the only variable and every assembly check stays
meaningful. Two things are protected because removing them would change the
construct for reasons unrelated to composition:

- the 5' UTR's final `GCCACC`, a canonical strong Kozak context
- the 3' UTR's opening `TAA`, the tandem stop the collaborator confirmed

One constraint comes from this project's own measurement rather than from the
literature: no out-of-frame uAUG in the 5' UTR. The m1-pseudouridine slope check
measured that penalty at -1.56 and -1.43 unmodified and -1.32 under m1-psi, a
large effect stable across the modification, and the supplied 5' UTR already has
none.

GC is sampled deliberately. It is the feature the calibration depends on most,
the axis on which the construct extrapolates, and the relationship m1-psi was
measured to rescale, so members draw a target transcript GC and are generated
toward it rather than letting GC emerge from uniform sampling.

A designed-UTR member is a NEW construct. It does not carry the supplied UTRs'
provenance, and this module never implies otherwise.
"""
import hashlib
import random

from .synonymous_window import (
    codon_table,
    longest_homopolymer,
    split_codons,
    synonyms,
    translate,
    window_indices,
)

KOZAK_SUFFIX = "GCCACC"
TANDEM_STOP_PREFIX = "TAA"
GC_BASES = ("G", "C")
AU_BASES = ("A", "T")


def gc_count(sequence):
    return sequence.count("G") + sequence.count("C")


def editable_spans(utr5, utr3):
    """Which UTR positions may be redesigned, and which are protected."""
    if not utr5.endswith(KOZAK_SUFFIX):
        raise ValueError(f"5' UTR does not end with the Kozak context {KOZAK_SUFFIX}")
    if not utr3.startswith(TANDEM_STOP_PREFIX):
        raise ValueError(f"3' UTR does not start with the tandem stop {TANDEM_STOP_PREFIX}")
    return {
        "utr5_free": len(utr5) - len(KOZAK_SUFFIX),
        "utr5_preserved": KOZAK_SUFFIX,
        "utr3_free": len(utr3) - len(TANDEM_STOP_PREFIX),
        "utr3_preserved": TANDEM_STOP_PREFIX,
    }


def out_of_frame_uaug(utr5):
    """Out-of-frame upstream start codons, which cost ribosome load.

    The main start codon sits immediately after the 5' UTR, so an ATG beginning
    at zero-based position p is in frame when (len(utr5) - p) is a multiple of 3.
    """
    return [i for i in range(len(utr5) - 2)
            if utr5[i:i + 3] == "ATG" and (len(utr5) - i) % 3 != 0]


def reachable_gc_range(utr5, cds, utr3):
    """Transcript GC fraction reachable with lengths fixed.

    Computed from the extremes: every free UTR position GC or AU, and every
    substitutable codon pushed to its highest or lowest GC synonym.
    """
    spans = editable_spans(utr5, utr3)
    codons = split_codons(cds)
    groups, table = synonyms(), codon_table()
    indices = set(window_indices(codons, len(codons)))
    low = high = 0
    for i, codon in enumerate(codons):
        options = groups[table[codon]] if i in indices else [codon]
        low += min(gc_count(c) for c in options)
        high += max(gc_count(c) for c in options)
    fixed = gc_count(spans["utr5_preserved"]) + gc_count(spans["utr3_preserved"])
    free = spans["utr5_free"] + spans["utr3_free"]
    total = len(utr5) + len(cds) + len(utr3)
    return {"minimum": (low + fixed) / total, "maximum": (high + fixed + free) / total,
            "free_utr_positions": free, "transcript_length_nt": total}


def _design_cds(codons, indices, groups, table, bias, rng):
    """Synonymous choice, GC-steered per member but randomised per codon.

    An earlier version selected `options[int(bias * len(options))]`, which is
    deterministic given the member's bias. Combined with a rejection filter that
    removed whole bias bands, 60 members collapsed onto 2 distinct ORFs. The fix
    keeps the member-level GC steering but randomises WITHIN it: the synonyms are
    split into a low-GC and a high-GC half, the half is chosen with probability
    `bias`, and the codon is drawn uniformly inside that half. Members at the
    same target GC therefore differ in sequence.
    """
    designed = list(codons)
    for i in indices:
        options = sorted(groups[table[codons[i]]], key=lambda c: (gc_count(c), c))
        middle = len(options) // 2 or 1
        half = options[middle:] if rng.random() < bias else options[:middle]
        designed[i] = rng.choice(half or options)
    return designed


def _design_utr(length, preserved, where, target_gc_positions, rng, max_homopolymer=6):
    """Fill free positions run-aware, so a homopolymer is never created.

    Sampling bases independently and rejecting afterwards discarded about 92
    percent of attempts and, worse, removed whole regions of the GC range: an
    AU-rich target needs many A and T bases and almost always produced a long
    run. Excluding any base that would extend a run past the bound generates
    inside the constraint instead of filtering after it.
    """
    free = length - len(preserved)
    wanted = max(0, min(free, target_gc_positions))
    slots = [True] * wanted + [False] * (free - wanted)
    rng.shuffle(slots)
    context = preserved if where == "prefix" else ""
    bases = []
    for slot in slots:
        pool = list(GC_BASES if slot else AU_BASES)
        recent = (context + "".join(bases))[-max_homopolymer:]
        if len(recent) >= max_homopolymer and len(set(recent)) == 1:
            pool = [b for b in pool if b != recent[-1]] or pool
        bases.append(rng.choice(pool))
    return ("".join(bases) + preserved) if where == "suffix" else (preserved + "".join(bases))


def build_pool(utr5, cds, utr3, size=512, seed=1729, max_homopolymer=6,
               max_attempts_per_member=400):
    """Sample a deterministic pool of whole-transcript designs.

    Member 0 is the unmodified reference. Each further member draws a target
    transcript GC uniformly across the reachable range and a codon GC
    preference, then the free UTR positions are filled to reach the target given
    the codon choices already made. Members violating any constraint are
    discarded and counted by cause; none is repaired.
    """
    utr5 = utr5.strip().upper().replace("U", "T")
    utr3 = utr3.strip().upper().replace("U", "T")
    cds = cds.strip().upper().replace("U", "T")
    spans = editable_spans(utr5, utr3)
    if out_of_frame_uaug(utr5):
        raise ValueError("The supplied 5' UTR already contains an out-of-frame uAUG")
    reference_codons = split_codons(cds)
    protein = translate(reference_codons)
    groups, table = synonyms(), codon_table()
    indices = window_indices(reference_codons, len(reference_codons))
    bounds = reachable_gc_range(utr5, cds, utr3)
    total = bounds["transcript_length_nt"]
    fixed_gc = gc_count(spans["utr5_preserved"]) + gc_count(spans["utr3_preserved"])

    def describe(member_utr5, member_cds_codons, member_utr3, is_reference):
        sequence = member_utr5 + "".join(member_cds_codons) + member_utr3
        substituted = sorted(i for i, (a, b) in enumerate(
            zip(reference_codons, member_cds_codons)) if a != b)
        return {
            "is_reference": is_reference,
            "utr5": member_utr5, "utr3": member_utr3,
            "orf": "".join(member_cds_codons),
            "substituted_codon_indices": substituted,
            "substitution_count": len(substituted),
            "utr5_edits": sum(1 for a, b in zip(utr5, member_utr5) if a != b),
            "utr3_edits": sum(1 for a, b in zip(utr3, member_utr3) if a != b),
            "transcript_gc_fraction": gc_count(sequence) / len(sequence),
            "utr5_gc_fraction": gc_count(member_utr5) / len(member_utr5),
            "utr3_gc_fraction": gc_count(member_utr3) / len(member_utr3),
            "orf_gc_fraction": gc_count("".join(member_cds_codons)) / len(member_cds_codons) / 3,
            "longest_homopolymer": longest_homopolymer(sequence),
            "transcript_length_nt": len(sequence),
            "transcript_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
        }

    rng = random.Random(seed)
    members = [describe(utr5, reference_codons, utr3, True)]
    members[0]["member"] = 0
    members[0]["target_gc_fraction"] = members[0]["transcript_gc_fraction"]
    seen = {members[0]["transcript_sha256"]}
    rejected, attempts = {}, 0
    while len(members) < size:
        attempts += 1
        if attempts > size * max_attempts_per_member:
            raise RuntimeError(f"Could not reach {size} members; rejections: {rejected}")
        target = rng.uniform(bounds["minimum"], bounds["maximum"])
        bias = rng.random()
        designed_codons = _design_cds(reference_codons, indices, groups, table, bias, rng)
        orf = "".join(designed_codons)
        needed = round(target * total) - gc_count(orf) - fixed_gc
        free5, free3 = spans["utr5_free"], spans["utr3_free"]
        share5 = round(needed * free5 / (free5 + free3)) if free5 + free3 else 0
        member_utr5 = _design_utr(len(utr5), spans["utr5_preserved"], "suffix",
                                  share5, rng, max_homopolymer)
        member_utr3 = _design_utr(len(utr3), spans["utr3_preserved"], "prefix",
                                  needed - share5, rng, max_homopolymer)

        if translate(designed_codons) != protein:
            rejected["protein_changed"] = rejected.get("protein_changed", 0) + 1
            continue
        if out_of_frame_uaug(member_utr5):
            rejected["out_of_frame_uaug"] = rejected.get("out_of_frame_uaug", 0) + 1
            continue
        sequence = member_utr5 + orf + member_utr3
        if len(sequence) != total:
            rejected["length_changed"] = rejected.get("length_changed", 0) + 1
            continue
        if longest_homopolymer(sequence) > max_homopolymer:
            rejected["homopolymer_run_too_long"] = rejected.get(
                "homopolymer_run_too_long", 0) + 1
            continue
        digest = hashlib.sha256(sequence.encode()).hexdigest()
        if digest in seen:
            rejected["duplicate"] = rejected.get("duplicate", 0) + 1
            continue
        seen.add(digest)
        entry = describe(member_utr5, designed_codons, member_utr3, False)
        entry["member"] = len(members)
        entry["target_gc_fraction"] = target
        members.append(entry)

    return {
        "reference_transcript_sha256": members[0]["transcript_sha256"],
        "protein_sha256": hashlib.sha256(protein.encode()).hexdigest(),
        "transcript_length_nt": total,
        "editable": spans,
        "substitutable_codons": len(indices),
        "reachable_gc_range": {"minimum": bounds["minimum"], "maximum": bounds["maximum"]},
        "size": len(members),
        "seed": seed,
        "max_homopolymer": max_homopolymer,
        "attempts": attempts,
        "rejected": rejected,
        "members": members,
        "scored": False,
        "utrs_are_designed_not_supplied": True,
    }
