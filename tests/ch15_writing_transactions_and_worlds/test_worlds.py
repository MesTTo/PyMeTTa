"""Purpose: prove immutable worlds branch, evaluate, and commit as values.

Guarantees:
  - reified evaluation leaves its parent unchanged and answers a new immutable
    world whose multiset diff can be committed as ordinary ordered events
    [tested: test_world_eval_branches_without_touching_parent,
    test_commit_applies_the_world_diff_as_post_commit_events; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - a composite containing a live provider without a snapshot capability
    refuses and names that member [tested:
    test_reify_refuses_and_names_a_live_composite_member; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - world evaluation fences State writes and emits no parent-space event
    [tested: test_world_eval_fences_state_and_emits_nothing; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - provider-owned journal commits persist the ordinary multiset diff before
    publishing it and replay that state after close [tested:
    test_a_journaled_world_commit_replays_its_ordinary_diff; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - effect admission joins source and compiled callees, refuses before scratch
    allocation or translation-time work, and admits exactly the declared rank
    [tested:
    test_an_uncovered_world_refuses_before_creating_scratch_or_running_the_operation,
    test_world_coverage_admits_the_joined_plan,
    test_refused_custom_translator_runs_no_compile_time_effect,
    test_reify_refuses_an_effectful_captured_compilation_before_replay,
    test_a_translator_expansion_cannot_hide_an_oracle_call; commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - lowering cannot erase nondeterminism, freshening state, host operations,
    or a dynamic masked return from the admission plan [tested:
    test_lowered_nondeterminism_remains_visible_to_world_admission,
    test_sealed_freshening_requires_state_coverage,
    test_a_masked_runtime_result_remains_dynamic; commit=173eeed021beb360b5e5f9f8461889e27190affc]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import uuid
from dataclasses import FrozenInstanceError

import pytest

from metta import Expression, S, State, V, spaces
from metta.errors import MettaError


def _unique(prefix: str) -> str:
    """Return a source-readable operation name unique to this process."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _install_effectful_translator(metta, space):
    """Install a lazy translator rule whose compilation is observable."""
    operation = _unique("world-translation-effect")
    rule = _unique("world-effect-rule")
    seen = []

    @metta.op(name=operation, effect="oracleIO")
    def translation_effect():
        seen.append(1)
        return S.done

    space.run(
        f"(: {rule} (-> %Undefined%))\n"
        f"(= ({rule})\n"
        f"   (let $_ ({operation})\n"
        "     (noeval (+ 1 2))))\n"
        f"!(add-translator-rule! {rule})"
    )
    return operation, rule, seen


def test_an_uncovered_world_refuses_before_creating_scratch_or_running_the_operation(
    metta,
    monkeypatch,
):
    """Admission is the first effectful action in ReifiedWorld.eval."""
    name = _unique("world-write")
    called = []

    @metta.op(name=name, effect="writesState")
    def world_write(value: int) -> int:
        called.append(value)
        return value

    parent = metta._new_space()
    world = parent.reify()
    scratch_attempts = []

    def forbid_scratch(_self, *args, **kwargs):
        scratch_attempts.append((args, kwargs))
        message = "world admission allocated scratch before refusal"
        raise AssertionError(message)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(type(parent), "_new_space", forbid_scratch)
            with pytest.raises(MettaError) as caught:
                world.eval(f"({name} 7)")
        error = caught.value
        assert error.operation == name
        assert error.capability == "writesState"
        assert error.ground is not None
        assert "EffectSafety" in str(error.ground)
        assert f"operation {name}" in str(error)
        assert "effect rank writesState" in str(error)
        assert "covers only pureStructural" in str(error)
        assert "space.covers('writesState')" in str(error)
        assert "mutable space" in str(error)
        assert called == []
        assert scratch_attempts == []
    finally:
        world.close()
        parent.drop()
        metta.unregister_op(name)


def test_world_coverage_admits_the_joined_plan(metta):
    """Coverage compares against the strongest member of a composite plan."""
    parent = metta._new_space()
    parent.covers("writesState")
    world = parent.reify()
    try:
        answers, successor = world.eval(
            "(progn (superpose (1 2)) "
            "(add-atom &self (joined yes)) done)"
        )
        try:
            assert answers == [S.done, S.done]
            assert successor.atoms == (S.joined(S.yes), S.joined(S.yes))
            assert parent.atoms() == []
        finally:
            successor.close()
    finally:
        world.close()
        parent.drop()


