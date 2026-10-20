"""Assemble the reference transcript from the recorded component inputs.

The 5' UTR and 3' UTR are recorded in configs/transcript_inputs_v1_2026-10-19.json
together with the region boundary decision. The CDS bases are not: an earlier
session retained only their hash, and the bases were lost. This module exists so
that when the CDS is re-supplied it is bound to that recorded hash and assembled
under the recorded layout in one step, rather than by hand.

Two rules are enforced rather than assumed:

Supplied bases are verified before use. A CDS whose hash does not match the
recorded one is a different sequence, and is refused rather than quietly
accepted as the same construct. The whole provenance chain depends on that
hash, so there is deliberately no override parameter to bypass it.

Conversion from DNA to RNA is explicit. Transcript performs no silent
normalization, so T to U conversion and case folding happen here, once, and are
reported in the result rather than applied invisibly somewhere downstream.

Assembling a transcript establishes no stability, translation or expression
claim. It produces a validated input, nothing more.
"""
from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path

from .component_integration import Transcript, digest

STOP_CODONS = ("UAA", "UAG", "UGA")


def to_rna(sequence):
    """Explicit uppercase DNA to RNA conversion; the only place this happens."""
    if not isinstance(sequence, str) or not sequence:
        raise ValueError("Sequence must be a nonempty string")
    upper = sequence.upper()
    if set(upper) - set("ACGTU"):
        raise ValueError("Sequence must contain only canonical ACGT/ACGU characters")
    if "T" in upper and "U" in upper:
        raise ValueError("Mixed T and U in one sequence; the intended alphabet is ambiguous")
    return upper.replace("T", "U")


def load_inputs(config_path):
    """Read the recorded transcript component inputs and boundary decision."""
    data = json.loads(Path(config_path).read_text())
    if "components" not in data or "region_boundary_decision" not in data:
        raise ValueError("Config is not a transcript inputs record")
    return data


@dataclass(frozen=True)
class AssemblyReport:
    """What was assembled, from what, and under which recorded decisions."""
    tx_id: str
    transcript_length_nt: int
    utr5_length_nt: int
    cds_length_nt: int
    utr3_length_nt: int
    poly_a_length_nt: int
    poly_a_included: bool
    cds_start: int
    cds_end: int
    protein_length_aa: int
    cds_sha256_dna_uppercase: str
    transcript_sha256_rna: str
    identity_sha256: str
    tandem_stop_present: bool
    tandem_stop_codon: str | None
    ribonn_exclusion: str | None
    alphabet_conversion: str
    cds_component: str
    config_path: str
    no_claim: str = (
        "A validated assembly of supplied inputs. Establishes no stability, "
        "translation or expression claim."
    )
    # Populated only by assemble_variant. A reference assembly leaves these
    # None so that a variant can never be mistaken for the reference in a
    # recorded artifact, or the reverse.
    variant_of: str | None = None
    reference_cds_sha256_dna_uppercase: str | None = None
    synonymous_verified: bool | None = None
    substituted_codon_indices: tuple | None = None
    protein_sha256: str | None = None
    # Populated only by assemble_designed. None elsewhere, so a designed
    # transcript can never be mistaken for one built on the supplied UTRs.
    utrs_designed: bool | None = None
    utr5_edits: int | None = None
    utr3_edits: int | None = None

    def to_dict(self):
        return asdict(self)


