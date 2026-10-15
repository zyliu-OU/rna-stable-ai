"""Deterministic synthetic controls; designed stems are not verified folds."""
import hashlib
import random
from pathlib import Path

LENGTHS = (1000, 2000, 5000, 10000)

def validate_sequence(sequence, expected_length=None):
    if not isinstance(sequence, str) or not sequence or set(sequence) - set('ACGU'):
        raise ValueError('RNA must be a nonempty uppercase A/C/G/U string')
    if expected_length is not None and len(sequence) != expected_length:
        raise ValueError(f'Expected {expected_length} nt, got {len(sequence)}')
    return sequence

def generate_sequence(length, kind='mixed', seed=1729):
    if not isinstance(length, int) or isinstance(length, bool) or length < 1:
        raise ValueError('length must be a positive integer')
    if kind not in ('mixed', 'structured'):
        raise ValueError('kind must be mixed or structured')
    rng = random.Random(f'RNA-StableAI-v1:{seed}:{length}:{kind}')
    if kind == 'mixed':
        # Alternating 250-nt regions: GC rich, AU rich, balanced.
        weights = [(1, 4, 4, 1), (4, 1, 1, 4), (1, 1, 1, 1)]
        sequence = ''.join(rng.choices('ACGU', weights=weights[(i // 250) % 3], k=1)[0]
                           for i in range(length))
    else:
        pieces = []
        total = 0
        complement = str.maketrans('ACGU', 'UGCA')
        while total < length:
            stem = ''.join(rng.choices('ACGU', k=24))
            unit = stem + 'GAAA' + stem.translate(complement)[::-1] + ''.join(rng.choices('ACGU', k=12))
            pieces.append(unit)
            total += len(unit)
        sequence = ''.join(pieces)[:length]
    return validate_sequence(sequence, length)

def write_fasta(path, name, sequence):
    validate_sequence(sequence)
    if not name or '\n' in name or '\r' in name:
        raise ValueError('Invalid FASTA identifier')
    text = '>' + name + '\n' + '\n'.join(sequence[i:i+80] for i in range(0, len(sequence), 80)) + '\n'
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text() != text:
            raise FileExistsError(f'Preserving existing FASTA: {path}')
    else:
        path.write_text(text)
    return path

def read_fasta(path):
    records = []
    name, chunks = None, []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        if line.startswith('>'):
            if name is not None:
                records.append((name, validate_sequence(''.join(chunks))))
            name, chunks = line[1:], []
            if not name:
                raise ValueError('Empty FASTA identifier')
        elif name is None:
            raise ValueError('Sequence before FASTA header')
        else:
            chunks.append(line.strip())
    if name is not None:
        records.append((name, validate_sequence(''.join(chunks))))
    if not records:
        raise ValueError('Empty FASTA')
    return records

def generate_dataset(directory, config):
    manifest = []
    for length in config['lengths']:
        for kind in config['kinds']:
            name = f'{kind}_{length}_seed{config["seed"]}'
            seq = generate_sequence(length, kind, config['seed'])
            path = write_fasta(Path(directory) / f'{name}.fasta', name, seq)
            manifest.append({'id': name, 'kind': kind, 'length': length, 'seed': config['seed'],
                             'sha256': hashlib.sha256(seq.encode()).hexdigest(), 'path': str(path)})
    return manifest
