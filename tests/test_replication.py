import pytest
from rnastable.replication import paired_comparisons


def rows():
    common = dict(kind='mixed',length=2000,sequence_seed=1729,search_seed=2718,
                  input_sha256='same-input',status='validated')
    return [dict(common,beam_size=200,input_pair_f1=.5,input_lf_wall_seconds=2,
                 vienna_delta_kcal_mol=-3),
            dict(common,beam_size=400,input_pair_f1=.7,input_lf_wall_seconds=5,
                 vienna_delta_kcal_mol=-5)]


def test_paired_direction_and_missing_failure():
    data = rows()
    pair = paired_comparisons(data)[0]
    assert pair['input_pair_f1_change'] == pytest.approx(.2)
    assert pair['input_lf_time_ratio'] == 2.5
    assert pair['vienna_delta_difference_kcal_mol'] == -2
    data[1].update(status='validation_failed',vienna_delta_kcal_mol=None)
    assert paired_comparisons(data)[0]['vienna_delta_difference_kcal_mol'] is None
    assert paired_comparisons(data)[0]['input_pair_f1_change'] == pytest.approx(.2)


@pytest.mark.parametrize('invalid', ['duplicate','missing','hash','beam'])
def test_invalid_pair_rejected(invalid):
    data = rows()
    if invalid == 'duplicate':
        data.append(dict(data[0]))
    elif invalid == 'missing':
        data.pop()
    elif invalid == 'hash':
        data[1]['input_sha256'] = 'different-input'
    else:
        data[1]['beam_size'] = 800
    with pytest.raises(ValueError):
        paired_comparisons(data)
