"""The Python twin of examples/types/builin_types.metta: the library's own types.

Thirty-six declarations imported from `lib_builtin_types` and read back with
`get-type`. There is nothing to define here, only to ask, so every form is a
term: `S["get-type"]` applied to the engine name whose type is in question, and
the answer compared against the arrow the library declares.

The arrow itself is an ordinary expression, `S["->"](S.Number, S.Number,
S.Number)`, and a type VARIABLE in one is an ordinary variable, `V.a`, which is
what makes `(-> $a $a Bool)` say that `==` compares two things of one type.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 142406

#: The arrows this file asks about, named once each because most of them
#: repeat: MeTTa's numeric surface is one shape said many times.
BINARY_NUMBER = S["->"](S.Number, S.Number, S.Number)
UNARY_NUMBER = S["->"](S.Number, S.Number)
COMPARISON = S["->"](S.Number, S.Number, S.Bool)
PREDICATE = S["->"](S.Number, S.Bool)


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    kind = S["get-type"]

    # !(import! &self (library lib_builtin_types)) answers (())
    yield m.eval(
        S["import!"](S["&self"], expr(S.library, S.lib_builtin_types))
    )

    # Type definitions of arithmetic operators.
    # !(test (get-type +) (-> Number Number Number))
    yield m.eval(S.test(kind(S["+"]), BINARY_NUMBER))
    # !(test (get-type -) (-> Number Number Number))
    yield m.eval(S.test(kind(S["-"]), BINARY_NUMBER))
    # !(test (get-type *) (-> Number Number Number))
    yield m.eval(S.test(kind(S["*"]), BINARY_NUMBER))
    # !(test (get-type /) (-> Number Number Number))
    yield m.eval(S.test(kind(S["/"]), BINARY_NUMBER))
    # !(test (get-type %) (-> Number Number Number))
    yield m.eval(S.test(kind(S["%"]), BINARY_NUMBER))

    # Type definitions of comparison operators.
    # !(test (get-type <) (-> Number Number Bool))
    yield m.eval(S.test(kind(S["<"]), COMPARISON))
    # !(test (get-type <=) (-> Number Number Bool))
    yield m.eval(S.test(kind(S["<="]), COMPARISON))
    # !(test (get-type >) (-> Number Number Bool))
    yield m.eval(S.test(kind(S[">"]), COMPARISON))
    # !(test (get-type >=) (-> Number Number Bool))
    yield m.eval(S.test(kind(S[">="]), COMPARISON))

    # ONE type variable, twice: == compares two things of one type and
    # refuses two of different KNOWN types, which is upstream's own
    # signature for it.
    same_type = S["->"](V.a, V.a, S.Bool)
    # !(test (get-type ==) (-> $a $a Bool))
    yield m.eval(S.test(kind(S["=="]), same_type))
    # !(test (get-type !=) (-> $a $a Bool))
    yield m.eval(S.test(kind(S["!="]), same_type))

    # Type definitions of common mathematical functions.
    # !(test (get-type pow-math) (-> Number Number Number))
    yield m.eval(S.test(kind(S["pow-math"]), BINARY_NUMBER))
    # !(test (get-type sqrt-math) (-> Number Number))
    yield m.eval(S.test(kind(S["sqrt-math"]), UNARY_NUMBER))
    # !(test (get-type abs-math) (-> Number Number))
    yield m.eval(S.test(kind(S["abs-math"]), UNARY_NUMBER))
    # !(test (get-type log-math) (-> Number Number Number))
    yield m.eval(S.test(kind(S["log-math"]), BINARY_NUMBER))
    # !(test (get-type trunc-math) (-> Number Number))
    yield m.eval(S.test(kind(S["trunc-math"]), UNARY_NUMBER))
    # !(test (get-type ceil-math) (-> Number Number))
    yield m.eval(S.test(kind(S["ceil-math"]), UNARY_NUMBER))
    # !(test (get-type floor-math) (-> Number Number))
    yield m.eval(S.test(kind(S["floor-math"]), UNARY_NUMBER))
    # !(test (get-type round-math) (-> Number Number))
    yield m.eval(S.test(kind(S["round-math"]), UNARY_NUMBER))
    # !(test (get-type sin-math) (-> Number Number))
    yield m.eval(S.test(kind(S["sin-math"]), UNARY_NUMBER))
    # !(test (get-type asin-math) (-> Number Number))
    yield m.eval(S.test(kind(S["asin-math"]), UNARY_NUMBER))
    # !(test (get-type cos-math) (-> Number Number))
    yield m.eval(S.test(kind(S["cos-math"]), UNARY_NUMBER))
    # !(test (get-type acos-math) (-> Number Number))
    yield m.eval(S.test(kind(S["acos-math"]), UNARY_NUMBER))
    # !(test (get-type tan-math) (-> Number Number))
    yield m.eval(S.test(kind(S["tan-math"]), UNARY_NUMBER))
    # !(test (get-type atan-math) (-> Number Number))
    yield m.eval(S.test(kind(S["atan-math"]), UNARY_NUMBER))
    # !(test (get-type min-atom) (-> $a Number))
    yield m.eval(
        S.test(kind(S["min-atom"]), S["->"](V.a, S.Number))
    )
    # !(test (get-type max-atom) (-> $a Number))
    yield m.eval(
        S.test(kind(S["max-atom"]), S["->"](V.a, S.Number))
    )
    # !(test (get-type min) (-> Number Number Number))
    yield m.eval(S.test(kind(S["min"]), BINARY_NUMBER))
    # !(test (get-type max) (-> Number Number Number))
    yield m.eval(S.test(kind(S["max"]), BINARY_NUMBER))
    # !(test (get-type exp) (-> Number Number))
    yield m.eval(S.test(kind(S["exp"]), UNARY_NUMBER))

    # Type definitions of isnan and isinf predicates.
    # !(test (get-type isnan-math) (-> Number Bool))
    yield m.eval(S.test(kind(S["isnan-math"]), PREDICATE))
    # !(test (get-type isinf-math) (-> Number Bool))
    yield m.eval(S.test(kind(S["isinf-math"]), PREDICATE))

    # Type definitions of boolean operators.
    boolean = S["->"](S.Bool, S.Bool, S.Bool)
    # !(test (get-type and) (-> Bool Bool Bool))
    yield m.eval(S.test(kind(S["and"]), boolean))
    # !(test (get-type or) (-> Bool Bool Bool))
    yield m.eval(S.test(kind(S["or"]), boolean))
    # !(test (get-type not) (-> Bool Bool))
    yield m.eval(
        S.test(kind(S["not"]), S["->"](S.Bool, S.Bool))
    )
    # !(test (get-type xor) (-> Bool Bool Bool))
    yield m.eval(S.test(kind(S["xor"]), boolean))
