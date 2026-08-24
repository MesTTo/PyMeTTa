"""examples/data/foldallmatch.metta in Python: folding a match, and folding a let.

Both claims fold something that answers more than once, and neither generator
may be run before the fold sees it: `foldall` reads its generator as a term and
enumerates it itself, so a list of rows the subscript door already collected
would be a value rather than a generator.

That is what a compiled body is for. Inside one, `match(m, pattern, template)`
is LOWERED rather than executed, so the first generator is written as the Python
it means and stored as the term foldall then enumerates. `fn.add` is the
aggregator mentioned by its operator word, `+`.

The second generator's `let` is load-bearing and stays, which is worth the
sentence because it does not look load-bearing. `(let $x (f) (+ 1 $x))` scopes
the two answers INSIDE the generator, where `(+ 1 (f))` lets them escape:
measured, the stored form `(foldall + (+ 1 (f)) 0)` answers 2 and 3 rather than
5, because the branching reaches back out and the whole fold runs once per
answer. There is no Python statement position inside another term's argument,
so that one binding is written as the term it is.

The template is where the arithmetic happens, one addition per answer, so each
fold sees 2 and 3 and answers 5.
"""

from metta import S, V, fn, match

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
BUDGET = 1


def twin(m):
    """Fold a query's rows, then fold a function's two answers."""
    m += [(S.kb, 1), (S.kb, 2)]                  # (kb 1) and (kb 2)

    @m.define
    def f():                                     # (= (f) 1)
        yield 1                                  # (= (f) 2)
        yield 2

    @m.define
    def bumped():                                # (= (bumped)
        return S.foldall(fn.add,                 #    (foldall +
                         match(m, S.kb(V.n), V.n + 1),  # (match &self (kb $n) (+ $n 1))
                         0)                      #     0))

    @m.define
    def raised():                                # (= (raised)
        return S.foldall(fn.add,                 #    (foldall +
                         S.let(V.x, S.f(), 1 + V.x),  # rung: this `let` scopes the branching inside foldall's generator slot, where no Python statement can stand
                         0)                      # (let $x (f) (+ 1 $x)), then 0

    assert bumped().one() == 5                   # [5]
    assert raised().one() == 5                   # [5]
