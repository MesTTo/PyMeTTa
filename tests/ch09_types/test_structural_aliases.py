"""Purpose: verify structural aliases through the public Python engine doors.

Guarantees: source, file, named-space and reflective calls share lexical
substitution and live mutation repair [tested: test_structural_aliases.py;
commit=WORKTREE].
Guarantees: nominal lookup costs count only metta_py_eval_all/3 execution,
excluding unrelated Python finalizer work between calls [tested:
test_nominal_subtyping_does_not_scan_unrelated_declarations; commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393].
Owns resources: fixtures close spaces and pytest removes temporary files.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import MeTTa, S, V, arrow, typed


@pytest.fixture
def m():
    """Release each declaration scope after its fixture."""
    with MeTTa().space() as space:
        yield space


def flattened(groups):
    """Retain source answer order while discarding runnable group boundaries."""
    return [str(answer) for group in groups for answer in group]


@pytest.mark.parametrize("route", ["source", "file", "reflective"])
def test_aliases_and_literal_types_agree_through_every_public_door(m, tmp_path, route):
    """A whole arrow alias reaches preparation and nested tuple checking."""
    declarations = [
        "(: Count (Alias Number))",
        "(: Row (Alias (Count String)))",
        "(: Signature (Alias (-> Row Row)))",
        "(: probe Signature)",
        "(= (probe $x) $x)",
    ]
    calls = '!(probe (1 "s"))\n!(get-type probe)\n!(get-type (probe (1 "s")))'
    if route == "reflective":
        for declaration in declarations:
            m.add(m.parse(declaration))
        actual = [str(a) for a in m.eval(S.probe((1, "s")))]
        actual += flattened(m.run("!(get-type probe)\n!(get-type (probe (1 \"s\")))"))
    elif route == "file":
        path = tmp_path / "aliases.metta"
        path.write_text("\n".join(declarations) + "\n" + calls, encoding="utf-8")
        actual = flattened(m.load(path))
    else:
        actual = flattened(m.run("\n".join(declarations) + "\n" + calls))
    with MeTTa().space() as direct:
        expected = flattened(direct.run(
            "(: probe (-> (Number String) (Number String)))\n"
            "(= (probe $x) $x)\n" + calls
        ))
    assert actual == expected == ["(1 \"s\")", "(-> (Number String) (Number String))", "(Number String)"]


def test_count_refuses_strings_and_preserves_the_source_type_in_diagnostics(m):
    """Failure retains Count and reports the expanded arrow beside it."""
    m.run("(: Count (Alias Number)) (: count-id (-> Count Count)) (= (count-id $n) $n)")
    assert m.eval(S["count-id"](1)) == [1]
    assert flattened(m.run('!(count-id "bad")')) == [
        '(Error (count-id "bad") (BadArgType 1 Count String '
        '(TypeExpansion (-> Count Count) (-> Number Number))))'
    ]


def test_an_atom_alias_preserves_the_argument_and_result_barriers(m):
    """Literal, retained, eval and constructed calls all return the held sum."""
    m.run("(: Held (Alias Atom)) (: hold (-> Held Held)) (= (hold $x) $x) (= (caller) (hold (+ 1 2)))")
    assert flattened(m.run("!(hold (+ 1 2)) !(caller) !(eval (hold (+ 1 2)))")) == ["(+ 1 2)"] * 3
    assert m.eval(S.hold(S["+"](1, 2))) == [S["+"](1, 2)]


def test_nested_aliases_and_rhs_variables_keep_their_relationships(m):
    """Two Duo occurrences freshen independently, but each pair stays related."""
    m.run("(: Duo (Alias ($t $t))) (: pairs (-> $t Duo Duo $t)) (= (pairs $n $a $b) $n)")
    assert m.eval(S.pairs(7, (1, 2), ("x", "y"))) == [7]
    refused = m.eval(S.pairs(7, (1, "bad"), (2, 3)))
    assert len(refused) == 1 and refused[0][0] == S.Error
    m.run("(: Count (Alias Number)) (: Row (Alias (Count String))) (: Nested (Alias (Row Bool))) (: nest (-> Nested Nested)) (= (nest $x) $x)")
    assert flattened(m.run('!(nest ((1 "s") True))')) == ['((1 "s") True)']


def test_local_shadowing_does_not_capture_names_inside_an_inherited_alias(m):
    """The shared alias keeps its declaration owner when a child binds its RHS."""
    root = MeTTa("&self").self
    suffix = uuid4().hex
    inner, outer = S[f"AliasInner{suffix}"], S[f"AliasOuter{suffix}"]
    shared = [typed(inner, S.Alias(S.Number)), typed(outer, S.Alias(inner))]
    for declaration in shared:
        root.add(declaration)
    try:
        m.add(typed(inner, S.Alias(S.String)))
        m.add(typed(S.inherited, arrow(outer, outer)))
        m.add(typed(S.local, arrow(inner, inner)))
        m.add(m.parse("(= (inherited $x) $x)"), m.parse("(= (local $x) $x)"))
        assert m.eval(S.inherited(7)) == [7]
        assert m.eval(S.local("local")) == ["local"]
        assert m.eval(S.inherited("local"))[0][0] == S.Error
        assert m.eval(S.local(7))[0][0] == S.Error
        m.remove(typed(inner, S.Alias(S.String)))
        assert m.eval(S.local(7)) == [7]
    finally:
        for declaration in reversed(shared):
            root.remove(declaration)


def test_late_alias_addition_and_removal_repair_retained_calls(m):
    """The same compiled caller changes when a previously opaque name changes."""
    m.run("(: identity (-> Count Count)) (= (identity $x) $x) (= (caller $x) (identity $x))")
    assert m.eval(S.caller(7))[0][0] == S.Error
    alias = typed(S.Count, S.Alias(S.Number))
    m.add(alias)
    assert m.eval(S.caller(7)) == [7]
    m.remove(alias)
    assert m.eval(S.caller(7))[0][0] == S.Error


def test_atom_alias_arrival_repairs_masks_and_definition_finality(m):
    """A compiled definition and its caller both change their evaluation view."""
    m.run("(: hold (-> FutureHeld FutureHeld)) (= (hold $x) $x) (= (caller) (hold (+ 1 2)))")
    assert m.eval(S.caller()) != [S["+"](1, 2)]
    alias = typed(S.FutureHeld, S.Alias(S.Atom))
    m.add(alias)
    assert m.eval(S.caller()) == [S["+"](1, 2)]
    m.remove(alias)
    assert m.eval(S.caller()) != [S["+"](1, 2)]


def test_a_failed_cycle_and_conflict_leave_previous_behavior_intact(m):
    """Alias errors carry paths or both definitions and roll back other writes."""
    m.run("(: Count (Alias Number)) (: identity (-> Count Count)) (= (identity $x) $x)")
    assert m.eval(S.identity(7)) == [7]

    def conflicting_edit():
        m.add(typed(S.Other, S.Alias(S.Bool)))
        m.add(typed(S.Count, S.Alias(S.String)))

    with pytest.raises(Exception, match=r"conflicting type alias|metta_type_alias_conflict"):
        m.transaction(conflicting_edit)
    assert m.eval(S.identity(7)) == [7]
    assert not list(m.match(typed(S.Other, V.type)))
    m.add(typed(S.CycleA, S.Alias(S.CycleB)))
    with pytest.raises(Exception, match=r"cyclic type alias|metta_type_alias_cycle") as caught:
        m.add(typed(S.CycleB, S.Alias(S.CycleA)))
    assert "CycleA" in str(caught.value) and "CycleB" in str(caught.value)
    assert m.eval(S.identity(7)) == [7]


def test_file_replacement_updates_aliases_and_failed_replacement_restores_them(m, tmp_path):
    """Reload withdraws raw aliases before accepting their replacement."""
    path = tmp_path / "alias-source.metta"
    path.write_text("(: Count (Alias Number))", encoding="utf-8")
    m.load(path)
    m.run("(: identity (-> Count Count)) (= (identity $x) $x) (= (caller $x) (identity $x))")
    assert m.eval(S.caller(7)) == [7]
    path.write_text("(: Count (Alias String))", encoding="utf-8")
    m.load(path)
    assert m.eval(S.caller("s")) == ["s"]
    assert m.eval(S.caller(7))[0][0] == S.Error
    path.write_text("(: Count (Alias Count))", encoding="utf-8")
    with pytest.raises(Exception, match=r"cyclic type alias|metta_type_alias_cycle"):
        m.load(path)
    assert m.eval(S.caller("s")) == ["s"]


def test_raw_reflection_and_scoped_type_inspection_keep_distinct_views(m):
    """Stored spelling survives while each type observer returns its expansion."""
    m.run("(: Count (Alias Number)) (: item Count)")
    assert [row.type for row in m.match(typed(S.item, V.type))] == [S.Count]
    assert flattened(m.run("!(get-type item)")) == ["Number"]
    assert m.eval(S["get-type-space"](m, S.item)) == [S.Number]


@pytest.mark.parametrize("alias", [False, True])
def test_alias_and_literal_checks_agree_with_discharge_verification(m, alias):
    """Retained proofs and registry checks agree even after a user refusal."""
    prefix = "(: Count (Alias Number))\n" if alias else ""
    expected = "Count" if alias else "Number"
    m.run(f"{prefix}(: checked (-> {expected} {expected})) (= (checked $x) (+ $x 1)) (= (caller $x) (checked $x))")
    call = "!(with-pragma! ((verify-discharges True)) (caller 7))"
    assert m.run(call) == [[8]]
    m.fn.add_typing_rule(S.deny_numbers, S.ordinary, S.Number, S.Number, S.refuse(S.denied))
    [refused] = m.run(call)
    assert len(refused) == 1 and refused[0][0] == S.Error
    assert "TypingRuleRefusal deny-numbers denied" in str(refused[0])
    m.fn.remove_typing_rule(S.deny_numbers)
    assert m.run(call) == [[8]]


def test_aliases_expand_in_python_and_source_cast_targets(m):
    """Casts keep their existing failure and unchecked-target behavior."""
    from metta.convert import CastError

    m.run("(: Count (Alias Number)) (: Held (Alias Atom)) (: value Count)")
    assert m.cast(S.value, "Count") is S.value
    assert m.cast(7, "Count") == 7
    assert m.cast(S.unknown, "Held") is S.unknown
    with pytest.raises(CastError, match="Count"):
        m.cast("bad", "Count")
    assert flattened(m.run('!(type-cast 7 Count &self) !(type-cast "bad" Count &self)')) == [
        "7", '(Error "bad" BadType)'
    ]


def test_alias_casts_keep_the_strict_witness_and_obey_user_refusals(m):
    """Unknown actuals stay unknown; aliases do not bypass ordinary policy."""
    from metta.convert import CastError

    m.run("(: Count (Alias Number)) (: Any (Alias %Undefined%))")
    with pytest.raises(CastError, match="Count"):
        m.cast(S.mystery, "Count")
    assert m.cast(7, "Any") == 7
    assert m.run("!(type-cast mystery Count &self)") == [[S.Error(S.mystery, S.BadType)]]
    m.run("!(add-typing-rule! deny ordinary Count Count (refuse denied))")
    with pytest.raises(CastError, match="Count"):
        m.cast(7, "Count")
    m.run("!(remove-typing-rule! deny)")
    assert m.cast(7, "Count") == 7


@pytest.mark.parametrize("target", ["Atom", "%Undefined%", "_"])
def test_aliases_of_unchecked_cast_targets_stay_unchecked(m, target):
    """A wildcard target asks for no witness under either type spelling."""
    m.run(f"(: Unchecked (Alias {target})) "
          "!(add-typing-rule! deny ordinary $a $e (refuse denied))")
    try:
        assert m.cast(7, target) == m.cast(7, "Unchecked") == 7
        assert m.cast(S.mystery, target) is m.cast(S.mystery, "Unchecked") is S.mystery
    finally:
        m.run("!(remove-typing-rule! deny)")


def test_a_resolved_inherited_type_is_not_expanded_in_the_callers_scope(m):
    """An opaque terminal stays opaque even when the caller aliases its name."""
    from metta.convert import CastError

    root = MeTTa("&self").self
    suffix = uuid4().hex
    opaque, inherited, value = [S[f"{name}{suffix}"] for name in ("Opaque", "Inherited", "value")]
    shared = [typed(inherited, S.Alias(opaque)), typed(value, opaque)]
    for declaration in shared:
        root.add(declaration)
    try:
        m.add(typed(opaque, S.Alias(S.String)))
        m.add(typed(S.takes_inherited, arrow(inherited, inherited)))
        m.add(m.parse("(= (takes-inherited $x) $x)"))
        assert m.eval(S.takes_inherited(value)) == [value]
        assert m.eval(S.takes_inherited("s"))[0][0] == S.Error
        assert m.cast(value, inherited) is value
        assert m.cast("s", opaque) == "s"
        with pytest.raises(CastError):
            m.cast("s", inherited)
    finally:
        for declaration in reversed(shared):
            root.remove(declaration)


def test_aliases_expand_on_both_sides_of_subtype_edges(m):
    """Widening preserves the direct graph's ordered diamond multiplicity."""
    m.run("(: Species (Alias Dog)) (: Top (Alias Animal)) (: rex Species) "
          "(:< Species B) (:< Species C) (:< B Top) (:< C Top)")
    expected = [S.Dog, S.B, S.C, S.Animal, S.Animal]
    assert m.eval(S["get-type"](S.rex)) == expected
    assert m.eval(S["get-type-space"](m, S.rex)) == expected


