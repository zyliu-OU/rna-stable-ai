"""Describe search variability within each input before summarizing across inputs."""
from collections import defaultdict
import math
import statistics


INPUT_FIELDS = ['kind', 'length', 'beam_size', 'sequence_seed', 'input_sha256',
                'search_runs', 'validated_candidates', 'failed_candidates', 'selected_finalists',
                'returned_inputs', 'selection_missing_runs', 'known_selected_energies', 'distinct_selected_sequences',
                'mean_selected_delta_kcal_mol', 'sd_selected_delta_kcal_mol',
                'min_selected_delta_kcal_mol', 'max_selected_delta_kcal_mol',
                'mean_candidate_delta_kcal_mol', 'candidate_worsenings']
GROUP_FIELDS = ['kind', 'length', 'beam_size', 'input_count', 'search_runs',
                'validated_candidates', 'failed_candidates', 'selected_finalists', 'returned_inputs', 'selection_missing_runs',
                'inputs_with_measured_selection', 'mean_input_mean_selected_delta_kcal_mol',
                'sd_input_mean_selected_delta_kcal_mol']


def search_variability(rows):
    groups = defaultdict(list)
    seen = set()
    for row in rows:
        key = tuple(row[k] for k in ('kind', 'length', 'beam_size', 'sequence_seed'))
        identity = key+(row['search_seed'],)
        if identity in seen:
            raise ValueError('Duplicate search observation')
        seen.add(identity)
        groups[key].append(row)
    inputs = []
    for key, group in sorted(groups.items()):
        hashes = {r['input_sha256'] for r in group}
        if len(hashes) != 1:
            raise ValueError('Repeated searches must share an exact input')
        selected = []
        candidates = []
        for row in group:
            value = row.get('selected_vienna_delta_kcal_mol')
            if value is not None:
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value > 1e-9:
                    raise ValueError('Invalid selected energy change')
                selected.append(value)
            if row['status']=='validated':
                value = row['vienna_delta_kcal_mol']
                if not math.isfinite(value):
                    raise ValueError('Nonfinite validated candidate energy change')
                candidates.append(value)
        result = dict(zip(('kind','length','beam_size','sequence_seed'),key))
        result.update(input_sha256=next(iter(hashes)), search_runs=len(group),
                      validated_candidates=len(candidates), failed_candidates=len(group)-len(candidates),
                      selected_finalists=sum(r.get('selection_source')=='finalist' for r in group),
                      returned_inputs=sum(r.get('selection_source')=='input' for r in group),
                      selection_missing_runs=sum(r.get('selection_source') not in ('input','finalist') for r in group),
                      known_selected_energies=len(selected),
                      distinct_selected_sequences=len({r['selected_sha256'] for r in group if r.get('selected_sha256')}),
                      mean_selected_delta_kcal_mol=statistics.mean(selected) if selected else None,
                      sd_selected_delta_kcal_mol=statistics.stdev(selected) if len(selected)>1 else None,
                      min_selected_delta_kcal_mol=min(selected) if selected else None,
                      max_selected_delta_kcal_mol=max(selected) if selected else None,
                      mean_candidate_delta_kcal_mol=statistics.mean(candidates) if candidates else None,
                      candidate_worsenings=sum(v>1e-9 for v in candidates))
        inputs.append(result)
    across = []
    for key in sorted({tuple(r[k] for k in ('kind','length','beam_size')) for r in inputs}):
        group = [r for r in inputs if tuple(r[k] for k in ('kind','length','beam_size'))==key]
        means = [r['mean_selected_delta_kcal_mol'] for r in group if r['mean_selected_delta_kcal_mol'] is not None]
        result = dict(zip(('kind','length','beam_size'),key))
        result.update(input_count=len(group), inputs_with_measured_selection=len(means),
                      mean_input_mean_selected_delta_kcal_mol=statistics.mean(means) if means else None,
                      sd_input_mean_selected_delta_kcal_mol=statistics.stdev(means) if len(means)>1 else None)
        for field in ('search_runs','validated_candidates','failed_candidates','selected_finalists','returned_inputs','selection_missing_runs'):
            result[field] = sum(r[field] for r in group)
        across.append(result)
    return inputs, across
