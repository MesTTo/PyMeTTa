"""Purpose: keep cached native programs valid when generated code retires.

Guarantees:
  - publishing an atom-delivery operation preserves earlier native callable
    answers across segment arities [tested:
    test_operation_publication_preserves_cached_native_callables;
    commit=bdf3a42670d84dc9925c5db7e767415c1e8a5c19]
"""

from collections.abc import Callable

import pytest

from metta import Atom, Expression, MeTTa, S, V, convert


@pytest.mark.parametrize("arity", (0, 1, 5))
def test_operation_publication_preserves_cached_native_callables(arity):
    """The callable's source is unchanged while its generated code is retired."""
    with MeTTa() as context:
        m = context.self
        parameters = [V[f"item{index}"] for index in range(arity)]
        m.add(S[":"](S["cached-source"], S["->"](*([S.Atom] * arity), S.Atom)))
        m.add(S["="](S["cached-source"](*parameters), S.payload(*parameters)))
        values = tuple(range(arity))
        expected = S.payload(*values)
        callback = convert.build(S["cached-source"], Callable[..., Atom], space=m)
        assert callback(*values) == expected

        def unrelated(value: Atom) -> Atom:
            return value

        m.op(unrelated, effect="oracleIO", declarations=[S.arguments(S.unrelated, S.atoms)])
        m.add(S.internal(S.unrelated))
        assert callback(*values) == expected
        assert m.eval(Expression([callback.__metta__(), *values])) == [expected]
