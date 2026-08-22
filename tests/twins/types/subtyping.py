"""The Python twin of examples/types/subtyping.metta: widening, not deciding.

Two things about subtyping surprise people, and both survive translation whole.
The spelling is `:<` and the arrow points from the subtype UP to the supertype,
so `(:< Dog Animal)` reads "Dog is below Animal". And the mechanism is not what
the name suggests: nothing decides whether one type is below another while
checking an argument. Declaring an edge WIDENS a value's type list and the
ordinary check then runs unchanged, which is why `get-type` is where the whole
feature is visible.

Every edge and declaration is an atom, `S[":<"]` and `S[":"]`, because that is
what they are; nothing here is a signature Python could carry. `speak` is a
computation and is written as one, and its body is a MeTTa STRING literal,
which a compiled body spells as a Python string literal.

The `speak` declaration stays an atom because `Animal` is a dynamic MeTTa type,
not a sound Python annotation for the host function. Annotation-derived
declarations now publish before their equations; outputtype.py exercises that
door directly.
"""

from petta import S, V, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9315 to 9506, +191, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 9315 by 47554fc's control/types twin baseline.
BUDGET = 9506


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    below = S[":<"]
    kind = S["get-type"]

    # (: Rex Dog)
    m += S[":"](S.Rex, S.Dog)
    # (:< Dog Animal)
    m += below(S.Dog, S.Animal)

    # One value, two types now, in declaration order and then supertype
    # order.
    # !(test (collapse (get-type Rex)) (Dog Animal))
    yield m.eval(S.test(S.collapse(kind(S.Rex)), (S.Dog, S.Animal)))

    # Which is what makes an argument acceptable: `speak` asks for an Animal
    # and Rex is a Dog, and the check passes because Animal is in Rex's
    # widened list.
    # (: speak (-> Animal String))
    m += S[":"](S.speak, S["->"](S.Animal, S.String))

    @m.define
    def speak(_a):
        # (= (speak $a) "some noise")
        # The parameter is a head variable the body never reads, and the
        # underscore says so to a Python reader.
        return "some noise"

    # !(test (speak Rex) "some noise")
    yield m.eval(S.test(S.speak(S.Rex), val("some noise")))

    # It is transitive, because widening repeats over what the previous
    # round added.
    # (:< Animal LivingThing)
    m += below(S.Animal, S.LivingThing)
    # !(test (collapse (get-type Rex)) (Dog Animal LivingThing))
    yield m.eval(
        S.test(
            S.collapse(kind(S.Rex)),
            (S.Dog, S.Animal, S.LivingThing),
        )
    )

    # Two things are NOT widened, and both are deliberate: a grounded
    # literal's built-in type, and the return type of an application.
    # (:< Number Countable)
    m += below(S.Number, S.Countable)
    # !(test (collapse (get-type 1)) (Number))
    yield m.eval(S.test(S.collapse(kind(1)), (S.Number,)))

    # (: half (-> Number Fraction))
    m += S[":"](S.half, S["->"](S.Number, S.Fraction))
    # (:< Fraction Rational)
    m += below(S.Fraction, S.Rational)
    # !(test (collapse (get-type (half 3))) (Fraction))
    yield m.eval(S.test(S.collapse(kind(S.half(3))), (S.Fraction,)))

    # A diamond answers its join TWICE, and that is not a bug to report:
    # widening checks what is already present against the list as it stood
    # when the round BEGAN.
    # (:< Bat Bird)
    m += below(S.Bat, S.Bird)
    # (:< Bat Mammal)
    m += below(S.Bat, S.Mammal)
    # (:< Bird Animal2)
    m += below(S.Bird, S.Animal2)
    # (:< Mammal Animal2)
    m += below(S.Mammal, S.Animal2)
    # (: Stellaluna Bat)
    m += S[":"](S.Stellaluna, S.Bat)
    # !(test (collapse (get-type Stellaluna)) (Bat Bird Mammal Animal2 Animal2))
    yield m.eval(
        S.test(
            S.collapse(kind(S.Stellaluna)),
            (S.Bat, S.Bird, S.Mammal, S.Animal2, S.Animal2),
        )
    )

    # An edge whose subtype side is a PATTERN contributes an instance,
    # because the lookup is the ordinary two-sided matcher rather than a
    # table of symbols.
    # (:< (Boxed $t) Container)
    m += below(S.Boxed(V.t), S.Container)
    # (: crate (Boxed Apple))
    m += S[":"](S.crate, S.Boxed(S.Apple))
    # !(test (collapse (get-type crate)) ((Boxed Apple) Container))
    yield m.eval(
        S.test(
            S.collapse(kind(S.crate)),
            (S.Boxed(S.Apple), S.Container),
        )
    )
