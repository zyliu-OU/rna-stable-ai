"""Matched beam comparisons; failed measurements remain missing."""
from collections import defaultdict


PAIR_FIELDS = ['kind', 'length', 'sequence_seed', 'search_seed', 'input_sha256',
               'low_beam', 'high_beam', 'low_status', 'high_status',
               'input_pair_f1_change', 'input_lf_time_ratio',
               'vienna_delta_difference_kcal_mol']


def paired_comparisons(rows, low_beam=200, high_beam=400):
    groups = defaultdict(dict)
    for row in rows:
        key = tuple(row[k] for k in ('kind', 'length', 'sequence_seed', 'search_seed'))
        beam = row['beam_size']
        if beam not in (low_beam, high_beam):
            raise ValueError('Unexpected beam in paired comparison')
        if beam in groups[key]:
            raise ValueError('Duplicate paired observation')
        groups[key][beam] = row
    output = []
    for key, beams in sorted(groups.items()):
        if set(beams) != {low_beam, high_beam}:
            raise ValueError('Missing paired observation')
        low, high = beams[low_beam], beams[high_beam]
        if low['input_sha256'] != high['input_sha256']:
            raise ValueError('Paired inputs differ')
        result = dict(zip(('kind', 'length', 'sequence_seed', 'search_seed'), key))
        result.update(input_sha256=low['input_sha256'], low_beam=low_beam,
                      high_beam=high_beam, low_status=low['status'], high_status=high['status'])
        for output_key, measurement in [('input_pair_f1_change', 'input_pair_f1'),
                                        ('vienna_delta_difference_kcal_mol', 'vienna_delta_kcal_mol')]:
            a, b = low.get(measurement), high.get(measurement)
            result[output_key] = b-a if a is not None and b is not None else None
        a, b = low.get('input_lf_wall_seconds'), high.get('input_lf_wall_seconds')
        result['input_lf_time_ratio'] = b/a if a is not None and a > 0 and b is not None else None
        output.append(result)
    return output
