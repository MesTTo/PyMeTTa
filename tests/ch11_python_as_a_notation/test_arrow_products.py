"""Purpose: verify annotated-arrow contracts through public Python consumers.

Guarantees: effect plans and world admission consume annotations, memoization
does NOT, cardinality auditing observes one execution, and source lifetimes
keep effects current [tested:
extensions/python/tests/ch11_python_as_a_notation/test_arrow_products.py;
commit=ccad9f6d588270ec2f0810fc56c30e9e59207e7c].
Owns resources: pytest fixtures release spaces; tests restore the cardinality
pragma and close every successor world they create.
"""

import pytest

from metta import S, V
from metta._errors.errors import MettaError
from metta.vocabularies import EffectClass


@pytest.fixture
def product_space(metta):
    """Release each declaration before the next case joins its catalog rows."""
    with metta._new_space() as space:
        yield space


@pytest.mark.parametrize(
    ("product", "expected"),
    [
        ("det,writesState", EffectClass.writesState),
        ("nondet,readOnlyLookup", EffectClass.nondeterministicReadOnly),
        ("nondet,pureStructural", EffectClass.nondeterministicReadOnly),
        ("semidet,stable", EffectClass.readOnlyLookup),
        ("det", EffectClass.oracleIO),
    ],
)
def test_arrow_effect_reaches_planning_and_leaves_the_cache_to_its_author(
    product_space, product, expected
):
    """The declaration's class reaches planning; it does not veto a cache.

    An annotation is what the function's author says the function DOES, and
    effect planning and world admission are the two consumers that need it. It
    used to be a third thing as well, a refusal at `memoize-exact`, so an
    author who wrote a `writesState` arrow took the cache away from every
    caller. Caching is the caller's own decision about their own program and
    this library carries it out as written (user ruling, 2026-09-06).
    """
    product_space.run(
        f"(: arrow-py-f (-[{product}]-> Number Number)) "
        "(= (arrow-py-f $x) $x)"
    )
    plan = product_space.effect_plan(S.arrow_py_f(1))
    assert plan.effect is expected
    assert plan.operations == (("arrow-py-f", expected),)
    rows = product_space._at("&metta").match(S.effect(S.arrow_py_f, V.effect))
    assert [str(row.effect) for row in rows] == [expected.value]

    product_space.run("!(import! &self (library lib_memo))")
    assert product_space.run("!(memoize-exact arrow-py-f)") == [[True]]
    assert product_space.run("!(is-memoized arrow-py-f)") == [[True]]
    assert product_space.eval(S.arrow_py_f(1)) == [1]
    # And the declaration still says what it said: the cache did not weaken it.
    assert product_space.effect_plan(S.arrow_py_f(1)).effect is expected


def test_an_annotated_effectful_body_answers_from_its_cache(product_space):
    """The honoured declaration is a working cache, not a recorded flag.

    The body's one call has an observable effect, so a second answer that costs
    no second effect is the cache serving it.
    """
    seen = []

    @product_space.op(name="arrow-py-record", effect="writesState")
    def record(value: int) -> int:
        seen.append(value)
        return value

    try:
        product_space.run(
            "(: arrow-py-writer (-[det,writesState]-> Number Number)) "
            "(= (arrow-py-writer $x) (arrow-py-record $x)) "
            "!(import! &self (library lib_memo))"
        )
        assert product_space.run("!(memoize arrow-py-writer)") == [[True]]
        assert product_space.eval(S.arrow_py_writer(3)) == [3]
        assert product_space.eval(S.arrow_py_writer(3)) == [3]
        assert seen == [3]
    finally:
        product_space.unregister_op("arrow-py-record")


def test_an_annotated_pure_function_remains_memoizable(product_space):
    """A pureStructural annotation is as ordinary as it always was."""
    product_space.run(
        "(: arrow-py-f (-[det,pureStructural]-> Number Number)) "
        "(= (arrow-py-f $x) $x) !(import! &self (library lib_memo))"
    )
    assert product_space.run("!(memoize-exact arrow-py-f)") == [[True]]
    assert product_space.eval(S.arrow_py_f(7)) == [7]


