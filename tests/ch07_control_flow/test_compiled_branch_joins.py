"""Purpose: prove a compiled function continues past an if or a match the way
Python does, each arm that falls through running the statements after the
branch, from a plain body, an elif chain, a loop body, a try body and a
constructor alike.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import importlib.util
from dataclasses import dataclass

import pytest

from metta import Expression, S, Space
from metta._errors.errors import CompileError, MettaResultError


def _atom_size(atom):
    return 1 + sum(map(_atom_size, atom)) if isinstance(atom, Expression) else 1


def _seen(space):
    return sorted(str(atom) for atom in space.atoms() if str(atom).startswith("(Seen"))


def _equations(space, name):
    return [
        atom for atom in space.atoms()
        if isinstance(atom, Expression) and atom.head == S["="]
        and isinstance(atom[1], Expression) and str(atom[1].head).startswith(name)
    ]


def test_the_reports_if_else_runs_the_statement_after_it(scratch_space):
    """Syntropy's program: neither arm returns, so both reach `return 7`."""
    m = scratch_space

    @m.define
    def effects(flag):
        if flag:
            S.add_atom(S.context_space(), S.Seen(1))
        else:
            S.add_atom(S.context_space(), S.Seen(2))
        return 7

    assert list(effects(flag=True)) == [7]
    assert _seen(m) == ["(Seen 1)"]
    assert list(effects(flag=False)) == [7]
    assert _seen(m) == ["(Seen 1)", "(Seen 2)"]


def test_an_else_less_if_whose_arm_falls_through_runs_what_follows(scratch_space):
    """The true arm used to answer None and skip `return 7`."""
    m = scratch_space

    @m.define
    def effect_then_seven(flag):
        if flag:
            S.add_atom(S.context_space(), S.Seen(1))
        return 7

    assert list(effect_then_seven(flag=True)) == [7]
    assert list(effect_then_seven(flag=False)) == [7]
    assert _seen(m) == ["(Seen 1)"]


def test_a_match_whose_arms_fall_through_runs_what_follows(scratch_space):
    """A matched arm continues too, and an exhaustive match is no longer refused."""
    m = scratch_space

    @m.define
    def partial(x):
        match x:
            case 1:
                S.add_atom(S.context_space(), S.Seen(1))
        return 7

    @m.define
    def total(x):
        match x:
            case 1:
                S.add_atom(S.context_space(), S.Seen(10))
            case _:
                S.add_atom(S.context_space(), S.Seen(0))
        return 7

    assert [list(partial(1)), list(partial(2))] == [[7], [7]]
    assert [list(total(1)), list(total(2))] == [[7], [7]]
    assert _seen(m) == ["(Seen 0)", "(Seen 1)", "(Seen 10)"]


def test_an_elif_chain_and_a_loop_body_continue_past_their_branch(scratch_space):
    """The loop's true arm used to recur straight after its own statement."""
    m = scratch_space

    @m.define
    def classified(x):
        y = 0
        if x == 1:
            y = 10
        elif x == 2:
            y = 20
        return y + 1

    @m.define
    def accumulated(xs):
        total = 0
        for x in xs:
            if x > 0:
                total = total + x
            total = total + 100
        return total

    assert [classified(x).one() for x in (1, 2, 3)] == [11, 21, 1]
    assert accumulated((1, -1, 2)).one() == accumulated.py((1, -1, 2)) == 303


def test_an_unmatched_subject_falls_through_to_what_follows_and_otherwise_answers_nothing(scratch_space):
    """With statements after it, an unmatched case continues into them, as
    Python's does; with nothing after it, nested or not, it answers nothing,
    as MeTTa's case does.
    """  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose
    m = scratch_space

    @m.define
    def unmatched_then(key, flag):
        if flag:
            match key:
                case 1:
                    return S.one
        return S.after

    @m.define
    def case_band(key):
        match key:
            case 90:
                return True
            case remaining:
                match remaining:
                    case 40:
                        return False

    assert [unmatched_then(1, flag=True).one(), unmatched_then(2, flag=True).one(), unmatched_then(1, flag=False).one()] == [
        S.one, S.after, S.after,
    ]
    assert case_band(55) == []
    assert m.fn.not_provable(S.case_band(55)) == [True]
    assert m.fn.not_provable(S.case_band(90)) == [False]


def test_a_branch_in_a_try_body_continues_inside_the_try(scratch_space):
    """The joined statements still run under the try's handlers."""
    m = scratch_space

    @m.define
    def guarded(x):
        try:
            if x > 0:
                y = 10 // (x - 1)
            else:
                y = -1
            z = y + 1
        except ZeroDivisionError:
            z = 0
        return z

    assert [guarded(x).one() for x in (3, 1, -4)] == [guarded.py(x) for x in (3, 1, -4)] == [6, 0, 0]


