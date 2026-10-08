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


def base_pairs(structure):
    """Return zero-based pairs for a validated pseudoknot-free structure."""
    paired_fraction(structure)
    stack, pairs = [], set()
    for i, char in enumerate(structure):
        if char == '(':
            stack.append(i)
        elif char == ')':
            pairs.add((stack.pop(), i))
    return pairs


def structure_agreement(prediction, reference):
    """Pair agreement against a computational reference, not biological truth."""
    if len(prediction) != len(reference):
        raise ValueError('Structure length mismatch')
    predicted, actual = base_pairs(prediction), base_pairs(reference)
    common = len(predicted & actual)
    both_empty = not predicted and not actual
    return {
        'reference_pairs': len(actual), 'predicted_pairs': len(predicted), 'shared_pairs': common,
        'pair_precision': common/len(predicted) if predicted else float(both_empty),
        'pair_recall': common/len(actual) if actual else float(both_empty),
        'pair_f1': 2*common/(len(predicted)+len(actual)) if predicted or actual else 1.0,
        'pair_jaccard': common/len(predicted | actual) if predicted or actual else 1.0,
        'base_pair_distance': len(predicted ^ actual),
    }
