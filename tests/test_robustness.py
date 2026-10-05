import pytest
from rnastable.robustness import search_variability


def row(seed,search,delta,**updates):
    result=dict(kind='mixed',length=1000,beam_size=200,sequence_seed=seed,search_seed=search,
                input_sha256=str(seed),status='validated',selection_source='finalist',
                selected_sha256=f'{seed}-{search}',selected_vienna_delta_kcal_mol=delta,
                vienna_delta_kcal_mol=delta)
    result.update(updates)
    return result


def test_search_repeats_are_averaged_within_inputs_first():
    inputs,groups=search_variability([row(1,1,-2),row(1,2,-4),row(2,1,-9)])
    assert inputs[0]['mean_selected_delta_kcal_mol']==-3
    assert inputs[0]['sd_selected_delta_kcal_mol']==pytest.approx(2**.5)
    assert groups[0]['mean_input_mean_selected_delta_kcal_mol']==-6
    assert groups[0]['input_count']==2 and groups[0]['search_runs']==3


def test_worsened_candidate_stays_visible_after_returning_input():
    inputs,groups=search_variability([row(1,1,0,selection_source='input',vienna_delta_kcal_mol=2)])
    assert inputs[0]['candidate_worsenings']==1
    assert inputs[0]['mean_candidate_delta_kcal_mol']==2
    assert inputs[0]['mean_selected_delta_kcal_mol']==0
    assert groups[0]['selected_finalists']==0 and groups[0]['returned_inputs']==1


def test_unknown_validation_not_converted_to_zero():
    inputs,groups=search_variability([row(1,1,None,status='validation_failed',selection_source='input',
                                            vienna_delta_kcal_mol=None)])
    assert inputs[0]['known_selected_energies']==0
    assert inputs[0]['mean_selected_delta_kcal_mol'] is None
    assert groups[0]['failed_candidates']==1
    assert groups[0]['mean_input_mean_selected_delta_kcal_mol'] is None


@pytest.mark.parametrize('change',[{'input_sha256':'different'},
    {'selected_vienna_delta_kcal_mol':1},{'selected_vienna_delta_kcal_mol':float('nan')}])
def test_invalid_observation_rejected(change):
    with pytest.raises(ValueError):
        search_variability([row(1,1,-2),row(1,2,-3,**change)])


def test_duplicate_search_rejected():
    with pytest.raises(ValueError,match='Duplicate'):
        search_variability([row(1,1,-2),row(1,1,-2)])


def test_cell_error_without_selected_artifact_remains_missing():
    item=row(1,1,None,status='error',vienna_delta_kcal_mol=None)
    del item['selection_source'];del item['selected_sha256']
    inputs,groups=search_variability([item])
    assert inputs[0]['selection_missing_runs']==1
    assert inputs[0]['returned_inputs']==inputs[0]['selected_finalists']==0
    assert groups[0]['failed_candidates']==1 and groups[0]['selection_missing_runs']==1
