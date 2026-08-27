"""Purpose: pin the flat callable door's typed dispatch against the eval
door. A defined function called flat, `f(x)`, once took a direct compiled
goal that skipped call-site typing entirely: with an arrow declared, the
eval door refused a wrong-typed argument while the flat door echoed the raw
clause, and a user typing rule's refusal never ran (the two P14.9 residue
rows retired 2026-08-25). metta_typed_dispatch_applies/2, the engine-owned
ownership door (metta/types.pl), closes the fast path exactly where the
translator's own call-site chains are nonempty or a translator rule owns
the head; the shim only asks it, so shim.plt's engine-free suites cannot
reach the gate: its first cut read a module-private registry and crashed
every undeclared flat call in the packaged boot with an existence error no
Prolog suite saw.
Guarantees:
  - an undeclared defined function still answers through the flat door
    [tested: test_an_undeclared_function_answers_through_the_flat_door]
  - a declared arrow refuses a wrong-typed argument identically through
    the flat and the eval door
    [tested: test_a_declared_arrow_refuses_identically_through_both_doors]
  - a user typing rule's refusal reaches the flat door and its removal
    restores the acceptance
    [tested: test_a_typing_rule_refuses_a_flat_python_call]
  - wherever the direct goal is eligible, its answers equal the general
    path's, over every head class and plain-argument class the door admits
    [tested: test_the_direct_goal_path_and_the_general_path_agree_on_every_corpus_call]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import MeTTa, S, V, arrow, fn, typed


@pytest.fixture()
def m():
    """A fresh space, not `&self`: these tests declare types, install
    rules, and import libraries, and `&self` is shared engine-wide, so
    dirtying it would leak into every later file in the same worker.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    return MeTTa().space()


def test_an_undeclared_function_answers_through_the_flat_door(m):
    """The gate must fail for an undeclared head, and fail QUIETLY: its
    first cut raised `Unknown procedure: typing_rule_entry/7` on every such
    call, breaking 177 of 218 twins while shim.plt stayed green, because
    the gate is the one shim predicate that reads engine state
    [reproduced 2026-08-25, tools/twin_coverage.py --observe rounds 4-10].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    @m.define
    def plain(x):
        """(= (plain $x) (* $x 2))."""
        return x * 2

    assert plain(21) == [42]


def test_a_declared_arrow_refuses_identically_through_both_doors(m):
    """(: gate (-> A A)) beside (: b1 B): the flat call must answer the
    BadArgType the eval door answers, not the raw clause's echo.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m += typed(S.gate, arrow(S.A, S.A))
    m += typed(S.a1, S.A)
    m += typed(S.b1, S.B)

    @m.define
    def gate(x):
        """(= (gate $x) $x)."""
        return x

    assert gate(S.a1) == [S.a1]
    flat = gate(S.b1)
    assert flat == m.eval(S.gate(S.b1))
    assert flat == [S.Error(S.gate(S.b1), S.BadArgType(1, S.A, S.B))]


