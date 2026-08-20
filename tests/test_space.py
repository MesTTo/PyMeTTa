"""Purpose: engine-backed tests for the MeTTa runtime surface: run, load,
space edits, queries, eval, parse, and the semantics matching the CLI's own.
Guarantees:
  - run(), run_status() and load() register a source's whole signature set
    before processing any of its forms, as the engine's file reader does, so a
    `!` may name a function the same source defines lower down [tested
    test_a_source_registers_every_signature_before_any_form_runs,
    test_run_status_registers_signatures_before_any_form_runs]
  - an equation for a name SWI imports into the engine shadows it inside the
    space that wrote it and leaves the engine's own predicate answering, so
    the engine survives what used to brick it [tested
    test_a_system_predicate_survives_an_equation_for_its_name]
  - a write into one space never removes atoms from another [tested
    test_adding_in_one_space_never_removes_atoms_from_another]
  - copy() answers a space that holds what its source holds and answers what
    its source answers, generated specializations included [tested
    test_a_copy_reproduces_the_space_it_copied]
  - run() preserves a runnable variable's source spelling through collection
    and the public wire [tested test_variable_names_survive_to_the_printer]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re

import pytest

import petta
from petta import (
    EngineError,
    MeTTa,
    MettaOperationError,
    MettaSyntaxError,
    PettaError,
    S,
    StrictError,
    TimeLimitError,
    V,
    _engine,
    alpha_eq,
    decode,
    expr,
    parse,
    val,
)
from petta.atoms import Gnd, Var
from petta.foreign import SpaceProvider, register_provider, unregister_provider


@pytest.fixture()
def m(metta):
    """A fresh anonymous space per test, on the shared engine."""
    return metta.new_space()


def test_run_groups_answers_per_directive(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    r = metta.run("!(+ 1 2)\n!(superpose (a b))")
    assert r == [[3], [S.a, S.b]]


def test_run_tutorial_shape(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    r = metta.run("(= (foo42) boo)\n!(foo42)\n!(match &self (= (foo42) $b) $b)")
    assert r[0] == [S.boo]
    assert r[1] == [S.boo]


def test_run_booleans_and_strings(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    r = metta.run('!(> 3 2)\n!(repr 42)')
    assert r[0] == [True]
    assert r[1] == ["42"]


def test_run_syntax_error_is_loud(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(MettaSyntaxError) as failure:
        metta.run("! (broken")
    assert "line 1" in str(failure.value)
    assert "Unknown error term" not in str(failure.value)
    assert "metta_control_signal" not in str(failure.value)


def test_an_undefined_head_inside_arithmetic_is_left_as_written(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # An undefined head reduces to itself, so the arithmetic around it has an
    # argument whose type decides nothing and the whole call stays as written.
    # It used to be a hard engine error that took the rest of the file with it
    # [source: LeaTTa tests/semantics/grounded/07-partial-core.metta].
    assert metta.run("!(+ 1 (no-such-function-anywhere 2))") == [
        [parse("(+ 1 (no-such-function-anywhere 2))")]
    ]


@pytest.mark.parametrize(
    ("source", "answer"),
    [
        ("!(+ 1 a)", "(+ 1 a)"),
        ("!(< 1 a)", "(< 1 a)"),
        ("!(min-atom (a b))",
         '(Error (min-atom (a b)) "Only numbers are allowed in expression: (a b)")'),
        ("!(and True 5)", "(Error (and True 5) (BadArgType 2 Bool Number))"),
    ],
)
def test_an_operation_that_cannot_compute_answers_rather_than_raising(metta, source, answer):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # MeTTa's error channel is an ANSWER, so the parts arrive as data and the
    # form after the refusal still runs.
    assert [str(a) for group in metta.run(source) for a in group] == [answer]


@pytest.mark.parametrize(
    ("source", "operation", "expected", "culprit"),
    [
        ("!(reduce a)", "reduce", "list", "a"),
        ("!(change-state! (State 5) 6)", "change-state!", "atom", ["State", 5]),
    ],
)
def test_operation_error_carries_its_parts(metta, source, operation, expected, culprit):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The engine names the written operation in the error term, so the parts
    # arrive as data rather than as text a caller would have to parse. These
    # two are structural refusals rather than a grounded operation declining a
    # value, so they are still raises.
    with pytest.raises(MettaOperationError) as failure:
        metta.run(source)
    assert failure.value.operation == operation
    assert failure.value.kind == "type_error"
    assert failure.value.expected == expected
    assert failure.value.culprit == culprit
    assert isinstance(failure.value, EngineError)
    assert "classifier failed" not in str(failure.value)


def test_an_operation_error_keeps_the_variables_the_source_wrote(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A variable inside a culprit must render, or (a $x) and an absent part
    # both arrive as None and read alike.
    with pytest.raises(MettaOperationError) as failure:
        m.run("!(change-state! (a $x) 6)")
    assert failure.value.culprit == ["a", "$_0"]
    with pytest.raises(MettaOperationError) as absent:
        m.run("!(/ 1 0)")
    assert absent.value.kind == "evaluation_error"
    assert absent.value.expected is None
    assert absent.value.culprit is None


def test_engine_error_without_an_operation_stays_plain(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A missing import carries an operation name in its context too, but it is
    # not a builtin refusing a value, so classification must not claim it.
    with pytest.raises(EngineError) as failure:
        metta.run('!(import! &self "definitely-not-here.metta")')
    assert not isinstance(failure.value, MettaOperationError)


def test_reserved_kinds_win_over_operation_classification(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(MettaSyntaxError) as failure:
        metta.run("! (broken")
    assert not isinstance(failure.value, MettaOperationError)


@pytest.mark.parametrize(
    ("setup", "source", "status"),
    [
        ("(= (d $x) (* $x 2))", "(d 4)", "value"),
        ("", "(+ 1 2)", "value"),
        ("", "(quote (a b))", "value"),
        ("", "(Point 1 2)", "not-reducible"),
        ("", "(fct 5)", "not-reducible"),
        ("", "(empty)", "empty"),
        ("(= (only-zero 0) yes)", "(only-zero 7)", "empty"),
    ],
)
def test_eval_status_reports_the_four_outcomes(m, setup, source, status):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A pruned branch and an unevaluated term look alike in the answers
    # alone, which is exactly what this separates.
    if setup:
        m.run(setup)
    reported = m.eval_status(parse(source))
    assert [kind for kind, _ in reported] == [status]
    if status == "empty":
        assert reported[0][1] is None
    else:
        assert reported[0][1] is not None


def test_run_status_reports_each_directive(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (d $x) (* $x 2))")
    reported = m.run_status("!(d 4)\n!(Point 1 2)\n!(empty)")
    assert [[kind for kind, _ in group] for group in reported] == [
        ["value"],
        ["not-reducible"],
        ["empty"],
    ]


def test_strict_refuses_only_what_did_not_reduce(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (d $x) (* $x 2))")
    with pytest.raises(StrictError) as failure:
        m.run("!(d 4)\n!(fct 5)", strict=True)
    assert failure.value.directive == 2
    assert str(failure.value.term) == "(fct 5)"
    assert "not reducible" in str(failure.value)


@pytest.mark.parametrize(
    "source",
    [
        "!(+ 1 2)",
        "!(quote (a b))",
        "!(empty)",
        "!(superpose ((Node 1) (Node 2)))",
    ],
)
def test_strict_accepts_a_pruned_branch_and_every_reduction(m, source):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Each of these once raised, because an empty answer and an unevaluated
    # term were read as the same thing.
    m.run(source, strict=True)


def test_strict_is_opt_in(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert m.run("!(fct 5)") == [[parse("(fct 5)")]]


def test_add_query_atoms(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.Parent(S.Tom, S.Bob), S.Parent(S.Bob, S.Ann))
    rows = m.query(S.Parent(V.x, S.Bob))
    assert rows.columns == ("x",)
    assert [r.x for r in rows] == [S.Tom]


def test_query_join(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.Edge(S.a, S.b), S.Edge(S.b, S.c), S.Edge(S.c, S.d))
    rows = m.query(S.Edge(V.x, V.y), S.Edge(V.y, V.z))
    assert {(r.x, r.z) for r in rows} == {(S.a, S.c), (S.b, S.d)}


def test_query_projection_and_column(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.age(S.Ada, 36), S.age(S.Bob, 41))
    rows = m.query(S.age(V.who, V.years))
    assert set(rows["who"]) == {S.Ada, S.Bob}
    assert sorted(rows["years"], key=int) == [36, 41]


def test_query_surfaces_share_column_order(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    patterns = (
        S.left(V.first, V.second, V.first, V._),
        S.right(V.third, V.second),
    )
    expected = ("first", "second", "third")
    assert m.query(*patterns).columns == expected
    assert m.prepare(*patterns).columns == expected
    with m.stream(*patterns) as cursor:
        assert cursor.columns == expected


def test_atoms_count_contains_remove_clear(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.item(1), S.item(2))
    assert m.count() == 2 and len(m) == 2
    assert S.item(1) in m
    assert S.item(3) not in m
    m.remove(S.item(1))
    assert m.count() == 1
    m.clear()
    assert m.count() == 0


def test_clear_removes_equations_too(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(parse("(= (clr-f) 77)"))
    assert m.run("!(clr-f)") == [[77]]
    m.clear()
    # The equation is gone: the call no longer reduces, it stays inert.
    assert m.run("!(clr-f)") == [[expr(S["clr-f"])]]


def test_empty_space_is_still_true(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The trap __bool__ exists for: without it bool() falls to __len__
    # and `if space:` skips an empty space it was handed on purpose.
    assert m.count() == 0
    assert bool(m) is True
    assert m


def test_getitem_queries_and_a_tuple_joins(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.edge(S.a, S.b), S.edge(S.b, S.c))
    assert set(m[S.edge(V.x, V.y)]["x"]) == {S.a, S.b}
    assert len(m["(edge $x $y)"]) == 2
    joined = m[S.edge(V.a, V.b), S.edge(V.b, V.c)]
    assert list(joined["c"]) == [S.c]


def test_getitem_refuses_a_slice_naming_the_doors(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError, match=r"query\(limit=n\)"):
        m[0:3]
    with pytest.raises(TypeError, match=r"stream\(\)"):
        m[:]


def test_delitem_removes_every_unifying_occurrence(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.edge(S.a, S.b), S.edge(S.a, S.b), S.edge(S.b, S.c))
    del m[S.edge(S.a, V.y)]
    assert m.atoms() == [S.edge(S.b, S.c)]
    with pytest.raises(KeyError):
        del m[S.edge(S.zz, V.y)]
    # remove() stays the door that reports absence instead of raising.
    assert m.remove(S.edge(S.zz, V.y)) is False


def test_ior_merges_a_space_equations_included(metta, m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    src = metta.new_space()
    src.add(parse("(= (ior-double $x) (* 2 $x))"), S.edge(S.a, S.b))
    m |= src
    assert S.edge(S.a, S.b) in m
    # The equation crossed as an atom AND compiled on arrival.
    assert parse("(= (ior-double $x) (* 2 $x))") in m
    assert m.run("!(ior-double 21)") == [[42]]


def test_ior_merges_an_iterable_and_a_registered_name(metta, m):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    m |= [S.note(1), "(note 2)"]
    assert m.count() == 2
    m |= m.space_name
    assert m.count() == 4  # a space is a multiset: self-merge doubles
    with pytest.raises(KeyError, match="space_names"):
        m |= "&never-written-space"


def test_ior_refuses_the_operands_add_would_lift(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # add({...}) lifts a dict into ONE grounded atom; iterating it here
    # would read the same operand a second way, so |= refuses it.
    with pytest.raises(TypeError, match="lift"):
        m |= {"a": 1}
    with pytest.raises(TypeError, match="lift"):
        m |= b"ab"
    with pytest.raises(TypeError, match="none of"):
        m |= 3.5
    # += keeps add()'s lifted reading: one expression atom, not two.
    m += [1, 2]
    assert m.atoms() == [expr(1, 2)]


def test_space_names_lists_the_registered_spaces(metta, m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    names = metta.space_names()
    assert names == sorted(names)
    assert "&self" in names and "&petta" in names
    assert "&named-but-never-written" not in names
    # Registration happens on WRITE, not on naming: a fresh new_space is
    # absent until its first atom lands.
    assert m.space_name not in names
    m.add(S.mark(1))
    assert m.space_name in metta.space_names()


def test_eval(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert metta.eval(S["car-atom"](expr(1, 2, 3))) == [1]
    assert metta.eval(S.superpose(expr(S.x, S.y))) == [S.x, S.y]
    assert metta.eval(expr(S["+"], 20, 22)) == [42]


def test_source_strings_are_parsed_where_atoms_are_expected(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add("(likes Ada Coffee)")
    assert m.query("(likes $who Coffee)")[0].who == S.Ada


@pytest.mark.parametrize(
    "source",
    [
        "(pair-up 1 2)",
        "(pair-up (pair-up 1 2) 3)",
        "(pair-up $a $a)",
        "(pair-up $_ $_)",
        '(pair-up "text" sym)',
        "(pair-up True 2.5)",
        "(nondeterministic)",
    ],
)
def test_a_source_target_evaluates_as_its_parsed_term_does(m, source):
    """Source text is evaluated where it is read, in one crossing.

    Parsing it in Python first crossed to the engine's reader, built an Atom
    from the wire form it answered, and walked that Atom straight back to the
    same wire form for the evaluation. Passing the text through leaves the two
    spellings of one call to agree, which is what this checks.
    """
    m.run(
        "(= (pair-up $x $y) ($x $y))\n"
        "(= (nondeterministic) 1)\n(= (nondeterministic) 2)"
    )
    from_text, from_term = m.eval(source), m.eval(parse(source))
    # Fresh variables carry machine names, so the answers agree up to renaming.
    assert [alpha_eq(a, b) for a, b in zip(from_text, from_term, strict=True)] == [
        True
    ] * len(from_text)


def test_a_source_target_shares_its_variables_by_name(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (twin $x $y) ($x $y))")
    (shared,) = m.eval("(twin $a $a)")
    (fresh,) = m.eval("(twin $b $c)")
    assert shared[0] == shared[1]
    assert fresh[0] != fresh[1]


def test_a_malformed_wire_target_is_refused(m):
    """A wire term is exactly two elements, and anything else reaching the
    engine as a list is our own encoder's bug rather than a query that
    answered nothing. Before this it failed, and findall turned that into an
    empty answer list no caller could tell from a real one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with pytest.raises(EngineError, match="petta_py_wire_term"):
        m._rt.apply_must("petta_py_eval_all", m.space_name, ["n", 1, "extra"])


