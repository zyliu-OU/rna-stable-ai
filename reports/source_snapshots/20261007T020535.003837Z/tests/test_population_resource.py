import pytest
from rnastable.population_resource import toy_record,training_step,tensor_digest
from rnastable.population_sampling import PairPopulation
from rnastable.pair_model import CANONICAL


def config():return {'mode':'long_comparative_development_only','seed':20261006,'learning_rate':.001,'embedding_dim':4,'channels':4,'pair_dim':4,'dilations':[1,2,4,8],'cpu_threads':2,'positive_weight_exponent':1.,'pair_features':'local_helix_context_v1'}


def test_synthetic_training_step_replays_loss_gradient_and_model_state():
    record=toy_record(40);settings={'seed':7,'negatives_per_positive':2,'minimum_negatives':1,'max_length':10000}
    first,metadata,result=training_step(record,config(),settings);second,other,replay=training_step(record,config(),settings)
    assert metadata==other and result==replay
    assert result['initial_state_tensor_sha256']!=result['final_state_tensor_sha256']
    assert result['gradient_l2_norm']>0 and result['optimizer_steps']==1
    assert result['accuracy_evaluated'] is False and result['full_pair_labels_materialized'] is False
    assert result['full_label_tensor_bytes_if_materialized']>metadata['retained_tensor_bytes']


@pytest.mark.parametrize('length',[7,9,10002,True])
def test_toy_resource_bounds(length):
    with pytest.raises(ValueError):toy_record(length)


def test_population_rank_inventory_matches_many_constructed_sequences():
    for seed in range(16):
        for length in (8,12,20,40,80):
            record=toy_record(length,seed);population=PairPopulation(record)
            expected={(i,j) for j in range(length) for i in range(j-3) if record['sequence'][i]+record['sequence'][j] in CANONICAL}-population.positives
            actual={population.negative_at(rank) for rank in range(population.negative_count)}
            assert actual==expected and population.positive_count==(length-4)//2
