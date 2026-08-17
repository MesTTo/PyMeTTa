"""Purpose: hypothesis strategies for property-testing code built on this
library, the pandas.testing reading: the exact generators the library's own
suite fuzzes itself with, exported, so user operations, translators and
spaces get tested against atoms the engine actually reads back. The
filters encode engine truths worth not rediscovering: which characters the
tokeniser reads back whole, that true/false ARE the boolean atoms so their
symbol spellings canonicalize, and that `_` is the anonymous variable,
fresh at every occurrence.
Guarantees:
  - check_space_provider holds match soundness and exact pushdown claims
    to the whole pattern family of every stored atom, ground, opened and
    repeated-variable, judged by two-way unifiability [tested 2026-08-17:
    test_a_repeated_variable_liar_is_caught_by_the_folded_pattern,
    test_a_ground_only_matcher_is_caught_by_the_open_pattern].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from types import GeneratorType

from ._optional import require_module
from .atoms import Expr, Gnd, Sym, Var, encode
from .atoms import parse as atoms_parse
from .benchmarking import (
    BenchmarkBaseline,
    benchmark_case,
    benchmark_counter_slope,
    count_atoms,
    measure_instructions,
)
from .foreign import (
    Enumerable,
    MatchClassifier,
    Matcher,
    SpaceProvider,
    _candidates_from_matcher,
    pushdown_class,
)

__all__ = [
    "BenchmarkBaseline",
    "GatewayComplianceSuite",  # noqa: F822  resolved by __getattr__ below, PEP 562
    "SpaceComplianceSuite",  # noqa: F822  resolved by __getattr__ below, PEP 562
    "atoms",
    "benchmark_case",
    "benchmark_counter_slope",
    "check_minted_handles",
    "check_replay",
    "check_space_provider",
    "check_twin",
    "count_atoms",
    "expressions",
    "grounded",
    "measure_instructions",
    "names",
    "numbers",
    "numpy_scalars",
    "record_replay",
    "symbols",
    "texts",
    "variables",
]


def __getattr__(name: str):
    """SpaceComplianceSuite on demand.

    It is a pytest class, so importing it needs pytest at class-definition
    time, and `import petta.testing` for the hypothesis strategies must not.
    PEP 562 is what keeps both true: the name is in __all__ and resolves on
    first use, raising the installation guidance if pytest is not there.
    """
    if name == "SpaceComplianceSuite":
        from ._compliance import SpaceComplianceSuite  # noqa: PLC0415

        return SpaceComplianceSuite
    if name == "GatewayComplianceSuite":
        from ._gateway_compliance import GatewayComplianceSuite  # noqa: PLC0415

        return GatewayComplianceSuite
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _st():
    hypothesis = require_module(
        "hypothesis",
        "petta.testing generates atoms with hypothesis, which is not installed; "
        "install petta[test]",
    )
    return hypothesis.strategies


def names():
    """Symbol and variable names PeTTa's tokeniser reads back whole: no
    whitespace, parens or quotes, none of the characters that mean
    something else at the front, and never the boolean spellings (the
    engine holds its booleans as those very atoms, so True and true are
    one term there and a round trip canonicalizes) or the anonymous `_`
    (fresh at every occurrence by contract, so it never shares)."""
    st = _st()
    return st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_?<>=+*"),
        min_size=1,
        max_size=12,
    ).filter(
        lambda s: (
            s[0] not in "$&-<>=+*?0123456789" and s not in ("True", "False", "true", "false", "_")
        )
    )


def symbols():
    """Sym atoms with engine-readable names."""
    return names().map(Sym)


def variables():
    """Var atoms with engine-readable names."""
    return names().map(Var)


def numbers():
    """Numbers the engine's printer round-trips: integers within the
    tagged-integer range, floats without NaN (never compares equal) or
    infinity (prints as a symbol), both printer limits, not carried bugs."""
    st = _st()
    return st.one_of(
        st.integers(min_value=-(2**62), max_value=2**62),
        st.floats(allow_nan=False, allow_infinity=False, width=64),
    )


def numpy_scalars():
    """NumPy integer and real scalar values accepted by PeTTa's Number type.

    NumPy is optional. Install ``petta[arrays,test]`` before requesting this
    strategy.
    """
    st = _st()
    np = require_module(
        "numpy",
        "petta.testing.numpy_scalars requires numpy; install petta[arrays,test]",
    )
    return st.one_of(
        st.integers(-(2**31), 2**31 - 1).map(np.int32),
        st.integers(-(2**62), 2**62).map(np.int64),
        st.floats(allow_nan=False, allow_infinity=False, width=32).map(np.float32),
        st.floats(allow_nan=False, allow_infinity=False, width=64).map(np.float64),
    )


def texts():
    """Strings as the engine stores them; NUL is the one exclusion."""
    st = _st()
    return st.text(
        alphabet=st.characters(codec="utf-8", exclude_characters="\x00"),
        max_size=20,
    )


def grounded():
    """Grounded atoms over numbers, booleans and strings."""
    st = _st()
    return st.one_of(
        numbers().map(Gnd),
        st.booleans().map(Gnd),
        texts().map(Gnd),
    )


def atoms(max_leaves: int = 8, *, ground: bool = False):
    """Whole atoms: symbols, variables (unless ground=True), grounded
    values, and expressions recursively over all of them; max_leaves is
    hypothesis's own size knob for the recursion.

        from hypothesis import given
        from petta import testing

        @given(testing.atoms())
        def test_my_translator_round_trips(atom):
            assert decode(encode(atom)) == atom
    """
    st = _st()
    leaves = [symbols(), grounded()]
    if not ground:
        leaves.insert(1, variables())
    return st.recursive(
        st.one_of(*leaves),
        lambda inner: st.lists(inner, max_size=4).map(Expr),
        max_leaves=max_leaves,
    )


def expressions(max_leaves: int = 8, *, ground: bool = False):
    """Non-empty expression-rooted atoms, the shape spaces store."""
    st = _st()
    return st.lists(atoms(max_leaves, ground=ground), min_size=1, max_size=4).map(Expr)


# ------------------------------------------------------ conformance for seams


def check_space_provider(provider, *, atoms_to_store=None, source="repeated") -> list[str]:
    """Prove a SpaceProvider before its users find out. Answers the checks run.

    The platform ships the conformance suite for its own extension points,
    which is the CSI sanity suite's reading, and JDBC's, and pytest's own
    `pytester`. Without it a downstream library learns its provider is wrong
    from a bug report.

        from petta import testing

        def test_my_provider_conforms():
            testing.check_space_provider(MyProvider(rows))

    Three things are checked, and the second is the one worth having.

    **Every declared capability is reachable.** `can_run` may say yes to an
    operation whose method is absent, which is a registration-time mistake
    that otherwise surfaces as an AttributeError inside an engine callback.

    **Match over-approximates rather than under-approximates.** The seam's
    central soundness claim is that a provider may yield more than the pattern
    asks for, because the engine keeps unification, and may never yield less.
    Every stored atom vouches for a whole pattern family, itself, each
    position opened to a variable, and repeated-variable folds, and the
    provider's answers for each are compared with a brute-force unification
    scan of `atoms()`. A provider that filters too eagerly, or that only
    handles ground patterns, or whose filter treats a repeated variable's
    occurrences independently, fails here rather than answering wrongly in
    production. An exact pushdown claim is held to the same family.

    **A refusal names itself.** An operation the provider declines raises with
    a sentence rather than failing, so a caller learns what to do instead.

    `source` names the provider's consumption discipline, matching its
    (source ...) declaration. A linear provider is one-shot, so every
    check that consumes more than once is skipped and said so; repeated
    and peek providers are enumerated twice and the two enumerations must
    agree, which is the promise those words make.

    Raises AssertionError on the first violation, naming the provider class,
    the operation and the atom.
    """
    if source not in ("linear", "repeated", "peek"):
        raise ValueError(f"source is linear, repeated or peek, not {source!r}")
    name = type(provider).__name__
    if not isinstance(provider, SpaceProvider):
        raise AssertionError(
            f"{name} is not a SpaceProvider: register_provider checks this too, "
            f"and without the base class every operation dies inside an engine "
            f"callback on a missing can_run"
        )
    ran = _check_declared_capabilities(provider, name)
    if not isinstance(provider, Enumerable):
        return ran
    if source == "linear":
        return [
            *ran,
            "source: linear, so every check that consumes twice is skipped",
        ]
    if atoms_to_store is not None:
        adder = getattr(provider, "add", None)
        if adder is None or not provider.can_run("add"):
            raise AssertionError(
                f"{name} cannot add, so atoms_to_store has nothing to store "
                f"through; pre-load the provider yourself and omit it"
            )
        for atom in atoms_to_store:
            adder(atom)
    stored = list(provider.atoms())
    again = sorted(str(atom) for atom in provider.atoms())
    if again != sorted(str(atom) for atom in stored):
        raise AssertionError(
            f"{name} declared a {source} source and its second enumeration "
            f"disagrees with the first: a {source} source re-enumerates "
            f"identically, so this object is linear and should be declared "
            f"(source ... linear), where a second consumption is a loud "
            f"error instead of a silently different answer"
        )
    return [
        *ran,
        f"source: {source}, two enumerations agree",
        *_check_round_trip(name, atoms_to_store, stored),
        *_check_match_contract(provider, name, stored),
        *_check_pushdown_claim(provider, name, stored),
    ]


def _check_round_trip(name: str, atoms_to_store, stored) -> list[str]:
    """The lens literature's GetPut law wearing MeTTa clothes: add then
    enumerate is identity on the stored atom, up to variable renaming,
    because stored data keeps its literal atoms. A store that normalizes
    or mangles fails here naming the atom, instead of answering a
    different atom in production."""
    if atoms_to_store is None:
        return []
    from .atoms import alpha_eq  # noqa: PLC0415 - alpha_eq only serves this check

    for atom in atoms_to_store:
        if not any(alpha_eq(atom, held) for held in stored):
            raise AssertionError(
                f"{name} stored {atom} and its enumeration does not answer "
                f"it back: add then enumerate must be identity on the "
                f"stored atom, up to variable renaming, because stored "
                f"data keeps its literal atoms. The store answered "
                f"{[str(held) for held in stored]}"
            )
    return [f"round-trip: {len(list(atoms_to_store))} stored atoms recovered intact"]


def _check_declared_capabilities(provider, name: str) -> list[str]:
    """Every capability the provider declares has a method behind it."""
    ran: list[str] = []
    for capability in ("match", "enumerate", "add", "remove", "clear", "subscribe"):
        if provider.can_run(capability):
            if not SpaceProvider.can_run(provider, capability):
                raise AssertionError(
                    f"{name}.can_run says yes to {capability} and the method is "
                    f"not there; implement it or let can_run answer for it"
                )
            ran.append(f"{capability}: declared")
            continue
        stated = getattr(provider, "refusal", _no_refusal)(capability)
        ran.append(
            f"{capability}: declined, with the generic wording"
            if stated is None
            else f"{capability}: declined, {stated}"
        )
    return ran


def _claim_patterns(atom):
    """The pattern family one stored atom vouches for: the atom itself, each
    position opened to a fresh variable, every argument opened at once, and
    each pair of positions folded onto ONE repeated variable.

    Ground self-match proves nothing about variables. The classic wrong
    filter treats a repeated variable's occurrences independently and
    answers (edge a b) to (edge $x $x); the folded variants catch it, and
    the open ones catch a provider that only handles ground patterns. Every
    variant is a query a caller can actually send.
    """
    yield atom
    if not isinstance(atom, Expr) or len(atom.children) < 2:
        return
    children = list(atom.children)
    positions = range(len(children))
    for index in positions:
        opened = children.copy()
        opened[index] = Var(f"petta-check-{index}")
        yield Expr(opened)
    if len(children) > 2:
        yield Expr(
            [children[0], *(Var(f"petta-check-{i}") for i in positions if i)]
        )
    for low in positions:
        for high in positions:
            if high <= low:
                continue
            folded = children.copy()
            folded[low] = folded[high] = Var("petta-check-fold")
            yield Expr(folded)


def _unifiable(left, right) -> bool:
    """Two-way syntactic unifiability, the question the engine's own
    re-unification answers.

    atoms.unify is one-way by design, so a candidate carrying variables of
    its own would be judged wrongly by it; this judges the pair the way the
    engine will, in miniKanren's walk/unify shape. Variables bind by name
    in one namespace, `_` matches anything and binds nothing, and no
    occurs check, matching SWI's default. Check-side variables are named
    petta-check-*, so a collision would need a stored $petta-check-*
    variable.
    """
    bindings: dict = {}
    stack = [(encode(left), encode(right))]
    while stack:
        x, y = (_walk(term, bindings) for term in stack.pop())
        if _anonymous(x) or _anonymous(y):
            continue
        if not _unify_pair(x, y, bindings, stack):
            return False
    return True


def _walk(term, bindings):
    """Resolve a variable through its bindings, miniKanren's walk."""
    while isinstance(term, Var) and term.name != "_" and term.name in bindings:
        term = bindings[term.name]
    return term


