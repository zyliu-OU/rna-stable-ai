"""Count only current live checkpoints, excluding preserved checkpoint archives."""
import json
from pathlib import Path


def count_saved_searches(tasks):
    total=0
    for task in tasks:
        manifests=sorted((Path(task['root'])/'results/equal_budget_runs').glob('*/manifest.json'))
        if not manifests:
            continue
        run=manifests[-1].parent
        for arm in ('long','restarts'):
            checkpoints=sorted((run/arm/'results/sweep_runs').glob('*/checkpoint.json'))
            if not checkpoints:
                continue
            try:
                record=json.loads(checkpoints[-1].read_text())
                rows=record['rows']
                if not isinstance(rows,list) or record['completed_jobs']!=len(rows):
                    continue
                total+=len(rows)
            except (OSError,ValueError,KeyError):
                # A child can be writing a checkpoint during this heartbeat.
                continue
    return total