def test_a_failed_first_file_load_restores_existing_callers(m, tmp_path):
    """A failing runnable withdraws its alias and repairs a surviving caller."""
    m.run("(: identity (-> Count Count)) (= (identity $x) $x) (= (caller $x) (identity $x))")
    before = m.eval(S.caller(7))
    path = tmp_path / "failed-alias.metta"
    path.write_text("(: Count (Alias Number))\n!(caller 7)\n!(+ $a $b)", encoding="utf-8")
    with pytest.raises(Exception, match=r"unsolved_arithmetic|more than one unknown"):
        m.load(path)
    assert not list(m.match(typed(S.Count, V.type)))
    assert m.eval(S.caller(7)) == before


def test_a_late_alias_repairs_a_compiled_typed_binding(m):
    """An annotation inside a body records even an unsuccessful alias lookup."""
    m.run("(= (bound $x) (let (__metta_typed_binding__ (: $v Count)) $x $v))")
    assert m.eval(S.bound(7)) == []
    alias = typed(S.Count, S.Alias(S.Number))
    m.add(alias)
    assert m.eval(S.bound(7)) == [7]
    m.remove(alias)
    assert m.eval(S.bound(7)) == []


def test_aliases_compose_with_annotated_arrows(m):
    """Arrow metadata remains visible after its alias fields are expanded."""
    m.run("(: Count (Alias Number)) (: Signature (Alias (-[det]-> Count Count))) "
          "(: annotated Signature) (= (annotated $x) $x)")
    assert m.eval(S.annotated(7)) == [7]
    assert m.eval(S.annotated("bad"))[0][0] == S.Error
    assert flattened(m.run("!(get-type annotated)")) == ["(-[det]-> Number Number)"]


