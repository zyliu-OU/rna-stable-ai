"""Durable exposure events, including test starts before inference can reveal results."""
import json
from pathlib import Path

from .artifacts import timestamp
from .reference import digest, text_field
from .sequences import validate_sequence


def exposure_records(records, source):
    text_field(source, 'exposure source')
    output = []
    for record in records:
        row = {'sequence': validate_sequence(record['sequence']), 'source': source}
        for key in ('family_id', 'pdb_accession'):
            if key in record: row[key] = text_field(record[key], key)
        output.append(row)
    return output


def record_exposure(run, stage, records):
    if stage not in ('training_started', 'validation_started', 'test_started'):
        raise ValueError('Unsupported exposure stage')
    run = Path(run).resolve()
    rows = exposure_records(records, str(run)+' '+stage)
    path = run/'exposures'/(timestamp()+'.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(rows, sort_keys=True).encode()
    record = {'schema_version': 1, 'run_dir': str(run), 'stage': stage,
              'records': rows, 'records_sha256': digest(content)}
    with path.open('x') as stream:
        json.dump(record, stream, indent=2); stream.write('\n')
        import os
        stream.flush(); os.fsync(stream.fileno())
    # Persist directory entries as well as file contents before returning to inference.
    for directory in (path.parent,run,run.parent):
        descriptor=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    return {'path': str(path), 'sha256': digest(path.read_bytes()), 'stage': stage}


def read_exposure(path):
    path = Path(path)
    data = json.loads(path.read_text())
    if type(data.get('schema_version')) is not int or data['schema_version'] != 1 or data.get('stage') not in ('training_started', 'validation_started', 'test_started'):
        raise ValueError('Invalid exposure event schema/stage')
    if Path(data['run_dir']).resolve() != path.resolve().parents[1]:
        raise ValueError('Exposure event belongs to a different run')
    if digest(json.dumps(data['records'], sort_keys=True).encode()) != data['records_sha256']:
        raise ValueError('Exposure event records changed')
    for row in data['records']:
        validate_sequence(row['sequence']); text_field(row.get('source'), 'exposure source')
        for key in ('family_id', 'pdb_accession'):
            if key in row: text_field(row[key], key)
    return data


def collect_known_exposures(root):
    root = Path(root)
    rows = []
    # Historical runs predate events. Snapshot presence is conservatively treated as exposure.
    snapshots = list((root/'results/experimental_pilot_runs').glob('*/*_references.json'))
    for name in ('train.json', 'validation.json'):
        snapshots.extend((root/'results/pair_development_runs').glob('*/'+name))
    for path in sorted(snapshots):
        rows.extend(exposure_records(json.loads(path.read_text())['records'], str(path)))
    for path in sorted((root/'results').rglob('exposures/*.json')):
        rows.extend(read_exposure(path)['records'])
    unique = {}
    for row in rows:
        key = (row['sequence'], row.get('family_id'), row.get('pdb_accession'))
        unique.setdefault(key, row)
    return list(unique.values())
