"""Descriptive scores, not validated RNA stability or biological fitness."""
from .sequences import validate_sequence

def gc_fraction(sequence):
    validate_sequence(sequence)
    return (sequence.count('G') + sequence.count('C')) / len(sequence)

def mfe_per_nt(mfe_kcal_mol, sequence):
    import math
    validate_sequence(sequence)
    if not math.isfinite(mfe_kcal_mol):
        raise ValueError('MFE must be finite')
    return mfe_kcal_mol / len(sequence)

def paired_fraction(structure, expected_length=None):
    if not structure or set(structure) - set('.()'):
        raise ValueError('Expected nonempty dot-bracket structure')
    if expected_length is not None and len(structure) != expected_length:
        raise ValueError('Structure length mismatch')
    depth = 0
    for char in structure:
        depth += (char == '(') - (char == ')')
        if depth < 0:
            raise ValueError('Unbalanced structure')
    if depth:
        raise ValueError('Unbalanced structure')
    return (structure.count('(') + structure.count(')')) / len(structure)