def assemble(cds_bases, config_path, tx_id, provenance, assay_context, include_poly_a=False,
             cds_component="cds"):
    """Assemble and validate a transcript from a supplied CDS.

    The CDS is verified against the hash recorded in the config before anything
    else happens, so a wrong sequence fails immediately rather than after
    producing a plausible-looking transcript.

    `cds_component` names which recorded CDS to verify against. The project
    records more than one construct (Fluc and Fluc-PEST), and they are different
    sequences of different lengths. Naming the component explicitly keeps each
    one bound to its own hash, so the second construct cannot be assembled by
    relaxing the first one's gate.
    """
    data = load_inputs(config_path)
    components = data["components"]
    recorded = data["region_boundary_decision"]["consequence"]
    if cds_component not in components:
        raise ValueError(f"Config records no CDS component named {cds_component!r}")
    cds_record = components[cds_component]

    cds_upper = cds_bases.upper().strip() if isinstance(cds_bases, str) else None
    if not cds_upper:
        raise ValueError("CDS bases must be a nonempty string")
    if set(cds_upper) - set("ACGTU"):
        raise ValueError("CDS must contain only canonical ACGT/ACGU characters")
    # Hash the DNA form, because that is the form the recorded hash was taken
    # over. Hashing the RNA form would never match and would look like a
    # supplied-sequence error rather than a convention error.
    cds_dna = cds_upper.replace("U", "T")
    observed = hashlib.sha256(cds_dna.encode()).hexdigest()
    expected = cds_record["sha256_dna_uppercase"]
    if observed != expected:
        raise ValueError(
            f"Supplied CDS does not match the recorded CDS {cds_component!r}. "
            f"Expected sha256 {expected}, observed {observed} "
            f"(supplied length {len(cds_dna)} nt, recorded {cds_record['length_nt']} nt). "
            "This is a different sequence and must not be treated as the same construct."
        )

    utr5 = to_rna(components["utr5"]["sequence_dna_uppercase"])
    utr3 = to_rna(components["utr3"]["sequence_dna_uppercase"])
    cds = to_rna(cds_dna)

    # The config carries the lengths the boundary decision was made under. If a
    # component were edited without that decision being revisited, the layout
    # would silently shift, so the two are cross-checked rather than trusted.
    # The UTRs and the tandem-stop decision are shared across constructs, so
    # they are checked against the boundary decision. The CDS length is checked
    # against its own component record, because a second construct legitimately
    # has a different length while sharing the same UTR layout.
    for label, observed_len, recorded_len in (
        ("utr5", len(utr5), recorded["utr5_length_nt"]),
        ("cds", len(cds), cds_record["length_nt"]),
        ("utr3", len(utr3), recorded["utr3_length_nt"]),
    ):
        if observed_len != recorded_len:
            raise ValueError(
                f"{label} length {observed_len} nt contradicts the recorded region "
                f"boundary decision ({recorded_len} nt). The boundary decision must be "
                "revisited before assembly, not worked around."
            )

    sequence = utr5 + cds + utr3
    expected_length = (recorded["utr5_length_nt"] + cds_record["length_nt"]
                       + recorded["utr3_length_nt"])
    if len(sequence) != expected_length:
        raise ValueError("Assembled length contradicts the recorded component lengths")
    if cds_component == "cds" and len(sequence) != recorded["transcript_length_nt"]:
        raise ValueError("Assembled length contradicts the recorded transcript length")

    # The real transfected molecule carries a template-encoded poly(A) tail, but
    # appending it may push the input outside the distribution the downstream
    # models were derived on. The choice is therefore explicit, never implied by
    # the config merely recording a tail.
    poly_a = ""
    if include_poly_a:
        context = data.get("construct_context_from_ping", {}).get("poly_a")
        if not context:
            raise ValueError("No poly(A) is recorded in this config, so none can be appended")
        poly_a = "A" * int(context["length_nt"])
        sequence = sequence + poly_a

    # Transcript validates the CDS itself: start codon, terminal stop, no
    # internal stop, complete frame.
    transcript = Transcript(
        tx_id=tx_id,
        sequence=sequence,
        cds_start=len(utr5),
        cds_end=len(utr5) + len(cds),
        provenance=provenance,
        assay_context=assay_context,
    )

    # The recorded decision assigns a tandem stop to the 3' UTR. Report whether
    # one is actually present rather than assuming the decision was applied.
    leading = utr3[:3]
    tandem = leading in STOP_CODONS

    return transcript, AssemblyReport(
        tx_id=tx_id,
        transcript_length_nt=len(sequence),
        utr5_length_nt=len(utr5),
        cds_length_nt=len(cds),
        utr3_length_nt=len(utr3),
        poly_a_length_nt=len(poly_a),
        poly_a_included=bool(include_poly_a),
        cds_start=transcript.cds_start,
        cds_end=transcript.cds_end,
        # Transcript has already enforced a terminal stop and complete frame, so
        # the residue count is the codon count less that stop.
        protein_length_aa=len(cds) // 3 - 1,
        cds_sha256_dna_uppercase=observed,
        transcript_sha256_rna=digest(sequence),
        identity_sha256=transcript.identity_sha256,
        tandem_stop_present=tandem,
        tandem_stop_codon=leading if tandem else None,
        ribonn_exclusion=transcript.ribonn_exclusion(),
        alphabet_conversion="supplied DNA uppercased and T converted to U",
        cds_component=cds_component,
        config_path=str(config_path),
    )


