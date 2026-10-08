from datetime import datetime,timezone
import json
from pathlib import Path
import pytest
from rnastable.folding import tool_commands
from rnastable.native_journal import atomic_json
from rnastable.reference import digest
from rnastable.reference_extension import prepare,execute,audit,can_admit,validate_config
from rnastable.sequences import write_fasta
from test_pooled_proposals import config as source_config


def config():return {'input_indices':[2],'seeds':[20261006,20261007],'temperature_c':37,'beam_size':100,'timeout_seconds':300,'memory_limit_gib':4,'planned_requests':12,'deadline_utc':'2099-01-01T00:00:00+00:00'}


def source(tmp_path):
    original='GGAAAACC'+'A'*9992;finalist='GAGAAACC'+'A'*9992;components=[]
    for seed in config()['seeds']:
        run=tmp_path/('source_'+str(seed));run.mkdir();cfg={**source_config(),'seed':seed}
        atomic_json(run/'manifest.json',{'input_index':2,'config':cfg})
        write_fasta(run/'input.fasta','input',original)
        for policy in ('random_pool','compatibility_only','checkpoint_prior'):
            directory=run/policy;directory.mkdir();write_fasta(directory/'finalist.fasta',policy,finalist)
            atomic_json(directory/'result.json',{'search':{'status':'completed','sequence':finalist},'row':{'selected_vienna_delta_kcal_mol':None}})
        atomic_json(run/'summary.json',{'seed':seed,'run_dir':str(run)})
        components.append({'summary':str(run/'summary.json'),'sha256':digest((run/'summary.json').read_bytes())})
    path=tmp_path/'replication.json';atomic_json(path,{'complete':True,'test_accuracy_evaluated':False,'model_fitted':False,'components':components})
    return path


def native(root,sequence,cfg,tool,path):
    energy=-10. if sequence.startswith('GG') else -11.;structure='.'*len(sequence)
    path.write_text(sequence+'\n'+structure+f' ({energy:.2f})\nSTDERR:\n')
    return {'status':'ok','tool':tool,'device':'CPU','command':tool_commands(root,cfg)[tool][0],'returncode':0,'structure':structure,'paired_fraction':0.,'mfe_kcal_mol':energy,'wall_seconds':.5,'raw_output':str(path)}


def test_reference_extension_keeps_original_source_and_replays_native_selection(tmp_path):
    source_path=source(tmp_path);before=source_path.read_bytes();run=prepare(tmp_path,source_path,config(),[])
    result=execute(tmp_path,run,native);assert source_path.read_bytes()==before
    assert result['unique_native_requests']==12 and result['current_invocation_callbacks']==12
    assert result['known_native_wall_seconds']==6 and result['unknown_native_requests']==0
    assert all(row['selected_vienna_delta_kcal_mol']==-1 and row['selected_mutations']==2 and row['prior_selected_vienna_delta_kcal_mol'] is None for row in result['rows'])
    assert audit(tmp_path,run/'summary.json')==result
    before={str(p):p.read_bytes() for p in run.rglob('*') if p.is_file()}
    assert execute(tmp_path,run,lambda *args:pytest.fail('Complete reference repeated'))==result
    assert before=={str(p):p.read_bytes() for p in run.rglob('*') if p.is_file()}


def test_reference_extension_interrupt_is_unknown_and_never_retried(tmp_path):
    run=prepare(tmp_path,source(tmp_path),config(),[]);calls=[]
    def interrupted(*args):
        calls.append(str(args[-1]))
        if len(calls)==2:raise KeyboardInterrupt
        return native(*args)
    with pytest.raises(KeyboardInterrupt):execute(tmp_path,run,interrupted)
    result=execute(tmp_path,run,native)
    assert result['unique_native_requests']==12 and result['unknown_native_requests']==1
    assert result['completed_native_requests']==11 and result['known_native_wall_seconds']==5.5
    assert result['current_invocation_callbacks']==10 and result['current_invocation_cache_hits']==2
    assert result['rows'][0]['selection_reason']=='validation_failed'
    audit(tmp_path,run/'summary.json')


def test_deadline_admission_defers_before_a_new_native_request(tmp_path):
    cfg={**config(),'deadline_utc':'2000-01-01T00:00:00+00:00'};run=prepare(tmp_path,source(tmp_path),cfg,[])
    assert execute(tmp_path,run,lambda *args:pytest.fail('Request after deadline')) is None
    assert not list((run/'native_journal').glob('*.json')) and not (run/'summary.json').exists()
    assert json.loads((run/'progress.json').read_text())['state']=='deadline_deferred'
    cfg={**config(),'deadline_utc':'2026-10-07T04:00:00+00:00'}
    assert can_admit(cfg,datetime(2026,10,7,3,54,44,tzinfo=timezone.utc))
    assert not can_admit(cfg,datetime(2026,10,7,3,54,46,tzinfo=timezone.utc))


@pytest.mark.parametrize('changed',[{'timeout_seconds':float('inf')},{'timeout_seconds':True},{'memory_limit_gib':0},{'planned_requests':True},{'deadline_utc':'2026-10-07T04:00:00'},{'seeds':[20261007]}])
def test_reference_extension_budget_and_deadline_validation(changed):
    with pytest.raises(ValueError):validate_config({**config(),**changed})


def test_changed_snapshot_fails_before_execution_and_changed_raw_fails_audit(tmp_path):
    run=prepare(tmp_path,source(tmp_path),config(),[]);manifest=json.loads((run/'manifest.json').read_text())
    path=run/next(iter(manifest['snapshot_sha256']));original=path.read_bytes();path.write_text('changed')
    with pytest.raises(ValueError,match='snapshot'):execute(tmp_path,run,lambda *args:pytest.fail('Changed inputs ran'))
    path.write_bytes(original);execute(tmp_path,run,native)
    raw=next((run/'arms').glob('*/*_ViennaRNA.txt'));raw.write_text('changed')
    with pytest.raises(ValueError,match='raw output'):audit(tmp_path,run/'summary.json')