@settings(max_examples=30)
@given(st.recursive(st.sampled_from(["Number", "String", "Bool"]),
                    lambda child: st.tuples(child, child), max_leaves=6))
def test_generated_nested_aliases_match_their_literal_type_tree(tree):
    """Acyclic alias trees agree with their fully substituted positional types."""
    declarations = []

    def lower(node):
        if isinstance(node, str):
            raw = node
            value = {"Number": "7", "String": '\"s\"', "Bool": "True"}[node]
            expanded = node
        else:
            left, right = [lower(child) for child in node]
            raw = f"({left[0]} {right[0]})"
            expanded = f"({left[1]} {right[1]})"
            value = f"({left[2]} {right[2]})"
        name = f"Alias{len(declarations)}"
        declarations.append(f"(: {name} (Alias {raw}))")
        return name, expanded, value

    alias, literal, value = lower(tree)
    with MeTTa().space() as aliased, MeTTa().space() as direct:
        suffix = f"(= (identity $x) $x) !(identity {value}) !(get-type identity)"
        actual = flattened(aliased.run(" ".join(declarations) +
                           f" (: identity (-> {alias} {alias})) " + suffix))
        expected = flattened(direct.run(f"(: identity (-> {literal} {literal})) " + suffix))
        assert actual == expected == [value, f"(-> {literal} {literal})"]