def assemble_variant(variant_cds_bases, config_path, tx_id, provenance, assay_context,
                     include_poly_a=False, reference_component="cds"):
    """Assemble a transcript from a SYNONYMOUS VARIANT of a recorded CDS.

    `assemble` hash-gates the CDS against the config, which is exactly right for
    the reference construct and refuses a designed variant by design. This is
    the deliberate, separate path for variants, and it does not weaken that
    gate -- it adds a stricter one.

    The reference CDS is still read from the config's recorded `sequence_file`
    and still verified against its recorded hash, so the UTR layout and the
    region-boundary decision remain bound to the same reference as before. The
    supplied variant must then prove it is a synonymous variant of that exact
    sequence: identical length, identical translated protein, and a valid
    reading frame. A variant that changes the protein, the length or the frame
    is refused.

    Both hashes and the substituted codon positions are recorded, so a variant
    transcript can never be mistaken for the reference in a later artifact.
    """
    data = load_inputs(config_path)
    components = data["components"]
    if reference_component not in components:
        raise ValueError(f"Config records no CDS component named {reference_component!r}")
    record = components[reference_component]
    sequence_file = record.get("sequence_file")
    if not sequence_file:
        raise ValueError(
            f"Component {reference_component!r} records no sequence_file, so the "
            "reference CDS cannot be read and a variant cannot be checked against it")

    reference_path = Path(config_path).resolve().parents[1] / sequence_file
    reference_dna = "".join(reference_path.read_text().split()).upper().replace("U", "T")
    reference_hash = hashlib.sha256(reference_dna.encode()).hexdigest()
    if reference_hash != record["sha256_dna_uppercase"]:
        raise ValueError(
            f"Recorded reference CDS {reference_component!r} does not match its own hash. "
            f"Expected {record['sha256_dna_uppercase']}, observed {reference_hash} from "
            f"{sequence_file}. The reference must be fixed before any variant is assembled.")

    variant_upper = variant_cds_bases.upper().strip() if isinstance(variant_cds_bases, str) else None
    if not variant_upper:
        raise ValueError("Variant CDS bases must be a nonempty string")
    if set(variant_upper) - set("ACGTU"):
        raise ValueError("Variant CDS must contain only canonical ACGT/ACGU characters")
    variant_dna = variant_upper.replace("U", "T")

    if len(variant_dna) != len(reference_dna):
        raise ValueError(
            f"Variant length {len(variant_dna)} nt differs from the reference "
            f"{len(reference_dna)} nt. A synonymous variant has the same length.")

    from .synonymous_window import split_codons, translate

    reference_codons = split_codons(reference_dna)
    variant_codons = split_codons(variant_dna)
    reference_protein = translate(reference_codons)
    if translate(variant_codons) != reference_protein:
        raise ValueError(
            "Variant does not translate to the reference protein. This is not a "
            "synonymous variant and must not be assembled as one.")

    substituted = tuple(i for i, (a, b) in enumerate(zip(reference_codons, variant_codons))
                        if a != b)
    variant_hash = hashlib.sha256(variant_dna.encode()).hexdigest()

    utr5 = to_rna(components["utr5"]["sequence_dna_uppercase"])
    utr3 = to_rna(components["utr3"]["sequence_dna_uppercase"])
    cds = to_rna(variant_dna)
    recorded = data["region_boundary_decision"]["consequence"]
    for label, observed_len, recorded_len in (
        ("utr5", len(utr5), recorded["utr5_length_nt"]),
        ("cds", len(cds), record["length_nt"]),
        ("utr3", len(utr3), recorded["utr3_length_nt"]),
    ):
        if observed_len != recorded_len:
            raise ValueError(
                f"{label} length {observed_len} nt contradicts the recorded region "
                f"boundary decision ({recorded_len} nt). The boundary decision must be "
                "revisited before assembly, not worked around.")

    sequence = utr5 + cds + utr3
    poly_a = ""
    if include_poly_a:
        context = data.get("construct_context_from_ping", {}).get("poly_a")
        if not context:
            raise ValueError("No poly(A) is recorded in this config, so none can be appended")
        poly_a = "A" * int(context["length_nt"])
        sequence = sequence + poly_a

    transcript = Transcript(
        tx_id=tx_id,
        sequence=sequence,
        cds_start=len(utr5),
        cds_end=len(utr5) + len(cds),
        provenance=provenance,
        assay_context=assay_context,
    )
    leading = utr3[:3]
    tandem = leading in STOP_CODONS

    return transcript, AssemblyReport(
        tx_id=tx_id,
        transcript_length_nt=len(sequence),
        utr5_length_nt=len(utr5),
        cds_length_nt=len(cds),
        utr3_length_nt=len(utr3),
        poly_a_length_nt=len(poly_a),
        poly_a_included=bool(include_poly_a),
        cds_start=transcript.cds_start,
        cds_end=transcript.cds_end,
        protein_length_aa=len(cds) // 3 - 1,
        cds_sha256_dna_uppercase=variant_hash,
        transcript_sha256_rna=digest(sequence),
        identity_sha256=transcript.identity_sha256,
        tandem_stop_present=tandem,
        tandem_stop_codon=leading if tandem else None,
        ribonn_exclusion=transcript.ribonn_exclusion(),
        alphabet_conversion="supplied DNA uppercased and T converted to U",
        cds_component=reference_component,
        config_path=str(config_path),
        no_claim=(
            "A validated assembly of a synonymous variant of the recorded reference CDS. "
            "The protein is preserved and verified. Establishes no stability, translation "
            "or expression claim, and the variant has no measurement of any kind."),
        variant_of=reference_component,
        reference_cds_sha256_dna_uppercase=reference_hash,
        synonymous_verified=True,
        substituted_codon_indices=substituted,
        protein_sha256=hashlib.sha256(reference_protein.encode()).hexdigest(),
    )


