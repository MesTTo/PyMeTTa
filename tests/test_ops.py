"""Purpose: engine-backed tests for Python-backed MeTTa functions: kinds,
typing from annotations, defaults as arities, declines, errors, raw mode.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import uuid

import pytest

from petta import Atom, Decline, EngineError, Expr, S, Sym, expr, val


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_det_op_composes_with_equations(metta):
    name = unique("dbl")

    @metta.register_op(name=name)
    def double(x: int) -> int:
        return 2 * x

    assert metta.run(f"!({name} 21)") == [[42]]
    quad = unique("quad")
    assert metta.run(f"(= ({quad} $x) ({name} ({name} $x)))\n!({quad} 5)") == [[20]]


def test_generator_is_nondeterministic(metta):
    name = unique("upto")

    @metta.register_op(name=name)
    def upto(n: int):
        yield from range(1, n + 1)

    assert metta.run(f"!(collapse ({name} 3))") == [[expr(1, 2, 3)]]
    # Composes with let and arithmetic like any nondeterministic function.
    assert metta.run(f"!(collapse (let $x ({name} 3) (* $x 10)))") == [[expr(10, 20, 30)]]


def test_none_and_decline_answer_nothing(metta):
    evens = unique("evens")
    picky = unique("picky")

    @metta.register_op(name=evens)
    def only_even(x: int):
        return x if x % 2 == 0 else None

    @metta.register_op(name=picky)
    def picky_op(x: int):
        if x < 0:
            raise Decline
        return x

    r = metta.run(f"!(collapse (superpose (({evens} 1) ({evens} 2) ({evens} 3))))")
    assert r == [[expr(2)]]
    r = metta.run(f"!(collapse (superpose (({picky} -1) ({picky} 7))))")
    assert r == [[expr(7)]]


def test_python_exception_is_a_hard_error(metta):
    name = unique("boom")

    @metta.register_op(name=name)
    def boom(x: int) -> int:
        raise ValueError("exploded on purpose")

    with pytest.raises(EngineError) as excinfo:
        metta.run(f"!({name} 1)")
    assert "exploded on purpose" in str(excinfo.value)


def test_annotations_declare_types(metta):
    name = unique("typed")

    @metta.register_op(name=name)
    def typed_op(x: int) -> int:
        return x

    assert metta.run(f"!(get-type ({name} 1))") == [[S.Number]]


def test_defaults_register_every_arity(metta):
    name = unique("greet")

    @metta.register_op(name=name)
    def greet(who: str, greeting: str = "hello") -> str:
        return f"{greeting}, {who}"

    assert metta.run(f'!({name} "Ada")') == [["hello, Ada"]]
    assert metta.run(f'!({name} "Ada" "hi")') == [["hi, Ada"]]


def test_ops_see_atoms_not_mush(metta):
    name = unique("peek")
    seen = []

    @metta.register_op(name=name)
    def peek(x) -> bool:
        seen.append(x)
        return True

    metta.run(f'!({name} foo)\n!({name} "foo")\n!({name} True)\n!({name} (a 1))')
    sym_arg, str_arg, bool_arg, expr_arg = seen
    assert sym_arg == S.foo and isinstance(sym_arg, Sym)
    assert str_arg == "foo" and isinstance(str_arg, str)
    assert bool_arg is True
    assert isinstance(expr_arg, Expr) and expr_arg[0] == S.a and expr_arg[1] == 1


def test_pass_atoms_hands_over_atoms(metta):
    name = unique("atoms")
    seen = []

    @metta.register_op(name=name, pass_atoms=True)
    def watch(x) -> bool:
        seen.append(x)
        return True

    metta.run(f"!({name} 42)")
    assert isinstance(seen[0], Atom) and seen[0] == 42


def test_objects_flow_through_ops_by_identity(metta):
    make = unique("make")
    read = unique("read")

    class Counter:
        def __init__(self):
            self.n = 0

    box = []

    @metta.register_op(name=make)
    def make_counter():
        c = Counter()
        box.append(c)
        return val(c)

    @metta.register_op(name=read)
    def read_counter(c) -> int:
        assert c is box[0]
        c.n += 1
        return c.n

    assert metta.run(f"!({read} ({make}))") == [[1]]
    assert box[0].n == 1


def test_raw_mode_for_number_work(metta):
    name = unique("rawsum")

    @metta.register_op(name=name, raw=True, typed=False)
    def raw_sum(a, b):
        return a + b

    assert metta.run(f"!({name} 20 22)") == [[42]]


def test_operation_registration_names_are_symmetric(metta):
    assert hasattr(metta, "register_op")
    assert hasattr(metta, "unregister_op")
    assert metta.op.__func__ is metta.register_op.__func__
    assert metta.unregister.__func__ is metta.unregister_op.__func__

    @metta.register_op
    def very_unique_op_name_xyz(x: int) -> int:
        return x

    assert metta.run("!(very-unique-op-name-xyz 9)") == [[9]]
    metta.unregister_op("very-unique-op-name-xyz")
    # Unregistered: the call no longer reduces, the engine leaves it inert.
    r = metta.run("!(very-unique-op-name-xyz 9)")
    assert r == [[expr(S["very-unique-op-name-xyz"], 9)]]


def test_var_kw_params_are_refused(metta):
    with pytest.raises(TypeError):

        @metta.register_op
        def bad(*args):
            return 0

    with pytest.raises(TypeError):

        @metta.register_op
        def bad2(*, key=1):
            return 0
