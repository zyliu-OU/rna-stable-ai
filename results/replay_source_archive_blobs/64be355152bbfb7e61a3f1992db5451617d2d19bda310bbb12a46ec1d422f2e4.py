"""Audit native driver events, with explicit evidence fallbacks for older runs."""
from datetime import datetime
import json
from pathlib import Path


def event_peak(events, names, limit):
    active=set();started=set();peak=0;complete=False
    for event in events:
        kind=event['event'];name=event.get('component')
        if complete:
            raise ValueError('Events follow a completed driver attempt')
        if kind=='started':
            if name not in names or name in started:
                raise ValueError('Unexpected or duplicate component start')
            active.add(name);started.add(name);peak=max(peak,len(active))
            if peak>limit:raise ValueError('Recorded concurrency exceeds the worker limit')
        elif kind=='finished':
            if name not in active or event.get('returncode')!=0:
                raise ValueError('Unmatched or unsuccessful component completion')
            active.remove(name)
        elif kind=='complete':
            if active or started!=set(names):raise ValueError('Incomplete driver event coverage')
            complete=True
        elif kind!='heartbeat':raise ValueError('Unexpected driver event')
    if not complete:raise ValueError('Driver attempt has no completion event')
    return peak


def concurrency_evidence(run, manifest, status, command_log):
    names={t['id'] for t in manifest['components']};limit=manifest['execution']['max_cpu_jobs']
    if status.get('event_log'):
        path=Path(status['event_log']).resolve()
        if not path.is_relative_to(run.resolve()/'driver_events'):
            raise ValueError('Driver event log is outside its run directory')
        events=[json.loads(line) for line in path.read_text().splitlines()]
        return event_peak(events,names,limit),'native driver events'
    marker=f'CPU batch study: {run}\n'
    logs=[json.loads(line) for line in command_log.read_text().splitlines()] if command_log.exists() else []
    entries=[e for e in logs if marker in e.get('output','') and e.get('returncode')==0]
    if entries:
        events=[]
        for line in entries[-1]['output'].splitlines():
            for kind in ('started','finished'):
                prefix=f'CPU batches: {kind} '
                if line.startswith(prefix):
                    events.append({'event':kind,'component':line.removeprefix(prefix).split(';')[0],
                                   'returncode':0})
        events.append({'event':'complete'})
        return event_peak(events,names,limit),'saved outer command output'
    # Legacy direct invocations still have durable per-component command logs.
    # These cover CLI execution intervals, not unrecorded parent startup/teardown.
    boundaries=[]
    for task in manifest['components']:
        path=Path(task['root'])/'reports/commands.jsonl'
        if not path.exists():raise ValueError(f'Missing component command log: {path}')
        entries=[json.loads(line) for line in path.read_text().splitlines()]
        matches=[e for e in entries if e.get('returncode')==0 and
                 '--output-root' in e.get('command',[]) and
                 e['command'][e['command'].index('--output-root')+1]==task['root']]
        if not matches:raise ValueError(f'No successful component command: {task["id"]}')
        record=matches[-1]
        if not record.get('started_utc'):raise ValueError('Component command lacks a start timestamp')
        start,end=datetime.fromisoformat(record['started_utc']),datetime.fromisoformat(record['utc'])
        if start.tzinfo is None or end.tzinfo is None or end<start:
            raise ValueError('Invalid component command interval')
        boundaries.extend([(start,1),(end,-1)])
    active=peak=0
    for _,change in sorted(boundaries):
        active+=change;peak=max(peak,active)
        if active<0 or peak>limit:raise ValueError('Component intervals exceed the recorded worker limit')
    if active:raise ValueError('Unclosed component command intervals')
    return peak,'legacy component CLI intervals; parent startup/teardown concurrency unavailable'