def test_a_typing_rule_refuses_a_flat_python_call(m):
    """The P14.9 measurement, rerun through the door it named: once the
    rule installs, the flat call answers the TypingRuleRefusal the eval
    door answers, and removing the rule restores the acceptance.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m += typed(S.demo, arrow(S.DemoPayload, S.Atom))

    @m.define
    def demo(value):
        """(= (demo $value) (seen $value))."""
        return S.seen(value)

    payload = S.mystery
    assert demo(payload) == [S.seen(payload)]

    m.fn.add_typing_rule(S.deny_mystery, S.ordinary, S["%Undefined%"],
                         S.DemoPayload, S.refuse(S.not_a_payload))
    flat = demo(payload)
    assert flat == m.eval(S.demo(payload))
    refusal = S.BadArgType(1, S.DemoPayload, S["%Undefined%"],
                           S.TypingRuleRefusal(S.deny_mystery,
                                               S.not_a_payload))
    assert flat == [S.Error(S.demo(payload), refusal)]

    m.fn.remove_typing_rule(S.deny_mystery)
    assert demo(payload) == [S.seen(payload)]


def test_the_direct_goal_path_and_the_general_path_agree_on_every_corpus_call(m):
    """The gate's soundness condition, run as a differential over the
    door's whole eligibility space instead of harvested call sites: every
    head class (undeclared, declared right- and wrong-typed, rule-refused,
    wildcard-covered, two-argument) crossed with every plain-argument
    class the door admits (int, float, str, bool, plain symbol, declared
    symbol). The general path is reached by shape: `collapse` makes the
    call a nested operand, which metta_py_plain_args disqualifies, so the
    same call compiles through the translator; the flat spelling is
    whatever the gate decides. Wherever the two disagree, the fast path
    answered something translation would not, which is the exact defect
    class P14.32 named.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m += typed(S.checked, arrow(S.A, S.A))
    m += typed(S.a1, S.A)
    m += typed(S.b1, S.B)
    m += typed(S.ruled, arrow(S.RulePayload, S.Atom))
    m.fn.add_typing_rule(S.deny_plain, S.ordinary, S["%Undefined%"],
                         S.RulePayload, S.refuse(S.not_a_rule_payload))

    @m.define
    def free(x):
        """(= (free $x) (echo $x))."""
        return S.echo(x)

    @m.define
    def checked(x):
        """(= (checked $x) $x)."""
        return x

    @m.define
    def ruled(x):
        """(= (ruled $x) (held $x))."""
        return S.held(x)

    @m.define
    def pair(x, y):
        """(= (pair $x $y) (both $x $y))."""
        return S.both(x, y)

    arguments = [7, 2.5, "text", True, S.plain, S.a1, S.b1]
    calls = [S.free(a) for a in arguments]
    calls += [S.checked(a) for a in arguments]
    calls += [S.ruled(a) for a in arguments]
    calls += [S.pair(a, 7) for a in arguments]
    for call in calls:
        flat = m.eval(call)
        general = m.eval(fn.collapse(call))
        assert len(general) == 1, (call, general)
        assert flat == list(general[0]), (call, flat, general)

    # A wildcard declaration types EVERY head, so it must close the fast
    # path for the previously undeclared function too, in a fresh space
    # where nothing else is declared.
    fresh = MeTTa().space()
    fresh += typed(V.any, S.Wide)

    @fresh.define
    def open_head(x):
        """(= (open-head $x) (kept $x))."""
        return S.kept(x)

    for a in [7, "text", S.plain]:
        call = S.open_head(a)
        flat = fresh.eval(call)
        general = fresh.eval(fn.collapse(call))
        assert len(general) == 1, (call, general)
        assert flat == list(general[0]), (call, flat, general)


def test_a_rule_owned_head_obeys_its_orientation_through_the_flat_door(m):
    """A translator rule's orientation gate (a bidirectional rewrite fires
    only when it lowers the form's cost) lives in translation, so a
    rule-owned head must decline the direct goal: the derived inverse of a
    bidirectional rule, called raw, rewrote `(twin 1 1)` UP in cost while
    every translated door blocked it [measured 2026-08-25,
    examples/translation/translatorrule_direction.metta].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    from typing import Any

    from metta import Atom, Expression, equation

    m += typed(S.unpack, arrow(Atom, Any))

    @m.rules
    def unwrapping(x):
        """(= (unpack (wrap (box $x))) (noeval (twin $x $x)))."""
        yield equation(S.unpack(S.wrap(S.box(x)))).to(S.noeval(S.twin(x, x)))

    m.fn.add_translator_rule(S.unpack, Expression((S.direction(S.bidirectional),)))

    small, small_unpack = S.twin(1, 1), S.unpack(S.wrap(S.box(1)))
    assert m.eval(small) == [small]              # three nodes stay three
    assert m.eval(small_unpack) == [small]       # four nodes lower to three
