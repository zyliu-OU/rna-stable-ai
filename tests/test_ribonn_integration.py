import copy
import hashlib

import pytest

from rnastable.ribonn_integration import selected_checkpoints,exact_prediction_replay,verify_weight_files


def runs():
    return [{"run_id":f"fold{fold}_rank{rank}","params.test_fold":str(fold),
             "metrics.val_r2":str(score)} for fold in [0,1] for rank,score in enumerate([0.9,0.8,0.7])]


def test_checkpoint_top_k_is_per_fold_and_validation_only():
    selected=selected_checkpoints(list(reversed(runs())),2)
    assert [(r["fold"],r["run_id"]) for r in selected]==[
        (0,"fold0_rank0"),(0,"fold0_rank1"),(1,"fold1_rank0"),(1,"fold1_rank1")]


@pytest.mark.parametrize("problem",["duplicate","tie","nonfinite","fold","path","short"])
def test_checkpoint_inventory_rejects_ambiguous_or_incomplete_inputs(problem):
    rows=runs()
    if problem=="duplicate":rows.append(rows[0])
    if problem=="tie":rows[2]["metrics.val_r2"]="0.8"
    if problem=="nonfinite":rows[0]["metrics.val_r2"]="nan"
    if problem=="fold":rows[0]["params.test_fold"]="0.5"
    if problem=="path":rows[0]["run_id"]="../escape"
    if problem=="short":rows=rows[:1]
    with pytest.raises(ValueError):selected_checkpoints(rows,2)


def predictions():
    return [{"tx_id":"a","fold":str(f),"tx_sequence":"ATGTAA","task":str(1+f/10)} for f in [0,1]]


def test_exact_replay_is_keyed_and_accepts_shuffled_rows():
    first=predictions()
    assert exact_prediction_replay(first,list(reversed(first)),"task")["bitwise_float_equal"]


@pytest.mark.parametrize("problem",["duplicate","missing","sequence","score","nonfinite"])
def test_replay_rejects_row_loss_identity_changes_and_changed_scores(problem):
    first=predictions(); second=copy.deepcopy(first)
    if problem=="duplicate":second.append(second[0])
    if problem=="missing":second.pop()
    if problem=="sequence":second[0]["tx_sequence"]="ATGTAG"
    if problem=="score":second[0]["task"]="1.0000000000000002"
    if problem=="nonfinite":second[0]["task"]="nan"
    with pytest.raises(ValueError):exact_prediction_replay(first,second,"task")


def test_weight_inventory_checksum_and_path_guard(tmp_path):
    path=tmp_path/"state.pth";path.write_bytes(b"fixed test payload")
    manifest={"files":[{"path":"state.pth","bytes":path.stat().st_size,
                         "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}]}
    assert verify_weight_files(manifest,tmp_path)==1
    path.write_bytes(b"changed test bytes")
    with pytest.raises(ValueError):verify_weight_files(manifest,tmp_path)
    manifest["files"][0]["path"]="../outside"
    with pytest.raises(ValueError):verify_weight_files(manifest,tmp_path)
