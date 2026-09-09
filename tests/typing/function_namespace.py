"""Purpose: verify the closed static function namespace through the public root.

Guarantees: ordinary names, composite operators and exact bracket access retain
their result types; unknown attributes remain errors rather than Any
[tested: mypy; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from typing import assert_type

from metta import Expression, Symbol, fn

assert_type(fn.car_atom, Symbol)
assert_type(fn.neg(2), Expression)
assert_type(fn["some-exact-head"], Symbol)
_missing = fn.no_such_function_in_the_catalog  # type: ignore[attr-defined]
