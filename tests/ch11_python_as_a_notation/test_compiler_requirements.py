"""Purpose: refuse incomplete compiler collaborators before lowering starts."""

import importlib
import inspect

import pytest

from metta._compile.context import CompilerContext


def test_incomplete_compiler_is_refused_before_lowering():
    """An omitted collaborator cannot wait until a source path calls it."""
    with pytest.raises(TypeError, match="abstract"):
        CompilerContext()

    compiler = importlib.import_module("metta._declare.define")._Compiler
    assert not inspect.isabstract(compiler)

    class Incomplete(compiler):
        expression = CompilerContext.expression

    with pytest.raises(TypeError, match="expression"):
        Incomplete.__new__(Incomplete)
