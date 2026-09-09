"""Purpose: record provider answers and compare replay and host twins.

Guarantees: the public testing contracts survive the package partition
[tested: test_the_prolog_twin_is_checked_against_its_reference; commit=WORKTREE].
"""

from __future__ import annotations

from types import GeneratorType

from metta._atoms.factories import (
    Expression,
    Symbol,
    _encode,
)
from metta._atoms.factories import parse as atoms_parse
from metta._faces.space import Space
from metta.foreign import (
    SpaceProvider,
    _candidates_from_matcher,
)


class _Recording:
    """A provider proxied with an append-only log of its answers."""

    def __init__(self, provider):
        self._provider = provider
        self.log = []

    def __getattr__(self, name):
        return getattr(self._provider, name)

    def atoms(self):
        collected = list(self._provider.atoms())
        self.log.append(("atoms", None, [str(a) for a in collected]))
        yield from collected

    def match(self, pattern, *, limit=None):
        collected = list(_candidates_from_matcher(self._provider, pattern, limit))
        self.log.append(("match", str(pattern), [str(a) for a in collected]))
        yield from collected


class _Replayer(SpaceProvider):
    """Serves exactly what the log recorded, reparsed from its text, so a
    log written in one process replays in another; an unseen query is
    loud.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, log):
        self._log = list(log)

    def _serve(self, kind, key):
        for entry_kind, entry_key, answers in self._log:
            if entry_kind == kind and entry_key == key:
                return answers
        msg = (
            f"the replay log holds no {kind} entry for {key!r}: the "
            f"recorded run never asked this, so replaying it would "
            f"invent an answer"
        )
        raise AssertionError(msg)

    def atoms(self):
        for text in self._serve("atoms", None):
            yield atoms_parse(text)

    def match(self, pattern, *, limit=None):
        answers = self._serve("match", str(pattern))
        if limit is not None:
            answers = answers[:limit]
        for text in answers:
            yield atoms_parse(text)


def record_replay(provider):
    """Wrap a provider so its answers append to a log, with the replayer.

    The CakeML-oracle shape for host-stateful contexts: an append-only
    log makes a nondeterministic context's run replayable, and the
    differential replays the log instead of demanding a determinism the
    world does not have. Returns (recording, replay) where `recording`
    stands in for the provider and `replay()` builds a provider serving
    the log verbatim.
    """
    recording = _Recording(provider)
    return recording, lambda: _Replayer(recording.log)


# The parameter name is public API, older than the patterns() strategy.
def check_replay(provider, patterns) -> list[str]:  # pylint: disable=redefined-outer-name
    """The ec_determ lane: for a fixed host state, evaluation is a
    function. Each pattern is matched live and recorded, then the log's
    replay must serve byte-identical answers, which is what makes a
    recorded session a differential oracle for a backend nobody can
    re-run.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    recording, replay = record_replay(provider)
    ran = []
    for pattern in patterns:
        live = [str(a) for a in recording.match(pattern)]
        replayed = [str(a) for a in replay().match(pattern)]
        if replayed != live:
            msg = (
                f"replaying {pattern!r} answered {replayed!r} where the "
                f"log holds {live!r}; the log is append-only and the "
                f"replayer serves it verbatim, so this divergence is the "
                f"harness's own bug"
            )
            raise AssertionError(msg)
        ran.append(f"replay: {pattern!s} serves {len(live)} answer(s) verbatim")
    return ran


def check_minted_handles(provider, registered=()) -> list[str]:
    """The engine-minted-handles law: space identities are the engine's to
    mint, and a backend answers INTO spaces, never fabricates one.

    Every &-headed symbol in the provider's answers must be a space the
    engine registered; a fabricated one is the reference nobody can
    resolve, cheap to refuse now and expensive to chase after a program
    stores it. `registered` names the spaces this provider may mention.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    known = {str(name) for name in registered}
    minted = [
        f"{symbol} in {atom}"
        for atom in provider.atoms()
        for symbol in _space_symbols(_encode(atom))
        if symbol not in known
    ]
    if minted:
        msg = (
            f"{type(provider).__name__} answers mention space identities "
            f"the engine never minted: {', '.join(sorted(set(minted)))}. "
            f"A backend answers into spaces; the engine mints their "
            f"identities. Pass registered= if these are real registered "
            f"spaces"
        )
        raise AssertionError(msg)
    return ["minted-handles: every space identity in the answers is the engine's"]


def _space_symbols(atom):
    if isinstance(atom, Space):
        yield str(atom.name)
    elif isinstance(atom, Symbol) and atom.name.startswith("&"):
        yield atom.name
    elif isinstance(atom, Expression):
        for child in atom.children:
            yield from _space_symbols(child)

def _comparable(value):
    """An engine answer and a twin answer in one shape.

    Encoding is the public boundary's normalization: atoms stay atoms, Python
    sequences become expressions, and scalar species stay distinct groundings.
    """
    return _encode(value)


def _twin_answers(defined, arguments) -> list:
    """The Python twin's answers, one or many, in engine order."""
    answered = defined.py(*arguments)
    if isinstance(answered, GeneratorType):
        return [_comparable(item) for item in answered]
    return [_comparable(answered)]


# The parameter name is public API, and it is what the caller passes:
# the cases() strategy's own answer.
def check_twin(defined, cases) -> list[str]:  # pylint: disable=redefined-outer-name
    """Prove a definition and its Python twin answer the same. Answers the
    cases run.

    `@m.define` keeps the original Python reachable as `.py`, and
    `@m.define(prolog=...)` keeps it when the fast side is written in
    Prolog instead. Either way the pair is a differential oracle, and this
    runs it:

        from metta import testing

        def test_the_fast_one_still_agrees():
            testing.check_twin(vec_dot, [((1, 2), (3, 4)), ((0,), (9,))])

    `cases` is an iterable of argument tuples. Drive it with hypothesis for
    a real sweep; `metta.testing` exports the strategies the library fuzzes
    itself with.

    A generator twin is compared answer by answer in order, since a
    generator compiles to nondeterminism and order is part of the answer. A
    twin that RAISES on a case requires the engine to answer nothing for
    it: a reference that has no answer and a fast side that invents one is
    the disagreement most worth catching.

    Raises AssertionError on the first case where they differ, naming the
    case and both answers.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    ran: list[str] = []
    for case in cases:
        arguments = tuple(case)
        engine = [_comparable(answer) for answer in defined(*arguments)]
        try:
            twin = _twin_answers(defined, arguments)
        except Exception as refused:
            if engine:
                msg = (
                    f"{defined.name}{arguments!r}: the Python twin raised "
                    f"{type(refused).__name__}: {refused}, so the reference has no "
                    f"answer, but the engine answered {engine!r}"
                )
                raise AssertionError(msg) from refused
            ran.append(f"{defined.name}{arguments!r}: neither answers")
            continue
        if engine != twin:
            msg = (
                f"{defined.name}{arguments!r}: the engine answered {engine!r} and "
                f"the Python twin answered {twin!r}. One of the two is wrong, and "
                f"the twin is the readable one."
            )
            raise AssertionError(msg)
        ran.append(f"{defined.name}{arguments!r}: {engine!r}")
    return ran
