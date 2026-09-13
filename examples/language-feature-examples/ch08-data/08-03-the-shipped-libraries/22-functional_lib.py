"""Purpose: the functional and iteration utilities from Python.

Beside them are lib_patrick's four idioms, which this library grew out of.

A collection is a tuple, a function argument is the symbol of a defined
function or a written lambda, and a held body is a written expression, so each
claim reads as its MeTTa twin does with the parentheses moved. The loop with
state keeps its counter in a named space, whose handle crosses into the two
compiled helpers as the argument it is; `odd?` keeps its question mark through
the explicit `name=`, because no Python identifier can spell it, and the three
helpers take their arithmetic and comparisons by the engine's words, `fn.mul`,
`fn.mod`, `fn.eq` and `fn.gt`, where Python's own operators on an unannotated
parameter would cross to the host once per element.

Guarantees: the same claims as 22-functional_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/22-functional_lib.metta; commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import FALSE, TRUE, Expression, G, S, V, fn, if_, lib, match
from metta._errors.errors import MettaError


def twin(m):
    """Zip, slice, flatten, partition, group, sort, scan, unfold, pipe and loop."""
    m += lib.functional
    # lib_unicode is imported for one claim below, whose test is a head the
    # library declares deterministic: that is the case a verdict has to be read
    # rather than asked for.
    m += lib.unicode

    # The three helpers take their arithmetic and comparisons by the engine's
    # WORDS, so each body is the MeTTa form it stands for rather than a host
    # operator crossing once per element.
    @m.define
    def double(x):
        return fn.mul(2, x)

    @m.define(name="odd?")
    def odd(x):
        return fn.eq(1, fn.mod(x, 2))  # engine equality is intentional

    @m.define
    def grade(score):
        return S["pass"] if fn.gt(score, 50) else S.fail

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    def rows(answers):
        """One answer's expression of expressions, as a list of tuples."""
        return [tuple(row) for row in answers.one()]

    # `zip` pairs corresponding elements and stops at the shorter collection, so
    # a long one zipped with a short one is the short one's length. `unzip`
    # inverts it.
    assert rows(m.fn.zip((1, 2, 3), (S.a, S.b, S.c))) == [(1, S.a), (2, S.b), (3, S.c)]
    assert rows(m.fn.zip((1, 2, 3), (S.a, S.b))) == [(1, S.a), (2, S.b)]
    assert list(m.fn.zip((), (S.a,)).one()) == []
    assert rows(m.fn.unzip(((1, S.a), (2, S.b)))) == [(1, 2), (S.a, S.b)]
    assert rows(m.fn.unzip(m.fn.zip((1, 2), (S.a, S.b)).one())) == [(1, 2), (S.a, S.b)]
    assert refused(S.unzip((1,)))

    # `drop` is the suffix. The PREFIX is lib_combinatorics' `takeK`, so this
    # library adds no second spelling of it.
    assert list(m.fn.drop((1, 2, 3, 4), 2).one()) == [3, 4]
    assert list(m.fn.drop((1, 2), 5).one()) == []
    assert list(m.fn.drop((1, 2), 0).one()) == [1, 2]

    # `chunk` cuts a collection into pieces, the last one short when the size
    # does not divide the length. `window` slides instead of cutting, so
    # consecutive windows overlap by all but one element.
    assert rows(m.fn.chunk((1, 2, 3, 4, 5), 2)) == [(1, 2), (3, 4), (5,)]
    assert rows(m.fn.chunk((1, 2, 3, 4), 2)) == [(1, 2), (3, 4)]
    assert list(m.fn.chunk((), 2).one()) == []
    assert rows(m.fn.window((1, 2, 3, 4), 2)) == [(1, 2), (2, 3), (3, 4)]
    assert rows(m.fn.window((1, 2, 3), 3)) == [(1, 2, 3)]
    assert list(m.fn.window((1, 2), 3).one()) == []
    assert refused(S.chunk((1, 2), 0))
    assert refused(S.window((1, 2), 0))

    # `flatten-once` removes ONE level of nesting and `flatten-deep` removes
    # every one, which is the difference between concatenating and collecting
    # the leaves. Both say the depth in the name, because the bare name
    # `flatten` is the host Prolog's own every-level flatten and the library
    # leaves it alone.
    assert list(m.fn.flatten_once(((1, 2), (3,), (), 4)).one()) == [1, 2, 3, 4]
    # An inner collection's own nesting is data one level does not touch.
    assert list(m.fn.flatten_once((((1, (2,)),), 3)).one()) == [Expression((1, Expression((2,)))), 3]
    assert list(m.fn.flatten_deep(((1, (2, (3,))), 4)).one()) == [1, 2, 3, 4]
    assert list(m.fn.flatten_deep((((),),)).one()) == []

    # `partition` splits on a test and loses nothing: whatever the test does not
    # answer True for lands in the second side.
    assert rows(m.fn.partition(S["odd?"], (1, 2, 3, 4))) == [(1, 3), (2, 4)]
    assert rows(m.fn.partition(S["odd?"], ())) == [(), ()]
    assert rows(m.fn.partition(S["|->"]((V.x,), S.gt(V.x, 10)), (1, 2))) == [(), (1, 2)]
    # The test's verdict is READ and compared, never threaded into the call as an
    # expected answer, so a test whose own head is declared deterministic answers
    # False rather than failing: this one is lib_unicode's, over one-character
    # strings.
    assert rows(m.fn.partition(S["|->"]((V.c,), S.unicode_is(V.c, S.letter)),
                               (G("a"), G("1")))) == [(G("a"),), (G("1"),)]

    # `group-by` gathers by what a key function answers, keys in
    # first-appearance order and members in the collection's order, so grouping
    # needs no sort.
    assert rows(m.fn.group_by(S["odd?"], (1, 2, 3, 4))) == [(True, Expression((1, 3))), (False, Expression((2, 4)))]
    assert rows(m.fn.group_by(S.grade, (80, 20, 90))) == [(S["pass"], Expression((80, 90))), (S.fail, Expression((20,)))]
    assert list(m.fn.group_by(S["odd?"], ()).one()) == []

    # `sort-by` orders by the key and is STABLE, so equal keys keep their order.
    assert list(m.fn.sort_by(S.double, (3, 1, 2)).one()) == [1, 2, 3]
    second = S["|->"]((V.p,), S.index_atom(V.p, 1))
    assert rows(m.fn.sort_by(second, ((S.b, 1), (S.a, 1), (S.c, 0)))) == [(S.c, 0), (S.b, 1), (S.a, 1)]

    # `scan` is a fold that answers its running results, so a prefix sum is scan
    # with +. The answer is one longer than the input, because the start is
    # first.
    assert list(m.fn.scan(S["+"], 0, (1, 2, 3)).one()) == [0, 1, 3, 6]
    assert list(m.fn.scan(S["+"], 0, ()).one()) == [0]
    consing = S["|->"]((V.acc, V.x), S.cons_atom(V.x, V.acc))
    assert rows(m.fn.scan(consing, (), (1, 2))) == [(), (1,), (2, 1)]

    # `unfold` is the opposite of a fold: a seed grows into a collection while
    # the step answers (Value NextSeed), and stops when it answers nothing.
    counting = S["|->"]((V.n,), if_(S.lt(V.n, 4), Expression((V.n, V.n + 1)), S.empty()))
    assert list(m.fn.unfold(counting, 1).one()) == [1, 2, 3]
    assert list(m.fn.unfold(S["|->"]((V.n,), S.empty()), 1).one()) == []

    # `pipe` applies functions left to right, which is the reading order;
    # lib_patrick's `compose` applies them right to left, the mathematical
    # order. The collection of functions is HELD, so it is not read as a call.
    assert m.fn.pipe((S.double, S.double), 3) == [12]
    assert m.fn.pipe((), 3) == [3]
    assert m.fn.pipe((S.double, S["odd?"]), 3) == [False]

    # `apply-to` turns a collection of arguments into a call, which is what a
    # fold over a variable number of arguments needs.
    assert m.fn.apply_to(S["+"], (1, 2)) == [3]
    assert m.fn.apply_to(S.double, (5,)) == [10]

    # The three control forms hold their body: `repeat` runs it a fixed number
    # of times, `while` runs it until its condition stops answering True, and
    # `unless` runs it when the condition answers False.
    assert list(m.fn.repeat(3, S["+"](3, 4))) == [7, 7, 7]
    assert list(m.fn.repeat(0, S["+"](3, 4))) == []
    # The condition is MeTTa's own Bool atom where it is written as a literal:
    # a Python bool would be a host value crossing into a held parameter.
    assert list(m.fn.unless(FALSE, S["+"](1, 1))) == [2]
    assert list(m.fn.unless(TRUE, S["+"](1, 1))) == []
    assert list(m.fn["while"](FALSE, S.never)) == []

    # A while loop with state: the counter lives in the space, the condition
    # reads it and the body advances it, so the loop ends when the space says
    # so. Held parameters are what make this work: an evaluated body would run
    # once.
    counter = metta.space(S.ticks)
    counter += S.count(0)

    @m.define
    def ticks():
        # (= (ticks) (car-atom (collapse (match &ticks (count $n) $n))))
        return fn.car_atom(S.collapse(match(counter, S.count(V.n), V.n)))  # rung: `collapse` is list(), which a compiled body has no lowering for (P14.4)

    @m.define
    def tick():
        # (= (tick) (let $now (ticks) (let $gone (remove-atom &ticks (count $now))
        #             (let $next (+ $now 1) (let $added (add-atom &ticks (count $next)) $next)))))
        now = ticks()
        _gone = fn.remove_atom(counter, S.count(now))
        after = fn.add(now, 1)
        _added = fn.add_atom(counter, S.count(after))
        return after

    assert list(m.fn["while"](S.lt(S.ticks(), 3), S.tick())) == [1, 2, 3]
    assert m.fn.ticks() == [3]

    # And lib_patrick's own four, unchanged, from their own library.
    m += lib.patrick
    assert m.fn.compose((S.double, S.double), (3,)) == [12]
    # The same composition written both ways: double then odd? left to right is
    # odd? after double right to left, and 6 is even either way.
    assert m.fn.compose((S["odd?"], S.double), (3,)) == [False]
    assert m.fn["@"](V.x, S["+"](1, 2)) == [3]
    assert m.fn["for"](V.x, (1, 2, 3), V.x * 10) == [10, 20, 30]
    step = S["|->"](Expression((V.i, V.s)), V.s + V.i)
    assert m.fn.iterate(0, 3, 0, step) == [3]

    @m.define
    def branch_add(a, b):
        yield fn.add(a, b)
        yield fn.add(1, fn.add(a, b))

    @m.define
    def branch_key(x):
        yield fn.mod(x, 2)
        yield fn.add(2, fn.mod(x, 2))

    @m.define
    def branch_step(seed):
        yield (seed, fn.add(seed, 1)) if fn.lt(seed, 2) else fn.empty()
        yield (fn.add(seed, 10), fn.add(seed, 1)) if fn.lt(seed, 2) else fn.empty()

    @m.define
    def increment_function():
        yield lambda x: fn.add(x, 1)
        yield lambda x: fn.add(x, 2)

    assert list(m.fn.scan(S.branch_add, 0, (1, 2))) == [
        (0, 1, 3), (0, 1, 4), (0, 2, 4), (0, 2, 5),
    ]
    assert list(m.fn.unfold(S.branch_step, 0)) == [(0, 1), (0, 11), (10, 1), (10, 11)]
    assert list(m.fn.group_by(S.branch_key, (0, 1))) == [
        ((0, (0,)), (1, (1,))), ((0, (0,)), (3, (1,))),
        ((2, (0,)), (1, (1,))), ((2, (0,)), (3, (1,))),
    ]
    assert list(m.fn.pipe((S.increment_function(), S.increment_function()), 0)) == [2, 3, 3, 4]
    assert list(m.fn.apply_to(S.increment_function(), (1,))) == [2, 3]
    both = S["|->"]((V.x,), S.superpose((FALSE, TRUE)))
    none = S["|->"]((V.x,), S.empty())
    assert rows(m.fn.partition(both, (1, 2))) == [(1, 2), ()]
    assert rows(m.fn.partition(none, (1, 2))) == [(), (1, 2)]
    assert list(m.fn.scan(S["|->"]((V.a, V.b), S.empty()), 0, (1,))) == []
    malformed = S["|->"]((V.n,), if_(S.eq(V.n, 0), (1, 2, 3), S.empty()))
    assert refused(S.unfold(malformed, 0))

    arithmetic, error_data = S["+"](1, 2), S.Error(S.a, S.b)
    literal = (arithmetic, error_data)
    assert rows(m.fn.zip(S.quote(literal), (S.a, S.b))) == [
        (arithmetic, S.a), (error_data, S.b),
    ]
    assert rows(m.fn.unzip(S.quote(((S["+"], S.a), (S.Error, S.b))))) == [
        (S["+"], S.Error), (S.a, S.b),
    ]
    assert list(m.fn.flatten_once(S.quote(((arithmetic,), error_data))).one()) == [
        arithmetic, S.Error, S.a, S.b,
    ]
    assert list(m.fn.flatten_deep(S.quote(((arithmetic,), error_data))).one()) == [
        S["+"], 1, 2, S.Error, S.a, S.b,
    ]
    expression = S["|->"]((V.x,), S.eq(S.get_metatype(V.x), S.Expression))
    assert rows(m.fn.partition(expression, S.quote((*literal, 3)))) == [literal, (3,)]
    metatype = S["|->"]((V.x,), S.get_metatype(V.x))
    assert m.fn.group_by(metatype, S.quote(literal)) == [((S.Expression, literal),)]
    constant = S["|->"]((V.x,), 0)
    assert m.fn.sort_by(constant, S.quote(literal)) == [literal]
    item = S["|->"]((V.acc, V.item), S.quote(V.item))
    assert m.fn.scan(item, S.a, S.quote(literal)) == [(S.a, *literal)]
    assert rows(m.fn.chunk(S.quote(literal), 1)) == [(arithmetic,), (error_data,)]
    assert rows(m.fn.window(S.quote(literal), 2)) == [literal]
    identity = S["|->"]((V.data,), S.quote(V.data))
    assert m.fn.apply_to(identity, S.quote((arithmetic,))) == [arithmetic]
    assert m.fn.pipe((identity,), S.quote(arithmetic)) == [arithmetic]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 51 claims cover the fourteen registered heads,
