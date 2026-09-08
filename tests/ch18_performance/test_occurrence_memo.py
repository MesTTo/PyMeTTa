"""Purpose: preserve recursive answer multiplicity through memoization.

Guarantees: automatic and forced memoization preserve the plain recursive bag
    [tested: test_recursive_memo_coefficients; commit=WORKTREE].
"""

from collections import Counter

from metta import MeTTa


def test_recursive_memo_coefficients():
    """Repeated equal leaves multiply across independent recursive calls."""
    program = """
!(import! &self (library lib_memo))
(= (leaf) 1)
(= (leaf) 1)
(= (leaf) 2)
(= (coefficient $n)
   (if (== $n 0) (leaf)
       (+ (coefficient (- $n 1)) (coefficient (- $n 1)))))
"""
    expected = [Counter({1: 2, 2: 1})]
    for _ in range(3):
        next_bag = Counter()
        for left, left_count in expected[-1].items():
            for right, right_count in expected[-1].items():
                next_bag[left + right] += left_count * right_count
        expected.append(next_bag)
    assert [bag.total() for bag in expected] == [3, 9, 81, 6561]
    with MeTTa() as context:
        for declaration, memoized in (("(cache coefficient refuse)", False),
                                      ("", True), ("(cache coefficient force)", True)):
            with context.space() as space:
                space.run(program)
                try:
                    if declaration:
                        space.run(f"!(add-atom &metta {declaration})")
                    for depth, bag in enumerate(expected):
                        actual = Counter(int(str(atom)) for atom in space.eval(f"(coefficient {depth})"))
                        assert actual == bag, (declaration, depth)
                    assert space.eval("(is-memoized coefficient)") == [memoized]
                finally:
                    if declaration:
                        space.run(f"!(remove-atom &metta {declaration})")