def test_world_coverage_uses_the_annotated_effect(product_space):
    """An identity body cannot hide the writer declared above it."""
    product_space.run(
        "(: arrow-py-f (-[det,writesState]-> Number Number)) "
        "(= (arrow-py-f $x) $x)"
    )
    product_space.covers("pureStructural")
    world = product_space.reify()
    try:
        with pytest.raises(MettaError) as caught:
            world.eval(S.arrow_py_f(1))
        assert caught.value.operation == "arrow-py-f"
        assert caught.value.capability == "writesState"
        product_space.covers("writesState")
        answers, successor = world.eval(S.arrow_py_f(1))
        try:
            assert answers == [1]
        finally:
            successor.close()
    finally:
        world.close()


def test_cardinality_auditing_observes_one_execution(product_space):
    """A choicepoint raises before another equation or a replay can write."""
    seen = []

    @product_space.op(name="arrow-py-observe", effect="writesState")
    def observe(value: int) -> int:
        seen.append(value)
        return value

    try:
        product_space.run(
            "(: arrow-py-f (-[det,writesState]-> Number Number)) "
            "(= (arrow-py-f $x) (arrow-py-observe $x)) "
            "(= (arrow-py-f $x) (arrow-py-observe (+ $x 1)))"
        )
        product_space.run("!(pragma! verify-cardinality true)")
        with pytest.raises(MettaError, match="choicepoint"):
            product_space.eval(S.arrow_py_f(1))
        assert seen == [1]
    finally:
        product_space.run("!(pragma! verify-cardinality none)")
        product_space.unregister_op("arrow-py-observe")


def test_higher_order_and_scoped_pragma_calls_keep_cardinality_checks(product_space):
    """A function value and a scoped mode reach the ordinary checked dispatch."""
    product_space.run(
        "(: arrow-py-f (-[det]-> Number Number)) "
        "(= (arrow-py-f $x) $x) (= (arrow-py-f $x) $x) "
        "(: arrow-py-apply (-> (-> Number Number) Number Number)) "
        "(= (arrow-py-apply $f $x) ($f $x))"
    )
    with pytest.raises(MettaError, match="choicepoint"):
        product_space.run(
            "!(with-pragma! ((verify-cardinality true)) "
            "(arrow-py-apply arrow-py-f 1))"
        )
    assert product_space.eval(S.arrow_py_f(1)) == [1, 1]


def test_source_reload_and_failure_withdraw_owned_effect_rows(product_space, tmp_path):
    """A successful reload and a failed first load leave no orphan effects."""
    source = tmp_path / "arrow-source.metta"
    source.write_text(
        "(: arrow-py-f (-[det,writesState]-> Number Number)) "
        "(= (arrow-py-f $x) $x)",
        encoding="utf-8",
    )
    product_space.load(source)
    assert product_space.effect_plan(S.arrow_py_f(1)).effect is EffectClass.writesState
    source.write_text(
        "(: arrow-py-f (-> Number Number)) (= (arrow-py-f $x) $x)",
        encoding="utf-8",
    )
    product_space.load(source)
    assert product_space.effect_plan(S.arrow_py_f(1)).effect is EffectClass.pureStructural
    assert list(product_space._at("&metta").match(S.effect(S.arrow_py_f, V.effect))) == []

    failed = tmp_path / "arrow-failed.metta"
    failed.write_text(
        "(: arrow-py-failed (-[det,writesState]-> Number Number)) "
        "!(pragma! arrow-unsupported-setting true)",
        encoding="utf-8",
    )
    with pytest.raises(MettaError):
        product_space.load(failed)
    assert list(product_space._at("&metta").match(S.effect(S.arrow_py_failed, V.effect))) == []