def assemble_designed(utr5, cds_bases, utr3, config_path, tx_id, provenance, assay_context,
                      reference_component="cds"):
    """Assemble a transcript whose UTRs are DESIGNED, not the supplied ones.

    `assemble_variant` holds the UTRs at the collaborator's supplied sequences and
    allows only a synonymous CDS. This path additionally accepts redesigned UTR
    composition, and is deliberately separate because the guarantee it can offer
    is weaker: the protein is still verified exactly, but the UTRs no longer
    carry the supplied sequences' provenance.

    What is still enforced, because removing any of it would change the construct
    for reasons unrelated to the composition being designed:

    - the protein, verified by translating against the recorded reference CDS
    - every length: the supplied UTR lengths and the reference CDS length
    - the 5' UTR's final Kozak context and the 3' UTR's opening tandem stop
    - no out-of-frame uAUG in the 5' UTR

    The report records what was redesigned and marks the UTRs as designed, so a
    designed transcript can never be mistaken for the supplied construct.
    """
    from .transcript_design import KOZAK_SUFFIX, TANDEM_STOP_PREFIX, out_of_frame_uaug
    from .synonymous_window import split_codons, translate

    data = load_inputs(config_path)
    components = data["components"]
    if reference_component not in components:
        raise ValueError(f"Config records no CDS component named {reference_component!r}")
    record = components[reference_component]
    sequence_file = record.get("sequence_file")
    if not sequence_file:
        raise ValueError(f"Component {reference_component!r} records no sequence_file")

    reference_path = Path(config_path).resolve().parents[1] / sequence_file
    reference_dna = "".join(reference_path.read_text().split()).upper().replace("U", "T")
    reference_hash = hashlib.sha256(reference_dna.encode()).hexdigest()
    if reference_hash != record["sha256_dna_uppercase"]:
        raise ValueError(
            f"Recorded reference CDS {reference_component!r} does not match its own hash")

    supplied5 = components["utr5"]["sequence_dna_uppercase"].upper()
    supplied3 = components["utr3"]["sequence_dna_uppercase"].upper()
    designed5 = utr5.strip().upper().replace("U", "T")
    designed3 = utr3.strip().upper().replace("U", "T")
    variant_dna = cds_bases.strip().upper().replace("U", "T")
    for label, value in (("5' UTR", designed5), ("CDS", variant_dna), ("3' UTR", designed3)):
        if not value or set(value) - set("ACGT"):
            raise ValueError(f"{label} must be nonempty and canonical ACGT/ACGU")

    for label, got, want in (("5' UTR", len(designed5), len(supplied5)),
                             ("CDS", len(variant_dna), len(reference_dna)),
                             ("3' UTR", len(designed3), len(supplied3))):
        if got != want:
            raise ValueError(
                f"{label} length {got} nt differs from the recorded {want} nt. This path "
                "designs composition only; lengths are fixed.")

    if not designed5.endswith(KOZAK_SUFFIX):
        raise ValueError(f"Designed 5' UTR does not preserve the Kozak context {KOZAK_SUFFIX}")
    if not designed3.startswith(TANDEM_STOP_PREFIX):
        raise ValueError(
            f"Designed 3' UTR does not preserve the tandem stop {TANDEM_STOP_PREFIX}")
    if out_of_frame_uaug(designed5):
        raise ValueError("Designed 5' UTR contains an out-of-frame uAUG")

    reference_codons = split_codons(reference_dna)
    variant_codons = split_codons(variant_dna)
    reference_protein = translate(reference_codons)
    if translate(variant_codons) != reference_protein:
        raise ValueError("Designed CDS does not translate to the reference protein")

    substituted = tuple(i for i, (a, b) in enumerate(zip(reference_codons, variant_codons))
                        if a != b)
    sequence = to_rna(designed5) + to_rna(variant_dna) + to_rna(designed3)
    transcript = Transcript(
        tx_id=tx_id, sequence=sequence, cds_start=len(designed5),
        cds_end=len(designed5) + len(variant_dna),
        provenance=provenance, assay_context=assay_context)
    leading = to_rna(designed3)[:3]

    return transcript, AssemblyReport(
        tx_id=tx_id,
        transcript_length_nt=len(sequence),
        utr5_length_nt=len(designed5),
        cds_length_nt=len(variant_dna),
        utr3_length_nt=len(designed3),
        poly_a_length_nt=0,
        poly_a_included=False,
        cds_start=transcript.cds_start,
        cds_end=transcript.cds_end,
        protein_length_aa=len(variant_dna) // 3 - 1,
        cds_sha256_dna_uppercase=hashlib.sha256(variant_dna.encode()).hexdigest(),
        transcript_sha256_rna=digest(sequence),
        identity_sha256=transcript.identity_sha256,
        tandem_stop_present=leading in STOP_CODONS,
        tandem_stop_codon=leading if leading in STOP_CODONS else None,
        ribonn_exclusion=transcript.ribonn_exclusion(),
        alphabet_conversion="supplied DNA uppercased and T converted to U",
        cds_component=reference_component,
        config_path=str(config_path),
        no_claim=(
            "A validated assembly of a DESIGNED transcript. The protein is preserved and "
            "verified, and every length, the Kozak context and the tandem stop are unchanged. "
            "The UTRs are DESIGNED and do NOT carry the supplied sequences' provenance: this "
            "is a new construct, not the supplied construct with tweaks. Establishes no "
            "stability, translation or expression claim, and has no measurement of any kind."),
        variant_of=reference_component,
        reference_cds_sha256_dna_uppercase=reference_hash,
        synonymous_verified=True,
        substituted_codon_indices=substituted,
        protein_sha256=hashlib.sha256(reference_protein.encode()).hexdigest(),
        utrs_designed=True,
        utr5_edits=sum(1 for a, b in zip(supplied5, designed5) if a != b),
        utr3_edits=sum(1 for a, b in zip(supplied3, designed3) if a != b),
    )
