"""Purpose: hypothesis strategies for property-testing code built on this
library, the pandas.testing reading: the exact generators the library's own
suite fuzzes itself with, exported, so user operations, translators and
spaces get tested against atoms the engine actually reads back. The
filters encode engine truths worth not rediscovering: which characters the
tokeniser reads back whole, that true/false ARE the boolean atoms so their
symbol spellings canonicalize, and that `_` is the anonymous variable,
fresh at every occurrence.

The conformance surfaces live here too, one rung per audience:
check_space_provider and check_codec run in process against an author's own
object, SpaceComplianceSuite and GatewayComplianceSuite are pytest classes
that run the engine's own expectations against a provider or a URL.
Guarantees:
  - a repeated source's two enumerations are compared up to variable
    renaming, because a stored variable's engine name is a stack offset that
    moves with anything else the process does [tested:
    test_overlay_passes_the_conformance_kit; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - check_space_provider holds match soundness and exact pushdown claims
    to the whole pattern family of every stored atom, ground, opened and
    repeated-variable, judged by two-way unifiability [tested:
    test_a_repeated_variable_liar_is_caught_by_the_folded_pattern,
    test_a_ground_only_matcher_is_caught_by_the_open_pattern;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321].
  - check_twin consumes a Defined call's eager answer list exactly once
    [tested: test_the_prolog_twin_is_checked_against_its_reference;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321].
  - minted-space conformance recognizes decoded Space handles in provider
    answers [tested: test_fabricated_space_identities_are_refused;
    commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - numpy_scalars generates non-primitive scalar objects whose identity and
    numeric dispatch survive an engine round trip [tested:
    test_numpy_scalar_strategy_round_trips_through_the_engine;
    commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f]
  - from_pattern generates ground substitutions, preserving repeated named
    variables while drawing anonymous occurrences independently [tested:
    test_from_pattern_generates_ground_instances_without_losing_aliases and
    test_from_pattern_draws_anonymous_occurrences_independently;
    commit=5750e8fe84d8e933c1b5ef5d08c801846c8e5eb8]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from types import GeneratorType

from ._codec_kit import CodecDriver, check_codec, codec_corpus, codec_plan
from ._library import lib
from ._optional import require_module
from ._space import Space
from .atoms import Atom, Expression, Grounded, S, Symbol, Variable, _alpha_eq, _encode
from .atoms import parse as atoms_parse
from .benchmarking import (
    CPU_SECONDS,
    INSTRUCTIONS,
    BenchmarkBaseline,
    CounterRuns,
    Metric,
    benchmark_case,
    benchmark_counter_slope,
    count_atoms,
    measure_counters,
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
    "CPU_SECONDS",
    "INSTRUCTIONS",
    "BenchmarkBaseline",
    "CodecDriver",
    "CounterRuns",
    "GatewayComplianceSuite",  # noqa: F822  resolved by __getattr__ below, PEP 562
    "Metric",
    "SpaceComplianceSuite",  # noqa: F822  resolved by __getattr__ below, PEP 562
    "atoms",
    "benchmark_case",
    "benchmark_counter_slope",
    "check_codec",
    "check_minted_handles",
    "check_replay",
    "check_space_provider",
    "check_twin",
    "codec_corpus",
    "codec_plan",
    "count_atoms",
    "expressions",
    "from_pattern",
    "ground_atoms",
    "grounded",
    "measure_counters",
    "measure_instructions",
    "names",
    "numbers",
    "numpy_scalars",
    "patterns",
    "record_replay",
    "symbols",
    "texts",
    "variables",
]


def __getattr__(name: str):
    """SpaceComplianceSuite on demand.

    It is a pytest class, so importing it needs pytest at class-definition
    time, and `import metta.testing` for the hypothesis strategies must not.
    PEP 562 is what keeps both true: the name is in __all__ and resolves on
    first use, raising the installation guidance if pytest is not there.
    """
    if name == "SpaceComplianceSuite":
        from ._compliance import SpaceComplianceSuite  # noqa: PLC0415

        return SpaceComplianceSuite
    if name == "GatewayComplianceSuite":
        from ._gateway_compliance import GatewayComplianceSuite  # noqa: PLC0415

        return GatewayComplianceSuite
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def _st():
    hypothesis = require_module(
        "hypothesis",
        "metta.testing generates atoms with hypothesis, which is not installed; "
        "install pymetta[test]",
    )
    return hypothesis.strategies


def names():
    """Symbol and variable names MeTTa's tokeniser reads back whole: no
    whitespace, parens or quotes, none of the characters that mean
    something else at the front, and never the boolean spellings (the
    engine holds its booleans as those very atoms, so True and true are
    one term there and a round trip canonicalizes) or the anonymous `_`
    (fresh at every occurrence by contract, so it never shares).
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
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
    """Symbol atoms with engine-readable names."""
    return names().map(Symbol)


