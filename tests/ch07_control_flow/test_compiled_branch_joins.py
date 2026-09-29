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
from metta._errors.errors import CompileError


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


def _chain(tmp_path, count):
    name = f"value_chain_{count}"
    source = [f"def {name}(flag, value: int):"]
    for _ in range(count):
        source.extend([
            "    if flag:",
            "        value = value + 1",
            "    else:",
            "        value = value + 2",
        ])
    source.append("    return value")
    path = tmp_path / f"{name}.py"
    path.write_text("\n".join(source) + "\n")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name)


def test_emitted_size_is_linear_across_sequential_branches(scratch_space, tmp_path):
    """Count every stored helper too, so moving duplication cannot hide it."""
    m = scratch_space
    sizes = []
    for count in (1, 2, 4, 8):
        function = m.define(_chain(tmp_path, count))
        sizes.append(sum(map(_atom_size, _equations(m, function.name))))
        assert function(flag=False, value=0).one() == 2 * count
        assert function(flag=True, value=0).one() == count
    step = sizes[1] - sizes[0]
    assert [sizes[2] - sizes[1], sizes[3] - sizes[2]] == [2 * step, 4 * step]


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