def test_a_library_reloaded_into_two_spaces_keeps_both_products(product_space, tmp_path):
    """Both spaces keep their product when the file they share is reloaded.

    A library is a file more than one space loads, and a reload withdraws every
    copy. Each copy's declaration owns a catalog row of its own and the rows are
    equal, so a withdrawal that removed one of them by value reached the row the
    other space still owned and refused mid-reload.
    """
    source = tmp_path / "arrow-library.metta"
    source.write_text(
        "(: arrow-py-lib (-[det,writesState]-> Number Number)) "
        "(= (arrow-py-lib $x) $x)",
        encoding="utf-8",
    )
    with product_space._new_space() as other:
        product_space.load(source)
        other.load(source)
        catalog = product_space._at("&metta")
        rows = catalog.match(S.effect(S.arrow_py_lib, V.effect))
        assert [str(row.effect) for row in rows] == ["writesState", "writesState"]

        source.write_text(
            "(: arrow-py-lib (-[det,writesState]-> Number Number)) "
            "(= (arrow-py-lib $x) (+ $x 100))",
            encoding="utf-8",
        )
        product_space.load(source)

        rows = catalog.match(S.effect(S.arrow_py_lib, V.effect))
        assert [str(row.effect) for row in rows] == ["writesState", "writesState"]
        assert product_space.eval(S.arrow_py_lib(1)) == [101]
        assert other.eval(S.arrow_py_lib(1)) == [101]
        assert product_space.effect_plan(S.arrow_py_lib(1)).effect is EffectClass.writesState
        assert other.effect_plan(S.arrow_py_lib(1)).effect is EffectClass.writesState


def test_fast_source_restore_reinstalls_the_product(product_space, tmp_path):
    """The saved written type recreates policy when its old owner is gone."""
    cache = tmp_path / "arrow-cache.qlf"
    with product_space._new_space() as donor:
        donor.run(
            "(: arrow-py-cache (-[det,writesState]-> Number Number)) "
            "(= (arrow-py-cache $x) $x)"
        )
        donor.save(cache, format="fast")
    product_space.load(cache)
    assert product_space.effect_plan(S.arrow_py_cache(1)).effect is EffectClass.writesState
    assert product_space.eval(S.arrow_py_cache(1)) == [1]


def test_an_unresolved_product_refuses_at_source_load(product_space):
    """The diagnostic identifies the unsupported assertion before storing it."""
    with pytest.raises(MettaError, match="product variables"):
        product_space.run("(: arrow-py-f (-[$effect]-> Number Number))")
    assert list(product_space._at("&metta").match(S.effect(S.arrow_py_f, V.effect))) == []


def test_forward_memoization_preserves_deferred_answer_aggregation(product_space):
    """Arriving alternatives are definitions even before they are compiled."""
    product_space.run("!(import! &self (library lib_memo))")
    try:
        answers = product_space.run(
            "!(config-memoize (aggregate sum)) !(memoize arrow-py-forward) "
            "(= (arrow-py-forward $x) $x) "
            "(= (arrow-py-forward $x) (+ $x 1)) "
            "(= (arrow-py-forward $x) (+ $x 2)) !(arrow-py-forward 5)"
        )
        assert answers[-1] == [18]
        assert product_space.run("!(is-memoized arrow-py-forward)") == [[True]]
    finally:
        product_space.run("!(config-memoize (aggregate none))")


def test_a_pending_cache_survives_a_later_author_effect(product_space):
    """A forward declaration is honoured when its annotated body arrives.

    `!(memoize arrow-py-forward)` names a function that has no equations yet,
    so there is nothing to inspect at admission; the annotation and the body
    both land afterwards. This used to be the one shape the library could still
    refuse late, and it refused the DECLARATION rather than the cache, so an
    author who annotated their own function was told to delete somebody else's
    cached definition first.
    """
    product_space.run(
        "!(import! &self (library lib_memo)) !(memoize arrow-py-forward) "
        "(: arrow-py-forward (-[det,writesState]-> Number Number)) "
        "(= (arrow-py-forward $x) $x)"
    )
    rows = product_space._at("&metta").match(S.effect(S.arrow_py_forward, V.effect))
    assert [str(row.effect) for row in rows] == ["writesState"]
    assert product_space.run("!(is-memoized arrow-py-forward)") == [[True]]
    assert product_space.eval(S.arrow_py_forward(1)) == [1]