def variables():
    """Variable atoms with engine-readable names."""
    return names().map(Variable)


def numbers():
    """Numbers the engine's printer round-trips: integers within the
    tagged-integer range, floats without NaN (never compares equal) or
    infinity (prints as a symbol), both printer limits, not carried bugs.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    st = _st()
    return st.one_of(
        st.integers(min_value=-(2**62), max_value=2**62),
        st.floats(allow_nan=False, allow_infinity=False, width=64),
    )


def numpy_scalars():
    """Generate NumPy integer and real scalar values.

    These retain identity while MeTTa accepts them as Number operands and
    dispatches through Python operators.

    NumPy is optional. Install ``pymetta[arrays,test]`` before requesting this
    strategy.
    """
    st = _st()
    np = require_module(
        "numpy",
        "metta.testing.numpy_scalars requires numpy; install pymetta[arrays,test]",
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
        numbers().map(Grounded),
        st.booleans().map(Grounded),
        texts().map(Grounded),
    )


def atoms(max_leaves: int = 8, *, ground: bool = False):
    """Whole atoms: symbols, variables (unless ground=True), grounded
    values, and expressions recursively over all of them; max_leaves is
    hypothesis's own size knob for the recursion.

        from hypothesis import given
        from metta import testing

        @given(testing.atoms())
        def test_my_translator_round_trips(atom):
            assert decode(encode(atom)) == atom
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    st = _st()
    leaves = [symbols(), grounded()]
    if not ground:
        leaves.insert(1, variables())
    return st.recursive(
        st.one_of(*leaves),
        lambda inner: st.lists(inner, max_size=4).map(Expression),
        max_leaves=max_leaves,
    )


def expressions(max_leaves: int = 8, *, ground: bool = False):
    """Non-empty expression-rooted atoms, the shape spaces store."""
    st = _st()
    return st.lists(atoms(max_leaves, ground=ground), min_size=1, max_size=4).map(Expression)


def ground_atoms(max_leaves: int = 8):
    """Atoms carrying no variables: what a store holds after matching.
    atoms(ground=True) under the name provider fuzzing reaches for.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return atoms(max_leaves, ground=True)


def patterns(max_leaves: int = 8):
    """Expression-rooted atoms guaranteed to carry at least one variable:
    the query side of match, built rather than filtered so hypothesis
    never discards an example.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    st = _st()

    def weave(parts):
        before, variable, after = parts
        return Expression([*before, variable, *after])

    return st.tuples(
        st.lists(atoms(max_leaves, ground=False), max_size=2),
        variables(),
        st.lists(atoms(max_leaves, ground=False), max_size=2),
    ).map(weave)


def from_pattern(pattern, max_leaves: int = 8):
    """Generate ground instances of ``pattern`` by consistent substitution.

    Repeated named variables share one draw. Each anonymous ``V._`` occurrence
    receives its own draw, matching the engine's non-binding anonymous law.
    """
    st = _st()
    term = _encode(pattern)
    values = ground_atoms(max_leaves)
    variable_names = tuple(name for name in term.vars if name != "_")

    @st.composite
    def instances(draw):
        bindings = {name: draw(values) for name in variable_names}

        def instantiate(atom):
            if not isinstance(atom, Variable):
                return atom
            if atom.name == "_":
                return draw(values)
            return bindings[atom.name]

        return term.map(instantiate)

    return instances()


# ------------------------------------------------------ conformance for seams


