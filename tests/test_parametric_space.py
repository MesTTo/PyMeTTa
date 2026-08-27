"""Purpose: pin expression-named native spaces at the public MeTTa surface.

Guarantees:
  - one ground expression identifies one isolated storage and execution
    context, and context-space exposes its parameters to local equations
    [tested: test_two_instances_of_a_parametric_space_answer_independently;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - malformed identifiers fail before any native or execution cache entry is
    published [tested: test_invalid_parametric_names_publish_no_cache_entry;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - derivation leaves recover the expression identity from its canonical
    storage module [tested: test_a_parametric_fact_leaf_names_its_space;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a callable family head cannot evaluate a registered identity at a space
    door [tested: test_a_callable_family_head_does_not_replace_the_identity;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import pytest

from metta import S, V, space
from metta.errors import EngineError


def _answers(metta, source):
    return [str(atom) for group in metta.run(source) for atom in group]


def _release(metta, space_term):
    metta.runtime.must(f"metta_release_space({space_term})")


def test_python_space_factory_accepts_atom_valued_names(metta):
    """Symbols and ground expressions name source-visible stores."""
    users = space(S.users)
    cache = space(S.cache(S.base, 100))
    try:
        users += S.member(S.Ada)
        cache += S.entry(S.key, S.value)

        assert users.match(S.member(V.who)).one().who == S.Ada
        assert cache.match(S.entry(V.key, V.value)).one().value == S.value
        assert metta.run("!(match &users (member $who) $who)") == [[S.Ada]]
        assert metta.run(
            "!(match (cache base 100) (entry $key $value) $value)"
        ) == [[S.value]]
        assert space(S.cache(S.base, 100)).digest() == cache.digest()
    finally:
        users.drop()
        cache.drop()

    with pytest.raises(ValueError, match=r"free variable.*open"):
        space(S.cache(V.base, 100))


def test_two_instances_of_a_parametric_space_answer_independently(metta):
    """Two instances of one parametric family hold independent atoms and answers."""
    left = "(cache &p12-param-left 100)"
    right = "(cache &p12-param-right 10)"
    definition = (
        "(= (cache-config) "
        "(let (cache $base $limit) (context-space) "
        "(config $base $limit)))"
    )

    try:
        assert _answers(metta, f"!(new-space {left})") == [left]
        assert _answers(metta, f"!(new-space {right})") == [right]

        for space in (left, right):
            assert _answers(metta, f"!(add-atom {space} {definition})") == ["()"]

        metta.run(f"!(add-atom {left} (entry left))")
        metta.run(f"!(add-atom {left} (edge a b))")
        metta.run(f"!(add-atom {left} (edge b c))")
        metta.run(f"!(add-atom {left} (: local-token LeftToken))")
        metta.run(f"!(add-atom {right} (entry right))")
        metta.run(f"!(add-atom {right} (edge x y))")
        metta.run(f"!(add-atom {right} (: local-token RightToken))")

        assert _answers(metta, f"!(evalc (cache-config) {left})") == [
            "(config &p12-param-left 100)"
        ]
        assert _answers(metta, f"!(evalc (cache-config) {right})") == [
            "(config &p12-param-right 10)"
        ]
        assert _answers(metta, f"!(evalc (context-space) {left})") == [left]
        assert _answers(metta, f"!(get-type {left})") == ["SpaceType"]
        assert _answers(metta, f"!(evalc (get-type local-token) {left})") == [
            "LeftToken"
        ]
        assert _answers(metta, f"!(evalc (get-type local-token) {right})") == [
            "RightToken"
        ]

        assert _answers(
            metta,
            f"!(collapse (match {left} (, (edge $x $y) (edge $y $z)) ($x $z)))",
        ) == ["((a c))"]
        assert _answers(
            metta, f"!(collapse (match {right} (entry $x) $x))"
        ) == ["(right)"]
        assert _answers(
            metta, f"!(collapse (match {left} (entry $x) $x))"
        ) == ["(left)"]

        assert _answers(metta, f"!(remove-atom {left} (entry left))") == ["()"]
        assert _answers(
            metta, f"!(collapse (match {left} (entry $x) $x))"
        ) == ["()"]
        assert _answers(
            metta, f"!(collapse (match {right} (entry $x) $x))"
        ) == ["(right)"]
    finally:
        _release(metta, "[cache, '&p12-param-right', 10]")
        _release(metta, "[cache, '&p12-param-left', 100]")


def test_invalid_parametric_names_publish_no_cache_entry(metta):
    """A malformed parametric identifier publishes no native or execution cache entry."""
    before = metta.runtime.must(
        "aggregate_all(count, space_parametric(_), Parametric), "
        "aggregate_all(count, native_storage_module_cache(_, _), Storage), "
        "aggregate_all(count, metta_exec_module_known(_, _), Exec)"
    )

    for source in [
        "!(new-space ())",
        "!(new-space ((cache) &p12-bad 1))",
        "!(new-space (cache $unbound 1))",
    ]:
        with pytest.raises(EngineError):
            metta.run(source)

    after = metta.runtime.must(
        "aggregate_all(count, space_parametric(_), Parametric), "
        "aggregate_all(count, native_storage_module_cache(_, _), Storage), "
        "aggregate_all(count, metta_exec_module_known(_, _), Exec)"
    )
    assert after == before


def test_a_parametric_fact_leaf_names_its_space(metta):
    """A derivation leaf recovers the ground expression identity of its space."""
    name = "[cache, '&p12-param-leaf', 1]"
    try:
        metta.run("!(new-space (cache &p12-param-leaf 1))")
        metta.run("!(add-atom (cache &p12-param-leaf 1) (entry left))")
        row = metta.runtime.must(
            f"_Name={name}, native_storage_module(_Name, _Module), "
            "_Goal = '$metta_parametric_atom'(entry, left), "
            "metta_py_leaf(_Module, _Goal, _Tree), term_string(_Tree, Text)"
        )
        assert row["Text"] == "[fact([cache,'&p12-param-leaf',1],[entry,left])]"
    finally:
        _release(metta, name)


def test_a_callable_family_head_does_not_replace_the_identity(metta):
    """A callable family head at a space door names the instance, never evaluates."""
    surface = "(cache &p12-param-callable 2)"
    name = "[cache, '&p12-param-callable', 2]"
    try:
        metta.run("(= (cache $base $limit) &wrong-space)")
        assert _answers(metta, f"!(new-space {surface})") == [surface]
        assert _answers(metta, f"!(is-space {surface})") == ["True"]
        assert _answers(metta, f"!(add-atom {surface} (entry local))") == ["()"]
        assert _answers(metta, f"!(space-contains {surface} (entry local))") == [
            "True"
        ]
        assert _answers(metta, f"!(space-atom-count {surface})") == ["1"]
        assert _answers(metta, f"!(collapse (get-atoms {surface}))") == [
            "((entry local))"
        ]
    finally:
        _release(metta, name)
