"""Purpose: the @define path: write Python, get PeTTa. For whoever is fluent
in Python rather than s-expressions, language models included; the compiled
subset keeps a callable Python twin so both sides stay checkable.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

from petta import CompileError, MeTTa, S

m = MeTTa().fresh_space()


@m.define
def fact(n):
    if n == 0:
        return 1
    return n * fact(n - 1)


check("equations run", m.run("!(fact 6)"), [[720]])
check("the Python twin agrees", fact.py(6), 720)
check("calling the name builds the term", str(fact(6)), "(fact 6)")


@m.define
def moves(pos):
    yield pos - 1          # a generator is nondeterminism: one answer per yield
    yield pos + 1


check("yields superpose", m.run("!(collapse (moves 10))"), [[m.parse("(9 11)")]])


m.add(S.parent(S.Tom, S.Bob), S.parent(S.Bob, S.Ann))


@m.define
def grandchild(gp):
    return match(parent(gp, mid), match(parent(mid, gc), gc))  # noqa: F821


check("match in the body", m.run("!(grandchild Tom)"), [[S.Ann]])

# Refusals teach the subset: construct, line, and what to write instead.
try:
    @m.define
    def looped(n):
        while n > 0:
            n = n - 1
        return n
except CompileError as e:
    check("refusal names the fix", "recursion" in str(e) and "line" in str(e))
done("python_definitions")
