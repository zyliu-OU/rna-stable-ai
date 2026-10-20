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
    config_path: str
    no_claim: str = (
        "A validated assembly of supplied inputs. Establishes no stability, "
        "translation or expression claim."
    )

    def to_dict(self):
        return asdict(self)


def assemble(cds_bases, config_path, tx_id, provenance, assay_context, include_poly_a=False):
    """Assemble and validate the reference transcript from a supplied CDS.

    The CDS is verified against the hash recorded in the config before anything
    else happens, so a wrong sequence fails immediately rather than after
    producing a plausible-looking transcript.
    """
    data = load_inputs(config_path)
    components = data["components"]
    recorded = data["region_boundary_decision"]["consequence"]

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
    expected = components["cds"]["sha256_dna_uppercase"]
    if observed != expected:
        raise ValueError(
            "Supplied CDS does not match the recorded reference CDS. "
            f"Expected sha256 {expected}, observed {observed} "
            f"(supplied length {len(cds_dna)} nt, recorded {components['cds']['length_nt']} nt). "
            "This is a different sequence and must not be treated as the same construct."
        )

    utr5 = to_rna(components["utr5"]["sequence_dna_uppercase"])
    utr3 = to_rna(components["utr3"]["sequence_dna_uppercase"])
    cds = to_rna(cds_dna)

    # The config carries the lengths the boundary decision was made under. If a
    # component were edited without that decision being revisited, the layout
    # would silently shift, so the two are cross-checked rather than trusted.
    for label, observed_len, recorded_len in (
        ("utr5", len(utr5), recorded["utr5_length_nt"]),
        ("cds", len(cds), recorded["cds_length_nt"]),
        ("utr3", len(utr3), recorded["utr3_length_nt"]),
    ):
        if observed_len != recorded_len:
            raise ValueError(
                f"{label} length {observed_len} nt contradicts the recorded region "
                f"boundary decision ({recorded_len} nt). The boundary decision must be "
                "revisited before assembly, not worked around."
            )

    sequence = utr5 + cds + utr3
    if len(sequence) != recorded["transcript_length_nt"]:
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
        config_path=str(config_path),
    )