def _anonymous(term) -> bool:
    return isinstance(term, Var) and term.name == "_"


def _unify_pair(x, y, bindings, stack) -> bool:
    """One walked pair: bind a variable, descend an expression, or compare."""
    if isinstance(x, Var):
        if not (isinstance(y, Var) and y.name == x.name):
            bindings[x.name] = y
        return True
    if isinstance(y, Var):
        bindings[y.name] = x
        return True
    if isinstance(x, Expr) and isinstance(y, Expr):
        if len(x.children) != len(y.children):
            return False
        stack.extend(zip(x.children, y.children, strict=True))
        return True
    return bool(x == y)


def _check_pushdown_claim(provider, name: str, stored: list) -> list[str]:
    """An exact claim is true: every candidate for the pattern unifies with it.

    This is the one claim in the seam that can cost answers. Everything else a
    provider says is checked by over-approximation being sound, but "exact"
    licenses truncating at the caller's bound, and a provider that truncates
    while yielding non-matching candidates answers fewer rows than exist.
    Under-answering is the one thing the contract forbids, so the claim is
    tested against the provider's own output over the whole pattern family of
    every stored atom, ground AND open AND repeated-variable: a filter that
    is exact on ground data and treats a repeated variable's occurrences
    independently is exactly the liar the family exists to catch.
    """
    if not isinstance(provider, MatchClassifier):
        return ["pushdown: not claimed, so inexact and re-unified"]
    if not isinstance(provider, Matcher):
        return ["pushdown: claimed without a match, so nothing pushes down"]
    if not stored:
        return ["pushdown: no atoms to check the claim against"]
    exact = 0
    checked = 0
    for atom in stored:
        for pattern in _claim_patterns(atom):
            checked += 1
            if pushdown_class(provider, pattern) != "exact":
                continue
            exact += 1
            for found in provider.match(pattern):
                if not _unifiable(pattern, found):
                    raise AssertionError(
                        f"{name}.pushdown({pattern!r}) claims exact and "
                        f"match({pattern!r}) yielded {found!r}, which does not "
                        f"unify with it. exact means every candidate you yield "
                        f"for this pattern unifies with it, so the caller may "
                        f"stop at its bound; a claim that is wrong loses "
                        f"answers"
                    )
    return [f"pushdown: {exact} of {checked} patterns claimed exact, and are"]