def test_one_arm_reaching_the_rest_compiles_it_in_place(scratch_space):
    """An early return leaves one arm falling through, so no helper is minted;
    two arms falling through share one helper, called from each.
    """  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose
    m = scratch_space

    @m.define
    def early(n):
        if n > 0:
            return n
        m2 = n * 2
        return m2 + 1

    @m.define
    def shared(n):
        if n > 0:
            n = n + 1
        else:
            n = n - 1
        return n * 10

    assert [early(4).one(), early(-3).one()] == [4, -5]
    assert [shared(4).one(), shared(-3).one()] == [50, -40]
    assert len(_equations(m, "early")) == 1
    helpers = [atom for atom in _equations(m, "shared") if "--after-branch-" in str(atom[1].head)]
    assert len(helpers) == 1
    calls = str(shared.body).count(str(helpers[0][1].head))
    assert calls == 2


def _branch_chain(count):
    """Sequential if/else branches whose arms both fall through."""
    source = [f"def branch_chain_{count}(x):", "    value = 0"]
    for _ in range(count):
        source += ["    if x > 0:", "        value = value + 1", "    else:", "        value = value + 2"]
    return [*source, "    return value"]


def _guarded_cases(count):
    """Guarded cases of two alternatives each, then a case that falls through."""
    source = [f"def guarded_cases_{count}(x):", "    match x:"]
    for case in range(1, count + 1):
        source += [f"        case {case} | {case + 100} if x > {case - 1}:", f"            return {case}"]
    return [*source, "        case _:", "            x = x * 2", "    return x"]


def _nested_alternatives(count):
    """Nested matches whose arm of two alternatives falls through at every level."""
    source = [f"def nested_alternatives_{count}(x):", "    total = 0"]
    indent = "    "
    for level in range(1, count + 1):
        source += [f"{indent}match x % 3:", f"{indent}    case 1 | 2:", f"{indent}        total = total + {level}"]
        indent += "        "
    return [*source, f"{indent}total = total + x", "    return total"]


@pytest.mark.parametrize("shape", [_branch_chain, _guarded_cases, _nested_alternatives])
def test_emitted_size_is_linear_in_branches_guarded_cases_and_alternatives(scratch_space, tmp_path, shape):
    """Count every stored helper too, so moving duplication cannot hide it: a
    guard places the later cases twice and alternatives share one arm, and
    neither multiplies what follows.
    """  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose
    m = scratch_space
    inputs = (-1, 0, 1, 2, 3, 101)
    sizes = []
    for count in (1, 2, 4, 8):
        source = shape(count)
        name = source[0].removeprefix("def ").split("(")[0]
        path = tmp_path / f"{name}.py"
        path.write_text("\n".join(source) + "\n")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        native = getattr(module, name)
        function = m.define(native)
        sizes.append(sum(map(_atom_size, _equations(m, function.name))))
        assert [list(function(x)) for x in inputs] == [[native(x)] for x in inputs]
    step = sizes[1] - sizes[0]
    assert [sizes[2] - sizes[1], sizes[3] - sizes[2]] == [2 * step, 4 * step]


def test_alternatives_share_one_body_with_their_own_bindings(scratch_space):
    """Each alternative binds the pattern's names in its own positions and
    calls the one body, so a loop in that body compiles once; alternatives
    that prove different things about a name each keep their own body.
    """  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose
    m = scratch_space

    @m.define
    def positions(pair):
        total = 0
        match pair:
            case (a, 1) | (1, a):
                total = a * 10
        return total + 1

    @m.define
    def looped(x):
        total = 0
        match x:
            case 1 | 2 | 3:
                for k in (1, 2):
                    total = total + k * x
            case _:
                total = -1
        return total

    @m.define
    def extended(pair):
        match pair:
            case (2, rest) | (1, *rest):
                return rest + (9,)  # noqa: RUF005 -- concatenation is the operation whose operand kind is under test
        return ()

    assert [positions(pair).one() for pair in ((5, 1), (1, 7), (2, 2))] == [51, 71, 1]
    assert [looped(x).one() for x in (1, 2, 3, 4)] == [looped.py(x) for x in (1, 2, 3, 4)] == [3, 6, 9, -1]
    assert [len(_equations(m, f"looped--{label}-")) for label in ("case-body", "each")] == [1, 1]
    # Python's rest is the tuple (5, 6) in the first alternative and the list
    # [5, 6] in the second, which a tuple cannot extend.
    assert extended((2, (5, 6))).one() == Expression([5, 6, 9])
    with pytest.raises(MettaResultError, match="can only concatenate list"):
        extended((1, 5, 6)).one()


