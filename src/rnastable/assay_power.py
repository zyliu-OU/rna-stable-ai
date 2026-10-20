"""Replayable power and minimum-detectable-effect arithmetic for the assay design.

This module exists because `configs/assay_definition_v3_2026-10-19.json` records
specific numerical power claims (power at n=3 per CV, the replicate count needed
for 80 percent power, the minimum detectable effect, and a paired alternative)
that no executable artifact reproduced. A design conclusion that rests on
arithmetic nobody can replay is not auditable, so the arithmetic lives here and
is pinned by tests.

Nothing here measures anything. Every input is a planning assumption, and a
power figure establishes no stability, translation or expression benefit; it
states only what an experiment of a given size could detect if the assumed
dispersion turned out to be correct.

The dispersion convention must always be passed explicitly. The frozen v3
figures were produced under `log1p_cv`, which is an approximation, not the
log-normal relation; `lognormal_exact` is the exact one and yields lower power
from the same CV. Defaulting either way would silently pick a side of that
discrepancy, so there is no default.
"""
from dataclasses import dataclass, asdict
import math

from scipy import stats

# ln(1 + CV) is the convention under which the frozen assay_definition_v3
# figures were computed. It is retained so those figures stay replayable, not
# because it is correct: for a log-normal with coefficient of variation CV the
# log-scale standard deviation is sqrt(ln(1 + CV**2)). The two agree to first
# order in CV and diverge as CV grows, with log1p_cv the more optimistic of the
# pair, so the convention is part of any power claim rather than an internal
# detail.
DISPERSION_CONVENTIONS = ("lognormal_exact", "log1p_cv")

DESIGNS = ("unpaired_two_sample", "paired_one_sample")


def log_scale_sd(cv, convention):
    """Standard deviation on the natural-log scale implied by a CV."""
    if convention not in DISPERSION_CONVENTIONS:
        raise ValueError(f"Dispersion convention must be one of {DISPERSION_CONVENTIONS}")
    if not isinstance(cv, (int, float)) or isinstance(cv, bool) or not 0 < cv < 10:
        raise ValueError("Coefficient of variation must be a fraction in (0, 10), not a percentage")
    if convention == "lognormal_exact":
        return math.sqrt(math.log(1.0 + cv * cv))
    return math.log(1.0 + cv)


def _standard_error(sd, n, design):
    """Standard error of the log fold-change estimate for n units per condition."""
    if design not in DESIGNS:
        raise ValueError(f"Design must be one of {DESIGNS}")
    if type(n) is not int or n < 2:
        raise ValueError("At least 2 units per condition are required to estimate dispersion")
    if design == "paired_one_sample":
        # Paired analysis differences out the between-unit component, so the
        # same n buys a smaller standard error and one fewer degree of freedom
        # group. It is only legitimate when units are genuinely matched.
        return sd / math.sqrt(n), n - 1
    return sd * math.sqrt(2.0 / n), 2 * n - 2


def power(cv, n, fold_change, convention, design="unpaired_two_sample", alpha=0.05):
    """Probability of rejecting the null at `alpha` if `fold_change` is real.

    The test is two-sided on the log scale with an unknown variance, so the
    alternative distribution is noncentral t rather than normal. Using a normal
    approximation at these sample sizes would overstate power materially.
    """
    if not isinstance(fold_change, (int, float)) or isinstance(fold_change, bool) or fold_change <= 0:
        raise ValueError("Fold change must be a positive ratio")
    if fold_change == 1.0:
        raise ValueError("A fold change of 1.0 is the null; its power is alpha by definition")
    if not isinstance(alpha, (int, float)) or isinstance(alpha, bool) or not 0 < alpha < 1:
        raise ValueError("Alpha must lie strictly between 0 and 1")
    sd = log_scale_sd(cv, convention)
    se, df = _standard_error(sd, n, design)
    # abs() makes enhancement and reduction of the same ratio equally powered,
    # which is what a two-sided test actually delivers.
    ncp = abs(math.log(fold_change)) / se
    critical = stats.t.ppf(1.0 - alpha / 2.0, df)
    # Rejection in the far tail is negligible here but is not dropped, because
    # omitting it would understate power for very large effects.
    return float(1.0 - stats.nct.cdf(critical, df, ncp) + stats.nct.cdf(-critical, df, ncp))


