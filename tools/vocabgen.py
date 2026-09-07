"""Purpose: generate extensions/python/metta/vocabularies.py from the running engine's
(vocabulary ...) catalog rows, so the binding's option types and runtime
value sets follow the catalog's one authority.

Every vocabulary renders as one StrEnum class: each member IS its wire string,
so `mode=OnError.keep` autocompletes, renames, enumerates with `list(OnError)`,
survives every `value in ("keep", ...)` membership test a plain word passes,
and crosses the boundary as the symbol it always was through `__metta__`.
Bare words stay the runtime escape hatch at every consuming call; the enum is
what the annotations name, which is the guide's "never strings" rule for
option values made checkable.

Assumes:
  - swipl is on PATH and engine/metta.pl consults from the repository root,
    which is how every gate lane already runs it
Guarantees:
  - the checked-in module equals what this produces, gated on every run
    [tested: test_the_vocabulary_module_is_generated;
    commit=918e4eaae8b99077f8b8b293b4ec5c3e0e2b2cf6]
  - the Node seat's table, extensions/node/src/vocabularies.ts, is written
    from the same rows with the Node package's own casing map, so the two
    seats cannot drift from each other or from the engine (the refinement
    vocabulary reached Python and not Node before this, and the Node test
    caught it on the merged tree) [tested: test_the_vocabulary_module_is_generated;
    commit=a376df6dff8099d6145ace55132c7e30922ea1de]
  - output is deterministic: vocabularies sorted by name, values kept in
    their declared order
    [tested: test_the_vocabulary_module_is_generated;
    commit=918e4eaae8b99077f8b8b293b4ec5c3e0e2b2cf6]
  - the catalog visibility row generates the exact PUBLIC/INTERNAL enum
    [tested: test_visibility_is_a_generated_catalog_vocabulary;
    commit=918e4eaae8b99077f8b8b293b4ec5c3e0e2b2cf6]
  - a catalog name that already uses CamelCase keeps that spelling in its
    Python class [tested: test_generated_alias_preserves_declared_camel_case;
    commit=4d01efe426a5a3b79d404afd993f3260e23a210c]
  - every generated member encodes as its MeTTa symbol [tested:
    test_every_vocabulary_member_crosses_as_its_symbol;
    commit=918e4eaae8b99077f8b8b293b4ec5c3e0e2b2cf6]
  - EffectClass alone carries catalog-order comparison and strongest-member
    join/compose operations [tested:
    test_effect_class_is_the_public_five_rank_join_lattice,
    test_effect_join_obeys_the_lattice_laws;
    commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
  - a value that spells a Python keyword takes a trailing underscore as its
    member name and keeps the bare word as its value [tested:
    test_a_keyword_value_takes_a_trailing_underscore; commit=4d01efe426a5a3b79d404afd993f3260e23a210c]
  - both seats' class names ARE the MeTTa type name the engine writes into
    `&metta`, read from the catalog rather than mapped here: the mechanical
    CamelCase of the kebab row name, or the `(vocabulary-type ...)` row where
    one is declared. The RENAMES dict this file used to carry for
    `on-error-mode` is now that row [tested:
    test_the_vocabulary_module_is_generated,
    test_every_vocabulary_is_typed_by_the_engine; commit=WORKTREE]
  - a vocabulary the engine declares OPEN renders as an enum that also
    accepts a word registered through `(add-atom &metta (vocabulary-member
    <vocab> <word>))`, in Python through `_missing_` and in TypeScript
    through the `| (string & {})` union [tested:
    test_an_open_vocabulary_accepts_a_registered_word; commit=WORKTREE]
  - the wire tag table is generated from the engine's own `(wire-tag ...)`
    rows, so `metta._schemas` and `metta._projection` read one grammar
    instead of keeping an eight-tag and a nine-tag copy of it [tested:
    test_the_wire_tag_table_is_the_engines_own; commit=WORKTREE]
  - the run FAILS when the engine's own `(: ...)` type atoms disagree with
    its vocabulary rows, so this lane covers the atoms as well as the
    generated files [tested: test_the_vocabulary_module_is_generated;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import itertools
import json
import keyword
import pathlib
import re
import subprocess
import sys
from typing import NamedTuple

ROOT = pathlib.Path(__file__).resolve().parents[3]
MODULE = ROOT / "extensions" / "python" / "metta" / "vocabularies.py"
TS_MODULE = ROOT / "extensions" / "node" / "src" / "vocabularies.ts"

#: One engine process answers every question this generator asks, as tagged
#: lines: V a vocabulary row, T a declared type name, R an order chain, O an
#: open marker, W a wire tag, C a `(: subject object)` atom and S a
#: `(:< narrow wide)` edge. The last two are what let this lane check the
#: atoms the engine WROTE against the rows they come from.
QUERY = (
    "consult('engine/metta.pl'), "
    "forall(metta_catalog_row([vocabulary, V|Vs]), "
    "       (format('V ~w', [V]), forall(member(X, Vs), format(' ~w', [X])), nl)), "
    "forall(metta_catalog_row(['vocabulary-type', V, T]), "
    "       format('T ~w ~w~n', [V, T])), "
    "forall(metta_catalog_row(['vocabulary-order', V|Cs]), "
    "       (format('R ~w', [V]), forall(member(X, Cs), format(' ~w', [X])), nl)), "
    "forall(metta_catalog_row(['vocabulary-open', V, _]), "
    "       format('O ~w~n', [V])), "
    "forall(metta_catalog_row(['wire-tag', Tag, Class, Payload, Means]), "
    "       format('W ~w ~w ~w ~w~n', [Tag, Class, Payload, Means])), "
    "forall(metta_catalog_row([':', Subject, Object]), "
    "       format('C ~w ~w~n', [Subject, Object])), "
    "forall(metta_catalog_row([':<', Narrow, Wide]), "
    "       format('S ~w ~w~n', [Narrow, Wide]))"
)

HEADER = '''"""Purpose: expose catalog vocabularies as generated StrEnum classes.

