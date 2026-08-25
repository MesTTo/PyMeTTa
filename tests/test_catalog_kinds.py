"""Purpose: a third-party declaration kind changes routing through published
seams alone. Catalog rows declare the kind's vocabulary, shape and routing;
a route-cap advisor loaded as an ordinary Prolog extension reads them
through the published shape route; and the engine's pushdown of a caller's
bound follows the declared freshness, with no kernel edit anywhere.
Assumes:
  - an Exact handles route pushes the caller's bound to the provider, so
    the bound the provider records is the routing observable
    [tested: test_foreign.py's bound-pushdown suite]
Guarantees:
  - generated vocabulary aliases preserve declared CamelCase names
    [tested: test_generated_alias_preserves_declared_camel_case;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - visibility is generated as the exact PUBLIC/INTERNAL catalog vocabulary
    [tested: test_visibility_is_a_generated_catalog_vocabulary;
    commit=918e4eaae8b99077f8b8b293b4ec5c3e0e2b2cf6]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import sys

import pytest

from metta import MeTTa, S, V
from metta.errors import EngineError
from metta.foreign import SpaceProvider
from metta.vocabularies import Fidelity, Semiring, Visibility


class _Recording(SpaceProvider):
    """Answers (edge ...) rows and records the bound each match arrived
    with: None is the engine keeping the bound for re-unification, an
    integer is the bound pushed down, which only an exact route licenses.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    def __init__(self):
        self.asked = []
        self._rows = [S.edge(S.a, S.b), S.edge(S.c, S.d), S.edge(S.e, S.f)]

    def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        self.asked.append(limit)
        rows = self._rows if limit is None else self._rows[:limit]
        yield from rows


EXTENSION = """\
:- metta_extension(freshness, [requires(1-1)]).
:- metta_export("(export freshness-of 2)").

%The routed freshness level of one query shape in one context.
'freshness-of'(Ctx, Query, Level) :-
    petta_shape_route(freshness, Ctx, Query, _, [Level]).

%The advisors: a cached context's routes lose the pushdown licence, a
%stale one's are refused outright. Both read the third-party kind's own
%catalog rows through the published shape route.
:- multifile seam:route_cap/4.
seam:route_cap(Space, Pattern, inexact, freshness(cached)) :-
    petta_shape_route(freshness, Space, Pattern, _, [cached]).
seam:route_cap(Space, Pattern, refuse, freshness(stale)) :-
    petta_shape_route(freshness, Space, Pattern, _, [stale]).
"""


def test_a_third_party_declaration_kind_changes_routing_through_published_seams(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    tmp_path,
):
    m = MeTTa().self
    provider = _Recording()
    m._register_space(provider, "&fr-rows")
    m._at("&fr-rows").handles("(edge $a $b)", "Exact")

    rows = m._at("&fr-rows").match(S.edge(V.x, V.y), limit=2)
    assert len(rows) == 2
    assert provider.asked[-1] == 2, "the declared Exact route pushes the bound"

    extension = tmp_path / "freshness.pl"
    extension.write_text(EXTENSION)
    m.register_prolog(path=extension)

    m.run("!(add-atom &petta (vocabulary freshness-level live cached stale))")
    m.run("!(add-atom &petta (kind freshness symbol pattern (one-of freshness-level)))")
    m.run("!(add-atom &petta (routed-by-shape freshness))")
    m.run("!(add-atom &petta (freshness &fr-rows (edge $a $b) cached))")

    assert m.run("!(freshness-of &fr-rows (edge x y))") == [[S.cached]]

    rows = m._at("&fr-rows").match(S.edge(V.x, V.y), limit=2)
    assert len(rows) == 2
    assert provider.asked[-1] is None, (
        "a cached context is demoted: the bound stays with the engine and "
        "the candidates are re-unified"
    )

    m.run("!(remove-atom &petta (freshness &fr-rows (edge $a $b) cached))")
    m.run("!(add-atom &petta (freshness &fr-rows (edge $a $b) stale))")

    with pytest.raises(EngineError, match="refuses"):
        list(m._at("&fr-rows").match(S.edge(V.x, V.y), limit=2))


def test_a_malformed_third_party_declaration_is_refused_at_the_add(tmp_path):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    m = MeTTa().self
    m.run("!(add-atom &petta (vocabulary mood-level calm tense))")
    m.run("!(add-atom &petta (kind mood symbol (one-of mood-level)))")
    with pytest.raises(EngineError, match="does not fit its declared kind"):
        m.run("!(add-atom &petta (mood &somewhere excited))")