#: the three held control forms and lib_patrick's four idioms; the example pays
#: 127,108 inferences for the same work, and the twin's surplus is the three
#: compiled helpers and the loop's two, each a definition the example writes
#: as an equation and the twin compiles from a Python body
#: [measured 2026-09-12: 135975 inferences, minimum of three serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --measure
#: --rounds 3 examples/ch08-data/08-03-the-shipped-libraries/22-functional_lib.metta;
#: fixture=lib_functional at its functional commit, artifacts purged before
#: the run; commit=a2a80061cd8264d8f714b14c76b94d00f44a0755].
#: RE-PINNED 2026-09-12, 135975 to 134567 (-1408), lib_patrick keeps its own
#: four idioms and does not import this library, so the example asks for both
#: halves itself and pays the second import once [measured 2026-09-12: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=a2a80061cd8264d8f714b14c76b94d00f44a0755].
#: RE-PINNED 2026-09-12, 134567 to 151546 (+16979), the partition claim that
#: reads its test's verdict rather than threading an expected answer, and the
#: lib_unicode import it needs [measured 2026-09-12: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b2a180eace9ff7e51677b1a40a8d6374ee05972b].
#: RE-PINNED 2026-09-13, 151546 to 1091943: collection operations now compose
#: MeTTa matching, folds and application; segment continuations are protected
#: compiler helpers. The example measures 1074085 for the same claims
#: [measured: 1091943 inferences; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3 examples/ch08-data/08-03-the-shipped-libraries/22-functional_lib.metta;
#: fixture=minimum of three serial fresh processes after purging engine/lib QLF;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 1091943 to 1093280 (+1337), The validated range
#: continuation now lives in the private support file rather than appearing as
#: a public library head. The import adds its measured loading cost without
#: changing the continuation body [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 1093280 to 1093245 (-35), Math and Statistics derive
#: their recipes from MeTTa equations; Statistics consolidates finite laws and
#: adds reflective claims. Their collection dependencies share the proper
#: finite expression boundary in lib/_support/collections_data.pl [measured
#: 2026-09-13: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 1093245

#: DIVERGED 2026-09-12, the example holds 1 atom the twin does not (1 =) and
#: the twin holds 1 atom the example does not (1 =): the loop's tick helper is
#: a sequence of four Python statements, which compile to four nested one-
#: binding let* forms where the example writes four nested let forms; the
#: bindings, the effects and the answer are the same [measured 2026-09-12: the
#: two stored-atom surpluses, one fresh process per side; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=a2a80061cd8264d8f714b14c76b94d00f44a0755].
#: DIVERGED 2026-09-13, the example holds 5 atoms the twin does not (2 :, 3 =)
#: and the twin holds 5 atoms the example does not (2 :, 3 =): The tick helper
#: still compiles Python assignments to nested let* while the example writes
#: nested let. The two Python lambda bodies yielded by increment_function
#: consume two generated names before later calls, shifting the otherwise
#: identical partition and unfold specializations from lambda_67 and lambda_66
#: to lambda_69 and lambda_68; the branch and literal claims verify both paths
#: [measured 2026-09-13: the two stored-atom surpluses, one fresh process per
#: side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
DIVERGENCE = "657f0b5df5fb6e201a726937590d125fdbc13e415a6611d6956683c38278ae62"
