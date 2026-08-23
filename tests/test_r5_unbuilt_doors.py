"""Purpose: prove the thirteen R5 Python doors replace their corpus workarounds.

Assumes:
  - R6 supplies the canonical root atoms and iterable ``Expression`` after
    integration; these tests use neither a duplicate nor a compatibility copy.
Guarantees:
  - each numbered R5 item has a direct behavioral regression [tested:
    python -m pytest bindings/python/tests/test_r5_unbuilt_doors.py -q;
    commit=c34c9bf3e55a8425d3f251c3ad06c33bc9755a22]
  - the package coordination family exposes future spaces, races, timers,
    channels, parallel maps, and quiet-gap watch timeouts [tested:
    test_the_coordination_family_is_python_shaped; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - unary plus preserves atom identity while unary minus keeps its staged
    subtraction meaning [tested: test_unary_plus_is_atom_identity;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import builtins
import math
import operator
from dataclasses import dataclass
from typing import Any

import pytest

import metta as pymetta
from metta import Expression, Grounded, S, V, equation
from metta.atoms import order_key


def test_solve_retires_the_five_relational_let_workarounds(metta):
    """R5.1: five corpus sites no longer hand-build relational ``let``."""
    assert metta.solve(4, V.x - 1).x == 5
    assert metta.solve(12, V.y * 4).y == 3


def test_solve_refuses_an_anonymous_only_subject(metta):
    """Anonymous variables stay fresh and never become result columns."""
    with pytest.raises(ValueError, match="at least one variable"):
        metta.solve(4, V._ - 1)


def test_typed_and_arrow_retire_49_raw_type_symbols():
    """R5.2: 33 arrows and 16 undefined symbols use the shared type table."""
    assert pymetta.arrow(int, int) == S["->"](S.Number, S.Number)
    assert pymetta.arrow(Any, str) == S["->"](S["%Undefined%"], S.String)
    assert pymetta.typed(S.f, pymetta.arrow(int, int)) == S[":"](
        S.f, S["->"](S.Number, S.Number)
    )


def test_keyword_builders_retire_53_raw_if_mentions():
    """R5.3: quoted/stored terms use Python-safe keyword builders."""
    assert pymetta.if_(V.ok, S.yes, S.no) == S["if"](V.ok, S.yes, S.no)
    assert pymetta.not_(V.ok) == S["not"](V.ok)
    assert pymetta.and_(V.a, V.b) == S["and"](V.a, V.b)
    assert pymetta.or_(V.a, V.b) == S["or"](V.a, V.b)
    assert pymetta.in_(V.x, S.items) == S["in"](V.x, S.items)


def test_take_peek_and_watch_retire_the_thread_linda_fn_strings(metta):
    """R5.4: thread_linda's handle verbs preserve data and expose bindings."""
    with metta._new_space() as mailbox:
        first = S.message(1)
        mailbox.add(first)
        assert mailbox.peek(S.message(V.n), deadline=0.1) == first
        assert first in mailbox
        assert mailbox.take(S.message(V.n), deadline=0.1) == first
        assert first not in mailbox
        with pytest.raises(TimeoutError):
            mailbox.take(S.message(V.n), deadline=0.01)

        changes = mailbox.watch(S.message(V.n))
        mailbox.add(S.message(7))
        event = next(changes)
        assert event.n == 7
        changes.close()


def test_watch_close_before_first_event_cancels_its_eager_subscription(metta):
    """Closing a never-started watch releases its standing query."""
    reflection = metta._at("&petta")
    descriptor = S.subscription(S[metta.name], S.r5_watch(V.n), S["add"])
    changes = metta.watch(S.r5_watch(V.n))
    assert len(reflection.match(descriptor)) == 1
    changes.close()
    assert not reflection.match(descriptor)