def test_parse_keeps_variable_names():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    p = parse("(Parent $x Bob)")
    assert p == S.Parent(V.x, S.Bob)


def test_parse_reads_booleans_the_way_the_engine_does():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert parse("True") == Gnd(True)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    assert parse("(a False)") == expr(S.a, False)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch


def test_live_object_identity(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Model:
        pass

    model = Model()
    m.add(S.model(S.main, val(model)))
    back = m.query(S.model(S.main, V.m))[0].m
    assert decode(back) is model


def test_boxed_container_identity(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    payload = {"weights": [1, 2]}
    m.add(S.blob(val(payload)))
    assert decode(m.query(S.blob(V.d))[0].d) is payload


def test_fact_isolation_between_spaces(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    a, b = metta.new_space(), metta.new_space()
    a.add(S.fact(S.here))
    assert a.count() == 1
    assert b.count() == 0
    assert len(b.query(S.fact(V.x))) == 0


def test_default_metta_handles_share_the_self_space():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    first, second = MeTTa(), MeTTa()
    shared = S["shared-default-handle"](S.value)
    first.add(shared)
    try:
        assert shared in second
    finally:
        first.remove(shared)


def test_space_name_validation():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError):
        MeTTa("kb")


def test_load_runs_a_file(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    f = tmp_path / "prog.metta"
    f.write_text("(= (loaded-f) 5)\n!(loaded-f)\n")
    groups = metta.load(str(f))
    assert groups == [[5]]


def test_load_adds_to_existing_space(m, tmp_path):
    """A load adds the file's atoms to whatever the space already holds; it
    replaces only what that same file put there. Loading the same file twice
    is test_reload.py's job.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    first = tmp_path / "first.metta"
    second = tmp_path / "second.metta"
    first.write_text("(loaded-copy value)\n")
    second.write_text("(other-copy value)\n")

    m.add(S.existing(S.value))
    m.load(first)
    m.load(second)

    assert m.count() == 3
    assert len(m.query(S["loaded-copy"](V.value))) == 1
    assert len(m.query(S["other-copy"](V.value))) == 1


def test_why(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.Parent(S.Tom, S.Bob))
    text = m.why(S.Parent(S.Nobody, V.x))
    assert "none unifies" in text
    assert "Missing" in m.why(S.Missing(V.x))
    m.add(S.Parent(S.a, S.b, S.c))
    assert "elements" in m.why(S.Parent(V.x,))
    assert "did you mean car-atom?" in m.why(S["car-atmo"](S.value))


def test_match_patterns_are_structural(m):
    """The engine's own rule: match evaluates its space and its body, never
    the pattern. A function call written inside a pattern is data there.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.add(S.pair(S.small, S.yes))
    m.run("(= (sz-here) small)")
    # The evaluated idiom: compute first, then match the value.
    assert m.run("!(let $s (sz-here) (match (context-space) (pair $s $v) $v))") == [[S.yes]]
    # The literal idiom: the pattern (pair (sz-here) $v) matches nothing,
    # because no stored atom is literally shaped that way.
    assert m.run("!(collapse (match (context-space) (pair (sz-here) $v) $v))") == [[expr()]]


def test_bare_atoms_are_refused_loudly(m):
    """A stored atom is a non-empty expression; anything else must error,
    never vanish: the silent write was a real bug this pins.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with pytest.raises(TypeError):
        m.add(S.bare)
    with pytest.raises(TypeError):
        m.add(7)
    with pytest.raises(TypeError, match="non-empty expression"):
        m.add(expr())
    with pytest.raises(TypeError, match="non-empty expression"):
        m.remove(expr())


def test_a_bare_runnable_atom_answers_a_group(m):
    """! atom answers its group, one per directive, like any runnable.

    The arbiter's self-evaluating rule: a symbol nothing defines, a
    number, a string and a free variable each return themselves as one
    answer group (LeaTTa eval-core/self-evaluating-atoms.metta, MEASURED
    [untouched-symbol], [42], ["text"], [$free], hyperon 0.2.10
    verbatim). The reader admitted the bare form first and the run half
    answered nothing; the grouped runner treats every runnable form
    alike now, and this pins all four categories.
    """
    assert m.run("! untouched-symbol") == [[S["untouched-symbol"]]]
    assert m.run("! 42") == [[42]]
    assert m.run('! "text"') == [["text"]]
    variable_groups = m.run("! $free")
    assert len(variable_groups) == 1 and len(variable_groups[0]) == 1
    assert isinstance(variable_groups[0][0], Var)


def test_variable_names_survive_to_the_printer(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    free, repeated, first_epoch, second_epoch = m.run(
        "! $free\n"
        "! (pair $left $left)\n"
        "! (sealed () (pair $x $x))\n"
        "! (sealed ($x) (triple $x $y $y))"
    )

    assert free == [Var("free")]
    assert repeated == [expr(S.pair, Var("left"), Var("left"))]
    assert first_epoch == [expr(S.pair, Var("x#0"), Var("x#0"))]
    assert second_epoch == [
        expr(S.triple, Var("x"), Var("y#1"), Var("y#1"))
    ]
    assert str(free[0]) == "$free"
    assert str(repeated[0]) == "(pair $left $left)"


def test_remove_reports_presence_and_subtracts_one_duplicate(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    atom = S.duplicate(S.value)

    assert m.remove(atom) is False
    m.add(atom, atom)
    # Multiset subtraction: the first removal leaves the second copy, so the
    # atom is still there and the count is one, not zero.
    assert m.remove(atom) is True
    assert atom in m and m.count() == 1
    assert m.remove(atom) is True
    assert atom not in m
    assert m.remove(atom) is False


def test_object_identity_survives_the_boundary(m):
    """One live object is one box everywhere: stored, found, removed."""
    class Thing:
        pass

    thing = Thing()
    m.add(S.holds(val(thing)))
    assert S.holds(val(thing)) in m
    rows = m.query(S.holds(V.x))
    assert rows[0].x.value is thing
    assert m.remove(S.holds(val(thing))) is True
    assert S.holds(val(thing)) not in m


def test_anonymous_variables_do_not_join(m):
    """Two underscores are two fresh variables, exactly as parsed $_ $_."""
    m.add(S.duo(S.a, S.a), S.duo(S.a, S.b))
    assert len(m.query(S.duo(V._, V._))) == 2
    # And the anonymous variable never becomes a column.
    assert m.query(S.duo(V.x, V._)).columns == ("x",)


def test_new_spaces_drop_and_names_recycle(metta):
    """A dropped space's name returns to the pool, so churn does not grow
    the engine's module table; the with-block is the drop.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with metta.new_space() as scratch:
        first = scratch.space_name
        scratch.add(S.noted(S.here))
        assert len(scratch) == 1
    with metta.new_space() as again:
        assert again.space_name == first
        assert len(again) == 0
    with pytest.raises(TypeError):
        with metta:
            pass


def test_load_restores_the_working_directory(metta, tmp_path):
    """One load resolves its imports from its own directory and puts the
    process's directory back afterwards, so later runs are untouched.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    inner = tmp_path / "prog.metta"
    inner.write_text("!(+ 1 1)\n")
    before = petta.janus.query_once("working_dir(D)")
    metta.load(str(inner))
    after = petta.janus.query_once("working_dir(D)")
    assert (before or {}).get("D") == (after or {}).get("D")


def test_runtime_refuses_a_second_tree(metta):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError):
        MeTTa(petta_path="/definitely/not/this/tree")


def test_a_dropped_handle_cannot_write_into_the_name_it_released(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # new_space() pools names, so a live handle to a dropped space would
    # otherwise write into whatever space took the name next.
    dead = metta.new_space()
    released = dead.space_name
    dead.drop()
    reused = metta.new_space()
    assert reused.space_name == released
    with pytest.raises(PettaError) as failure:
        dead.add(S.ghost(1))
    assert "was dropped" in str(failure.value)
    assert reused.count() == 0
    dead.drop()  # idempotent, as closing twice is
    assert "dropped" in repr(dead)


def test_add_table_reads_records_by_value(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.p(S.a, S.b))
    rows = m.query(S.p(V.x, V.y))
    records = m.new_space()
    records.add_table(S.p, rows.to_dicts())
    # Iterating a mapping yields keys, so this once stored ("x" "y").
    assert [str(atom) for atom in records.atoms()] == ['(p "a" "b")']
    lossless = m.new_space()
    lossless.add_table(S.p, {c: rows[c] for c in rows.columns})
    assert lossless.digest() == m.digest()


def test_add_table_refuses_records_whose_key_order_drifts(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="same keys in the same order"):
        m.add_table(S.p, [{"x": 1, "y": 2}, {"y": 3, "x": 4}])


def test_the_empty_symbol_is_refused_rather_than_written_unreadably(m, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.t(S[""], 1))
    target = tmp_path / "empty.metta"
    with pytest.raises(ValueError, match="empty symbol"):
        m.save(str(target))
    assert not target.exists()


@pytest.mark.parametrize("guard", [123, "oops", 4.5, S.oops])
def test_a_where_guard_that_can_never_be_true_is_refused(m, guard):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.age(S.Ada, 36))
    with pytest.raises(TypeError, match="can never answer true"):
        m.query(S.age(V.who, V.n), where=guard)


def test_wrong_bound_types_name_the_argument(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError, match="limit must be"):
        m.query(S.age(V.who, V.n), limit="x")
    with pytest.raises(TypeError, match="timeout must be"):
        m.run("!(+ 1 2)", timeout="x")
    with pytest.raises(TypeError, match="inferences must be"):
        m.run("!(+ 1 2)", inferences="x")
    with pytest.raises(TypeError, match="space name is a string"):
        MeTTa(123)


def test_a_reserved_limit_does_not_leak_janus_framing(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("(= (spin $n) (spin (+ $n 1)))")
    with pytest.raises(TimeLimitError) as failure:
        metta.run("!(spin 0)", timeout=0.05)
    assert "0.05 second time limit" in str(failure.value)
    assert "Unknown error term" not in str(failure.value)
    assert "metta_control_signal" not in str(failure.value)


def test_build_never_hands_back_its_private_sentinel(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.p(S.a))
    rows = m.query(S.p(V.x))
    assert petta.convert.build(S.a, str) == S.a
    assert rows.build("x", str) == [S.a]


def test_a_provider_error_is_not_a_system_error(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Exploding(SpaceProvider):
        def atoms(self):
            msg = "provider exploded"
            raise RuntimeError(msg)

    register_provider(_engine.runtime(), "&exploding_probe", Exploding())
    try:
        with pytest.raises(EngineError) as failure:
            metta.space("&exploding_probe").atoms()
        # A generator body runs at the first pull, inside py_iter, where an
        # exception surfaces as SystemError naming apply_once.
        assert not isinstance(failure.value, SystemError)
        assert "provider exploded" in str(failure.value)
    finally:
        unregister_provider(_engine.runtime(), "&exploding_probe")


def test_a_provider_without_the_interface_is_refused_at_registration():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class NotAProvider:
        def match(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return iter(())

    with pytest.raises(TypeError, match="can_run"):
        register_provider(_engine.runtime(), "&not_a_provider", NotAProvider())


def test_removing_what_was_never_registered_is_reported(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(KeyError):
        metta.unregister_op("no-such-operation-anywhere")
    with pytest.raises(KeyError):
        unregister_provider(_engine.runtime(), "&no_such_provider")


def test_an_unknown_column_names_the_columns_that_exist(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.p(S.a))
    rows = m.query(S.p(V.who))
    with pytest.raises(KeyError, match="did you mean 'who'"):
        rows["wh"]


@pytest.mark.parametrize(
    ("call", "match"),
    [
        (lambda m: m.run(None), "source as a string"),
        (lambda m: m.is_function(None), "name as a string"),
        (lambda m: m.is_function_here(1), "name as a string"),
    ],
)
def test_a_wrong_argument_type_names_the_argument(m, call, match):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError, match=match):
        call(m)


def test_a_rational_tree_join_fails_the_row_instead_of_the_process(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The engine's matching is occurs-checked on purpose (the arbiter's
    # variable cases), and match_native guards its OUT template with
    # acyclic_term. The query lanes keep bindings outside that template,
    # and a cyclic join once sailed through to the row encoder and died
    # at a 53-million-frame walk. Now the cyclic candidate fails its row,
    # exactly as the same pattern behaves through match.
    m.add(parse("(rt-fact (f $x) $x)"))
    assert len(m.query(parse("(rt-fact $y $y)"))) == 0
    assert m.run("!(collapse (match (context-space) (rt-fact $y $y) hit))") == [
        [expr()]
    ]
    # The acyclic twin still answers through both doors.
    m.add(parse("(rt-fact ok ok)"))
    assert len(m.query(parse("(rt-fact $y $y)"))) == 1


def test_copy_clones_through_the_bulk_door(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    import copy as copy_module

    with metta.new_space() as original:
        original.run("(= (cp-double $x) (* $x 2))")
        original.add(parse("(cp-fact one)"))
        clone = original.copy()
        try:
            # equations copy as equations: the clone's function RUNS
            assert list(clone.eval("(cp-double 21)")) == [42]
            assert clone.count() == original.count()
            assert clone.digest() == original.digest()
            # and the spaces are independent after the clone
            clone.add(parse("(cp-fact extra)"))
            assert clone.count() == original.count() + 1
        finally:
            clone.drop()
        protocol = copy_module.copy(original)
        try:
            assert protocol.digest() == original.digest()
        finally:
            protocol.drop()


def test_eval_using_carries_identity(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # using= binds named host values into a TERM, the same vocabulary run()
    # takes for source, so reaching for eval instead of run costs no change
    # of spelling. The value crosses by identity, not as a printed form.
    class Blob:
        def __init__(self, n):
            self.n = n

    blob = Blob(7)
    m.register_op(lambda o: o.n, name="blob-n", raw=True, typed=False)
    m.run("(= (describe $o) (Seen (blob-n $o)))")
    try:
        assert str(m.one("(describe o)", using={"o": blob})) == "(Seen 7)"
        assert m.eval("(describe o)", using={"o": blob}) == [parse("(Seen 7)")]
        assert str(m.first("(describe o)", using={"o": blob})) == "(Seen 7)"
        # a built atom is the same door
        assert str(m.one(parse("(describe o)"), using={"o": blob})) == "(Seen 7)"
        # and the object arrived itself, not a copy
        assert m.one("(blob-n o)", using={"o": blob}) == 7
    finally:
        m.unregister_op("blob-n")


def test_eval_using_refuses_to_pretend_it_composes_with_residuals(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(petta.PettaError, match="do not compose"):
        m.eval("(+ 1 2)", using={"x": 1}, residuals=True)


def test_a_source_registers_every_signature_before_any_form_runs(metta):
    """The engine's file reader registers a source's WHOLE signature set
    before processing any of its forms, so a `!` may name a function the same
    source defines lower down [source: engine/filereader.pl
    register_parsed_signatures/1]. run() and load() reach the engine through
    bindings/python/petta/shim.pl rather than through that reader, and until this they
    skipped the pass: seven shipped examples passed in the engine and failed
    here with `Domain error: function_symbol expected` [measured 2026-08-18].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.run("!(import! &self (library lib_reflect))")
    groups = metta.run(
        "!(engine-knows p111-later)\n"
        "!(engine-arity p111-later)\n"
        "(= (p111-later $x) (+ $x 1))\n"
    )
    assert groups == [[True], [2]]


def test_run_using_registers_signatures_over_the_forms_that_will_run(metta):
    """using= rewrites the parsed forms before they run, so the pass reads
    what will actually run rather than the text it was read from.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.run("!(import! &self (library lib_reflect))")
    groups = metta.run(
        "!(engine-knows p111-scaled)\n(= (p111-scaled $x) (* $x factor))\n",
        using={"factor": 3},
    )
    assert groups == [[True]]
    assert metta.run("!(p111-scaled 4)") == [[12]]


def test_run_status_registers_signatures_before_any_form_runs(metta):
    """run_status reads a source through its own entry point, so it carries
    the same pre-pass.

    What the pass registers is the SIGNATURE, not the clauses: `!(p111-status
    4)` above its own definition still cannot answer, in either configuration,
    because nothing has compiled a clause for it yet. A `!` that NAMES the
    function is what this buys, which is how `memoize` is written.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.run("!(import! &self (library lib_reflect))")
    reported = metta.run_status(
        "!(engine-knows p111-status)\n(= (p111-status $x) (* $x 2))"
    )
    assert [[(kind, str(answer)) for kind, answer in group] for group in reported] == [
        [("value", "True")]
    ]


def test_a_declaration_that_cannot_type_what_the_source_defines_is_refused(metta):
    """The other half the shared pre-pass brings: the engine refuses a
    non-arrow type on a function the same source defines, before any of that
    source's forms run, and run() went straight past it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with pytest.raises(EngineError, match="is not an arrow"):
        metta.run("(: p111-decl Number)\n(= (p111-decl $x) $x)\n")


def test_load_memoizes_a_function_the_same_file_defines_lower_down(metta, tmp_path):
    """The shape the seven shipped examples are written in: `!(memoize f)`
    reads fun/1, and under load() nothing had asserted it yet
    [source: lib/lib_memo.pl:888].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    source = tmp_path / "p111_memo.metta"
    source.write_text(
        "!(import! &self (library lib_memo))\n"
        "!(memoize p111-sq)\n"
        "(= (p111-sq $x) (* $x $x))\n"
        "!(p111-sq 9)\n"
    )
    assert metta.load(source)[-2:] == [[True], [81]]


def _atom_multiset(space):
    """A space's atoms as a comparable multiset. Each read hands back fresh
    variables, so the printed names differ between two reads of one atom and
    comparing the raw strings compares nothing.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    return sorted(re.sub(r"\$_\d+", "$V", str(atom)) for atom in space)


def test_adding_in_one_space_never_removes_atoms_from_another(metta):
    """A specialization belongs to the space whose code triggered it, and
    invalidate_specializations/2's predecessor read ho_specialization/3's
    module argument
    with a WILDCARD, so an equation added in ANY space invalidated that name's
    specializations in EVERY space and took their stored equations with them.

    copy() is where it showed: it enumerates the source and re-adds every atom
    into a fresh space, so re-adding the base equation THERE stripped the
    specialization's atom from HERE and the source of a copy lost atoms to the
    copy. It was the suite's one known flake, `assert 51 == 47`, 1 firing in 12
    parallel runs, with no concurrency involved.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.run("(= (p6-inc $x) (+ $x 1))")
    metta.run("(= (p6-map $f $x) ($f $x))")
    metta.run("(= (p6-use $z) (p6-map p6-inc $z))")
    assert metta.run("!(p6-use 1)") == [[2]]

    before = _atom_multiset(metta)
    # The specialization the call above planned is a stored equation of the
    # source space, so this is not an abstract multiset: it is what copy() went
    # on to delete.
    assert any("p6-map_Spec_" in atom for atom in before), before

    clone = metta.copy()
    try:
        assert _atom_multiset(metta) == before
    finally:
        clone.drop()

    # The direct form, with no copy in it: two spaces defining one name, and
    # neither losing atoms to the other.
    with metta.new_space() as other:
        other.run("(= (p6-map $f $x) ($f $x))")
        assert _atom_multiset(metta) == before
        other_before = _atom_multiset(other)
        metta.run("(= (p6-map $f $x) ($f $x))")
        assert _atom_multiset(other) == other_before


def test_a_system_predicate_survives_an_equation_for_its_name(metta):
    """`!(add-atom &self (= (b_setval $a) clash))` used to brick the engine.

    `&self` compiled into the module the engine itself resolves in, so the
    equation did not shadow `b_setval/2`, it REPLACED it: the predicate went
    from imported_from(system) to a local definition and every engine path
    through it stopped. The translator emits `b_setval` into the clause bodies
    it builds, so the very next form failed to translate, and
    `with_metta_module/2` failed, which takes every named space with it.

    Refusing the equation is the wrong fix, measured: the guard forbids 78
    names in `&self`, `plus` among them, and `plus` is an ordinary MeTTa
    function name a shipped example is right to use. Giving `&self` a module of
    its own makes the same equation a local shadow, so the engine keeps the
    predicate and MeTTa keeps the name.
    """
    metta.run("!(add-atom &self (= (b_setval $a) clash))")
    try:
        # MeTTa's name now answers what the equation says.
        assert metta.run("!(b_setval anything)") == [[S.clash]]
        # A form the engine has to translate still translates.
        assert metta.run("!(+ 1 2)") == [[3]]
        # And a named space still runs, which is with_metta_module/2 working.
        with metta.new_space() as other:
            assert other.run("!(+ 1 2)") == [[3]]
    finally:
        metta.run("!(remove-atom &self (= (b_setval $a) clash))")
    # The shadow goes with the equation, so the name is MeTTa's only while an
    # equation says so, and removing it leaves the term unreduced rather than
    # leaving a clause behind in the space's module.
    assert metta.run("!(b_setval anything)") == [[parse("(b_setval anything)")]]
    assert metta.run("!(+ 1 2)") == [[3]]


def test_a_copy_reproduces_the_space_it_copied(metta):
    """copy() enumerates a space and re-adds every atom into a fresh one, so a
    specialization the clone DERIVES for itself used to land on top of the
    copied one: a four-atom space cloned to six and answered its query three
    times instead of once.

    The specializer owns the names it generates, so an equation arriving for a
    name this module already derived carries nothing new.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with metta.new_space() as source:
        source.run("(= (cp-inc $x) (+ $x 1))")
        source.run("(= (cp-map $f $x) ($f $x))")
        source.run("(= (cp-use $z) (cp-map cp-inc $z))")
        assert source.run("!(cp-use 1)") == [[2]]
        # The specialization is stored content, which is why the clone gets it.
        assert any("cp-map_Spec_" in str(atom) for atom in source.atoms())

        clone = source.copy()
        try:
            assert clone.count() == source.count()
            assert clone.digest() == source.digest()
            assert clone.run("!(cp-use 1)") == source.run("!(cp-use 1)")
        finally:
            clone.drop()
