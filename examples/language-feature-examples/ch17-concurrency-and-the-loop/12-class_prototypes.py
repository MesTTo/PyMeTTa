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
#: warm; commit=a8cfae1f5c0be628bc40eb7c18b07749d995e9a0].
#: RE-PINNED 2026-09-18, 8621275 to 8605993 (-15282), the branch's landings
#: since the 09-10 pins, re-taken on the tip f06186a96: the compiled call law
#: (e59104ace: an Atom argument enters as written, a Python object crosses as a
#: value, a positional call of a bound callee is the plain application and a
#: compiled lambda is bare where it is applied), the one codec at the grounded
#: call (fd0af38f7, whose read of a call site's written keyword tail costs
#: about six inferences per translated site, read once since 7cc8fb863), the
#: runnable cache's dependency index written by the producer (a9e2c06d3, which
#: takes back the walk of the generated code 5416e741d charged at every miss),
#: the host patches of 09-17 and the class units of 09-13 to 09-16 the ladder
#: in docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-PINNED 2026-09-18, 8605993 to 8606342 (+349), 49478d67a landed the
#: polynomial carrier, whose preset row and variable claim every catalog scan
#: reads, the product carriers and the guard read in the fixpoint door, and the
#: binding's five-element rule read: the examples that scan the catalog moved
#: with their twins (restricted_spaces +522, the three pln twins +63 each, the
#: two tabling twins +20 and +10, reflect_lib +6) and the twins that cross the
#: seat's declaration and query paths moved with their examples unmoved (the
#: class twins between -4212 and +2841, the reference twins +208 and +317, the
#: tagged fixpoint twin +610, the documentation twins -22 and -50, types_nondet
#: +5) [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 8606342
OVERRUN = 8407909

#: DIVERGED 2026-09-18, the example holds 2 atoms the twin does not (2 :) and
#: the twin holds 55 atoms the example does not (53 :, 2 @doc): The twin's
#: @m.define derives the class's arrows, application and binding contracts and
#: documentation rows into the class space beside the equations the example
#: writes by hand, so the referenced content differs by exactly those derived
#: rows [measured 2026-09-18: the two stored-atom surpluses, one fresh process
#: per side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=a8cfae1f5c0be628bc40eb7c18b07749d995e9a0].
DIVERGENCE = "a3e79abae0b5d5ca62ccdbcfd75fc630b20c7f355fa8cd3055c82e42208ee70a"
