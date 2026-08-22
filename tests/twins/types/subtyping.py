"""examples/types/subtyping.metta in Python: `:<` widens, it does not decide.

Two things surprise people about subtyping here. The spelling is `:<` and it
points from the subtype UP, so `(:< Dog Animal)` reads "Dog is below Animal".
And nothing DECIDES whether one type is below another while checking an
argument: declaring an edge WIDENS a value's type list, and the ordinary check
then runs unchanged against the wider list. `get-type` is where the whole
feature is visible, which is why every claim here reads it.

`speak` asks for an Animal, and Python's own class is how an annotation names
that type: `def speak(a: Animal) -> str` IS `(: speak (-> Animal String))`.
The edge itself still has to be written as an atom, because a Python subclass
declares no `:<` (filed as friction, and it is the natural door).
"""

from petta import S, V, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9506 to 5074, -4432 (-46.62%), by the twin-shape
#: rewrite: seven `test`-plus-`collapse` wrappers left the engine for
#: `assert` over `.all()`, and `speak`'s signature is an annotation rather
#: than a written declaration atom. Against the example's 19567 the ratio is
#: 0.2593 [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/types/subtyping.metta`]. Prior: RE-PINNED at 9506 by P14.8's
#: m.eval fuel-scope alignment.
BUDGET = 5074


class Animal:
    """The MeTTa type `Animal`, as a Python class so an annotation can say it."""


def twin(m):
    """Declare edges, then watch what each value's type list becomes."""
    typed, below, arrow = S[":"], S[":<"], S["->"]
    kind = m.fn("get-type")

    m += typed(S.Rex, S.Dog)
    m += below(S.Dog, S.Animal)

    # One value, two types now, in declaration order and then supertype order.
    assert kind.all(S.Rex) == [S.Dog, S.Animal]

    # Which is what makes the argument acceptable: speak asks for an Animal
    # and Rex is a Dog, and Animal is in Rex's widened list.
    @m.define
    def speak(a: Animal) -> str:  # noqa: ARG001  -- the parameter is what the signature declares; the body answers a constant
        return "some noise"

    assert speak(S.Rex) == [val("some noise")]

    # Transitive, because widening repeats over what the previous round added.
    m += below(S.Animal, S.LivingThing)
    assert kind.all(S.Rex) == [S.Dog, S.Animal, S.LivingThing]

    # Two things are NOT widened, both deliberately: a grounded literal's
    # built-in type, and the return type of an application.
    m += below(S.Number, S.Countable)
    assert kind.all(1) == [S.Number]

    m += typed(S.half, arrow(S.Number, S.Fraction))
    m += below(S.Fraction, S.Rational)
    assert kind.all(S.half(3)) == [S.Fraction]

    # A diamond answers its join TWICE, and that is not a bug to report:
    # widening checks against the list as it stood when the round BEGAN, so
    # both parents reach the join in the same round and both append it.
    m += below(S.Bat, S.Bird)
    m += below(S.Bat, S.Mammal)
    m += below(S.Bird, S.Animal2)
    m += below(S.Mammal, S.Animal2)
    m += typed(S.Stellaluna, S.Bat)
    assert kind.all(S.Stellaluna) == [S.Bat, S.Bird, S.Mammal, S.Animal2, S.Animal2]

    # An edge whose subtype side is a PATTERN contributes an instance, because
    # the lookup is the ordinary two-sided matcher, not a table of symbols.
    m += below(S.Boxed(V.t), S.Container)
    m += typed(S.crate, S.Boxed(S.Apple))
    assert kind.all(S.crate) == [S.Boxed(S.Apple), S.Container]
