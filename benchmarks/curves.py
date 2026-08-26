"""Purpose: the curve arithmetic both sized benchmark lanes share.

"Memory over sizes" and "any counter over sizes" fit their points the same way,
and this is where that sameness lives.

Three estimators live here and they answer different questions. ``least_squares``
is ordinary linear regression and is the arithmetic underneath the other two.
``power_fit`` fits ``y = a*x^b`` in log-log space and reports the exponent with
R-squared, which is what a declared-class gate compares against. ``select_model``
is google/benchmark's ``Complexity()``: least squares against each of a fixed set
of shapes with the lowest normalised RMS winning, which names a shape instead of
producing a number.

Both are needed because neither is sufficient alone. trend-prof found the same
linear cost was a defect in one program at R-squared 0.95 and not a defect in
another at 0.65, so an exponent only decides against a DECLARED expectation; and
a model name only says which of the offered shapes fits best, never whether the
best one fits well.

Assumes: sizes are positive and strictly increasing, and a caller that wants an
  exponent passes positive values, since log-log space has no other meaning.
Guarantees:
  - ``select_model`` reproduces google/benchmark's selection exactly: a
    no-intercept coefficient, RMS normalised by the mean of the observations,
    ``o1`` taken as the default best, and a strict ``<`` comparison so a tie
    keeps the earlier and simpler model
    [source: https://github.com/google/benchmark/blob/eddb0241389718a23a42db6af5f0164b6e0139af/src/complexity.cc#L81-L152;
    commit=906a4057ac57a340a3544ad909e829f851f35af3]
  - ``power_fit`` reports ``r_squared`` as None rather than a number when the
    observations do not vary, because the total sum of squares is then zero and
    every residual ratio is undefined. This is not hypothetical: one call
    against a head carrying n equations costs a flat 129 inferences at every
    size once the equations are compiled, so the whole ladder is one value
    [tested: test_curves_power_fit_reports_no_r_squared_for_a_flat_curve;
    commit=906a4057ac57a340a3544ad909e829f851f35af3]
  - the arithmetic is pure: no counter is read and no process is spawned here
    [tested: test_curves_power_fit_recovers_a_planted_exponent; commit=906a4057ac57a340a3544ad909e829f851f35af3]
Fails when: fewer than two points are supplied, which cannot determine a slope.
Decides: log-log regression for the exponent and google/benchmark's rule for the
  shape, with each lane keeping its own normalisation policy at its own call
  site rather than selecting one here through a flag.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True)
class LeastSquares:
    """An ordinary least-squares fit, plus the scale terms callers normalise by."""

    intercept: float
    slope: float
    residual: float
    mean: float
    span: float


def least_squares(xs: Sequence[float], ys: Sequence[float]) -> LeastSquares:
    """Fit ``y = intercept + slope*x`` and report the residual RMS with its scales."""
    if len(xs) != len(ys) or len(xs) < 2:
        msg = "a fit needs equally sized sequences with at least two points"
        raise ValueError(msg)
    mean_x = fmean(xs)
    mean_y = fmean(ys)
    denominator = sum((value - mean_x) ** 2 for value in xs)
    slope = (
        0.0
        if denominator == 0
        else sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
        / denominator
    )
    intercept = mean_y - slope * mean_x
    residual = math.sqrt(
        fmean((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    )
    return LeastSquares(
        intercept=intercept,
        slope=slope,
        residual=residual,
        mean=mean_y,
        span=max(ys) - min(ys),
    )


@dataclass(frozen=True)
class PowerFit:
    """``y = coefficient * size**exponent`` fitted in log-log space."""

    exponent: float
    r_squared: float | None
    coefficient: float
    pair_slopes: tuple[float, ...]


def power_fit(sizes: Sequence[int], values: Sequence[float]) -> PowerFit:
    """Fit a power law to the points and report the exponent with R-squared.

    ``pair_slopes`` is the exponent between each pair of consecutive sizes. It
    is kept because a single fitted exponent hides the direction of travel: a
    cost that is a sum of a linear and a quadratic term reads as one middling
    exponent, while the pair slopes climb toward the higher class and say so.
    """
    points = [
        (float(size), float(value))
        for size, value in zip(sizes, values, strict=True)
        if size > 0 and value > 0
    ]
    if len(points) < 2:
        msg = "a power fit needs at least two points with positive size and value"
        raise ValueError(msg)
    log_sizes = [math.log(size) for size, _ in points]
    log_values = [math.log(value) for _, value in points]
    fit = least_squares(log_sizes, log_values)
    mean_log_value = fmean(log_values)
    total = sum((value - mean_log_value) ** 2 for value in log_values)
    residual = sum(
        (value - (fit.intercept + fit.slope * size)) ** 2
        for size, value in zip(log_sizes, log_values, strict=True)
    )
    return PowerFit(
        exponent=fit.slope,
        # A flat curve has no variance to explain, so a ratio against it would
        # be a division by zero dressed up as a goodness of fit.
        r_squared=None if total == 0 else 1.0 - residual / total,
        coefficient=math.exp(fit.intercept),
        pair_slopes=tuple(
            math.log(after / before) / math.log(larger / smaller)
            for (smaller, before), (larger, after) in itertools.pairwise(points)
        ),
    )


@dataclass(frozen=True)
class Model:
    """One candidate shape, its rank among the classes, and its term in ``n``."""

    name: str
    order: int
    term: Callable[[int], float]


# The shapes google/benchmark offers, in its own order: o1 is the default best
# and the remaining five are tried against it
# [source: https://github.com/google/benchmark/blob/eddb0241389718a23a42db6af5f0164b6e0139af/src/complexity.cc#L133-L146].
# Its oLogN and oNLogN use log base two, which changes each coefficient and
# leaves every normalised RMS unchanged, since a constant factor inside the
# term is absorbed by the fitted coefficient.
STANDARD_MODELS: tuple[Model, ...] = (
    Model("constant", 0, lambda _size: 1.0),
    Model("log_n", 1, lambda size: math.log2(float(size))),
    Model("linear", 2, float),
    Model("n_log_n", 3, lambda size: float(size) * math.log2(float(size))),
    Model("quadratic", 4, lambda size: float(size) ** 2),
    Model("cubic", 5, lambda size: float(size) ** 3),
)


def select_model(
    sizes: Sequence[int],
    values: Sequence[float],
    models: Sequence[Model] = STANDARD_MODELS,
) -> tuple[str, dict[str, float]]:
    """Name the shape with the lowest normalised RMS, and report every shape's.

    This is ``MinimalLeastSq`` and its selection loop transcribed: the
    coefficient minimises the squared error of ``coef*f(n)`` with no intercept,
    and the RMS is divided by the mean of the observations so shapes measured in
    different units stay comparable.
    """
    if len(sizes) != len(values) or len(sizes) < 2:
        msg = "model selection needs equally sized sequences with at least two points"
        raise ValueError(msg)
    observations = [float(value) for value in values]
    mean = fmean(observations)
    scores: dict[str, float] = {}
    for model in models:
        terms = [model.term(size) for size in sizes]
        squared = sum(term * term for term in terms)
        coefficient = (
            0.0
            if squared == 0
            else sum(
                value * term for value, term in zip(observations, terms, strict=True)
            )
            / squared
        )
        error = math.sqrt(
            fmean(
                (value - coefficient * term) ** 2
                for value, term in zip(observations, terms, strict=True)
            )
        )
        scores[model.name] = error / mean if mean != 0 else error
    best = models[0].name
    for model in models[1:]:
        if scores[model.name] < scores[best]:
            best = model.name
    return best, scores
