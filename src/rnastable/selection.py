"""Select a deployable sequence only after a finite reference-energy improvement."""
import math


def select_finalist(original, finalist, search_status, reference, validation):
    """Return the decision, preserving the distinction between unknown and zero.

    Search proposals remain evidence even when selection returns the input.
    The numerical tolerance matches existing ViennaRNA improvement reporting.
    """
    def energy(record):
        if not record or record.get('status') != 'ok':
            return None
        value = record.get('mfe_kcal_mol')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return None
        return value

    before, after = energy(reference), energy(validation)
    delta = after-before if before is not None and after is not None else None
    if delta is not None and not math.isfinite(delta):
        delta = None
    confirmed = delta < -1e-9 if delta is not None else None
    if search_status != 'completed':
        reason = 'search_failed'
    elif delta is None:
        reason = 'validation_failed'
    elif finalist == original:
        reason = 'unchanged_sequence'
    elif confirmed:
        reason = 'confirmed_improvement'
    else:
        reason = 'no_reference_improvement'
    selected = reason == 'confirmed_improvement'
    return {'policy': 'require_vienna_improvement_v1',
            'source': 'finalist' if selected else 'input', 'reason': reason,
            'vienna_improvement_confirmed': confirmed,
            'candidate_vienna_delta_kcal_mol': delta,
            'selected_vienna_energy_kcal_mol': after if selected else before,
            'selected_vienna_delta_kcal_mol': delta if selected else (0.0 if before is not None else None)}