def test_a_small_default_and_a_small_shared_body_stay_in_place(scratch_space):
    """Sharing costs a call at each place and an equation, so a term smaller
    than that is copied: the common guarded case followed by a default, and
    an alternative pattern's short body, keep their code inline.
    """  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose
    m = scratch_space

    @m.define
    def signed(x):
        match x:
            case n if n > 0:
                return 1
            case _:
                return 0

    @m.define
    def small(x):
        match x:
            case 1 | 2:
                return 0
        return x

    assert [signed(x).one() for x in (5, -5)] == [signed.py(x) for x in (5, -5)] == [1, 0]
    assert [small(x).one() for x in (1, 2, 3)] == [small.py(x) for x in (1, 2, 3)] == [0, 0, 3]
    assert [len(_equations(m, name)) for name in ("signed", "small")] == [1, 1]


def test_statements_no_arm_reaches_are_refused_as_unreachable(scratch_space):
    """Every arm returning leaves nothing to run after the branch."""
    def both_return(flag):
        if flag:
            return 1
        else:  # noqa: RET505 -- the else arm is the compiler input under test
            return 2
        return 3

    def every_case_returns(x):
        match x:
            case 1:
                return 1
            case _:
                return 2
        return 3

    for function in (both_return, every_case_returns):
        with pytest.raises(CompileError, match=r"unreachable.*every arm returns or raises"):
            scratch_space.define(function)


def test_a_value_read_after_a_branch_is_bound_on_every_path(scratch_space):
    """Python's UnboundLocalError for the path that skipped the binding, refused with its remedy."""
    def missing(flag):
        if flag:
            value = 1
        return value

    with pytest.raises(CompileError, match=r"value.*not bound.*bind.*every arm"):
        scratch_space.define(missing)


class JoinedEntity:
    """An entity whose constructor joins an if/else before its last field."""

    x: int
    y: int

    def __init__(self, a: int):
        """Choose x in either arm, then set y after the join."""
        if a < 0:
            self.x = 0
        else:
            self.x = a
        self.y = 5


class ElseLessEntity:
    """An entity whose constructor's else-less arm falls through."""

    x: int
    y: int

    def __init__(self, a: int):
        """Maybe clamp x, then set y after the if."""
        self.x = a
        if a < 0:
            self.x = 0
        self.y = 5


class LoopLastEntity:
    """An entity whose constructor ends in a loop that never reads its receiver."""

    x: int

    def __init__(self, a: int):
        """Set x, then run a loop over locals only."""
        self.x = a
        t = 0
        for k in (1, 2):
            t = t + k


@dataclass(frozen=True)
class JoinedValue:
    """A value whose constructor binds a field in both arms of a join."""

    x: int
    y: int

    def __init__(self, a: int):
        """Choose x in either arm, then set y after the join."""
        if a < 0:
            self.x = 0
        else:
            self.x = a
        self.y = 5


def test_constructors_keep_their_receiver_and_fields_across_branches_and_loops(scratch_space):
    """A constructor's closer reads the receiver, or a value's fields, which no
    statement spells: the join and a trailing loop carry them all the same.
    """  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose
    m = scratch_space
    for cls in (JoinedEntity, ElseLessEntity, LoopLastEntity):
        m.define(cls)
    assert [(item.x, item.y) for item in map(JoinedEntity, (-3, 4))] == [(0, 5), (4, 5)]
    assert [(item.x, item.y) for item in map(ElseLessEntity, (-3, 4))] == [(0, 5), (4, 5)]
    assert [item.x for item in map(LoopLastEntity, (-3, 4))] == [-3, 4]
    m.define(JoinedValue)
    assert m.eval(S["make-JoinedValue"](-3)) == [S.JoinedValue(0, 5)]
    assert m.eval(S["make-JoinedValue"](4)) == [S.JoinedValue(4, 5)]


def test_a_space_parameter_records_each_arm_that_falls_through(scratch_space):
    """The effects of every arm that runs, then the joined statement's own."""
    m = scratch_space

    @m.define
    def logged(target: Space, a: int):
        if a > 0:
            target += S.Seen(1, a)
        elif a < 0:
            target += S.Seen(2, a)
        target += S.Seen(3, a)
        return a

    for a in (5, -5, 0):
        with m._new_space() as native, m._new_space() as compiled:
            assert logged(compiled, a).one() == logged.py(native, a) == a
            assert [str(atom) for atom in compiled.atoms()] == [str(atom) for atom in native.atoms()]
