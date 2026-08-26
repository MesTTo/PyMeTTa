<!--
Purpose: state the answer and resource laws shared by the Python twin corpus.
Guarantees: the fib depth divergence remains concrete, operational, and separate from answer equality.
[tested: test_twin_docs_state_python_stack_engine_lco_and_answer_equality,
test_twin_depth_divergence_is_operational_not_an_answer_difference; commit=ee43d4a0585593b4f40d0c3c0557db8214688829]
-->

# Twin depth and fuel

Every Python twin states the same answer claim as its paired `examples/` program, but the two routes need not spend the same execution resource. In `basics/fib.py`, `fib.py(n)` recurses on Python's stack and is bounded by `sys.getrecursionlimit()`, while the compiled equation runs with the engine's last-call optimization (LCO) and spends `max-stack-depth` reduction fuel instead of Python frames. With the test-set recursion limit of 80, both routes answer 55 at `n=10`; at `n=100`, `.py` raises `RecursionError` while the engine answers 354224848179261915075. Whenever both routes finish, they must answer the same value, so this is an operational depth divergence and never an answer divergence.