def test_a_forward_cached_body_keeps_an_annotated_dependency(product_space):
    """A dependency's annotation does not withdraw a caller's cache.

    The body compiles after the cache is declared, and it calls a function
    whose author annotated it `writesState`. Compiling it used to raise, from a
    `function_clauses_changed` handler installed once per cached name; the
    handler is gone with the check it existed for.
    """
    product_space.run(
        "!(import! &self (library lib_memo)) "
        "(: arrow-py-writer (-[det,writesState]-> Number Number)) "
        "(= (arrow-py-writer $x) $x) !(memoize arrow-py-forward) "
        "(= (arrow-py-forward $x) (arrow-py-writer $x)) "
    )
    assert product_space.run("!(arrow-py-forward 1)") == [[1]]
    assert product_space.run("!(is-memoized arrow-py-forward)") == [[True]]
    assert (
        product_space.effect_plan(S.arrow_py_forward(1)).effect is EffectClass.writesState
    )


@pytest.mark.parametrize("cached", ["arrow-py-f", "arrow-py-caller"])
@pytest.mark.parametrize("elsewhere", [False, True])
def test_a_late_effect_lands_while_a_dependent_cache_is_live(product_space, cached, elsewhere):
    """A new author assertion lands beside a direct or caller cache.

    The annotation is stored, the plan reports it, and the cache keeps
    answering; whether that cache should have been declared over this function
    is the question the declaring program already answered.
    """
    product_space.run(
        "(: arrow-py-f (-> Number Number)) (= (arrow-py-f $x) $x) "
        "(: arrow-py-caller (-> Number Number)) "
        "(= (arrow-py-caller $x) (arrow-py-f $x)) "
        f"!(import! &self (library lib_memo)) !(memoize-exact {cached})"
    )
    assert product_space.eval(S[cached](1)) == [1]
    declaration = "(: arrow-py-f (-[det,writesState]-> Number Number))"
    with product_space._new_space() as other:
        owner = other if elsewhere else product_space
        owner.run(declaration)
        assert product_space.effect_plan(S.arrow_py_f(1)).effect is EffectClass.writesState
        assert declaration in {str(atom) for atom in owner.atoms()}
        assert product_space.eval(S[cached](1)) == [1]
        assert product_space.run(f"!(is-memoized {cached})") == [[True]]


def test_a_failed_late_annotation_restores_plain_callers(product_space, tmp_path):
    """Source rollback removes the compiler checkpoint along with its policy."""
    product_space.run(
        "(: arrow-py-f (-> Number Number)) "
        "(= (arrow-py-f $x) $x) (= (arrow-py-f $x) $x) "
        "(= (arrow-py-caller $x) (arrow-py-f $x))"
    )
    assert product_space.eval(S.arrow_py_caller(1)) == [1, 1]
    source = tmp_path / "arrow-late-failed.metta"
    source.write_text(
        "(: arrow-py-f (-[det]-> Number Number)) "
        "!(pragma! arrow-unsupported-setting true)",
        encoding="utf-8",
    )
    with pytest.raises(MettaError):
        product_space.load(source)
    assert product_space.run(
        "!(with-pragma! ((verify-cardinality true)) (arrow-py-caller 1))"
    ) == [[1, 1]]
    assert product_space.effect_plan(S.arrow_py_f(1)).effect is EffectClass.pureStructural


