#!/usr/bin/env python3
"""Longer native validation budget, separate from the frozen proposal replication."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rnastable.reference_extension import NAME,prepare,execute,audit
from run_checkpoint_prior_replication import audit as audit_replication


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--resume',type=Path);parser.add_argument('--verify',action='store_true');parser.add_argument('--config',type=Path,default=ROOT/'configs/checkpoint_prior_reference_extension.json');args=parser.parse_args()
    if args.verify:return audit(ROOT,ROOT/'results'/f'{NAME}_summary.json')
    if args.resume:run=args.resume.resolve()
    else:
        source=ROOT/'results/checkpoint_prior_replication_summary.json';audit_replication(source)
        paths=[Path(__file__),*[ROOT/'src/rnastable'/name for name in ('reference_extension.py','native_journal.py','folding.py','process_guard.py','vienna_worker.py','pooled_native.py','selection.py','optimization.py','reference.py','reference_audit.py','exposures.py','scoring.py','sequences.py','artifacts.py')]]
        run=prepare(ROOT,source,json.loads(args.config.read_text()),paths)
    print(f'Extended reference run: {run}',flush=True);summary=execute(ROOT,run)
    if summary is not None:print(json.dumps(summary,indent=2))
    else:print('Reference extension deferred at deadline; retained journal can be resumed under its bound plan.')
    return summary

if __name__=='__main__':main()
