import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import pytest
from rnastable.folding import run_bounded,fold_sequence
from rnastable.cli import ROOT

pytestmark=pytest.mark.skipif(not sys.platform.startswith('linux'),reason='Linux parent-death supervision')


def alive(pid):
    path=Path(f'/proc/{pid}/stat')
    try:return path.read_text().split(') ',1)[1].split()[0]!='Z'
    except FileNotFoundError:return False


def wait_until(predicate,seconds=5):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if predicate():return True
        time.sleep(.02)
    return predicate()


def test_bounded_supervisor_preserves_output_status_and_timeout():
    result=run_bounded([sys.executable,'-c','import sys; print(sys.stdin.readline().strip()); sys.exit(7)'],'GGAAAACC',timeout=5,memory_limit_gib=1)
    assert result['status']=='error' and result['returncode']==7 and result['stdout'].strip()=='GGAAAACC'
    assert result['supervisor']=='linux_parent_death_guard_v1'
    result=run_bounded([sys.executable,'-c','import time; time.sleep(10)'],'GGAAAACC',timeout=.1,memory_limit_gib=1)
    assert result['status']=='timeout' and result['returncode']<0 and 'killed process group' in result['error']


def test_driver_sigkill_terminates_native_child_and_grandchild(tmp_path):
    marker=tmp_path/'pids.json';tool=tmp_path/'native.py';driver=tmp_path/'driver.py'
    tool.write_text('import json,os,subprocess,sys,time\nchild=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"])\nopen(sys.argv[1],"w").write(json.dumps({"native":os.getpid(),"leaf":child.pid}))\ntime.sleep(60)\n')
    driver.write_text('import sys\nfrom rnastable.folding import run_bounded\nrun_bounded([sys.executable,sys.argv[1],sys.argv[2]],"GGAAAACC",timeout=60,memory_limit_gib=1)\n')
    environment={**os.environ,'PYTHONPATH':str(ROOT/'src')}
    parent=subprocess.Popen([sys.executable,str(driver),str(tool),str(marker)],env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,start_new_session=True)
    pids={}
    try:
        assert wait_until(marker.exists),parent.stderr.read() if parent.poll() is not None else 'Native startup timed out'
        pids=json.loads(marker.read_text());assert all(alive(pid) for pid in pids.values())
        parent.kill();parent.wait(timeout=5)
        assert wait_until(lambda:all(not alive(pid) for pid in pids.values())),'Native descendants survived their driver'
    finally:
        if parent.poll() is None:parent.kill();parent.wait(timeout=5)
        if parent.stderr:parent.stderr.close()
        for pid in pids.values():
            if alive(pid):
                try:os.kill(pid,signal.SIGKILL)
                except ProcessLookupError:pass


def test_native_vienna_result_is_still_parseable_and_bound_to_inner_command(tmp_path):
    config={'temperature_c':37,'beam_size':100,'timeout_seconds':5,'memory_limit_gib':4}
    result=fold_sequence(ROOT,'GGAAAACC',config,'ViennaRNA',tmp_path/'fold.txt')
    assert result['status']=='ok' and result['tool']=='ViennaRNA' and result['supervisor']=='linux_parent_death_guard_v1'
    assert len(result['structure'])==8 and result['raw_output']==str(tmp_path/'fold.txt')
    assert 'process_guard' not in result['command']


def test_timeout_exit_race_still_returns_bounded_timeout(monkeypatch):
    import subprocess
    from rnastable import folding
    class GoneProcess:
        pid=123456789
        returncode=-9
        def __init__(self):self.calls=0
        def wait(self,timeout=None):
            self.calls+=1
            if self.calls==1:raise subprocess.TimeoutExpired(['fixture'],timeout)
            return self.returncode
    process=GoneProcess();monkeypatch.setattr(folding.subprocess,'Popen',lambda *args,**kwargs:process)
    def already_gone(*args):raise ProcessLookupError('Exit raced timeout cleanup')
    monkeypatch.setattr(folding.os,'killpg',already_gone)
    result=folding.run_bounded(['fixture'],'A',timeout=.01)
    assert result['status']=='timeout' and process.calls==2


def test_unexpected_wait_failure_kills_process_group_before_propagating(monkeypatch):
    from rnastable import folding
    import pytest
    events=[]
    class FailedWait:
        pid=123456789
        returncode=-9
        def __init__(self):self.calls=0
        def wait(self,timeout=None):
            self.calls+=1;events.append('wait')
            if self.calls==1:raise RuntimeError('Fixture wait failure')
    monkeypatch.setattr(folding.subprocess,'Popen',lambda *args,**kwargs:FailedWait());monkeypatch.setattr(folding.os,'killpg',lambda *args:events.append('kill'))
    with pytest.raises(RuntimeError,match='wait failure'):folding.run_bounded(['fixture'],'A',timeout=.01)
    assert events==['wait','kill','wait']