def required_replicates(cv, fold_change, convention, design="unpaired_two_sample",
                        alpha=0.05, target_power=0.80, max_n=1000):
    """Smallest n per condition reaching `target_power`, or None within max_n.

    Returns None rather than raising when the target is unreachable, so a
    caller can report "not reachable at this CV" instead of treating an
    exhausted search as an error.
    """
    if not isinstance(target_power, (int, float)) or isinstance(target_power, bool) or not 0 < target_power < 1:
        raise ValueError("Target power must lie strictly between 0 and 1")
    for n in range(2, int(max_n) + 1):
        if power(cv, n, fold_change, convention, design, alpha) >= target_power:
            return n
    return None


def minimum_detectable_fold_change(cv, n, convention, design="unpaired_two_sample",
                                   alpha=0.05, target_power=0.80, tolerance=1e-10):
    """Smallest enhancement ratio detectable with `target_power` at size n.

    This is the figure to report when a design cannot reach its target effect:
    it says what the experiment can actually resolve, instead of implying the
    target was achievable.
    """
    if not isinstance(target_power, (int, float)) or isinstance(target_power, bool) or not 0 < target_power < 1:
        raise ValueError("Target power must lie strictly between 0 and 1")
    sd = log_scale_sd(cv, convention)
    se, df = _standard_error(sd, n, design)
    critical = stats.t.ppf(1.0 - alpha / 2.0, df)
    # Power rises monotonically in the log effect, so bisect on it. The upper
    # bracket is grown rather than fixed so that extreme CVs stay solvable.
    low, high = 0.0, max(1.0, 10.0 * se)
    while 1.0 - stats.nct.cdf(critical, df, high / se) < target_power:
        high *= 2.0
        if high > 1e6:
            raise ValueError("Target power is unreachable at this dispersion and sample size")
    while high - low > tolerance:
        mid = (low + high) / 2.0
        if 1.0 - stats.nct.cdf(critical, df, mid / se) < target_power:
            low = mid
        else:
            high = mid
    return float(math.exp((low + high) / 2.0))


@dataclass(frozen=True)
class PowerAssessment:
    """One design's power and resolution against one target effect."""
    cv: float
    replicates: int
    fold_change_target: float
    dispersion_convention: str
    design: str
    alpha: float
    target_power: float
    log_scale_sd: float
    power_at_target: float
    minimum_detectable_fold_change: float
    required_replicates_for_target_power: int | None
    target_reachable_at_this_size: bool
    no_claim: str = (
        "Planning arithmetic from an assumed CV. Establishes no stability, "
        "translation or expression benefit, and measures nothing."
    )

    def to_dict(self):
        return asdict(self)


def assess(cv, replicates, fold_change, convention, design="unpaired_two_sample",
           alpha=0.05, target_power=0.80):
    """Bundle the figures a design decision needs, including the honest resolution."""
    achieved = power(cv, replicates, fold_change, convention, design, alpha)
    mde = minimum_detectable_fold_change(cv, replicates, convention, design, alpha, target_power)
    return PowerAssessment(
        cv=float(cv),
        replicates=int(replicates),
        fold_change_target=float(fold_change),
        dispersion_convention=convention,
        design=design,
        alpha=float(alpha),
        target_power=float(target_power),
        log_scale_sd=float(log_scale_sd(cv, convention)),
        power_at_target=achieved,
        minimum_detectable_fold_change=mde,
        required_replicates_for_target_power=required_replicates(
            cv, fold_change, convention, design, alpha, target_power),
        # The design is adequate only if it both reaches target power on the
        # target effect and resolves an effect no larger than that target.
        target_reachable_at_this_size=bool(achieved >= target_power and mde <= fold_change),
    )
