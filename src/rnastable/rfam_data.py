"""Bind legacy Rfam accessions to exact processed RNA STRAND sequences and pairs."""
import json
from pathlib import Path
import re
import zipfile

from .experimental_data import parse_bpseq, sequence_similarity
from .reference import digest


def load_rfam_candidates(eterna_root, config):
    root = Path(eterna_root).resolve()
    metadata, sources = {}, {}
    files = [('train', 'train_datasets/S-Processed-TRA.fasta'),
             ('holdout', 'holdout_datasets/S-Processed-VAL.fasta'),
             ('test', 'test_datasets/S-Processed-TES.fasta')]
    for split, name in files:
        path = root/'datasets_in_fasta_form'/name; content = path.read_bytes()
        sources[str(path)] = digest(content)
        header, sequence = None, []
        def store():
            if header and 'EXT_SOURCE=Rfam Database;' in header:
                fields = dict(part.strip().split('=', 1) for part in header.lstrip('> ').split(';'))
                family = fields['EXT_ID'].split()[0]
                if not re.fullmatch(r'RF\d{5}', family): raise ValueError('Malformed upstream Rfam accession')
                key = (split, fields['SSTRAND_ID'], ''.join(sequence))
                if key in metadata and metadata[key] != fields: raise ValueError('Ambiguous Rfam metadata binding')
                metadata[key] = fields
        for line in [*content.decode().splitlines(), '>end']:
            if line.startswith('>'): store(); header, sequence = line, []
            else: sequence.append(line.strip())
    archive_path = root/'input_data.zip'; sources[str(archive_path)] = digest(archive_path.read_bytes())
    records, exclusions = [], []
    with zipfile.ZipFile(archive_path) as archive:
        for name in sorted(archive.namelist()):
            if not re.fullmatch(r'input_data/StructureData/(train|holdout|test)/RFA_[^/]+\.bpseq', name): continue
            identity = name.replace('/', '_').removesuffix('.bpseq')
            try:
                content = archive.read(name); sequence, structure = parse_bpseq(content.decode())
                strand_id = re.search(r'RFA_\d+', Path(name).stem).group()
                split = name.split('/')[2]
                fields = metadata.get((split, strand_id, sequence))
                if fields is None: raise ValueError('No exact Rfam-source metadata match')
                family = fields['EXT_ID'].split()[0]
                if not config['min_length'] <= len(sequence) <= config['max_length']: raise ValueError('Outside fixed length range')
                if family not in {f for fs in config['families'].values() for f in fs}: raise ValueError('Family not in fixed plan')
                records.append({'id': identity, 'sequence': sequence, 'structure': structure,
                    'reference_kind': 'computational', 'source': 'Processed comparative RNA STRAND Rfam annotation; '+fields['EXT_ID'],
                    'family_id': family, 'family_source': 'Exact legacy RNA STRAND/EternaFold FASTA EXT_ID; https://rfam.org/family/'+family,
                    'external_id': fields['EXT_ID'], 'rna_strand_id': strand_id, 'upstream_split': split,
                    'organism': fields['ORGANISM'], 'bpseq_member': name, 'bpseq_sha256': digest(content),
                    'conditions': 'Legacy processed comparative annotation; no assay conditions or direct pair measurement inferred.'})
            except ValueError as exc: exclusions.append({'id': identity, 'reason': str(exc)})
    return records, {'source_sha256': sources, 'exclusions': exclusions,
                     'interpretation': 'Historical family IDs bound to upstream metadata; processed comparative references, not new experimental measurements.'}


def select_cohort(records, config, exposed):
    retained, excluded = [], []
    family_order = [f for split in ('test', 'validation', 'train') for f in config['families'][split]]
    for family in family_order:
        group = []
        for record in sorted((r for r in records if r['family_id'] == family), key=lambda r: r['id']):
            if any(record['sequence'] == old['sequence'] or sequence_similarity(record['sequence'], old['sequence']) >= .8 for old in exposed):
                excluded.append({'id': record['id'], 'reason': 'prior_sequence_exposure'}); continue
            if any(record['sequence'] == old['sequence'] or sequence_similarity(record['sequence'], old['sequence']) >= .8 for old in retained+group):
                excluded.append({'id': record['id'], 'reason': 'sequence_redundancy'}); continue
            if len(group) >= config['max_records_per_family']:
                excluded.append({'id': record['id'], 'reason': 'fixed_family_cap'}); continue
            group.append(record)
        if not group: raise ValueError('Filtering left an empty planned family: '+family)
        retained.extend(group)
    return retained, excluded


def cohort_inputs(records, config):
    references = {'schema_version': 1, 'dataset_id': 'legacy_rfam_family_disjoint_trial', 'records': records}
    assignments = {'schema_version': 1, 'records': [{'id': r['id'], 'sequence_sha256': digest(r['sequence'].encode()),
        'family_id': r['family_id'], 'source': r['family_source']} for r in records]}
    return references, assignments, config['families']
