import json
from pathlib import Path
import pytest
from rnastable.batch_audit import concurrency_evidence,event_peak


def trace():
    return [{'event':'started','component':'a'}, {'event':'started','component':'b'},
            {'event':'finished','component':'a','returncode':0},
            {'event':'finished','component':'b','returncode':0},{'event':'complete'}]


def test_complete_native_trace_and_exceeded_limit():
    assert event_peak(trace(),{'a','b'},2)==2
    with pytest.raises(ValueError,match='exceeds'):event_peak(trace(),{'a','b'},1)


@pytest.mark.parametrize('events',[trace()[:-1],trace()[:1]+trace()[:1],
    [{'event':'finished','component':'a','returncode':0}],
    trace()[:-2]+[{'event':'finished','component':'b','returncode':7},{'event':'complete'}]])
def test_incomplete_duplicate_or_failed_trace_rejected(events):
    with pytest.raises(ValueError):event_peak(events,{'a','b'},2)


def legacy(tmp_path):
    tasks=[]
    for name,start,end in [('a','00:00:00','00:00:02'),('b','00:00:01','00:00:03')]:
        root=tmp_path/name;(root/'reports').mkdir(parents=True)
        record={'command':['rnastable','evaluate','--output-root',str(root)],'returncode':0,
                'started_utc':f'2026-10-05T{start}+00:00','utc':f'2026-10-05T{end}+00:00'}
        (root/'reports/commands.jsonl').write_text(json.dumps(record)+'\n')
        tasks.append({'id':name,'root':str(root)})
    return {'components':tasks,'execution':{'max_cpu_jobs':2}}


def test_direct_legacy_run_uses_existing_component_intervals(tmp_path):
    manifest=legacy(tmp_path)
    peak,source=concurrency_evidence(tmp_path,manifest,{},tmp_path/'missing-outer-log')
    assert peak==2 and 'parent startup/teardown concurrency unavailable' in source
    manifest['execution']['max_cpu_jobs']=1
    with pytest.raises(ValueError,match='intervals exceed'):
        concurrency_evidence(tmp_path,manifest,{},tmp_path/'missing-outer-log')


def test_native_run_needs_no_outer_log_and_incomplete_native_does_not_fallback(tmp_path):
    manifest=legacy(tmp_path)
    path=tmp_path/'driver_events/attempt/events.jsonl';path.parent.mkdir(parents=True)
    path.write_text('\n'.join(json.dumps(e) for e in trace())+'\n')
    assert concurrency_evidence(tmp_path,manifest,{'event_log':str(path)},tmp_path/'missing')[1]=='native driver events'
    path.write_text('\n'.join(json.dumps(e) for e in trace()[:-1])+'\n')
    with pytest.raises(ValueError,match='completion event'):
        concurrency_evidence(tmp_path,manifest,{'event_log':str(path)},tmp_path/'missing')
