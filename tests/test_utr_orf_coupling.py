"""Tests for the UTR-ORF coupling measurement helpers.

The experiment's conclusion rests entirely on these two functions being right:
the shuffle must preserve dinucleotide composition (or the comparison would be
about composition rather than arrangement), and the rank correlation must be
correct (or the reordering claim would be unfounded).
"""
import collections
import importlib.util
import random
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "measure_utr_orf_coupling.py"
spec = importlib.util.spec_from_file_location("coupling", SCRIPT)
coupling = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coupling)

REF = "AAAUAAGAGAGAAAAGAAGAGUAAGAAGAAAUAUAAGAGCCACC"


def dinucs(s):
    return collections.Counter(a + b for a, b in zip(s, s[1:]))


# --- dinucleotide shuffle -------------------------------------------------

@pytest.mark.parametrize("seed", range(8))
def test_shuffle_preserves_dinucleotide_composition(seed):
    """The whole point: arrangement changes, composition does not."""
    out = coupling.dinucleotide_shuffle(REF, random.Random(seed))
    assert dinucs(out) == dinucs(REF)


@pytest.mark.parametrize("seed", range(8))
def test_shuffle_preserves_length_and_mononucleotide_counts(seed):
    out = coupling.dinucleotide_shuffle(REF, random.Random(seed))
    assert len(out) == len(REF)
    assert collections.Counter(out) == collections.Counter(REF)


@pytest.mark.parametrize("seed", range(8))
def test_shuffle_preserves_first_and_last_base(seed):
    """An Eulerian path shuffle keeps the endpoints; that is what makes counts work."""
    out = coupling.dinucleotide_shuffle(REF, random.Random(seed))
    assert out[0] == REF[0]
    assert out[-1] == REF[-1]


def test_shuffle_actually_rearranges():
    """A shuffle that returned the input would silently void the experiment."""
    rng = random.Random(0)
    outs = {coupling.dinucleotide_shuffle(REF, rng) for _ in range(30)}
    assert len(outs) > 10
    assert any(o != REF for o in outs)


def test_shuffle_is_deterministic_given_a_seed():
    a = coupling.dinucleotide_shuffle(REF, random.Random(99))
    b = coupling.dinucleotide_shuffle(REF, random.Random(99))
    assert a == b


def test_shuffled_variants_are_not_candidates():
    """The shuffle destroys the Kozak, which is what keeps these out of scope."""
    rng = random.Random(7)
    outs = [coupling.dinucleotide_shuffle(REF, rng) for _ in range(40)]
    assert sum(o.endswith("GCCACC") for o in outs) == 0


def test_shuffle_handles_a_homopolymer():
    """Degenerate input must not hang or corrupt; every shuffle equals the input."""
    assert coupling.dinucleotide_shuffle("AAAAA", random.Random(1)) == "AAAAA"


# --- rank correlation -----------------------------------------------------

def test_spearman_perfect_positive():
    assert coupling.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)


def test_spearman_perfect_negative():
    assert coupling.spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


def test_spearman_is_rank_based_not_value_based():
    """Monotone rescaling must not change the answer."""
    xs = [1, 2, 3, 4, 5]
    assert coupling.spearman(xs, [1, 4, 9, 16, 25]) == pytest.approx(1.0)


def test_spearman_known_value():
    """Textbook case with a single inversion: rho = 0.9 for n=5."""
    assert coupling.spearman([1, 2, 3, 4, 5], [1, 2, 3, 5, 4]) == pytest.approx(0.9)


def test_spearman_handles_ties_by_averaging():
    assert coupling.spearman([1, 1, 2, 2], [1, 1, 2, 2]) == pytest.approx(1.0)


def test_spearman_of_a_constant_series_is_nan_not_an_exception():
    """A degenerate series must surface as nan rather than a crash or a fake 1.0."""
    result = coupling.spearman([1, 2, 3], [5, 5, 5])
    assert result != result  # nan


def test_spearman_matches_scipy_on_random_data():
    """Cross-check the hand-rolled implementation against a reference."""
    scipy_stats = pytest.importorskip("scipy.stats")
    rng = random.Random(4)
    for _ in range(5):
        xs = [rng.random() for _ in range(25)]
        ys = [rng.random() for _ in range(25)]
        assert coupling.spearman(xs, ys) == pytest.approx(
            scipy_stats.spearmanr(xs, ys).statistic)
