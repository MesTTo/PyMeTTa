"""Purpose: the @define path: write Python, get MeTTa. For whoever is fluent
in Python rather than s-expressions, language models included; the compiled
subset keeps a callable Python twin so both sides stay checkable.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from dataclasses import dataclass

from _common import check, done

from metta import MeTTa, S, equation, rules
from metta._errors.errors import CompileError

m = MeTTa().space()


@m.define
def fact(n):
    if n == 0:
        return 1
    return n * fact(n - 1)


check("equations run", m.run("!(fact 6)"), [[720]])
check("the Python twin agrees", fact.py(6), 720)
check("calling the name evaluates", fact(6), [720])
check("the S door builds the term", str(S.fact(6)), "(fact 6)")


@m.define
def twice(value):
    return value + value


@rules
def arithmetic(value):
    yield equation(S.via_rule(value)).to(twice(value))


m.add(arithmetic)
check("rules are ordinary atoms", m.eval(S.via_rule(6)), [12])


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


@dataclass
class OpenBox:
    """A class whose fields and methods are intentionally callable in MeTTa."""

    value: int

    def reveal(self) -> int:
        """Return the value exposed to MeTTa."""
        return self.value


@dataclass
class OpaqueBox:
    """A data type whose host capabilities must stay on the Python side."""

    value: int

    def reveal(self) -> int:
        """Return the value only to Python callers."""
        return self.value


m.define(OpenBox)
m.define(OpaqueBox, accessors=False, methods=False)
stored = {str(atom) for atom in m.atoms()}
builtins = set(m.builtins())
check(
    "default class exposure installs a field accessor",
    any("OpenBox-value" in atom for atom in stored),
)
check("default class exposure installs a method", "OpenBox-reveal" in builtins)
check(
    "accessors=False keeps the field private",
    all("OpaqueBox-value" not in atom for atom in stored),
)
check("methods=False keeps the method private", "OpaqueBox-reveal" not in builtins)
done("python_definitions")
