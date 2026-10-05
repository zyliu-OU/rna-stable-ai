import sys
import pytest
from rnastable.batching import run_batches


def tasks(tmp_path,count):
    return [{'id':str(i),'log':str(tmp_path/f'job{i}.txt')} for i in range(count)]


def test_concurrency_is_bounded_and_failures_do_not_stop_other_batches(tmp_path):
    events=[];active=set();peak=0
    def progress(event,index,value,completed,total):
        nonlocal peak
        events.append((event,index,value))
        if event=='started':active.add(index);peak=max(peak,len(active))
        elif event=='finished':active.discard(index)
    def command(task):
        code=7 if task['id']=='1' else 0
        return [sys.executable,'-c',f'import time,sys;print("test-only batch");time.sleep(.25);sys.exit({code})']
    result=run_batches(tasks(tmp_path,4),command,workers=2,progress=progress)
    assert result==[0,7,0,0] and peak==2 and not active
    assert all((tmp_path/f'job{i}.txt').read_text().strip()=='test-only batch' for i in range(4))


def test_launch_failure_and_invalid_worker_limit(tmp_path):
    assert run_batches(tasks(tmp_path,2),lambda t:[str(tmp_path/'missing')],workers=1)==[127,127]
    with pytest.raises(ValueError):run_batches([],lambda t:[],workers=3)


def test_interrupt_cleans_owned_child(tmp_path):
    import os
    pid=None
    def progress(event,index,value,completed,total):
        nonlocal pid
        if event=='started':pid=value;raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        run_batches(tasks(tmp_path,1),lambda t:[sys.executable,'-c','import time;time.sleep(60)'],progress=progress)
    with pytest.raises(ProcessLookupError):os.kill(pid,0)
