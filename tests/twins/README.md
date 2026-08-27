<!--
Purpose: state the answer and resource laws shared by the Python twin corpus.
Guarantees: the fib depth divergence remains concrete, operational, and separate from answer equality.
[tested: test_twin_docs_state_python_stack_engine_lco_and_answer_equality,
test_twin_depth_divergence_is_operational_not_an_answer_difference; commit=ee43d4a0585593b4f40d0c3c0557db8214688829]
Guarantees: the pricing block sits at the end of every twin and a re-pin appends there.
[tested: test_twin_docs_state_where_the_pricing_block_lives,
test_the_layout_check_passes_the_shipped_twins,
test_a_repin_appends_below_the_code_and_rewrites_the_number;
commit=845d851b7241ccea3b6a13f532172945bf6d8d9e]
-->

# Where a twin's pricing lives

A twin reads: module docstring, imports, then the example. `BUDGET`, `RUNG` and
the `#:` re-pin chain that documents them sit at the END of the file, and a
re-pin APPENDS one more paragraph there. The chain never shrinks and every
merge adds to it, so at the top it buried what the file is for:
`basics/identity.py` opened with 297 comment lines before its first statement.

Re-pin through the door rather than by hand, which is what put the chain on top
in the first place:

```sh
python bindings/python/tools/twin_coverage.py --repin \
    --reason "the mechanism that moved the count" examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/01-identity.metta
```

It measures min-of-three in fresh processes, writes the paragraph under the
existing chain, rewrites the number, and refuses a twin whose declarations are
still above its code, an empirical envelope, or a move with no stated
mechanism. The evidence tag it writes carries `commit=WORKTREE`, so
`RELEASE=1 python tests/check_evidence_tags.py` refuses a tree that ships one
before the provenance pin.

# Twin depth and fuel

Every Python twin states the same answer claim as its paired `examples/` program, but the two routes need not spend the same execution resource. In `basics/fib.py`, `fib.py(n)` recurses on Python's stack and is bounded by `sys.getrecursionlimit()`, while the compiled equation runs with the engine's last-call optimization (LCO) and spends `max-stack-depth` reduction fuel instead of Python frames. With the test-set recursion limit of 80, both routes answer 55 at `n=10`; at `n=100`, `.py` raises `RecursionError` while the engine answers 354224848179261915075. Whenever both routes finish, they must answer the same value, so this is an operational depth divergence and never an answer divergence.
