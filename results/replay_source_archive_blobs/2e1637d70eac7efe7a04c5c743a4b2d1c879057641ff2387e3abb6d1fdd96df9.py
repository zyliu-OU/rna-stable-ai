#!/usr/bin/env python3
"""Apply the current selection rule to saved sweep evidence; no new folds."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from rnastable.artifacts import publish, sha256, timestamp
from rnastable.optimization import check_constraints, hamming
from rnastable.selection import select_finalist
from rnastable.sequences import read_fasta, write_fasta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT/'results/evaluation_replication_summary.json')
    args = parser.parse_args()
    source = args.summary.resolve()
    subprocess.run([sys.executable, str(ROOT/'scripts/verify_sweep.py'), '--summary', str(source)], check=True)
    summary = json.loads(source.read_text())
    stamp = timestamp()
    run = ROOT/'results/selection_reviews'/stamp
    run.mkdir(parents=True)
    rows = []
    for row in summary['rows']:
        if not row.get('summary_path'):
            raise ValueError('Cannot review a run without saved sequence and validation evidence')
        path = Path(row['summary_path'])
        evidence = json.loads(path.read_text())
        original = read_fasta(path.parent/'input.fasta')[0][1]
        finalist = read_fasta(row['finalist_fasta'])[0][1]
        decision = select_finalist(original, finalist, evidence['search']['status'],
                                   evidence['reference'], evidence['validation'])
        selected = finalist if decision['source'] == 'finalist' else original
        check_constraints(selected, original, evidence['config'])
        output = write_fasta(run/(row['job_id']+'_selected.fasta'), row['job_id']+'_selected', selected)
        rows.append({'job_id': row['job_id'], 'source_status': row['status'],
                     'selection_source': decision['source'], 'selection_reason': decision['reason'],
                     'candidate_vienna_delta_kcal_mol': decision['candidate_vienna_delta_kcal_mol'],
                     'selected_vienna_delta_kcal_mol': decision['selected_vienna_delta_kcal_mol'],
                     'selected_fasta': str(output), 'selected_sha256': sha256(selected),
                     'selected_mutations_from_input': hamming(selected, original),
                     'source_evidence': str(path),
                     'source_evidence_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    result = {'utc': stamp, 'run_dir': str(run), 'source_summary': str(source),
              'source_summary_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'selection_code_sha256': hashlib.sha256((ROOT/'src/rnastable/selection.py').read_bytes()).hexdigest(),
              'mode': 'saved_evidence_review_no_new_folds', 'rows': rows,
              'selection_counts': dict(Counter(r['selection_source'] for r in rows)),
              'reason_counts': dict(Counter(r['selection_reason'] for r in rows))}
    (run/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Selection review of saved CPU folding evidence', '',
             f'Source: `{source}`; output: `{run}`.', '',
             'This review reuses previously audited input/finalist folds. No folding, benchmarking or training was rerun. Original sweep evidence remains unchanged.', '',
             f'Selected sources: {result["selection_counts"]}; reasons: {result["reason_counts"]}.', '',
             '| Job | Selected source | Reason | Candidate Vienna change | Selected Vienna change |',
             '|---|---|---|---:|---:|']
    for row in rows:
        lines.append('| '+' | '.join(str(row[k]) for k in ['job_id','selection_source','selection_reason',
                      'candidate_vienna_delta_kcal_mol','selected_vienna_delta_kcal_mol'])+' |')
    lines += ['', 'Only confirmed lower ViennaRNA energy selects a finalist. Otherwise the selected FASTA contains the input; its change is zero only if input reference energy is known. Rejected finalists remain in their source runs. This is computed energy, not experimental biological stability.', '']
    publish(ROOT, 'selection_review', result, rows, list(rows[0]), '\n'.join(lines))
    print(json.dumps({k:result[k] for k in ['run_dir','mode','selection_counts','reason_counts']}, indent=2))


if __name__ == '__main__':
    main()
