"""Tests for the windowed synonymous design space.

A generator that quietly produces a non-synonymous variant would corrupt every
downstream claim, and one that quietly repairs a bad variant would hide its own
failures. Those are the first things pinned here. The rest pins the window
boundaries, the declared constraints, determinism, and the measured GC confound
that makes the free/neutral choice matter.
"""
import pytest

from rnastable.synonymous_window import (
    build_pool,
    check_variant,
    codon_table,
    describe,
    longest_homopolymer,
    split_codons,
    synonyms,
    translate,
    window_indices,
)

REFERENCE = ("ATG" "GAG" "GAC" "GCC" "AAG" "AAC" "ATT" "AAG" "AAA" "GGC" "TGA")


@pytest.fixture(scope="module")
def codons():
    return split_codons(REFERENCE)


def test_the_codon_table_covers_every_codon_and_marks_stops():
    table = codon_table()
    assert len(table) == 64
    assert table["ATG"] == "M"
    assert {table[c] for c in ("TAA", "TAG", "TGA")} == {"*"}


def test_synonym_groups_are_deterministically_ordered():
    groups = synonyms()
    assert groups["M"] == ["ATG"]
    assert groups["W"] == ["TGG"]
    assert len(groups["L"]) == 6
    assert groups["L"] == sorted(groups["L"])


def test_split_codons_requires_a_complete_reading_frame():
    with pytest.raises(ValueError):
        split_codons("ATGGA")
    with pytest.raises(ValueError):
        split_codons("GAGTGA")          # no start codon
    with pytest.raises(ValueError):
        split_codons("ATGGAG")          # no stop codon
    with pytest.raises(ValueError):
        split_codons("ATGTGAGAGTGA")    # internal in-frame stop
    with pytest.raises(ValueError):
        split_codons("ATGNNNTGA")       # non-ACGT


def test_split_codons_accepts_rna_spelling():
    assert split_codons("AUGGAGUGA") == ["ATG", "GAG", "TGA"]


def test_the_window_excludes_the_start_and_stop_codons(codons):
    indices = window_indices(codons, 30)
    assert indices[0] == 1
    assert max(indices) == len(codons) - 2
    assert 0 not in indices


def test_the_window_is_clipped_to_the_orf(codons):
    assert window_indices(codons, 3) == [1, 2, 3]
    assert window_indices(codons, 1000) == list(range(1, len(codons) - 1))


def test_a_window_must_be_a_positive_integer_and_contain_something(codons):
    for bad in (0, -1, 2.5):
        with pytest.raises(ValueError):
            window_indices(codons, bad)
    with pytest.raises(ValueError):
        window_indices(["ATG", "TGA"], 5)


def test_longest_homopolymer():
    assert longest_homopolymer("") == 0
    assert longest_homopolymer("A") == 1
    assert longest_homopolymer("AACCCG") == 3
    assert longest_homopolymer("GGGGGG") == 6


def test_check_variant_names_each_violation(codons):
    assert check_variant(codons, codons, window_indices(codons, 30), 6) is None
    indices = window_indices(codons, 2)

    changed_protein = list(codons)
    changed_protein[1] = "TTT"
    assert check_variant(codons, changed_protein, indices, 6) == "protein_changed"

    outside = list(codons)
    outside[5] = [c for c in synonyms()[codon_table()[codons[5]]] if c != codons[5]][0]
    assert check_variant(codons, outside, indices, 6) == "change_outside_window"

    start = list(codons)
    start[0] = "GTG"
    assert check_variant(codons, start, indices, 6) == "protein_changed"

    stop = list(codons)
    stop[-1] = "TAA"
    assert check_variant(codons, stop, window_indices(codons, 30), 6) == "stop_codon_changed"

    assert check_variant(codons, codons[:-1], indices, 6) == "length_changed"
    assert check_variant(codons, codons, indices, 2) == "homopolymer_run_too_long"


def test_describe_reports_composition_and_a_hash(codons):
    description = describe(codons, codons, window_indices(codons, 30))
    assert description["substitution_count"] == 0
    assert description["substituted_codon_indices"] == []
    assert 0.0 <= description["window_gc_fraction"] <= 1.0
    assert len(description["orf_sha256"]) == 64


def test_describe_emits_no_score_or_feature_vector(codons):
    """Scoring is gate-disabled; descriptive composition is not a score."""
    description = describe(codons, codons, window_indices(codons, 30))
    for banned in ("score", "objective", "feature", "rank", "predicted"):
        assert not any(banned in key for key in description), banned


