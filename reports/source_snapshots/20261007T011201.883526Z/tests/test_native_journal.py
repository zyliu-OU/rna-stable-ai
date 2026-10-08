import json
import pytest
from rnastable.native_journal import NativeJournal,exclusive_driver
from rnastable.reference import digest


def fold():return {'status':'ok','structure':'((....))','mfe_kcal_mol':-3.,'wall_seconds':.5}


def test_completed_native_request_is_reused_after_reopening(tmp_path):
    calls=[];journal=NativeJournal(tmp_path,digest(b'plan'))
    def native():calls.append(1);return fold()
    first=journal.run('method_proposal_1','GGAAAACC',{'beam':100},native);first['mfe_kcal_mol']=999
    reopened=NativeJournal(tmp_path,digest(b'plan'));second=reopened.run('method_proposal_1','GGAAAACC',{'beam':100},native)
    assert second==fold() and calls==[1] and reopened.cache_hits==1 and reopened.callbacks_invoked==0


def test_interruption_remains_unknown_and_does_not_call_native_again(tmp_path):
    journal=NativeJournal(tmp_path,digest(b'plan'));calls=[]
    def native():calls.append(1);raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):journal.run('request_1','GGAAAACC',{'beam':100},native)
    result=NativeJournal(tmp_path,digest(b'plan')).run('request_1','GGAAAACC',{'beam':100},lambda:pytest.fail('Interrupted request was retried'))
    assert result['status']=='error' and result['interrupted'] is True and 'mfe_kcal_mol' not in result and 'wall_seconds' not in result and calls==[1]


def test_started_marker_without_completion_is_conservatively_recovered(tmp_path):
    journal=NativeJournal(tmp_path,digest(b'plan'));payload={'binding_sha256':digest(b'plan'),'key':'started','state':'started','sequence_sha256':digest(b'GGAAAACC'),'parameters':{'beam':100},'driver_pid':0};journal.write('started',payload)
    result=journal.run('started','GGAAAACC',{'beam':100},lambda:pytest.fail('Incomplete request was retried'))
    assert result['interrupted'] and journal.read('started')['state']=='interrupted'


def test_binding_parameters_sequence_and_corruption_fail_closed(tmp_path):
    journal=NativeJournal(tmp_path,digest(b'plan'));journal.run('request','GGAAAACC',{'beam':100},fold)
    with pytest.raises(ValueError,match='parameters'):journal.run('request','CCAAAAGG',{'beam':100},fold)
    with pytest.raises(ValueError,match='parameters'):journal.run('request','GGAAAACC',{'beam':200},fold)
    with pytest.raises(ValueError,match='binding'):NativeJournal(tmp_path,digest(b'other')).run('request','GGAAAACC',{'beam':100},fold)
    p=journal.path('request');envelope=json.loads(p.read_text());envelope['payload']['result']['mfe_kcal_mol']=-999;p.write_text(json.dumps(envelope))
    with pytest.raises(ValueError,match='payload'):journal.run('request','GGAAAACC',{'beam':100},fold)


def test_concurrent_driver_and_invalid_energy_do_not_create_success(tmp_path):
    journal=NativeJournal(tmp_path,digest(b'plan'))
    with exclusive_driver(tmp_path/'.lock'):
        with pytest.raises(ValueError,match='active'):journal.run('request','GGAAAACC',{},fold)
    assert not journal.path('request').exists()
    with pytest.raises(ValueError,match='finite'):journal.run('bad_energy','GGAAAACC',{},lambda:{**fold(),'mfe_kcal_mol':True})
    assert journal.read('bad_energy')['state']=='interrupted'
