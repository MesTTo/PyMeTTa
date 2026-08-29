"""Purpose: lower a symbolic tensor identity to one numeric GEMM operation.

Assumes: NumPy is present. It is not a dependency of the library, so this
  program skips where it is absent, the way every other integration example
  does.
Guarantees:
  - the declared top-down lowering rewrites ``MM(T(T(x)), y)`` to one matmul
    call, and tropical ``under=`` carries the checked numeric result
    [tested: test_a_gallery_program_runs; commit=4b6f6bf075e80f794ebcb46a5748dba46dcd3522]
Owns resources: one named space plus one pure operation registration; an
  explicit unregister call and drop() release them after evaluation, while
  process exit releases the process-local lowering registry after failure.
"""

from unittest.mock import patch

from _common import claim, doctest, done, skip

try:
    import numpy as np
except ImportError:
    skip("numpy is not installed")

from metta import Expression, Grounded, MeTTa, S, equation, rules, tropical


@rules
def gallery_linalg(left, right):
    """Cancel a double transpose and select the GEMM primitive."""
    yield equation(S.MM(S.T(S.T(left)), right)).to(S.gallery_gemm(left, right))


def matrix_cells(rows: int, columns: int) -> int:
    """Count the scalar cells in a dense tensor.

    >>> !(matrix-cells 2 3)
    [6]
    """
    return rows * columns


engine = MeTTa()
space = engine.space("&gallery-tensors")
cells = space.define(matrix_cells)
doctest("tensor shape doctest", cells)


@space.pure
def gallery_gemm(left, right):
    """Multiply two structural Matrix atoms through exactly one NumPy GEMM."""
    left_rows = _matrix_rows(left)
    right_rows = _matrix_rows(right)
    if not left_rows or not right_rows:
        message = "gallery-gemm needs two nonempty matrices"
        raise ValueError(message)
    left_columns = len(left_rows[0]) if left_rows else 0
    if left_columns != len(right_rows):
        msg = (
            f"incompatible GEMM shapes: left has {left_columns} columns, "
            f"right has {len(right_rows)} rows"
        )
        raise ValueError(msg)
    product = np.matmul(np.asarray(left_rows), np.asarray(right_rows))
    return S.Matrix(*(S.Row(*(value.item() for value in row)) for row in product))


def _matrix_rows(matrix):
    """Decode one rectangular structural Matrix into numeric Python rows."""
    if not isinstance(matrix, Expression) or not matrix.children or matrix.children[0] != S.Matrix:
        message = "gallery-gemm expects (Matrix (Row ...) ...) atoms"
        raise TypeError(message)
    rows = []
    for row in matrix.children[1:]:
        if not isinstance(row, Expression) or not row.children or row.children[0] != S.Row:
            message = "gallery-gemm expects every Matrix child to be a Row"
            raise TypeError(message)
        values = []
        for value in row.children[1:]:
            if not isinstance(value, Grounded) or not isinstance(value.value, int | float):
                message = "gallery-gemm expects grounded numeric matrix cells"
                raise TypeError(message)
            values.append(value.value)
        rows.append(tuple(values))
    widths = {len(row) for row in rows}
    if len(widths) > 1:
        message = "gallery-gemm expects rectangular matrices"
        raise ValueError(message)
    return tuple(rows)


gallery_linalg.lower(S.topdown, requires=S.blas, space=space)


def evaluate_under_tropical(term):
    """Expose the algebra answer and require exactly one numeric GEMM call."""
    with patch.object(np, "matmul", wraps=np.matmul) as gemm:
        answers = [
            S.Answer(answer.value, answer.annotation)
            for answer in space.answers(term, under=tropical)
        ]
    if gemm.call_count != 1:
        message = f"symbolic lowering executed {gemm.call_count} GEMMs instead of one"
        raise RuntimeError(message)
    return answers


claim(
    "symbolic lowering reaches GEMM",
    S.MM(
        S.T(S.T(S.Matrix(S.Row(1.0, 2.0)))),
        S.Matrix(S.Row(3.0), S.Row(4.0)),
    ),
    evaluate_under_tropical,
)
# -> (MM (T (T (Matrix (Row 1.0 2.0)))) (Matrix (Row 3.0) (Row 4.0)))
# => (Answer (Matrix (Row 11.0)) 0)

space.unregister_op("gallery-gemm")
space.drop()
done("symbolic_tensors")