@pytest.fixture(scope="module")
def pool(real_orf):
    return build_pool(real_orf, window_codons=30, size=48, seed=1729)


@pytest.fixture(scope="module")
def real_orf():
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "data/constructs/fluc_orf.txt"
    if not path.exists():
        pytest.skip("reference ORF not available")
    return "".join(path.read_text().split())


def test_member_zero_is_the_unmodified_reference(pool, real_orf):
    first = pool["members"][0]
    assert first["is_reference"] is True
    assert first["substitution_count"] == 0
    assert "".join(first["codons"]) == real_orf.upper().replace("U", "T")


def test_every_member_preserves_the_protein_exactly(pool, real_orf):
    protein = translate(split_codons(real_orf))
    for member in pool["members"]:
        assert translate(member["codons"]) == protein


def test_every_member_changes_only_window_codons(pool, real_orf):
    reference = split_codons(real_orf)
    allowed = set(pool["window_codon_indices"])
    for member in pool["members"]:
        changed = {i for i, (a, b) in enumerate(zip(reference, member["codons"])) if a != b}
        assert not changed - allowed


def test_members_are_unique(pool):
    hashes = [member["orf_sha256"] for member in pool["members"]]
    assert len(set(hashes)) == len(hashes)


def test_the_pool_spans_edit_distance_rather_than_clustering(pool):
    """Per-position independent draws would leave nothing near the reference."""
    counts = [member["substitution_count"] for member in pool["members"]]
    assert min(counts) == 0
    assert len(set(counts)) > len(counts) // 4


def test_the_homopolymer_bound_is_enforced(pool):
    for member in pool["members"]:
        assert member["longest_homopolymer"] <= pool["max_homopolymer"]


def test_rejections_are_counted_by_cause_not_repaired(pool):
    assert isinstance(pool["rejected"], dict)
    assert all(isinstance(count, int) for count in pool["rejected"].values())


def test_the_pool_is_deterministic(real_orf):
    a = build_pool(real_orf, window_codons=30, size=32, seed=7)
    b = build_pool(real_orf, window_codons=30, size=32, seed=7)
    assert [m["orf_sha256"] for m in a["members"]] == [m["orf_sha256"] for m in b["members"]]


def test_a_different_seed_gives_a_different_pool(real_orf):
    a = build_pool(real_orf, window_codons=30, size=32, seed=7)
    b = build_pool(real_orf, window_codons=30, size=32, seed=1729)
    assert [m["orf_sha256"] for m in a["members"]] != [m["orf_sha256"] for m in b["members"]]


def test_the_caller_global_rng_state_is_untouched(real_orf):
    import random
    random.seed(99)
    expected = random.random()
    random.seed(99)
    build_pool(real_orf, window_codons=30, size=16, seed=7)
    assert random.random() == expected


def test_neutral_mode_holds_window_gc_exactly_constant(real_orf):
    pool = build_pool(real_orf, window_codons=30, size=64, seed=1729, gc_mode="neutral")
    assert len({member["window_gc_fraction"] for member in pool["members"]}) == 1
    assert pool["substitutable_positions"] < 29


def test_free_mode_leaves_gc_correlated_with_edit_distance(real_orf):
    """The confound that makes the free/neutral choice a real decision."""
    import statistics

    pool = build_pool(real_orf, window_codons=30, size=256, seed=1729, gc_mode="free")
    counts = [member["substitution_count"] for member in pool["members"]]
    window_gc = [member["window_gc_fraction"] for member in pool["members"]]
    assert statistics.correlation(counts, window_gc) < -0.5
    # The reference is GC-maximal, which is why sampling cannot fix it.
    assert pool["members"][0]["window_gc_fraction"] == max(window_gc)


def test_an_unknown_gc_mode_is_rejected(real_orf):
    with pytest.raises(ValueError):
        build_pool(real_orf, window_codons=30, size=8, gc_mode="low")


def test_a_bad_size_is_rejected(real_orf):
    for bad in (0, -5, 2.5):
        with pytest.raises(ValueError):
            build_pool(real_orf, window_codons=30, size=bad)


def test_the_pool_records_that_it_is_unscored(pool):
    assert pool["scored"] is False
    assert pool["optimizer_features_emitted"] is False
