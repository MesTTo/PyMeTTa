"""Purpose: pin the public contextual names, inferred target types, save format,
and constants.
Guarantees:
  - type hints distinguish spaces, MeTTa functions, and save formats
    [tested: test_canonical_context_types_replace_public_newtypes]
  - cast and build preserve a concrete target class for static callers [tested
    test_target_type_overloads_preserve_the_requested_class]
  - cast's implementation-only target name is not a keyword API [tested
    test_cast_target_is_positional_only]
  - the fixed cache, constructor, and close policies are Final [tested
    test_policy_constants_are_final]
  - root persistence and async three-valued evaluation annotations retain the
    runtime value species [tested: test_root_space_hint_accepts_pathlike_journals,
    test_async_result_hints_preserve_undefined_answers; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]
  - every public door that wants a space answers the same for a context and
    for that context's home space [tested:
    test_every_space_door_takes_a_context_or_a_space; commit=f25ac80f93e7c3626b87e593117d09b9c9bc8c95]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import inspect
import os
from typing import Any, Final, get_args, get_overloads, get_type_hints

import metta_arrays as arrays
import pytest

import metta
from metta import (
    MeTTa,
    S,
    V,
    _api_types,
    aio,
    algebra,
    convert,
    integrate,
    lint,
    live,
    parse,
    remote,
    structures,
    tables,
)
from metta import _atom_namespace as atom_namespace
from metta._ops import Operation
from metta._space import Space, current_space
from metta.convert import cast
from metta.vocabularies import SaveFormat


def test_canonical_context_types_replace_public_newtypes():
    """Space handles and symbols replace the two public string NewTypes."""
    assert "SpaceName" not in dir(metta)
    assert "MettaName" not in dir(metta)
    assert _api_types.__all__ == []
    assert get_type_hints(Space.save)["format"] is SaveFormat
    assert get_type_hints(aio.AsyncMeTTa.save)["format"] is SaveFormat
    assert issubclass(SaveFormat, str)
    assert [member.value for member in SaveFormat] == ["metta", "fast"]


def test_root_space_hint_accepts_pathlike_journals():
    """The root facade exposes the persistence path accepted at runtime."""
    assert get_type_hints(metta.space)["journal"] == str | os.PathLike[str] | None


def test_async_result_hints_preserve_undefined_answers():
    """Every async route exposing WFS answers includes Undefined."""
    direct = get_overloads(aio.AsyncMeTTa.eval)
    # Explicit option selections have their own return product. Omitted
    # answer selection retains the precise scalar and grouped WFS types.
    assert [get_type_hints(overload)["return"] for overload in direct] == [
        Any,
        Any,
        list[metta.Atom | metta.Undefined],
        list[list[metta.Atom | metta.Undefined]],
    ]
    assert all(inspect.signature(overload).parameters[option].default is
               inspect.Parameter.empty for overload, option in
               zip(direct[:2], ("delivery", "answer"), strict=True))
    assert all("answer" not in inspect.signature(overload).parameters
               for overload in direct[2:])
    assert get_type_hints(aio.AsyncSaga.run)["return"] == list[
        metta.Atom | metta.Undefined
    ]
    assert get_type_hints(aio.AsyncWorld.eval)["return"] == tuple[
        list[metta.Atom | metta.Undefined], aio.AsyncWorld
    ]


def test_a_name_parameter_takes_a_plain_string():
    """A NewType is deliberately not assignable from str, which is right for
    a value threaded through internals and wrong for a parameter users pass
    literals to. The typing reference's own example constructs at the
    boundary, get_user_name(UserId(42351)), and the ergonomic spelling was
    an error in five separate example programs before this: register_space
    (name="&cmetta"), unregister_space("&crm"), MeTTa(space="&bounds-demo"),
    register_op(name="fuzmatch") and is_function("<lambda>")
    [measured 2026-08-17].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    # space() also takes back the Space it answers, so its union is asserted
    # by MEMBERSHIP. What is pinned is unchanged: a literal still fits, which
    # a NewType would not.
    space_name = set(get_args(get_type_hints(MeTTa.space)["name"]))
    assert {str, Space, type(None)} <= space_name
    assert get_type_hints(Space.op)["name"] == str | None
    assert get_type_hints(Space.is_function)["name"] is str
    assert get_type_hints(Space._register_space)["name"] is str
    # The async doors forward straight into Space(space), so their parameter
    # IS the constructor's name domain; equality keeps the three doors from
    # drifting, and membership keeps the literal-fits law pinned.
    async_space = get_type_hints(aio.AsyncMeTTa.__init__)["space"]
    assert async_space == get_type_hints(Space.__init__)["name"]
    assert async_space == get_type_hints(aio.connect)["space"]
    assert str in get_args(async_space)
    assert get_type_hints(current_space)["default"] is str


