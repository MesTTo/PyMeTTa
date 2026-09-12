"""Purpose: verify reference rows and the engine's shared property projections.

Guarantees: Python writes ordinary rows and preserves their live withdrawal;
cards and callable reflection retain defining homes [tested:
test_from_is_a_live_stored_row, test_a_card_reads_the_loaded_library_home;
commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
Guarantees: a source can reload after its previous scoped home is released
without reviving the old handle [tested:
test_a_library_reloads_after_its_first_scope_closes; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1].
"""

from collections import Counter

import pytest

from metta import Expression, Grounded, S, lib, library, parse
from metta._errors.errors import EngineError


def test_from_is_a_live_stored_row(metta):
    """The Python door has exactly the lifetime of the row it adds."""
    with metta._new_space() as home, metta._new_space() as target:
        home.run("(= (reference-value) first)\n(data stays-home)\n")
        target.from_(home)
        row = Expression((S["from"], home))
        assert row in target
        assert parse("(data stays-home)") not in target
        assert target.eval(parse("(reference-value)")) == [S.first]
        home.run("(= (reference-later $x) (+ $x 1))\n")
        assert target.eval(parse("(reference-later 41)")) == [42]
        target.remove(row)
        assert row not in target
        assert target.eval(parse("(reference-value)")) == [parse("(reference-value)")]


def test_get_property_matches_metta_and_explain(metta):
    """Both Python and MeTTa read the same complete property bag."""
    properties = metta.get_property("car-atom")
    assert isinstance(properties, tuple)
    assert Counter(properties) == Counter(metta.eval(parse("(get-property car-atom)")))
    (explanation,) = metta.eval(parse("(explain (car-atom (x y)))"))
    assert set(properties) <= set(explanation.children)
    assert parse("(visibility public)") in properties
    assert parse("(cost linear length)") in properties


def test_get_property_requires_a_head_name(metta):
    """A value cannot silently turn into a different head name."""
    with pytest.raises(TypeError, match="requires a head name"):
        metta.get_property(42)


def test_a_library_handle_and_partial_map_reach_the_canonical_home(metta):
    """A handle uses the engine's library resolver and one defining module."""
    with metta._new_space() as a, metta._new_space() as b:
        a.from_(lib.string, parse("(prefix text.)"))
        b.from_(lib.string, parse("(only (string-length))"))
        assert a.eval(parse('(text.string-length "hello")')) == [5]
        assert b.eval(parse('(string-length "hello")')) == [5]
        homes_a = {str(p.args[0]) for p in a.get_property("text.string-length") if p.head == S.origin}
        homes_b = {str(p.args[0]) for p in b.get_property("string-length") if p.head == S.origin}
        assert homes_a == homes_b and len(homes_a) == 1


def test_a_library_reloads_after_its_first_scope_closes(tmp_path, metta):
    """Source identity is stable; each released space has a distinct lifetime."""
    source = tmp_path / "scoped-source.metta"
    source.write_text("(= (scoped-library-value) 17)\n")
    with metta.scope():
        with metta._new_space() as first:
            first.from_(source)
            origins = [p.args[0] for p in first.get_property("scoped-library-value")
                       if p.head == S.origin]
            assert first.eval(S.scoped_library_value()) == [17]
    with metta._new_space() as second:
        second.from_(source)
        assert second.eval(S.scoped_library_value()) == [17]
        reloaded = [p.args[0] for p in second.get_property("scoped-library-value")
                    if p.head == S.origin]
        assert len(origins) == len(reloaded) == 1
        assert origins != reloaded


def test_a_grounded_default_map_keeps_the_symbol_result_boundary(metta):
    """A callable is accepted; its non-symbol answer names the refused head."""
    with metta._new_space() as home, metta._new_space() as target:
        home.run("(= (reference-value) mapped)\n")
        mapper = Grounded(lambda _head: 42)
        assert target.eval(Expression(S["pragma!"], S.from_map, mapper)) == [Expression()]
        with pytest.raises(EngineError, match="42 for reference-value; each answer must be a symbol"):
            target.from_(home)


def test_reference_except_and_compiled_exception_dispatch_coexist(metta):
    """The public map and Python's class test have independent names."""
    with metta._new_space() as home, metta._new_space() as target:
        home.run("(= (reference-kept) kept)\n(= (reference-skipped) skipped)\n")
        target.from_(home, S.except_((S.reference_skipped,)))
        assert target.eval(S.reference_kept()) == [S.kept]
        assert target.eval(S.reference_skipped()) == [S.reference_skipped()]

        @target.define
        def catch_zero(value):
            try:
                return 10 // value
            except ZeroDivisionError:
                return S.caught

        assert list(catch_zero(0)) == [S.caught]
        assert list(catch_zero(2)) == [5]
        assert target.eval(S.except_((S.reference_skipped,), S.reference_kept)) == [S.reference_kept]


def test_a_card_reads_the_loaded_library_home(tmp_path, metta):
    """Card visibility and source origins come from the home's live claims."""
    folder = tmp_path / "lib" / "lib_claims"
    folder.mkdir(parents=True)
    source = folder / "lib_claims.metta"
    source.write_text(
        '(internal claims-hidden)\n'
        '(@doc claims-visible (@desc "visible documentation"))\n'
        '(= (claims-visible $x) (+ $x 1))\n'
        '(= (claims-hidden) hidden)\n',
        encoding="utf-8",
    )
    with metta._new_space() as target:
        target.run("!(pragma! load lazy)")
        target.from_(source)
        properties = target.get_property("claims-visible")
        origins = [p for p in properties if p.head == S.origin]
        assert len(origins) == 1
        assert origins[0].args[1:] == (str(source), 3)
        home_name = str(origins[0].args[0])
        try:
            card = library.card("lib_claims", root=tmp_path)
            heads = {head.name: head for head in card.heads}
            assert heads["claims-hidden"].visibility == "internal"
            assert heads["claims-visible"].visibility == "public"
            assert heads["claims-visible"].origins == ((home_name, heads["claims-visible"].origin),)
            assert heads["claims-visible"].origin == (str(source), 3)
            assert target.fn["claims-visible"].origin == ((str(source), 3),)
            assert "visible documentation" in heads["claims-visible"].doc
            assert "internal" in str(card) and home_name in str(card)
            assert "<th>visibility</th>" in card._repr_html_()
        finally:
            metta._at(home_name).drop()
