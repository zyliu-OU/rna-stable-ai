import json
from pathlib import Path
import subprocess
import sys
import pytest
from rnastable.sequences import generate_sequence, generate_dataset, validate_sequence, write_fasta, read_fasta
from rnastable.scoring import gc_fraction, mfe_per_nt, paired_fraction
from rnastable.folding import run_bounded, parse_output, benchmark_folding
from rnastable.cli import ROOT, load_config

@pytest.mark.parametrize('length', [1000, 2000, 5000, 10000])
@pytest.mark.parametrize('kind', ['structured', 'mixed'])
def test_generation(length, kind, tmp_path):
    seq = generate_sequence(length, kind, 1729)
    assert len(seq) == length and set(seq) <= set('ACGU')
    assert seq == generate_sequence(length, kind, 1729)
    assert seq != generate_sequence(length, kind, 1730)
    path = write_fasta(tmp_path/'control.fasta', 'control', seq)
    assert read_fasta(path) == [('control', seq)]
    assert max(map(len, path.read_text().splitlines()[1:])) <= 80

@pytest.mark.parametrize('value', ['', 'ACGT', 'acgu', 'ACGN', 'AC GU', None])
def test_validation(value):
    with pytest.raises(ValueError):
        validate_sequence(value)

def test_expected_length():
    with pytest.raises(ValueError):
        validate_sequence('ACGU', 5)

@pytest.mark.parametrize('length', [0, -1, 1.5, True])
def test_invalid_lengths(length):
    with pytest.raises(ValueError):
        generate_sequence(length)

def test_small_length():
    assert len(generate_sequence(1, 'structured')) == 1

def test_preserves_fasta(tmp_path):
    path = tmp_path/'existing.fasta'
    path.write_text('original data')
    with pytest.raises(FileExistsError):
        write_fasta(path, 'new', 'ACGU')
    assert path.read_text() == 'original data'

def test_scores():
    assert gc_fraction('GGCCAAUU') == 0.5
    assert mfe_per_nt(-8, 'ACGU') == -2
    assert paired_fraction('((..))', 6) == pytest.approx(2/3)
    assert paired_fraction('....') == 0

@pytest.mark.parametrize('structure', ['(()', ')(..', '..x.', ''])
def test_invalid_structure(structure):
    with pytest.raises(ValueError):
        paired_fraction(structure)

def test_nonfinite_score():
    with pytest.raises(ValueError):
        mfe_per_nt(float('nan'), 'ACGU')

def test_parsers():
    assert parse_output('ViennaRNA', 'ACGU\n.... ( -1.20)\n', 4)['mfe_kcal_mol'] == -1.2
    assert parse_output('LinearFold', '((..)) (-3.50)', 6)['paired_fraction'] == pytest.approx(2/3)
    ensemble = parse_output('LinearPartition', 'Free Energy of Ensemble: -1.41344 kcal/mol', 9)
    assert ensemble == {'ensemble_free_energy_kcal_mol': -1.41344}
    with pytest.raises(ValueError):
        parse_output('LinearFold', '.. (-2.0)', 5)

def test_timeout_and_failure():
    timeout = run_bounded([sys.executable, '-c', 'import time; time.sleep(5)'], 'ACGU', timeout=0.15)
    assert timeout['status'] == 'timeout'
    assert timeout['wall_seconds'] < 3
    failed = run_bounded([sys.executable, '-c', 'import sys; sys.stderr.write("exact failure"); sys.exit(7)'], 'ACGU')
    assert failed['status'] == 'error' and failed['returncode'] == 7
    assert 'exact failure' in failed['error']

def test_missing_tools_continue(tmp_path, monkeypatch):
    config = load_config(ROOT/'configs/benchmark.json')
    config.update(lengths=[1000], kinds=['mixed'])
    manifest = generate_dataset(tmp_path/'data', config)
    monkeypatch.setattr('rnastable.folding.tool_commands', lambda *_: {})
    rows = benchmark_folding(tmp_path, manifest, config, tmp_path/'raw')
    assert len(rows) == 3 and all(r['status'] == 'unavailable' for r in rows)
    assert all('wall_seconds' not in r for r in rows)