def test_internal_identifier_types_do_not_reopen_public_doors():
    """Transport identifiers remain distinct but private to the engine seam."""
    assert get_type_hints(Operation)["name"] is _api_types._OperationName
    assert get_type_hints(Operation)["space"] == _api_types._SpaceId | None
    assert get_type_hints(Space.name.fget)["return"] is _api_types._SpaceId
    assert get_type_hints(current_space)["return"] is _api_types._SpaceId


def test_policy_constants_are_final():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert get_type_hints(aio)["DEFAULT_CLOSE_TIMEOUT"] == Final[float]
    assert get_type_hints(atom_namespace)["NAMESPACE_CACHE_MAX"] == Final[int]
    assert get_type_hints(arrays)["_CONSTRUCTOR_ARITIES"] == Final[dict[str, tuple[int, ...]]]
    assert get_type_hints(current_space)["return"] is _api_types._SpaceId


def test_target_type_overloads_preserve_the_requested_class():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    for function in (cast, Space.cast, aio.AsyncMeTTa.cast, convert.build):
        typed_target = get_overloads(function)[0]
        hints = get_type_hints(typed_target)
        target = hints["type_" if "type_" in hints else "cls"]
        assert get_args(target) == (hints["return"],)


def test_cast_target_is_positional_only():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    for function in (cast, Space.cast, aio.AsyncMeTTa.cast):
        assert (
            inspect.signature(function).parameters["type_"].kind
            is inspect.Parameter.POSITIONAL_ONLY
        )

    with pytest.raises(TypeError, match="positional-only"):
        cast(None, 3, type_=int)


