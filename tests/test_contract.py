"""Purpose: the contract surface in &petta: a registration's declarations are
readable back as atoms and live and die with the registration, and
(handles ...) entries route foreign matching, push or withhold the take
bound, refuse loudly, and stay coherent, down to a SQL backend example.
Guarantees:
  - operation facts are typed OpDecl values and callable documentation shares
    the registration transaction, replacement, ownership, and unregister
    lifecycle [tested:
    test_every_register_op_writes_its_declaration_and_get_doc_answers;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - every Python operation owns one canonical five-rank effect fact throughout
    registration, replacement, reflection, and unregister
    [tested: test_structural_registration_reflects_an_effect_atom;
    test_reregistration_replaces_the_effect_rank;
    test_a_registered_structural_effect_reaches_the_purity_walk;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - lint evidence and named intent facts inhabit their declared reflection
    types [tested: test_lint_evidence_and_intent_are_typed_reflection_facts;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import uuid

import pytest

from metta import parse
from metta.atoms import Expression, Variable
from metta.errors import EngineError
from metta.foreign import SpaceProvider
from metta.vocabularies import EffectClass


def _effect_atom(name, effect=EffectClass.pureStructural):
    return parse(f"(effect {name} {effect.value})")


def test_structural_registration_reflects_an_effect_atom(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def add1(x: int) -> int:
        return x + 1

    metta.op(add1, name="ct-pure", effect=EffectClass.pureStructural)
    petta_space = metta._at("&petta")
    assert _effect_atom("ct-pure") in petta_space
    # The op fact and the effect fact are one surface.
    assert parse("(op ct-pure 1 det)") in petta_space


def test_unclassified_registration_is_refused_with_the_five_rank_remedy(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def add1(x: int) -> int:
        return x + 1

    with pytest.raises(TypeError) as error:
        metta.op(add1, name="ct-unclassified", effect=None)
    for effect in EffectClass:
        assert f"EffectClass.{effect.value}" in str(error.value)
    reflection = metta._at("&petta")
    assert parse("(op ct-unclassified 1 det)") not in reflection
    assert reflection.match(parse("(effect ct-unclassified $effect)")) == []


def test_unregister_removes_the_effect_atom_with_the_op_facts(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    values = {1: 2}

    def lookup(x: int) -> int:
        return values[x]

    metta.op(lookup, name="ct-gone", effect=EffectClass.readOnlyLookup)
    petta_space = metta._at("&petta")
    assert _effect_atom("ct-gone", EffectClass.readOnlyLookup) in petta_space
    metta.unregister_op("ct-gone")
    assert _effect_atom("ct-gone", EffectClass.readOnlyLookup) not in petta_space
    assert parse("(op ct-gone 1 det)") not in petta_space


def test_reregistration_replaces_the_effect_rank(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    writes = []

    def add1(x: int) -> int:
        return x + 1

    def remember(x: int) -> int:
        writes.append(x)
        return x + 1

    metta.op(add1, name="ct-flip", effect=EffectClass.pureStructural)
    petta_space = metta._at("&petta")
    assert _effect_atom("ct-flip") in petta_space
    # Replacement owns exactly one rank. A claim from a previous registration
    # must not survive after the new operation takes ownership of its facts.
    metta.op(remember, name="ct-flip", effect=EffectClass.writesState)
    assert _effect_atom("ct-flip") not in petta_space
    assert _effect_atom("ct-flip", EffectClass.writesState) in petta_space
    metta.unregister_op("ct-flip")


def test_the_effect_atom_is_matchable_from_metta(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    values = {1: 2}

    def lookup(x: int) -> int:
        return values[x]

    metta.op(lookup, name="ct-query", effect=EffectClass.readOnlyLookup)
    rows = metta._at("&petta").match(parse("(effect ct-query $e)"))
    assert [str(row.e) for row in rows] == ["readOnlyLookup"]


def test_the_ontology_is_loaded_at_boot(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    petta_space = metta._at("&petta")
    assert parse("(: Declaration Type)") in petta_space
    assert parse("(:< Exact Partial)") in petta_space
    assert parse("(:< Partial Sound)") in petta_space
    for effect in EffectClass:
        assert parse(f"(: {effect.value} Effect)") in petta_space
    # Refuse is a Fidelity but deliberately outside the chain.
    assert parse("(: Refuse Fidelity)") in petta_space
    assert parse("(:< Refuse Sound)") not in petta_space


def test_lint_evidence_and_intent_are_typed_reflection_facts(metta):
    """The two lint records are declarations programs can query by type."""
    reflection = metta._at("&petta")
    evidence = '(lint-evidence &self kind "subject" "path.py" 1 2 "authority")'
    intent = '(lint-intent &self kind "path.py" 1 2 3 4 "authority")'

    assert reflection.run(f"!(get-type {evidence})") == [[parse("LintEvidence")]]
    assert reflection.run(f"!(get-type {intent})") == [[parse("LintIntent")]]


def test_the_ontology_loads_once(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta import _contract

    _contract.install(metta.runtime)
    _contract.install(metta.runtime)
    rows = metta._at("&petta").match(parse("(: Declaration $t)"))
    assert [str(row.t) for row in rows] == ["Type"]


def test_every_register_op_writes_its_declaration_and_get_doc_answers(metta, monkeypatch):
    """All five operation kinds are typed; docs follow the full lifecycle."""
    suffix = uuid.uuid4().hex

    def deterministic(value):
        """Deterministic operation documentation."""
        return value

    def nondeterministic(value):
        """Nondeterministic operation documentation."""
        yield value

    async def asynchronous(value):
        """Asynchronous operation documentation."""
        return value

    functions = (
        (
            f"p5-det-{suffix}",
            deterministic,
            "encoded",
            "det",
            EffectClass.pureStructural,
        ),
        (
            f"p5-many-{suffix}",
            nondeterministic,
            "encoded",
            "many",
            EffectClass.nondeterministicReadOnly,
        ),
        (
            f"p5-raw-det-{suffix}",
            deterministic,
            "raw",
            "raw_det",
            EffectClass.pureStructural,
        ),
        (
            f"p5-raw-many-{suffix}",
            nondeterministic,
            "raw",
            "raw_many",
            EffectClass.nondeterministicReadOnly,
        ),
        (
            f"p5-async-{suffix}",
            asynchronous,
            "encoded",
            "async",
            EffectClass.pureStructural,
        ),
    )
    reflection = metta._at("&petta")
    assert parse("(: OpKind Type)") in reflection
    assert reflection.run("!(get-type async)") == [[parse("OpKind")]]
    assert parse("(: op (-> Symbol Number OpKind OpDecl))") in reflection
    for name, fn, transport, kind, effect in functions:
        metta.op(fn, name=name, transport=transport, effect=effect)
        fact = parse(f"(op {name} 1 {kind})")
        assert fact in reflection
        assert metta._at("&petta").run(f"!(get-type {fact})") == [[parse("OpDecl")]]
        docs = metta.run(f"!(get-doc {name})")
        assert len(docs) == 1 and "operation documentation." in str(docs[0][0])

    # Retaining the same documentation during replacement must not remove the
    # shared atom when the previous registration releases its ownership.
    stable = f"p5-stable-{suffix}"

    def same(value):
        """Stable replacement documentation."""
        return value

    metta.op(same, name=stable, effect=EffectClass.pureStructural)
    metta.op(same, name=stable, effect=EffectClass.pureStructural)
    assert len(metta.run(f"!(get-doc {stable})")) == 1

    replacement = f"p5-replacement-{suffix}"

    def first(value):
        """First registration documentation."""
        return value

    def second(value):
        """Second registration documentation."""
        return value

    metta.op(first, name=replacement, effect=EffectClass.pureStructural)
    metta.op(second, name=replacement, effect=EffectClass.pureStructural)
    replaced_docs = metta.run(f"!(get-doc {replacement})")
    assert len(replaced_docs) == 1
    assert "Second registration documentation." in str(replaced_docs[0][0])
    assert "First registration documentation." not in str(replaced_docs[0][0])

    # Force the last transactional step to fail. The documentation was
    # retained already, so its absence proves rollback releases it too.
    rollback = f"p5-rollback-{suffix}"

    def documented_failure(value):
        """Documentation which must roll back."""
        return value

    runtime_type = type(metta.runtime)
    real_must = runtime_type.must
    failed = False

    def fail_compile(runtime, goal, **inputs):
        nonlocal failed
        if not failed and goal == "petta_py_compile_op(Name)" and inputs.get("Name") == rollback:
            failed = True
            msg = "forced registration failure"
            raise EngineError(msg)
        return real_must(runtime, goal, **inputs)

    monkeypatch.setattr(runtime_type, "must", fail_compile)
    with pytest.raises(EngineError, match="forced registration failure"):
        metta.op(
            documented_failure,
            name=rollback,
            effect=EffectClass.pureStructural,
        )
    assert metta.run(f"!(get-doc {rollback})") == [[]]
    assert parse(f"(op {rollback} 1 det)") not in reflection

    for name, *_ in functions:
        metta.unregister_op(name)
        assert metta.run(f"!(get-doc {name})") == [[]]
    for name in (stable, replacement):
        metta.unregister_op(name)
        assert metta.run(f"!(get-doc {name})") == [[]]


def test_the_fidelity_chain_rides_subtype_widening(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    petta_space = metta._at("&petta")
    petta_space.run("!(add-atom &petta (: ct-widen Exact))")
    answers = petta_space.run("!(get-type ct-widen)")
    assert [str(a) for a in answers[0]] == ["Exact", "Partial", "Sound"]


def test_a_registered_structural_effect_reaches_the_purity_walk(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def lookup(x: int) -> int:
        return x + 10

    metta.op(lookup, name="ct-mdecl", effect=EffectClass.pureStructural)
    metta.run("!(import! &self (library lib_tabling))")
    metta.run("(= (ct-mwrap $x) (ct-mdecl $x))")
    assert metta.run("!(tabled (ct-mwrap $x))") == [[True]]
    assert _effect_atom("ct-mdecl") in metta._at("&petta")


def test_an_unchecked_declaration_memoizes_an_impure_body(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    calls = []

    def draw(x: int) -> int:
        calls.append(x)
        return len(calls)

    metta.op(draw, name="ct-draw", effect=EffectClass.writesState)
    metta.run("!(import! &self (library lib_memo))")
    metta.run("(= (ct-uwrap $x) (ct-draw $x))")
    with pytest.raises(EngineError):
        metta.run("!(memoize ct-uwrap)")
    metta.run("!(add-atom &petta (cache ct-uwrap unchecked))")
    assert metta.run("!(memoize ct-uwrap)") == [[True]]
    # The declared acceptance is real: the second call answers from the
    # cache, so Python runs once and the answer repeats.
    first = metta.run("!(ct-uwrap 7)")
    second = metta.run("!(ct-uwrap 7)")
    assert first == second == [[1]]
    assert calls == [7]


def test_an_unchecked_declaration_tables_an_impure_body(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    calls = []

    def now(x: int) -> int:
        calls.append(x)
        return x

    metta.op(now, name="ct-tnow", effect=EffectClass.writesState)
    metta.run("!(import! &self (library lib_tabling))")
    metta.run("(= (ct-twrap $x) (ct-tnow $x))")
    metta.run("!(add-atom &petta (cache ct-twrap unchecked))")
    assert metta.run("!(tabled (ct-twrap $x))") == [[True]]


class _CtPoint:
    def __init__(self, x, y):
        self.x, self.y = x, y


def test_an_explicitly_registered_type_projects_from_an_op(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta import convert

    convert.register_type(
        _CtPoint,
        image="expression",
        to_atom=lambda p: (p.x, p.y),
        from_atom=lambda x, y: _CtPoint(x, y),
        name="CtPoint",
    )

    def mk(x: int, y: int):
        return _CtPoint(x, y)

    def spray(x: int):
        yield _CtPoint(x, 0)
        yield _CtPoint(0, x)

    metta.op(mk, name="ct-mkpt", effect=EffectClass.pureStructural)
    metta.op(
        spray,
        name="ct-spray",
        effect=EffectClass.nondeterministicReadOnly,
    )
    assert [str(a) for a in metta.run("!(ct-mkpt 3 4)")[0]] == ["(CtPoint 3 4)"]
    # The generator path crosses the same encoder, one projection per answer.
    assert [str(a) for a in metta.run("!(collapse (ct-spray 7))")[0]] == [
        "((CtPoint 7 0) (CtPoint 0 7))"
    ]


def test_a_memoized_default_never_projects_from_an_op(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    import dataclasses

    from metta import Grounded, convert

    @dataclasses.dataclass
    class _CtPlain:
        x: int

    # project() elsewhere memoizes a default for the type; the op result
    # must not change because of it: the floor is opaque, and only an
    # author's explicit opt-in projects.
    convert.project(_CtPlain(1))

    def mk(x: int):
        return _CtPlain(x)

    metta.op(mk, name="ct-plain", effect=EffectClass.writesState)
    answers = metta.run("!(ct-plain 5)")
    assert isinstance(answers[0][0], Grounded)


def test_an_explicit_handle_image_stays_opaque(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    import dataclasses

    from metta import Grounded, convert

    @dataclasses.dataclass
    class _CtHandle:
        x: int

    convert.register_type(_CtHandle, image="handle", name="CtHandle")

    def mk(x: int):
        return _CtHandle(x)

    metta.op(mk, name="ct-handle", effect=EffectClass.writesState)
    answers = metta.run("!(ct-handle 5)")
    assert isinstance(answers[0][0], Grounded)


def test_a_metta_hook_projects_from_an_op(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta import parse

    class _CtHooked:
        def __metta__(self):
            return parse("(hooked yes)")

    def mk():
        return _CtHooked()

    metta.op(mk, name="ct-hooked", effect=EffectClass.pureStructural)
    assert [str(a) for a in metta.run("!(ct-hooked)")[0]] == ["(hooked yes)"]


def test_register_type_reflects_an_image_atom(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta import convert

    class _CtImaged:
        pass

    convert.register_type(
        _CtImaged,
        image="expression",
        to_atom=lambda _v: (1,),
        from_atom=lambda _x: _CtImaged(),
        name="CtImaged",
    )
    petta_space = metta._at("&petta")
    assert parse("(type-image CtImaged expression)") in petta_space
    convert.unregister_type(_CtImaged)
    assert parse("(type-image CtImaged expression)") not in petta_space


def test_a_pre_boot_registration_is_reflected_by_the_snapshot(repo_root):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The listener hears the future; the snapshot hears the past. A type
    # registered before any engine exists must still appear in &petta.
    import subprocess
    import sys

    script = (
        "import sys; sys.path.insert(0, 'bindings/python')\n"
        "import metta\n"
        "from metta import convert, parse\n"
        "class Early: pass\n"
        "convert.register_type(Early, image='handle', name='CtSnapshot')\n"
        "m = metta.MeTTa(petta_path='.')\n"
        "print(parse('(type-image CtSnapshot handle)') in m.space('&petta'))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=repo_root / "PeTTa" if (repo_root / "PeTTa").exists() else repo_root,
        timeout=180,
    )
    assert result.stdout.strip().endswith("True"), result.stderr[-500:]


def test_auto_image_is_total_reproducible_and_two_valued():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta.convert import auto_image

    cases = {
        None: "transparent",
        True: "transparent",
        7: "transparent",
        1.5: "transparent",
        "s": "transparent",
        b"b": "transparent",
    }
    for value, want in cases.items():
        assert auto_image(value) == want
    assert auto_image([1, 2, 3]) == "transparent"
    assert auto_image(list(range(1000))) == "opaque"
    assert auto_image(iter([1, 2, 3])) == "opaque"  # unsized stays a handle
    assert auto_image(object()) == "opaque"
    # Reproducible, and never a third value.
    seen = {auto_image(v) for v in (None, [1], list(range(99)), object(), iter(()))}
    assert seen <= {"opaque", "transparent"}
    assert auto_image(list(range(1000))) == auto_image(list(range(1000)))


# ---------------------------------------------------- the handles route


class _RecordingProvider(SpaceProvider):
    """Yields its rows up to the limit it is handed, recording that limit.

    It does no filtering at all, which is legal: the engine re-unifies. What
    it records is the one thing the route decides, whether the caller's
    bound reached it.
    """

    def __init__(self, rows):
        self.rows = [parse(row) for row in rows]
        self.limits = []

    def atoms(self):
        return list(self.rows)

    def match(self, pattern, *, limit=None):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        self.limits.append(limit)
        for index, atom in enumerate(self.rows):
            if limit is not None and index >= limit:
                return
            yield atom


_EDGES = ["(edge a b)", "(edge b c)", "(edge c d)", "(edge d d)"]


def _routed(metta, name, entries):
    provider = _RecordingProvider(_EDGES)
    metta._register_space(provider, name)
    for entry in entries:
        metta.run(f"!(add-atom &petta (handles {name} {entry}))")
    return provider


def test_an_undeclared_space_keeps_todays_floor(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _routed(metta, "&hr-floor", [])
    metta.run("!(collapse (take 2 (match &hr-floor (edge $x $y) $y)))")
    assert provider.limits == [None]


def test_a_declared_exact_entry_licenses_the_take_bound(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _routed(metta, "&hr-exact", ["(edge $x $y) Exact"])
    out = metta.run("!(collapse (take 2 (match &hr-exact (edge $x $y) $y)))")
    assert provider.limits == [2]
    assert str(out[0][0]) == "(b c)"


def test_the_most_specific_entry_wins_and_sound_withholds_the_bound(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _routed(
        metta, "&hr-spec", ["(edge $x $y) Exact", "(edge $x $x) Sound"]
    )
    # The repeated-variable query routes to its own, more specific entry:
    # no bound reaches the provider, so the self-loop past the bound is
    # still found. A wrongly pushed bound would have lost it.
    out = metta.run("!(collapse (take 2 (match &hr-spec (edge $x $x) $x)))")
    assert provider.limits == [None]
    assert str(out[0][0]) == "(d)"
    # The general query still rides the Exact entry.
    provider.limits.clear()
    metta.run("!(collapse (take 2 (match &hr-spec (edge $x $y) $y)))")
    assert provider.limits == [2]


def test_a_join_never_offers_the_bound(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _routed(metta, "&hr-join", ["(edge $x $y) Exact"])
    out = metta.run(
        "!(collapse (take 2 (match &hr-join"
        " (, (edge $x $y) (edge $y $z)) (path $x $z))))"
    )
    assert set(provider.limits) == {None}
    assert str(out[0][0]) == "((path a c) (path b d))"


def test_a_refuse_entry_throws_before_the_provider_is_asked(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _routed(metta, "&hr-refuse", ["(secret $x) Refuse"])
    with pytest.raises(EngineError, match="Refuse"):
        metta.run("!(collapse (match &hr-refuse (secret $x) $x))")
    assert provider.limits == []
    # Other shapes still answer.
    metta.run("!(collapse (match &hr-refuse (edge $x $y) $y))")
    assert provider.limits == [None]


def test_an_in_adornment_matches_only_a_bound_argument(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _routed(metta, "&hr-adorn", ["(edge (in $a) $b) Refuse"])
    # A scan-only source in one line: bound-subject lookups are refused,
    # the free scan is not.
    metta.run("!(collapse (match &hr-adorn (edge $x $y) $y))")
    assert provider.limits == [None]
    with pytest.raises(EngineError, match="Refuse"):
        metta.run("!(collapse (match &hr-adorn (edge a $y) $y))")


def test_a_join_checks_access_patterns_at_plan_time(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _routed(metta, "&hr-modes", ["(edge (in $a) $b) Refuse"])
    # The nested loop would bind the second conjunct's subject per row,
    # which is the refused access pattern; the whole join is refused before
    # a single row is pulled, the Mercury-modes reading.
    with pytest.raises(EngineError, match="Refuse"):
        metta.run(
            "!(collapse (match &hr-modes"
            " (, (edge $x $y) (edge $y $z)) (p $x $z)))"
        )
    assert provider.limits == []


def test_overlapping_entries_that_disagree_are_loud(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _routed(metta, "&hr-clash", ["(edge a $y) Exact", "(edge $x b) Sound"])
    # (edge a b) is matched by both, neither is more specific, and the
    # claims differ: the critical pair is a declaration bug, named as one.
    with pytest.raises(EngineError, match="disagree"):
        metta.run("!(collapse (match &hr-clash (edge a b) ok))")
    # A query only the Sound entry matches routes without conflict: (edge
    # $q b) is outside (edge a $y) because subsumption never binds the
    # query's own variables.
    out = metta.run("!(collapse (match &hr-clash (edge $q b) ok))")
    assert str(out[0][0]) == "(ok)"


def test_overlapping_entries_that_agree_are_fine(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _routed(
        metta, "&hr-agree", ["(edge a $y) Exact", "(edge $x b) Exact"]
    )
    metta.run("!(collapse (take 1 (match &hr-agree (edge a b) ok)))")
    assert provider.limits == [1]


def test_a_declared_route_outranks_the_provider_pushdown_method(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class _Claimer(_RecordingProvider):
        def pushdown(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return "exact"

    provider = _Claimer(_EDGES)
    metta._register_space(provider, "&hr-rank")
    metta.run("!(add-atom &petta (handles &hr-rank (edge $x $x) Sound))")
    # The method says exact for everything; the declaration says Sound for
    # the repeated-variable shape, and the declaration wins there.
    metta.run("!(collapse (take 2 (match &hr-rank (edge $x $x) $x)))")
    assert provider.limits == [None]
    # Where nothing is declared the method is still the floor.
    provider.limits.clear()
    metta.run("!(collapse (take 2 (match &hr-rank (edge $x $y) $y)))")
    assert provider.limits == [2]


def test_declare_handles_writes_the_atom_and_routes(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _routed(metta, "&hr-sugar", [])
    atom = metta._at("&hr-sugar").handles("(edge $x $y)", "Exact")
    assert atom in metta._at("&petta")
    metta.run("!(collapse (take 2 (match &hr-sugar (edge $x $y) $y)))")
    assert provider.limits == [2]
    # Removing the returned atom withdraws the declaration: the floor.
    metta._at("&petta").remove(atom)
    provider.limits.clear()
    metta.run("!(collapse (take 2 (match &hr-sugar (edge $x $y) $y)))")
    assert provider.limits == [None]


def test_declare_handles_keeps_repeated_variables_shared(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _routed(metta, "&hr-sugar2", [])
    metta._at("&hr-sugar2").handles("(edge $x $y)", "Exact")
    metta._at("&hr-sugar2").handles("(edge $x $x)", "Sound")
    out = metta.run("!(collapse (take 2 (match &hr-sugar2 (edge $x $x) $x)))")
    assert provider.limits == [None]
    assert str(out[0][0]) == "(d)"


def test_declare_handles_rejects_a_conflict_eagerly(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _routed(metta, "&hr-sugar3", [])
    metta._at("&hr-sugar3").handles("(edge a $y)", "Exact")
    with pytest.raises(EngineError, match="disagree"):
        metta._at("&hr-sugar3").handles("(edge $x b)", "Sound")
    # The transaction rolled the losing atom back, so the overlap query
    # routes cleanly on the surviving entry instead of conflicting.
    out = metta.run("!(collapse (match &hr-sugar3 (edge a b) ok))")
    assert str(out[0][0]) == "(ok)"


def test_declare_handles_validates_the_fidelity_word(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="Exact, Partial, Sound, Refuse"):
        metta._at("&hr-sugar4").handles("(edge $x $y)", "Sorta")


def test_the_scan_only_source_in_two_declarations(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _routed(metta, "&hr-scan", [])
    metta._at("&hr-scan").handles("(edge (in $a) $b)", "Refuse")
    metta._at("&hr-scan").handles("(edge $x $y)", "Exact")
    # The free scan is exact, so the bound pushes; the bound-subject
    # lookup is the refused access pattern. Two atoms describe the whole
    # access model of a forward-only source.
    metta.run("!(collapse (take 2 (match &hr-scan (edge $x $y) $y)))")
    assert provider.limits == [2]
    with pytest.raises(EngineError, match="Refuse"):
        metta.run("!(collapse (match &hr-scan (edge a $y) $y))")


def test_a_sql_backed_space_under_declared_handles(metta):
    """The spec's own acceptance pair, on a real backend: (edge $x $y)
    Exact with (edge $x $x) Sound. SQL can express bound positions and a
    LIMIT, and cannot express a repeated variable, so the general entry
    licenses the bound and the narrower one withholds it exactly where the
    WHERE clause goes blind.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    import sqlite3

    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE edges (a TEXT, b TEXT)")
    connection.executemany(
        "INSERT INTO edges VALUES (?, ?)",
        [("a", "b"), ("b", "c"), ("c", "d"), ("d", "d")],
    )
    executed = []

    class SqlEdges(SpaceProvider):
        def atoms(self):
            rows = connection.execute("SELECT a, b FROM edges")
            return (parse(f"(edge {a} {b})") for a, b in rows)

        def match(self, pattern, *, limit=None):
            where, arguments = [], []
            if isinstance(pattern, Expression) and len(pattern.children) == 3:
                for column, child in zip(
                    ("a", "b"), pattern.children[1:], strict=True
                ):
                    if not isinstance(child, Variable):
                        where.append(f"{column} = ?")
                        arguments.append(str(child))
            sql = "SELECT a, b FROM edges"
            if where:
                sql += " WHERE " + " AND ".join(where)
            if limit is not None:
                sql += f" LIMIT {int(limit)}"
            executed.append(sql)
            rows = connection.execute(sql, arguments)
            return (parse(f"(edge {a} {b})") for a, b in rows)

    metta._register_space(SqlEdges(), "&sql")
    metta._at("&sql").handles("(edge $x $y)", "Exact")
    metta._at("&sql").handles("(edge $x $x)", "Sound")

    # The bound reaches SQL as LIMIT on the exact simple pattern.
    out = metta.run("!(collapse (take 2 (match &sql (edge $x $y) (edge $x $y))))")
    assert executed == ["SELECT a, b FROM edges LIMIT 2"]
    assert str(out[0][0]) == "((edge a b) (edge b c))"

    # A bound position reaches SQL as WHERE.
    executed.clear()
    out = metta.run("!(collapse (match &sql (edge d $y) $y))")
    assert executed == ["SELECT a, b FROM edges WHERE a = ?"]
    assert str(out[0][0]) == "(d)"

    # The repeated variable is the shape SQL's WHERE cannot see: the
    # narrower Sound entry wins, no LIMIT is pushed, and the self-loop
    # past the bound survives.
    executed.clear()
    out = metta.run("!(collapse (take 2 (match &sql (edge $x $x) $x)))")
    assert executed == ["SELECT a, b FROM edges"]
    assert str(out[0][0]) == "(d)"

    # Across a join the bound belongs to the joined rows: no LIMIT.
    executed.clear()
    metta.run(
        "!(collapse (take 2 (match &sql"
        " (, (edge $x $y) (edge $y $z)) (path $x $z))))"
    )
    assert executed
    assert all("LIMIT" not in sql for sql in executed)


