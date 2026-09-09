"""Purpose: check provider contracts and assert engine answer bags.

Guarantees: the public testing contracts survive the package partition
[tested: test_a_repeated_variable_liar_is_caught_by_the_folded_pattern; commit=WORKTREE].
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    S,
    Symbol,
    Variable,
    _alpha_eq,
    _encode,
)
from metta._atoms.library import lib
from metta._binding.runtime import runtime as _runtime
from metta._errors.errors import EngineError, Remedy, refusing
from metta._faces.space import Space
from metta.foreign import (
    Enumerable,
    MatchClassifier,
    Matcher,
    SpaceProvider,
    pushdown_class,
)

# ------------------------------------------ conformance for provider interfaces


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

    **Match over-approximates rather than under-approximates.** The provider
    contract's central soundness claim is that a provider may yield more than
    the pattern asks for, because the engine keeps unification, and may never
    yield less.
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

    THE CHECK IS UNIVERSAL: a provider is any foreign substrate, not only a
    Python object, and every substrate implements the space-provider protocol.
    Handed a ``Space`` handle, this runs the engine's own checker
    (lib/lib_conformance/lib_conformance.pl's ``check-space-provider``), which holds the
    same laws (capability reachability, the match pattern family, the
    declared source discipline, the canary round trip, the pushdown claim)
    asked through that protocol, so a provider written in Prolog, C, or anything
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
            f"the registered space's handle to run the engine's own checker, "
            f"whatever the provider's substrate"
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
    exactly as metta_match_atoms/2 and the match method now bind under the
    petta alignment. A join that resolves into itself is a legal rational
    tree on the engine side but has no finite atom form here, so it comes
    back as the sentinel and the caller decides what a provider owes for it.
    Check-side variables are named metta-check-*, so a collision would need
    a stored $metta-check-* variable.
    [source: extensions/python/metta/_atoms/factories.py:552 and
    engine/spaces/bounded_matching.pl:metta_match_atoms/2; commit=WORKTREE]
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

    This is the one claim in the provider contract that can cost answers.
    Everything else a provider says is checked by over-approximation being
    sound, but "exact" licenses truncating at the caller's bound, and a provider
    that truncates while yielding non-matching candidates answers fewer rows
    than exist.
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

    The method refuses a rational-tree row loudly, and that refusal is EVIDENCE, not
    absence: the wire raises it only while answering a row whose binding is
    cyclic, so the candidate exists on the engine side, where the provider contract's
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
                    # The method itself refused a rational-tree row loudly,
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
    """Atom equality as the engine sees it, by printed form RENAMED APART.

    A variable's NAME does not survive storage, so comparing atoms that carry
    variables by identity fails for the wrong reason. The printed form is what
    a provider author can reason about, and `_renamed_apart` above is what
    makes that form answerable: the same stored atom crossing twice is named
    twice, so the raw spelling differed for a variable that never changed and
    a sound provider read as an unsound one. Renaming by first occurrence is
    the same normalisation the enumeration check already applies; for a ground
    atom it changes nothing.
    """
    return _renamed_apart(left) == _renamed_apart(right)

# ----------------------------------------------- assertions over answer bags
#
# The Python face of the engine's own two assertion doors, and deliberately
# nothing more than a face. What is NOT here is a second multiset difference:
# `subtraction-atom` removes by the engine's standard-order equality, so two
# separately named variables are two answers there where Python's
# `Variable("x") == Variable("x")` is one, and a `Counter` written here would
# agree with the MeTTa forms only by review. Both bags cross instead and the
# engine decides the verdict, computes the difference, writes the sentence and
# throws the ball the AssertionFailure classifier already reads.

#: What to write when a bag arrives as one answer rather than as a sequence of
#: them. A str is the case worth naming: it is iterable, so without this a
#: message passed by mistake would be compared character by character.
_BAG_REMEDY = Remedy(
    "pass the answers as a sequence",
    "quickfix",
    "prose",
    python="assert_answers([<answer>, ...], [<answer>, ...])",
)


def _bag(values: Any, side: str) -> list[Atom]:
    """One answer bag as atoms, from whatever a query answered.

    `Rows` iterates as rows, so each row becomes the expression of its values,
    `(a b)` for a two-column answer and `(b)` for a one-column one; project a
    single column with `rows.x` to compare the values themselves. Everything
    else is encoded the way every other boundary here encodes it.
    """
    if isinstance(values, (Atom, str, bytes)):
        msg = (
            f"the {side} answers arrived as a single {type(values).__name__}; "
            f"an answer bag is a sequence of answers, so one answer is [answer]"
        )
        raise refusing(TypeError(msg), remedy=_BAG_REMEDY)
    if not isinstance(values, Iterable):
        msg = (
            f"the {side} answers arrived as {type(values).__name__}, which is "
            f"not iterable; an answer bag is Rows, Answers, or any sequence of "
            f"atoms or of values encode accepts"
        )
        raise refusing(TypeError(msg), remedy=_BAG_REMEDY)
    return [_encode(value) for value in values]


def _assert_over_bags(head: str, door: str, actual, expected, msg) -> None:
    """Hand one written call to the engine door that decides `head`.

    The call is ONE wire because it is both what the door reports as the form
    the program wrote and where the door reads its two bags from: decoding it
    once shares a variable by name across the two bags, which is what one MeTTa
    source writing the same two bags does.
    """
    call = Expression(
        [
            Symbol(head),
            Expression(_bag(actual, "actual")),
            Expression(_bag(expected, "expected")),
            *((_encode(msg),) if msg is not None else ()),
        ]
    )
    if not _runtime().do(door, call.to_wire()):
        refused = (
            f"the engine refused {door}: an answer bag reached it as something "
            f"other than a tuple of atoms, which this door builds and so cannot "
            f"receive from a caller"
        )
        raise EngineError(refused)


def assert_answers(actual, expected, *, msg=None) -> None:
    """Assert that two answer bags are equal, ignoring order.

    The Python face of MeTTa's `(assert-answers ...)`, which is the door
    `assertEqualToResult` reaches: multiplicity counts and order does not, so
    `(a a b)` is not `(a b b)` and `(1 2)` is `(2 1)`.

        from metta import testing

        def test_the_edges_are_what_the_program_stored():
            testing.assert_answers(space.match(pattern).x, [S.b, S.c])

    Each side is `Rows`, `Answers`, or any sequence of atoms or of values
    `encode` accepts; a `Rows` compares row by row, each row the expression of
    its values, so project one column with `rows.x` to compare values.

    A false claim raises `AssertionFailure` carrying `.missing` and `.excess`,
    the two directed bag differences as tuples of atoms, and a message whose
    report reads exactly as the engine's own does for the same two bags. It is
    printed on stderr as well as raised, which is what every MeTTa assertion
    does and for the same reason: a ball any `except` can swallow says nothing
    when it is swallowed.

    pytest's assertion rewriting is not involved. This raises, so it reports
    the same way inside a `unittest` case, a plain script or a notebook.
    """
    _assert_over_bags("assert-answers", "metta_py_assert_answers", actual, expected, msg)


def assert_includes(actual, expected, *, msg=None) -> None:
    """Assert that every expected answer was produced, and allow more.

    The Python face of MeTTa's `(assert-includes-answers ...)`, which is the
    door `assertIncludes` reaches. The relation is containment, so an answer in
    excess of the expectation is LEGAL and the failure names only what was
    wanted and never came: `.missing` carries that bag and `.excess` is None,
    absence rather than an empty tuple, because a two-sided report of a
    one-sided verdict points the reader at something that is not broken.

    `assert_answers` is the two-sided relation. Everything else about the two
    is the same, arguments included.
    """
    _assert_over_bags(
        "assert-includes-answers", "metta_py_assert_includes", actual, expected, msg
    )
