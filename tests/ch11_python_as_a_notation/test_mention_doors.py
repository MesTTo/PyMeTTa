"""Purpose: pin the compiled-body S, V, and static fn mention doors.
Guarantees:
  - builders retain their outside-body meanings when the compiler reads them
    [tested: test_compiled_bodies_reach_all_four_mention_families;
    commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - exact catalog names win before the underscore-to-hyphen fallback and
    unknown or shadowed host calls refuse without execution [tested:
    test_bare_callees_ask_exact_then_mapped,
    test_rejected_attributes_never_execute_host_objects; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - the runtime fn namespace and its typed stub come from one deterministic
    catalog snapshot [tested: test_the_fn_namespace_is_generated;
    commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - INTERNAL catalog names remain exact S/fn mentions but are absent from the
    generated typed and reference surfaces [tested:
    test_internal_catalog_names_stay_exact_but_leave_public_outputs;
    commit=8779452fed89853c3f77c3469f7a6ec7b12e9efa]
  - the S, static fn, and bound fn attribute doors share Python's operator
    word vocabulary while bracket access remains exact and composite ``neg``
    keeps its canonical image [tested:
    test_operator_words_precede_the_mechanical_name_map,
    test_compiled_operator_word_calls_preserve_composite_images;
    commit=8ec44dec3cafba5981e7cf712749cca0e1bdcc45]
  - mapped generator calls remain nondeterministic in definition effects
    [tested: test_mapped_nondeterministic_calls_keep_their_call_role;
    commit=8ec44dec3cafba5981e7cf712749cca0e1bdcc45]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

import metta as metta_package
from metta import Expression, S, V, Variable, fn
from metta.errors import CompileError
from metta.vocabularies import EffectClass


@pytest.fixture()
def m(metta):
    """Give each compiler scenario an isolated equation namespace."""
    return metta._new_space()


if TYPE_CHECKING:
    # These declarations let static tools see the bare target-language names.
    # They deliberately do not create runtime host bindings.
    def sc_edge_to(value: Any) -> Any:
        """Declare a statically visible target-language callee."""
        ...

    def two_spellings(value: Any) -> Any:
        """Declare the target used to test exact-name precedence."""
        ...

    def match(pattern: Any, template: Any) -> Any:
        """Declare the compiler's target-language match form."""
        ...

    def pragma() -> Any:
        """Declare the bare spelling of the catalog's banged form."""
        ...

    def mapped_values() -> Any:
        """Declare the Python image of a hyphenated generator."""
        ...


def _lowercase_mention():
    return S.done


def _minted_variable():
    return V.b


def _capitalized_constructor(value):
    return S.Parent(value)


def _hyphenated_callee(values):
    return fn.car_atom(values)


def _exact_callee(value):
    return fn["=="](value, value)


def _exact_mentions():
    return S["my_var"], V["lambda"]


def _banged_mentions():
    return fn.pragma, pragma


def _mapped_values():
    yield 1
    yield 2


def _delegate_mapped_values():
    yield from mapped_values()


def _iterate_mapped_values():
    for value in mapped_values():
        yield value + 0


def _unknown_fn_member(value):
    return fn.not_a_catalog_member(value)


def _computed_fn_member(name, value):
    return fn[name](value)


def _mapped_bare_callee(value):
    return sc_edge_to(value)


def _exact_bare_callee(value):
    return two_spellings(value)


def _gallery_ancestor(a, d):
    yield match((S.Parent, a, d), True)  # noqa: FBT003  -- target-language template
    yield _gallery_ancestor(match((S.Parent, a, V.m), V.m), d)


class _HostTrap:
    reads = 0

    def __getattribute__(self, name: str) -> Any:
        if name not in {"reads", "__class__"}:
            type(self).reads += 1
        return object.__getattribute__(self, name)


_HOST_TRAP = _HostTrap()


def _host_attribute_call(value):
    return _HOST_TRAP.call(value)


def _shadowed_builder(fn):
    return fn.car_atom


