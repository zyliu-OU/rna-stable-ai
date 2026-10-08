"""Import PDB-derived S-Processed BPSEQ annotations without changing pairs."""
from difflib import SequenceMatcher
import json
import math
from pathlib import Path
import re
import zipfile

from .reference import digest
from .scoring import base_pairs
from .sequences import validate_sequence


def load_pilot_config(path):
    config = json.loads(Path(path).read_text())
    for key, upper in [('min_length', 256), ('max_length', 256), ('epochs', 100),
                       ('embedding_dim', 128), ('channels', 128), ('cpu_threads', 2), ('beam_size', 1000)]:
        value = config.get(key)
        if type(value) is not int or not 1 <= value <= upper:
            raise ValueError(f'{key} must be an integer in 1..{upper}')
    if config['min_length'] > config['max_length']:
        raise ValueError('min_length exceeds max_length')
    if type(config.get('seed')) is not int or not 0 <= config['seed'] < 2**32:
        raise ValueError('seed must be a nonnegative 32-bit integer')
    for key, upper in [('learning_rate', 1), ('similarity_threshold', 1), ('timeout_seconds', 120), ('memory_limit_gib', 8)]:
        value = config.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= upper:
            raise ValueError(f'{key} must be finite in (0, {upper}]')
    if config.get('temperature_c') != 37:
        raise ValueError('Pilot requires temperature_c=37')
    return config


def parse_bpseq(content):
    rows = [line.split() for line in content.splitlines() if line.strip() and not line.startswith('#')]
    if not rows or any(len(row) != 3 for row in rows):
        raise ValueError('Expected complete three-column BPSEQ')
    sequence = validate_sequence(''.join(row[1] for row in rows))
    try:
        indices = [int(row[0]) for row in rows]
        partners = [int(row[2]) for row in rows]
    except ValueError as exc:
        raise ValueError('BPSEQ indices must be integers') from exc
    if indices != list(range(1, len(rows)+1)):
        raise ValueError('BPSEQ indices must be contiguous and one-based')
    pairs = set()
    chars = ['.'] * len(rows)
    for i, partner in enumerate(partners, 1):
        if partner == 0:
            continue
        if not 1 <= partner <= len(rows) or partner == i or partners[partner-1] != i:
            raise ValueError('BPSEQ partners must be reciprocal, in range and nonself')
        if i < partner:
            pairs.add((i-1, partner-1))
            chars[i-1], chars[partner-1] = '(', ')'
    structure = ''.join(chars)
    if base_pairs(structure) != pairs:
        raise ValueError('Crossing pairs are unsupported; no pseudoknot projection permitted')
    return sequence, structure


def sequence_similarity(first, second):
    # Symmetrize the heuristic; no claim that this is an alignment identity metric.
    return max(SequenceMatcher(None, first, second, autojunk=False).ratio(),
               SequenceMatcher(None, second, first, autojunk=False).ratio())


def conflicts(first, second, threshold):
    return (first['pdb_accession'] == second['pdb_accession']
            or first['sequence'] == second['sequence']
            or sequence_similarity(first['sequence'], second['sequence']) >= threshold)


def filter_splits(candidates, threshold):
    """Retain upstream splits with test > validation > training conflict priority."""
    kept, rejected, occupied = {}, [], []
    for split in ('test', 'validation', 'train'):
        records = []
        for record in sorted(candidates[split], key=lambda r: r['id']):
            collision = next((r for r in occupied if conflicts(record, r, threshold)), None)
            if collision:
                rejected.append({'id': record['id'], 'split': split, 'reason': 'accession_or_sequence_overlap',
                                 'retained_id': collision['id']})
            else:
                records.append(record)
                occupied.append(record)
        kept[split] = records
    return kept, rejected


