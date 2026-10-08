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


def test_directory_binding_rejects_a_different_plan_even_for_a_new_key(tmp_path):
    journal=NativeJournal(tmp_path,digest(b'one'));journal.run('first','GGAAAACC',{},fold)
    other=NativeJournal(tmp_path,digest(b'two'))
    with pytest.raises(ValueError,match='directory binding'):other.run('new_key','GGAAAACC',{},lambda:pytest.fail('Foreign plan ran'))
    assert not other.path('new_key').exists()


def test_orphaned_raw_output_is_preserved_without_a_native_callback(tmp_path):
    raw=tmp_path/'native.txt';raw.write_text('surviving output')
    journal=NativeJournal(tmp_path/'ledger',digest(b'plan'))
    with pytest.raises(ValueError,match='without a journal'):journal.run('orphan','GGAAAACC',{'raw_output':str(raw)},lambda:pytest.fail('Duplicate native work'))
    assert raw.read_text()=='surviving output' and journal.callbacks_invoked==0 and not journal.path('orphan').exists()


@pytest.mark.parametrize('value',[-1.,True,float('inf'),float('nan')])
def test_invalid_native_cost_is_unknown_and_not_cached_as_success(tmp_path,value):
    journal=NativeJournal(tmp_path,digest(b'plan'))
    with pytest.raises(ValueError):journal.run('bad_cost','GGAAAACC',{},lambda:{**fold(),'wall_seconds':value})
    assert journal.read('bad_cost')['state']=='interrupted'
    result=journal.run('bad_cost','GGAAAACC',{},lambda:pytest.fail('Unknown request retried'))
    assert result['interrupted'] and 'wall_seconds' not in result


def test_rehashed_malformed_result_fails_schema_validation_without_retry(tmp_path):
    journal=NativeJournal(tmp_path,digest(b'plan'));journal.run('cached','GGAAAACC',{},fold)
    payload=journal.read('cached');payload['result']['wall_seconds']=-1;journal.write('cached',payload)
    with pytest.raises(ValueError,match='cost'):journal.run('cached','GGAAAACC',{},lambda:pytest.fail('Corrupt cache retried'))


def test_cached_structure_length_and_interrupted_energy_are_revalidated(tmp_path):
    journal=NativeJournal(tmp_path,digest(b'plan'));journal.run('cached','GGAAAACC',{},fold)
    payload=journal.read('cached');payload['result']['structure']='.';journal.write('cached',payload)
    with pytest.raises(ValueError):journal.run('cached','GGAAAACC',{},lambda:pytest.fail('Wrong structure retried'))
    payload['state']='interrupted';payload['result']={'status':'error','interrupted':True,'mfe_kcal_mol':0.};journal.write('cached',payload)
    with pytest.raises(ValueError,match='interrupted'):journal.read('cached')


def test_legacy_ledger_read_is_immutable_and_write_adoption_checks_all_entries(tmp_path):
    journal=NativeJournal(tmp_path,digest(b'plan'))
    payload={'binding_sha256':journal.binding,'key':'legacy','state':'complete','sequence_sha256':digest(b'GGAAAACC'),'parameters':{},'result':fold()};journal.write('legacy',payload)
    before=journal.path('legacy').read_bytes();assert journal.read('legacy')==payload and not (tmp_path/'.binding').exists()
    journal.run('new','GGAAAACC',{},fold)
    assert (tmp_path/'.binding').exists() and journal.path('legacy').read_bytes()==before
