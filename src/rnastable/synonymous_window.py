"""Windowed synonymous ORF variants: the declared design space.

The user chose on 2026-10-20 that the optimisation domain is **synonymous edits
confined to a window at the 5' end of the ORF**, enumerated into a finite pool
that the optimizer then selects from. The whole-ORF space is about 10^273
variants and is not a domain; a 30-codon window is still about 10^13, so even
the window is sampled into a pool rather than enumerated exhaustively.

Why a window at the 5' end: edits there are localised, so a result is
interpretable, and the region is the one usually implicated in initiation. That
is the stated reason for the choice, **not** a finding of this project. Nothing
here establishes that 5' edits matter more than edits elsewhere.

What this module does NOT do:

- It does not score anything. `new_sequence_scoring_enabled` is false in gate
  v5, and no structure, stability or translation value is computed here.
- It does not propose assay candidates. `expression_candidate_design_enabled` is
  false. A pool is a specification of the domain; promoting members to
  candidates is a separate gate decision.
- It emits no optimizer feature matrix, for the same reason.

The protein is preserved exactly. Every constraint below is checked on every
member, and a member that fails any of them is discarded rather than repaired,
so the pool cannot contain a silently corrected sequence.
"""
import hashlib
import random

from .sequences import validate_sequence

# Standard genetic code, built once from Biopython so the table is not retyped
# here. Stops are included so the terminator is handled like any other codon.
_CODON_TO_AA = None


def codon_table():
    """Codon -> amino acid for the standard code, with '*' for stops."""
    global _CODON_TO_AA
    if _CODON_TO_AA is None:
        from Bio.Data.CodonTable import unambiguous_dna_by_id

        table = unambiguous_dna_by_id[1]
        mapping = dict(table.forward_table)
        mapping.update({codon: "*" for codon in table.stop_codons})
        _CODON_TO_AA = mapping
    return _CODON_TO_AA


def synonyms():
    """Amino acid -> its codons, each list in deterministic sorted order."""
    groups = {}
    for codon, amino_acid in sorted(codon_table().items()):
        groups.setdefault(amino_acid, []).append(codon)
    return groups


def split_codons(cds):
    """Codons of a DNA ORF, validated as a complete reading frame."""
    cds = cds.strip().upper().replace("U", "T")
    if not cds or len(cds) % 3:
        raise ValueError(f"ORF length {len(cds)} is not a multiple of three")
    if set(cds) - set("ACGT"):
        raise ValueError("ORF must contain A, C, G and T only")
    codons = [cds[i: i + 3] for i in range(0, len(cds), 3)]
    table = codon_table()
    if table[codons[0]] != "M":
        raise ValueError(f"ORF does not start with a start codon: {codons[0]}")
    if table[codons[-1]] != "*":
        raise ValueError(f"ORF does not end with a stop codon: {codons[-1]}")
    if any(table[codon] == "*" for codon in codons[:-1]):
        raise ValueError("ORF contains an internal in-frame stop codon")
    return codons


def translate(codons):
    table = codon_table()
    return "".join(table[codon] for codon in codons)


def window_indices(codons, window_codons):
    """Codon positions open to substitution.

    The start codon is excluded because AUG is its own only synonym and because
    changing position 0 is not a synonymous edit in any case. The terminator is
    excluded for the same reason: its substitutions change the stop identity,
    and the construct's tandem-stop arrangement is a deliberate design the
    collaborator confirmed, not something to vary.
    """
    if type(window_codons) is not int or window_codons < 1:
        raise ValueError("window_codons must be a positive integer")
    last = min(1 + window_codons, len(codons) - 1)
    if last <= 1:
        raise ValueError("Window does not contain a substitutable codon")
    return list(range(1, last))


def longest_homopolymer(sequence):
    longest, run = 1, 1
    for previous, current in zip(sequence, sequence[1:]):
        run = run + 1 if current == previous else 1
        longest = max(longest, run)
    return longest if sequence else 0


def check_variant(reference_codons, variant_codons, indices, max_homopolymer):
    """Return the reason a variant is unacceptable, or None if it is fine.

    Returning a reason rather than raising lets the sampler count rejections by
    cause, which is what makes a pool's composition auditable.
    """
    if len(variant_codons) != len(reference_codons):
        return "length_changed"
    if translate(variant_codons) != translate(reference_codons):
        return "protein_changed"
    if variant_codons[0] != reference_codons[0]:
        return "start_codon_changed"
    if variant_codons[-1] != reference_codons[-1]:
        return "stop_codon_changed"
    allowed = set(indices)
    changed = {i for i, (a, b) in enumerate(zip(reference_codons, variant_codons)) if a != b}
    if changed - allowed:
        return "change_outside_window"
    sequence = "".join(variant_codons)
    if longest_homopolymer(sequence) > max_homopolymer:
        return "homopolymer_run_too_long"
    return None


