"""Purpose: running a program with an argument vector, and watching a started one.

A program name and an argument are `G("...")` text, because they are text; a run
answers a `(process-result Code Output Error)` expression, read as a tuple. The two
started processes are Python names holding the identifiers, as the example's `bind!`
forms are.

Guarantees: the same claims as 32-process_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/32-process_lib.metta; commit=WORKTREE].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, lib
from metta._errors.errors import MettaError


def twin(m):
    """Run, capture, feed, start, poll, signal and wait."""
    m += lib.process

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    def result(answers):
        """One run's (process-result Code Output Error) expression, as a tuple."""
        return tuple(answers.one())

    run, feed = m.fn["process-run!"], m.fn["process-run-input!"]
    start, wait = m.fn["process-start!"], m.fn["process-wait!"]
    status, signal = m.fn.process_status, m.fn["process-signal!"]

    # A run answers (process-result Code Output Error): the exit code as a Number and
    # both streams as Strings. The program is named and the arguments are a
    # COLLECTION, so nothing in them can become a second command.
    assert result(run(G("echo"), (G("hi"),))) == (S.process_result, 0, G("hi\n"), G(""))
    assert result(run(G("echo"), (G("one"), G("two")))) == (
        S.process_result, 0, G("one two\n"), G(""),
    )
    assert result(run(G("true"), ())) == (S.process_result, 0, G(""), G(""))

    # A nonzero exit is a STATUS and not an error.
    assert result(run(G("false"), ())) == (S.process_result, 1, G(""), G(""))
    assert m.fn.index_atom(S["process-run!"](G("sh"), (G("-c"), G("exit 7"))), 1) == [7]

    # Both streams are captured separately.
    assert result(run(G("sh"), (G("-c"), G("echo out; echo err 1>&2; exit 3")))) == (
        S.process_result, 3, G("out\n"), G("err\n"),
    )

    # An argument is never parsed: this file name would be two commands to a shell,
    # and here it is one argument.
    assert result(run(G("echo"), (G("; echo hacked"),))) == (
        S.process_result, 0, G("; echo hacked\n"), G(""),
    )
    # Running a shell is the caller's own choice, and it says so in the program's name.
    assert result(run(G("sh"), (G("-c"), G("echo shell")))) == (
        S.process_result, 0, G("shell\n"), G(""),
    )

    # A program that reads its input is fed without a temporary file.
    assert result(feed(G("cat"), (), G("fed"))) == (S.process_result, 0, G("fed"), G(""))
    assert result(feed(G("wc"), (G("-c"),), G("1234"))) == (
        S.process_result, 0, G("4\n"), G(""),
    )

    # A program that could not be launched is a refusal naming it.
    assert refused(S["process-run!"](G("no_such_program_anywhere"), ()))
    assert refused(S["process-run!"](G("/no/such/binary"), ()))

    # A started process is the caller's: it answers an identifier, process-status asks
    # without waiting, and process-wait! answers the code.
    quick = start(G("true"), ()).one()
    assert quick > 0
    assert wait(quick) == [0]
    # Waiting twice is a refusal, because the host has already forgotten the process.
    assert refused(S["process-wait!"](quick))

    # A process that outlives the call is signalled, and a signalled program answers
    # the negative of its signal number.
    sleeper = start(G("sleep"), (G("30"),)).one()
    assert status(sleeper) == [S.running]
    assert signal(sleeper, S.term) == [True]
    assert wait(sleeper) == [-15]

    # Every signal the library sends is data, and one it does not know is refused.
    assert list(m.fn.process_signals().one()) == [S.term, S.kill, S.int, S.hup]
    assert refused(S["process-signal!"](1, S.nosuch))

    # The refusals for what is not a program, not a vector and not a process.
    # A String where the vector belongs is refused by the DECLARATION, so it answers
    # the engine's own BadArgType; if-error reads that and a raise the same way.
    assert list(m.eval(S["process-run!"](G("echo"), G("not a collection")))) == [
        S.Error(S["process-run!"](G("echo"), G("not a collection")),
                S.BadArgType(2, S.Expression, S.String)),
    ]
    assert refused(S["process-run!"](G("echo"), (S.nested(),)))
    assert list(m.eval(S["process-run!"](7, ()))) == [
        S.Error(S["process-run!"](7, ()), S.BadArgType(1, S.String, S.Number)),
    ]
    assert list(m.eval(S["process-wait!"](G("not a process")))) == [
        S.Error(S["process-wait!"](G("not a process")), S.BadArgType(1, S.Number, S.String)),
    ]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 24 claims cover the seven heads, the exit code as a
#: status, the signalled process's negative code and the refusals. A run's cost is
#: mostly the host's: the child does the work, so both sides here are well under the
#: other libraries' examples [measured 2026-09-12: 47068 inferences against the
#: example's 50892, minimum of three serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/32-process_lib.metta;
#: fixture=lib_process at its functional commit, artifacts purged before the run;
#: commit=WORKTREE].
BUDGET = 47068
