"""The bit-parallel filter must never discard a SequenceMatcher overlap."""

from difflib import SequenceMatcher
from itertools import product
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_bprna_training_subset_v2 import lcs_length, masks, overlap_after_lcs  # noqa: E402


def dynamic_lcs(first, second):
    previous = [0] * (len(second) + 1)
    for base in first:
        current = [0]
        for index, other in enumerate(second, 1):
            current.append(previous[index - 1] + 1 if base == other
                           else max(current[-1], previous[index]))
        previous = current
    return previous[-1]


def test_bit_parallel_lcs_matches_dynamic_short_rnas():
    strings = ["".join(chars) for length in range(1, 5)
               for chars in product("ACG", repeat=length)]
    for first in strings:
        for second in strings:
            assert lcs_length(first, masks(second)) == dynamic_lcs(first, second)


def test_lcs_filter_preserves_symmetric_sequence_matcher_hits():
    samples = ["ACGU" * 20, "ACGA" * 20, "U" * 10 + "ACGU" * 20,
               "G" * 80, "ACGU" * 15 + "UUUU" * 5]
    for first in samples:
        for second in samples:
            exact = max(SequenceMatcher(None, first, second, autojunk=False).ratio(),
                        SequenceMatcher(None, second, first, autojunk=False).ratio())
            if exact >= 0.8:
                assert overlap_after_lcs(first, second, masks(second), 0.8)