Each class corresponds to one (vocabulary ...) row in &metta.

GENERATED by extensions/python/tools/vocabgen.py from the running engine's catalog
presets; edit the presets in engine/spaces/catalog.pl and rerun with --write, never
this file. The vocab-sync gate lane fails when the two drift.

Each member IS its wire string, so it passes every membership test a bare
word passes and crosses as the symbol it always was; bare words remain the
runtime escape hatch at every consuming call.

Guarantees:
  - every class here exactly matches its catalog vocabulary row, values in
    declared order
    [tested: test_the_vocabulary_module_is_generated;
    commit=918e4eaae8b99077f8b8b293b4ec5c3e0e2b2cf6]
  - every member encodes as its MeTTa symbol
    [tested: test_every_vocabulary_member_crosses_as_its_symbol;
    commit=918e4eaae8b99077f8b8b293b4ec5c3e0e2b2cf6]
  - Visibility is the catalog's exact PUBLIC/INTERNAL discriminator
    [tested: test_visibility_is_a_generated_catalog_vocabulary;
    commit=918e4eaae8b99077f8b8b293b4ec5c3e0e2b2cf6]
  - EffectClass compares by catalog rank and joins a plan to its strongest
    member [tested: test_effect_class_is_the_public_five_rank_join_lattice,
    test_effect_join_obeys_the_lattice_laws;
    commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
  - a class name IS the MeTTa type name the engine writes: `(: EffectClass
    Type)` and `(: pureStructural EffectClass)` are atoms in `&metta`, and the
    name comes from the row rather than from a map kept here
    [tested: test_every_vocabulary_is_typed_by_the_engine; commit=WORKTREE]
  - a class the engine declares OPEN accepts a word registered through
    `(add-atom &metta (vocabulary-member <vocab> <word>))`
    [tested: test_an_open_vocabulary_accepts_a_registered_word; commit=WORKTREE]
  - WIRE_TAGS is the wire grammar as the engine states it, one row per tag
    [tested: test_the_wire_tag_table_is_the_engines_own; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from collections.abc import Iterable, Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Final, NamedTuple

from .atoms import Symbol


class _AtomStrEnum(StrEnum):
    """A closed Python option whose wire identity is its MeTTa symbol."""

    def __metta__(self):
        return Symbol(self.value)


class _OpenStrEnum(_AtomStrEnum):
    """An option set the engine's row declares OPEN, so a word a library
    registered is a member too.

    The members written out below are what the engine ships. A word registered
    through `(add-atom &metta (vocabulary-member <vocab> <word>))` reaches this
    class through `_missing_`, which mints a member for it exactly as
    `enum.IntFlag` mints one for a composite nobody wrote down.

    The rung below is the engine's own refusal. This class does not ask the
    engine whether the word is registered, because the catalog checks it at the
    write and refuses an unregistered one there, naming the row; asking here
    would buy a crossing per call to say the same thing earlier. Protocol
    Buffers draws the same line for its open enums: an undeclared value is
    carried, and what it means is the application's business.
    """  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str):
            return None
        member = str.__new__(cls, value)
        member._name_ = value
        member._value_ = value
        return cls._value2member_map_.setdefault(value, member)


class _EffectStrEnum(_AtomStrEnum):
    """One member of an ordered effect lattice, strongest value winning."""

    @property
    def rank(self) -> int:
        """The catalog position, from structural purity to host I/O."""
        return tuple(type(self)).index(self)

    # The reason is here rather than beside the pragma because pylint reads
    # everything after disable= as message names: this is the effect
    # lattice's own operation, which shares a name with str.join on a
    # str-derived enum, and the docstring below says why that is deliberate.
    # pylint: disable-next=arguments-renamed
    def join(self, other):
        """The least upper bound of two effects: their strongest member.

        This shadows ``str.join`` on a str-derived enum deliberately: join
        is the lattice operation's own name and its laws are tested
        (commutative, idempotent, associative, with the weakest rank as
        identity). Anything that is not an effect refuses by naming both
        readings, so a caller who wanted the string operation is told which
        operation they called rather than seeing a bad-enum-value error.
        """
        try:
            other = type(self)(other)
        except ValueError:
            msg = (
                f"{other!r} is not {type(self).__name__} member; this join "
                f"is the effect lattice's least upper bound, not str.join. "
                f"To join strings, call str.join on a plain string."
            )
            raise TypeError(msg) from None
        return self if self.rank >= other.rank else other

    @classmethod
    def compose(cls, effects: Iterable):
        """Join a plan's effects; an empty plan has no observable effect."""
        result = next(iter(cls))
        for effect in effects:
            result = result.join(effect)
        return result

    def _other_rank(self, other):
        try:
            return type(self)(other).rank
        except (TypeError, ValueError):
            return NotImplemented

    def __lt__(self, other):
        rank = self._other_rank(other)
        return NotImplemented if rank is NotImplemented else self.rank < rank

    def __le__(self, other):
        rank = self._other_rank(other)
        return NotImplemented if rank is NotImplemented else self.rank <= rank

    def __gt__(self, other):
        rank = self._other_rank(other)
        return NotImplemented if rank is NotImplemented else self.rank > rank

    def __ge__(self, other):
        rank = self._other_rank(other)
        return NotImplemented if rank is NotImplemented else self.rank >= rank

'''

#: The Node table's fixed text around the generated blocks: the contract
#: header, then the reflection door and the effect-lattice helpers.
TS_HEADER = '/**\n * Purpose: the engine\'s own closed value sets, as TypeScript unions, so a\n *   program that names one of these names it exactly and a typo is a compile\n *   error rather than an answer that never comes.\n * Assumes:\n *   - each block below is one `(vocabulary ...)` row in the `&metta` catalog,\n *     whose presets live in `engine/spaces/catalog.pl`\n * Guarantees:\n *   - this file is GENERATED by extensions/python/tools/vocabgen.py from the\n *     engine\'s own `(vocabulary ...)` rows, beside the Python module the same\n *     tool writes; edit the presets in engine/spaces/catalog.pl and rerun it\n *     with --write, never this file, and the `vocab-sync` lane fails on any\n *     drift [tested: test_the_vocabulary_module_is_generated; commit=a376df6dff8099d6145ace55132c7e30922ea1de]\n *   - every table here matches its catalog row exactly, values in the\n *     catalog\'s own order, and the test that checks it BOOTS the engine and\n *     reads `&metta` rather than reading a copy of this file, so the two\n *     cannot drift [tested: "every vocabulary here matches the engine\'s own";\n *     commit=bbb512316280110a747e31c26adfc31e8c5104be]\n *   - `AlgebraLaw` publishes every accepted declaration spelling, read from\n *     the same live catalog row [tested: "every vocabulary here matches the\n *     engine\'s own"; commit=5e0ae6c22d604c4b980766e3cc4811ee545e5c9e]\n *   - a value\'s KEY is this package\'s own casing map applied to the word, so\n *     `AnswerPolicy.bestFirst` is `"best-first"`, exactly as `S.bestFirst` is\n *     the symbol `best-first`. A word the map leaves alone keeps its exact\n *     spelling, which is why `OpKind.raw_det` carries an underscore the style\n *     guide would otherwise refuse: it is the engine\'s word, not an identifier\n *     this package chose\n * Decides: a const object plus a derived union type, not an `enum`. The\n *   package compiles under `erasableSyntaxOnly`, which refuses `enum` because\n *   an enum emits runtime code that type stripping cannot erase; the const\n *   object is the shape TypeScript\'s own documentation recommends in its\n *   place, and it has the property an enum lacks — the VALUES are the engine\'s\n *   own words, so a bare string still passes every door.\n * Open Obligations:\n *   To Do: None\n *   Hacks: None\n *   Future Enhancements: None\n */\n\n'
TS_TAIL = '/** One vocabulary\'s engine name. */\nexport type VocabularyName = keyof Vocabularies;\n\n/** Every value of one vocabulary, in the catalog\'s own order. */\nexport function valuesOf(vocabulary: VocabularyName): readonly string[] {\n  return Object.values(VOCABULARIES[vocabulary]);\n}\n\n/** Whether a word is a value of one vocabulary. */\nexport function isValueOf(vocabulary: VocabularyName, word: string): boolean {\n  return valuesOf(vocabulary).includes(word);\n}\n\n/**\n * How strong an effect class is, from structural purity to host I/O.\n *\n * The catalog declares the five in RANK ORDER, so the position in the row is\n * the rank and nothing here restates it.\n */\nexport function effectRank(effect: EffectClass): number {\n  return valuesOf("effect-class").indexOf(effect);\n}\n\n/**\n * The strongest of several effect classes: the lattice join.\n *\n * A plan\'s effect is the strongest effect any step of it has, which is what\n * makes this a join rather than a sum. With no arguments the answer is the\n * bottom of the lattice, `pureStructural`, because a plan that does nothing\n * has no effect.\n */\nexport function joinEffects(...effects: readonly EffectClass[]): EffectClass {\n  let strongest: EffectClass = EffectClass.pureStructural;\n  for (const effect of effects) {\n    if (effectRank(effect) > effectRank(strongest)) strongest = effect;\n  }\n  return strongest;\n}\n'


class Catalog(NamedTuple):
    """Everything one engine process answers about its own vocabularies."""

    vocabularies: list[tuple[str, list[str]]]
    types: dict[str, str]
    orders: dict[str, list[str]]
    open_: set[str]
    wire_tags: list[tuple[str, str, str, str]]
    colon: set[tuple[str, str]]
    sub: set[tuple[str, str]]


def catalog() -> Catalog:
    """Ask the engine itself, once, for every row this generator reads."""
    completed = subprocess.run(  # noqa: S603  -- fixed argv, no untrusted input
        ["swipl", "-g", QUERY, "-t", "halt"],  # noqa: S607  -- PATH swipl, as every lane runs it
        cwd=ROOT, capture_output=True, text=True, timeout=120, check=True,
    )
    rows: list[tuple[str, list[str]]] = []
    types: dict[str, str] = {}
    orders: dict[str, list[str]] = {}
    open_: set[str] = set()
    wire_tags: list[tuple[str, str, str, str]] = []
    colon: set[tuple[str, str]] = set()
    sub: set[tuple[str, str]] = set()
    for line in completed.stdout.splitlines():
        words = line.split()
        if not words:
            continue
        kind, rest = words[0], words[1:]
        if kind == "V":
            rows.append((rest[0], rest[1:]))
        elif kind == "T":
            types[rest[0]] = rest[1]
        elif kind == "R":
            orders[rest[0]] = rest[1:]
        elif kind == "O":
            open_.add(rest[0])
        elif kind == "W":
            tag, cls, payload, means = line.split(maxsplit=4)[1:]
            wire_tags.append((tag, cls, payload, means))
        elif kind == "C":
            colon.add((rest[0], rest[1]))
        elif kind == "S":
            sub.add((rest[0], rest[1]))
    if not rows:
        msg = (
            "the engine answered no (vocabulary ...) rows; the catalog "
            "presets failed to load, which is its own defect"
        )
        raise SystemExit(msg)
    return Catalog(sorted(rows), types, orders, open_, wire_tags, colon, sub)


def type_atom_findings(known: Catalog) -> list[str]:
    """Where the engine's own `(: ...)` atoms disagree with its rows.

    The generated files are only half of what a vocabulary row implies. The
    other half is what the engine writes into `&metta`: one
    `(: <TypeName> Type)` per row, one `(: <member> <TypeName>)` per member,
    and the `(:< ...)` edges of any declared order. Checking them here is what
    makes `vocab-sync` cover the atoms rather than only the two tables.
    """
    wanted: set[tuple[str, str]] = set()
    edges: set[tuple[str, str]] = set()
    for vocab, values in known.vocabularies:
        name = alias_name(vocab, known)
        wanted.add((name, "Type"))
        wanted.update((value, name) for value in values)
        chain = known.orders.get(vocab, [])
        edges.update(itertools.pairwise(chain))
    names = {alias_name(vocab, known) for vocab, _ in known.vocabularies}
    # An atom whose object is a vocabulary type, or which declares one of those
    # types, is this lane's business; anything else in `&metta` is not.
    present = {
        (subject, obj)
        for subject, obj in known.colon
        if obj in names or (obj == "Type" and subject in names)
    }
    findings: list[str] = []
    findings.extend(
        f"the engine never wrote (: {subject} {obj})"
        for subject, obj in sorted(wanted - present)
    )
    findings.extend(
        f"the engine wrote (: {subject} {obj}), which no row implies"
        for subject, obj in sorted(present - wanted)
    )
    findings.extend(
        f"the engine never wrote (:< {narrow} {wide})"
        for narrow, wide in sorted(edges - known.sub)
    )
    return findings


def alias_name(vocab: str, known: Catalog) -> str:
    """The MeTTa type name of a vocabulary, which is also its class name.

    One rule, declared exceptions. The engine resolves the same two steps in
    `metta_vocabulary_type/2`, so a name is never spelled twice; reading the
    exception from the row is what retired this file's own RENAMES dict.
    """
    if vocab in known.types:
        return known.types[vocab]
    return camel(vocab)


def camel(vocab: str) -> str:
    """The mechanical map: `effect-class` is `EffectClass`, and a name already
    in CamelCase keeps its spelling.
    """  # noqa: D205  -- the rule is one sentence with its exception
    return "".join(part[:1].upper() + part[1:] for part in vocab.split("-"))


def member_name(value: str) -> str:
    """Map a vocabulary value with the catalog's mechanical transliteration."""
    name = value.replace("-", "_")
    if keyword.iskeyword(name):
        name += "_"
    if not name.isidentifier():
        msg = f"vocabulary value {value!r} has no Python member spelling"
        raise SystemExit(msg)
    return name


def member_suffix(member: str) -> str:
    """The narrow lint/type exemption forced by one authored wire spelling."""
    if member[:1].islower() and any(character.isupper() for character in member[1:]):
        return "  # noqa: N815  -- the member keeps the catalog's public wire spelling"
    if hasattr(str, member):
        return "  # type: ignore[assignment]  # the member deliberately shadows a str method; the word is the API"
    return ""


def ts_key(value: str) -> str:
    """Map a vocabulary value with the Node package's own casing map.

    A hyphenated word becomes camelCase (`best-first` is `bestFirst`, exactly
    as `S.bestFirst` is that symbol); a word the map leaves alone keeps its
    spelling, underscore and all (`raw_det`). A result that is not a
    TypeScript identifier is written as a quoted key.
    """
    head, *rest = value.split("-")
    key = head + "".join(part[:1].upper() + part[1:] for part in rest)
    if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", key):
        return key
    return f'"{key}"'


def ts_text(known: Catalog) -> str:
    """Render the Node vocabulary table from the same rows as the module."""
    blocks = []
    for vocab, values in known.vocabularies:
        alias = alias_name(vocab, known)
        keys = [ts_key(value) for value in values]
        if len(set(keys)) != len(keys):
            msg = f"vocabulary {vocab!r} has values that collide as TypeScript keys"
            raise SystemExit(msg)
        members = "".join(
            f'  {key}: "{value}",\n' for key, value in zip(keys, values, strict=True)
        )
        # An open row's type admits a word a library registered, which is what
        # `| (string & {})` spells: the literals keep their autocomplete and
        # any other string is still assignable. protobuf-es faces the same
        # question for proto3's open enums and has no better form either.
        opening = " | (string & {})" if vocab in known.open_ else ""
        note = (
            f"/** The `{vocab}` vocabulary, in the catalog's own order. */\n"
            if vocab not in known.open_
            else (
                f"/**\n * The `{vocab}` vocabulary, in the catalog's own order.\n"
                f" *\n * The engine declares this vocabulary OPEN, so the type also admits a\n"
                f" * word registered through `(add-atom &metta (vocabulary-member\n"
                f" * {vocab} <word>))`; the words below are the ones it ships.\n */\n"
            )
        )
        blocks.append(
            f"{note}"
            f"export const {alias} = {{\n{members}}} as const;\n\n"
            f"/** One value of the `{vocab}` vocabulary. */\n"
            f"export type {alias} = (typeof {alias})[keyof typeof {alias}]{opening};\n\n"
        )
    interface = "".join(
        f'  readonly "{vocab}": typeof {alias_name(vocab, known)};\n'
        for vocab, _ in known.vocabularies
    )
    registry = "".join(
        f'  "{vocab}": {alias_name(vocab, known)},\n' for vocab, _ in known.vocabularies
    )
    return (
        TS_HEADER
        + "".join(blocks)
        + "/**\n * Every vocabulary, by the engine's own name for it.\n *\n"
        " * The reflection door: a tool that must enumerate the closed sets reads this\n"
        " * rather than a list it keeps itself, and the sync test walks it against\n"
        " * `&metta`.\n */\n"
        f"export interface Vocabularies {{\n{interface}}}\n\n"
        "/** Every vocabulary, by the engine's own name for it. */\n"
        f"export const VOCABULARIES: Vocabularies = {{\n{registry}}};\n\n"
        + TS_TAIL
    )


def wire_tag_text(known: Catalog) -> str:
    """Render the wire grammar as one table, from the engine's own rows."""
    rows = "".join(
        f'    "{tag}": WireTag(\n'
        f"        {alias_name('wire-class', known)}.{member_name(cls)},\n"
        f"        {alias_name('wire-payload', known)}.{member_name(payload)},\n"
        f"        {json.dumps(means)},\n"
        f"    ),\n"
        for tag, cls, payload, means in known.wire_tags
    )
    return (
        "class WireTag(NamedTuple):\n"
        '    """One tag of the wire grammar: what class of thing it is, what\n'
        "    class its payload is, and the sentence CODEC.md shows for it.\n"
        '    """  # noqa: D205  -- the row is one claim, not summary-and-body prose\n'
        "\n"
        f"    kind: {alias_name('wire-class', known)}\n"
        f"    payload: {alias_name('wire-payload', known)}\n"
        "    means: str\n"
        "\n"
        "\n"
        "#: Every wire tag, in the catalog's own order. A `term` tag nests inside an\n"
        "#: atom, a `frame` tag wraps a whole answer, and a `reply` tag is one door's\n"
        "#: answer shape. metta._projection reads the term tags for its OpenAPI atom\n"
        "#: schema and metta._schemas reads the payload class for each arm, so the\n"
        "#: shim's clauses and both of those follow one grammar.\n"
        "WIRE_TAGS: Final[Mapping[str, WireTag]] = MappingProxyType({\n"
        f"{rows}"
        "})\n"
    )


def module_text(known: Catalog) -> str:
    """Render one deterministic generated vocabulary module."""
    body = []
    for vocab, values in known.vocabularies:
        members = [member_name(value) for value in values]
        if len(set(members)) != len(members):
            msg = f"vocabulary {vocab!r} has values that collide as members"
            raise SystemExit(msg)
        body.append(f"#: (vocabulary {vocab} {' '.join(values)})")
        if vocab == "effect-class":
            base = "_EffectStrEnum"
        elif vocab in known.open_:
            base = "_OpenStrEnum"
        else:
            base = "_AtomStrEnum"
        body.append(f"class {alias_name(vocab, known)}({base}):")
        if vocab in known.open_:
            body.append(f'    """Typed values of the {vocab} vocabulary, which the engine')
            body.append("    declares OPEN: a word registered through")
            body.append(f"    `(add-atom &metta (vocabulary-member {vocab} <word>))` is")
            body.append("    accepted too, and the members below are the ones it ships.")
            body.append('    """  # noqa: D205  -- the contract is one claim, not summary-and-body prose')
        else:
            body.append(f'    """Typed values of the {vocab} vocabulary."""')
        body.extend(
            f'    {member} = "{value}"' + member_suffix(member)
            for member, value in zip(members, values, strict=True)
        )
        body.append("")
    # Ruff's RUF022 order for a generated `__all__`: the SCREAMING_CASE
    # constant first, then the classes alphabetically, which is what an
    # isort-style sort produces and what the lane checks.
    exported = [
        "WIRE_TAGS",
        *sorted(
            [alias_name(vocab, known) for vocab, _ in known.vocabularies] + ["WireTag"]
        ),
    ]
    names = ",\n    ".join(f'"{name}"' for name in exported)
    return (
        HEADER
        + "__all__ = [\n    " + names + ",\n]\n\n"
        + "\n".join(body)
        + "\n" + wire_tag_text(known)
    )


def main(argv: list[str]) -> int:
    """Check both generated tables and the engine's type atoms, or rewrite the
    tables when asked. The atoms are never rewritten from here: they are the
    engine's own writes, and a disagreement is an engine defect.
    """  # noqa: D205  -- the two halves of the lane are one contract
    known = catalog()
    findings = type_atom_findings(known)
    stale = []
    for path, wanted in ((MODULE, module_text(known)), (TS_MODULE, ts_text(known))):
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == wanted:
            continue
        if "--write" in argv:
            path.write_text(wanted, encoding="utf-8")
            print(f"rewrote {path.relative_to(ROOT)}")
        else:
            stale.append(str(path.relative_to(ROOT)))
    if stale:
        print(
            f"{', '.join(stale)} no longer match the engine's (vocabulary ...) "
            f"rows: run `python extensions/python/tools/vocabgen.py --write`"
        )
    for finding in findings:
        print(f"the catalog's type atoms disagree with its rows: {finding}")
    return 1 if stale or findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