def check_space_provider(provider, *, atoms_to_store=None, source="repeated") -> list[str]:
    """Prove a SpaceProvider before its users find out. Answers the checks run.

    The platform ships the conformance suite for its own extension points,
    which is the CSI sanity suite's reading, and JDBC's, and pytest's own
    `pytester`. Without it a downstream library learns its provider is wrong
    from a bug report.

        from metta import testing

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

    THE DOOR IS UNIVERSAL: a provider is any foreign substrate, not only a
    Python object, and every substrate sits behind the space seam. Handed a
    ``Space`` handle, this runs the engine's own checker
    (lib/lib_conformance/lib_conformance.pl's ``check-space-provider``), which holds the
    same laws — capability reachability, the match pattern family, the
    declared source discipline, the canary round trip, the pushdown claim —
    asked through the seam, so a provider written in Prolog, C, or anything
    else is held to one contract. The object form stays the
    pre-registration half for Python authors; ``source=`` applies to it
    alone, because a registered space carries its declared ``(source ...)``
    class and the engine checker reads that instead of trusting a claim.
    """
    if isinstance(provider, Space):
        return _check_space_through_the_seam(provider)
    if source not in ("linear", "repeated", "peek"):
        msg = f"source is linear, repeated or peek, not {source!r}"
        raise ValueError(msg)
    name = type(provider).__name__
    if not isinstance(provider, SpaceProvider):
        msg = (
            f"{name} is not a SpaceProvider, and it is not a Space handle: "
            f"pass the provider object for the pre-registration half, or "
            f"the registered space's handle to run the engine's own checker "
            f"through the seam, whatever the provider's substrate"
        )
        raise AssertionError(msg)  # noqa: TRY004  -- the harness is checking its own invariant, so AssertionError is the intended contract
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
            msg = (
                f"{name} cannot add, so atoms_to_store has nothing to store "
                f"through; pre-load the provider yourself and omit it"
            )
            raise AssertionError(msg)
        for atom in atoms_to_store:
            adder(atom)
    stored = list(provider.atoms())
    again = sorted(_renamed_apart(atom) for atom in provider.atoms())
    if again != sorted(_renamed_apart(atom) for atom in stored):
        msg = (
            f"{name} declared a {source} source and its second enumeration "
            f"disagrees with the first: a {source} source re-enumerates "
            f"identically, so this object is linear and should be declared "
            f"(source ... linear), where a second consumption is a loud "
            f"error instead of a silently different answer"
        )
        raise AssertionError(msg)
    return [
        *ran,
        f"source: {source}, two enumerations agree",
        *_check_round_trip(name, atoms_to_store, stored),
        *_check_match_contract(provider, name, stored),
        *_check_pushdown_claim(provider, name, stored),
    ]


def _check_space_through_the_seam(space: Space) -> list[str]:
    """The engine's checker, reached from the handle: lib.conformance is
    imported into a scratch sibling of the space's own context, so the
    subject space is inspected and never touched, and the answers cross
    back as the check strings the Prolog kit reports.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    # The with-block drops the scratch on exit. Left undropped, the kit's
    # anonymous space and its imported conformance library outlived every
    # call in the process, one leaked space per kit invocation. The handle
    # is bound before entry because ``+=`` rebinds its target, and a
    # rebound with-target is the PLW2901 defect class.
    scratch = space.metta.space()
    with scratch:
        scratch += lib.conformance
        (answers,) = scratch.answers(S.check_space_provider(space))
        return [
            str(finding.value) if isinstance(finding, Grounded) else str(finding)
            for finding in answers
        ]


def _check_round_trip(name: str, atoms_to_store, stored) -> list[str]:
    """The lens literature's GetPut law wearing MeTTa clothes: add then
    enumerate is identity on the stored atom, up to variable renaming,
    because stored data keeps its literal atoms. A store that normalizes
    or mangles fails here naming the atom, instead of answering a
    different atom in production.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if atoms_to_store is None:
        return []
    for atom in atoms_to_store:
        if not any(_alpha_eq(atom, held) for held in stored):
            msg = (
                f"{name} stored {atom} and its enumeration does not answer "
                f"it back: add then enumerate must be identity on the "
                f"stored atom, up to variable renaming, because stored "
                f"data keeps its literal atoms. The store answered "
                f"{[str(held) for held in stored]}"
            )
            raise AssertionError(msg)
    return [f"round-trip: {len(list(atoms_to_store))} stored atoms recovered intact"]


def _check_declared_capabilities(provider, name: str) -> list[str]:
    """Every capability the provider declares has a method behind it."""
    ran: list[str] = []
    for capability in ("match", "enumerate", "add", "remove", "clear", "subscribe"):
        if provider.can_run(capability):
            if not SpaceProvider.can_run(provider, capability):
                msg = (
                    f"{name}.can_run says yes to {capability} and the method is "
                    f"not there; implement it or let can_run answer for it"
                )
                raise AssertionError(msg)
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
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    yield atom
    if not isinstance(atom, Expression) or len(atom.children) < 2:
        return
    children = list(atom.children)
    positions = range(len(children))
    for index in positions:
        opened = children.copy()
        opened[index] = Variable(f"metta-check-{index}")
        yield Expression(opened)
    if len(children) > 2:
        yield Expression([children[0], *(Variable(f"metta-check-{i}") for i in positions if i)])
    for low in positions:
        for high in positions:
            if high <= low:
                continue
            folded = children.copy()
            folded[low] = folded[high] = Variable("metta-check-fold")
            yield Expression(folded)