def test_the_vocabulary_module_is_generated(repo_root):
    """The catalog presets and the binding's Literal types are one
    authority: the checked-in module has to equal what the engine's own
    (vocabulary ...) rows produce.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    sys.path.insert(0, str(repo_root / "bindings" / "python" / "tools"))
    try:
        import vocabgen
    finally:
        sys.path.pop(0)
    assert vocabgen.main([]) == 0


def test_generated_alias_preserves_declared_camel_case(repo_root):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    sys.path.insert(0, str(repo_root / "bindings" / "python" / "tools"))
    try:
        import vocabgen
    finally:
        sys.path.pop(0)
    assert vocabgen.alias_name("answer-policy") == "AnswerPolicy"
    assert vocabgen.alias_name("ClauseFailedEnum") == "ClauseFailedEnum"


def test_visibility_is_a_generated_catalog_vocabulary():
    """The discriminator's Python spelling preserves its two wire words."""
    assert list(Visibility) == ["PUBLIC", "INTERNAL"]


def test_the_binding_refuses_by_the_generated_vocabulary():
    """The runtime checks read the generated vocabulary classes, so the
    refusal names exactly the values the engine's checker enforces.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m = MeTTa().self
    with pytest.raises(ValueError, match=", ".join(Fidelity)):
        m._at("&vg-rows").handles("(edge $a $b)", "Exactly")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=", ".join(Semiring)):
        m.annotations("&vg-rows", "heap")  # type: ignore[arg-type]


def test_every_vocabulary_member_crosses_as_its_symbol():
    """Each generated class is a StrEnum whose members ARE their wire words.

    The whole point of rendering enums instead of Literal aliases: a member
    equals its bare word, joins as it, hashes as it, and encodes as the
    symbol it always was, so nothing downstream changes while the annotation
    surface stops being stringly.
    """
    from enum import StrEnum

    from metta import vocabularies
    from metta.atoms import Symbol

    for name in vocabularies.__all__:
        cls = getattr(vocabularies, name)
        assert issubclass(cls, StrEnum), name
        for member in cls:
            assert member == member.value, (name, member)
            assert member.__metta__() == Symbol(member.value), (name, member)
            assert member.value in cls, (name, member)


def test_a_keyword_value_takes_a_trailing_underscore(repo_root):
    """route-key's `global` cannot be a bare member name, so rung 4's own
    keyword convention applies: trailing underscore on the member, bare word
    as the value.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    from metta.vocabularies import RouteKey

    assert RouteKey.global_.value == "global"
    assert "global" in RouteKey
    sys.path.insert(0, str(repo_root / "bindings" / "python" / "tools"))
    try:
        import vocabgen
    finally:
        sys.path.pop(0)
    assert vocabgen.member_name("global") == "global_"
    assert vocabgen.member_name("best-first") == "best_first"


def test_the_ledger_rename_names_on_error(repo_root):
    """on-error-mode exports as OnError, the design record's spelling beside
    Space.on_error; every other class keeps the mechanical CamelCase.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    from metta.vocabularies import AnswerPolicy, OnError

    assert OnError.__name__ == "OnError"
    assert list(OnError) == ["keep", "empty", "abort"]
    assert AnswerPolicy.best_first.value == "best-first"
    sys.path.insert(0, str(repo_root / "bindings" / "python" / "tools"))
    try:
        import vocabgen
    finally:
        sys.path.pop(0)
    assert vocabgen.alias_name("on-error-mode") == "OnError"
    assert vocabgen.alias_name("cache-mode") == "CacheMode"


def test_the_image_declaration_is_catalog_validated():
    """(image space type setting) now has a catalog kind row: the binding door
    and a direct &petta write refuse the same junk word, and a member crosses
    as the symbol the vocabulary declares.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    from metta.errors import EngineError
    from metta.vocabularies import ImageMode

    m = MeTTa().self
    by_member = m.image("VgBlob", ImageMode.transparent)
    by_word = m.image("VgBlob", "transparent")
    assert str(by_member) == str(by_word) == "(image &self VgBlob transparent)"
    with pytest.raises(ValueError, match="opaque, transparent, auto"):
        m.image("VgBlob", "sideways")  # type: ignore[arg-type]
    with pytest.raises(EngineError, match=r"one-of image-mode"):
        m.run("!(add-atom &petta (image x y sideways))")