def test_every_declaration_door_removes_every_stale_duplicate(metta):
    """What `covers` promised, the other declaration doors now keep too.

    `_replace_catalog_declaration` removes in a LOOP and inside a
    TRANSACTION, and only two doors called it; ten more wrote the shape
    longhand with a single `once` removal and no transaction. Both halves
    were wrong. A second row survived a redeclaration, so the engine read two
    policies for one space [measured 2026-08-31: planting a second
    `(emits &s fair)` left `['fair', 'best-first']`], and a failure between
    the remove and the add left the declaration missing rather than unchanged.
    """
    catalog = metta._at("&metta")

    def rows(head, space):
        return [
            str(row.rest)
            for row in catalog.match(Expression([S[head], S[str(space.name)], V.rest]))
        ]

    # (door head, first declaration, a VALID second row, the redeclaration).
    # The planted row has to be valid: the catalog checks a declaration
    # against its declared kind, so a bogus value is refused before it can
    # become the duplicate this is about.
    cases = [
        ("emits", "emits", lambda s: s.emits("depth"), S.fair,
         lambda s: s.emits("best-first")),
        ("source", "source", lambda s: s.source("linear"), S.repeated,
         lambda s: s.source("peek")),
        ("context", "context", lambda s: s.context("closed-world"), S["open-world"],
         lambda s: s.context("closed-world")),
        ("atomicity", "writes", lambda s: s.atomicity("atomic-single"),
         S["best-effort"], lambda s: s.atomicity("transactional")),
        ("agenda", "agenda", lambda s: s.agenda("recency"), S.specificity,
         lambda s: s.agenda("declaration")),
    ]
    for door, head, first, planted, again in cases:
        space = metta._new_space()
        first(space)
        catalog.add(Expression([S[head], S[str(space.name)], planted]))
        assert len(rows(head, space)) == 2, door
        again(space)
        assert len(rows(head, space)) == 1, f"{door} left a stale row"

    # `image` keys on the TYPE as well as the space, so its row is
    # `(image <space> <type> <setting>)` and the key is two atoms FLAT. Passing
    # them as one nested pair built a retract pattern matching nothing and left
    # every previous row standing, which the sqlite suite caught at once.
    space = metta._new_space()
    space.image("Blob", "opaque")
    catalog.add(S.image(S[str(space.name)], S.Blob, S.transparent))
    settings = lambda: [  # noqa: E731 -- a local read, not a definition
        str(row.setting)
        for row in catalog.match(S.image(S[str(space.name)], S.Blob, V.setting))
    ]
    assert len(settings()) == 2
    space.image("Blob", "auto")
    assert settings() == ["auto"]


def test_redeclaring_coverage_removes_every_stale_duplicate(metta):
    """The host declaration door replaces even manually duplicated rows."""
    parent = metta._new_space()
    catalog = parent._at("&metta")
    subject = parent._name_atom or S[str(parent)]
    operation = _unique("world-coverage-downgrade")
    called = []

    @metta.op(name=operation, effect="oracleIO")
    def oracle() -> int:
        called.append(1)
        return 1

    try:
        catalog.add(
            S.covers(subject, S.oracleIO),
            S.covers(subject, S.readOnlyLookup),
        )
        parent.covers("writesState")
        rows = list(catalog.match(S.covers(subject, V.effect)))
        assert [str(row.effect) for row in rows] == ["writesState"]

        parent.covers("pureStructural")
        world = parent.reify()
        try:
            with pytest.raises(MettaError) as caught:
                world.eval(f"({operation})")
            assert caught.value.operation == operation
            assert caught.value.capability == "oracleIO"
            assert called == []
        finally:
            world.close()
    finally:
        parent.drop()
        metta.unregister_op(operation)


def test_lowered_nondeterminism_remains_visible_to_world_admission(metta):
    """The superpose head remains in the plan after control lowering."""
    parent = metta._new_space()
    world = parent.reify()
    try:
        with pytest.raises(MettaError) as caught:
            world.eval("(superpose (1 2))")
        assert caught.value.operation == "superpose"
        assert caught.value.capability == "nondeterministicReadOnly"

        parent.covers("nondeterministicReadOnly")
        answers, successor = world.eval("(superpose (1 2))")
        try:
            assert answers == [1, 2]
            assert successor.atoms == ()
        finally:
            successor.close()
    finally:
        world.close()
        parent.drop()


