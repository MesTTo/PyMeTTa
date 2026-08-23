"""Purpose: examples/types/subtyping.metta in Python: `:<` widens, it does not decide.

Two things surprise people about subtyping here. The spelling is `:<` and it
points from the subtype UP, so `(:< Dog Animal)` reads "Dog is below Animal".
And nothing DECIDES whether one type is below another while checking an
argument: declaring an edge WIDENS a value's type list, and the ordinary check
then runs unchanged against the wider list. `get-type` is where the whole
feature is visible, which is why every claim here reads it, and reads the whole
answer set rather than the accessor's first type.

`speak` asks for an Animal, and Python's own class is how an annotation names
that type: `def speak(a: Animal) -> str` IS `(: speak (-> Animal String))`.
The edge itself still has to be written as an atom, because a Python subclass
declares no `:<` (filed as friction, and it is the natural door).
"""

from petta import S, V, arrow, ground, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1

#: The subtype edge. `:<` is a declaration head like `:` and `->`, and the one
#: of the three with no exported builder, so it takes the quoted-name rung.
BELOW = S[":<"]


class Animal:
    """The MeTTa type `Animal`, as a Python class so an annotation can say it."""


def twin(m):
    """Declare edges, then watch what each value's type list becomes."""
    kind = m.fn.get_type

    m += typed(S.Rex, S.Dog)
    m += BELOW(S.Dog, S.Animal)

    # One value, two types now, in declaration order and then supertype order.
    assert kind(S.Rex) == [S.Dog, S.Animal]

    # Which is what makes the argument acceptable: speak asks for an Animal
    # and Rex is a Dog, and Animal is in Rex's widened list.
    @m.define
    def speak(a: Animal) -> str:  # noqa: ARG001  -- the parameter is what the signature declares; the body answers a constant
        return "some noise"

    assert speak(S.Rex) == [ground("some noise")]

    # Transitive, because widening repeats over what the previous round added.
    m += BELOW(S.Animal, S.LivingThing)
    assert kind(S.Rex) == [S.Dog, S.Animal, S.LivingThing]

    # Two things are NOT widened, both deliberately: a grounded literal's
    # built-in type, and the return type of an application.
    m += BELOW(S.Number, S.Countable)
    assert kind(1) == [S.Number]

    m += typed(S.half, arrow(int, S.Fraction))
    m += BELOW(S.Fraction, S.Rational)
    assert kind(S.half(3)) == [S.Fraction]

    # A diamond answers its join TWICE, and that is not a bug to report:
    # widening checks against the list as it stood when the round BEGAN, so
    # both parents reach the join in the same round and both append it.
    m += BELOW(S.Bat, S.Bird)
    m += BELOW(S.Bat, S.Mammal)
    m += BELOW(S.Bird, S.Animal2)
    m += BELOW(S.Mammal, S.Animal2)
    m += typed(S.Stellaluna, S.Bat)
    assert kind(S.Stellaluna) == [
        S.Bat, S.Bird, S.Mammal, S.Animal2, S.Animal2,
    ]

    # An edge whose subtype side is a PATTERN contributes an instance, because
    # the lookup is the ordinary two-sided matcher, not a table of symbols.
    m += BELOW(S.Boxed(V.t), S.Container)
    m += typed(S.crate, S.Boxed(S.Apple))
    assert kind(S.crate) == [S.Boxed(S.Apple), S.Container]
