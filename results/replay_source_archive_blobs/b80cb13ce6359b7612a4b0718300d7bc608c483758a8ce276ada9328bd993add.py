"""Validate explicit family-separated plans with sequence-bound provenance."""
import json
from pathlib import Path

from .experimental_data import sequence_similarity
from .reference import digest, text_field, validate_inputs


def plan_families(references, assignments, plan, exposed):
    validate_inputs(references, {'schema_version': 1, 'methods': ['validation-only'], 'records': []})
    if not isinstance(assignments, dict) or type(assignments.get('schema_version')) is not int or assignments['schema_version'] != 1 or not isinstance(assignments.get('records'), list):
        raise ValueError('Family assignments require schema_version=1 and records')
    if not isinstance(plan, dict) or set(plan) != {'train', 'validation', 'test'}:
        raise ValueError('Plan requires explicit train/validation/test family lists')
    family_split = {}
    for split, families in plan.items():
        if not isinstance(families, list) or not families:
            raise ValueError('Every split requires at least one family')
        for family in families:
            text_field(family, 'family_id')
            if family in family_split:
                raise ValueError('A family appears in multiple plan entries')
            family_split[family] = split
    index = {}
    refs = {r['id']: r for r in references['records']}
    for item in assignments['records']:
        if not isinstance(item, dict):
            raise ValueError('Family assignments must be objects')
        identity = item.get('id')
        if not isinstance(identity, str) or identity not in refs or identity in index:
            raise ValueError('Duplicate or unknown family assignment id')
        if item.get('sequence_sha256') != digest(refs[identity]['sequence'].encode()):
            raise ValueError('Family assignment sequence hash differs')
        family = text_field(item.get('family_id'), 'family_id')
        text_field(item.get('source'), 'family assignment source')
        if family not in family_split:
            raise ValueError('Assigned family is outside the plan')
        index[identity] = item
    if set(index) != set(refs):
        raise ValueError('Every reference requires an explicit sequence-bound family assignment')
    if set(family_split) != {r['family_id'] for r in index.values()}:
        raise ValueError('Every planned family requires records')
    if not isinstance(exposed, list):
        raise ValueError('Exposure ledger must be a list')
    for record in exposed:
        if not isinstance(record, dict) or not isinstance(record.get('sequence'), str) or not record.get('source'):
            raise ValueError('Exposure records require sequence and source')
        from .sequences import validate_sequence
        validate_sequence(record['sequence'])
        text_field(record['source'], 'exposure source')
        for field in ('family_id', 'pdb_accession'):
            if field in record: text_field(record[field], 'exposure '+field)
    splits = {s: [] for s in plan}
    for identity, reference in refs.items():
        if 'pdb_accession' in reference: text_field(reference['pdb_accession'], 'reference pdb_accession')
        item = index[identity]
        split = family_split[item['family_id']]
        splits[split].append({**reference, 'family_id': item['family_id'], 'family_source': item['source']})
    def overlaps(first, second):
        return (first.get('family_id') and first.get('family_id') == second.get('family_id')
                or first.get('pdb_accession') and first['pdb_accession'].casefold() == second.get('pdb_accession', '').casefold()
                or first['sequence'] == second['sequence']
                or sequence_similarity(first['sequence'], second['sequence']) >= .8)
    for split, records in splits.items():
        for record in records:
            for other_split, others in splits.items():
                if split != other_split and any(overlaps(record, other) for other in others):
                    raise ValueError('Accession or sequence overlap crosses planned family splits')
            if split == 'test' and any(overlaps(record, old) for old in exposed):
                raise ValueError('Proposed test overlaps previously exposed data')
    return {'complete': True, 'dataset_id': references['dataset_id'], 'splits': splits,
            'counts': {s: len(rs) for s, rs in splits.items()}, 'families': plan,
            'exposure_records_checked': len(exposed),
            'interpretation': 'Family IDs/sources are caller-supplied evidence; broad RNA types are not inferred as families. Sequence overlap uses a fixed symmetric SequenceMatcher 0.8 heuristic.'}


def save_family_plan(run, references_path, assignments_path, plan_path, exposure_path, known_exposure=None):
    paths = [Path(p) for p in (references_path, assignments_path, plan_path, exposure_path)]
    contents = [p.read_bytes() for p in paths]
    inputs = [json.loads(c) for c in contents]
    if not isinstance(inputs[3], list):
        raise ValueError('Exposure ledger must be a list')
    inputs[3] = inputs[3] + (known_exposure or [])
    result = plan_families(*inputs)
    run = Path(run)
    run.mkdir(parents=True, exist_ok=False)
    for name, content in zip(('references.json', 'assignments.json', 'plan.json', 'exposure.json'), contents):
        (run/name).write_bytes(content)
    (run/'effective_exposure.json').write_text(json.dumps(inputs[3], indent=2)+'\n')
    result['effective_exposure_sha256'] = digest((run/'effective_exposure.json').read_bytes())
    result['sources'] = {str(p.resolve()): digest(c) for p, c in zip(paths, contents)}
    result['snapshot_sha256'] = {name: digest(content) for name, content in
        zip(('references.json', 'assignments.json', 'plan.json', 'exposure.json'), contents)}
    (run/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def audit_family_plan(run):
    run = Path(run)
    result = json.loads((run/'summary.json').read_text())
    for name, expected in result['snapshot_sha256'].items():
        if name not in ('references.json', 'assignments.json', 'plan.json', 'exposure.json') or digest((run/name).read_bytes()) != expected:
            raise ValueError('Frozen family input snapshot changed')
    if set(result['snapshot_sha256']) != {'references.json', 'assignments.json', 'plan.json', 'exposure.json'}:
        raise ValueError('Incomplete frozen family input snapshots')
    exposure = run/'effective_exposure.json'
    if digest(exposure.read_bytes()) != result['effective_exposure_sha256']:
        raise ValueError('Effective exposure ledger changed')
    expected = plan_families(*[json.loads((run/name).read_text()) for name in
        ('references.json', 'assignments.json', 'plan.json', 'effective_exposure.json')])
    for key, value in expected.items():
        if result.get(key) != value:
            raise ValueError('Frozen family plan differs from inputs')
    return result