def test_a_typed_structural_chain_is_not_falsely_refused(metta):
    """A source-backed scalar result does not become an opaque dynamic call."""
    parent = metta._new_space()
    world = parent.reify()
    try:
        answers, successor = world.eval("(chain 1 $x (+ $x 2))")
        try:
            assert answers == [3]
            assert successor.atoms == ()
        finally:
            successor.close()
    finally:
        world.close()
        parent.drop()


def test_native_control_profiles_keep_pure_calls_and_nested_effects_distinct(metta):
    """Reviewed control builtins contribute only the branches they can run."""
    parent = metta._new_space()
    world = parent.reify()
    try:
        answers, successor = world.eval("(and-then True (+ 1 2))")
        try:
            assert answers == [3]
        finally:
            successor.close()
        with pytest.raises(MettaError) as caught:
            world.eval("(and-then True (random-int 1 1000000))")
        assert caught.value.operation == "random-int"
        assert caught.value.capability == "oracleIO"
    finally:
        world.close()
        parent.drop()


def test_a_masked_runtime_result_remains_dynamic(metta):
    """A returned masked argument may reveal a runtime operation head."""
    function = _unique("world-mask-return")
    parent = metta._new_space()
    parent.run(
        f"(: {function} (-> Atom %Undefined%))\n"
        f"(= ({function} $x) $x)"
    )
    world = parent.reify()
    try:
        with pytest.raises(MettaError) as caught:
            world.eval(f"({function} (random-int 1 1000000))")
        assert caught.value.operation == "<dynamic-operation>"
        assert caught.value.capability == "oracleIO"
    finally:
        world.close()
        parent.drop()


def test_an_atom_result_keeps_a_masked_operation_as_structural_data(metta):
    """Atom is the final-result twin of a %Undefined% dynamic return."""
    function = _unique("world-hold-atom")
    numeric = _unique("world-hold-number")
    parent = metta._new_space()
    parent.run(
        f"(: {function} (-> Atom Atom))\n"
        f"(= ({function} $x) $x)\n"
        f"(: {numeric} (-> Number Number))\n"
        f"(= ({numeric} $x) $x)"
    )
    world = parent.reify()
    try:
        answers, successor = world.eval(
            f"({function} (random-int 1 1000000))"
        )
        try:
            assert answers == [S["random-int"](1, 1000000)]
            assert len(successor.atoms) == len(world.atoms)
        finally:
            successor.close()
        numeric_answers, numeric_successor = world.eval(f"({numeric} 3)")
        try:
            assert numeric_answers == [3]
            assert len(numeric_successor.atoms) == len(world.atoms)
        finally:
            numeric_successor.close()
    finally:
        world.close()
        parent.drop()


def test_sealed_freshening_requires_state_coverage(metta):
    """Each sealed evaluation allocates fresh variables and is a state write."""
    parent = metta._new_space()
    world = parent.reify()
    try:
        with pytest.raises(MettaError) as caught:
            world.eval("(sealed () (pair $x $x))")
        assert caught.value.operation == "sealed"
        assert caught.value.capability == "writesState"
    finally:
        world.close()
        parent.drop()


def test_function_descends_into_nested_host_effects(metta):
    """Function walks instructions but treats a return payload as data."""
    operation = _unique("world-function-write")
    called = []

    @metta.op(name=operation, effect="writesState")
    def function_write() -> int:
        called.append(1)
        return 7

    parent = metta._new_space()
    world = parent.reify()
    try:
        answers, successor = world.eval(
            f"(function (return ({operation})))"
        )
        try:
            assert answers == [S[operation]()]
            assert called == []
        finally:
            successor.close()
        with pytest.raises(MettaError) as caught:
            world.eval(f"(function (eval ({operation})))")
        assert caught.value.capability == "writesState"
        assert operation in str(caught.value)
        assert called == []
        with pytest.raises(MettaError) as caught:
            world.eval("(function (eval (git-module! example)))")
        assert caught.value.operation == "git-module!"
        assert caught.value.capability == "oracleIO"
    finally:
        world.close()
        parent.drop()
        metta.unregister_op(operation)