def _check_match_contract(provider, name: str, stored: list) -> list[str]:
    """Match over-approximates rather than under-approximates, over the whole
    pattern family: for every pattern a stored atom vouches for, each stored
    atom that unifies with it must be answered. Yielding extra candidates is
    always sound because the engine re-unifies; yielding fewer than unify is
    the one wrong a provider can do, and a provider that only handles ground
    patterns fails here on the first open one instead of answering empty
    sets in production.
    """
    if not stored:
        return ["match: no atoms to check the contract against"]
    if not isinstance(provider, Matcher):
        return ["match: enumeration is the candidate set, filtered by the engine"]
    checked = 0
    for atom in stored:
        for pattern in _claim_patterns(atom):
            checked += 1
            answered = list(provider.match(pattern))
            for entry in stored:
                if not _unifiable(pattern, entry):
                    continue
                if not any(_same_atom(found, entry) for found in answered):
                    raise AssertionError(
                        f"{name}.match({pattern!r}) did not answer {entry!r}, "
                        f"which the space holds and the pattern matches. A "
                        f"provider may over-approximate and may never "
                        f"under-approximate: yielding every atom is always "
                        f"correct, yielding fewer than unify is never allowed "
                        f"to be"
                    )
    return [f"match: over-approximation holds over {checked} patterns"]


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
    loud."""

    def __init__(self, log):
        self._log = list(log)

    def _serve(self, kind, key):
        for entry_kind, entry_key, answers in self._log:
            if entry_kind == kind and entry_key == key:
                return answers
        raise AssertionError(
            f"the replay log holds no {kind} entry for {key!r}: the "
            f"recorded run never asked this, so replaying it would "
            f"invent an answer"
        )

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


def check_replay(provider, patterns) -> list[str]:
    """The ec_determ lane: for a fixed host state, evaluation is a
    function. Each pattern is matched live and recorded, then the log's
    replay must serve byte-identical answers, which is what makes a
    recorded session a differential oracle for a backend nobody can
    re-run.
    """
    recording, replay = record_replay(provider)
    ran = []
    for pattern in patterns:
        live = [str(a) for a in recording.match(pattern)]
        replayed = [str(a) for a in replay().match(pattern)]
        if replayed != live:
            raise AssertionError(
                f"replaying {pattern!r} answered {replayed!r} where the "
                f"log holds {live!r}; the log is append-only and the "
                f"replayer serves it verbatim, so this divergence is the "
                f"harness's own bug"
            )
        ran.append(f"replay: {pattern!s} serves {len(live)} answer(s) verbatim")
    return ran


def check_minted_handles(provider, registered=()) -> list[str]:
    """The engine-minted-handles law: space identities are the engine's to
    mint, and a backend answers INTO spaces, never fabricates one.

    Every &-headed symbol in the provider's answers must be a space the
    engine registered; a fabricated one is the reference nobody can
    resolve, cheap to refuse now and expensive to chase after a program
    stores it. `registered` names the spaces this provider may mention.
    """
    known = {str(name) for name in registered}
    minted = []
    for atom in provider.atoms():
        for symbol in _space_symbols(encode(atom)):
            if symbol not in known:
                minted.append(f"{symbol} in {atom}")
    if minted:
        raise AssertionError(
            f"{type(provider).__name__} answers mention space identities "
            f"the engine never minted: {', '.join(sorted(set(minted)))}. "
            f"A backend answers into spaces; the engine mints their "
            f"identities. Pass registered= if these are real registered "
            f"spaces"
        )
    return ["minted-handles: every space identity in the answers is the engine's"]


def _space_symbols(atom):
    if isinstance(atom, Sym) and atom.name.startswith("&"):
        yield atom.name
    elif isinstance(atom, Expr):
        for child in atom.children:
            yield from _space_symbols(child)


def _no_refusal(*_args, **_kwargs) -> None:
    """A provider without a refusal() hook says nothing extra."""


def _same_atom(left, right) -> bool:
    """Atom equality as the engine sees it, by printed form.

    A variable's NAME does not survive storage, so comparing atoms that carry
    variables by identity fails for the wrong reason. The printed form is what
    a provider author can reason about.
    """
    return str(left) == str(right)


def _comparable(value):
    """An engine answer and a twin answer in one shape.

    A Gnd holds its Python value, an Expr and a Python sequence are both a
    tuple of comparable parts, and everything else compares as itself.
    """
    if isinstance(value, Gnd):
        return _comparable(value.value)
    if isinstance(value, Expr):
        return tuple(_comparable(child) for child in value)
    if isinstance(value, (list, tuple)):
        return tuple(_comparable(item) for item in value)
    return value


def _twin_answers(defined, arguments) -> list:
    """The Python twin's answers, one or many, in engine order."""
    answered = defined.py(*arguments)
    if isinstance(answered, GeneratorType):
        return [_comparable(item) for item in answered]
    return [_comparable(answered)]