def test_cli_generation(tmp_path):
    result = subprocess.run([str(ROOT/'scripts/rnastable'), 'generate', '--output-root', str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    records = json.loads(result.stdout)
    assert len(records) == 8
    assert sorted({r['length'] for r in records}) == [1000, 2000, 5000, 10000]
    result = subprocess.run([str(ROOT/'scripts/rnastable'), '--version'], capture_output=True, text=True)
    assert result.returncode == 0 and '0.1.0' in result.stdout

def test_cli_bad_config(tmp_path):
    config = load_config(ROOT/'configs/benchmark.json')
    config['lengths'] = [0]
    path = tmp_path/'bad.json'; path.write_text(json.dumps(config))
    result = subprocess.run([str(ROOT/'scripts/rnastable'), 'generate', '--config', str(path)], capture_output=True, text=True)
    assert result.returncode == 2 and 'lengths' in result.stderr

def test_cli_benchmark_outputs_and_archive(tmp_path):
    # Current host has no folding tools. Fake external executables are not treated as measurements.
    config = load_config(ROOT/'configs/benchmark.json')
    config.update(lengths=[32], kinds=['mixed'], repeats=1, warmup=0, timeout_seconds=0.2)
    path = tmp_path/'config.json'; path.write_text(json.dumps(config))
    command = [str(ROOT/'scripts/rnastable'), 'benchmark', '--config', str(path), '--output-root', str(tmp_path)]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    original = (tmp_path/'results/benchmark_summary.json').read_text()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    archived = list((tmp_path/'results/runs').glob('*/benchmark_summary.json'))
    assert len(archived) == 1 and archived[0].read_text() == original
    for file in ('folding_benchmark.csv', 'gpu_benchmark.csv', 'benchmark_summary.json'):
        assert (tmp_path/'results'/file).exists()
    assert (tmp_path/'reports/benchmark_report.md').exists()

def test_successful_subprocess():
    result = run_bounded([sys.executable, '-c', 'import sys; print(sys.stdin.read().strip())'], 'ACGU')
    assert result['status'] == 'ok' and result['stdout'].strip() == 'ACGU'
    assert result['wall_seconds'] > 0
    if Path('/usr/bin/time').exists():
        assert result['peak_rss_mib'] > 0

def test_encoder_missing_dependency(monkeypatch):
    from rnastable.gpu import benchmark_gpu
    config = load_config(ROOT/'configs/benchmark.json')
    monkeypatch.setitem(sys.modules, 'torch', None)
    rows = benchmark_gpu(config)
    assert [r['length'] for r in rows] == [1000, 2000, 5000, 10000]
    assert all(r['status'] == 'skipped' for r in rows)
    assert all('gpu_seconds' not in r for r in rows)

def test_setup_failure_is_nonzero_and_continues_tools(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location('rnastable_setup', ROOT/'scripts/setup.py')
    setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup)
    monkeypatch.setattr(setup, 'ROOT', tmp_path)
    (tmp_path/'reports').mkdir()
    monkeypatch.setattr(setup.shutil, 'which', lambda name: '/test/uv' if name == 'uv' else None)
    attempted = []
    def fail(command, env=None):
        attempted.append(command)
        return subprocess.CompletedProcess(command, 1, stdout='Test-only simulated download failure')
    monkeypatch.setattr(setup, 'run', fail)
    assert setup.main() == 1
    clones = [command for command in attempted if command[:2] == ['git', 'clone']]
    assert len(clones) == 3
    status = json.loads((tmp_path/'reports/setup_status.json').read_text())
    assert status['status'] == 'incomplete'
    assert len(status['required_failures']) == 3
    assert len(status['optional_failures']) == 1
    assert not (tmp_path/'.venv').exists()