def test_elapsed_and_timeout_require_oracle_coverage(metta):
    """Timing wrappers observe host scheduling even around structural work."""
    parent = metta._new_space()
    world = parent.reify()
    try:
        for target, operation in (
            ("(elapsed (+ 1 2))", "elapsed"),
            ("(timeout 1 (+ 1 2))", "timeout"),
        ):
            with pytest.raises(MettaError) as caught:
                world.eval(target)
            assert caught.value.operation == operation
            assert caught.value.capability == "oracleIO"
    finally:
        world.close()
        parent.drop()


@pytest.mark.parametrize(
    ("target", "operation"),
    [
        ("(call (get_time))", "call"),
        ("(call (random 1 1000))", "call"),
        (
            "(translatePredicate (writeln world-raw-output))",
            "translatePredicate",
        ),
    ],
)
def test_raw_prolog_escape_hatches_require_oracle_coverage(
    metta,
    capsys,
    target,
    operation,
):
    """Raw Prolog doors fail closed before time, randomness, or output."""
    parent = metta._new_space()
    world = parent.reify()
    try:
        with pytest.raises(MettaError) as caught:
            world.eval(target)
        assert caught.value.operation == operation
        assert caught.value.capability == "oracleIO"
        assert "world-raw-output" not in capsys.readouterr().out
    finally:
        world.close()
        parent.drop()


def test_a_statically_refused_host_call_has_no_runtime_effect_to_cover(metta):
    """BadArgType is the plan when typed dispatch rejects before the call."""
    operation = _unique("world-typed-oracle")
    called = []

    @metta.op(name=operation, effect="oracleIO")
    def typed_oracle(value: int) -> int:
        called.append(value)
        return value

    parent = metta._new_space()
    world = parent.reify()
    try:
        answers, successor = world.eval(f'({operation} "bad")')
        try:
            assert len(answers) == 1
            assert "BadArgType" in str(answers[0])
            assert called == []
        finally:
            successor.close()
    finally:
        world.close()
        parent.drop()
        metta.unregister_op(operation)


def test_refused_custom_translator_runs_no_compile_time_effect(metta):
    """The source lower bound is checked before an executable rule compiles."""
    operation = _unique("world-compile-effect")
    rule = _unique("world-effect-rule")
    seen = []

    @metta.op(name=operation, effect="writesState")
    def compile_effect():
        seen.append(1)
        return S.done

    parent = metta._new_space()
    try:
        parent.run(
            f"(: {rule} (-> %Undefined%))\n"
            f"(= ({rule})\n"
            f"   (let $_ ({operation})\n"
            "     (noeval (+ 1 2))))\n"
            f"!(add-translator-rule! {rule})"
        )
        world = parent.reify()
        try:
            assert seen == []
            with pytest.raises(MettaError) as caught:
                world.eval(f"({rule})")
            assert caught.value.operation == operation
            assert caught.value.capability == "writesState"
            assert seen == []
        finally:
            world.close()
    finally:
        parent.drop()
        metta.unregister_op(operation)


def test_a_translator_expansion_cannot_hide_an_oracle_call(metta):
    """Admission walks the executable term returned by a translator rule."""
    operation = _unique("world-expanded-oracle")
    rule = _unique("world-expanding-rule")
    seen = []

    @metta.op(name=operation, effect="oracleIO")
    def expanded_oracle():
        seen.append(1)
        return S.done

    parent = metta._new_space()
    try:
        parent.run(
            f"(: {rule} (-> %Undefined%))\n"
            f"(= ({rule}) (noeval ({operation})))\n"
            f"!(add-translator-rule! {rule})"
        )
        world = parent.reify()
        try:
            with pytest.raises(MettaError) as caught:
                world.eval(f"({rule})")
            assert caught.value.operation == operation
            assert caught.value.capability == "oracleIO"
            assert seen == []
        finally:
            world.close()
    finally:
        parent.drop()
        metta.unregister_op(operation)


def test_lambda_compilation_is_admitted_before_its_translator_rule_runs(metta):
    """A held lambda body still compiles before the constructor returns."""
    parent = metta._new_space()
    operation, rule, seen = _install_effectful_translator(metta, parent)
    world = parent.reify()
    try:
        seen.clear()
        with pytest.raises(MettaError) as caught:
            world.eval(f"(|-> () ({rule}))")
        assert caught.value.operation == operation
        assert caught.value.capability == "oracleIO"
        assert seen == []
    finally:
        world.close()
        parent.drop()
        metta.unregister_op(operation)


