"""Purpose: examples/ch17-concurrency-and-the-loop/12-class_prototypes.metta in Python.

A class that inherits `Space` is a prototype: each instance owns a space
whose facts are its fields and whose equations are its private rules, a
method reads the instance through the receiver it is handed, and a subclass
shares the class's equations through its space's reference. The example
writes those rows by hand; this twin declares the classes and proves the
same claims.
"""

from dataclasses import dataclass

from metta import S, Space, Symbol, V, convert, equation


def twin(m):
    """Declare the prototype classes and prove the example's six claims."""
    @m.define
    @dataclass
    class Agent(Space):
        mood: Symbol

        def decide(self):
            return S.act_on(self.mood)

    @m.define
    @dataclass
    class Scout(Agent):
        def decide(self):
            return S.scouting(self.mood)

    calm, alert = Agent(S.calm), Agent(S.alert)
    # !(test (decide &calm) (act-on calm))
    assert calm.decide() == S.act_on(S.calm)
    # !(test (decide &alert) (act-on alert))
    assert alert.decide() == S.act_on(S.alert)
    # A rule private to one agent: added to its own space, run there through evalc.
    calm += S.internal(S.private_rule)
    calm += equation(S.private_rule(V.agent)).to(S.secret(S.Agent_mood(V.agent)))
    receiver = convert.project(calm).atom
    # !(test (let (Agent $space) &calm (evalc (private-rule &calm) $space)) (secret calm))
    assert calm.fn.private_rule(calm).one() == S.secret(S.calm)
    # !(test (== (private-rule &calm) (quote (private-rule &calm))) True)
    assert m.eval(S.private_rule(receiver)) == [S.private_rule(receiver)]
    # !(test (decide &scout) (scouting curious))
    assert Scout(S.curious).decide() == S.scouting(S.curious)


#: The twin declares its classes, whose grains, accessors, method equations,
#: dispatch rows, call contracts and Python proxies the declaration derives,
#: and then proves the example's claims through them; the native example
#: writes only the rows its claims read. The difference is that declaration
#: and crossing work, the OVERRUN declared below.
#: [measured: 8621275 twin and 213366 native inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure
#: examples/ch17-concurrency-and-the-loop/12-class_prototypes.metta; fixture=min of three
#: serial fresh processes in a provisioned battery worktree with the .qlf set
#: warm; commit=WORKTREE].
BUDGET = 8621275
OVERRUN = 8407909

#: DIVERGED 2026-09-18, the example holds 2 atoms the twin does not (2 :) and
#: the twin holds 55 atoms the example does not (53 :, 2 @doc): The twin's
#: @m.define derives the class's arrows, application and binding contracts and
#: documentation rows into the class space beside the equations the example
#: writes by hand, so the referenced content differs by exactly those derived
#: rows [measured 2026-09-18: the two stored-atom surpluses, one fresh process
#: per side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
DIVERGENCE = "a3e79abae0b5d5ca62ccdbcfd75fc630b20c7f355fa8cd3055c82e42208ee70a"