def _unifiable(left, right) -> bool:
    """Two-way syntactic unifiability, the question the engine's own
    re-unification answers.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return _joined(left, right) is not None


#: The join exists but has no finite atom form: the pattern unifies with the
#: candidate only through a rational-tree binding, which the engine now
#: accepts (bindings are raw under the petta alignment) and which no finite
#: S-expression can spell.
_CYCLIC = object()


class _CyclicJoinError(Exception):
    """Raised by _resolve when a binding walks back into itself."""


def _joined(pattern, atom):
    """The two-way unification RESULT of pattern against atom.

    None when they do not unify, or the _CYCLIC sentinel when they unify only
    through a rational-tree binding.

    Public atoms.unify is symmetric and returns only the substitution. This
    helper instead returns the joined pattern under the engine's one binding
    law, in miniKanren's walk/unify shape: variables bind by name in one
    namespace, `_` matches anything and binds nothing, and bindings are RAW,
    exactly as metta_match_atoms/2 and the match door now bind under the
    petta alignment. A join that resolves into itself is a legal rational
    tree on the engine side but has no finite atom form here, so it comes
    back as the sentinel and the caller decides what a provider owes for it.
    Check-side variables are named metta-check-*, so a collision would need
    a stored $metta-check-* variable.
    [source: extensions/python/metta/atoms.py:unify and
    engine/spaces/bounded_matching.pl:metta_match_atoms/2; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
    """
    bindings: dict = {}
    stack = [(_encode(pattern), _encode(atom))]
    while stack:
        x, y = (_walk(term, bindings) for term in stack.pop())
        if _anonymous(x) or _anonymous(y):
            continue
        if not _unify_pair(x, y, bindings, stack):
            return None
    try:
        return _resolve(_encode(pattern), bindings, frozenset())
    except _CyclicJoinError:
        return _CYCLIC


def _resolve(term, bindings, path):
    """The term with every variable walked to its binding, recursively.

    Raises _CyclicJoinError when a binding on the current path walks back into
    itself, which is how a rational-tree join is detected without an occurs
    check at bind time.
    """
    if isinstance(term, Variable) and term.name != "_" and term.name in bindings:
        if term.name in path:
            raise _CyclicJoinError
        return _resolve(bindings[term.name], bindings, path | {term.name})
    if isinstance(term, Expression):
        return Expression(
            [_resolve(child, bindings, path) for child in term.children]
        )
    return term


def _walk(term, bindings):
    """Resolve a variable through its bindings, miniKanren's walk."""
    while isinstance(term, Variable) and term.name != "_" and term.name in bindings:
        term = bindings[term.name]
    return term


def _anonymous(term) -> bool:
    return isinstance(term, Variable) and term.name == "_"


def _unify_pair(x, y, bindings, stack) -> bool:
    """One walked pair: bind a variable RAW, descend an expression, or compare.

    A self-containing binding is legal and surfaces at resolve time as
    _CyclicJoinError.
    """
    if isinstance(x, Variable):
        if isinstance(y, Variable) and y.name == x.name:
            return True
        bindings[x.name] = y
        return True
    if isinstance(y, Variable):
        bindings[y.name] = x
        return True
    if isinstance(x, Expression) and isinstance(y, Expression):
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
            found_all = _match_or_cyclic_evidence(provider, pattern)
            if found_all is _CYCLIC:
                continue
            for found in found_all:
                if not _unifiable(pattern, found):
                    msg = (
                        f"{name}.pushdown({pattern!r}) claims exact and "
                        f"match({pattern!r}) yielded {found!r}, which does not "
                        f"unify with it. exact means every candidate you yield "
                        f"for this pattern unifies with it, so the caller may "
                        f"stop at its bound; a claim that is wrong loses "
                        f"answers"
                    )
                    raise AssertionError(msg)
    return [f"pushdown: {exact} of {checked} patterns claimed exact, and are"]


def _match_or_cyclic_evidence(provider, pattern):
    """provider.match(pattern) as a list, or the _CYCLIC sentinel it refused with.

    The door refuses a rational-tree row loudly, and that refusal is EVIDENCE, not
    absence: the wire raises it only while answering a row whose binding is
    cyclic, so the candidate exists on the engine side, where the seam's
    real consumer re-unifies natively with no wire between them. A python
    probe is the limited observer here, and the certification reads the
    refusal as the coverage it proves
    [source: website/live/remote-protocol.md, the rational-tree paragraph].
    """
    try:
        return list(provider.match(pattern))
    except Exception as error:
        if "rational-tree binding has no finite wire form" in str(error):
            return _CYCLIC
        raise


def _check_match_contract(provider, name: str, stored: list) -> list[str]:
    """Match over-approximates rather than under-approximates, over the whole
    pattern family: for every pattern a stored atom vouches for, each stored
    atom that unifies with it must be answered. Yielding extra candidates is
    always sound because the engine re-unifies; yielding fewer than unify is
    the one wrong a provider can do, and a provider that only handles ground
    patterns fails here on the first open one instead of answering empty
    sets in production.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if not stored:
        return ["match: no atoms to check the contract against"]
    if not isinstance(provider, Matcher):
        return ["match: enumeration is the candidate set, filtered by the engine"]
    checked = 0
    for atom in stored:
        for pattern in _claim_patterns(atom):
            checked += 1
            answered = _match_or_cyclic_evidence(provider, pattern)
            for entry in stored:
                joined = _joined(pattern, entry)
                if joined is None:
                    continue
                if answered is _CYCLIC:
                    # The door itself refused a rational-tree row loudly,
                    # which only happens while answering one: every entry
                    # this pattern joins is covered by that evidence.
                    continue
                if joined is _CYCLIC:
                    # The pattern reaches this entry only through a
                    # rational-tree binding: legal on the engine side, but
                    # there is no finite instantiation form, so the one
                    # answer a provider can owe for it is the stored atom
                    # itself.
                    if not any(_same_atom(found, entry) for found in answered):
                        msg = (
                            f"{name}.match({pattern!r}) did not answer "
                            f"{entry!r}, which the space holds and the "
                            f"pattern matches through a rational-tree "
                            f"binding; that join has no finite "
                            f"instantiation form, so the stored atom "
                            f"itself is the answer owed"
                        )
                        raise AssertionError(msg)
                    continue
                # A candidate vouches for the stored entry either as the
                # entry itself (an enumerate-and-filter store) or as this
                # pattern's unification result with it (a gateway that
                # answers instantiations): both preserve this pattern's
                # answer set exactly, which is what soundness is about.
                if not any(
                    _same_atom(found, entry) or _alpha_eq(found, joined) for found in answered
                ):
                    msg = (
                        f"{name}.match({pattern!r}) answered neither "
                        f"{entry!r}, which the space holds and the pattern "
                        f"matches, nor its unification result {joined!r}. A "
                        f"provider may over-approximate and may never "
                        f"under-approximate: yielding every atom is always "
                        f"correct, yielding fewer than unify is never allowed "
                        f"to be"
                    )
                    raise AssertionError(msg)
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


def _no_refusal(*_args, **_kwargs) -> None:
    """A provider without a refusal() hook says nothing extra."""


def _renamed_apart(atom) -> str:
    """One atom rendered with its variables named by first occurrence.

    A stored variable's engine name is a stack offset, so the SAME atom read
    twice prints two ways once anything has moved the stack in between, and an
    enumeration compared by printed form then reads as a store that changed
    under it. The name carries nothing else -- `_same_atom` below says so, "a
    variable's NAME does not survive storage" -- so this is what "the same
    atoms twice" means [measured 2026-08-31: a member space's
    (cmb-fact (f $_78) $_78) enumerated as $_78 and then as a different offset
    once an earlier suite had run in the same process].
    """
    renamings: dict[str, str] = {}

    def named(term):
        if not isinstance(term, Variable) or term.name == "_":
            return term
        return Variable(renamings.setdefault(term.name, f"_{len(renamings)}"))

    return str(atom.map(named)) if isinstance(atom, Atom) else str(atom)


def _same_atom(left, right) -> bool:
    """Atom equality as the engine sees it, by printed form.

    A variable's NAME does not survive storage, so comparing atoms that carry
    variables by identity fails for the wrong reason. The printed form is what
    a provider author can reason about.
    """
    return str(left) == str(right)


def _comparable(value):
    """An engine answer and a twin answer in one shape.

    A Grounded holds its Python value, an Expression and a Python sequence are both a
    tuple of comparable parts, and everything else compares as itself.
    """
    if isinstance(value, Grounded):
        return _comparable(value.value)
    if isinstance(value, Expression):
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