def load_pdb_splits(eterna_root, config):
    eterna_root = Path(eterna_root).resolve()
    source_files = {}
    candidates = {s: [] for s in ('train', 'validation', 'test')}
    rejected = []
    paths = {'train': ('train', 'train_datasets/S-Processed-TRA.fasta'),
             'validation': ('holdout', 'holdout_datasets/S-Processed-VAL.fasta'),
             'test': ('test', 'test_datasets/S-Processed-TES.fasta')}
    archive_path = eterna_root/'input_data.zip'
    source_files[str(archive_path)] = digest(archive_path.read_bytes())
    with zipfile.ZipFile(archive_path) as archive:
        for split, (upstream, fasta_name) in paths.items():
            fasta = eterna_root/'datasets_in_fasta_form'/fasta_name
            source_files[str(fasta)] = digest(fasta.read_bytes())
            metadata = {}
            header, chunks = None, []
            def record_header():
                if header and 'EXT_SOURCE=RCSB Protein Data Bank;' in header:
                    fields = dict(part.strip().split('=', 1) for part in header.lstrip('> ').split(';'))
                    metadata[(fields['SSTRAND_ID'], ''.join(chunks))] = fields
            for line in [*fasta.read_text().splitlines(), '>end']:
                if line.startswith('>'):
                    record_header()
                    header, chunks = line, []
                else:
                    chunks.append(line.strip())
            prefix = f'input_data/StructureData/{upstream}/PDB_'
            for name in sorted(n for n in archive.namelist() if n.startswith(prefix) and n.endswith('.bpseq')):
                identity = Path(name).stem
                try:
                    data = archive.read(name)
                    sequence, structure = parse_bpseq(data.decode())
                    strand_id = re.search(r'PDB_\d+', identity).group()
                    fields = metadata.get((strand_id, sequence))
                    if fields is None:
                        raise ValueError('No exact matching PDB-source FASTA metadata')
                    if not config['min_length'] <= len(sequence) <= config['max_length']:
                        raise ValueError('Outside prespecified pilot length range')
                    candidates[split].append({
                        'id': split+'_'+identity, 'sequence': sequence, 'structure': structure,
                        'reference_kind': 'experimental', 'source': 'PDB-derived RNA STRAND annotation processed by EternaFold; '+fields['EXT_ID'],
                        'pdb_accession': fields['EXT_ID'].lower(), 'rna_strand_id': strand_id,
                        'rna_type': fields['TYPE'], 'organism': fields['ORGANISM'],
                        'upstream_split': upstream, 'bpseq_member': name, 'bpseq_sha256': digest(data),
                        'source_url': 'https://www.rcsb.org/structure/'+fields['EXT_ID'],
                        'conditions': 'Upstream processed PDB annotation; record-specific experimental conditions not inferred.',
                    })
                except ValueError as exc:
                    rejected.append({'id': split+'_'+identity, 'split': split, 'reason': str(exc)})
    kept, overlap = filter_splits(candidates, config['similarity_threshold'])
    rejected += overlap
    if any(not records for records in kept.values()):
        raise ValueError('Filtering left an empty train/validation/test split')
    return kept, {'source_sha256': source_files, 'rejected': rejected,
                  'candidate_counts': {s: len(r) for s, r in candidates.items()},
                  'retained_counts': {s: len(r) for s, r in kept.items()},
                  'policy': 'upstream_splits_test_priority_one_accession_and_symmetric_sequencematcher_filter_v1',
                  'similarity_threshold': config['similarity_threshold'],
                  'interpretation': 'Processed PDB-derived annotations, not raw experimental pair measurements; sequence heuristic does not establish RNA-family independence.'}


def write_splits(run, splits):
    records = {}
    for split, data in splits.items():
        path = Path(run)/(split+'_references.json')
        path.write_text(json.dumps({'schema_version': 1, 'dataset_id': 'pdb_processed_pilot_'+split,
                                    'records': data}, indent=2)+'\n')
        records[split] = {'path': str(path.resolve()), 'sha256': digest(path.read_bytes()), 'count': len(data)}
    return records