def test_compiled_bodies_reach_all_four_mention_families(m):
    """Lowercase data, holes, hyphenated callees, and constructors all stage."""
    lowercase = m.define(_lowercase_mention)
    minted = m.define(_minted_variable)
    constructor = m.define(_capitalized_constructor)
    callee = m.define(_hyphenated_callee)

    assert lowercase() == [S.done]
    assert minted.body == Variable("b")
    assert constructor(7) == [S.Parent(7)]
    assert callee(Expression(1, 2, 3)) == [1]


def test_attribute_factories_apply_the_total_map_and_brackets_stay_exact():
    """Factory attributes transliterate; brackets preserve target spelling."""
    assert S.take_atom == S["take-atom"]
    assert V.some_hole == V["some-hole"]
    assert S["take_atom"] != S.take_atom
    assert V["some_hole"] != V.some_hole


def test_operator_words_precede_the_mechanical_name_map(m):
    """All three Symbol mention doors share one fixed operator vocabulary."""
    words = {
        "eq": "==",
        "ne": "!=",
        "lt": "<",
        "le": "<=",
        "gt": ">",
        "ge": ">=",
        "add": "+",
        "sub": "-",
        "mul": "*",
        "mod": "%",
        "pow": "pow-math",
        "truediv": "/",
    }
    for word, head in words.items():
        assert getattr(S, word) == S[head]
        assert getattr(fn, word) == S[head]
        assert getattr(m.fn, word).__name__ == head

    assert S.eq(V.x, 2) == S["=="](V.x, 2)
    assert S["eq"] != S.eq
    assert m.fn.add(1, 2).one() == 3
    assert S.neg(V.x) == fn.neg(V.x) == S["-"](0, V.x) == -V.x
    assert m.fn.neg(4).one() == -4
    assert "neg" in dir(S)
    assert "neg" in dir(fn)
    assert "neg" in dir(m.fn)
    assert S["neg"] != S.neg
    with pytest.raises(AttributeError, match=r"floordiv.*floor-math.* /"):
        _ = m.fn.floordiv


def test_exact_name_mentions_compile_without_transformation(m):
    """The bottom rung preserves underscores, keywords, and operator names."""
    exact = m.define(_exact_mentions)
    equality = m.define(_exact_callee)

    assert exact.body == Expression(S["my_var"], V["lambda"])
    assert equality(9) == [True]


def test_banged_catalog_names_take_the_mechanical_fallback(m):
    """A bangless Python attribute reaches the sole banged catalog name."""
    mentioned = m.define(_banged_mentions)

    assert fn.pragma == S["pragma!"]
    assert mentioned.body == Expression(S["pragma!"], S["pragma!"])


def test_mapped_nondeterministic_calls_keep_their_call_role(m):
    """Name transliteration does not turn generator answers into tuple data."""
    m.define(_mapped_values, name="mapped-values")
    delegated = m.define(_delegate_mapped_values)
    iterated = m.define(_iterate_mapped_values)

    assert delegated.facts.effect is EffectClass.nondeterministicReadOnly
    assert iterated.facts.effect is EffectClass.nondeterministicReadOnly
    assert not delegated.facts.pure
    assert not iterated.facts.pure
    assert delegated() == [1, 2]
    assert iterated() == [1, 2]


def test_bare_callees_ask_exact_then_mapped(m):
    """An exact catalog hit wins; a unique mapped hit is the fallback."""
    m.run("(= (sc-edge-to $x) (Edge $x))")
    mapped = m.define(_mapped_bare_callee)
    assert mapped.body == S["sc-edge-to"](V.value)
    assert mapped(S.a) == [S.Edge(S.a)]

    m.run("(= (two_spellings $x) Exact)")
    m.run("(= (two-spellings $x) Mapped)")
    exact = m.define(_exact_bare_callee)
    assert exact.body == S["two_spellings"](V.value)
    assert exact(S.a) == [S.Exact]