def test_dropped_memo_owners_do_not_block_a_reused_space(product_space):
    """A dying table and its metadata leave before a space name is reused."""
    product_space.run("!(import! &self (library lib_memo))")
    with product_space._new_space() as donor:
        donor.run(
            "(: arrow-py-drop (-> Number Number)) (= (arrow-py-drop $x) $x) "
            "!(memoize-exact arrow-py-drop)"
        )
        assert donor.eval(S.arrow_py_drop(1)) == [1]
    with product_space._new_space() as successor:
        successor.run(
            "(: arrow-py-drop (-[det,writesState]-> Number Number)) "
            "(= (arrow-py-drop $x) $x)"
        )
        assert successor.run("!(is-memoized arrow-py-drop)") == [[False]]
        assert successor.eval(S.arrow_py_drop(1)) == [1]
        assert successor.effect_plan(S.arrow_py_drop(1)).effect is EffectClass.writesState


def test_a_removed_cache_owner_retires_while_another_definition_remains(product_space):
    """A surviving namesake cannot keep a removed owner's cache enabled."""
    product_space.run(
        "!(import! &self (library lib_memo)) "
        "(: arrow-py-shared (-> Number Number)) (= (arrow-py-shared $x) $x) "
        "!(memoize-exact arrow-py-shared)"
    )
    with product_space._new_space() as other:
        other.run("(= (arrow-py-shared $x) (+ $x 1))")
        product_space.run("!(remove-atom &self (= (arrow-py-shared $x) $body))")
        assert product_space.run("!(is-memoized arrow-py-shared)") == [[False]]
        product_space.run(
            "(: arrow-py-shared (-[det,writesState]-> Number Number)) "
            "(= (arrow-py-shared $x) $x)"
        )
        assert product_space.eval(S.arrow_py_shared(1)) == [1]
        assert other.eval(S.arrow_py_shared(1)) == [2]


def test_retired_memo_owners_release_their_event_and_dispatch_clauses(product_space):
    """Repeated cache lives restore the seam census they started with.

    `Changed` counts a clause memoization no longer installs. It stays in the
    census as the pin on that: a live cache must add nothing to
    `function_clauses_changed`, because the only handler it ever put there ran
    an effect plan per module holding the name on every compiled equation.
    """
    product_space.run("!(import! &self (library lib_memo))")
    census = """
        aggregate_all(count,
            clause(seam:dispatch_call('arrow-py-hooks', _, _, _), _), Dispatch),
        aggregate_all(count,
            clause(seam:function_clauses_changed('arrow-py-hooks'), _), Changed),
        aggregate_all(count,
            clause(seam:atom_removed(_, [=, ['arrow-py-hooks'|_], _]), _), Atom),
        aggregate_all(count,
            clause(seam:function_removed('arrow-py-hooks'), _), Removed)
    """
    before = product_space.runtime.once(census)
    for _ in range(3):
        with product_space._new_space() as space:
            space.run(
                "(: arrow-py-hooks (-> Number Number)) "
                "(= (arrow-py-hooks $x) $x) !(memoize-exact arrow-py-hooks)"
            )
            assert space.eval(S.arrow_py_hooks(1)) == [1]
            live = product_space.runtime.once(census)
            assert live["Dispatch"] == before["Dispatch"] + 1
            assert live["Changed"] == before["Changed"]
            space.clear()
            assert product_space.runtime.once(census) == before


BULK_CLEAR_SIZES = (0, 200, 2000)
# What the two data sizes decide is which pass ran, so the case bounds the
# GROWTH between them and not the cost itself: the same clear costs 4,602
# inferences in a fresh process and 14,617 in a pytest worker that has already
# run other files. The removal funnel charges about 65 inferences an atom, so
# routing this data through it grows by more than 110,000. The bulk pass
# charges nothing per atom in a controlled process, measured at 0.000 an atom
# at 200, 2,000 and 20,000 atoms, with and without a capacity counter,
# lib_tabling and a live subscription on another space; a worker carrying other
# files' state has been seen at 2.2, which is not that funnel and is not
# explained. Ten an atom sits six times from each.
BULK_CLEAR_GROWTH = 10 * (BULK_CLEAR_SIZES[2] - BULK_CLEAR_SIZES[1])


