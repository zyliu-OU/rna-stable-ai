"""Constrained CPU ViennaRNA MFE routine, for the native constraint decoder.

Reads two stdin lines: the sequence, then a dot-bracket hard-constraint string
of equal length. Unconstrained positions are '.', and enforced pairs are given
as matching brackets. Constraints are enforced rather than merely preferred, so
an unsatisfiable constraint surfaces as a refusal here instead of silently
folding without it.

ViennaRNA does not always refuse an unsatisfiable enforced pair. A pair that
violates the minimum hairpin size is dropped and the fold proceeds without it,
returning a finite energy and a structure that does not contain the requested
pair. Every enforced pair is therefore checked against the returned structure
here, and a dropped constraint is reported as a refusal rather than a fold.
"""
import sys

import RNA

from .scoring import base_pairs

sequence = sys.stdin.readline().strip()
constraint = sys.stdin.readline().strip()
if len(constraint) != len(sequence):
    raise SystemExit(
        f"Constraint length {len(constraint)} does not match sequence {len(sequence)}"
    )
md = RNA.md()
md.temperature = float(sys.argv[1])
compound = RNA.fold_compound(sequence, md)
compound.hc_add_from_db(
    constraint, RNA.CONSTRAINT_DB_DEFAULT | RNA.CONSTRAINT_DB_ENFORCE_BP
)
structure, energy = compound.mfe()
# An enforced constraint that cannot be met yields an infinite MFE rather than
# an exception, so the refusal is made explicit instead of being reported as a
# successful fold.
if energy != energy or abs(energy) > 1e6:
    raise SystemExit(f"Enforced constraint is unsatisfiable (MFE {energy})")
missing = sorted(base_pairs(constraint) - base_pairs(structure))
if missing:
    raise SystemExit(
        f"Enforced constraint silently dropped; {len(missing)} requested pairs "
        f"absent from the fold, first {missing[0]}"
    )
print(sequence)
print(f"{structure} ({energy:.2f})")
