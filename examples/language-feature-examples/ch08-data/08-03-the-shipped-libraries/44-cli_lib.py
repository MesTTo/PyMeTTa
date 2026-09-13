"""Purpose: typed options, literal tokens, custom converters and generated help.

Guarantees: the same 64 claims as 44-cli_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/44-cli_lib.metta; commit=WORKTREE].
"""

from metta import FALSE, TRUE, G, S, V, arrow, lib, typed
from metta._errors.errors import MettaError


def twin(m):
    """Preserve argument spelling and validate options through their declarations."""
    m += lib.string
    m += lib.cli

    def option(key, *fields):
        """One native-shaped declaration with its required key."""
        return (S.opt(key), *fields)

    specification = (
        option(S.count, S.type(S.integer), S.shortflags((S.n,)),
               S.longflags((S.count, S.count2)), S.default(1),
               S.meta(G("N")), S.help(G("Item count"))),
        option(S.verbose, S.type(S.boolean), S.shortflags((S.v,)),
               S.longflags((S.verbose,)), S.default(FALSE)),
        option(S.name, S.shortflags((S.s,)), S.longflags((S.name,)), S.default(G("guest"))),
    )
    m.add(typed(S.cli_main, arrow(S.Expression, S.Symbol, S.Expression)),
          S["="](S.cli_main(V.arguments, V.duplicates),
                  S.cli_parse(specification, V.arguments, V.duplicates)),
          S["="](S.cli_plus(V.increment, V.text), S["+"](V.increment, S.parse_number(V.text))))

    def scan(arguments, policy=S.keeplast):
        """Use the same application declaration and repeat policy as the example."""
        return m.fn.cli_main(arguments, policy)

    def refused(call):
        """Keep the native failure and its context for the refusal claims."""
        try:
            list(m.eval(call))
        except MettaError as error:
            return error
        return None

    parse, help_text = m.fn.cli_parse, m.fn.cli_help
    count, verbose, name = S.count, S.verbose, S.name
    defaults = (count(1), verbose(FALSE), name(G("guest")))
    missing_count = (verbose(FALSE), name(G("guest")))

    assert m.fn.cli_types() == [(S.boolean, S.integer, S.float, S.atom, S.string, S.metta)]
    assert scan(()) == [(defaults, ())]
    assert scan((G("--count"), G("3"), G("file"))) == [((*missing_count, count(3)), (G("file"),))]
    assert scan((G("-n4"), G("--name=π🙂"), G("-v"), G("input"))) == [((count(4), name(G("π🙂")), verbose(TRUE)), (G("input"),))]
    assert scan((G("--count2=7"), G("--no-verbose")), S.keepall) == [((name(G("guest")), count(7), verbose(FALSE)), ())]
    assert scan((G("-n"), G("2"), G("--name=a"), G("--count=3")), S.keepfirst) == [((verbose(FALSE), count(2), name(G("a"))), ())]
    assert scan((G("-n"), G("2"), G("--name=a"), G("--count=3"))) == [((verbose(FALSE), name(G("a")), count(3)), ())]
    assert scan((G("-n"), G("2"), G("--name=a"), G("--count=3")), S.keepall) == [((verbose(FALSE), count(2), name(G("a")), count(3)), ())]
    assert scan((G("--verbose=false"), G("-vtrue"), G("--no-verbose")), S.keepall) == [((count(1), name(G("guest")), verbose(FALSE), verbose(TRUE), verbose(FALSE)), ())]

    assert scan((G("--name"), G(""))) == [((count(1), verbose(FALSE), name(G(""))), ())]
    assert scan((G("--name="),)) == [((count(1), verbose(FALSE), name(G(""))), ())]
    assert scan((G("--name=-v"),)) == [((count(1), verbose(FALSE), name(G("-v"))), ())]
    assert scan((G("-s--count"),)) == [((count(1), verbose(FALSE), name(G("--count"))), ())]
    assert scan((G("--count"), G("-3"))) == [((*missing_count, count(-3)), ())]
    assert scan((G("before"), G("--"), G("--count"), G("3"), G(""))) == [(defaults, (G("before"), G("--count"), G("3"), G(""),))]
    assert parse((), (G("-2"), G("-1.5"), G("-"), G(""),), S.keepall) == [((), (G("-2"), G("-1.5"), G("-"), G(""),))]
    assert parse((), (G("--"), G("--"), G(""),), S.keepall) == [((), (G("--"), G(""),))]
    text = m.fn.string_from_codes((97, 0, 98)).one()
    argument = m.fn.string_join(G(""), (G("--name="), text)).one()
    parsed = m.fn.cli_main((argument,), S.keeplast)[0]
    assert m.fn["=alpha"](parsed, ((count(1), verbose(FALSE), name(text)), ())) == [True]
    assert scan((G("--name=a=b=c"),)) == [((count(1), verbose(FALSE), name(G("a=b=c"))), ())]
    assert parse((option(S.missing, S.longflags((S.missing,))),), (), S.keepall) == [((), ())]
    assert parse((option(S.symbol, S.type(S.atom), S.default(S["_"])),
                  option(S.text, S.default(G("_")))), (), S.keepall) == [((S.symbol(S["_"]), S.text(G("_"))), ())]
    assert parse((option(S.short, S.shortflags((S.x,))), option(S.long, S.longflags((S.x,)))),
                 (G("-x"), G("left"), G("--x"), G("right"),), S.keepall) == [((S.short(G("left")), S.long(G("right"))), ())]
    assert parse((option(S.digit, S.type(S.integer), S.shortflags((G("2"),))),),
                 (G("-2"), G("7"),), S.keepall) == [((S.digit(7),), ())]
    assert parse((option(S.mark, S.longflags((S["9?"],))),), (G("--9?=yes"),), S.keepall) == [((S.mark(G("yes")),), ())]
    assert parse((option(S.verbose, S.type(S.boolean), S.longflags((S.verbose,))),
                  option(S.named, S.longflags((S.no_verbose,)))),
                 (G("--no-verbose"), G("literal"),), S.keepall) == [((S.named(G("literal")),), ())]
    assert parse((option(S.ratio, S.type(S.float), S.longflags((S.ratio,))),),
                 (G("--ratio=1.25"),), S.keepall) == [((S.ratio(1.25),), ())]
    assert parse((option(S.mode, S.type(S.atom), S.longflags((S.mode,))),),
                 (G("--mode=scan"),), S.keepall) == [((S.mode(S.scan),), ())]

    literal = (option(S.value, S.type(S.metta), S.longflags((S.value,))),)
    assert parse(literal, (G("--value=(+ 1 2)"),), S.keepall) == [((S.value(S["+"](1, 2)),), ())]
    assert parse(literal, (G("--value=()"),), S.keepall) == [((S.value(()),), ())]
    parsed = parse(literal, (G("--value=(row $x $x)"),), S.keepall)[0]
    assert m.fn["=alpha"](parsed, ((S.value(S.row(V.a, V.a)),), ())) == [True]
    positive = S.Annotated(S.Number, S.Gt(0))
    sized = (option(S.size, S.type(S.parse(positive, S.parse_number)),
                    S.longflags((S.size,)), S.default(1)),)
    assert parse(sized, (G("--size=3"),), S.keepall) == [((S.size(3),), ())]
    assert parse(sized, (), S.keepall) == [((S.size(1),), ())]
    uppercase = S["|->"]((V.x,), S.string_upper(V.x))
    assert parse((option(S.text, S.type(S.parse(S.String, uppercase)), S.longflags((S.text,))),),
                 (G("--text=hello"),), S.keepall) == [((S.text(G("HELLO")),), ())]
    assert parse((option(S.size, S.type(S.parse(S.Number, S.cli_plus(10))), S.longflags((S.size,))),),
                 (G("--size=5"),), S.keepall) == [((S.size(15),), ())]
    arguments = m.fn.quote((G("--count=9"),))[0]
    assert m.fn.cli_main(arguments, S.keeplast) == [((*missing_count, count(9)), ())]
    assert m.fn.get_metatype(m.fn["cli-arguments!"]()[0]) == [S.Expression]

    assert help_text(()) == [G("")]
    assert help_text((option(S.hidden, S.default(G("local"))),)) == [G("")]
    described = option(S.count, S.type(S.integer), S.shortflags((S.n,)),
                       S.default(1), S.meta(G("N")), S.help(G("Item count")))
    assert m.fn.string_contains(help_text(((*described, S.longflags((S.count,))),))[0], G("--count")) == [True]
    assert m.fn.string_contains(help_text((described,))[0], G("N:integer=1")) == [True]
    assert m.fn.string_contains(help_text((option(S.text, S.longflags((S.text,)), S.default(G("π")),
                                              S.help((G("First line"), G("Second line"),))),))[0], G("Second line")) == [True]
    empty_decoder = S["|->"]((V.x,), S.empty())
    assert m.fn.string_contains(help_text((option(S.text, S.type(S.parse(S.String, empty_decoder)),
                                         S.longflags((S.text,))),))[0], G("String")) == [True]

    error = refused(S.cli_main((G("--count"), G("bad")), S.keeplast))
    assert error is not None and "--count" in str(error) and "declared type" in str(error)
    assert refused(S.cli_main((G("--name"),), S.keeplast)) is not None
    assert refused(S.cli_main((G("--name"), G("--verbose"),), S.keeplast)) is not None
    assert refused(S.cli_main((G("--unknown"),), S.keeplast)) is not None
    assert refused(S.cli_main((G("--bad?"),), S.keeplast)) is not None
    assert refused(S.cli_main((G("-n=3"),), S.keeplast)) is not None
    assert refused(S.cli_main((G("-vn"),), S.keeplast)) is not None
    assert refused(S.cli_main((G("--count=bad"), G("--count=3"),), S.keeplast)) is not None
    assert refused(S.cli_parse((), (), S.unknown)) is not None
    assert refused(S.cli_parse((option(S.x), option(S.x)), (), S.keepall)) is not None
    assert refused(S.cli_parse((option(S.x, S.type(S.integer), S.type(S.integer)),), (), S.keepall)) is not None
    assert refused(S.cli_parse((option(S.x, S.longflags((S.same,))), option(S.y, S.longflags((S.same,)))), (), S.keepall)) is not None
    assert refused(S.cli_parse((option(S.x, S.longflags((G("bad name"),))),), (), S.keepall)) is not None
    assert refused(S.cli_parse((option(S.x, S.wat(1)),), (), S.keepall)) is not None
    assert refused(S.cli_parse(((S.type(S.string),),), (), S.keepall)) is not None
    assert refused(S.cli_parse((option(S.x, S.type(S.unknown)),), (), S.keepall)) is not None
    assert refused(S.cli_parse((option(S.x, S.type(S.integer), S.default(G("bad"))),), (), S.keepall)) is not None
    assert refused(S.cli_parse((option(S.x, S.type(S.metta), S.longflags((S.x,))),), (G("--x=1 2"),), S.keepall)) is not None
    assert refused(S.cli_parse((option(S.x, S.type(S.parse(positive, S.parse_number)), S.longflags((S.x,))),), (G("--x=0"),), S.keepall)) is not None
    assert refused(S.cli_parse((option(S.x, S.type(S.parse(S.String, empty_decoder)), S.longflags((S.x,))),), (G("--x=a"),), S.keepall)) is not None
    two = S["|->"]((V.x,), S.superpose((1, 2)))
    assert refused(S.cli_parse((option(S.x, S.type(S.parse(S.Number, two)), S.longflags((S.x,))),), (G("--x=a"),), S.keepall)) is not None
    wrong = S["|->"]((V.x,), G("wrong"))
    assert refused(S.cli_parse((option(S.x, S.type(S.parse(S.Number, wrong)), S.longflags((S.x,))),), (G("--x=a"),), S.keepall)) is not None


#: MEASURED: all 64 claims, including custom conversion and schema refusals.
#: The example pays 347414 inferences.
#: [measured: 367784 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/44-cli_lib.metta;
#: fixture=lib_cli with engine/lib QLF artifacts purged; commit=WORKTREE].
BUDGET = 367784