def test_the_coordination_family_is_python_shaped():
    """Package coordination rides lib_thread while retaining space identity."""
    from metta import Timeout, channel, every, par_map, race, spawn

    m = pymetta.engine().self

    @m.define(name="coord-inc")
    def coord_inc(value):
        return value + 1

    future = spawn(S.coord_inc(41))
    assert isinstance(future, pymetta.Space)
    assert list(future.wait()) == [42]
    assert list(future) == [42]
    assert future.settled()

    assert tuple(par_map(S.coord_inc, [1, 2, 3])) == (2, 3, 4)
    assert race(S.coord_inc(1), S.coord_inc(2)) in {2, 3}

    timer = every(0.01, S.coord_inc(9))
    arrivals = iter(timer)
    assert next(arrivals) == Grounded(10)
    assert timer.cancel() is True
    arrivals.close()

    mailbox = channel(max=1)
    assert mailbox.send(S.job(7)) is True
    assert mailbox.recv(deadline=0.1) == S.job(7)
    assert mailbox.try_recv() is None
    with pytest.raises(Timeout):
        mailbox.recv(deadline=0.01)
    mailbox.close()

    quiet = m._new_space()
    changes = quiet.watch(S.never(V.value), deadline=0.01)
    with pytest.raises(Timeout):
        next(changes)
    quiet.drop()

    assert issubclass(Timeout, TimeoutError)


def test_unary_plus_is_atom_identity():
    """Unary plus has Python's identity meaning and constructs no term."""
    assert +V.number is V.number
    assert +S.value is S.value
    assert -V.number == S["-"](0, V.number)


def test_define_absorbs_class_declaration_and_frees_space_type(metta):
    """R5.5: one decorator replaces the second spelling under appendix 8."""
    import metta.ops as op_module

    @metta.define
    @dataclass
    class R5Point:
        x: int

    point = R5Point(3)
    assert metta.type(point) == S.R5Point
    assert "record" not in pymetta.__all__
    assert not hasattr(op_module, "record")


def test_state_retires_three_state_function_strings(metta):
    """R5.6: new/get/change state compose through one typed Python handle."""
    state = pymetta.State[int](5, space=metta)
    assert state.value == 5
    state.value = 8
    assert state.value == 8
    assert metta.type(state) == S.StateMonad(S.Number)


MATH_MENTIONS = (
    (math.pow, "pow-math"),
    (math.sqrt, "sqrt-math"),
    (math.fabs, "abs-math"),
    (math.log, "log-math"),
    (math.trunc, "trunc-math"),
    (math.ceil, "ceil-math"),
    (math.floor, "floor-math"),
    (builtins.round, "round-math"),
    (math.sin, "sin-math"),
    (math.asin, "asin-math"),
    (math.cos, "cos-math"),
    (math.acos, "acos-math"),
    (math.tan, "tan-math"),
    (math.atan, "atan-math"),
)


@pytest.mark.parametrize(("callable_value", "head"), MATH_MENTIONS)
def test_callable_mentions_share_operator_and_fourteen_math_names(
    metta, callable_value, head
):
    """R5.7: operator.add and the builtin-types math family become mentions."""
    assert pymetta.wire.encode(operator.add) == S["+"]
    assert pymetta.wire.encode(callable_value) == S[head]

    @metta.define(name="r5-math-sqrt")
    def r5_math_sqrt(x):
        return math.sqrt(x)

    assert r5_math_sqrt.body == S["sqrt-math"](V.x)
    assert r5_math_sqrt(9) == [3.0]


def test_callable_mentions_require_identity_even_when_equality_is_spoofed():
    """A user callable equal to a standard one remains a grounded value."""
    class AddSpoof:
        def __call__(self, left, right):
            return left + right

        def __hash__(self):
            return hash(operator.add)

        def __eq__(self, other):
            return other is operator.add

    spoof = AddSpoof()
    assert spoof == operator.add
    encoded = pymetta.wire.encode(spoof)
    assert isinstance(encoded, pymetta.Grounded)
    assert encoded.value is spoof