def test_program_write_compilation_is_included_in_world_admission(metta):
    """Writes-only coverage cannot compile an effectful equation payload."""
    parent = metta._new_space()
    parent.covers("writesState")
    operation, rule, seen = _install_effectful_translator(metta, parent)
    world = parent.reify()
    try:
        seen.clear()
        with pytest.raises(MettaError) as caught:
            world.eval(
                f"(add-atom &self (= (world-added-program) ({rule})))"
            )
        assert caught.value.operation == operation
        assert caught.value.capability == "oracleIO"
        assert seen == []
    finally:
        world.close()
        parent.drop()
        metta.unregister_op(operation)


def test_reify_refuses_an_effectful_captured_compilation_before_replay(
    metta,
    monkeypatch,
):
    """A frozen image is refused in reify(), before any successor exists.

    The image's own compilation is an effect, so the refusal is owed by
    reify() rather than by the first eval(): a world that has already been
    handed back would carry a retained program image whose materialisation
    ran the very operation its coverage forbids.
    """
    parent = metta._new_space()
    parent.covers("writesState")
    operation, rule, seen = _install_effectful_translator(metta, parent)
    function = _unique("world-remove-program")
    parent.run(
        f"(= ({function} a) ({rule}))\n"
        f"(= ({function} b) 2)"
    )
    image_attempts = []

    def forbid_image(_self, *args, **kwargs):
        image_attempts.append((args, kwargs))
        message = "reify allocated a successor image before refusing"
        raise AssertionError(message)

    try:
        seen.clear()
        with monkeypatch.context() as patch:
            patch.setattr(type(parent), "_new_space", forbid_image)
            with pytest.raises(MettaError) as caught:
                parent.reify()
        assert caught.value.operation == rule
        assert caught.value.capability == "oracleIO"
        assert "<frozen world image>" in str(caught.value.atom)
        assert caught.value.ground is not None
        assert "EffectSafety" in str(caught.value.ground)
        assert seen == []
        assert image_attempts == []
    finally:
        parent.run(
            f"!(remove-atom &self (= ({function} a) ({rule})))\n"
            f"!(remove-atom &self (= ({function} b) 2))\n"
            f"!(remove-translator-rule! {rule})"
        )
        parent.drop()
        metta.unregister_op(operation)


@pytest.mark.parametrize("operation", ["add-reduct", "add-reducts"])
def test_reducing_space_writes_plan_the_expression_they_execute(
    metta,
    operation,
):
    """A reduction hidden behind a write remains in the joined plan."""
    effect = _unique("world-reduct-effect")
    called = []

    @metta.op(name=effect, effect="oracleIO")
    def reduct_effect():
        called.append(1)
        return 7

    parent = metta._new_space()
    parent.covers("writesState")
    world = parent.reify()
    payload = f"({effect})" if operation == "add-reduct" else f"(({effect}))"
    try:
        with pytest.raises(MettaError) as caught:
            world.eval(f"({operation} &self {payload})")
        assert caught.value.capability == "oracleIO"
        assert effect in str(caught.value)
        assert called == []
    finally:
        world.close()
        parent.drop()
        metta.unregister_op(effect)


def test_world_eval_branches_without_touching_parent(metta):
    """Two successors share a base value and mutate neither it nor the store."""
    parent = metta._new_space()
    parent.covers("writesState")
    parent.add(S.base(1))
    world = parent.reify()

    answers, left = world.eval("(progn (add-atom &self (left 2)) done)")
    _, right = world.eval("(progn (add-atom &self (right 3)) done)")

    assert answers == [S.done]
    assert parent.atoms() == [S.base(1)]
    assert world.atoms == (S.base(1),)
    assert left.atoms == (S.base(1), S.left(2))
    assert right.atoms == (S.base(1), S.right(3))
    assert left.diff(right) == ([S.left(2)], [S.right(3)])
    with pytest.raises(FrozenInstanceError):
        left.atoms = ()


def test_world_rebases_copied_self_references_on_every_branch(metta):
    """An equation captured from a parent writes only into each scratch world."""
    parent = metta._new_space()
    parent.covers("writesState")
    parent.run("(= (world-plant) (add-atom &self (owned yes)))")

    _, planted = parent.reify().eval("(world-plant)")
    assert S.owned(S.yes) in planted.atoms
    assert list(parent.match(S.owned(V.what))) == []

    _, planted_twice = planted.eval("(world-plant)")
    assert planted_twice.atoms.count(S.owned(S.yes)) == 2
    assert list(parent.match(S.owned(V.what))) == []


