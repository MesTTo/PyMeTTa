"""examples/ch08-data/08-01-atoms-lists-and-folds/18-sorting_and_deduplication.metta in Python: four ways to tidy a collection.

`sort`, `msort` and `list_to_set` keep their Prolog underscores and come
through the exact subscript door; `sort-atom` is a MeTTa name and takes the
host-convention map.

`alpha-unique` works over an answer STREAM rather than an expression, so its
Python spelling is an answer LIST: `m.answers(fn.alpha_unique(fn.superpose(...)))`
is the collapse, because a list IS what collapse answers. Its answers carry
fresh variables, so the claims read their heads and their length rather than
comparing variable names the engine mints.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, fn


def twin(m):
    """Order, deduplicate, drop an item, and deduplicate up to renaming."""
    # COST, recorded rather than hidden: this twin costs 16159 against the
    # example's 11629, past the 10% band and with no compiled definition to
    # earn the band's per-definition credit. The gap is the Python boundary
    # rather than anything this file does differently -- twenty calls cross
    # it where the example's twenty forms are compiled into one program --
    # and it is the library's to close, not this twin's
    # [measured 2026-09-07: python extensions/python/tools/twin_coverage.py
    # --measure --rounds 3 on this file's own pair].
    ordered, kept, merged = m.fn["sort"], m.fn.sort_atom, m.fn["msort"]
    to_set, exclude = m.fn["list_to_set"], m.fn.exclude_item

    # `sort` is the standard order of terms with duplicates REMOVED;
    # `sort-atom` and `msort` order and keep them.
    assert ordered((3, 1, 2, 1)) == [(1, 2, 3)]
    assert kept((3, 1, 2, 1)) == [(1, 1, 2, 3)]
    assert merged((3, 1, 2, 1)) == [(1, 1, 2, 3)]
    assert ordered(()) == [()]

    # The order is the STANDARD order of terms, so mixed content still has
    # one total order: numbers, then strings, then names.
    assert ordered((S.b, S.a, 10, 2, G_TEXT)) == [(2, 10, G_TEXT, S.a, S.b)]

    # `list_to_set` removes duplicates and keeps the ORIGINAL order.
    assert to_set((S.b, S.a, S.b, S.c, S.a)) == [(S.b, S.a, S.c)]
    assert to_set((3, 1, 2, 1)) == [(3, 1, 2)]
    assert to_set(()) == [()]

    # `exclude-item` drops one named item wherever it appears, item first.
    assert exclude(2, (1, 2, 3, 2)) == [(1, 3)]
    assert exclude(S.x, (1, 2, 3)) == [(1, 2, 3)]
    assert exclude(1, (1, 1, 1)) == [()]

    # `alpha-unique` deduplicates an answer stream up to a consistent renaming
    # of variables; `unique` compares atoms exactly, so two answers differing
    # only in a variable's name both survive there and one survives here.
    varied = (S.f(V.x), S.f(V.y), S.g(V.z))
    assert len(m.answers(fn.unique(fn.superpose(varied)))) == 3
    alpha = m.answers(fn.alpha_unique(fn.superpose(varied)))
    assert [answer[0] for answer in alpha] == [S.f, S.g]

    # A ground answer is only alpha-equivalent to itself, so on ground data
    # the two agree.
    assert m.answers(fn.alpha_unique(fn.superpose((1, 2, 1, 3)))) == [1, 2, 3]
    assert m.answers(fn.unique(fn.superpose((1, 2, 1, 3)))) == [1, 2, 3]

    # And a variable answer is not the same as the ground one it would unify
    # with: (f $x) and (f 1) are two answers, not one.
    mixed = m.answers(fn.alpha_unique(fn.superpose((S.f(V.x), S.f(V.y), S.f(1)))))
    assert len(mixed) == 2
    assert mixed[1] == S.f(1)


#: The one string this file compares, as ground data rather than as source.
from metta import G  # noqa: E402  -- the value below is data the claims share

G_TEXT = G("s")


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 16159 inferences, 1.3895x the example's 11629; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
BUDGET = 16159
