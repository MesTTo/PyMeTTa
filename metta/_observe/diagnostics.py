"""Purpose: build derivation trees and explain unsuccessful space patterns.
Guarantees:
  - derivation depth is either absent or a positive integer [tested
    test_derivation_depth_must_be_a_positive_integer_or_none]
  - depth exhaustion remains a partial proof rather than no proof [tested
    test_depth_exhaustion_returns_a_partial_proof]
  - why() distinguishes stored-shape misses, functions, and close names
    [tested test_why]
  - why() and lint() reach one head verdict, so a translator special form is
    never reported as an unknown name and a call at an undefined arity is
    named by both [tested: test_why_and_lint_agree_about_a_special_form,
    test_why_and_lint_agree_about_a_call_at_an_undefined_arity,
    test_why_and_lint_draw_suggestions_from_one_pool; commit=bd3a1bbad63952fc7c0d7367f38237dd1c219d8b]
  - eager query explanations distinguish a pattern miss, failed join, and
    rejecting guard [tested test_query_rows_explain_empty_results]
  - derivation enumeration selects ``metta_py_limited/6`` when a scoped stack
    bound exists [tested: test_stack_limit_is_carried_to_the_limited_six_seam;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - derivation enumeration crosses through the shared execution-policy wrapper,
    so atomic, speculative, and capture scopes cover the whole proof search
    [tested: test_every_public_execution_door_honours_speculative_policy,
    test_derivation_speculation_fences_the_engine_global_self;
    commit=cf6507cfe9c3d6512ac75039ae22f178140e0cbf]
  - ordinary derivation executes effectful premises and retains their engine
    writes; the existing speculative policy is the explicit rollback boundary
    [tested:
    test_derivation_effects_are_explicit_and_speculation_discards_engine_writes;
    commit=418bed011dfc47bb2c2d9e6b51e0d2a6f7b7e729]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import importlib as _importlib
from typing import TYPE_CHECKING, Any

import metta._declare.operations as _ops_module
import metta.doors as _doors
import metta.seam as _seam
from metta._atoms.designation import space_of as _space_of
from metta._atoms.factories import Atom, Expression, Symbol, _atom_from_wire, _to_atom
from metta._atoms.templates import read_targets as _read_targets
from metta._binding.runtime import Runtime
from metta._catalog.meaning import EngineRegistry, head_meaning
from metta._lazy import lazy
from metta._spaces.evaluate import _prepared_ask
from metta._spaces.execution import _EXPLAIN_KEYWORDS, _controlled_run
from metta._spaces.handle import _substituted
from metta._spaces.profile import Explanation
from metta._spaces.results import raise_error_answers
from metta._spaces.scope import _limits
from metta._spaces.source import _held
from metta.vocabularies import EffectClass


def derivations(
    rt: Runtime,
    space: str,
    target: Any,
    depth: int | None,
    *,
    timeout: float | None,
    inferences: int | None,
) -> list[Any]:
    """Return each guarded derivation for one target."""
    _validate_depth(depth)
    trees = _controlled_run(
        rt,
        "metta_py_derivations",
        [space, _to_atom(target).to_wire(), -1 if depth is None else depth],
        _limits(timeout, inferences),
    )
    derivation_type = _importlib.import_module(
        'metta.derivation'
    ).Derivation
    return [derivation_type.from_atom(_atom_from_wire(tree)) for tree in trees]

def _validate_depth(depth: int | None) -> None:
    if depth is not None and (isinstance(depth, bool) or not isinstance(depth, int) or depth <= 0):
        msg = f"derivation depth must be a positive integer or None, got {depth!r}"
        raise ValueError(msg)

def _stored_with_head(space: Any, name: str) -> list[Expression]:
    return [
        atom
        for atom in space.atoms()
        if isinstance(atom, Expression) and isinstance(atom.head, Symbol) and atom.head.name == name
    ]

def _stored_explanation(atom: Expression, name: str, stored: list[Expression]) -> str:
    sizes = sorted({len(candidate) for candidate in stored})
    if len(atom) not in sizes:
        # One observed size reads as a number, not a set: "[3] elements" looks
        # like a list of one element rather than an element count of three.
        observed = str(sizes[0]) if len(sizes) == 1 else str(sizes)
        return f"{name} atoms here have {observed} elements; the pattern has {len(atom)}"
    return f"{len(stored)} {name} atom(s) exist here but none unifies with {atom}"

def _unstored_explanation(space: Any, name: str, arguments: int) -> str:
    """Explain a head no stored atom carries, from the shared head verdict.

    The same head_meaning() lint() reads, so the two cannot disagree about
    what carries a name. Asking fun/1 alone, which this did through 0.7.3,
    answered "nothing here is headed by if, and no function has that name;
    did you mean if?" for a translator special form used correctly.
    """
    meaning = head_meaning(name, arguments, EngineRegistry(space.runtime))
    if meaning.wrong_arity:
        return (
            f"no {name} atoms are stored here, and {name} is a function "
            f"defined for {sorted(meaning.arities)} argument(s) rather than "
            f"{arguments}, so evaluating this will not answer either"
        )
    if meaning.route == "function":
        return (
            f"no {name} atoms are stored here; {name} is a function, so its "
            f"answers come from evaluation, not matching: try eval"
        )
    if meaning.route == "translated":
        return (
            f"no {name} atoms are stored here; {name} is a special form the "
            f"translator compiles, so its answers come from evaluation, not "
            f"matching: try eval"
        )
    # The near-miss needs no special case of its own: with no
    # underscore-to-hyphen rewriting left in the surface, nn_next against a
    # stored nn-next is a close match like any other.
    suggestion = f"; did you mean {meaning.suggestion}?" if meaning.suggestion else ""
    return f"nothing here is headed by {name}, and no function has that name{suggestion}"

def explain_no_match(space: Any, pattern: Any) -> str:
    """Explain the first cheap reason one pattern cannot match."""
    atom: Atom = _to_atom(pattern)
    if not isinstance(atom, Expression) or not atom.children:
        return f"{atom} is not an expression pattern"
    head = atom.head
    if not isinstance(head, Symbol):
        return f"the pattern head {head} is not a symbol"
    stored = _stored_with_head(space, head.name)
    if stored:
        return _stored_explanation(atom, head.name, stored)
    return _unstored_explanation(space, head.name, len(atom) - 1)

def _first_unmatched_pattern(space: Any, patterns: tuple[Atom, ...]) -> tuple[int, Atom] | None:
    for index, pattern in enumerate(patterns, start=1):
        if not space.match(pattern, limit=1):
            return index, pattern
    return None

def explain_empty_query(
    space: Any,
    patterns: tuple[Atom, ...],
    where: Atom | None,
) -> str:
    """Explain which stage removed every answer from one eager query."""
    if len(patterns) == 1 and where is None:
        return explain_no_match(space, patterns[0])
    if where is not None and space.match(*patterns, limit=1):
        return (
            f"the patterns match together, but the where guard {where} "
            "rejects every joined row"
        )
    unmatched = _first_unmatched_pattern(space, patterns)
    if unmatched is not None:
        index, pattern = unmatched
        detail = explain_no_match(space, pattern)
        if len(patterns) == 1:
            return detail
        return f"pattern {index} cannot match: {detail}"
    if len(patterns) > 1:
        return (
            "each pattern matches on its own, but no shared variable binding "
            "satisfies them together"
        )
    return "the empty query returned no rows"

_WRITING_EFFECTS = frozenset({EffectClass.writesState, EffectClass.oracleIO})

_EXPLAINED_MATCH_HEADS = frozenset({"match", "match%"})

_UNRESOLVED_OPERATION = "<dynamic-operation>"

@_seam.service(
    "catalog",
    "The declaration space a receiver's runtime reads and writes, given a "
    "context or a space. Published here because a space is this module's, and "
    "metta.seam sits below the base layer where it cannot import one.",
)
def _catalog_of(m: Any) -> _root.Space:
    """The `&metta` space of the runtime behind a context or a space."""
    return lazy('metta._faces.space').Space("&metta", _runtime=_space_of(m).runtime)

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch14_seeing_your_program/test_explain_plan.py::test_a_rows_with_no_query_behind_it_refuses_to_explain', 'extensions/python/tests/ch14_seeing_your_program/test_explain_plan.py::test_an_explanation_is_a_mapping_over_its_item_heads', 'extensions/python/tests/ch14_seeing_your_program/test_explain_plan.py::test_an_explanation_is_data_a_space_stores_and_matches_back'),
)
def explain(
    space: _root.Space,
    query: Any,
    /,
    *,
    analyze: bool = False,
    allow_writes: bool = False,
    **values: Any,
) -> Explanation:
    """What the engine will do with this query, reflected rather than run.

        e = m.self.explain(
            "(match &self (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))"
        )
        e.plan          # (plan generic-join (order ...) (relations ...))
        e["writes"]     # (writes transactional)

    SQL's EXPLAIN, over this engine's own decisions. A match form answers
    which seam entry handles it and with what fidelity, whether a bound
    pushes into the provider, the source, the context world, the
    annotation semiring, emission, event delivery, writes, the error mode,
    the merge policy, whether the space's source relations are
    materialised, and the PLAN: `generic-join` with the variable order and
    each conjunct's columns, `nested-loop` with the conjunct the matcher
    leads with, or `empty-factor` with the conjunct that has no candidate.
    An operation call answers its effect, whether it has an inverse, its
    annotations, its error mode and the cache decision the memo made.

    The plan names the join the engine RUNS. Deciding that costs the
    query's shape and one scan of each conjunct's relation, because a
    conjunction whose stored rows are not all ground declines the Generic
    Join and must read `nested-loop`; nothing is sorted and no trie is
    built, so explaining a triangle over 2,048 stored edges cost 7,350
    engine inferences against the query's own 237,473, and the share falls
    as the data grows: 10.1%, 4.6% and 3.1% at 128, 512 and 2,048 rows
    [measured 2026-09-07; command=PYTHONPATH=extensions/python
    python extensions/python/benchmarks/probes/explain_plan_cost.py;
    fixture=a two-out-degree ring of
    1,024 nodes at loadavg 62].

    `analyze=True` is EXPLAIN ANALYZE: the same items plus `(inferences
    N)`, `(answers N)` and `(cputime S)` measured by running the query
    inside `stats()`. It REFUSES the query when the engine can NAME an
    operation in it that writes, because an analysis that mutates is not an
    analysis; `allow_writes=True` says to measure it anyway. A match
    TEMPLATE is evaluated once per answer, so `(match &s (edge $x $y)
    (add-atom &s (seen $x)))` is a writing query.

    The longhand is the MeTTa form: `m.run("!(explain <query>)")` answers
    the same atoms, and `analyze=True` is that run with a `stats()` block
    around `eval()` of the same query. A form that is neither a match nor
    an operation call keeps the engine's own `type_error(explainable, ...)`.
    """
    (target,), holes = _read_targets(
        (query,), values, called="explain", reserved=_EXPLAIN_KEYWORDS
    )
    subject = _to_atom(_held(target, holes, handed_on=True))
    explained = space.eval(Symbol("explain")(subject))
    raise_error_answers(explained, space=space._space, target=subject)
    items = tuple(
        child
        for answer in explained
        if isinstance(answer, Expression)
        for child in answer.children
    )
    if not analyze:
        return Explanation(subject, items, analyzed=False)
    _refuse_analysing_a_write(space, subject, allow_writes=allow_writes)
    with space.stats() as measured:
        answers = space.eval(subject)
    return Explanation(
        subject,
        (
            *items,
            Symbol("inferences")(measured.inferences),
            Symbol("answers")(len(answers)),
            Symbol("cputime")(measured.cputime),
        ),
        analyzed=True,
    )

def _refuse_analysing_a_write(space: _root.Space, subject: Atom, *, allow_writes: bool) -> None:
    """Refuse to MEASURE a query that writes, naming it and the override.

    The engine's own effect walk over the compiled target answers this, so
    a template that writes is caught as readily as a direct call:
    `(match &s (edge $x $y) (add-atom &s (seen $x)))` names `add-atom`,
    because a match template IS evaluated, once per answer.

    Two of the walk's rows are read past. `match` carries `writesState`
    itself, because resolving a named space may create its execution module
    [source: engine/metta/effects.pl, metta_semantic_effect(match,
    writesState)]; that is the door being explained rather than the query's
    mutation, and every match carries it. `<dynamic-operation>` is the walk
    saying it could not resolve a call, which a variable-headed template
    makes ordinary -- `($x $y $z)` is the commonest template there is -- so
    it says unknown, not writes. The guard therefore sees every operation
    the engine can NAME, and `allow_writes=True` is the answer for the rest.
    """
    if allow_writes:
        return
    ignored = {_UNRESOLVED_OPERATION}
    if isinstance(subject, Expression) and subject.children:
        head = str(subject.children[0])
        if head in _EXPLAINED_MATCH_HEADS:
            ignored.add(head)
    writers = [
        f"{name} is {effect.value}"
        for name, effect in space.effect_plan(subject).operations
        if effect in _WRITING_EFFECTS and name not in ignored
    ]
    if not writers:
        return
    msg = (
        f"explain(analyze=True) RUNS the query to measure it, and this one "
        f"writes: {', '.join(writers)}. An analysis that mutates is not an "
        f"analysis; pass allow_writes=True to measure it anyway, or drop "
        f"analyze= to read the plan without running anything"
    )
    raise ValueError(msg)

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_effect_plan.py::test_async_effect_plan_retains_the_sync_contract', 'extensions/python/tests/ch11_python_as_a_notation/test_effect_plan.py::test_effect_plan_reads_replaced_operation_classification', 'extensions/python/tests/ch11_python_as_a_notation/test_effect_plan.py::test_effect_plan_reports_nested_calls_without_executing_them'),
    binding=_doors.Binding('metta_py_world_effect_plan', _doors.Wire.goal),
)
def effect_plan(space: _root.Space, target: Any) -> _ops_module.EffectPlan:
    """Return operations the target may execute and their joined effect.

    The engine translates the same atom or source form ``eval`` accepts,
    follows nested compiled calls, and reads current operation metadata.
    It does not execute the target. A later registration change is visible
    on the next call. This is the analysis reified-world admission uses.
    """
    target_wire = target if isinstance(target, str) else _to_atom(target).to_wire()
    rows, effect, _coverage = space._rt.apply_must(
        "metta_py_world_effect_plan",
        space._space,
        space._space,
        target_wire,
    )
    operations = tuple(
        (str(name), EffectClass(str(declared))) for name, declared in rows
    )
    return _ops_module.EffectPlan(operations, EffectClass(str(effect)))

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_per_space.py::test_derivation_follows_the_spaces_module', 'extensions/python/tests/ch05_equations_and_evaluation/test_per_ask_evaluation.py::test_derivation_binds_host_values_like_the_doors_beside_it', 'extensions/python/tests/ch14_seeing_your_program/test_derivation.py::test_a_cut_inside_once_stays_inside_it'),
)
def derivation(
    space: _root.Space,
    target: Any,
    depth: int | None = None,
    *,
    timeout: float | None = None,
    inferences: int | None = None,
) -> list[Any]:
    """Every proof of an answer, as trees in MeTTa terms.

    Each tree names the equations that fired and the stored atoms at the
    leaves, read from the translated_from links the engine keeps for
    every compiled clause. Meta-interpreted, so slower than evaluation;
    a diagnostic, not an evaluation path. The default walks each proof
    without a depth cutoff. A positive depth returns a partial tree with
    Truncated nodes when its budget ends, so an empty list means no proof.
    `timeout` and `inferences` guard the whole search. An evaluation error
    inside a proof surfaces as itself rather than as an empty proof list.

    Building a proof executes every premise it records, including
    effectful operations. Engine writes persist and repeated derivations
    accumulate them, just as repeated evaluations do. Use
    ``with space.speculative():`` when the proof should return while its
    engine writes are discarded. That scope cannot undo Python side
    effects, I/O, or subscription callbacks that already fired, so do not
    derive an effectful target when those effects must not happen.

    A `bind()` scope binds host values into the term, for the reason
    eval_status needs it: the substitution lands BEFORE the search, so the
    proof of an evaluation that binds anything was unaskable. Name keys
    mean symbols and atom keys mean themselves, so `bind({V.x: 5})` fills
    a variable hole. It takes no `theory` or
    `interpreter`, because a meta-interpreted diagnostic does not select an
    evaluation relation.
    """
    target, using = _prepared_ask(space, target, None)
    diagnostics = _importlib.import_module('metta._observe.diagnostics')
    return diagnostics.derivations(
        space._rt,
        space._space,
        _substituted(target, using) if using else target,
        depth,
        timeout=timeout,
        inferences=inferences,
    )

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.text,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_why', 'extensions/python/tests/ch14_seeing_your_program/test_lint.py::test_lint_and_why_agree_on_whether_a_head_is_known', 'extensions/python/tests/ch14_seeing_your_program/test_lint.py::test_why_and_lint_agree_about_a_call_at_an_undefined_arity'),
)
def why(space: _root.Space, pattern: Any, *, where: Any | None = None) -> str:
    """Why a pattern matches nothing here, in words.

    Checks the cheap explanations in order: unknown function, wrong
    arity, no stored atoms with that head. Honest when it cannot tell,
    and honest about the PREMISE too: a pattern that does match is a
    question with a false premise, and this refuses it the way
    Answers.why() always did rather than answering it. Asking why
    `(job $id $pri)` matched nothing, when it matches two atoms, used to
    answer "2 job atom(s) exist here but none unifies with it"
    [measured 2026-08-31].

    `where` is match()'s guard, and asking with one is where the answer
    gets interesting: a query can be empty because the pattern found
    nothing OR because the guard rejected everything it found, and only
    the guarded question can tell you which.

    One implementation, because there were two and they agreed word for
    word on every genuine miss while disagreeing about the premise.
    """
    return space.match(pattern, where=where).why()

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
