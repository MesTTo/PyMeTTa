"""The Python twin of examples/integration/python.metta: py-call, five ways.

The five definitions stay at the container door because every one of them names
`py-call`, and a compiled body names a function by exactly its MeTTa spelling,
which `py-call` is not a Python identifier for. That is what the file is ABOUT:
the seam it exercises is the MeTTa-side one, so a twin that reached the same
Python objects through `@m.op` would be testing a different door. The residue
records the missing spelling against P14.4.

Dotted Python paths (`types.SimpleNamespace`, `importlib.import_module`) and
bound-method heads (`.upper`, `.__add__`) are subscripted because none of them
is a Python identifier; that is exactly what the subscript door is for.
"""

from petta import S, V, equation, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 7591


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (make-object) (py-call (types.SimpleNamespace)))
    m += equation(S["make-object"]()).to(S["py-call"](S["types.SimpleNamespace"]()))

    # (= (get-attribute $obj $name) (py-call (getattr $obj $name)))
    m += equation(S["get-attribute"](V.obj, V.name)).to(S["py-call"](S.getattr(V.obj, V.name)))

    # (= (set-attribute $obj $name $value) (py-call (setattr $obj $name $value)))
    m += equation(S["set-attribute"](V.obj, V.name, V.value)).to(
        S["py-call"](S.setattr(V.obj, V.name, V.value))
    )

    # (= (import $name) (py-call (importlib.import_module $name)))
    m += equation(S["import"](V.name)).to(S["py-call"](S["importlib.import_module"](V.name)))

    # (= (math.pi) (get-attribute (import math) pi))
    m += equation(S["math.pi"]()).to(S["get-attribute"](S["import"](S.math), S.pi))

    # !(test (let* (($obj (make-object))
    #               ($temp (set-attribute $obj foo (math.pi))))
    #              (get-attribute $obj foo))
    #        3.141592653589793)
    yield m.eval(
        S.test(S["let*"](((V.obj, S["make-object"]()),
                    (V.temp, S["set-attribute"](V.obj, S.foo, S["math.pi"]()))),
                S["get-attribute"](V.obj, S.foo)),
            3.141592653589793)
    )

    # !(test (py-call (.upper "abc")) ABC)
    yield m.eval(S.test(S["py-call"](S[".upper"](val("abc"))), S.ABC))

    # !(test (py-call (.__add__ 5 3)) 8)
    yield m.eval(S.test(S["py-call"](S[".__add__"](5, 3)), 8))
