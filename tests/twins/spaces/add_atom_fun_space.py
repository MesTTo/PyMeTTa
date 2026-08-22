"""The Python twin of examples/spaces/add_atom_fun_space.metta: the target space is computed.

A function answers a SPACE NAME and the write lands in that space, which is the
whole example. That is also why the two writes below stay TERMS instead of going
through `space += atom`: the container door needs a space HANDLE, and resolving
`(space)` to one in Python would evaluate it here rather than where the write
does, which is precisely the behaviour under demonstration (residue, P14.10).

The equation is at the container door for a second, separate reason: its body is
the bare symbol `&my_space_name`, and a compiled body has no spelling for a name
beginning with `&` (residue, P14.4).
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 1826 across the P14 twin-style rewrite: equation().to()
#: and named symbols build the same three atoms the nested expr() calls built,
#: and the match variable's rename ($a to $found) is free because a variable is
#: an identity rather than a spelling. Measured 1826 before and after.
#: Prior: ADDED 2026-08-22 at 1826 by the wave-3 spaces baseline.
BUDGET = 1826


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (space) &my_space_name)
    m += equation(S.space()).to(S["&my_space_name"])

    # !(add-atom (space) (my test atom))
    yield m.eval(S["add-atom"](S.space(), (S.my, S.test, S.atom)))

    # !(test (match (space) $a $a) (my test atom))
    yield m.eval(
        S.test(S.match(S.space(), V.found, V.found), (S.my, S.test, S.atom))
    )