@pytest.mark.parametrize("declaration_kind", ["ordinary", "marker", "batch"])
def test_a_local_non_alias_declaration_retires_an_inherited_alias(m, declaration_kind):
    """Every declaration mutation door repairs an inherited lookup shadow."""
    root = MeTTa("&self").self
    name = S[f"InheritedNumber{uuid4().hex}"]
    shared = typed(name, S.Alias(S.Number))
    root.add(shared)
    try:
        m.add(typed(S.inherited_call, arrow(name, name)))
        m.add(m.parse("(= (inherited-call $x) $x)"))
        m.add(m.parse("(= (retained $x) (inherited-call $x))"))
        assert m.eval(S.retained(7)) == [7]
        kind = S.DontEvalType if declaration_kind == "marker" else S.Type
        local = typed(name, kind)
        if declaration_kind == "batch":
            m.add(local, S.row(1))
        else:
            m.add(local)
        assert m.eval(S.retained(7))[0][0] == S.Error
        m.remove(local)
        assert m.eval(S.retained(7)) == [7]
    finally:
        root.remove(shared)


def test_aliases_reach_admission(m):
    """Admission requires evidence for the expanded type."""
    m.run("(: Count (Alias Number))")
    assert flattened(m.run('!(has-declared-type 7 Count) !(has-declared-type "bad" Count)')) == ["True", "False"]


def test_a_variable_type_head_stays_opaque_when_alias_lookup_is_active(m):
    """A declaration pattern is not an Alias constructor by unification."""
    m.run("(: PairLike ($head Number)) (: value PairLike) (: Count (Alias Number))")
    assert m.eval(S["get-type"](S.value)) == [S.PairLike]


def test_nominal_subtyping_does_not_scan_unrelated_declarations(m):
    """An alias-free query's cost does not grow with the type inventory."""
    m.run("(: rex Dog) (:< Dog Animal)")
    query = S["get-type"](S.rex)
    assert m.eval(query) == [S.Dog, S.Animal]
    # Measure inside the evaluator: Python collection between calls can
    # release an unrelated abandoned world, which an outer stats block counts
    # as query work. The accounted door runs the same metta_py_eval_all/3.
    def measure():
        total = 0
        for _ in range(100):
            answers, spent = m.runtime.apply_must(
                "metta_py_eval_accounted", m.name, query.to_wire()
            )
            assert answers == [S.Dog.to_wire(), S.Animal.to_wire()]
            total += spent
        return total

    before = measure()
    m.add(*(typed(S[f"Unrelated{i}"], S.Payload) for i in range(1000)))
    after = measure()
    assert abs(after - before) <= 4