def test_a_handle_is_a_grounded_species():
    """The canonical glossary's law in the class tree: a handle answers
    isinstance against Grounded, deconstructs to nothing, is always truthy,
    refuses raw-value ordering, and its value slot is deliberately unset so
    a payload read names the mistake instead of answering something.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    import pytest

    from metta import Grounded, MeTTa

    space = MeTTa().space()
    assert isinstance(space, Grounded)
    assert bool(space) is True
    with pytest.raises(AttributeError):
        _ = space.value
    match space:
        case Grounded():
            pass
        case _:
            msg = "a handle must match the Grounded pattern"
            raise AssertionError(msg)


class _OneRow:
    """The DB-API slice a table bridge stands on, answering one row."""

    def execute(self, _sql, _parameters=()):
        return [("a1", "b1")]

    def commit(self):
        return None

    def rollback(self):
        return None


def _stub_integration(tag):
    import types

    module = types.ModuleType(f"api_types_probe_{tag}")
    module.install_metta = lambda space: space.add(S["door-installed"]())
    return module


def _cast(receiver, _tag, _tmp_path):
    return cast(receiver, 3, int)


def _lint(receiver, _tag, _tmp_path):
    receiver.run("(= (door-lint) (if True 1 1))")
    return sorted({finding.kind for finding in lint.lint(receiver)})


def _lint_file(receiver, _tag, tmp_path):
    path = tmp_path / "door.metta"
    path.write_text("(= (door-lint-file) (if True 1 1))\n", encoding="utf-8")
    return sorted({finding.kind for finding in lint.lint_file(path, m=receiver)})


def _tabled_map(receiver, _tag, _tmp_path):
    receiver.run("(= (door-double $x) (* 2 $x))")
    return structures.TabledMap(receiver, "door-double")[(4,)]


def _live_view(receiver, _tag, _tmp_path):
    receiver.add(S["door-alert"](S.red))
    view = structures.LiveView(receiver, S["door-alert"](V.level))
    try:
        return len(view)
    finally:
        view.close()


def _live(receiver, _tag, _tmp_path):
    receiver.add(S["door-live"](S.red))
    view = live.Live(receiver, S["door-live"](V.level))
    try:
        return len(view)
    finally:
        view.close()


def _closure_view(receiver, tag, _tmp_path):
    relation = f"door-rel-{tag}"
    receiver.add(S[relation](S.a, S.b), S[relation](S.b, S.c))
    return (S.a, S.c) in structures.ClosureView(receiver, relation)


def _tables_declare(receiver, tag, _tmp_path):
    stored = tables.declare(
        receiver,
        f"&door-{tag}",
        "(bridge (edge $a $b) (row edges (a $a) (b $b)))",
    )
    return str(stored.children[2])


def _tables_from_context(receiver, tag, _tmp_path):
    tables.declare(
        receiver,
        f"&door-bridge-{tag}",
        "(bridge (edge $a $b) (row edges (a $a) (b $b)))",
    )
    bridge = tables.TableBridge.from_context(
        receiver, f"&door-bridge-{tag}", _OneRow()
    )
    return [str(atom) for atom in bridge.atoms()]


def _tables_add(receiver, _tag, _tmp_path):
    return tables.add(receiver, S["door-row"], [(1,), (2,)])


def _algebra_declare(receiver, tag, _tmp_path):
    declared = algebra.declare(
        receiver, f"door-{tag}", combine="max", extend="min", zero=0, one=1
    )
    return str(declared.children[2])


def _algebra_resolve(receiver, _tag, _tmp_path):
    return algebra.resolve(receiver, "bool").name


def _algebra_evaluate(receiver, _tag, _tmp_path):
    receiver.add(algebra.tagged_fact(1, S["door-seed"](0)))
    evaluation = algebra.evaluate(receiver, S["door-seed"](0), algebra="counting")
    return [str(answer.tag) for answer in evaluation.answers]


def _algebra_sample(receiver, tag, _tmp_path):
    algebra.declare(
        receiver, f"door-rates-{tag}", combine="+", extend="*", zero=0, one=1
    )
    receiver.add(
        algebra.tagged_fact(parse("(rate 1)"), S["door-branch"](S.slow)),
        algebra.tagged_fact(parse("(rate 3)"), S["door-branch"](S.fast)),
    )
    drawn = algebra.sample(
        receiver,
        S["door-branch"](V.which),
        algebra=f"door-rates-{tag}",
        draws=4,
        seed=7,
    )
    return len(drawn)


def _integrate(receiver, tag, _tmp_path):
    installed = integrate.integrate(receiver, _stub_integration(tag))
    return installed.removesuffix(tag)


def _gateway(receiver, _tag, _tmp_path):
    receiver.add(S["door-served"](1))
    gateway = remote.Gateway(receiver)
    try:
        return gateway("atoms", {})["atoms"]
    finally:
        gateway.close()


#: Every public door that wants a SPACE, with what it answers. A context is
#: what a caller usually holds, and MeTTa refuses a Space door rather than
#: forwarding it, so each of these used to die on the first Space door it
#: reached: `MeTTa has no 'parse'` from tables.declare, `MeTTa has no 'name'`
#: from lint, algebra and the closure view, `'MeTTa' object has no attribute
#: '_space'` from cast. Keeping the inventory together is what makes a new
#: door extend the property instead of drifting away from its siblings.
SPACE_DOORS = {
    "algebra.declare": (_algebra_declare, "max"),
    "algebra.evaluate": (_algebra_evaluate, ["1"]),
    "algebra.resolve": (_algebra_resolve, "bool"),
    "algebra.sample": (_algebra_sample, 4),
    "convert.cast": (_cast, 3),
    "integrate.integrate": (_integrate, "api_types_probe_"),
    "lint.lint": (_lint, ["constant-if-true"]),
    "lint.lint_file": (_lint_file, ["constant-if-true"]),
    "remote.Gateway": (_gateway, [["e", [["s", "door-served"], ["n", 1]]]]),
    "structures.ClosureView": (_closure_view, True),
    "live.Live": (_live, 1),
    "structures.LiveView": (_live_view, 1),
    "structures.TabledMap": (_tabled_map, 8),
    "tables.TableBridge.from_context": (_tables_from_context, ["(edge a1 b1)"]),
    "tables.add": (_tables_add, 2),
    "tables.declare": (_tables_declare, "(edge $a $b)"),
}


@pytest.mark.parametrize("door", sorted(SPACE_DOORS))
@pytest.mark.parametrize("receiver_kind", ["space", "context"])
def test_every_space_door_takes_a_context_or_a_space(door, receiver_kind, tmp_path):
    """One resolution, at every door: `_api_types.space_of`.

    The distinction the two classes draw stays: a context still refuses a
    Space door rather than forwarding it. What changes is that a door which
    WANTS a space says so once, at its own boundary, instead of failing
    somewhere inside on whichever Space door it happened to reach first.
    """
    exercise, expected = SPACE_DOORS[door]
    with MeTTa() as context:
        receiver = context.self if receiver_kind == "space" else context
        assert exercise(receiver, receiver_kind, tmp_path) == expected
