"""Purpose: YAML documents as values, in the shape lib_json already uses.

A mapping is a space, so `opened` is `metta.space(answers.one())` exactly as the
JSON twin's is, and the queries over a YAML document are the queries over a JSON
one. Text is `G("...")`, and the file scope takes a FUNCTION, so the read and
write pair is one `@m.define`.

Guarantees: the same claims as 28-yaml_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/28-yaml_lib.metta; commit=WORKTREE].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import G, S, ground, lib
from metta._errors.errors import MettaError

#: The document every query below reads, written once so the twin and its example
#: hold the same text. It is `ground()` data rather than a bare string, because a
#: bare string is a NAME and this is text.
CONF = ground("""name: petta
version: 1.5
tags:
  - prolog
  - metta
limits:
  depth: 3
  strict: true
  note:
  nothing: ~
""")


def twin(m):
    """Decode a document, query it, encode it back, and read and write a file."""
    m += lib.yaml

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    def opened(answers):
        """The handle for the space yaml-decode or dict-space answered by name."""
        return metta.space(answers.one())

    decode, encode = m.fn.yaml_decode, m.fn.yaml_encode
    at, value_of, keys = m.fn.json_at, m.fn.get_value, m.fn.get_keys

    # A mapping becomes a SPACE of (Key Value) atoms, which is lib_json's own
    # shape, so the queries over a YAML document are the queries over a JSON one.
    conf = opened(decode(CONF))
    assert sorted(keys(conf), key=str) == [S.limits, S.name, S.tags, S.version]
    assert value_of(conf, S.name) == [G("petta")]
    assert value_of(conf, S.version) == [1.5]
    assert list(value_of(conf, S.tags).one()) == [G("prolog"), G("metta")]
    assert at(conf, (S.tags, 0)) == [G("prolog")]
    assert at(conf, (S.limits, S.depth)) == [3]
    assert at(conf, (S.limits, S.strict)) == [True]
    # A key written with NO value decodes as the empty string rather than null: the
    # host's reader does not distinguish `note:` from `note: ""`, so a document
    # that means null writes `~` or `null`. An absent key has no answer at all.
    assert at(conf, (S.limits, S.note)) == [G("")]
    assert at(conf, (S.limits, S.nothing)) == [S.Null]
    assert list(value_of(conf, S.missing)) == []

    # A sequence becomes an expression and a scalar document stays a scalar.
    assert list(decode(G("- 1\n- 2\n")).one()) == [1, 2]
    assert decode(G("just text\n")) == [G("just text")]
    assert decode(G("42\n")) == [42]
    assert decode(G("true\n")) == [True]
    assert decode(G("null\n")) == [S.Null]
    # An empty document is Null, which is what YAML says it holds.
    assert decode(G("")) == [S.Null]
    # A quoted scalar keeps its type: this is the string "no", not a boolean,
    # because YAML 1.2's core schema has only true and false.
    assert at(opened(decode(G("k: no\n"))), (S.k,)) == [G("no")]

    # Encoding inverts decoding, and the text it writes is one document ending in
    # a newline.
    assert encode(S.yaml_decode(G("a: 1\nb:\n  - x\n"))) == [G("a: 1\nb:\n- x\n")]
    assert encode((1, 2, S.Null, True)) == [G("- 1\n- 2\n- null\n- true\n")]
    assert encode(G("text")) == [G("text\n")]
    assert encode(7) == [G("7\n")]
    assert encode(S.Null) == [G("null\n")]
    # A mapping to encode is a space of pairs, which dict-space builds without any
    # text in between.
    assert encode(S.dict_space(((S.a, 1), (S.b, G("two"))))) == [G("a: 1\nb: two\n")]
    assert at(opened(decode(S.yaml_encode(S.dict_space(((S.k, 1),))))), (S.k,)) == [1]

    # The file doors are one line each over lib_file: the read is the decode of a
    # whole file and the write is an atomic replacement, so a reader never sees
    # half a document. The scope is lib_file's own, and it takes a function.
    @m.define
    def write_and_read(directory):
        # (= (write-and-read $dir) (let $path (path-join $dir "conf.yaml") ...))
        path = S.path_join(directory, "conf.yaml")
        _written = S["yaml-write!"](path, S.dict_space(((S.host, "localhost"), (S.port, 8080))))
        text = S["read-file!"](path)
        return (text, S.json_at(S["yaml-read!"](path), (S.port,)))

    written = list(m.fn["with-temp-dir"](G("yaml-lib"), S.write_and_read).one())
    assert written == [G("host: localhost\nport: 8080\n"), 8080]

    # The four refusals. A stream with more than one document is refused naming
    # the marker, because the host's reader takes one and answering the first
    # would answer less than the text says.
    assert refused(S.yaml_decode(G("a: 1\n---\nb: 2\n")))
    # A tag the host has no value for is refused naming the tag, where it would
    # otherwise answer an opaque term no MeTTa form can read.
    assert refused(S.yaml_decode(G("k: !foo 1\n")))
    # Malformed text is refused with the line the host stopped on, and a duplicate
    # key is refused rather than silently keeping one of the two.
    assert refused(S.yaml_decode(G("a: [1,\n")))
    assert refused(S.yaml_decode(G("dup: 1\ndup: 2\n")))
    assert list(m.eval(S.yaml_decode(7))) == [
        S.Error(S.yaml_decode(7), S.BadArgType(1, S.String, S.Number)),
    ]
    # A space that is not a mapping is refused naming the atom that is not a pair.
    not_a_map = metta.space(S.notamap)
    not_a_map += S.a(1, 2)
    assert refused(S.yaml_encode(not_a_map))
    # A symbol encodes as the string it spells, so an expression of symbols is a
    # sequence of strings rather than a refusal.
    assert encode((S.one, S.two)) == [G("- one\n- two\n")]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 32 claims cover both heads, the two derived file
#: doors, the mapping-as-space shape lib_json owns and the five refusals; the
#: twin costs less than the example, whose `let` chain in the scope function is one
#: compiled body here
#: [measured 2026-09-12: 179414 inferences against the example's 182395, minimum
#: of three serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/28-yaml_lib.metta;
#: fixture=lib_yaml at its functional commit, artifacts purged before the run;
#: commit=WORKTREE].
BUDGET = 179414

#: DIVERGED 2026-09-12, the example holds 1 atom the twin does not (1 =) and
#: the twin holds 1 atom the example does not (1 =): the scope function is four
#: Python statements, which compile to four nested one-binding let* forms where
#: the example writes three nested let forms; the bindings, the effects and the
#: answer are the same [measured 2026-09-12: the two stored-atom surpluses, one
#: fresh process per side; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
DIVERGENCE = "8d664a1d907fafd4ac83a17261b96171d51aa90af16e18a69b69d77337a2fb6a"
