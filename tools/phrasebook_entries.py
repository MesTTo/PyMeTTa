"""Purpose: one row per MeTTa standard-library name: what the MeTTa form is,
what you write in Python instead, and which bucket the translation falls in.
`phrasebook.py` runs both sides of every row; this file is only the rows.

The names, their types and their metatypes are LeaTTa's, copied verbatim from
`tests/conformance/stdlib-manifest.json`, whose own derivation field says every
field was measured against LeaTTa's built binary rather than transcribed. The
manifest declares 382 operations over 380 distinct names: `print-alternatives!`
and `_minimal-foldl-atom` are each declared twice, once in the prelude and once
in a built-in module registry, with identical types both times.

Assumes:
  - a row's MeTTa form is a whole program, so `bind!` and `(= ...)` inside one
    are that row's own and cannot reach the row after it
  - `&pb` in a MeTTa form is that row's own space; the runner makes the name
    unique per row before running it here
Guarantees:
  - the `types` of every row equal LeaTTa's declaration for that name, which
    `phrasebook.py --gate` re-checks against the manifest whenever LeaTTa is
    checked out [tested: test_the_phrasebook_covers_every_leatta_name]
  - get-type, class declaration, and state rows use the consolidated R5 Python
    doors [tested: test_the_phrasebook_page_is_up_to_date; commit=c34c9bf3e55a8425d3f251c3ad06c33bc9755a22]
  - the matching, nondeterminism, fold, and state rows execute every public
    algebra-carrier spelling [tested: test_the_phrasebook_page_is_up_to_date;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - the Python-first additions table names the exact speculate and immutable
    world spellings [tested: test_python_first_world_faces_are_in_the_phrasebook;
    commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - strategy rows import lib_strategy only on PeTTa and may name an equivalent
    unary LeaTTa oracle form when the reified PeTTa plan has a different arity
    [tested: python bindings/python/tools/phrasebook.py --gate; commit=0d37dd6b24fe916e44cdbfb4efc6a1d5ffaf74aa]
  - the Python-first additions table documents module-tier operation
    registration [tested: test_python_first_world_faces_are_in_the_phrasebook;
    commit=WORKTREE]
  - the Python-first additions table documents the explicit inline host island
    marker [tested: test_python_first_world_faces_are_in_the_phrasebook;
    commit=WORKTREE]
Decides:
  - a row's bucket is a CLAIM about the translation, not a comment: the lane
    refuses a `dissolves` or `method` row with no spelling and an `absent` row
    that carries one, so the coverage count cannot be talked up
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the corpus contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from dataclasses import dataclass

#: The manifest these rows were taken from.
LEATTA_VERSION = "1.0.9"
LEATTA_COMMIT = "39c7c43"
LEATTA_ENTRY_COUNT = 382

BUCKETS = {
    "dissolves": (
        "Python already has the concept, so there is no metta name at all and the "
        "spelling is Python's own syntax, protocol or standard library"
    ),
    "method": "the concept is MeTTa's own, so it wears a metta name",
    "instruction": (
        "deep control that stays instruction-tier, reached by building the term at "
        "the `S.` door and reducing it"
    ),
    "internal": (
        "LeaTTa's mechanised interpreter, written in MeTTa; PeTTa writes its "
        "interpreter in Prolog, so these names are on neither surface"
    ),
    "absent": "a user-facing operation with no Python spelling today: the residue",
}

SECTIONS = {
    "arith": "Arithmetic",
    "compare": "Comparison and equality",
    "math": "Numeric functions",
    "logic": "Booleans",
    "atoms": "Expression structure",
    "sets": "Set operations",
    "control": "Control flow and nondeterminism",
    "spaces": "Spaces",
    "types": "Types",
    "state": "The state cell",
    "text": "Printing and text",
    "assert": "Testing",
    "doc": "Documentation",
    "modules": "Modules and imports",
    "errors": "Errors",
    "strategies": "Rewriting strategies",
    "matching": "Matching extensions",
    "instructions": "The minimal core",
    "interpreter": "The mechanised interpreter",
}


@dataclass(frozen=True)
class Entry:
    """One stdlib name, said in Python."""

    name: str
    types: tuple[str, ...]
    metatype: str
    section: str
    bucket: str
    note: str
    metta: str | None = None
    python: str | None = None
    differs: str | None = None
    unrun: str | None = None
    ruled: str | None = None
    petta_setup: str | None = None
    oracle_metta: str | None = None
    petta_inferences: int | None = None


@dataclass(frozen=True)
class PublicFace:
    """One Python-first public spelling with no LeaTTa stdlib row."""

    spelling: str
    meaning: str
    example: str


PUBLIC_FACES: tuple[PublicFace, ...] = (
    PublicFace(
        "@metta.op(effect=...)",
        "register a host callable in the lazy default engine with explicit effect metadata",
        "@metta.op(effect=\"pureStructural\")\ndef double(value):\n    return value * 2",
    ),
    PublicFace(
        "py(expr)",
        "mark one compiled-body expression for application-time host execution",
        "@metta.define\ndef status(url):\n    return py(requests.get(url).status_code)",
    ),
    PublicFace(
        "metta.speculate()",
        "scope each default-context execution as a discarded segment",
        "with metta.speculate():\n    metta.run(source)",
    ),
    PublicFace(
        "space.reify()",
        "capture an immutable evaluable world value, distinct from listing atoms",
        "world = space.reify()",
    ),
    PublicFace(
        "world.eval(target)",
        "evaluate without touching the parent and return answers plus a successor world",
        "answers, successor = world.eval(target)",
    ),
    PublicFace(
        "space.commit(world)",
        "land the world's base-relative diff as ordinary post-commit writes and events",
        "space.commit(successor)",
    ),
)


NUMBER2 = "(-> Number Number Number)"
NUMBER1 = "(-> Number Number)"
NUMBERB = "(-> Number Number Bool)"
BOOL2 = "(-> Bool Bool Bool)"
STRATEGY_SETUP = "!(import! (context-space) (library lib_strategy))"
PY_STRATEGY_SETUP = "space += metta.lib.strategy\n"
STRATEGY_INFERENCES = 20_000_000

ENTRIES: list[Entry] = [
    # ---------------------------------------------------------------- arith
    Entry(
        "+", (NUMBER2,), "Grounded", "arith", "dissolves",
        "Python's own operator. On atoms the same operator builds `(+ ...)` instead "
        "of computing, which is how a compiled body reaches the MeTTa function.",
        metta="!(+ 1 2)", python="1 + 2",
    ),
    Entry(
        "-", (NUMBER2,), "Grounded", "arith", "dissolves",
        "Python's own operator.",
        metta="!(- 5 2)", python="5 - 2",
    ),
    Entry(
        "*", (NUMBER2,), "Grounded", "arith", "dissolves",
        "Python's own operator.",
        metta="!(* 3 4)", python="3 * 4",
    ),
    Entry(
        "/", (NUMBER2,), "Grounded", "arith", "dissolves",
        "Python's `/` is true division, and so is PeTTa's. LeaTTa's integer `/` is "
        "EUCLIDEAN by its own ruling, so `(/ 7 2)` is 3 there and 3.5 here; on "
        "floats all three agree.",
        metta="!(/ 7 2)", python="7 / 2",
        differs="LeaTTa answers 3 (Euclidean integer division), PeTTa and Python 3.5",
    ),
    Entry(
        "%", (NUMBER2,), "Grounded", "arith", "dissolves",
        "Python's own operator. Both take the sign of the divisor for a positive "
        "divisor; LeaTTa's is Euclidean, so a NEGATIVE divisor parts them and "
        "`mod-floor` is the name for Python's convention.",
        metta="!(% -7 3)", python="-7 % 3",
    ),
    Entry(
        "div-floor", (NUMBER2,), "Grounded", "arith", "dissolves",
        "Python's `//` IS floored division, so the name has no Python spelling of "
        "its own.",
        metta="!(div-floor -7 2)", python="-7 // 2",
        unrun="PeTTa implements neither the floored nor the truncating division family",
    ),
    Entry(
        "mod-floor", (NUMBER2,), "Grounded", "arith", "dissolves",
        "Python's `%` IS the floored remainder, sign of the divisor.",
        metta="!(mod-floor -7 2)", python="-7 % 2",
        unrun="PeTTa implements neither the floored nor the truncating division family",
    ),
    Entry(
        "div-trunc", (NUMBER2,), "Grounded", "arith", "dissolves",
        "Truncating division is `math.trunc` over the true quotient; Python's `//` "
        "would floor instead, which differs on negatives.",
        metta="!(div-trunc -7 2)",
        python="import math\nmath.trunc(-7 / 2)",
        unrun="PeTTa implements neither the floored nor the truncating division family",
    ),
    Entry(
        "rem-trunc", (NUMBER2,), "Grounded", "arith", "dissolves",
        "`math.fmod` is the truncating remainder, sign of the dividend; it answers a "
        "float, so an integer row wraps it in `int`.",
        metta="!(rem-trunc -7 2)",
        python="import math\nint(math.fmod(-7, 2))",
        unrun="PeTTa implements neither the floored nor the truncating division family",
    ),
    Entry(
        "div-euclid", (NUMBER2,), "Grounded", "arith", "dissolves",
        "Euclidean division has no Python builtin because the remainder is defined "
        "non-negative; the quotient is the floor for a positive divisor and its "
        "negation otherwise.",
        metta="!(div-euclid -7 2)",
        python="a, b = -7, 2\na // b if b > 0 else -(a // -b)",
        unrun="PeTTa implements neither the floored nor the truncating division family",
    ),
    Entry(
        "mod-euclid", (NUMBER2,), "Grounded", "arith", "dissolves",
        "The Euclidean remainder is always non-negative, which is `a % abs(b)`.",
        metta="!(mod-euclid -7 2)",
        python="a, b = -7, 2\na % abs(b)",
        unrun="PeTTa implements neither the floored nor the truncating division family",
    ),
    # -------------------------------------------------------------- compare
    Entry(
        "<", (NUMBERB,), "Grounded", "compare", "dissolves",
        "Python's own operator.", metta="!(< 1 2)", python="1 < 2",
    ),
    Entry(
        "<=", (NUMBERB,), "Grounded", "compare", "dissolves",
        "Python's own operator.", metta="!(<= 2 2)", python="2 <= 2",
    ),
    Entry(
        ">", (NUMBERB,), "Grounded", "compare", "dissolves",
        "Python's own operator.", metta="!(> 2 1)", python="2 > 1",
    ),
    Entry(
        ">=", (NUMBERB,), "Grounded", "compare", "dissolves",
        "Python's own operator.", metta="!(>= 1 2)", python="1 >= 2",
    ),
    Entry(
        "==", ("(-> $t $t Bool)",), "Grounded", "compare", "dissolves",
        "Python's own operator, and atoms compare structurally under it.",
        metta="!(== (f 1) (f 1))", python="S.f(1) == S.f(1)",
    ),
    Entry(
        "=alpha", ("(-> Atom Atom Bool)",), "Grounded", "compare", "method",
        "Equality modulo variable renaming is not a Python concept, so it keeps "
        "MeTTa's noun. `a.alpha_eq(b)` is the method form of the same act.",
        metta="!(=alpha (f $x) (f $y))", python="S.f(V.x).alpha_eq(S.f(V.y))",
    ),
    Entry(
        "noreduce-eq", ("(-> Atom Atom Bool)",), "Symbol", "compare", "dissolves",
        "Comparing two atoms WITHOUT reducing them is what Python's `==` on atoms "
        "already does: building a term never evaluates it.",
        metta="!(noreduce-eq (+ 1 2) (+ 1 2))", python="S['+'](1, 2) == S['+'](1, 2)",
    ),
    # ----------------------------------------------------------------- math
    Entry(
        "abs-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "Python's builtin `abs`.", metta="!(abs-math -3)", python="abs(-3)",
    ),
    Entry(
        "sqrt-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "`math.sqrt`.", metta="!(sqrt-math 4)", python="import math\nmath.sqrt(4)",
    ),
    Entry(
        "pow-math", (NUMBER2,), "Grounded", "math", "dissolves",
        "Python's `**` operator. MeTTa answers a float where Python's integer "
        "power answers an integer, so the row raises a float.",
        metta="!(pow-math 2.0 3)", python="2.0 ** 3",
    ),
    Entry(
        "log-math", (NUMBER2,), "Grounded", "math", "dissolves",
        "`math.log(x, base)`, with the arguments the other way round: MeTTa takes "
        "the base first.",
        metta="!(log-math 2 8)", python="import math\nmath.log(8, 2)",
    ),
    Entry(
        "sin-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "`math.sin`.", metta="!(sin-math 0)", python="import math\nmath.sin(0)",
    ),
    Entry(
        "cos-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "`math.cos`.", metta="!(cos-math 0)", python="import math\nmath.cos(0)",
    ),
    Entry(
        "tan-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "`math.tan`.", metta="!(tan-math 0)", python="import math\nmath.tan(0)",
    ),
    Entry(
        "asin-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "`math.asin`.", metta="!(asin-math 0)", python="import math\nmath.asin(0)",
    ),
    Entry(
        "acos-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "`math.acos`.", metta="!(acos-math 1)", python="import math\nmath.acos(1)",
    ),
    Entry(
        "atan-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "`math.atan`.", metta="!(atan-math 0)", python="import math\nmath.atan(0)",
    ),
    Entry(
        "ceil-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "`math.ceil`, which answers an integer in Python 3 where LeaTTa keeps the "
        "float.",
        metta="!(ceil-math 2.1)", python="import math\nmath.ceil(2.1)",
        differs="LeaTTa answers 3.0 and keeps the float; PeTTa and Python answer 3",
    ),
    Entry(
        "floor-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "`math.floor`, the same integer-against-float difference as `ceil-math`.",
        metta="!(floor-math 2.9)", python="import math\nmath.floor(2.9)",
        differs="LeaTTa answers 2.0 and keeps the float; PeTTa and Python answer 2",
    ),
    Entry(
        "round-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "NOT Python's `round`: `round` breaks a tie to the EVEN neighbour, so "
        "`round(2.5)` is 2 where MeTTa answers 3. Half away from zero is "
        "`math.floor(x + 0.5)` for a positive number.",
        metta="!(round-math 2.5)", python="import math\nmath.floor(2.5 + 0.5)",
        differs="LeaTTa answers 3.0 and keeps the float; PeTTa and Python answer 3",
    ),
    Entry(
        "trunc-math", (NUMBER1,), "Grounded", "math", "dissolves",
        "`math.trunc`, or `int` on a float.",
        metta="!(trunc-math 2.9)", python="import math\nmath.trunc(2.9)",
        differs="LeaTTa answers 2.0 and keeps the float; PeTTa and Python answer 2",
    ),
    Entry(
        "isnan-math", ("(-> Number Bool)",), "Grounded", "math", "dissolves",
        "`math.isnan`.", metta="!(isnan-math 1)", python="import math\nmath.isnan(1)",
    ),
    Entry(
        "isinf-math", ("(-> Number Bool)",), "Grounded", "math", "dissolves",
        "`math.isinf`.", metta="!(isinf-math 1)", python="import math\nmath.isinf(1)",
    ),
    # ---------------------------------------------------------------- logic
    Entry(
        "and", (BOOL2,), "Grounded", "logic", "dissolves",
        "Python's own keyword. On atoms `&` builds the MeTTa `and` instead, because "
        "the keyword cannot be overloaded.",
        metta="!(and True False)", python="True and False",
    ),
    Entry(
        "or", (BOOL2,), "Grounded", "logic", "dissolves",
        "Python's own keyword; `|` is the operator form on atoms.",
        metta="!(or True False)", python="True or False",
    ),
    Entry(
        "not", ("(-> Bool Bool)",), "Grounded", "logic", "dissolves",
        "Python's own keyword; `~` is the operator form on atoms.",
        metta="!(not True)", python="not True",
    ),
    Entry(
        "xor", (BOOL2,), "Grounded", "logic", "dissolves",
        "Python's `^` on booleans.", metta="!(xor True False)", python="True ^ False",
    ),
    # ---------------------------------------------------------------- atoms
    Entry(
        "car-atom", ("(-> Expression %Undefined%)",), "Symbol", "atoms", "dissolves",
        "Indexing. An expression is a sequence in Python, so its head is `e[0]`.",
        metta="!(car-atom (a b c))",
        python="e = metta.Expression(S.a, S.b, S.c)\ne[0]",
    ),
    Entry(
        "cdr-atom", ("(-> Expression Expression)",), "Symbol", "atoms", "dissolves",
        "Slicing. `e[1:]` answers a Python tuple today rather than an Expression, "
        "which prints the same and is the T6 friction section 9e names as this "
        "bucket's one prerequisite.",
        metta="!(cdr-atom (a b c))",
        python="e = metta.Expression(S.a, S.b, S.c)\ne[1:]",
    ),
    Entry(
        "cons-atom", ("(-> Atom Expression Atom)",), "Symbol", "atoms", "dissolves",
        "Construction: call the head, or rebuild from head and tail with `*`.",
        metta="!(cons-atom f (a b))",
        python="tail = (S.a, S.b)\nS.f(*tail)",
    ),
    Entry(
        "decons-atom", ("(-> Expression Atom)",), "Symbol", "atoms", "dissolves",
        "Starred unpacking, which is the same act in one line: `head, *tail = e`.",
        metta="!(decons-atom (f a b))",
        python="e = metta.Expression(S.f, S.a, S.b)\nhead, *tail = e\n(head, tuple(tail))",
    ),
    Entry(
        "size-atom", ("(-> Expression Number)",), "Grounded", "atoms", "dissolves",
        "`len`. Both count CHILDREN, so `(f a b)` is 3 either way.",
        metta="!(size-atom (a b c))",
        python="e = metta.Expression(S.a, S.b, S.c)\nlen(e)",
    ),
    Entry(
        "index-atom", ("(-> Expression Number Atom)",), "Grounded", "atoms", "dissolves",
        "Indexing again, with the index you want.",
        metta="!(index-atom (a b c) 1)",
        python="e = metta.Expression(S.a, S.b, S.c)\ne[1]",
    ),
    Entry(
        "max-atom", ("(-> %Undefined% Number)",), "Grounded", "atoms", "dissolves",
        "Python's builtin `max` over the children.",
        metta="!(max-atom (1 2 3))", python="max([1, 2, 3])",
        differs="LeaTTa answers 3.0 and keeps the float; PeTTa and Python answer 3",
    ),
    Entry(
        "min-atom", ("(-> %Undefined% Number)",), "Grounded", "atoms", "dissolves",
        "Python's builtin `min` over the children.",
        metta="!(min-atom (1 2 3))", python="min([1, 2, 3])",
        differs="LeaTTa answers 1.0 and keeps the float; PeTTa and Python answer 1",
    ),
    Entry(
        "sort-strings", ("(-> Expression Expression)",), "Grounded", "atoms", "dissolves",
        "Python's builtin `sorted`. A tuple goes back in as one expression.",
        metta='!(sort-strings ("b" "a" "c"))',
        python='tuple(sorted(["b", "a", "c"]))',
    ),
    Entry(
        "map-atom",
        ("(-> Expression Variable Atom Expression)", "(-> Expression Expression Expression)"),
        "Symbol", "atoms", "dissolves",
        "A comprehension, or `map`. The variable and the template are the "
        "comprehension's own binder and body.",
        metta="!(map-atom (1 2 3) $x (+ $x 1))",
        python="tuple(x + 1 for x in [1, 2, 3])",
    ),
    Entry(
        "filter-atom",
        ("(-> Expression Variable Atom Expression)", "(-> Expression Expression Expression)"),
        "Symbol", "atoms", "dissolves",
        "A comprehension with an `if`, or `filter`.",
        metta="!(filter-atom (1 2 3) $x (> $x 1))",
        python="tuple(x for x in [1, 2, 3] if x > 1)",
    ),
    Entry(
        "foldl-atom",
        (
            "(-> Expression Atom Variable Variable Atom %Undefined%)",
            "(-> Expression Atom Expression %Undefined%)",
        ),
        "Symbol", "atoms", "dissolves",
        "`functools.reduce` with an initial value is the same finite left fold. "
        "For a change stream, `m.events().fold(..., under=algebra)` makes the "
        "algebra itself the step; `into=State(...)` is the running-gauge form.",
        metta="!(foldl-atom (1 2 3) 0 $a $b (+ $a $b))",
        python=(
            "import functools\n"
            "assert functools.reduce(lambda a, b: a + b, [1, 2, 3], 0) == 6\n"
            "folded = m.events().fold(space=space.name, "
            "pattern=S.fact(V.tag, V.value), under=metta.tropical)\n"
            "space += S.fact(6, S.answer)\n"
            "result = folded.take()\n"
            "folded.cancel()\n"
            "result"
        ),
    ),
    Entry(
        "for-each-in-atom", ("(-> Expression Atom (->))",), "Symbol", "atoms", "dissolves",
        "A `for` statement. It is called for its effect, so the row prints and "
        "answers the unit. Python's `for` has no value at all, and the concept map "
        "says `None` IS the unit, but `metta.ground(None)` renders `<NoneType>` "
        "rather than `()` today, so a row that wants the unit writes it "
        "[measured 2026-08-22].",
        metta="!(for-each-in-atom (1 2) println!)",
        python="for value in [1, 2]:\n    print(value)\nmetta.Expression()",
        differs="PeTTa answers one unit per element where LeaTTa answers one",
    ),
    Entry(
        "atom-subst", ("(-> Atom Variable Atom Atom)",), "Symbol", "atoms", "method",
        "Applying a substitution to a template, which `Atom.map` does over "
        "the whole term. Section 9e wants the bindings object to carry it, "
        "`b.apply(template)`; `metta.Bindings` has no such method yet, so the "
        "walker is the spelling.",
        metta="!(atom-subst a $x (f $x))",
        python="S.f(V.x).map(lambda a: S.a if a == V.x else a)",
        unrun="PeTTa leaves the MeTTa call unreduced",
    ),
    Entry(
        "if-decons-expr",
        ("(-> Expression Variable Variable Atom Atom %Undefined%)",),
        "Symbol", "atoms", "dissolves",
        "Starred unpacking inside an `if`: the empty case is the `else` branch.",
        metta="!(if-decons-expr (a b) $h $t (yes $h $t) no)",
        python=(
            "e = metta.Expression(S.a, S.b)\n"
            "S.yes(e[0], e[1:]) if len(e) else S.no"
        ),
        unrun="PeTTa leaves the call unreduced",
    ),
    # ----------------------------------------------------------------- sets
    Entry(
        "union", ("(-> Atom Atom %Undefined%)",), "Symbol", "sets", "dissolves",
        "Multiset union over nondeterministic answers, which is concatenation: "
        "answers are iterables and `+` joins them.",
        metta="!(union (superpose (a b b)) (superpose (b c)))",
        python="[S.a, S.b, S.b] + [S.b, S.c]",
    ),
    Entry(
        "intersection", ("(-> Atom Atom %Undefined%)",), "Symbol", "sets", "dissolves",
        "`collections.Counter` IS the multiset algebra, and `&` is its intersection.",
        metta="!(intersection (superpose (a b b c)) (superpose (b c c)))",
        python=(
            "from collections import Counter\n"
            "list((Counter([S.a, S.b, S.b, S.c]) & Counter([S.b, S.c, S.c])).elements())"
        ),
    ),
    Entry(
        "subtraction", ("(-> Atom Atom %Undefined%)",), "Symbol", "sets", "dissolves",
        "`Counter` again, with `-`.",
        metta="!(subtraction (superpose (a b b c)) (superpose (b c)))",
        python=(
            "from collections import Counter\n"
            "list((Counter([S.a, S.b, S.b, S.c]) - Counter([S.b, S.c])).elements())"
        ),
    ),
    Entry(
        "unique", ("(-> Atom %Undefined%)",), "Symbol", "sets", "dissolves",
        "`dict.fromkeys` is Python's order-preserving dedupe.",
        metta="!(unique (superpose (a b b c)))",
        python="list(dict.fromkeys([S.a, S.b, S.b, S.c]))",
    ),
    Entry(
        "union-atom", ("(-> Expression Expression Atom)",), "Grounded", "sets", "dissolves",
        "The same act over an expression's children; a tuple goes back in as one "
        "expression.",
        metta="!(union-atom (a b b) (b c))",
        python="tuple([S.a, S.b, S.b] + [S.b, S.c])",
    ),
    Entry(
        "intersection-atom", ("(-> Expression Expression Atom)",), "Grounded", "sets",
        "dissolves", "`Counter` over children, answering an expression.",
        metta="!(intersection-atom (a b b c) (b c c))",
        python=(
            "from collections import Counter\n"
            "tuple((Counter([S.a, S.b, S.b, S.c]) & Counter([S.b, S.c, S.c])).elements())"
        ),
    ),
    Entry(
        "subtraction-atom", ("(-> Expression Expression Atom)",), "Grounded", "sets",
        "dissolves", "`Counter` over children, answering an expression.",
        metta="!(subtraction-atom (a b b c) (b c))",
        python=(
            "from collections import Counter\n"
            "tuple((Counter([S.a, S.b, S.b, S.c]) - Counter([S.b, S.c])).elements())"
        ),
    ),
    Entry(
        "unique-atom", ("(-> Expression Atom)",), "Grounded", "sets", "dissolves",
        "`dict.fromkeys` over children.",
        metta="!(unique-atom (a b b c))",
        python="tuple(dict.fromkeys([S.a, S.b, S.b, S.c]))",
    ),
    # -------------------------------------------------------------- control
    Entry(
        "if", ("(-> Bool Atom Atom $t)",), "Symbol", "control", "dissolves",
        "Python's own `if`, and its conditional expression where a value is wanted. "
        "Both arms stay unevaluated in MeTTa because the parameters are Atom-typed, "
        "which is exactly what Python's own short-circuit does.",
        metta="!(if True a b)", python="S.a if True else S.b",
    ),
    Entry(
        "case", ("(-> Atom Expression %Undefined%)",), "Symbol", "control", "dissolves",
        "Python's `match` statement. A bare variable arm is `case _`.",
        metta="!(case 2 ((1 one) (2 two) ($x other)))",
        python=(
            "value = 2\n"
            "match value:\n"
            "    case 1:\n"
            "        answer = S.one\n"
            "    case 2:\n"
            "        answer = S.two\n"
            "    case _:\n"
            "        answer = S.other\n"
            "answer"
        ),
    ),
    Entry(
        "switch", ("(-> %Undefined% Expression %Undefined%)",), "Symbol", "control",
        "dissolves",
        "Python's `match` statement again. `switch` differs from `case` only in "
        "evaluating its subject first, which a Python expression does anyway.",
        metta="!(switch (+ 1 1) ((1 one) (2 two)))",
        python=(
            "match 1 + 1:\n"
            "    case 1:\n"
            "        answer = S.one\n"
            "    case 2:\n"
            "        answer = S.two\n"
            "answer"
        ),
    ),
    Entry(
        "let", ("(-> Atom %Undefined% Atom %Undefined%)",), "Symbol", "control", "dissolves",
        "Assignment. It reads in MeTTa's own order, bind then use, which is why "
        "plain assignment and not the walrus is the taught spelling.",
        metta="!(let $x 1 (+ $x 1))", python="x = 1\nx + 1",
    ),
    Entry(
        "let*", ("(-> Expression Atom %Undefined%)",), "Symbol", "control", "dissolves",
        "A sequence of assignments; a statement sequence in a compiled body already "
        "chains into `let*`.",
        metta="!(let* (($x 1) ($y 2)) (+ $x $y))", python="x = 1\ny = 2\nx + y",
    ),
    Entry(
        "unify", ("(-> Atom Atom Atom Atom %Undefined%)",), "Symbol", "control", "method",
        "Structural unification. `metta.unify(a, b)` symmetrically answers one "
        "bindings mapping or `None`; `metta.unify(a, b, then, els)` evaluates the "
        "engine conditional, running `then` once per binding set and `els` only "
        "when none exists. A compiled body lowers the same four-argument call "
        "directly to the engine form.",
        metta="!(unify (f $x) (f a) $x nope)",
        python=(
            "assert metta.unify(S.f(S.a), S.f(V.x)) == {'x': S.a}\n"
            "metta.unify(S.f(V.x), S.f(S.a), V.x, S.nope).one()"
        ),
    ),
    Entry(
        "superpose", ("(-> Expression %Undefined%)",), "Grounded", "control", "dissolves",
        "Nondeterminism has no primitive of its own because Python's iteration IS "
        "it: a list of values is a multiset of answers, and `yield` is the same act "
        "inside a compiled body. `space.sample(q, k=10, seed=7)` is the weighted "
        "choice door, with replacement and implicit `(rate n)` weights.",
        metta="!(superpose (a b))",
        python=(
            "space.add_tagged_fact(S.rate(1), S.choice(S.a))\n"
            "assert len(space.sample(S.choice(V.x), k=10, seed=7)) == 10\n"
            "[S.a, S.b]"
        ),
    ),
    Entry(
        "collapse", ("(-> Atom Atom)",), "Symbol", "control", "dissolves",
        "`list()` is the everyday spelling, materialising the answers; `tuple()` is "
        "the same act when you want MeTTa's own `( )` atom back, which is what "
        "collapse answers.",
        metta="!(collapse (superpose (a b)))", python="answers = [S.a, S.b]\ntuple(answers)",
    ),
    Entry(
        "id", ("(-> $t $t)",), "Symbol", "control", "dissolves",
        "The identity function, which Python writes as the value itself.",
        metta="!(id 5)", python="5",
    ),
    Entry(
        "nop", ("(-> (%Rest% %Undefined%) (->))",), "Grounded", "control", "dissolves",
        "Python's `pass`, or simply not writing the call. It answers the unit.",
        metta="!(nop 1 2)", python="metta.Expression()",
    ),
    Entry(
        "if-equal", ("(-> Atom Atom Atom Atom %Undefined%)",), "Grounded", "control",
        "dissolves",
        "A conditional expression over `==`.",
        metta="!(if-equal a a yes no)", python="S.yes if S.a == S.a else S.no",
    ),
    Entry(
        "quote", ("(-> Atom Atom)",), "Symbol", "control", "dissolves",
        "There is nothing to quote: building a term at the `S.` door never "
        "evaluates it, so the quoting question does not arise. `S.quote(x)` builds "
        "the term itself where a program needs the constructor.",
        metta="!(quote (+ 1 2))", python="S.quote(S['+'](1, 2))",
    ),
    Entry(
        "noeval", ("(-> Atom Atom)",), "Symbol", "control", "dissolves",
        "The same point as `quote`: a built term is already unevaluated.",
        metta="!(noeval (+ 1 2))", python="S['+'](1, 2)",
    ),
    Entry(
        "unquote", ("(-> %Undefined% %Undefined%)",), "Symbol", "control", "method",
        "Reducing a quoted term is `m.eval`, primitive 4.",
        metta="!(unquote (quote (+ 1 2)))", python="m.eval(S['+'](1, 2))",
    ),
    Entry(
        "gtry", ("(-> Atom Atom Atom)",), "Symbol", "control", "method",
        "LeaTTa's guarded try is lib_strategy's binary failure-to-identity "
        "spelling. Python builds the same gtry atom and evaluates it in the space.",
        metta="!(gtry id a)",
        python=PY_STRATEGY_SETUP + "space.eval(S.gtry(metta.strategies.id, S.a))",
        petta_setup=STRATEGY_SETUP,
        petta_inferences=STRATEGY_INFERENCES,
    ),
    Entry(
        "_check-alternatives", ("(-> Atom Atom)",), "Symbol", "control", "internal",
        "LeaTTa's alternative-set check inside the Stratego basis.",
    ),
    Entry(
        "_case-empty", ("(-> Expression Atom)",), "Symbol", "control", "internal",
        "LeaTTa's own decomposition of `case`.",
    ),
    Entry(
        "case%", ("(-> Atom Expression %Undefined%)",), "Symbol", "control", "absent",
        "LeaTTa's `%`-suffixed variant, the error-transparent twin of `case`. PeTTa "
        "ships no `%` family.",
        metta="!(case% 2 ((1 one) (2 two)))", unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "let%", ("(-> Atom %Undefined% Atom %Undefined%)",), "Symbol", "control", "absent",
        "LeaTTa's error-transparent twin of `let`.",
        metta="!(let% $x 1 (+ $x 1))", unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "let*%", ("(-> Expression Atom %Undefined%)",), "Symbol", "control", "absent",
        "LeaTTa's error-transparent twin of `let*`.",
        metta="!(let*% (($x 1)) $x)", unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "unify%", ("(-> Atom Atom Atom Atom %Undefined%)",), "Symbol", "control", "absent",
        "LeaTTa's error-transparent twin of `unify`.",
        metta="!(unify% (f a) (f $x) $x nope)", unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "=%", ("(-> $t $t %Undefined%)",), "Symbol", "control", "absent",
        "LeaTTa's error-transparent twin of `=`, the equation head itself.",
        metta="!(get-type =%)", unrun="PeTTa does not declare the name",
    ),
    Entry(
        "switch-minimal", ("(-> Atom Expression Atom)",), "Symbol", "control", "internal",
        "LeaTTa's own decomposition of `switch`.",
    ),
    Entry(
        "_switch-minimal%", ("(-> Atom Expression Atom)",), "Symbol", "control", "internal",
        "LeaTTa's own decomposition of `switch`.",
    ),
    Entry(
        "switch-internal", ("(-> Atom Expression Atom)",), "Symbol", "control", "internal",
        "LeaTTa's own decomposition of `switch`.",
    ),
    Entry(
        "switch-internal%", ("(-> Atom Expression Atom)",), "Symbol", "control", "internal",
        "LeaTTa's own decomposition of `switch`.",
    ),
    Entry(
        "case-empty-internal", ("(-> Atom Atom)",), "Symbol", "control", "internal",
        "LeaTTa's own decomposition of `case`.",
    ),
    # --------------------------------------------------------------- spaces
    Entry(
        "add-atom", ("(-> SpaceType Atom (->))",), "Grounded", "spaces", "dissolves",
        "`space += atom`, the container protocol. A plain Python tuple encodes to "
        "an expression on the way in, so a fact needs no builder ceremony.",
        metta="!(bind! &pb (new-space))\n!(add-atom &pb (f 1))\n!(get-atoms &pb)",
        python="space += (S.f, 1)\nspace.atoms()",
    ),
    Entry(
        "add-atoms", ("(-> SpaceType Expression (->))",), "Symbol", "spaces", "dissolves",
        "The same `+=` door, once per fact: anything that yields tuples is a fact "
        "stream. One friction, measured: a LIST on the `+=` door writes one atom "
        "holding the list rather than one atom per element, so the row loops "
        "[measured 2026-08-22: `space += [(S.f, 1), (S.f, 2)]` stores "
        "`((f 1) (f 2))`; `space.add(a, b)` is the varargs door that does write "
        "both].",
        metta="!(bind! &pb (new-space))\n!(add-atoms &pb ((f 1) (f 2)))\n!(get-atoms &pb)",
        python="for fact in [(S.f, 1), (S.f, 2)]:\n    space += fact\nspace.atoms()",
    ),
    Entry(
        "add-reduct", ("(-> SpaceType %Undefined% (->))",), "Symbol", "spaces", "dissolves",
        "There is no second door: `+=` adds what you give it, so adding a REDUCT is "
        "explicit composition, `space += m.eval(term)[0]`. The row wraps the sum "
        "because PeTTa's write door REFUSES a bare grounded atom that its own "
        "MeTTa door accepts [measured 2026-08-22: `space += metta.ground(3)` "
        "raises `a stored atom is a non-empty expression`, while "
        "`!(add-reduct &pb (+ 1 2))` stores `3`].",
        metta="!(bind! &pb (new-space))\n!(add-reduct &pb (total (+ 1 2)))\n!(get-atoms &pb)",
        python="space += S.total(m.eval(S['+'](1, 2))[0])\nspace.atoms()",
        differs=(
            "PeTTa stores `(total (+ 1 2))` UNREDUCED where LeaTTa and the Python "
            "composition both store `(total 3)`: this engine's add-reduct does not "
            "reduce inside an expression whose head has no equations"
        ),
    ),
    Entry(
        "add-reducts", ("(-> SpaceType %Undefined% (->))",), "Symbol", "spaces", "dissolves",
        "The plural of the same composition: evaluate, then write the answers.",
        metta="!(bind! &pb (new-space))\n"
              "!(add-reducts &pb ((total (+ 1 2)) (total (+ 2 2))))\n"
              "!(get-atoms &pb)",
        python="for term in [S['+'](1, 2), S['+'](2, 2)]:\n"
               "    space += S.total(m.eval(term)[0])\n"
               "space.atoms()",
        differs=(
            "PeTTa stores both forms UNREDUCED where LeaTTa and the Python "
            "composition store `(total 3)` and `(total 4)`, the same non-reduction "
            "as `add-reduct`"
        ),
    ),
    Entry(
        "remove-atom", ("(-> SpaceType Atom (->))",), "Grounded", "spaces", "dissolves",
        "`space -= atom` removes THAT atom and never pattern-matches; `del "
        "space[pattern]` is the pattern form, and the pair is taught together.",
        metta="!(bind! &pb (new-space))\n!(add-atom &pb (f 1))\n!(remove-atom &pb (f 1))\n"
              "!(get-atoms &pb)",
        python="space += S.f(1)\nspace -= S.f(1)\nspace.atoms()",
    ),
    Entry(
        "get-atoms", ("(-> SpaceType Atom)",), "Grounded", "spaces", "method",
        "`space.atoms()`, or `for atom in space` when you want to walk them.",
        metta="!(bind! &pb (new-space))\n!(add-atom &pb (f 1))\n!(get-atoms &pb)",
        python="space += S.f(1)\nlist(space)",
    ),
    Entry(
        "match", ("(-> SpaceType Atom Atom %Undefined%)",), "Grounded", "spaces", "method",
        "`space[pattern]` is the subscript door and `space.match(pattern)` the named "
        "one; the TEMPLATE is built in Python from the answer's bindings. "
        "`under=counting|tropical|prov|ranked` changes the annotation algebra; "
        "`answers(call, under=...)` is its call twin, `with metta.under(...)` "
        "scopes the default, and an annotated answer exposes `.annotation`, "
        "`.why()` and `.under(other)` without a re-query. `metta.algebra(...)` "
        "constructs arbitrary carriers while remaining their namespace.",
        metta="!(bind! &pb (new-space))\n!(add-atom &pb (f 1))\n!(match &pb (f $x) $x)",
        python=(
            "space += S.f(1)\n"
            "assert space.match(S.f(V.x), under=metta.counting).one() == 1\n"
            "space.run('(= (phrasebook-call) yes)')\n"
            "assert space.answers(S.phrasebook_call(), under=metta.counting).one() == 1\n"
            "with metta.under(metta.prov):\n"
            "    annotated = space.match(S.f(V.x)).one()\n"
            "assert annotated.annotation == S.one\n"
            "assert annotated.under(metta.counting).annotation == 1\n"
            "assert annotated.why()\n"
            "declared = metta.algebra(S.phrasebook_max_plus, plus=max, "
            "times=lambda a, b: a + b, zero=-100, one=0, order='descending')\n"
            "assert declared.name == 'phrasebook-max-plus'\n"
            "[row['x'] for row in space[S.f(V.x)]]"
        ),
    ),
    Entry(
        "match%", ("(-> SpaceType Atom Atom %Undefined%)",), "Grounded", "spaces", "absent",
        "LeaTTa's error-transparent twin of `match`.",
        metta="!(bind! &pb (new-space))\n!(match% &pb (f $x) $x)",
        unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "new-space", ("(-> SpaceType)",), "Grounded", "spaces", "method",
        "`metta.space()`. A constructor call is Python's own spelling for `make me "
        "a fresh one`, and the row asks the fresh space for its atoms because the "
        "NAME a space gets differs per engine.",
        metta="!(get-atoms (new-space))", python="list(metta.space())",
    ),
    Entry(
        "fork-space", ("(-> SpaceType SpaceType)",), "Grounded", "spaces", "method",
        "`space.copy()`, which answers an independent space: writing to the copy "
        "leaves the original alone [measured 2026-08-22].",
        metta="!(bind! &pb (new-space))\n!(add-atom &pb (f 1))\n!(get-atoms (fork-space &pb))",
        python="space += S.f(1)\nspace.copy().atoms()",
        unrun="PeTTa leaves the MeTTa call unreduced",
    ),
    Entry(
        "&self", ("SpaceType",), "Grounded", "spaces", "dissolves",
        "The space you are in, which in Python is the handle you already hold: `m` "
        "for the engine's own space, `space` for a named one. A name spelt as a "
        "symbol is what a Python binding is for.",
        metta="!(add-atom &self (f 1))\n!(get-atoms &self)",
        python="space += S.f(1)\nspace.atoms()",
    ),
    Entry(
        "context-space", ("(-> SpaceType)",), "Symbol", "spaces", "method",
        "The space a program is currently in, which in Python is the handle it "
        "holds; `metta.current_space()` is the door for code that did not receive "
        "one, and it follows Python's own `current_thread` and `current_task` "
        "convention, so the Python word wins over the instruction's name. The row "
        "asks both sides for the current space's atoms.",
        metta="!(add-atom (context-space) (f 1))\n!(get-atoms (context-space))",
        python="space += S.f(1)\nspace.atoms()",
    ),
    Entry(
        "mod-space!", ("(-> Atom SpaceType)",), "Grounded", "spaces", "absent",
        "The space of a loaded module. PeTTa's module story is Python packaging, so "
        "the name has no image here.",
        metta="!(mod-space! stdlib)", unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "module-space-no-deps", ("(-> SpaceType SpaceType)",), "Grounded", "spaces", "absent",
        "A module's own space without its dependencies. Same module story.",
        metta="!(module-space-no-deps (new-space))",
        unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "get-deps", ("(-> Atom Atom)",), "Grounded", "spaces", "absent",
        "A loaded module's direct dependency names. Same module story: PeTTa's "
        "module story is Python packaging, so the name has no image here.",
        metta="!(get-deps stdlib)", unrun="PeTTa leaves the call unreduced",
    ),
    # ---------------------------------------------------------------- types
    Entry(
        "get-type", ("(-> Atom %Undefined%)",), "Grounded", "types", "method",
        "Declared types are space-relative, so `space.type(atom)` asks the space. "
        "Class declarations use the consolidated `@space.define` decorator.",
        metta="!(get-type 1)", python="m.type(1)",
    ),
    Entry(
        "get-type-space", ("(-> SpaceType Atom Atom)",), "Grounded", "types", "method",
        "The same question asked of a named space through that handle's "
        "`space.type(atom)` method.",
        metta="!(get-type-space &self 1)",
        python="space.type(1)",
    ),
    Entry(
        "get-metatype", ("(-> Atom Atom)",), "Grounded", "types", "dissolves",
        "Python's own builtin `type`: the four atom classes ARE the four metatypes, "
        "so `type(a).__name__` is the metatype by construction.",
        metta="!(get-metatype (a b))",
        python="e = metta.Expression(S.a, S.b)\nS[e.metatype]",
    ),
    Entry(
        "is-function", ("(-> Type Bool)",), "Symbol", "types", "dissolves",
        "Asking whether a type is an arrow. In Python the same question is asked of "
        "the annotation, and `m.is_function(name)` asks it of a defined name.",
        metta="!(is-function (-> Number Number))",
        python="t = S['->'](S.Number, S.Number)\nt[0] == S['->']",
    ),
    Entry(
        "->", ("(-> (%Rest% Type) Type)",), "Symbol", "types", "dissolves",
        "Annotations. A parameter and return annotation on a decorated function "
        "emits the arrow, and `Callable[[int], int]` maps through the same one "
        "table; `S['->']` stays for a hand-built arrow.",
        metta="(: pbf (-> Number Number))\n(= (pbf $x) $x)\n!(get-type pbf)",
        python="t = S['->'](S.Number, S.Number)\nt",
    ),
    Entry(
        "=", ("(-> $t $t %Undefined%)",), "Symbol", "types", "method",
        "The definitional decorator. `@m.define` compiles a function into "
        "equations, `metta.equation(lhs).to(rhs)` builds one by hand, and both land "
        "as ordinary `(= ...)` atoms a program can match.",
        metta="(= (pbf $x) (+ $x 1))\n!(pbf 1)",
        python=(
            "space += metta.equation(S.pbf(V.x)).to(V.x + 1)\n"
            "space.eval(S.pbf(1))[0]"
        ),
    ),
    Entry(
        "SpaceType", ("Type",), "Symbol", "types", "absent",
        "The type of a space. PeTTa does not declare the name, so there is nothing "
        "for a Python type table to map to yet.",
        metta="!(get-type &self)", unrun="PeTTa answers SpaceType for a space but "
        "does not declare the symbol itself",
    ),
    Entry(
        "TP", ("Type",), "Symbol", "types", "method",
        "Lämmel's type-preserving strategy scheme, exported as the reified "
        "`metta.strategies.TP` symbol.",
        metta="!(get-type TP)",
        python=PY_STRATEGY_SETUP + "space.eval(S['get-type'](metta.strategies.TP))",
        petta_setup=STRATEGY_SETUP,
        petta_inferences=STRATEGY_INFERENCES,
    ),
    Entry(
        "TU", ("(-> Type Type)",), "Symbol", "types", "method",
        "Lämmel's type-unifying scheme constructor, exported as the reified "
        "`metta.strategies.TU` symbol.",
        metta="!(get-type TU)",
        python=PY_STRATEGY_SETUP + "space.eval(S['get-type'](metta.strategies.TU))",
        petta_setup=STRATEGY_SETUP,
        petta_inferences=STRATEGY_INFERENCES,
    ),
    Entry(
        "Pair", ("(-> $ta $tb (PairType $ta $tb))",), "Symbol", "types", "absent",
        "A constructor from LeaTTa's `skel` demonstration module. PeTTa has no "
        "such module; a class decorated with `@space.define` declares its "
        "constructor in that space.",
        metta="!(get-type (Pair 1 2))", unrun="PeTTa does not declare the name",
    ),
    Entry(
        "PairType", ("(-> $ta $tb Type)",), "Symbol", "types", "absent",
        "The parameterised type of `Pair`, from the same module.",
        metta="!(get-type PairType)", unrun="PeTTa does not declare the name",
    ),
    Entry(
        "skel-swap-pair", ("(-> (PairType $ta $tb) (PairType $tb $ta))",), "Symbol",
        "types", "absent",
        "The `skel` module's worked equation, LeaTTa's demonstration that a "
        "built-in module can ship both a MeTTa and a native implementation.",
        metta="!(skel-swap-pair (Pair 1 2))", unrun="PeTTa does not declare the name",
    ),
    Entry(
        "skel-swap-pair-native", ("(-> (PairType $ta $tb) (PairType $tb $ta))",), "Grounded",
        "types", "absent",
        "The native half of the same demonstration.",
        metta="!(skel-swap-pair-native (Pair 1 2))",
        unrun="PeTTa does not declare the name",
    ),
    Entry(
        "◁", ("(-> Atom Type Atom Atom)",), "Symbol", "types", "method",
        "The typed strategy-application atom selects the TP or TU scheme before "
        "running the named strategy.",
        metta="!(get-type ◁)",
        python=PY_STRATEGY_SETUP + "space.eval(S['get-type'](S['◁']))",
        petta_setup=STRATEGY_SETUP,
        petta_inferences=STRATEGY_INFERENCES,
    ),
    # ---------------------------------------------------------------- state
    Entry(
        "new-state", ("(-> $t (StateMonad $t))",), "Symbol", "state", "method",
        "`metta.State[T](value, space=space)` creates the typed Python handle. "
        "The row reads `.value` because the engine cell itself is deliberately "
        "hidden behind that handle. An event `fold(..., into=state)` passes this "
        "same process-shared cell to its step; individual reads and writes are "
        "thread-safe, but a compound read-modify-write needs coordination.",
        metta="!(get-state (new-state 1))",
        python=(
            "state = metta.State[int](1, space=m)\n"
            "def retain(cell, event):\n"
            "    cell.value += int(event.n)\n"
            "folded = m.events().fold(retain, space=space.name, "
            "pattern=S.delta(V.n), into=state)\n"
            "space += S.delta(0)\n"
            "folded.cancel()\n"
            "state.value"
        ),
    ),
    Entry(
        "get-state", ("(-> (StateMonad $tgso) $tgso)",), "Grounded", "state", "method",
        "Reading the cell is the typed handle's `state.value` property.",
        metta="!(let $c (new-state 5) (get-state $c))",
        python="state = metta.State[int](5, space=m)\nstate.value",
    ),
    Entry(
        "change-state!", ("(-> (StateMonad $tcso) $tcso (StateMonad $tcso))",), "Grounded",
        "state", "method",
        "Assigning `state.value` writes the same typed engine cell and reading it "
        "back returns the replacement.",
        metta="!(let $c (new-state 1) (get-state (change-state! $c 2)))",
        python=(
            "state = metta.State[int](1, space=m)\n"
            "state.value = 2\n"
            "state.value"
        ),
    ),
    Entry(
        "_new-state", ("(-> $t Expression (StateMonad $t))",), "Grounded", "state", "internal",
        "LeaTTa's internal constructor behind `new-state`.",
    ),
    # ----------------------------------------------------------------- text
    Entry(
        "println!", ("(-> %Undefined% (->))",), "Grounded", "text", "dissolves",
        "Python's `print`.",
        metta="!(println! hello)", python="print('hello')\nmetta.Expression()",
    ),
    Entry(
        "trace!", ("(-> %Undefined% Atom %Undefined%)",), "Grounded", "text", "dissolves",
        "`print` or `logging` beside the value; `m.trace()` is the engine's own "
        "reduction trace, a different and deeper thing.",
        metta="!(trace! hello (+ 1 2))",
        python="print('hello')\n1 + 2",
    ),
    Entry(
        "format-args", ("(-> String Expression String)",), "Grounded", "text", "dissolves",
        "An f-string. MeTTa's `{}` holes are Python's own interpolation.",
        metta='!(format-args "{} and {}" (a b))',
        python="a, b = S.a, S.b\nf'{a} and {b}'",
    ),
    Entry(
        "print-alternatives!", ("(-> Atom Expression (->))",), "Grounded", "text", "dissolves",
        "Python's `print` over the answers, which is what LeaTTa's assert family "
        "uses it for: showing what a form actually answered.",
        metta="!(print-alternatives! subject (a b))",
        python="print(S.subject, [S.a, S.b])\nmetta.Expression()",
        unrun="PeTTa leaves the MeTTa call unreduced",
    ),
    Entry(
        "_print-alternatives-each!", ("(-> Expression (->))",), "Symbol", "text", "internal",
        "LeaTTa's per-alternative half of the printer.",
    ),
    # --------------------------------------------------------------- assert
    Entry(
        "assert", ("(-> Atom (->))",), "Symbol", "assert", "dissolves",
        "Python's own `assert`. A twin or a test states its claims this way and the "
        "run proves them, because a false assertion raises.",
        metta="!(assert (== 1 1))", python="assert 1 == 1\nTrue",
        differs="LeaTTa answers the unit `()` where PeTTa answers True",
    ),
    Entry(
        "assertEqual", ("(-> Atom Atom (->))",), "Symbol", "assert", "dissolves",
        "`assert a == b`, and pytest's own assertion rewriting prints the halves.",
        metta="!(assertEqual (+ 1 1) 2)", python="assert m.eval(S['+'](1, 1))[0] == 2\nTrue",
        differs="LeaTTa answers the unit `()` where PeTTa answers True",
    ),
    Entry(
        "assertEqualMsg", ("(-> Atom Atom Atom (->))",), "Symbol", "assert", "dissolves",
        "`assert a == b, message`, which is Python's own second argument.",
        metta='!(assertEqualMsg (+ 1 1) 2 "sums")',
        python="assert m.eval(S['+'](1, 1))[0] == 2, 'sums'\nTrue",
        differs="LeaTTa answers the unit `()` where PeTTa answers True",
    ),
    Entry(
        "assertAlphaEqual", ("(-> Atom Atom (->))",), "Symbol", "assert", "dissolves",
        "`assert a.alpha_eq(b)`: the assertion is Python's, the relation is MeTTa's.",
        metta="!(assertAlphaEqual (f $x) (f $y))",
        python="assert S.f(V.x).alpha_eq(S.f(V.y))\nTrue",
        differs="LeaTTa answers the unit `()` where PeTTa answers True",
    ),
    Entry(
        "assertAlphaEqualMsg", ("(-> Atom Atom Atom (->))",), "Symbol", "assert", "dissolves",
        "The same with Python's assertion message.",
        metta='!(assertAlphaEqualMsg (f $x) (f $y) "renaming")',
        python="assert S.f(V.x).alpha_eq(S.f(V.y)), 'renaming'\nTrue",
        differs="LeaTTa answers the unit `()` where PeTTa answers True",
    ),
    Entry(
        "assertEqualToResult", ("(-> Atom Atom (->))",), "Symbol", "assert", "dissolves",
        "The right-hand side is a LIST of expected answers rather than one, which "
        "is `assert list(answers) == [...]`.",
        metta="!(assertEqualToResult (superpose (1 2)) (1 2))",
        python="assert m.eval(S.superpose(metta.Expression(1, 2))) == [1, 2]\nTrue",
        differs="LeaTTa answers the unit `()` where PeTTa answers True",
    ),
    Entry(
        "assertEqualToResultMsg", ("(-> Atom Atom Atom (->))",), "Symbol", "assert", "dissolves",
        "The same with Python's assertion message.",
        metta='!(assertEqualToResultMsg (superpose (1 2)) (1 2) "both")',
        python="assert m.eval(S.superpose(metta.Expression(1, 2))) == [1, 2], 'both'\nTrue",
        differs="LeaTTa answers the unit `()` where PeTTa answers True",
    ),
    Entry(
        "assertAlphaEqualToResult", ("(-> Atom Atom (->))",), "Symbol", "assert", "dissolves",
        "The answer-list form compared modulo renaming.",
        metta="!(assertAlphaEqualToResult (f $x) ((f $y)))",
        python="assert m.eval(S.f(V.x))[0].alpha_eq(S.f(V.y))\nTrue",
        differs="LeaTTa answers the unit `()` where PeTTa answers True",
    ),
    Entry(
        "assertAlphaEqualToResultMsg", ("(-> Atom Atom Atom (->))",), "Symbol", "assert",
        "dissolves", "The same with Python's assertion message.",
        metta='!(assertAlphaEqualToResultMsg (f $x) ((f $y)) "renaming")',
        python="assert m.eval(S.f(V.x))[0].alpha_eq(S.f(V.y)), 'renaming'\nTrue",
        differs="LeaTTa answers the unit `()` where PeTTa answers True",
    ),
    Entry(
        "assertIncludes", ("(-> Atom Expression (->))",), "Symbol", "assert", "dissolves",
        "Python's own `in`.",
        metta="!(assertIncludes (superpose (a b)) (a))",
        python="assert S.a in m.eval(S.superpose(metta.Expression(S.a, S.b)))\nTrue",
        differs="LeaTTa answers the unit `()` where PeTTa answers True",
    ),
    Entry(
        "_assert-results-are-equal", ("(-> Atom Atom Atom (->))",), "Grounded", "assert",
        "internal", "LeaTTa's internal comparison behind the assert family.",
    ),
    Entry(
        "_assert-results-are-equal-msg", ("(-> Atom Atom Atom Atom (->))",), "Grounded",
        "assert", "internal", "LeaTTa's internal comparison behind the assert family.",
    ),
    Entry(
        "_assert-results-are-alpha-equal", ("(-> Atom Atom Atom (->))",), "Grounded",
        "assert", "internal", "LeaTTa's internal comparison behind the assert family.",
    ),
    Entry(
        "_assert-results-are-alpha-equal-msg", ("(-> Atom Atom Atom Atom (->))",), "Grounded",
        "assert", "internal", "LeaTTa's internal comparison behind the assert family.",
    ),
    # ------------------------------------------------------------------ doc
    Entry(
        "get-doc", ("(-> SpaceType Atom %Undefined%)",), "Symbol", "doc", "dissolves",
        "Python's builtin `help`, over the docstring a decorated function already "
        "carries. PeTTa answers nothing here because no documentation atoms are "
        "written yet, which is the doc-vocabulary gap.",
        metta="!(get-doc &self +)",
        python="def slug(title):\n    'Make a title into a slug.'\nslug.__doc__",
        differs=(
            "LeaTTa answers the full `@doc-formal` structure for `+`; PeTTa answers "
            "nothing, because nothing emits documentation atoms"
        ),
    ),
    Entry(
        "@doc",
        (
            "(-> Atom DocDescription DocInformal)",
            "(-> Atom DocDescription DocParameters DocReturnInformal DocInformal)",
        ),
        "Symbol", "doc", "dissolves",
        "A docstring. One docstring is meant to feed both worlds: Python's `help` "
        "and the engine's `get-doc`, once the emission lands.",
        metta='!(@doc pbf (@desc "adds one"))',
        python="def pbf(x):\n    'adds one'\npbf.__doc__",
        differs=(
            "the MeTTa side is a CONSTRUCTOR and stays unreduced on both engines, "
            "which is correct; the Python side shows the same text"
        ),
    ),
    Entry(
        "@desc", ("(-> String DocDescription)",), "Symbol", "doc", "dissolves",
        "The description line of a docstring.",
        metta='!(@desc "adds one")',
        python="'adds one'",
        differs="the MeTTa side is a constructor and stays unreduced, correctly",
    ),
    Entry(
        "@param",
        ("(-> String DocParameterInformal)", "(-> DocType DocDescription DocParameter)"),
        "Symbol", "doc", "dissolves",
        "One parameter's line in a docstring, which the docstring convention "
        "already carries.",
        metta='!(@param "the addend")', python="'the addend'",
        differs="the MeTTa side is a constructor and stays unreduced, correctly",
    ),
    Entry(
        "@params", ("(-> Expression DocParameters)",), "Symbol", "doc", "dissolves",
        "The parameter block of a docstring.",
        metta='!(@params ((@param "the addend")))', python="['the addend']",
        differs="the MeTTa side is a constructor and stays unreduced, correctly",
    ),
    Entry(
        "@return",
        ("(-> String DocReturnInformal)", "(-> DocType DocDescription DocReturn)"),
        "Symbol", "doc", "dissolves",
        "The return line of a docstring.",
        metta='!(@return "the sum")', python="'the sum'",
        differs="the MeTTa side is a constructor and stays unreduced, correctly",
    ),
    Entry(
        "@type", ("(-> Type DocType)",), "Symbol", "doc", "dissolves",
        "The type shown in documentation, which annotations already supply.",
        metta="!(@type Number)",
        python="def pbf(x: int) -> int:\n    'adds one'\npbf.__annotations__['return']",
        differs="the MeTTa side is a constructor and stays unreduced, correctly",
    ),
    Entry(
        "@item", ("(-> Atom DocItem)",), "Symbol", "doc", "dissolves",
        "The subject a documentation record is about, which in Python is the "
        "object the docstring hangs on.",
        metta="!(@item pbf)", python="S.pbf",
        differs="the MeTTa side is a constructor and stays unreduced, correctly",
    ),
    Entry(
        "@doc-formal",
        (
            "(-> DocItem DocKindFunction DocType DocDescription DocParameters DocReturn"
            " DocFormal)",
            "(-> DocItem DocKindAtom DocType DocDescription DocFormal)",
            "(-> DocItem DocKindFunction DocType DocDescription DocFormal)",
        ),
        "Symbol", "doc", "dissolves",
        "The whole documentation record, which a typed and docstringed Python "
        "function already is: signature plus prose in one place.",
        metta='!(@doc-formal (@item pbf) (@kind function) (@type (-> Number Number))'
              ' (@desc "adds one"))',
        python=(
            "def pbf(x: int) -> int:\n"
            "    'adds one'\n"
            "(pbf.__annotations__['return'], pbf.__doc__)"
        ),
        differs="the MeTTa side is a constructor and stays unreduced, correctly",
    ),
    Entry(
        "help!", ("(-> Atom (->))", "(-> (->))"), "Symbol", "doc", "dissolves",
        "Python's builtin `help`, which is the same act on the same docstring.",
        metta="!(help! +)", python="def pbf(x):\n    'adds one'\npbf.__doc__",
        differs=(
            "LeaTTa prints the documentation and answers the unit; PeTTa leaves the "
            "call unreduced because it declares no documentation"
        ),
        unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "help-internal!", ("(-> Atom (->))", "(-> Symbol (->))"), "Symbol", "doc", "internal",
        "LeaTTa's internal dispatch behind `help!`.",
    ),
    Entry(
        "help-param!", ("(-> Atom (->))",), "Symbol", "doc", "internal",
        "LeaTTa's internal parameter printer behind `help!`.",
    ),
    Entry(
        "help-space!", ("(-> SpaceType (->))",), "Symbol", "doc", "internal",
        "LeaTTa's internal space-documentation printer behind `help!`.",
    ),
    Entry(
        "get-doc-atom", ("(-> SpaceType Atom %Undefined%)",), "Symbol", "doc", "internal",
        "LeaTTa's internal dispatch behind `get-doc`.",
    ),
    Entry(
        "get-doc-function", ("(-> SpaceType Atom Type %Undefined%)",), "Symbol", "doc",
        "internal", "LeaTTa's internal dispatch behind `get-doc`.",
    ),
    Entry(
        "get-doc-single-atom", ("(-> SpaceType Atom %Undefined%)",), "Symbol", "doc",
        "internal", "LeaTTa's internal dispatch behind `get-doc`.",
    ),
    Entry(
        "get-doc-params", ("(-> Expression Atom Expression (Expression Atom))",), "Symbol",
        "doc", "internal", "LeaTTa's internal dispatch behind `get-doc`.",
    ),
    Entry(
        "undefined-doc-function-type", ("(-> Expression Type)",), "Symbol", "doc", "internal",
        "LeaTTa's internal fallback type for an undocumented application.",
    ),
    # -------------------------------------------------------------- modules
    Entry(
        "import!", ("(-> Atom Atom (->))",), "Grounded", "modules", "dissolves",
        "Python's own `import`, and for a MeTTa library the boot manifest or "
        "`m.load(path)`. The module catalog IS Python packaging.",
        metta="!(import! &self (library lib_he))\n!(unify (f a) (f $x) $x nope)",
        python="import math\nS[math.__name__]",
        differs=(
            "MeTTa imports a MeTTa library into a space where Python imports a "
            "Python module into a namespace"
        ),
    ),
    Entry(
        "import-into!", ("(-> SpaceType Atom (->))",), "Grounded", "modules", "absent",
        "Importing into a NAMED space rather than the current one. PeTTa's loader "
        "does not offer it.",
        metta="!(import-into! (new-space) (library lib_he))",
        unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "import-item!", ("(-> Atom Atom Atom (->))",), "Grounded", "modules", "absent",
        "Importing one named item, which is Python's `from x import y`. Not "
        "implemented here.",
        metta="!(import-item! &self (library lib_he) unify)",
        unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "include", ("(-> Atom %Undefined%)",), "Grounded", "modules", "method",
        "`space.load(path)` reads a file into that space, which is what include "
        "does; Python's own `import` is the spelling for a Python module.",
        metta="!(get-metatype include)",
        python=(
            "import pathlib, tempfile\n"
            "path = pathlib.Path(tempfile.mkdtemp()) / 'inc.metta'\n"
            "path.write_text('(= (pbi) 7)\\n')\n"
            "space.load(str(path))\n"
            "space.eval(S.pbi())[0]"
        ),
        differs=(
            "no file path is portable between the two engines, so the MeTTa column "
            "shows only that the name is a grounded operation while the Python "
            "column loads a real file and calls what it defined"
        ),
    ),
    Entry(
        "git-import!", ("(-> String String Atom)",), "Grounded", "modules", "method",
        "pip and `importlib`. Fetching a dependency is packaging's job, the module "
        "catalog IS Python packaging, and a boot manifest names the distribution.",
        metta="!(get-metatype git-import!)",
        python="import importlib\nS[importlib.import_module('json').__name__]",
        differs=(
            "a row cannot fetch a repository, so the MeTTa column shows only that "
            "the name is a grounded operation while the Python column imports a "
            "distribution that is already installed"
        ),
    ),
    Entry(
        "git-module!", ("(-> Atom (->))",), "Grounded", "modules", "absent",
        "Upstream's bespoke package manager.",
        metta="!(get-metatype git-module!)",
        unrun="PeTTa does not declare the name",
        ruled=(
            "decision 8: the module catalog IS Python packaging, and upstream's "
            "bespoke manager is the fork not taken, so the absence is a decision "
            "rather than a gap"
        ),
    ),
    Entry(
        "register-module!", ("(-> Atom (->))",), "Grounded", "modules", "absent",
        "Registering a module with the bespoke catalog. A Python distribution "
        "registers itself by declaring an entry point, which pip then installs.",
        metta="!(get-metatype register-module!)",
        unrun="PeTTa does not declare the name",
        ruled=(
            "decision 8: pip and entry-point discovery are the catalog, so the "
            "absence is a decision rather than a gap"
        ),
    ),
    Entry(
        "print-mods!", ("(-> (->))",), "Grounded", "modules", "dissolves",
        "`print(sorted(sys.modules))`. Under the ruling that the module catalog IS "
        "Python packaging, the loaded-module question is Python's own.",
        metta="!(print-mods!)",
        python="import sys\nprint(len(sys.modules), 'modules')\nmetta.Expression()",
        differs=(
            "MeTTa modules there, Python modules here, which is what the ruling "
            "makes them"
        ),
        unrun="PeTTa does not declare the name",
    ),
    Entry(
        "loaded-mods!", ("(-> Atom)",), "Grounded", "modules", "dissolves",
        "`sys.modules`, the same list as data rather than printed.",
        metta="!(loaded-mods!)",
        python="import sys\nS['json'] if 'json' in sys.modules else S.absent",
        differs="MeTTa modules there, Python modules here",
        unrun="PeTTa does not declare the name",
    ),
    Entry(
        "module-tree!", ("(-> Atom)",), "Grounded", "modules", "dissolves",
        "`importlib.metadata.requires(name)`, which answers the dependency tree a "
        "distribution declares. The row names the door rather than a package, "
        "because no distribution is guaranteed installed wherever the lane runs.",
        metta="!(module-tree!)",
        python="import importlib.metadata\nS[importlib.metadata.requires.__name__]",
        differs=(
            "the trees are different: MeTTa modules there, installed distributions "
            "here"
        ),
        unrun="PeTTa does not declare the name",
    ),
    Entry(
        "bind!", ("(-> Symbol %Undefined% (->))",), "Grounded", "modules", "dissolves",
        "A Python name binding. `space = metta.space(...)` is exactly what a token "
        "binding was for, and Python's own scoping rules then apply.",
        metta="!(bind! &pb (new-space))\n!(add-atom &pb (f 1))\n!(get-atoms &pb)",
        python="space += S.f(1)\nspace.atoms()",
    ),
    # --------------------------------------------------------------- errors
    Entry(
        "Error", ("(-> Atom Atom ErrorType)",), "Symbol", "errors", "dissolves",
        "An exception. A Python operation raises and the boundary maps the "
        "exception INTO this algebra rather than inventing a parallel one. The "
        "constructor itself never reduces, on either engine, which is correct.",
        metta="!(Error a b)", python="S.Error(S.a, S.b)",
    ),
    Entry(
        "ErrorType", ("Type",), "Symbol", "errors", "dissolves",
        "The type an error atom carries, which on the Python side is the exception "
        "class.",
        metta="!(get-type (Error a b))", python="S.ErrorType",
    ),
    Entry(
        "BadType", ("(-> Type Type ErrorDescription)",), "Symbol", "errors", "absent",
        "The canonical wrong-type error description. PeTTa does not declare the "
        "name, which is the error-vocabulary gap ledger X names.",
        metta="!(get-type BadType)", unrun="PeTTa does not declare the name",
    ),
    Entry(
        "BadArgType", ("(-> Number Type Type ErrorDescription)",), "Symbol", "errors", "absent",
        "The positional form, `(BadArgType <pos> <expected> <actual>)`. Same gap.",
        metta="!(get-type BadArgType)", unrun="PeTTa does not declare the name",
    ),
    Entry(
        "IncorrectNumberOfArguments", ("ErrorDescription",), "Symbol", "errors", "absent",
        "The arity error description, which Python's own `TypeError` is the image "
        "of. Same gap.",
        metta="!(get-type IncorrectNumberOfArguments)",
        unrun="PeTTa does not declare the name",
    ),
    Entry(
        "if-error", ("(-> Atom Atom Atom %Undefined%)",), "Symbol", "errors", "dissolves",
        "`try`/`except`, or a conditional over the value. It is the railway "
        "combinator over Error atoms.",
        metta="!(if-error (Error a b) yes no)",
        python="e = S.Error(S.a, S.b)\nS.yes if e[0] == S.Error else S.no",
    ),
    Entry(
        "return-on-error", ("(-> Atom Atom %Undefined%)",), "Symbol", "errors", "dissolves",
        "Early return, which is Python's own `return` inside an `if`. Indexing "
        "needs the guard because a leaf atom is not indexable here.",
        metta="!(return-on-error a b)",
        python=(
            "value = S.a\n"
            "value if isinstance(value, metta.Expression) and value[0] == S.Error else S.b"
        ),
    ),
    Entry(
        "_separate-errors", ("(-> Expression Expression Expression)",), "Symbol", "errors",
        "dissolves",
        "Partitioning answers into errors and results, which is one comprehension "
        "per side.",
        metta="!(_separate-errors ((Error a b) c) ())",
        python=(
            "answers = [S.Error(S.a, S.b), S.c]\n"
            "[a for a in answers if isinstance(a, metta.Expression) and a[0] == S.Error]"
        ),
        unrun="PeTTa leaves the call unreduced",
    ),
    # ----------------------------------------------------------- strategies
    Entry(
        "try", ("TP", "(-> Atom Atom)"), "Symbol", "strategies", "method",
        "Stratego's `try(s) = s <+ id`. PeTTa reifies `s` in the plan and LeaTTa "
        "specialises the same law to one equality rewrite.",
        metta="(= (pb-try-step strategy-a) strategy-b)\n"
              "(= (pb-try-step $x) Empty)\n"
              "!(strategy-apply (try pb-try-step) strategy-a)",
        python=(
            PY_STRATEGY_SETUP
            + "space.run('(= (pb-try-step strategy-a) strategy-b) "
              "(= (pb-try-step $x) Empty)')\n"
              "space.eval(S['strategy-apply'](metta.strategies.try_(S['pb-try-step']), "
              "S['strategy-a']))"
        ),
        petta_setup=STRATEGY_SETUP,
        oracle_metta="(= strategy-a strategy-b)\n!(try strategy-a)",
        petta_inferences=STRATEGY_INFERENCES,
    ),
    Entry(
        "repeat", ("TP", "(-> Atom Atom)"), "Symbol", "strategies", "method",
        "Stratego's `repeat(s) = try(s ; repeat(s))`, root steps to a normal form.",
        metta="(= (pb-repeat-step strategy-a) strategy-b)\n"
              "(= (pb-repeat-step strategy-b) strategy-c)\n"
              "(= (pb-repeat-step $x) Empty)\n"
              "!(strategy-apply (repeat pb-repeat-step) strategy-a)",
        python=(
            PY_STRATEGY_SETUP
            + "space.run('(= (pb-repeat-step strategy-a) strategy-b) "
              "(= (pb-repeat-step strategy-b) strategy-c) "
              "(= (pb-repeat-step $x) Empty)')\n"
              "space.eval(S['strategy-apply'](metta.strategies.repeat(S['pb-repeat-step']), "
              "S['strategy-a']))"
        ),
        petta_setup=STRATEGY_SETUP,
        oracle_metta="(= strategy-a strategy-b)\n(= strategy-b strategy-c)\n"
                     "!(repeat strategy-a)",
        petta_inferences=STRATEGY_INFERENCES,
    ),
    Entry(
        "topdown", ("TP", "(-> Atom Atom)"), "Symbol", "strategies", "method",
        "Stratego's `topdown(s) = s ; all(topdown(s))`, preorder traversal.",
        metta="(= (pb-topdown-step strategy-a) strategy-b)\n"
              "(= (pb-topdown-step $x) Empty)\n"
              "!(strategy-apply (topdown (try pb-topdown-step)) "
              "(strategy-node strategy-a))",
        python=(
            PY_STRATEGY_SETUP
            + "space.run('(= (pb-topdown-step strategy-a) strategy-b) "
              "(= (pb-topdown-step $x) Empty)')\n"
              "plan = metta.strategies.topdown("
              "metta.strategies.try_(S['pb-topdown-step']))\n"
              "space.eval(S['strategy-apply'](plan, S['strategy-node'](S['strategy-a'])))"
        ),
        petta_setup=STRATEGY_SETUP,
        oracle_metta="(= strategy-a strategy-b)\n"
                     "(= (strategy-node strategy-b) strategy-bottomup-root)\n"
                     "!(topdown (strategy-node strategy-a))",
        petta_inferences=STRATEGY_INFERENCES,
    ),
    Entry(
        "bottomup", ("TP", "(-> Atom Atom)"), "Symbol", "strategies", "method",
        "Stratego's `bottomup(s) = all(bottomup(s)) ; s`, postorder traversal.",
        metta="(= (pb-bottomup-step strategy-a) strategy-b)\n"
              "(= (pb-bottomup-step (strategy-node strategy-b)) "
              "strategy-bottomup-root)\n"
              "(= (pb-bottomup-step $x) Empty)\n"
              "!(strategy-apply (bottomup (try pb-bottomup-step)) "
              "(strategy-node strategy-a))",
        python=(
            PY_STRATEGY_SETUP
            + "space.run('(= (pb-bottomup-step strategy-a) strategy-b) "
              "(= (pb-bottomup-step (strategy-node strategy-b)) "
              "strategy-bottomup-root) (= (pb-bottomup-step $x) Empty)')\n"
              "plan = metta.strategies.bottomup("
              "metta.strategies.try_(S['pb-bottomup-step']))\n"
              "space.eval(S['strategy-apply'](plan, S['strategy-node'](S['strategy-a'])))"
        ),
        petta_setup=STRATEGY_SETUP,
        oracle_metta="(= strategy-a strategy-b)\n"
                     "(= (strategy-node strategy-b) strategy-bottomup-root)\n"
                     "!(bottomup (strategy-node strategy-a))",
        petta_inferences=STRATEGY_INFERENCES,
    ),
    Entry(
        "innermost", ("TP", "(-> Atom Atom)"), "Symbol", "strategies", "method",
        "Stratego's `innermost(s) = bottomup(try(s ; innermost(s)))`.",
        metta="(= (pb-innermost-step strategy-a) strategy-b)\n"
              "(= (pb-innermost-step strategy-b) strategy-c)\n"
              "(= (pb-innermost-step (strategy-node strategy-c)) "
              "strategy-innermost-root)\n"
              "(= (pb-innermost-step $x) Empty)\n"
              "!(strategy-apply (innermost pb-innermost-step) "
              "(strategy-node strategy-a))",
        python=(
            PY_STRATEGY_SETUP
            + "space.run('(= (pb-innermost-step strategy-a) strategy-b) "
              "(= (pb-innermost-step strategy-b) strategy-c) "
              "(= (pb-innermost-step (strategy-node strategy-c)) "
              "strategy-innermost-root) (= (pb-innermost-step $x) Empty)')\n"
              "plan = metta.strategies.innermost(S['pb-innermost-step'])\n"
              "space.eval(S['strategy-apply'](plan, S['strategy-node'](S['strategy-a'])))"
        ),
        petta_setup=STRATEGY_SETUP,
        oracle_metta="(= strategy-a strategy-b)\n(= strategy-b strategy-c)\n"
                     "(= (strategy-node strategy-c) strategy-innermost-root)\n"
                     "!(innermost (strategy-node strategy-a))",
        petta_inferences=STRATEGY_INFERENCES,
    ),
    Entry(
        "stratego-all", ("(-> Atom Atom Atom)",), "Symbol", "strategies", "method",
        "Stratego's `all(s)`, applying a strategy to every immediate child.",
        metta="!(stratego-all id (f a b))",
        python=(
            PY_STRATEGY_SETUP
            + "plan = metta.strategies.stratego_all(metta.strategies.id)\n"
              "space.eval(S['strategy-apply'](plan, S.f(S.a, S.b)))"
        ),
        petta_setup=STRATEGY_SETUP,
        petta_inferences=STRATEGY_INFERENCES,
    ),
    Entry(
        "stratego-one", ("(-> Atom Atom Atom)",), "Symbol", "strategies", "method",
        "Stratego's `one(s)`, applying to one child. LeaTTa deliberately diverges "
        "from Stratego's committed choice by answering EVERY successful position "
        "through MeTTa's own nondeterminism.",
        metta="!(stratego-one id (f a b))",
        python=(
            PY_STRATEGY_SETUP
            + "plan = metta.strategies.stratego_one(metta.strategies.id)\n"
              "space.eval(S['strategy-apply'](plan, S.f(S.a, S.b)))"
        ),
        petta_setup=STRATEGY_SETUP,
        petta_inferences=STRATEGY_INFERENCES,
    ),
    Entry(
        "stratego-some", ("(-> Atom Atom Atom)",), "Symbol", "strategies", "absent",
        "Stratego's `some(s)`, the third traversal primitive beside `all` and "
        "`one`: apply the strategy to every immediate child it succeeds on, keep "
        "each declining child as written, and fail when no child succeeded. The "
        "non-emptiness guard is the whole content, since `all` composed with "
        "`gtry` can never fail. A LeaTTa extension beyond corelib.",
        metta="!(stratego-some id (f a b))", unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "_stratego-all-tail", ("(-> Atom Expression Expression)",), "Symbol", "strategies",
        "internal", "LeaTTa's internal tail recursion behind `stratego-all`.",
    ),
    Entry(
        "_stratego-some-walk", ("(-> Atom Expression Atom)",), "Symbol", "strategies",
        "internal", "LeaTTa's internal tail walk behind `stratego-some`, pairing "
        "the rebuilt tail with whether any member succeeded.",
    ),
    Entry(
        "eval-via-match", ("(-> Atom %Undefined%)",), "Symbol", "strategies", "absent",
        "The one-step rewriting strategy the whole basis is specialised to.",
        metta="!(eval-via-match (+ 1 2))", unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "eval-via-unify", ("(-> Atom %Undefined%)",), "Symbol", "strategies", "absent",
        "The unification-directed sibling of `eval-via-match`.",
        metta="!(eval-via-unify (+ 1 2))", unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "reduce-via-match", ("(-> Atom Atom %Undefined%)",), "Symbol", "strategies", "absent",
        "The reduction form of the same strategy.",
        metta="!(reduce-via-match (+ 1 2) x)", unrun="PeTTa leaves the call unreduced",
    ),
    # ------------------------------------------------------------- matching
    Entry(
        "fuzzy-match", ("(-> Atom Expression Number Atom)",), "Grounded", "matching", "absent",
        "LeaTTa's cost-bounded approximate matcher, answering each candidate with "
        "its cost. PeTTa has `metta.structures` for many-to-one matching and no "
        "approximate matcher.",
        metta="!(fuzzy-match (f a) ((f a) (f b)) 1)",
        unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "fuzzy-match-space", ("(-> SpaceType Atom Expression Number Atom)",), "Grounded",
        "matching", "absent", "The same over a space's atoms.",
        metta="!(fuzzy-match-space (new-space) (f a) ((f a)) 1)",
        unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "fuzzy-match-context", ("(-> SpaceType SpaceType Atom Expression Number Atom)",),
        "Grounded", "matching", "absent",
        "The same with a separate cost-declaration space.",
        metta="!(fuzzy-match-context (new-space) (new-space) (f a) ((f a)) 1)",
        unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "near-match", ("(-> Atom Expression Atom Atom)",), "Grounded", "matching", "absent",
        "The nearest-candidate form of the same family.",
        metta="!(near-match (f a) ((f a) (f b)) 1)",
        unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "sealed", ("(-> Expression Atom Atom)",), "Grounded", "matching", "method",
        "Freshening every variable except a named few, the hygiene primitive under "
        "rule emission. The Python surface makes most uses unnecessary by "
        "construction, because a parameter-scoped rule is fresh per rule, so the "
        "row shows the law spelling.",
        metta="!(sealed ($x) ($x $y))",
        python="m.eval(S.sealed(metta.Expression(V.x), metta.Expression(V.x, V.y)))[0]",
        differs=(
            "both freshen the second variable and keep the first, but the names "
            "differ: a variable built in Python comes back from the engine as "
            "`$_96674` rather than `$x`, so the two sides are alpha-equal and not "
            "string-equal"
        ),
    ),
    Entry(
        "capture", ("(-> Atom Atom)",), "Grounded", "matching", "absent",
        "Closing an atom over the current space. A Python function object already "
        "binds its engine and space, so the uses vanish; PeTTa does not implement "
        "the name.",
        metta="!(capture (+ 1 2))", unrun="PeTTa leaves the call unreduced",
    ),
    # --------------------------------------------------------- instructions
    Entry(
        "eval", ("(-> Atom Atom)",), "Symbol", "instructions", "method",
        "ONE step. `m.eval(term)` is the same one step and answers every result, "
        "and `space.eval(term)` is `evalc`, the same step in a named space.",
        metta="!(eval (+ 1 2))", python="m.eval(S['+'](1, 2))",
    ),
    Entry(
        "evalc", ("(-> Atom SpaceType Atom)",), "Symbol", "instructions", "method",
        "One step WITH an explicit context space, which is `space.eval(term)`: the "
        "signature IS term plus space.",
        metta="!(evalc (+ 1 2) &self)", python="space.eval(S['+'](1, 2))",
    ),
    Entry(
        "metta", ("(-> Atom Type SpaceType Atom)",), "Symbol", "instructions", "method",
        "The full interpreter, which is what CALLING does: a defined object called "
        "from Python evaluates, and `m.eval` on a built term is the same act.",
        metta="!(metta (+ 1 2) %Undefined% &self)", python="m.eval(S['+'](1, 2))",
    ),
    Entry(
        "chain", ("(-> Atom Variable Atom %Undefined%)",), "Symbol", "instructions", "dissolves",
        "Python assignment. Chain executes one instruction, binds, substitutes and "
        "continues, which is exactly `x = m.eval(t)[0]` followed by use of `x`.",
        metta="!(chain (+ 1 2) $x (foo $x))", python="x = m.eval(S['+'](1, 2))[0]\nS.foo(x)",
    ),
    Entry(
        "function", ("(-> Atom Atom)",), "Symbol", "instructions", "absent",
        "The core's function frame, which `return` closes. PeTTa's compiled "
        "definitions do not go through this instruction and it is not implemented.",
        metta="!(function (return 5))", unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "return", ("(-> $t $t)",), "Symbol", "instructions", "absent",
        "The core's return, paired with `function`: it is what closes the frame, "
        "so it only ever appears inside one.",
        metta="!(function (return (+ 2 3)))", unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "collapse-bind", ("(-> Atom Expression)", "(TU Expression)"), "Symbol", "instructions",
        "absent",
        "The deep-tier collapse that keeps each alternative's BINDINGS, "
        "`((a (bindings ...)) ...)`. It belongs to the bindings-carrying tier, "
        "never to the surface; PeTTa's engine has the bindings carrier "
        "(`answer_bindings`) but not this instruction.",
        metta="!(collapse-bind (superpose (a b)))",
        unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "superpose-bind", ("(-> Expression Atom)",), "Symbol", "instructions", "absent",
        "The inverse of `collapse-bind`: it restores each alternative WITH its "
        "recorded bindings, which is a different operation from `superpose`.",
        metta="!(superpose-bind ((a (bindings))))",
        unrun="PeTTa leaves the call unreduced",
    ),
    Entry(
        "_metta-call", ("(-> Atom Type SpaceType Atom)",), "Symbol", "instructions", "internal",
        "LeaTTa's grounded-call step inside `metta`.",
    ),
    Entry(
        "_metta-call-result", ("(-> Atom Atom Type SpaceType Atom)",), "Symbol", "instructions",
        "internal", "LeaTTa's grounded-call continuation inside `metta`.",
    ),
    Entry(
        "_minimal-foldl-atom",
        ("(-> Expression Atom Variable Variable Atom SpaceType %Undefined%)",), "Grounded",
        "instructions", "internal",
        "LeaTTa's internal fold behind `foldl-atom`, declared twice in the "
        "manifest: once in the prelude and once in a built-in module registry.",
    ),
]


def _family(names: dict[str, tuple[str, ...]], note: str) -> list[Entry]:
    """One entry per interpreter-internal name, all sharing one note."""
    return [
        Entry(name, types, "Symbol", "interpreter", "internal", note)
        for name, types in names.items()
    ]


#: LeaTTa's typed interpreter, `interpret` and its helper equations. These are
#: the mechanised interpreter written in MeTTa, which is what makes LeaTTa an
#: oracle rather than a second implementation; PeTTa's interpreter is Prolog,
#: so none of these names exists here and none is a surface operation.
_INTERPRET = {
    "interpret": ("(-> Atom Type SpaceType Atom)",),
    "interpret-args": ("(-> Atom Expression Expression Type SpaceType %Undefined%)",),
    "interpret-args-at": ("(-> Atom Expression Expression Type SpaceType Number %Undefined%)",),
    "interpret-args-ok": ("(-> Expression Atom)",),
    "interpret-args-tail": ("(-> Atom Atom Expression Expression Type SpaceType %Undefined%)",),
    "interpret-args-tail-at": (
        "(-> Atom Atom Expression Expression Type SpaceType Number %Undefined%)",
    ),
    "interpret-carrier-append": ("(-> Expression Expression SpaceType %Undefined%)",),
    "interpret-carrier-append-choice": (
        "(-> Bool Expression Expression SpaceType %Undefined%)",
    ),
    "interpret-dispatch": ("(-> Atom Type SpaceType Atom Atom)",),
    "interpret-expression": ("(-> Atom Type SpaceType %Undefined%)",),
    "interpret-expression-dispatch": ("(-> Bool Atom Type SpaceType Type %Undefined%)",),
    "interpret-expression-function": ("(-> Atom Atom)",),
    "interpret-expression-ok": ("(-> Atom Atom Atom)",),
    "interpret-expression-operator": ("(-> Atom Type SpaceType Atom Atom)",),
    "interpret-expression-selected": ("(-> Bool Atom %Undefined%)",),
    "interpret-expression-tuple": ("(-> Atom Atom)",),
    "interpret-func": ("(-> Atom Type Type SpaceType %Undefined%)",),
    "interpret-func-args": ("(-> Atom %Undefined%)",),
    "interpret-func-ok": ("(-> Atom Atom)",),
    "interpret-func-plan": ("(-> Atom Atom)",),
    "interpret-function-arg-data": ("(-> Atom Atom Expression Type Expression Atom)",),
    "interpret-function-check": ("(-> Atom Atom)",),
    "interpret-function-check-arg": ("(-> Bool Atom %Undefined%)",),
    "interpret-function-check-arg-return": ("(-> Bool Atom Type %Undefined%)",),
    "interpret-function-check-args": ("(-> Atom %Undefined%)",),
    "interpret-function-check-args-head": ("(-> Atom %Undefined%)",),
    "interpret-function-check-args-ready": ("(-> Bool Atom %Undefined%)",),
    "interpret-function-check-data": (
        "(-> Atom Expression Expression Type Type SpaceType Number Atom)",
    ),
    "interpret-function-check-result": ("(-> Atom Atom)",),
    "interpret-function-check-return": ("(-> Bool Atom %Undefined%)",),
    "interpret-function-check-tail": ("(-> Atom %Undefined%)",),
    "interpret-function-checked-data": ("(-> Expression Atom Atom)",),
    "interpret-function-return-data": ("(-> Atom Type Type Type Atom)",),
    "interpret-function-selected-data": ("(-> Atom Type Atom)",),
    "interpret-function-selection": ("(-> Atom Atom)",),
    "interpret-function-tail-data": ("(-> Atom Expression Bool Atom)",),
    "interpret-function-type": ("(-> Bool Atom %Undefined%)",),
    "interpret-function-type-classified": ("(-> Bool Atom %Undefined%)",),
    "interpret-function-type-data": ("(-> Type Expression Atom Atom)",),
    "interpret-function-type-ok": ("(-> Type Type Atom)",),
    "interpret-function-types": ("(-> Atom %Undefined%)",),
    "interpret-function-types-checked": ("(-> Atom %Undefined%)",),
    "interpret-function-types-data": (
        "(-> Expression Atom Type SpaceType Expression Bool Atom)",
    ),
    "interpret-function-types-end": ("(-> Atom %Undefined%)",),
    "interpret-function-types-end-classified": ("(-> Bool Atom %Undefined%)",),
    "interpret-function-types-tail": ("(-> Atom %Undefined%)",),
    "interpret-is-metatype": ("(-> Type Bool)",),
    "interpret-result-type": ("(-> Type Type)",),
    "interpret-tuple": ("(-> Atom Atom Atom)",),
    "interpret-type-cast": ("(-> Atom Type SpaceType %Undefined%)",),
    "interpret-type-cast-error-or-bad-type": ("(-> Atom Type Expression %Undefined%)",),
}

#: The minimal-interpreter half, `mi-*`: LeaTTa's MeTTa-written implementation
#: of the fourteen core instructions in terms of each other.
_MI = {
    "mi-apply-chain": ("(-> Atom Variable Atom Expression)",),
    "mi-apply-chain-collapsed": ("(-> %Undefined% Variable Atom Atom %Undefined%)",),
    "mi-apply-chain-collapsed-choice": (
        "(-> Bool Expression Variable Atom Atom %Undefined%)",
    ),
    "mi-apply-chain-empty-prepare": ("(-> Variable Atom Atom %Undefined%)",),
    "mi-apply-chain-prepare": ("(-> Expression Variable Atom Atom %Undefined%)",),
    "mi-apply-chain-prepare-choice": ("(-> Bool Expression Variable Atom Atom %Undefined%)",),
    "mi-apply-chain-prepare-head": (
        "(-> %Undefined% Expression Variable Atom Atom %Undefined%)",
    ),
    "mi-apply-chain-prepare-nonempty": ("(-> %Undefined% Variable Atom Atom %Undefined%)",),
    "mi-apply-chain-prepare-one": ("(-> %Undefined% Variable Atom Atom %Undefined%)",),
    "mi-apply-chain-prepare-tail": ("(-> %Undefined% Atom Expression %Undefined%)",),
    "mi-apply-chain-prepared": ("(-> Expression Atom)",),
    "mi-apply-chain-prepared-carrier": ("(-> %Undefined% Atom)",),
    "mi-apply-chain-prepared-one": ("(-> Atom Expression Atom)",),
    "mi-apply-chain-run": ("(-> %Undefined% Expression)",),
    "mi-apply-chain-run-result": ("(-> %Undefined% Expression)",),
    "mi-apply-chain-substituted": ("(-> Atom Atom)",),
    "mi-apply-chain-substituted-carrier": ("(-> %Undefined% Expression Atom %Undefined%)",),
    "mi-apply-chain-substitution-failed": ("(-> Atom)",),
    "mi-apply-unify": ("(-> Atom Atom Atom Atom Expression)",),
    "mi-apply-unify-attempt": ("(-> Atom Atom Atom Atom Atom %Undefined%)",),
    "mi-apply-unify-final": ("(-> Atom Atom %Undefined%)",),
    "mi-apply-unify-has-segment": ("(-> Atom Bool)",),
    "mi-apply-unify-hit": ("(-> Atom Atom)",),
    "mi-apply-unify-probe": ("(-> Atom Atom Atom Atom)",),
    "mi-apply-unify-probed": ("(-> %Undefined% Atom Atom Atom Atom %Undefined%)",),
    "mi-apply-unify-rigid": ("(-> Atom Atom Atom Atom %Undefined%)",),
    "mi-apply-unify-rigid-order": ("(-> Bool Atom Atom Atom Atom %Undefined%)",),
    "mi-apply-unify-rigid-result": ("(-> %Undefined% Expression)",),
    "mi-apply-unify-run": ("(-> Expression Expression)",),
    "mi-apply-unify-run-result": ("(-> %Undefined% Expression)",),
    "mi-chain": ("(-> Atom Variable Atom %Undefined%)",),
    "mi-chain-collapsed": ("(-> %Undefined% Variable Atom %Undefined%)",),
    "mi-chain-run": ("(-> %Undefined% Variable Atom %Undefined%)",),
    "mi-chain-substitute": ("(-> Atom Variable Atom %Undefined%)",),
    "mi-cons-atom": ("(-> Atom Expression Atom)",),
    "mi-decons-atom": ("(-> Expression Atom)",),
    "mi-function": ("(-> Atom %Undefined%)",),
    "mi-function-continue": ("(-> Atom Atom %Undefined%)",),
    "mi-function-loop": ("(-> Atom Atom %Undefined%)",),
    "mi-function-result": ("(-> Atom Atom)",),
    "mi-unify": ("(-> Atom Atom Atom Atom %Undefined%)",),
    "mi-unify-finish": ("(-> %Undefined% Atom Atom Atom Atom %Undefined%)",),
    "mi-unify-is-space": ("(-> Atom Atom Bool)",),
    "mi-unify-probe": ("(-> Atom Atom Atom Atom)",),
    "mi-unify-rigid-first": ("(-> Atom Atom Atom Atom %Undefined%)",),
    "mi-unify-rigid-first-result": ("(-> Atom Atom Atom Atom Atom %Undefined%)",),
    "mi-unify-rigid-second": ("(-> Atom Atom Atom Atom %Undefined%)",),
    "mi-unify-rigid-second-result": ("(-> Atom Atom Atom Atom Atom %Undefined%)",),
    "mi-unify-space": ("(-> SpaceType Atom Atom Atom %Undefined%)",),
    "mi-unify-space-carrier": ("(-> SpaceType Atom Atom Expression)",),
    "mi-unify-space-carriers": ("(-> Expression Expression)",),
    "mi-unify-space-finish": ("(-> %Undefined% Atom %Undefined%)",),
    "mi-unify-space-item": ("(-> Atom Atom)",),
    "mi-unify-structural": ("(-> Atom Atom Atom Atom %Undefined%)",),
}

#: The universal-machine half, `u-*`: LeaTTa's small-step machine over the
#: same instructions, with its instruction tags (`u-eval`, `u-chain`, ...) as
#: nullary symbols rather than operations.
_U = {
    "u-apply": ("(-> Expression Atom %Undefined%)",),
    "u-chain": ("Atom",),
    "u-chain-apply": ("(-> Expression Atom Variable Atom %Undefined%)",),
    "u-classify": ("(-> Atom %Undefined%)",),
    "u-classify-expression": ("(-> Atom Number Atom %Undefined%)",),
    "u-collapse-bind": ("Atom",),
    "u-cons-atom": ("Atom",),
    "u-context-space": ("Atom",),
    "u-decons-atom": ("Atom",),
    "u-equation": ("Atom",),
    "u-equation-apply": ("(-> Expression Atom %Undefined%)",),
    "u-equation-carrier": ("(-> Expression Atom %Undefined%)",),
    "u-eval": ("Atom",),
    "u-evalc": ("Atom",),
    "u-exhausted": ("(-> Atom Atom)",),
    "u-filter-carrier": ("(-> Expression %Undefined%)",),
    "u-filter-data": ("Atom",),
    "u-filter-head": ("(-> Atom %Undefined%)",),
    "u-filter-head-data": ("Atom",),
    "u-filter-held": ("(-> Atom %Undefined%)",),
    "u-freshen-equation": ("(-> SpaceType Atom %Undefined%)",),
    "u-function": ("Atom",),
    "u-hit": ("(-> Atom Atom)",),
    "u-metta": ("Atom",),
    "u-miss": ("Atom",),
    "u-native-apply": ("(-> Atom %Undefined%)",),
    "u-native-plan": ("(-> Atom Atom)",),
    "u-next-entry": ("Atom",),
    "u-reduce": ("(-> Expression Atom Atom %Undefined%)",),
    "u-reduce-carrier-append": ("(-> Expression Expression %Undefined%)",),
    "u-reduce-carrier-append-choice": ("(-> Bool Expression Expression %Undefined%)",),
    "u-reduce-carrier-classify": ("(-> Atom %Undefined%)",),
    "u-reduce-carrier-data": ("(-> Expression Atom)",),
    "u-reduce-carrier-entry": ("(-> Atom Atom)",),
    "u-reduce-carrier-held": ("(-> Expression Atom Atom %Undefined%)",),
    "u-reduce-carrier-list": ("(-> Expression Expression Atom %Undefined%)",),
    "u-reduce-carrier-list-choice": ("(-> Bool Expression Expression Atom %Undefined%)",),
    "u-reduce-carrier-one": ("(-> Expression Atom Atom %Undefined%)",),
    "u-reduce-carrier-one-classified": ("(-> Expression Atom Atom %Undefined%)",),
    "u-reduce-classified": ("(-> Atom Atom)",),
    "u-reduce-error": ("(-> Atom Atom)",),
    "u-reduce-held": ("(-> Expression Atom Atom %Undefined%)",),
    "u-reduce-held-classified": ("(-> Expression Atom Atom Atom %Undefined%)",),
    "u-reduce-term": ("(-> Atom Atom)",),
    "u-reduced": ("(-> Expression Atom)",),
    "u-run": ("(-> Expression Atom Atom %Undefined%)",),
    "u-run-held": ("(-> Expression Atom Atom %Undefined%)",),
    "u-run-term": ("(-> Atom Atom)",),
    "u-scan-data": ("Atom",),
    "u-scan-held": ("(-> Atom %Undefined%)",),
    "u-space": ("(-> Expression Atom)",),
    "u-space-add": ("(-> Atom Atom %Undefined%)",),
    "u-space-equality-theory": ("(-> Atom Expression)",),
    "u-space-eval": ("(-> Atom Atom Atom %Undefined%)",),
    "u-space-query": ("(-> Atom Atom Atom %Undefined%)",),
    "u-space-query-carrier": ("(-> Expression Atom Atom Expression)",),
    "u-space-query-choice": ("(-> Bool Expression Atom Atom SpaceType Expression)",),
    "u-space-query-scan": ("(-> Expression Atom Atom SpaceType Expression)",),
    "u-space-remove": ("(-> Atom Atom %Undefined%)",),
    "u-space-result": ("(-> Atom Atom Atom)",),
    "u-space-theory-choice": ("(-> Bool Expression Expression)",),
    "u-space-theory-head": ("(-> Atom Expression Expression)",),
    "u-space-theory-scan": ("(-> Expression Expression)",),
    "u-stuck": ("(-> Atom Atom)",),
    "u-superpose-bind": ("Atom",),
    "u-unify": ("Atom",),
    "u-unify-apply": ("(-> Expression Atom Atom Atom Atom %Undefined%)",),
    "u-unify-rigid": ("Atom",),
}

ENTRIES += _family(
    _INTERPRET,
    "LeaTTa's typed interpreter, written in MeTTa: `interpret` and the equations "
    "that implement it. This is the machinery that makes LeaTTa an oracle rather "
    "than a second implementation, and PeTTa writes its interpreter in Prolog, so "
    "none of these names is on either surface",
)
ENTRIES += _family(
    _MI,
    "LeaTTa's minimal interpreter, written in MeTTa: the fourteen core "
    "instructions implemented in terms of each other",
)
ENTRIES += _family(
    _U,
    "LeaTTa's universal small-step machine, written in MeTTa, with its instruction "
    "tags as nullary symbols",
)