def test_compiled_callable_mentions_preserve_python_call_semantics(metta):
    """Adapters preserve argument order, optional forms, and result kinds."""
    @metta.define(name="r5-log-base")
    def log_base(value, base):
        return math.log(value, base)

    @metta.define(name="r5-log-natural")
    def log_natural(value):
        return math.log(value)

    @metta.define(name="r5-fabs")
    def fabs(value):
        return math.fabs(value)

    @metta.define(name="r5-round")
    def round_builtin(value):
        return builtins.round(value)

    @metta.define(name="r5-true-divide")
    def true_divide(left, right):
        return operator.truediv(left, right)

    assert log_base.body == S["log-math"](V.base, V.value)
    assert log_base(100, 10) == [2.0]
    assert log_natural(math.e**2)[0].value == pytest.approx(2.0)
    assert fabs(2) == [2.0]
    assert type(fabs(2)[0].value) is float
    assert round_builtin(2.5) == [2]
    assert true_divide(6, 2) == [3.0]
    assert type(true_divide(6, 2)[0].value) is float


def test_plain_sorted_uses_the_engines_elementwise_order():
    """R5.8: plain sorted fixes the unequal-length divergence in order_key."""
    short = Expression(S.z)
    long = Expression(S.a, S.a)
    assert order_key(long) < order_key(short)
    assert sorted([short, long]) == [long, short]
    assert sorted([Grounded("a"), Grounded(1)]) == [Grounded(1), Grounded("a")]


def test_set_is_the_unique_image_of_solve_answers(metta):
    """R5.9: set() deduplicates the answer rows without an X-atom helper."""
    answers = metta.solve(5, S.superpose((V.x, V.x)))
    assert len(answers) == 2
    assert len(set(answers)) == 1


def test_fn_strips_one_bang_only_when_the_exact_name_is_absent(metta):
    """R5.10: attribute access loses bang strings; brackets stay exact.

    A keyword like import cannot be an attribute at all, and the factories'
    total map turns import_ into import-, so its bang form is the exact
    bracket spelling.
    """
    assert metta.fn.pragma.__name__ == "pragma!"
    assert metta.fn["import!"].__name__ == "import!"
    assert metta.fn.add_translator_rule.__name__ == "add-translator-rule!"
    assert metta.fn.change_state.__name__ == "change-state!"


def test_rules_lower_emits_queryable_declaration_and_registers_the_head(metta):
    """R5.11: six translator-registration strings collapse into lower()."""

    @pymetta.rules
    def r5_lowering(x):
        yield equation(S["r5-lower"](x)).to(S.noeval(S.r5_lowered(x)))

    declaration = r5_lowering.lower(S.topdown, requires=S.mork, space=metta)
    assert declaration == S.lowering(
        S["r5-lower"], S.topdown, S.requires(S.mork)
    )
    assert declaration in metta._at("&petta")
    assert metta.eval(S["r5-lower"](3)) == [S.r5_lowered(3)]


def test_rules_lower_refuses_an_empty_rule_set_before_mutating(metta):
    """A lowering needs a rule head to declare and register."""
    @pymetta.rules
    def empty_rules():
        if False:
            yield equation(S.unreachable).to(S.unreachable)

    with metta._new_space() as target:
        before = target.digest()
        with pytest.raises(ValueError, match="empty rule set"):
            empty_rules.lower(S.topdown, requires=S.mork, space=target)
        assert target.digest() == before


def test_transaction_term_uses_empty_answer_rollback_law(metta):
    """R5.12: term transactions complement callable exception rollback."""
    with metta._new_space() as space:
        fact = S.r5_written(1)
        term = S.progn(S["add-atom"](S[space.name], fact), S.empty())
        assert space.transaction(term) == []
        assert fact not in space

        with pytest.raises(RuntimeError):
            space.transaction(lambda: (space.add(fact), (_ for _ in ()).throw(RuntimeError("r5"))))
        assert fact not in space


def test_eval_keeps_unreduced_guarded_head_and_status(metta):
    """R5.13: P14.31 no longer conflates no matching clause with empty."""

    @metta.define(name="r5-pick")
    def r5_pick(_n=1):
        return 7

    call = S["r5-pick"](2)
    assert metta.eval(call) == [call]
    assert metta.eval_status(call) == [("not-reducible", call)]

    policy = S["dispatch-policy"](S["r5-pick"], S.NoMatchEnum, S.NoMatchFail)
    catalog = metta._at("&petta")
    catalog.add(policy)
    try:
        assert metta.eval(call) == []
    finally:
        catalog.remove(policy)