def describe(reference_codons, variant_codons, indices):
    """Descriptive composition only. No score, and no optimizer features."""
    sequence = "".join(variant_codons)
    window = "".join(variant_codons[i] for i in indices)
    substitutions = sorted(i for i, (a, b) in enumerate(zip(reference_codons, variant_codons))
                           if a != b)
    third_positions = [codon[2] for codon in variant_codons]
    return {
        "substituted_codon_indices": substitutions,
        "substitution_count": len(substitutions),
        "window_gc_fraction": (window.count("G") + window.count("C")) / len(window),
        "orf_gc_fraction": (sequence.count("G") + sequence.count("C")) / len(sequence),
        "orf_gc3_fraction": sum(base in "GC" for base in third_positions) / len(third_positions),
        "longest_homopolymer": longest_homopolymer(sequence),
        "orf_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
    }


def build_pool(cds, window_codons=30, size=512, seed=1729, max_homopolymer=6,
               gc_decorrelation=True, gc_mode="free",
               max_attempts_per_member=200):
    """Sample a deterministic pool of windowed synonymous variants.

    Member 0 is the unmodified reference, so the pool always contains the
    construct everything else is compared against.

    Each further member first draws how many positions to change, uniformly
    over 1..substitutable, then which positions, then a codon different from
    the reference at each. Drawing a codon independently per position instead
    would concentrate every member around the same substitution count -- with
    29 substitutable positions almost all members would change 14 to 19 of
    them -- leaving the pool with nothing near the reference. The edit distance
    to the reference is the one axis most likely to matter, so it is sampled
    evenly rather than left to emerge.

    `gc_mode` selects which synonyms are allowed:

    - "free": any synonym. The window is GC-rich, so edits walk GC downwards
      and GC stays correlated with edit distance even after decorrelation.
    - "neutral": only synonyms with the same GC count as the reference codon,
      which holds window GC exactly constant and removes that confound
      entirely, at the cost of a far smaller space.

    Duplicates are rejected, as are variants failing any constraint. The RNG is
    seeded locally and the caller's global random state is untouched.
    """
    validate_sequence(cds.strip().upper().replace("T", "U"))
    reference = split_codons(cds)
    indices = window_indices(reference, window_codons)
    groups = synonyms()
    table = codon_table()
    if type(size) is not int or size < 1:
        raise ValueError("size must be a positive integer")
    if gc_mode not in ("free", "neutral"):
        raise ValueError("gc_mode must be 'free' or 'neutral'")

    def gc_count(codon):
        return codon.count("G") + codon.count("C")

    def alternatives_for(i):
        options = [c for c in groups[table[reference[i]]] if c != reference[i]]
        if gc_mode == "neutral":
            options = [c for c in options if gc_count(c) == gc_count(reference[i])]
        return options

    substitutable = [i for i in indices if alternatives_for(i)]
    if not substitutable:
        raise ValueError("No substitutable codon in the window under this gc_mode")

    rng = random.Random(seed)
    members = [{"member": 0, "codons": list(reference), "is_reference": True,
                **describe(reference, reference, indices)}]
    seen = {"".join(reference)}
    rejected, attempts = {}, 0
    while len(members) < size:
        attempts += 1
        if attempts > size * max_attempts_per_member:
            raise RuntimeError(
                f"Could not reach {size} unique members after {attempts} attempts; "
                f"rejections so far: {rejected}")
        variant = list(reference)
        count = rng.randint(1, len(substitutable))
        # A GC tendency drawn once per member, independent of the edit count.
        # Without it, substituting uniformly at random walks the GC-rich 5'
        # window downwards, and window GC ends up almost perfectly collinear
        # with the number of edits (r = -0.98 measured), so no later analysis
        # could separate the two. Sharing one tendency across a member's
        # positions spans the GC range at every edit distance instead.
        bias = rng.random() if gc_decorrelation else None
        for i in rng.sample(substitutable, count):
            alternatives = alternatives_for(i)
            if bias is None:
                variant[i] = rng.choice(alternatives)
            else:
                ranked = sorted(alternatives, key=lambda c: (c.count("G") + c.count("C"), c))
                variant[i] = ranked[min(len(ranked) - 1, int(bias * len(ranked)))]
        sequence = "".join(variant)
        if sequence in seen:
            rejected["duplicate"] = rejected.get("duplicate", 0) + 1
            continue
        reason = check_variant(reference, variant, indices, max_homopolymer)
        if reason is not None:
            rejected[reason] = rejected.get(reason, 0) + 1
            continue
        seen.add(sequence)
        members.append({"member": len(members), "codons": variant, "is_reference": False,
                        **describe(reference, variant, indices)})
    return {
        "reference_orf_sha256": hashlib.sha256("".join(reference).encode()).hexdigest(),
        "protein_sha256": hashlib.sha256(translate(reference).encode()).hexdigest(),
        "orf_length_nt": len(cds.strip()),
        "codon_count": len(reference),
        "window_codons": window_codons,
        "window_codon_indices": indices,
        "substitutable_positions": len(substitutable),
        "size": len(members),
        "seed": seed,
        "max_homopolymer": max_homopolymer,
        "gc_decorrelation": gc_decorrelation,
        "gc_mode": gc_mode,
        "attempts": attempts,
        "rejected": rejected,
        "members": members,
        "scored": False,
        "optimizer_features_emitted": False,
    }