def test_gallery_program_one_compiles_and_runs(m):
    """The guide's recursive relation uses S and V inside both match positions."""
    m.add(
        S.Parent(S.Tom, S.Bob),
        S.Parent(S.Pam, S.Bob),
        S.Parent(S.Bob, S.Ann),
        S.Parent(S.Bob, S.Pat),
        S.Parent(S.Pat, S.Jim),
    )
    ancestor = m.define(_gallery_ancestor, name="gallery-ancestor")

    assert ancestor(S.Tom, S.Jim) == [True]
    assert ancestor(S.Pam, S.Jim) == [True]
    assert "$m" in str(ancestor.body)


def test_rejected_attributes_never_execute_host_objects(m):
    """Static AST classification rejects a host attribute before touching it."""
    _HostTrap.reads = 0
    with pytest.raises(CompileError, match=r"attribute|plain name"):
        m.define(_host_attribute_call)
    assert _HostTrap.reads == 0

    with pytest.raises(CompileError, match=r"shadows|plain name|attribute"):
        m.define(_shadowed_builder)

    with pytest.raises(CompileError, match="no target function"):
        m.define(_unknown_fn_member)
    with pytest.raises(CompileError, match="literal exact target name"):
        m.define(_computed_fn_member)


def test_the_generated_namespace_names_the_live_one_when_it_misses():
    """Two `fn` doors, and the refusal has to say which is which.

    The module-level `fn` is GENERATED, which is what gives it autocomplete and
    a type stub; `space.fn` is LIVE. So a name registered at run time is absent
    from one and present on the other, and saying only "not in the generated
    catalog" sends a caller looking for a typo they did not make.
    """
    import metta as metta_module

    space = metta_module.space("&fnremedy")

    @space.pure(name="fn-remedy-probe")
    def probe(value):
        return value

    try:
        with pytest.raises(AttributeError) as refused:
            _ = metta_module.fn.fn_remedy_probe
        message = str(refused.value)
        assert "space.fn.<name>" in message, message
        assert "S['<name>'](...)" in message, message
        # And the remedy is real, not advice.
        assert space.fn.fn_remedy_probe is not None
    finally:
        space.unregister_op("fn-remedy-probe")

    # The LIVE door names its own remedies, which are different ones: a miss
    # here means the name is defined nowhere this space can see, so the answer
    # is to define or register it rather than to look on another namespace.
    with pytest.raises(AttributeError) as absent:
        _ = space.fn.defined_nowhere
    live = str(absent.value)
    assert "@space.define" in live and "@space.op" in live, live
    assert "S['defined_nowhere'](...)" in live, live


def test_the_fn_namespace_is_generated(repo_root: Path):
    """One generator owns the runtime manifest and explicit typed members."""
    tools = repo_root / "extensions" / "python" / "tools"
    sys.path.insert(0, str(tools))
    try:
        fngen = importlib.import_module("fngen")
    finally:
        sys.path.pop(0)

    assert fngen.main([]) == 0
    assert fn.car_atom == S["car-atom"]
    assert fn["=="] == S["=="]
    missing = "not_a_catalog_member"
    with pytest.raises(AttributeError, match="no target function"):
        getattr(fn, missing)

    stub = (repo_root / "extensions" / "python" / "metta" / "_fn.pyi").read_text(encoding="utf-8")
    assert "car_atom: Symbol" in stub
    assert "def __getattr__" not in stub

    manifest = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    assert "*.pyi" in manifest["tool"]["setuptools"]["package-data"]["metta"]

    environment = os.environ | {"PYTHONPATH": str(repo_root / "extensions" / "python")}
    imported = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from metta import fn; "
            "assert 'metta._engine' not in sys.modules; print(fn.car_atom)",
        ],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert imported.stdout.strip() == "car-atom"


def test_internal_catalog_names_stay_exact_but_leave_public_outputs(repo_root: Path):
    """Visibility filters promises, not the target-language mention ladder."""
    internal = {
        "get-doc-atom",
        "get-doc-function",
        "get-doc-params",
        "get-doc-single-atom",
        "interpret",
        "match-type-or",
    }
    rows = metta_package.catalog.match(S.visibility(V.name, V.level))
    visibility = {str(row.name): str(row.level) for row in rows}
    assert all(visibility.get(name) == "INTERNAL" for name in internal)
    for name in internal:
        assert fn[name] == S[name]

    stub = (repo_root / "extensions" / "python" / "metta" / "_fn.pyi").read_text(
        encoding="utf-8"
    )
    aliases = {name.replace("-", "_").removesuffix("!") for name in internal}
    for alias in aliases:
        assert f"    {alias}:" not in stub

    reference = (
        repo_root / "website" / "reference" / "stdlib-phrasebook.md"
    ).read_text(encoding="utf-8")
    for name in internal:
        assert f"`{name}`" not in reference


