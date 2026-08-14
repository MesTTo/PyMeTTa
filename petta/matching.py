"""Purpose: custom matchers as first-class citizens. A matcher is a MeTTa
function with two modes, the shape py-field proved: with the candidate
bound it SCORES, answering (score candidate) when the score clears the
threshold; with the candidate unbound it GENERATES, best first. Both modes
answer (score value) pairs, the same shape lib_soft's soft-match and the
knn retrieval answer, so every matcher's results feed lib_measure:
ws-softmax over any matcher is attention through that matcher's notion of
closeness. matcher() builds one from plain Python functions;
install_fuzzy() ships lexical closeness over difflib, and
EmbeddingStore.matcher() (petta.arrays) is the semantic instance. The
composition rule is mettabase's semmatch design: matchers compose through
ordinary MeTTa evaluation and nondeterminism, structural match first or
last or in between, never through new syntax.
Guarantees:
  - regex lexicons choose exactly one source mode, iterable or factory
    [tested test_regex_lexicon_refuses_ambiguous_source]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import difflib
import math
import re
from collections.abc import Callable, Iterable
from functools import lru_cache
from typing import Any

from .atoms import Gnd, Sym, Var, decode, expr
from .errors import PettaError

__all__ = ["install_fuzzy", "install_regex", "matcher", "text_of"]


def text_of(value: Any) -> str:
    """A candidate as comparable text: symbols by name, strings as
    themselves, everything else by its printed form."""
    if isinstance(value, Sym):
        return value.name
    if isinstance(value, Gnd) and isinstance(value.value, str):
        return value.value
    return str(value)


def matcher(
    m,
    name: str,
    *,
    score: Callable[[Any, Any], float],
    generate: Callable[[Any], Iterable[tuple[Any, float]]] | None = None,
    threshold: float = 0.0,
) -> str:
    """Register a two-mode matcher under one MeTTa name.

        petta.matching.matcher(m, "sounds-like", score=phonetic_similarity)
        m.run('!(sounds-like "smith" "smyth")')     # (0.83 "smyth")

    score(query, candidate) answers the degree in [0, 1]. generate(query)
    yields (candidate, degree) pairs best first, and is what the unbound
    mode runs; a matcher without one refuses that mode by saying so.
    Answers clear the threshold or answer nothing, MeTTa's own way of
    saying no.
    """

    threshold = _bounded_degree(threshold, f"matcher {name!r} threshold")

    def run(query, candidate=None):
        if candidate is None or isinstance(candidate, Var):
            if generate is None:
                raise PettaError(
                    f"({name} $q $unbound) generates candidates, and this "
                    f"matcher has no generator; pass generate= to serve it"
                )
            for value, degree in generate(_plain(query)):
                degree = _bounded_degree(degree, f"matcher {name!r} generated degree")
                if degree >= threshold:
                    yield expr(degree, value)
            return
        degree = _bounded_degree(
            score(_plain(query), _plain(candidate)),
            f"matcher {name!r} score degree",
        )
        if degree >= threshold:
            yield expr(degree, candidate)

    m.register_op(run, name=name, typed=False, pass_atoms=True)
    return name


def _bounded_degree(value: Any, boundary: str) -> float:
    try:
        degree = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{boundary} must be a finite number in [0, 1], got {value!r}") from None
    if not math.isfinite(degree) or not 0.0 <= degree <= 1.0:
        raise ValueError(f"{boundary} must be finite and in [0, 1], got {degree!r}")
    return degree


def _plain(value: Any) -> Any:
    return decode(value) if isinstance(value, Gnd) else value


def install_fuzzy(m, name: str = "fuzmatch", threshold: float = 0.0) -> str:
    """Lexical closeness as a matcher: difflib's ratio over the printed
    forms, the standard library's own sequence similarity.

        m.run('!(fuzmatch "clase" "class")')        # (0.8 "class")
    """

    def ratio(query: Any, candidate: Any) -> float:
        return difflib.SequenceMatcher(None, text_of(query), text_of(candidate)).ratio()

    return matcher(m, name, score=ratio, threshold=threshold)


def install_regex(
    m,
    name: str = "rx-match",
    lexicon: Iterable[Any] | Callable[[], Iterable[Any]] | None = None,
) -> str:
    """Regex as a matcher: the crisp lexical modality beside fuzzy and
    semantic. The query IS the pattern; a candidate scores one exactly
    when the pattern matches its printed form (search semantics, the
    re-match reading), and the unbound mode generates every lexicon
    entry the pattern accepts. `lexicon` is an iterable, or a
    zero-argument callable answered fresh per generation for live
    sources, a space read included.

        matching.install_regex(m, lexicon=["alpha", "beta", "abbey"])
        m.run('!(collapse (rx-match "^a" $w))')
        # ((1.0 "alpha") (1.0 "abbey"))

    Patterns compile once and cache; scoring runs Python's re inside
    the callback, so no boundary is re-crossed per candidate, and
    inline flags like (?i) work. The pattern language is Python's,
    which agrees with lib_regex's PCRE2 on this searching subset.
    """

    @lru_cache(maxsize=256)
    def compiled(pattern: str):
        return re.compile(pattern)

    def hit(query: Any, candidate: Any) -> float:
        return 1.0 if compiled(text_of(query)).search(text_of(candidate)) else 0.0

    def generate(query: Any):
        if lexicon is None:
            raise RuntimeError("regex generation requires a lexicon")
        if isinstance(lexicon, Iterable):
            if callable(lexicon):
                raise TypeError(
                    "a regex lexicon cannot be both callable and iterable; "
                    "pass either its items or a zero-argument factory"
                )
            source = lexicon
        else:
            source = lexicon()
        pattern = compiled(text_of(query))
        for candidate in source:
            if pattern.search(text_of(candidate)):
                yield candidate, 1.0

    return matcher(
        m,
        name,
        score=hit,
        generate=None if lexicon is None else generate,
        threshold=1.0,
    )
