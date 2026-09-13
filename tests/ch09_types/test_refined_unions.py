"""Purpose: check native refined unions across Python call boundaries.

Guarantees:
  - native arrow edits change which borrowed values a compiled function
    accepts [tested: test_native_union_edits_change_python_call_admission;
    commit=7e2de138f59cd8137f55dce9e7f2f955906c76d1]
  - native refined union results preserve admitted values and filter the
    other results [tested: test_native_union_results_check_the_returned_value;
    commit=7e2de138f59cd8137f55dce9e7f2f955906c76d1]
"""

from collections import UserDict, UserList, abc
from typing import Any

import pytest

from metta import G, MeTTa, S
from metta._errors.errors import MettaResultError


def test_native_union_edits_change_python_call_admission():
    """The stored arrow owns membership after Python source compilation."""
    sequence = S["|"](S.Expression, S.Annotated(S.Grounded, S.Predicate(G(abc.Sequence.__instancecheck__))))
    mapping = S["|"](S.Expression, S.Annotated(S.Grounded, S.Predicate(G(abc.Mapping.__instancecheck__))))
    with MeTTa() as context:
        space = context.self

        @space.define
        def count(items: sequence) -> int:
            return len(items)

        assert list(count(G(UserList([1, 2])))) == [2]
        space.remove(S[":"](S.count, S["->"](sequence, S.Number)))
        space.add(S[":"](S.count, S["->"](mapping, S.Number)))
        assert list(count(G(UserDict(one=1, two=2)))) == [2]
        with pytest.raises(MettaResultError, match="BadArgType"):
            space.eval(S.count(G(UserList([1, 2]))), on_error="abort")


def test_native_union_results_check_the_returned_value():
    """Return checking reads the host value rather than only its class name."""
    result = S["|"](S.Expression, S.Annotated(S.Grounded, S.Predicate(G(abc.Sequence.__instancecheck__))))
    with MeTTa() as context:
        space = context.self

        @space.define
        def identity(value: Any) -> result:
            return value

        value = UserList([1, 2])
        assert identity(G(value)).one() is value
        assert list(identity(G(42))) == []
