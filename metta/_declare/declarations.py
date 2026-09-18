"""Purpose: express handling, storage and effect contracts as declaration atoms."""

from __future__ import annotations as _future_annotations

from collections import abc as _abc
from typing import TYPE_CHECKING, Any

import metta.doors as _doors
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Variable,
    _atom_from_wire,
    _to_atom,
)
from metta._lazy import lazy
from metta._spaces.cursor import _require_vocabulary
from metta._spaces.handle import current_space
from metta._spaces.subscriptions import _event_stream
from metta.vocabularies import (
    AgendaPolicy,
    AnswerPolicy,
    Atomicity,
    Delivery,
    Determinism,
    EffectClass,
    EventOrder,
    Fidelity,
    ImageMode,
    OnError,
    SemiringOrder,
    SourceKind,
    World,
)


@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.text,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_integration_restores_registry_preimages', 'extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_integration_unwinds_every_framework_registration', 'extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_outer_installation_unwinds_its_completed_dependency'),
)
def integrate(space: _root.Space, target: Any) -> str:
    """Install a library integration; see metta.integrate."""
    return lazy('metta.integrate').integrate(space, target)

def _register_space(space: _root.Space, provider: Any, name: str) -> Any:
    """A space answered by Python: matches, adds and removals route to
    the provider, so a table, a dataframe or a service is matchable the
    way stored atoms are. See metta.foreign.SpaceProvider.

    Subject first, as every register_* call: the thing being
    registered, then where it lives. The two calls that named the
    name first were the surface's own inconsistency, and learning
    the order from op raised TypeError here.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    lazy('metta.foreign').register_provider(space._rt, name, provider)
    return provider

def _unregister_space(space: _root.Space, name: str) -> None:
    """Remove a registered Python-backed space."""
    lazy('metta.foreign').unregister_provider(space._rt, name)

@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_a_sql_backed_space_under_declared_handles', 'extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_declare_handles_keeps_repeated_variables_shared', 'extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_declare_handles_rejects_a_conflict_eagerly'),
    binding=_doors.Binding('metta_py_declare_handles', _doors.Wire.goal),
)
def handles(
    space: _root.Space,
    pattern: str | Atom,
    fidelity: Fidelity,
    *,
    det: Determinism | None = None,
) -> Atom:
    """Declare how faithfully a space answers queries of one shape.

    The declaration is one (handles ...) atom in &metta, and queries
    are routed by the most specific declared shape that matches:
    Exact licenses pushing the caller's bound to the provider, Partial
    and Sound stay candidates the engine re-unifies, and Refuse makes
    the query a loud error instead of a silent partial answer. Write
    (in $x) at a position to match only queries arriving with it
    bound, so a scan-only source is three words:

        rows.handles("(edge (in $a) $b)", "Refuse")

    Coherence is checked eagerly in the same transaction as the
    write: a new entry that can disagree with an existing one on some
    query fails here, naming both, rather than on the first query
    that falls into their overlap. The atom is returned; removing it
    from &metta withdraws the declaration.
    """
    _require_vocabulary(
        fidelity, Fidelity, "fidelity",
        because="it is the declared claim the router acts on, so an "
        "unknown word would silently declare nothing",
    )
    if det is not None:
        _require_vocabulary(
            det, Determinism, "det",
            because="the same vocabulary declare_function_determinism uses everywhere else",
        )
    shape = _to_atom(pattern)
    children = [Symbol("handles"), Symbol(str(space.name)), shape, Symbol(fidelity)]
    if det is not None:
        children.append(Symbol(det))
    atom = Expression(children)
    space._rt.must(
        "metta_py_declare_handles(Space, W, Ctx)",
        Space="&metta",
        W=atom.to_wire(),
        Ctx=str(space.name),
    )
    return atom

@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_annotations_validates_and_replaces', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_prov_annotations_carry_source_terms', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_top_orders_mixed_integer_and_float_annotations_by_value'),
)
def annotations(
    space: _root.Space,
    subject_or_algebra: str,
    algebra: str | None = None,
    *,
    capabilities: _abc.Iterable[str] = (),
) -> Atom:
    """Declare the algebra a context's answer annotations live in.

    A context is a space name or an operation name. bool is the
    default at which everything vanishes; ranked admits ordered
    annotations, which is what (top k ...) consumes. A custom name must
    first be introduced with :meth:`algebra`. A one-argument call uses
    this space as the context; the two-argument form keeps an operation
    context as the explicit first subject. Capabilities are
    checked against the algebra's requirements before the catalog write;
    amplitude programs, for example, must explicitly declare ``finite``,
    ``contractive`` and ``staged`` [tested:
    test_amplitudes_interfere_inside_the_fragment_and_are_refused_outside;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]. Declaring replaces any earlier row for the
    context, so the reader never meets two disagreeing atoms.
    """
    name = space.name if algebra is None else subject_or_algebra
    algebra = subject_or_algebra if algebra is None else algebra
    algebra_api = lazy('metta.algebra')
    declaration = algebra_api.require(space, algebra)
    declared_capabilities = frozenset(capabilities)
    missing = declaration.requires - declared_capabilities
    if missing:
        refusal = (
            "amplitude_fragment_refused"
            if algebra == "amplitude"
            else "algebra_requirements_missing"
        )
        msg = f"{refusal}({name}, {algebra}, missing={sorted(missing)!r})"
        raise algebra_api.AlgebraRequirementError(msg)
    catalog = lazy('metta._faces.space').Space("&metta", _runtime=space._rt)
    for previous in catalog.atoms():
        if (
            isinstance(previous, Expression)
            and len(previous.children) >= 3
            and previous.children[0] == Symbol("annotations")
            and previous.children[1] == Symbol(str(name))
        ):
            catalog.remove(previous)
    children: list[Atom] = [
        Symbol("annotations"),
        Symbol(str(name)),
        Symbol(algebra),
    ]
    if declared_capabilities:
        children.append(
            Expression(
                [
                    Symbol("capabilities"),
                    *(Symbol(capability) for capability in sorted(declared_capabilities)),
                ]
            )
        )
    atom = Expression(children)
    catalog.add(atom)
    return atom

@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_algebra_lifecycle.py::test_drop_retires_algebra_before_redeclaration', 'extensions/python/tests/ch04_spaces_and_matching/test_algebra_lifecycle.py::test_rollback_releases_an_algebra_mirror', 'extensions/python/tests/ch04_spaces_and_matching/test_algebra_lifecycle.py::test_rollback_restores_a_replaced_algebra_mirror'),
)
def algebra(
    space: _root.Space,
    name: str,
    *,
    combine: str,
    extend: str,
    zero: Any,
    one: Any,
    laws: _abc.Iterable[str] = (),
    carrier: _abc.Iterable[Any] = (),
    type: Any = None,  # noqa: A002 -- Python spells a carrier type as type
    requires: _abc.Iterable[str] = (),
    order: SemiringOrder | None = None,
    negate: Any = None,
    saturated: Any = None,
    variable: Any = None,
) -> Atom:
    """Declare operations with carrier membership and optional checked laws.

    ``type`` accepts a Python type, MeTTa type atom, or Boolean predicate
    and checks every input and result. A type alone grants no laws or
    fusion. ``carrier`` enumerates the finite domain required for exhaustive
    law checking; it may accompany ``type`` to constrain that domain.
    Use ``prov`` and ``.under()`` to reinterpret uncertified tensor traces.
    ``negate``, ``saturated`` and ``variable`` are the three further
    operations a carrier may claim, each a callable, a Symbol or an
    operation name like ``combine``: the unary complement a model count
    weighs a variable's false branch with, the test that stops a fixpoint
    join, and the operation that mints the carrier's value for a source key
    and its tag.
    """
    algebra_api = lazy('metta.algebra')
    named = {
        role: None if operation is None else algebra_api._operation_name(
            space, name, role, operation, arity=1 if role == "negate" else 2,
        )
        for role, operation in (("negate", negate), ("saturated", saturated), ("variable", variable))
    }
    return algebra_api.declare(
        space,
        name,
        combine=combine,
        extend=extend,
        zero=zero,
        one=one,
        laws=laws,
        carrier=carrier,
        type=type,
        requires=requires,
        order=order,
        negate=named["negate"],
        saturated=named["saturated"],
        variable=named["variable"],
    )

def _replace_catalog_declaration(
    space: _root.Space,
    head: str,
    keys: tuple[Atom, ...],
    values: tuple[Atom, ...],
    *,
    supersedes: tuple[int, ...] = (),
) -> Atom:
    """Replace every catalog row this declaration supersedes, atomically.

    A row is `(<head> <key>... <value>...)`. The keys say WHICH row this
    is and the values say what it declares, both are passed, and the
    stored atom is built HERE, so the retract pattern and the atom that
    replaces it cannot disagree about the head or the key. They could
    before: a caller passed the head, the key and the whole atom
    separately and nothing checked the first two occurred in the third.
    `image` did disagree, passing its two key atoms as one nested pair,
    which built `(image (<space> <type>) $previous)` against a flat row,
    matched nothing, and left every previous row standing.

    Both halves of the replacement are load-bearing and both were got
    wrong by the methods that wrote this longhand instead of calling here.
    The removal LOOPS, because `metta_py_remove` takes one occurrence and
    a catalog that somehow holds two rows for one subject would keep the
    stale one: measured 2026-08-31, a second `(emits &s fair)` row
    survived a redeclaration and left the engine reading two policies for
    one space. And it runs in a TRANSACTION, because a failure between the
    remove and the add leaves the declaration missing rather than
    unchanged.

    How many trailing slots a superseded row has is `len(values)`, so no
    caller states it. ``supersedes`` names EXTRA counts, for a declaration
    whose own shape grew: `agenda` supersedes both the three-element form
    and the four-element one that names a function, whichever it writes.
    """
    atom = Expression([Symbol(head), *keys, *values])
    shapes = [
        Expression(
            [Symbol(head), *keys,
             *(Variable(f"previous{slot}") for slot in range(count))]
        )
        for count in {len(values), *supersedes}
    ]

    def supersede() -> Atom:
        for previous in shapes:
            while True:
                removed = space._rt.apply_must(
                    "metta_py_remove",
                    "&metta",
                    previous.to_wire(),
                )
                result = _atom_from_wire(removed)
                if not bool(getattr(result, "value", True)):
                    break
        space._rt.must(
            "metta_py_add(Space, W)",
            Space="&metta",
            W=atom.to_wire(),
        )
        return atom

    return space._at("&metta").transaction(supersede)

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_arrow_products.py::test_world_coverage_uses_the_annotated_effect', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_a_closed_world_releases_its_plan_image', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_a_collected_world_does_not_take_the_name_a_live_mint_released'),
)
def covers(space: _root.Space, effect: EffectClass | str) -> Atom:
    """Declare the strongest effect this reified world can handle.

    Coverage is a catalog fact ``(covers <space> <effect>)``. World
    evaluation always admits pureStructural plans. A stronger joined plan
    runs only when this declaration is at least as strong; redeclaring
    replaces the previous row atomically.

        orders.covers("writesState")
        world = orders.reify()
    """
    declared = EffectClass(_require_vocabulary(effect, EffectClass, "effect"))
    subject = (
        space._name_atom
        if space._name_atom is not None
        else Symbol(str(space._space))
    )
    return _replace_catalog_declaration(
        space, "covers", (subject,), (Symbol(str(declared)),)
    )

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_a_refused_recovery_receipt_still_compensates_the_effect_it_could_not_record', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_saga_compensates_in_reverse_commit_order', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_saga.py::test_a_discarded_step_runs_no_compensation'),
)
def compensates(space: _root.Space, operation: str, compensation: str) -> Atom:
    """Declare one recovery operation for an effectful operation.

    The catalog row is ``(compensates operation compensation)``. The
    source operation must already be registered at writesState or
    oracleIO, because weaker operations leave no saga receipt. The
    recovery name must already be a host operation or compiled MeTTa
    function. It receives the complete ``(did ...)`` receipt. The runner writes
    the call as ``(quote <receipt>)`` so the receipt is not evaluated
    on the way in; the quote is a barrier and does not survive, so the
    handler is handed the receipt itself.
    Redeclaring replaces the old row atomically.
    """
    operation_name = str(operation)
    compensation_name = str(compensation)
    return _replace_catalog_declaration(
        space, "compensates", (Symbol(operation_name),), (Symbol(compensation_name),)
    )

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch18_performance/test_algebra_rates.py::test_invalid_rates_are_refused_before_the_tagged_fact_lands', 'extensions/python/tests/ch06_many_answers/test_under_algebra.py::test_tagged_call_answers_use_the_carrier_without_hijacking_other_calls', 'extensions/python/tests/ch06_many_answers/test_under_algebra.py::test_tagged_derivations_flow_through_match_and_reinterpret_without_requery'),
)
def add_tagged_fact(space: _root.Space, tag: Any, proposition: Any) -> Atom:
    """Store ``(fact tag proposition)``, the normative annotation form."""
    atom = lazy('metta.algebra').tagged_fact(tag, proposition)
    space.add(atom)
    return atom

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch06_many_answers/test_under_algebra.py::test_tagged_derivations_flow_through_match_and_reinterpret_without_requery', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_tagged_algebra_debits_inferences_across_operations', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_tagged_algebra_forwards_bounds_to_every_evaluating_door'),
)
def add_tagged_rule(space: _root.Space, tag: Any, head: Any, *premises: Any) -> Atom:
    """Store one rule generated by the algebra-agnostic tag threader.

    A callable ``tag`` labels each instance with its result over the premise
    tags in order, in place of the carrier's extend fold: it registers under
    its own name and the rule stores ``(function <name>)``, the spelling a
    MeTTa equation of the same shape takes directly.
    """
    algebra_api = lazy('metta.algebra')
    if callable(tag) and not isinstance(tag, Atom):
        name = algebra_api._operation_name(
            space, "rule", getattr(tag, "__name__", "label"), tag, arity=len(premises),
        )
        tag = Expression((Symbol("function"), Symbol(name)))
    atom = algebra_api.tagged_rule(tag, head, *premises)
    space.add(atom)
    return atom

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/ext/metta-pydantic/tests/test_pydantic.py::test_the_row_is_registered_against_the_image_point', 'extensions/python/tests/ch11_python_as_a_notation/test_integrate.py::test_a_failed_integration_restores_registry_preimages', 'extensions/python/tests/ch20_extending_the_engine/test_catalog_kinds.py::test_the_image_declaration_is_catalog_validated'),
)
def image(
    space: _root.Space,
    type_name: str,
    setting: ImageMode,
) -> Atom:
    """Choose how one Python type crosses one context boundary.

    opaque carries the live object by identity; transparent projects its
    structural MeTTa image; auto makes that choice from the value's size
    and replayability. A later declaration for the same context and type
    replaces the earlier one, so an attached provider reads one policy.
    Use ``_`` as the type name for a context-wide fallback.
    """
    _require_vocabulary(setting, ImageMode, "image setting")
    # Keyed on the TYPE as well as the space: one space declares an image
    # per type, so there are two key atoms.
    return _replace_catalog_declaration(
        space, "image", (Symbol(str(space.name)), Symbol(type_name)),
        (Symbol(setting),)
    )

@_doors.door(
    kind=_doors.Kind.evaluation,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.nondet,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch06_many_answers/test_under_algebra.py::test_space_sample_is_seeded_and_uses_k_vocabulary', 'extensions/python/tests/ch18_performance/test_algebra_rates.py::test_declared_rates_make_seeded_selection_match_their_distribution'),
)
def sample(
    space: _root.Space,
    query: str | Atom,
    *,
    k: int = 10,
    seed: int = 7,
) -> list[Atom]:
    """Choose ``k`` tagged alternatives with replacement by ``(rate n)``.

    The argument names and list result follow ``random.choices``. A local
    seeded generator makes repeated calls reproducible without changing
    Python's process-global random state.
    """
    return list(
        lazy('metta.algebra').sample(
            space,
            query,
            algebra="prob",
            draws=k,
            seed=seed,
        )
    )

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_a_linear_source_refuses_its_second_consumption', 'extensions/python/tests/ch20_extending_the_engine/test_contract.py::test_consumption_validates', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_explain_answers_the_route_and_the_route_is_honest'),
)
def consumption(
    space: _root.Space,
    kind: SourceKind,
) -> Atom:
    """Declare a space's consumption discipline.

    repeated is the default: the source re-enumerates. linear is a
    one-shot source, a cursor or a feed: its SECOND consumption is a
    loud error naming the space, where the undeclared floor answers a
    silently empty set from the drained object; re-registering the
    provider resets the mark, because a fresh provider is a fresh
    source. peek promises reads do not consume, which the conformance
    kit checks by enumerating twice. The Python door is named
    ``consumption`` so ``source()`` can show program text; the MeTTa
    catalog row deliberately keeps its language-level ``source`` head.
    """
    _require_vocabulary(kind, SourceKind, "kind")
    return _replace_catalog_declaration(
        space, "source", (Symbol(str(space.name)),), (Symbol(kind),)
    )

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_on_error_validates', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_an_op_keeps_its_failure_as_the_error_atom', 'extensions/python/tests/ch11_python_as_a_notation/test_ops.py::test_relational_candidate_shape_errors_are_contract_errors'),
    binding=_doors.Binding('metta_py_add', _doors.Wire.goal),
)
def on_error(
    space: _root.Space,
    subject_or_pattern: str | Atom,
    pattern_or_mode: str | Atom,
    mode: OnError | None = None,
) -> Atom:
    """Declare what a context's failure becomes, per query shape.

    abort is the undeclared floor: the provider's error propagates.
    keep delivers the failure as one (Error <query> <reason>) answer
    beside the answers that already streamed, the language's own
    error-as-alternative reading. empty ends the stream silently, BY
    declaration, which is what separates it from a swallowed error.
    Shapes route most-specific-first exactly as (handles ...) entries
    do. Control signals and transport failures are never kept or
    emptied: an interrupt is the caller's, and an absent backend has
    said nothing about the data.
    """
    name = space.name if mode is None else subject_or_pattern
    pattern = subject_or_pattern if mode is None else pattern_or_mode
    chosen = str(pattern_or_mode) if mode is None else str(mode)
    _require_vocabulary(chosen, OnError, "mode")
    shape = _to_atom(pattern)
    atom = Expression([Symbol("on-error"), Symbol(str(name)), shape, Symbol(chosen)])
    space._rt.must(
        "metta_py_add(Space, W)", Space="&metta", W=atom.to_wire()
    )
    return atom

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_best_first_merge_orders_across_contexts', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_declared_fair_merge_interleaves', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_merge_validates'),
    binding=_doors.Binding('metta_py_add', _doors.Wire.goal),
)
def merge(
    space: _root.Space,
    pattern: str | Atom,
    policy: AnswerPolicy,
) -> Atom:
    """Declare how the engine merges one query shape's answers
    ACROSS contexts, for the multi-context idiom
    (match (superpose (&a &b)) ...).

    depth is today's space-after-space order and the undeclared
    floor. fair interleaves the streams round-robin. best-first is a
    k-way ordered merge by annotation, sound only when every merged
    context declares (emits <ctx> best-first), and loudly refused
    without. Shapes route most-specific-first as everywhere.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    _require_vocabulary(policy, AnswerPolicy, "policy")
    shape = _to_atom(pattern)
    atom = Expression([Symbol("merge"), shape, Symbol(policy)])
    space._rt.must(
        "metta_py_add(Space, W)", Space="&metta", W=atom.to_wire()
    )
    return atom

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_context_validates', 'extensions/python/ext/metta-otel/tests/test_otel.py::test_spans_nest_by_the_events_own_depth', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_explain_answers_the_route_and_the_route_is_honest'),
)
def context(
    space: _root.Space,
    world: World,
) -> Atom:
    """Record what a space's absence means.

    Negation as failure reads absence as falsity, which is only
    sound over a world the answerer holds whole, so a negated goal
    may consult a foreign space only when it declares closed-world;
    an undeclared one refuses under negation loudly. Native spaces
    are the engine's own database and closed by construction.
    """
    _require_vocabulary(world, World, "world")
    return _replace_catalog_declaration(
        space, "context", (Symbol(str(space.name)),), (Symbol(world),)
    )

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_worlds.py::test_every_declaration_door_removes_every_stale_duplicate',),
    refuses=(_doors.Refusal(_doors.RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[space:agenda]'),),
)
def agenda(
    space: _root.Space,
    policy: AgendaPolicy,
    function: str | None = None,
) -> Atom:
    """Declare which reaction fires first when several match one write.

    declaration is the default and the order they were declared, which is
    what the engine produced by accident before this was a policy;
    recency is the most recently declared first; specificity is the most
    tests in the pattern first; priority reads each reaction's own
    declared number, highest first; and user names a MeTTa function that
    SCORES a reaction, highest first. Every policy breaks ties on
    declaration order.

        alarms.reacts("(alert $w)", "(insert &log (all $w))")
        alarms.reacts("(alert fire)", "(insert &log (fire))", priority=9)
        alarms.agenda("priority")
    """
    _require_vocabulary(policy, AgendaPolicy, "policy")
    if (policy == "user") != (function is not None):
        msg = (
            "the user policy names the MeTTa function that scores a "
            "reaction, and no other policy takes one"
        )
        raise ValueError(msg)
    values = [Symbol(policy)]
    if function is not None:
        values.append(Symbol(str(function)))
    return _replace_catalog_declaration(
        space, "agenda", (Symbol(str(space.name)),), tuple(values), supersedes=(1, 2)
    )

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_bridge_cascade_is_bounded', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_bridge_inserts_under_the_matched_bindings', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_revise_bridge_replaces'),
    binding=_doors.Binding('metta_install_bridges', _doors.Wire.goal),
    refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:reacts]'),),
)
def reacts(
    space: _root.Space,
    pattern: str | Atom,
    operation: str | Atom,
    priority: int | None = None,
) -> Atom:
    """Declare a reaction, stored as an (on ...) atom: when an atom
    matching PATTERN lands in the space, OPERATION runs under the
    match's bindings.

    The managed heads are (insert <ctx> <atom>), (retract <ctx>
    <atom>) and (revise <ctx> <old> <new>), engine-routed rules
    going through the same write paths as direct writes. Declaring
    installs the engine's write hook, which is why reactions go
    through here or metta_install_bridges rather than a bare
    add-atom.

    A subscription bridge is the NEIGHBOUR, not a special case of this:
    a reaction's operation runs engine-side, so it reaches registered
    spaces, while the bridge rule delivers Python-side to anything
    with add and remove, an unregistered or remote target included.
    Same multi-context-systems idea, two delivery tiers.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    shape = _to_atom(pattern)
    op = _to_atom(operation)
    parts = [Symbol("on"), Symbol(str(space.name)), shape, op]
    if priority is not None:
        if not isinstance(priority, int) or isinstance(priority, bool):
            msg = f"priority is an integer, not {priority!r}"
            raise TypeError(msg)
        parts.append(Grounded(priority))
    atom = Expression(parts)
    space._rt.must(
        "metta_py_add(Space, W)", Space="&metta", W=atom.to_wire()
    )
    space._rt.must("metta_install_bridges")
    return atom

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch15_writing_transactions_and_worlds/test_admission_routes.py::test_relative_admits_declaration_installs_the_receiver_contract', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_admission_is_sugar_over_the_pre_add_hook', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_admission_types_the_pool'),
    binding=_doors.Binding('metta_admission_claim', _doors.Wire.goal),
)
def admits(space: _root.Space, type_name: str) -> Atom:
    """Type a pool's membership: only TYPE-carrying atoms enter.

    A thread pool is a space whose atoms are spaces, and this is its
    declaration: (admits &pool Space) plus per-atom (: <space> Space)
    declarations make membership a type judgement the ontology
    already knows how to make.
    """
    atom = _replace_catalog_declaration(
        space, "admits", (Symbol(str(space.name)),), (Symbol(type_name),)
    )
    space._rt.must(
        "metta_admission_claim(Pool, Declarer)",
        Pool=str(space.name),
        Declarer=current_space(),
    )
    return atom

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_capacity_bounds_the_pool', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_capacity_validates', 'extensions/python/tests/ch15_writing_transactions_and_worlds/test_admission_routes.py::test_relative_capacity_declaration_installs_the_receiver_contract'),
    binding=_doors.Binding('metta_admission_claim', _doors.Wire.goal),
    refuses=(_doors.Refusal(_doors.RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[space:capacity]'),),
)
def capacity(space: _root.Space, limit: int) -> Atom:
    """Bound a pool: an add beyond LIMIT atoms is refused loudly."""
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        msg = f"capacity is a positive integer, not {limit!r}"
        raise ValueError(msg)
    atom = _replace_catalog_declaration(
        space, "capacity", (Symbol(str(space.name)),), (Grounded(limit),)
    )
    space._rt.must(
        "metta_admission_claim(Pool, Declarer)",
        Pool=str(space.name),
        Declarer=current_space(),
    )
    return atom

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_failed_file_transaction_rolls_a_foreign_provider_back', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_failed_transaction_rolls_both_stores_back', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_file_transaction_enlists_and_commits_a_foreign_provider'),
)
def atomicity(
    space: _root.Space,
    atomicity: Atomicity,
) -> Atom:
    """Declare what a space's writes promise inside a transaction.

    Named for what it declares rather than for the atom it stores, which
    stays `(writes <ctx> ...)`: `writes` on a Space is the effect
    decorator for an OPERATION, and one object cannot spell two concepts
    one way.

    transactional providers implement metta.foreign.Transactional and
    are committed or rolled back WITH the engine's transaction;
    best-effort is the author's declared acceptance of a write that
    survives a rollback; atomic-single refuses transactional writes.
    Undeclared spaces refuse them loudly too, because a foreign write
    silently surviving a rolled-back transaction is the wrong answer
    the declaration exists to replace.
    """
    _require_vocabulary(atomicity, Atomicity, "atomicity")
    return _replace_catalog_declaration(
        space, "writes", (Symbol(str(space.name)),), (Symbol(atomicity),)
    )

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_declare_emits_validates', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_best_first_merge_orders_across_contexts', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_top_pushes_the_bound_under_three_declarations'),
)
def emits(
    space: _root.Space,
    policy: AnswerPolicy,
) -> Atom:
    """Declare the order a context emits its own answers in.

    best-first is the promise (top k ...) needs before its bound may
    reach the provider: the first k of a best-first emission ARE the
    k best. Distinct from the (merge <pattern> <policy>) strategy,
    which is how the ENGINE merges answers across several contexts.
    """
    _require_vocabulary(policy, AnswerPolicy, "policy")
    return _replace_catalog_declaration(
        space, "emits", (Symbol(str(space.name)),), (Symbol(policy),)
    )

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_events_delivers_leftovers_queued_before_cancel', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_events_times_out_quiet_and_refuses_callback_mode', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_subscription_is_a_context_manager_and_events_stream'),
)
def events(
    space: _root.Space,
    delivery: Delivery | None = None,
    order: EventOrder = EventOrder.unordered,
) -> Atom | Any:
    """Return the event stream, or declare what this context promises.

    Subscribability is a promise about the context, not something its
    methods alone establish. A native space needs no declaration:
    every write into it runs the engine's own hooks, so it delivers
    per-write-exactly and ordered by construction. A FOREIGN context
    declares, and one that declares nothing refuses a subscription
    instead of serving one that silently misses writes.

        shared.events("at-most-once")   # redis pub/sub
        mirror.events("per-write-exactly", "ordered")

    delivery is at-most-once, at-least-once or per-write-exactly, and
    order is ordered or unordered, defaulting to unordered because an
    omitted promise is the weaker one. A Python provider says the same
    thing by overriding delivers(), which registration writes here.
    """
    if delivery is None:
        return _event_stream(space)
    _require_vocabulary(delivery, Delivery, "delivery")
    _require_vocabulary(order, EventOrder, "order")
    return _replace_catalog_declaration(
        space, "events", (Symbol(str(space.name)),), (Symbol(delivery), Symbol(order))
    )

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