def test_generated_aliases_keep_exact_only_spellings_on_the_bracket_door():
    """Genuine underscores and non-Python-style names remain exact-only."""
    from metta._name_mapping import generated_aliases

    assert generated_aliases(["same-name", "same_name", "mixedCase", "pragma!"]) == {
        "neg": "neg",
        "pragma": "pragma!",
        "same_name": "same-name",
    }


def test_compiled_operator_word_calls_preserve_composite_images():
    """S.eq and fn.eq inside a compiled body store the operator's own head.

    The live factory consulted the word table and the body translator did
    not, so the same spelling meant two different atoms by door: `S.eq(a, b)`
    at the factory built `(== a b)` while a compiled body stored `(eq a b)`,
    the guide's rule-D critical pair. The translator now consults the same
    table after the V branch (V.eq stays the variable `$eq`), the bracket
    door stays exact by construction. The settled composite neg word expands
    to its canonical image at both call doors.
    """
    from metta import MeTTa, S, V, fn

    m = MeTTa().space()

    @m.define
    def word_eq(a, b):
        return S.eq(a, b)

    @m.define
    def word_add(a, b):
        return S.add(a, b)

    @m.define
    def word_fn_eq(a, b):
        return fn.eq(a, b)

    @m.define
    def word_exact(a, b):
        return S["eq"](a, b)

    stored = {
        head: str(m.match(S["="](S[head](V.a, V.b), V.body)).one().body[0])
        for head in ("word-eq", "word-add", "word-fn-eq", "word-exact")
    }
    assert stored == {
        "word-eq": "==",
        "word-add": "+",
        "word-fn-eq": "==",
        "word-exact": "eq",
    }

    @m.define
    def word_neg(a):
        return S.neg(a)

    @m.define
    def word_fn_neg(a):
        return fn.neg(a)

    assert word_neg.body == S["-"](0, V.a)
    assert word_fn_neg.body == S["-"](0, V.a)
    assert word_neg(7) == [-7]
    assert word_fn_neg(7) == [-7]


def test_a_defined_and_a_bound_function_mention_as_their_head():
    """Mentioning a function is holding its symbol.

    Guide 3.1: a Defined or a bound engine function in term position
    encodes as its own head rather than boxing the callable; G() stays
    the explicit box.
    """
    from metta import G, MeTTa, S
    from metta.atoms import Grounded

    m = MeTTa().self

    @m.define
    def mentioned_head(x):
        return x

    term = S.memoize(mentioned_head, 2)
    assert str(term) == "(memoize mentioned-head 2)"
    bound = m.fn["mentioned-head"]
    assert str(S.tabled(bound)) == "(tabled mentioned-head)"
    boxed = G(mentioned_head)
    assert isinstance(boxed, Grounded)
    assert boxed.value is mentioned_head


def test_catalogue_membership_answers_the_builtins_union(metta):
    """The point probe and the catalogue list answer the same union.

    The bound namespace resolves attributes by the probe (one indexed
    fun/1 lookup plus the special-form heads) instead of rebuilding the
    list after every definition, which measured 1,347 inferences on the
    next access; the union must stay identical or names would vanish
    from attribute resolution while dir() still showed them.
    """
    names = metta.builtins()
    assert names
    missing = [n for n in names if not metta._is_catalogued(n)]
    assert missing == []
    assert not metta._is_catalogued("no-such-catalogue-name-xyz")
    # A special form resolves at the attribute door exactly as before.
    assert metta.fn["collapse"] is not None
    import pytest

    with pytest.raises(AttributeError, match="no function"):
        metta.fn.no_such_catalogue_name_xyz  # noqa: B018  -- the refusal at access IS the scenario