def live_removal_hooks(root):
    """Every removed-atom hook clause head the process holds.

    A red bulk-clear case cannot be attributed without them: the pass it
    measures is refused by whichever hook the census will not call idle, and
    which hooks are live depends on what else has run in the same process.
    """
    return root.runtime.once(
        "findall(_Text, ( seam:atom_hook_clause(removed, _Ref), "
        "clause(_Clause, _, _Ref), strip_module(_Clause, _, _Head), "
        "term_string(_Head, _Text) ), Heads)"
    )["Heads"]


def bulk_clear_costs(root, function, data):
    """Clear a memoized space at each data size and return the last two costs.

    The size-zero life warms the cache machinery, so the two measured clears
    differ in their stored data and nothing else.
    """
    counts = []
    for size in BULK_CLEAR_SIZES:
        with root._new_space() as space:
            space.run(
                f"(: {function} (-> Number Number)) "
                f"(= ({function} $x) $x) "
                f"!(memoize-exact {function})"
            )
            space.add(*(data(value) for value in range(size)))
            with root.stats() as measured:
                space.clear()
            if size:
                counts.append(measured.inferences)
            assert list(space.atoms()) == []
            assert space.run(f"!(is-memoized {function})") == [[False]]
    return counts


def test_equation_observers_keep_plain_data_clear_bulk(product_space):
    """Retiring a memo owner must not enumerate unrelated data through hooks."""
    product_space.run("!(import! &self (library lib_memo))")
    counts = bulk_clear_costs(product_space, "arrow-py-bulk-memo", S.arrow_py_plain_data)
    assert counts[1] - counts[0] <= BULK_CLEAR_GROWTH, (
        counts,
        live_removal_hooks(product_space),
    )


def test_a_hook_that_names_another_space_keeps_the_bulk_clear(product_space):
    """A hook clause whose head names a space cannot fire for a different one.

    lib_tabling watches `&metta` for its (tabled ...) rows, and that single
    standing clause used to make every other space's clear walk its data atom
    by atom, because no host owns the clause and the census had no way to read
    the space out of its own head.
    """
    product_space.run("!(import! &self (library lib_memo))")
    product_space.run("!(import! &self (library lib_tabling))")
    counts = bulk_clear_costs(product_space, "arrow-py-named-hook", S.arrow_py_named_data)
    assert counts[1] - counts[0] <= BULK_CLEAR_GROWTH, (
        counts,
        live_removal_hooks(product_space),
    )


@pytest.mark.parametrize("atomicity", [None, "best-effort"])
def test_a_foreign_product_refuses_when_its_storage_cannot_roll_back(product_space, atomicity):
    """A partial provider write cannot separate the assertion from its catalog row."""
    if not product_space.runtime.once("current_predicate('mork-add-atoms'/3)")["truth"]:
        pytest.skip("MORK is not loaded")
    name = "&mork:arrow-product-refusal"
    space = product_space._at(name)
    try:
        if atomicity is not None:
            space.atomicity(atomicity)
        space.run(
            "(: arrow-py-foreign (-> Number Number)) "
            "(= (arrow-py-foreign $x) $x)"
        )
        assert space.eval(S.arrow_py_foreign(1)) == [1]
        declaration = "(: arrow-py-foreign (-[det,writesState]-> Number Number))"
        with pytest.raises(MettaError, match="transactional storage"):
            space.run(declaration)
        assert declaration not in {str(atom) for atom in space.atoms()}
        assert space.eval(S.arrow_py_foreign(1)) == [1]
        assert list(product_space._at("&metta").match(S.effect(S.arrow_py_foreign, V.effect))) == []
    finally:
        space.drop()
        if atomicity is not None:
            product_space._at("&metta").remove(S.writes(S[name], S.best_effort))