def test_world_commit_preserves_multiplicity_and_refuses_stale_or_wrong_origins(metta):
    """A world is an origin-bound optimistic multiset value."""
    parent = metta._new_space()
    parent.covers("writesState")
    parent.add(S.dup(1))
    _, doubled = parent.reify().eval("(add-atom &self (dup 1))")

    parent.commit(doubled)
    assert parent.atoms() == [S.dup(1), S.dup(1)]
    with pytest.raises(MettaError, match=r"changed after.*reified|stale"):
        parent.commit(doubled)

    other = metta._new_space()
    try:
        with pytest.raises(MettaError, match="belongs to"):
            other.commit(doubled)
    finally:
        other.drop()


def test_commit_applies_the_world_diff_as_post_commit_events(metta):
    """Observers run after the whole remove/add diff is visible in the parent."""
    parent = metta._new_space()
    parent.covers("writesState")
    parent.add(S.old(1))
    _, world = parent.reify().eval("(progn (remove-atom &self (old 1)) (add-atom &self (new 2)))")
    seen = []
    snapshots = []
    removed = parent.subscribe(
        S.old(V.n),
        lambda event: (seen.append(event), snapshots.append(parent.atoms())),
        on="remove",
    )
    added = parent.subscribe(
        S.new(V.n), lambda event: (seen.append(event), snapshots.append(parent.atoms()))
    )
    try:
        parent.commit(world)
        assert [(event.action, event.atom) for event in seen] == [
            ("remove", S.old(1)),
            ("add", S.new(2)),
        ]
        assert snapshots == [[S.new(2)], [S.new(2)]]
        assert parent.atoms() == [S.new(2)]
    finally:
        added.cancel()
        removed.cancel()


def test_reify_refuses_and_names_a_live_composite_member(metta):
    """Enumeration is not a snapshot capability, even when it is iterable."""
    native = metta._new_space()
    live = spaces.object_view({"answer": 42})
    composite = metta.metta.space(backing=spaces.union(native, live))
    try:
        with pytest.raises(MettaError, match="ObjectView"):
            composite.reify()
    finally:
        composite.drop()


def test_world_eval_fences_state_and_emits_nothing(metta):
    """A world may alter its own atoms, never the parent event or cell stores."""
    parent = metta._new_space()
    parent.covers("writesState")
    cell = State(7, space=parent)
    seen = []
    subscription = parent.subscribe(S.world(V.n), seen.append)
    try:
        _, changed = parent.reify().eval("(add-atom &self (world 1))")
        assert changed.atoms == (S.world(1),)
        assert seen == []
        assert parent.atoms() == []

        with pytest.raises(MettaError, match=r"state.*world|world.*state"):
            parent.reify().eval(S["change-state!"](cell, 8))
        assert cell.value == 7
    finally:
        subscription.cancel()


def test_a_journaled_world_commit_replays_its_ordinary_diff(metta, tmp_path):
    """The durable provider lands first, then emits remove/add in diff order."""
    journal = tmp_path / "world.db"
    parent = metta.metta.space(
        journal=journal,
        schema={"edge": 2},
        sync="close",
    )
    parent.covers("writesState")
    parent.events("per-write-exactly", "ordered")
    parent.add(S.edge(S.old, 1))
    _, changed = parent.reify().eval(
        "(progn (remove-atom &self (edge old 1)) (add-atom &self (edge new 2)))"
    )
    seen = []
    snapshots = []
    removed = parent.subscribe(
        S.edge(S.old, V.n),
        lambda event: (seen.append(event), snapshots.append(parent.atoms())),
        on="remove",
    )
    added = parent.subscribe(
        S.edge(S.new, V.n),
        lambda event: (seen.append(event), snapshots.append(parent.atoms())),
    )
    try:
        parent.commit(changed)
        assert [(event.action, event.atom) for event in seen] == [
            ("remove", S.edge(S.old, 1)),
            ("add", S.edge(S.new, 2)),
        ]
        assert snapshots == [[S.edge(S.new, 2)], [S.edge(S.new, 2)]]
    finally:
        added.cancel()
        removed.cancel()
        parent.drop()

    reopened = metta.metta.space(
        journal=journal,
        schema={"edge": 2},
        sync="close",
    )
    try:
        assert reopened.atoms() == [S.edge(S.new, 2)]
    finally:
        reopened.drop()
