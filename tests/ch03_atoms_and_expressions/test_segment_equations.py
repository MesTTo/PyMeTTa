"""Purpose: pin equation-head sequence variables through both Python doors.

Assumes: ``metta`` creates an isolated engine whose source runner compiles
equations before executing each runnable.
Guarantees: nested capture, empty capture, RHS splicing, variadic top-level
arity, shortest-first splits, overlap, mixed-role projection, and
variable-headed dispatch match LeaTTa 9ea9f9d.
"""


def _groups(metta, source):
    """Run source and return every answer group as rendered MeTTa atoms."""
    return [[str(answer) for answer in group] for group in metta.run(source)]


def test_equation_head_segments_match_the_reference_matrix(metta):
    """The compiled source door matches every discriminating LeaTTa row."""
    groups = _groups(
        metta,
        """
        (: py-seg-nested (-> Atom Atom))
        (= (py-seg-nested (outer (inner left (:seg $xs) right) tail)) $xs)
        !(py-seg-nested (outer (inner left a b right) tail))

        (: py-seg-zero (-> Atom Atom))
        (= (py-seg-zero (head (:seg $xs) tail)) $xs)
        !(py-seg-zero (head tail))

        (: py-seg-splice (-> Atom Atom))
        (= (py-seg-splice (head (:seg $xs) tail))
           (rebuilt before (:seg $xs) after))
        !(py-seg-splice (head a b tail))

        (: py-seg-all (-> (%Rest% Atom) Atom))
        (= (py-seg-all (:seg $xs)) (quote $xs))
        !(py-seg-all)
        !(py-seg-all a b)

        (: py-seg-split (-> Atom Atom))
        (= (py-seg-split (row (:seg $before) SEP (:seg $after)))
           (quote (pair $before $after)))
        !(py-seg-split (row a SEP b SEP c))

        (: py-seg-overlap (-> Atom Atom))
        (= (py-seg-overlap (row (:seg $items))) segment-branch)
        (= (py-seg-overlap $leaf) ordinary-branch)
        !(collapse (py-seg-overlap (row a b)))

        (: py-seg-mixed (-> Atom Atom))
        (= (py-seg-mixed ((:seg $items) tag $items)) yes)
        !(py-seg-mixed (a b tag (a b)))
        !(py-seg-mixed (a b tag (a c)))
        """,
    )
    assert groups == [
        ["(a b)"],
        ["()"],
        ["(rebuilt before a b after)"],
        ["(quote ())"],
        ["(quote (a b))"],
        ["(quote (pair (a) (b SEP c)))", "(quote (pair (a SEP b) (c)))"],
        ["(segment-branch ordinary-branch)"],
        ["yes"],
        ["(py-seg-mixed (a b tag (a c)))"],
    ]


def test_variable_headed_calls_use_the_same_segment_equations(metta):
    """A function name produced at run time preserves all split answers."""
    groups = _groups(
        metta,
        """
        (: py-seg-dynamic (-> Atom Atom))
        (= (py-seg-dynamic (row (:seg $before) SEP (:seg $after)))
           (quote (pair $before $after)))
        !(py-seg-dynamic (row a SEP b SEP c))
        !(let $f py-seg-dynamic ($f (row a SEP b SEP c)))

        (= (py-seg-dynamic-all (:seg $items)) (quote $items))
        !(py-seg-dynamic-all)
        !(let $f py-seg-dynamic-all ($f))
        !(let $f py-seg-dynamic-all ($f a b))
        """,
    )
    splits = ["(quote (pair (a) (b SEP c)))", "(quote (pair (a SEP b) (c)))"]
    assert groups == [
        splits,
        splits,
        ["(quote ())"],
        ["(quote ())"],
        ["(quote (a b))"],
    ]


def test_reference_stratego_one_rule_rebuilds_the_successful_child(metta):
    """The reference rule terminates and splices the successful child result."""
    groups = _groups(
        metta,
        """
        (: py-seg-child (-> Atom Atom))
        (= (py-seg-child b) B)
        (= (py-seg-child $x) Empty)
        (: py-seg-one (-> Atom Atom Atom))
        (= (py-seg-one $strategy ((:seg $before) $child (:seg $after)))
           (function
             (chain (metta ($strategy $child) %Undefined% &self) $child-result
               (return ((:seg $before) $child-result (:seg $after))))))
        (= (py-seg-one $strategy $leaf) Empty)
        !(collapse (py-seg-one py-seg-child (a b c)))
        """,
    )
    assert groups == [["((a B c))"]]