# ------------------------------------------------------- source discipline


class _StreamProvider(SpaceProvider):
    """A one-shot source: the generator drains, like a cursor or a feed."""

    def __init__(self):
        self.gen = iter(parse(s) for s in ["(edge a b)", "(edge b c)", "(edge c d)"])

    def atoms(self):
        return self.gen


def test_a_linear_source_refuses_its_second_consumption(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_StreamProvider(), "&sd-lin")
    metta._at("&sd-lin").source("linear")
    out = metta.run("!(collapse (match &sd-lin (edge $x $y) $y))")
    assert str(out[0][0]) == "(b c d)"
    # The undeclared floor answered a silently empty set here; declared,
    # the drained source is a loud error naming the space.
    with pytest.raises(EngineError, match="second consumption"):
        metta.run("!(collapse (match &sd-lin (edge $x $y) $y))")
    # A fresh provider is a fresh source: re-registration resets the mark.
    metta._unregister_space("&sd-lin")
    metta._register_space(_StreamProvider(), "&sd-lin")
    out = metta.run("!(collapse (match &sd-lin (edge $x $y) $y))")
    assert str(out[0][0]) == "(b c d)"


def test_a_join_over_a_linear_source_is_refused(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_StreamProvider(), "&sd-join")
    metta._at("&sd-join").source("linear")
    # The nested loop's inner conjunct is a second physical touch: today's
    # floor answers a wrong empty join from the drained generator.
    with pytest.raises(EngineError, match="second consumption"):
        metta.run(
            "!(collapse (match &sd-join"
            " (, (edge $x $y) (edge $y $z)) (path $x $z)))"
        )


def test_the_undeclared_floor_keeps_todays_behaviour(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta._register_space(_StreamProvider(), "&sd-floor")
    assert str(metta.run("!(collapse (match &sd-floor (edge $x $y) $y))")[0][0]) == "(b c d)"
    assert str(metta.run("!(collapse (match &sd-floor (edge $x $y) $y))")[0][0]) == "()"


def test_declare_source_validates(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="linear, repeated, peek"):
        metta._at("&sd-v").source("stream")


def test_the_kit_catches_a_linear_object_declared_repeated():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta import testing

    with pytest.raises(AssertionError, match="second enumeration disagrees"):
        testing.check_space_provider(_StreamProvider(), source="repeated")
    # Declared honestly, the one-shot checks pass and the rest skip loudly.
    checks = testing.check_space_provider(_StreamProvider(), source="linear")
    assert any("skipped" in line for line in checks)