def check_twin(defined, cases) -> list[str]:
    """Prove a definition and its Python twin answer the same. Answers the
    cases run.

    `@m.define` keeps the original Python reachable as `.py`, and
    `@m.define(prolog=...)` keeps it when the fast side is written in
    Prolog instead. Either way the pair is a differential oracle, and this
    runs it:

        from petta import testing

        def test_the_fast_one_still_agrees():
            testing.check_twin(vec_dot, [((1, 2), (3, 4)), ((0,), (9,))])

    `cases` is an iterable of argument tuples. Drive it with hypothesis for
    a real sweep; `petta.testing` exports the strategies the library fuzzes
    itself with.

    A generator twin is compared answer by answer in order, since a
    generator compiles to nondeterminism and order is part of the answer. A
    twin that RAISES on a case requires the engine to answer nothing for
    it: a reference that has no answer and a fast side that invents one is
    the disagreement most worth catching.

    Raises AssertionError on the first case where they differ, naming the
    case and both answers.
    """
    ran: list[str] = []
    for case in cases:
        arguments = tuple(case)
        engine = [_comparable(answer) for answer in defined.space.eval(defined(*arguments))]
        try:
            twin = _twin_answers(defined, arguments)
        except Exception as refused:
            if engine:
                raise AssertionError(
                    f"{defined.name}{arguments!r}: the Python twin raised "
                    f"{type(refused).__name__}: {refused}, so the reference has no "
                    f"answer, but the engine answered {engine!r}"
                ) from refused
            ran.append(f"{defined.name}{arguments!r}: neither answers")
            continue
        if engine != twin:
            raise AssertionError(
                f"{defined.name}{arguments!r}: the engine answered {engine!r} and "
                f"the Python twin answered {twin!r}. One of the two is wrong, and "
                f"the twin is the readable one."
            )
        ran.append(f"{defined.name}{arguments!r}: {engine!r}")
    return ran
