"""Purpose: define MeTTa errors and the operation non-reduction signal.

Guarantees:
  - refusing preserves exception descriptors, custom __setattr__ methods
    and their refusals when attaching metadata [source:
    extensions/python/metta/_errors/errors.py:refusing; commit=2d17a5e2218b713d5934b74f8bbb3e4f190a4e5c]
  - Timeout is both the MeTTa coordination miss and a builtin TimeoutError,
    so callers may catch at either abstraction [tested:
    test_the_coordination_family_is_python_shaped; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - every MettaError carries atom, space, operation and capability
    attributes, None by default, the message unchanged for their presence
    [tested test_base_fields_default_to_none]
  - MettaSyntaxError carries the 1-based line the reader stopped at, or None
    where it named none, so a caller points at the line instead of parsing
    the sentence [tested: test_a_json_error_line_names_its_input_line;
    commit=8d67307403c1e41ccf058bd3c8d4c079dd7cf7d5]
  - MettaOperationError.operation is the base field, not a shadow
    [tested test_operation_error_operation_is_the_base_field]
  - AssertionFailure is a MettaError and NOT an EngineError, so a harness
    separates a false claim from a broken engine by type [tested
    test_a_failing_assertion_is_a_different_exception_from_an_engine_fault]
  - AssertionFailure.missing and .excess carry the two directed bag
    differences as decoded atoms, None where the failing form computed none,
    which is a different answer from an empty tuple [tested:
    test_a_two_sided_difference_arrives_as_two_bags,
    test_a_form_with_no_bag_comparison_reports_neither_bag; commit=71de27a76dd16684941e3e090de0d17299d96493]
  - SpaceCapabilityError carries the refused space, operation, and capability
    as fields [tested:
    test_a_restricted_space_cannot_reach_what_its_base_does_not_publish;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - semantic refusals carry a structured Python-reference or MeTTa-law ground,
    and every CompileError derives one from its construct [tested:
    extensions/python/tests/ch10_errors_and_refusals/test_refusal_grounds.py,
    tests/checks/check_refusal_grounds.py;
    commit=WORKTREE]
  - a reified-world effect refusal carries the named EffectSafety law as its
    machine-readable ground [tested:
    test_an_uncovered_world_refuses_before_creating_scratch_or_running_the_operation;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - a stream janus pulls through py_iter/2 never raises into it: every failure
    ends the stream as stream_failure's reserved frame and stream_reraise
    raises it back on the Python side of the crossing, so a provider's
    exception, an operation's, and a control signal each reach the caller as
    themselves [tested:
    test_a_provider_generator_that_raises_names_the_space_and_the_provider,
    test_a_control_signal_out_of_a_python_stream_leaves_no_pending_exception,
    test_a_raising_inverse_generator_names_the_metta_call; commit=0ee5a2dfee0e37a23b0eb9c765b477d7f90295fe]
  - CompileError renders a source path, function, line and exact caret span
    while retaining its machine-readable construct and coordinates, and
    with_coordinates derives that block for a statement wall raised with the
    line alone, the caret gutter width-matched to the number gutter [tested:
    test_a_refusal_renders_the_file_line_function_and_exact_caret;
    commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - Remedy and Ground are frozen, slotted rows that project to
    (remedy ...) and (ground ...) atoms and read back, and a machine or maybe
    Remedy naming none of edit, replace or python is a construction error
    naming all three, while a prose Remedy may be its title alone
    [tested: test_a_remedy_round_trips_through_its_atom,
    test_a_ground_round_trips_through_its_atom,
    test_a_remedy_that_names_no_act_refuses_naming_the_three_fields,
    test_a_prose_remedy_may_be_its_title_alone; commit=f33b7ab0200e6dc74c88fb4c7f827bf545a447ed]
  - catalog templates and atom rows use one remedy-act parser, preserving
    their respective symbol and grounded-text readings [tested:
    test_remedy_templates_and_atoms_share_every_act; commit=8358dfc233bf299bb23eceddd94593a62372fe4b]
  - LockDrift carries every entry that differs as Drift rows AND names them in
    its message with both repairs, so a caller reacts to the rows where it
    used to parse the sentence [tested:
    test_a_lock_drift_refusal_names_every_entry_and_its_repair; commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
  - refusing() carries a remedy and a ground on an error of ANY class,
    including a TypeError, an AttributeError, a ValueError and a
    DeprecationWarning, so `except TypeError` stays the caller's spelling
    [tested: test_a_keyword_on_a_bare_symbol_names_the_positional_form,
    test_a_generated_namespace_miss_names_the_live_namespace,
    test_a_cyclic_value_handed_to_the_json_codec_names_ground,
    test_a_deprecation_rows_term_remedy_decodes_to_an_edit;
    commit=3fc5479961fd591b1884af118528c9a64a1afbb7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import ast
import functools
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from metta._lazy import lazy

__all__ = [
    "AssertionFailure",
    "CompileError",
    "EngineError",
    "Ground",
    "InferenceLimitError",
    "Interrupted",
    "LockDrift",
    "MettaError",
    "MettaOperationError",
    "MettaResultError",
    "MettaSyntaxError",
    "NotReducible",
    "Remedy",
    "ResourceLimitError",
    "RestraintError",
    "SourceNotFound",
    "SpaceCapabilityError",
    "StackLimitError",
    "SubscriberError",
    "TimeLimitError",
    "Timeout",
    "TransportFailure",
    "guarded",
    "guarding",
    "is_transport_failure",
    "refusal_classes",
    "refuse",
    "refusing",
    "stream_failure",
    "stream_reraise",
]


#: The three authorities a deliberate refusal can stand on. "host-reference"
#: is the host language's own specification, which on this seat is a section of
#: the Python Language Reference; "metta-law" a named law this engine states;
#: and "arbiter" a measured answer of upstream PeTTa at the parity pin, which
#: is what settles a question neither language's own documentation answers.
#: The three are the catalog's own `ground-kind` vocabulary, held equal to this
#: tuple by extensions/python/tests/repository/test_refusal_rows.py; the engine
#: spells the first without naming a host because it names none.
GROUND_KINDS = ("host-reference", "metta-law", "arbiter")

#: LSP CodeActionKind, restricted to the three this library issues: "quickfix"
#: repairs one diagnostic, "refactor" changes shape without changing meaning,
#: "source" acts on a whole file or project [source: LSP 3.17 CodeActionKind,
#: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#codeActionKind;
#: commit=3fc5479961fd591b1884af118528c9a64a1afbb7].
REMEDY_KINDS = ("quickfix", "refactor", "source")

#: rustc's Applicability, whose three useful levels this adopts: "machine" is
#: MachineApplicable (definitely what was meant, apply it), "maybe" is
#: MaybeIncorrect (valid, but it may not be what was meant), "prose" is
#: HasPlaceholders (the text shows the shape and a human fills it in)
#: [source: rustc_lint_defs::Applicability,
#: https://doc.rust-lang.org/nightly/nightly-rustc/rustc_lint_defs/enum.Applicability.html;
#: commit=3fc5479961fd591b1884af118528c9a64a1afbb7].
APPLICABILITIES = ("machine", "maybe", "prose")


@dataclass(frozen=True, slots=True)
class Ground:
    """The authority that requires one refusal, carried beside its prose.

    `kind` is one of GROUND_KINDS and `citation` names the exact place: a
    Python Language Reference section, a named MeTTa law, or the arbiter's
    own captured answer under `tests/conformance/petta/`. Its longhand is
    reading the message, which is why the message never changes for this
    field's presence.
    """

    kind: str
    citation: str

    def __post_init__(self) -> None:
        """Refuse a ground that names no admitted authority or no place."""
        if self.kind not in GROUND_KINDS:
            msg = (
                f"unknown refusal-ground kind {self.kind!r}; the admitted "
                f"kinds are {', '.join(GROUND_KINDS)}"
            )
            raise ValueError(msg)
        if not self.citation.strip():
            msg = "a refusal ground requires a nonempty citation"
            raise ValueError(msg)

    def __str__(self) -> str:
        """The authority as one line: kind, then the place it names."""
        return f"{self.kind}: {self.citation}"

    def as_atom(self) -> _root.Atom:
        """This ground as `(ground <kind> "<citation>")`, ordinary MeTTa data.

        The projection that lets a ground be stored, matched and later
        published as a catalog row; `from_atom` is its inverse.
        """
        return _root.Expression(
            [_root.Symbol("ground"), _root.Symbol(self.kind), _root.Grounded(self.citation)]
        )

    @classmethod
    def from_atom(cls, atom: _root.Atom) -> Ground:
        """Read back what `as_atom` wrote, refusing any other shape."""
        parts = _row_parts(atom, "ground", 3)
        return cls(_symbol_text(parts[1], "ground kind"), _text(parts[2], "citation"))


@dataclass(frozen=True, slots=True)
class Remedy:
    """What to write instead, as data rather than as a sentence to parse.

    A refusal that names its repair in prose leaves every reader to parse it;
    this is the same repair as an edit, which is what a compiler fix-it hint
    and an LSP code action are. `title` is the one line an editor puts in its
    menu, `kind` is LSP's CodeActionKind and `applicability` is rustc's
    Applicability: only "machine" is applied without being asked.

    The repair itself is one or more of three acts:

    - `edit` is the atom the remedy names: what to write, or to add;
    - `replace` is a stored atom and what it becomes, with `None` in the
      second position for a removal, which is LSP's own `newText: ""`;
    - `python` is the host-side text to write instead, which carries
      `<placeholders>` exactly when `applicability` is "prose".

    A "prose" remedy may name no act at all, and then the title IS the whole
    repair: advice with no mechanical edit, which is what PostgreSQL's
    `errhint()` and clang's `note:` carry [source: PostgreSQL documentation,
    55.3.2 Error Message Style Guide]. Nine of the thirteen refusal kinds in
    the `&metta` catalog are that shape, because their repair is a decision.
    A "machine" or "maybe" remedy naming no act stays a construction error:
    those two levels promise something an editor can apply.

    Its longhand is the sentence in the message, which never changes for this
    object's presence.
    """

    title: str
    kind: str
    applicability: str
    edit: _root.Atom | None = None
    replace: tuple[_root.Atom, _root.Atom | None] | None = None
    python: str | None = None

    def __post_init__(self) -> None:
        """Refuse a remedy that names no act, or an unknown classifier."""
        if not self.title.strip():
            msg = "a remedy requires a nonempty title"
            raise ValueError(msg)
        if self.kind not in REMEDY_KINDS:
            msg = (
                f"unknown remedy kind {self.kind!r}; the admitted kinds are "
                f"{', '.join(REMEDY_KINDS)}"
            )
            raise ValueError(msg)
        if self.applicability not in APPLICABILITIES:
            msg = (
                f"unknown remedy applicability {self.applicability!r}; the "
                f"admitted levels are {', '.join(APPLICABILITIES)}"
            )
            raise ValueError(msg)
        if (
            self.edit is self.replace is self.python is None
            and self.applicability != "prose"
        ):
            msg = (
                f"the remedy {self.title!r} is {self.applicability} and names "
                f"no act: give it edit= (the atom to write), replace= (a stored "
                f"atom and what it becomes, or None to remove it), python= (the "
                f"host text to write instead), or classify it as prose"
            )
            raise ValueError(msg)

    def __str__(self) -> str:
        """The one line an editor puts in its menu, which is the title."""
        return self.title

    def as_atom(self) -> _root.Atom:
        """This remedy as `(remedy "<title>" <kind> <applicability> <act>...)`.

        Each act is its own child expression, `(edit A)`, `(replace Old New)`,
        `(remove Old)` or `(python "text")`, so a remedy carrying two acts is
        one row with two act children and needs no second encoding.
        """
        acts: list[_root.Atom] = []
        if self.edit is not None:
            acts.append(_root.Expression([_root.Symbol("edit"), self.edit]))
        if self.replace is not None:
            stored, replacement = self.replace
            acts.append(
                _root.Expression([_root.Symbol("remove"), stored])
                if replacement is None
                else _root.Expression([_root.Symbol("replace"), stored, replacement])
            )
        if self.python is not None:
            acts.append(_root.Expression([_root.Symbol("python"), _root.Grounded(self.python)]))
        return _root.Expression(
            [
                _root.Symbol("remedy"),
                _root.Grounded(self.title),
                _root.Symbol(self.kind),
                _root.Symbol(self.applicability),
                *acts,
            ]
        )

    @classmethod
    def from_atom(cls, atom: _root.Atom) -> Remedy:
        """Read back what `as_atom` wrote, refusing any other shape."""
        parts = _row_parts(atom, "remedy", None)
        if len(parts) < 4:
            msg = (
                f"a (remedy ...) row carries a title, a kind and an "
                f"applicability, then any acts; {atom} carries {len(parts) - 1}"
            )
            raise ValueError(msg)
        return cls(
            _text(parts[1], "title"),
            _symbol_text(parts[2], "remedy kind"),
            _symbol_text(parts[3], "applicability"),
            *_remedy_acts(parts[4:], atom, lambda value: _text(value, "python text")),
        )


def _remedy_acts(
    acts: Iterable[_root.Atom], row: _root.Atom | str,
    text: Callable[[_root.Atom], str],
) -> tuple[_root.Atom | None, tuple[_root.Atom, _root.Atom | None] | None, str | None]:
    """Read act structure once; the caller supplies its text representation."""
    edit = None
    replace = None
    python = None
    for act in acts:
        head = _act_head(act, row)
        if head == "edit" and len(act) == 2:
            edit = act[1]
        elif head == "replace" and len(act) == 3:
            replace = (act[1], act[2])
        elif head == "remove" and len(act) == 2:
            replace = (act[1], None)
        elif head == "python" and len(act) == 2:
            python = text(act[1])
        else:
            msg = (
                f"{act} is not a remedy act; a (remedy ...) row carries "
                f"(edit A), (replace Old New), (remove Old) or (python T)"
            )
            raise ValueError(msg)
    return edit, replace, python


def _row_parts(atom: _root.Atom, head: str, arity: int | None) -> tuple[_root.Atom, ...]:
    """The children of one `(head ...)` row, refusing anything else."""
    if (
        not isinstance(atom, _root.Expression)
        or not atom.children
        or atom.children[0] != _root.Symbol(head)
    ):
        msg = f"{atom} is not a ({head} ...) row"
        raise ValueError(msg)
    if arity is not None and len(atom.children) != arity:
        msg = f"a ({head} ...) row carries {arity - 1} parts; {atom} carries {len(atom.children) - 1}"
        raise ValueError(msg)
    return atom.children


def _act_head(act: _root.Atom, row: _root.Atom | str) -> str:
    """The head symbol of one remedy act, refusing an act that is not a call."""
    if isinstance(act, _root.Expression) and act.children and isinstance(act.children[0], _root.Symbol):
        return act.children[0].name
    msg = f"{act} in {row} is not a remedy act expression"
    raise ValueError(msg)


def _text(atom: _root.Atom, what: str) -> str:
    """The Python text a grounded string carries, refusing any other atom."""
    value = getattr(atom, "value", None)
    if isinstance(value, str):
        return value
    msg = f"the {what} is text, and {atom} is not a grounded string"
    raise ValueError(msg)


def _symbol_text(atom: _root.Atom, what: str) -> str:
    """The name a symbol carries, refusing any other atom."""
    if isinstance(atom, _root.Symbol):
        return atom.name
    msg = f"the {what} is a symbol, and {atom} is not one"
    raise ValueError(msg)


def refusing[ExcT: BaseException](
    error: ExcT, *, remedy: Remedy | None = None, ground: Ground | None = None
) -> ExcT:
    """Attach a refusal's structured parts to an error of ANY class.

    Returns the error, so `raise refusing(TypeError(msg), remedy=...)` is one
    line at the site that refuses.

    MettaError takes both in its constructor; a refusal that is a TypeError,
    an AttributeError or a ValueError because Python's own word for it is
    that class has nowhere to put them, and inventing a subclass per builtin
    would make `except TypeError` the wrong spelling. Every exception
    instance carries a `__dict__`, so the parts ride there and a reader asks
    `getattr(error, "remedy", None)` whatever the class is.
    """
    if remedy is not None:
        setattr(error, "remedy", remedy)  # noqa: B010 -- preserve the generic exception's descriptors and custom setters
    if ground is not None:
        setattr(error, "ground", ground)  # noqa: B010 -- preserve the generic exception's descriptors and custom setters
    return error


def refuse(kind: str, message: str, /, **fields: Any) -> BaseException:
    """Build the refusal one catalog kind declares, ready to raise.

        raise refuse("capability", f"{operation} cannot use {space}",
                     space=space, operation=operation, capability=capability)

    The engine declares one `(refusal <kind> <class> <ground> <remedy>)` row
    per kind it can refuse for. This is the seat's door onto those rows: the
    CLASS comes from the row, the GROUND comes from the row, and the REMEDY is
    the row's own template with its `<field>` holes filled from `fields`, so a
    site writes the sentence and nothing else. The engine renders the same
    template for a ball it raises itself, through `metta_host_refusal/6`, and
    the two are held equal for every kind by
    extensions/python/tests/repository/test_refusal_rows.py.

    `fields` are the names that kind declares, and they are used twice: they
    fill the remedy's holes, and they are the keywords the class carries, so
    `SpaceCapabilityError.capability` is the same word the remedy names. A
    keyword the kind does not declare is refused by name rather than dropped.

    A remedy whose holes are not all filled is lowered to `prose`, which is
    rustc's HasPlaceholders and is exactly what the engine's own renderer
    does: the text shows the shape and a reader fills it in.

    Its longhand is constructing the class and calling `refusing(error,
    ground=..., remedy=...)` at the site, which is what a refusal with no
    catalog kind still does.
    """
    from metta._errors.refusals import REFUSALS  # noqa: PLC0415  -- atoms sits above this module

    row = REFUSALS.get(kind)
    if row is None:
        known = ", ".join(sorted(REFUSALS))
        msg = f"no refusal kind named {kind!r}; the engine declares: {known}"
        raise ValueError(msg)
    unknown = sorted(set(fields) - set(row.fields))
    if unknown:
        declared = ", ".join(row.fields) or "none"
        msg = (
            f"the {kind} refusal declares {declared}; "
            f"{', '.join(unknown)} is not one of them"
        )
        raise TypeError(msg)
    error_class = _refusal_class(row)
    ground = Ground(row.ground_kind, row.citation)
    remedy = _refusal_remedy(row, fields)
    if issubclass(error_class, MettaError):
        return error_class(message, ground=ground, remedy=remedy, **fields)
    # A kind this seat spells with a builtin, because Python's own word for the
    # condition is that class and `except ValueError` has to stay the caller's
    # spelling. The parts ride on the instance instead of in the constructor.
    return refusing(error_class(message), ground=ground, remedy=remedy)


def refusal_classes() -> Mapping[str, type[BaseException]]:
    """Every refusal kind's class on this seat, keyed by the engine's word.

    The map the crossing classifies a raised ball with. It is DERIVED from the
    `(refusal ...)` rows rather than kept beside them, which is what stopped a
    seat-side table of seven kinds from standing beside the engine's thirteen
    and silently reporting the other six as a bare EngineError.
    """
    from metta._errors.refusals import REFUSALS  # noqa: PLC0415  -- atoms sits above this module

    return MappingProxyType(
        {kind: _refusal_class(row) for kind, row in REFUSALS.items()}
    )


def _refusal_class(row: Any) -> type[BaseException]:
    """The class one row names, from this module or from builtins."""
    import builtins  # noqa: PLC0415  -- atoms sits above this module

    found = globals().get(row.cls) or getattr(builtins, row.cls, None)
    if not (isinstance(found, type) and issubclass(found, BaseException)):
        msg = (
            f"the {row.kind} refusal names the class {row.cls}, which is "
            f"neither in metta._errors.errors nor a builtin exception"
        )
        raise TypeError(msg)
    return found


def _fill_text(text: str, fields: Mapping[str, Any]) -> str:
    """One template's `<name>` holes, replaced by the values a site gave."""
    for name, value in fields.items():
        text = text.replace(f"<{name}>", str(value))
    return text


def _fill_act(act: Any, fields: Mapping[str, Any]) -> Any:
    """One remedy act's holes, filled, as the atom the act denotes."""
    if isinstance(act, str):
        return _root.Symbol(_fill_text(act, fields))
    return _root.Expression([_fill_act(part, fields) for part in act])


def _has_hole(text: str) -> bool:
    """Whether a filled template still shows a `<name>` placeholder."""
    opening = text.find("<")
    # A closing bracket AFTER the opening one, which `find` answers -1 for when
    # there is none, and -1 is below every opening position.
    return 0 <= opening < text.find(">", opening)


def _refusal_remedy(row: Any, fields: Mapping[str, Any]) -> Remedy:
    """One row's remedy template, filled from the fields a site gave.

    The engine's own renderer, on this side of the crossing: a hole the
    fields do not fill lowers the applicability to `prose`, because what is
    left is a shape rather than an edit [source: engine/metta/registration.pl,
    metta_host_refusal_remedy/3].
    """
    title = _fill_text(row.title, fields)
    acts = [_fill_act(act, fields) for act in row.acts]
    applicability = row.applicability
    if _has_hole(title) or any(_has_hole(str(act)) for act in acts):
        applicability = "prose"
    return Remedy(title, row.remedy_kind, applicability, *_remedy_acts(acts, title, str))


_PYTHON_COMPARISON_GROUND = Ground(
    "host-reference",
    "Python Language Reference section 6.10, Comparisons",
)
_PYTHON_RICH_COMPARISON_GROUND = Ground(
    "host-reference",
    "Python Language Reference section 3.3.1, Basic customization",
)
_EFFECT_SAFETY_GROUND = Ground(
    "metta-law",
    "EffectSafety: a reified world admits only an effect plan covered by its handlers",
)

#: Which section of the Python Language Reference governs each construct the
#: compiler refuses. The CONSTRUCTS are not written here: they are whatever the
#: compiler's own `CompileError(construct=...)` sites name, plus the `ast` node
#: class names its `type(node).__name__` sites produce, and
#: extensions/python/tests/ch10_errors_and_refusals/test_refusal_grounds.py
#: derives that list from the source and holds this table to it both ways. A
#: construct with no row here is a finding unless _EXPRESSION_CONSTRUCTS names
#: it, and a term here that governs no construct is a finding too.
# closed-set: decides; policy=which section of the Python Language Reference governs each construct the compiler refuses; reads=none, the CONSTRUCTS are derived from the compiler's own sites by test_every_construct_the_compiler_refuses_has_a_citation and only the citations are decided here
_COMPILE_REFERENCE_BY_CONSTRUCT = (
    (("match", "pattern", "case", "capture"), "Python Language Reference section 8.6, The match statement"),
    (("for", "while"), "Python Language Reference section 8.2-8.3, while and for statements"),
    (("with",), "Python Language Reference section 8.5, The with statement"),
    (("yield", "generator"), "Python Language Reference section 6.2.9, Yield expressions"),
    (("call", "callee", "keyword", "function", "def", "twin", "argument", "overload"), "Python Language Reference section 6.3.4, Calls"),
    (("attribute", "field"), "Python Language Reference section 6.3.2, Attribute references"),
    (("subscript", "slice"), "Python Language Reference section 6.3.3, Subscriptions"),
    (("compare", "boolop"), "Python Language Reference section 6.10-6.11, Comparisons and Boolean operations"),
    (("floor", "reduce", "binop"), "Python Language Reference section 6.7, Binary arithmetic operations"),
    (("name", "ambiguous", "identifier", "binding"), "Python Language Reference section 4.2, Naming and binding"),
    (("raise",), "Python Language Reference section 7.8, The raise statement"),
    (("try", "except", "finally"), "Python Language Reference section 8.4, The try statement"),
    (("global", "nonlocal"), "Python Language Reference section 7.12-7.13, The global and nonlocal statements"),
    (("type alias",), "Python Language Reference section 7.15, The type statement"),
    (("class", "constructor"), "Python Language Reference section 8.7, Class definitions"),
    (("assignment", "assign", "walrus", "annotation", "annassign", "augassign"), "Python Language Reference section 7.2, Assignment statements"),
    (("delete", "del",), "Python Language Reference section 7.5, The del statement"),
    (("return",), "Python Language Reference section 7.6, The return statement"),
    (("if",), "Python Language Reference section 8.1, The if statement"),
    (("lambda",), "Python Language Reference section 6.14, Lambdas"),
    (("comprehension", "listcomp", "setcomp", "dictcomp"), "Python Language Reference section 6.2.8, Displays for lists, sets and dictionaries"),
    (("f-string", "joinedstr", "constant", "literal", "list", "tuple", "dict", "set"), "Python Language Reference section 6.2.2, Literals"),
    (("import",), "Python Language Reference section 7.11, The import statement"),
    (("assert",), "Python Language Reference section 7.3, The assert statement"),
    (("await", "async"), "Python Language Reference section 8.8.2, Coroutines"),
    (("operator word",), "Python Language Reference section 6.7, Binary arithmetic operations"),
)

#: Constructs the DEFAULT citation governs, named rather than left to fall
#: through it. Every one is a whole EXPRESSION this compiler refuses for a
#: reason of its own rather than for a rule the grammar states about a
#: particular form: what the library will and will not compile is the library's
#: own subset, and section 6 is the part of the reference that says what an
#: expression is at all.
# closed-set: decides; policy=which constructs the expressions section governs, named rather than left to fall through to it; reads=none, it is the source the same drift test reads
_EXPRESSION_CONSTRUCTS = frozenset(
    {
        "None",
        "body",
        "clause order",
        "host binding",
        "py host island",
        "override declaration",
        "range",
        "round",
        "source",
        "sum",
        "structural capture",
    }
)

#: What a construct with no row of its own stands on.
_EXPRESSION_REFERENCE = "Python Language Reference section 6, Expressions"


def _compile_ground(construct: str | None) -> Ground:
    lowered = "" if construct is None else construct.lower()
    citation = next(
        (
            reference
            for terms, reference in _COMPILE_REFERENCE_BY_CONSTRUCT
            if any(term in lowered for term in terms)
        ),
        _EXPRESSION_REFERENCE,
    )
    return Ground("host-reference", citation)


def _grounded_type_error(
    message: str, *, ground: Ground, remedy: Remedy | None = None
) -> TypeError:
    """Construct a TypeError without exposing a second public exception name."""
    return refusing(TypeError(message), ground=ground, remedy=remedy)


class MettaError(Exception):
    """Base class for everything this library raises on purpose.

    Machine-readable parts ride beside the message, the way
    AttributeError.name and OSError.errno do: `atom` is the MeTTa atom
    the error is about, an `(Error ...)` answer or the offending term;
    `space` is the space name involved; `operation` the operation that
    refused; `capability` the capability that was missing; `ground` the
    Python-reference, named MeTTa law or arbiter answer that requires a
    semantic refusal; `remedy` the repair the message spells in prose, as
    the edit an editor can offer.
    Each defaults to None, and the message never changes for their presence, so a
    program reacts to the part where it used to parse the sentence.
    """

    def __init__(
        self,
        *args: object,
        atom: object | None = None,
        space: str | None = None,
        operation: str | None = None,
        capability: str | None = None,
        ground: Ground | None = None,
        remedy: Remedy | None = None,
    ):
        super().__init__(*args)
        self.atom = atom
        self.space = space
        self.operation = operation
        self.capability = capability
        self.ground = ground
        self.remedy = remedy


class Timeout(MettaError, TimeoutError):  # noqa: N818 -- a timeout is the public outcome, not an implementation error suffix
    """A bounded coordination wait ended before anything arrived."""


class MettaSyntaxError(MettaError):
    """The reader refused the source. Carries the engine's own message.

    `line` is the 1-based source line the reader stopped at when it named
    one, and None when it did not. The message already says the line in
    prose; the attribute is there so a caller that has to POINT at it reads
    a number instead of parsing the sentence, which is the split CPython
    makes between `SyntaxError`'s message and its `lineno`
    [source: https://docs.python.org/3.14/library/exceptions.html#SyntaxError].
    An unbalanced form names its line; a single form read on its own and a
    numeric literal past binary64 do not, and answer None.
    """

    def __init__(
        self,
        *args: object,
        line: int | None = None,
        **fields: Any,
    ):
        super().__init__(*args, **fields)
        self.line = line


class SourceNotFound(MettaError, FileNotFoundError):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """A file this library was asked to load is not there.

    Both bases on purpose. A caller reaching for a source file writes
    `except FileNotFoundError`, and a caller wrapping a whole registration
    writes `except MettaError`; one exception answering to both is what
    stops the second reading from silently missing this case, which is what
    a plain FileNotFoundError did.

    `source` is the path that is not there, which is the field the `source`
    refusal row declares and the one the remedy names.
    """

    def __init__(
        self,
        *args: object,
        source: str | None = None,
        **fields: Any,
    ):
        super().__init__(*args, **fields)
        self.source = source


class EngineError(MettaError):
    """A Prolog-side exception crossed the boundary.

    The original janus exception rides along as __cause__, so nothing is
    hidden; the message here is the engine's, trimmed of janus framing.
    """


class SpaceCapabilityError(EngineError):
    """A restricted space tried an operation its creation grants omit."""

    def __init__(
        self,
        message: str,
        *,
        space: str,
        operation: str,
        capability: str,
        ground: Ground | None = None,
        remedy: Remedy | None = None,
    ):
        """Carry the refusing space, operation, and missing capability as data."""
        super().__init__(
            message,
            space=space,
            operation=operation,
            capability=capability,
            ground=ground,
            remedy=remedy,
        )


class MettaOperationError(EngineError):
    """A builtin refused a value, naming the operation the source wrote.

    The engine keeps the ISO formal term and adds the written operation, so
    the parts arrive as data: `operation` is what to look for in the source,
    `kind` is the formal's functor, and `expected` and `culprit` carry the
    type and the offending value when the formal is a type error. Catching
    EngineError still catches this.
    """

    def __init__(
        self,
        message: str,
        *,
        operation: str,
        kind: str,
        expected: object | None = None,
        culprit: object | None = None,
        ground: Ground | None = None,
        remedy: Remedy | None = None,
    ):
        super().__init__(message, operation=operation, ground=ground, remedy=remedy)
        self.kind = kind
        self.expected = expected
        self.culprit = culprit


class MettaResultError(MettaError):
    """The evaluation ANSWERED an `(Error ...)` atom through a single-value
    accessor.

    In MeTTa an error is a result: `(Error culprit reason)` is one
    element of the answer multiset, which is why the aggregation methods,
    eval(), run(), function iteration and the streams, keep it as data. An
    accessor that answers exactly one value has no multiset for the error to be
    data in, so one(), first() and calling a function raise it instead.
    `atom` carries the whole `(Error ...)` expression, `culprit` the
    term it blames, `reason` the explanation beside it. Not an
    EngineError on purpose: the engine did not throw, the program
    answered an error value.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(
        self,
        message: str,
        *,
        atom: object,
        culprit: object | None = None,
        reason: object | None = None,
        space: str | None = None,
        ground: Ground | None = None,
        remedy: Remedy | None = None,
    ):
        super().__init__(message, atom=atom, space=space, ground=ground, remedy=remedy)
        self.culprit = culprit
        self.reason = reason


class LockDrift(MettaError):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """The tree no longer matches the lock a program was asked to run under.

    `drifts` carries one entry per artefact that differs, each naming what the
    lock recorded and what is here now, so a caller reports every difference
    at once rather than discovering them one run at a time. The message names
    the same entries in prose and states both repairs: re-pin, or restore what
    was pinned.
    """

    def __init__(
        self,
        drifts: Iterable[object],
        *,
        source: object | None = None,
        **fields: Any,
    ):
        """Build the refusal from the drift rows, naming `source` if given."""
        entries = tuple(drifts)
        listed = "; ".join(str(entry) for entry in entries)
        named = str(source) if source is not None else "the lock"
        repair = Remedy(
            title="re-pin the lock from this tree",
            kind="source",
            applicability="maybe",
            python="metta.engine().lock().write('metta.lock')",
        )
        message = (
            f"{named} no longer describes this tree: {listed}. The remedy is "
            f"to re-pin with `metta lock -o <lock>`, or to restore the pinned "
            f"revision of what changed"
        )
        fields.setdefault("remedy", repair)
        super().__init__(message, **fields)
        self.drifts = entries


class AssertionFailure(MettaError):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """A MeTTa `(test ...)` or `(assert ...)` said something false.

    Deliberately NOT an EngineError: the engine worked, the program's claim
    did not hold. A harness runs a suite and has to tell "this file's
    assertion is red" from "the interpreter under it broke", and those two
    call for opposite responses, so they are opposite types. Both are still
    MettaError, so a caller wrapping a whole run keeps catching both.

    `operation` is the form that failed, "test" or "assert"; `actual` is what
    the expression produced and `expected` what the source asked for, each
    None where the form carries no such value (a failed `assert` has a goal
    and no pair, and a `test` with no answer at all has no actual).

    `missing` and `excess` are the two directed bag differences a failing
    comparison over answers already computed, as tuples of atoms: the answers
    expected and not produced, and the answers produced and not expected.
    Both are None where the failing form computed no such difference, and
    None is a different answer from an empty tuple -- `()` for both says the
    two answer bags agree and the answers differ only in order. The message
    carries the same two lines, because the engine's own sentence does; these
    are the fields a harness reads instead of parsing it.
    """

    def __init__(
        self,
        message: str,
        *,
        operation: str,
        actual: object | None = None,
        expected: object | None = None,
        missing: tuple[_root.Atom, ...] | None = None,
        excess: tuple[_root.Atom, ...] | None = None,
        ground: Ground | None = None,
        remedy: Remedy | None = None,
    ):
        super().__init__(
            message, operation=operation, atom=actual, ground=ground, remedy=remedy
        )
        self.actual = actual
        self.expected = expected
        self.missing = missing
        self.excess = excess


class SubscriberError(MettaError):
    """A watcher raised, and the write it was watching had already landed.

    A subscription callback runs inside the write that triggered it, so its
    exception comes back out through the writer. Told apart from a refused
    write only by reading the message, the two invited opposite responses to
    the same sentence: retry a refused write, never retry an applied one.
    A space is a multiset, so the second copy the retry stores is permanent.

    `subscription` is the standing query whose callback raised, `atom` and
    `space` are what was written and where, `action` is "add" or "remove",
    and `__cause__` is what the callback actually raised.

    The write is applied when this is raised. An enclosing atomic run or
    `(transaction ...)` scope is the one thing that undoes it, and it does
    so as this error leaves the scope.
    """

    def __init__(
        self,
        message: str,
        *,
        subscription: object,
        action: str,
        atom: object | None = None,
        space: str | None = None,
        ground: Ground | None = None,
        remedy: Remedy | None = None,
    ):
        super().__init__(message, atom=atom, space=space, ground=ground, remedy=remedy)
        self.subscription = subscription
        self.action = action


class ResourceLimitError(EngineError):
    """A per-call resource guard stopped the evaluation.

    The guard is the caller's own timeout= or inferences= bound. Whatever
    the goal completed before the stop, writes included, stands; that is
    what stopping a computation mid-way means everywhere.

    `limit` is the bound that was reached, None where the ball named none:
    SWI's own `inference_limit_exceeded` and `time_limit_exceeded` arrive
    unenveloped from a nested query and know only which resource ran out.
    It is the field the three limit rows declare and the one their remedies
    name, so a caller reads the number instead of the sentence around it.
    """

    def __init__(
        self,
        *args: object,
        limit: object | None = None,
        **fields: Any,
    ):
        super().__init__(*args, **fields)
        self.limit = limit


class TimeLimitError(ResourceLimitError):
    """timeout= seconds elapsed before the call finished."""


class InferenceLimitError(ResourceLimitError):
    """inferences= engine steps were spent before the call finished."""


class StackLimitError(ResourceLimitError):
    """The evaluation ran out of the stack ceiling in force when it did.

    SWI reports the ceiling as part of the ball, and it is the ceiling that
    was IN FORCE when the stack ran out, not the one in force now: a program
    that raises `(pragma! stack-limit ...)` after the fact still reads the
    number the refusal happened under. Its two siblings bound a caller's own
    keyword; this one bounds the engine's own memory, which is why the remedy
    the row carries names a pragma rather than a keyword.
    """


class RestraintError(ResourceLimitError):
    """A restraint the program declared for one of its tables tripped.

    The bound is the program's own `(cache name (max-answers N))`,
    `(subgoal-abstract N)` or `(answer-abstract N)` row rather than a
    caller's keyword, which is the one difference from its two siblings.
    `restraint` is that word, `bound` its integer, and `call` the tabled call
    the engine was evaluating, as MeTTa text. Whatever the goal completed
    before the stop stands, and the table keeps the answers it had, so the
    next call of the same table signals again until it is cleared.
    """

    def __init__(
        self,
        message: str,
        *,
        restraint: str | None = None,
        bound: int | None = None,
        call: str | None = None,
        ground: Ground | None = None,
        remedy: Remedy | None = None,
    ):
        super().__init__(message, ground=ground, remedy=remedy)
        self.restraint = restraint
        self.bound = bound
        self.call = call



class Interrupted(EngineError):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """interrupt() stopped the evaluation mid-goal.

    The sqlite3 and DuckDB reading of interrupt: whatever the goal
    completed before the stop, writes included, stands.
    """


class CompileError(MettaError):
    """A Python construct the define compiler refuses, with the reason.

    Refusals are the contract: every one names the construct, the line, and
    what to write instead, so the message teaches the subset rather than
    hiding it. Never a silent fallback.
    """

    def __init__(
        self,
        message: str,
        *,
        construct: str | None = None,
        line: int | None = None,
        ground: Ground | None = None,
        remedy: Remedy | None = None,
        path: str | None = None,
        source_line: str | None = None,
        column: int | None = None,
        end_column: int | None = None,
        function: str | None = None,
        annotation: str | None = None,
    ):
        if path is not None and line is not None and source_line is not None:
            headline, *detail = message.splitlines()
            place = f"  --> {path}:{line}"
            if function is not None:
                place += f" in {function}"
            place += f" (line {line})"
            start = max(column or 0, 0)
            stop = max(end_column or start + 1, start + 1)
            caret = " " * start + "^" * (stop - start)
            if annotation is not None:
                caret += f" {annotation}"
            number = f"{line:>3}"
            gutter = " " * len(number)
            rendered = "\n".join(
                [
                    headline,
                    place,
                    f"{gutter} |",
                    f"{number} | {source_line.rstrip()}",
                    f"{gutter} | {caret}",
                    *detail,
                ]
            )
        else:
            where = f" (line {line})" if line is not None else ""
            rendered = f"{message}{where}"
        super().__init__(
            rendered, ground=ground or _compile_ground(construct), remedy=remedy
        )
        self.message = message
        self.construct = construct
        self.line = line
        self.path = path
        self.source_line = source_line
        self.column = column
        self.end_column = end_column
        self.function = function
        self.annotation = annotation


def character_column(line: str, byte_column: int) -> int:
    """Translate Python AST's UTF-8 byte offset into a display column."""
    return len(line.encode("utf-8")[:byte_column].decode("utf-8"))


def _statement_span(source: str, line: int) -> tuple[int, int] | None:
    """The first statement's exact span on a 1-based line of SOURCE.

    Statement walls raise with the line alone, so the span is recovered
    here from the tree rather than threaded through every raise site. A
    line holding no statement head (a bare clause keyword) answers None
    and the caller falls back to the text span.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and node.lineno == line:
            end = (
                node.end_col_offset
                if node.end_lineno == node.lineno and node.end_col_offset is not None
                else None
            )
            return node.col_offset, end if end is not None else -1
    return None


def with_coordinates(
    error: CompileError,
    *,
    source: str,
    first_line: int,
    path: str,
    function: str,
) -> CompileError:
    """The same refusal, carrying the caret block a statement wall omits.

    Expression walls build their coordinates where the node is in hand;
    a statement wall raises with the function-relative line alone, and
    this boundary derives the rest from the compiler's own held source:
    the absolute line, the source line, and the exact statement span read
    back out of the tree (the head line of a multi-line statement, the
    way rustc points a primary span). Already-placed errors and errors
    without a line pass through untouched.
    """
    if error.path is not None or error.line is None:
        return error
    lines = source.splitlines()
    if not 0 < error.line <= len(lines):
        return error
    source_line = lines[error.line - 1]
    span = _statement_span(source, error.line)
    if span is not None:
        start = character_column(source_line, span[0])
        stop = (
            character_column(source_line, span[1])
            if span[1] >= 0
            else len(source_line.rstrip())
        )
    else:
        stripped = source_line.rstrip()
        start = len(stripped) - len(stripped.lstrip())
        stop = len(stripped)
    return CompileError(
        error.message,
        construct=error.construct,
        line=first_line + error.line - 1,
        ground=error.ground,
        remedy=error.remedy,
        path=path,
        source_line=source_line,
        column=start,
        end_column=max(stop, start + 1),
        function=function,
        annotation=error.annotation,
    )


class TransportFailure(MettaError):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """The backend is ABSENT rather than wrong: a connection, a timeout, a
    closed stream. The remote protocol's error trichotomy treats these
    differently from application errors: a declared keep or empty mode never
    applies, transport always aborts, because retrying or giving up is the
    caller's decision and an absent backend has said nothing about the data.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose


def is_transport_failure(error: BaseException) -> bool:
    """Whether an error is the backend being ABSENT rather than wrong.

    The obvious test does not separate them: a socket timeout raises OSError,
    and a transport whose own timeout does NOT subclass it misses exactly the
    shape a broken event stream takes under load. Which classes those are is
    the `transport-error` point's rows, one per transport library, so a client
    with its own exception hierarchy declares it rather than being added here.
    Hoisted from the DAS surface to the shared error model, because every
    remote backend needs the same trichotomy.
    """
    from metta import seam  # noqa: PLC0415  -- the seam, which errors sits under
    from metta._lazy import optional_module  # noqa: PLC0415  optional probe

    cause = error.__cause__ if isinstance(error, MettaError) else error
    if isinstance(error, TransportFailure):
        return True
    if isinstance(cause, (OSError, TimeoutError)):
        return True
    for row in seam.transport_error.table().values():
        module = optional_module(row.module)
        if module is not None and isinstance(cause, row.classes(module)):
            return True
    return False


class NotReducible(Exception):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """Raised inside an operation to answer nothing at all.

    A deterministic operation that raises NotReducible makes the call fail rather
    than error, which is how a semi-deterministic MeTTa function says no. A
    generator operation needs no signal: yielding nothing already is one.
    """


# --------------------------------------------------------- the py_iter crossing


def _failed_during_generator_close(error: BaseException) -> bool:
    """Tell a release failure from an ordinary mid-iteration failure.

    ``contextlib.closing`` calls the owned generator's ``close`` while handling
    ``GeneratorExit`` from this stream. A release error then carries that
    control signal as its direct context and must propagate rather than yield,
    because yielding while closing raises ``RuntimeError: generator ignored
    GeneratorExit`` and hides the resource failure.
    """
    return isinstance(error.__context__, GeneratorExit)


def stream_failure(error: BaseException) -> list:
    """Carry a terminal stream failure as data until Prolog can raise it.

    Janus pulls a Python iterator with ``PyIter_Next`` inside ``py_iter/2`` and
    never consults the error indicator afterwards, so an iterator that RAISES is
    indistinguishable there from one that is exhausted: the Prolog goal carries
    on with a silently truncated stream and the still-set Python exception
    surfaces at whatever crossing runs next [source: janus 1.5.3
    janus.c:py_iter3, the two ``state->next = PyIter_Next(state->iterator)``
    calls, neither followed by ``check_error``; commit=0ee5a2dfee0e37a23b0eb9c765b477d7f90295fe]. What "whatever
    runs next" turned out to be was a provider match answering one atom instead
    of two and then dying inside janus's own error path with SIGSEGV, because
    ``py_record`` asks Python to build a ``Term`` while the indicator is set,
    CPython refuses, and ``Py_SetPrologErrorFromObject`` increments the NULL
    that leaves; and a KeyboardInterrupt out of a nondeterministic operation
    printing ``foreign predicate system:$new_findall_bag/0 did not clear
    exception`` before vanishing [tested:
    test_an_inference_limit_spent_inside_a_provider_callback_is_an_inference_limit_error,
    test_a_control_signal_out_of_a_python_stream_leaves_no_pending_exception;
    commit=0ee5a2dfee0e37a23b0eb9c765b477d7f90295fe].

    So a stream this library hands to ``py_iter`` may not raise. It ends with
    this reserved frame instead, carrying the live exception object; the Prolog
    side hands that object straight back to ``stream_reraise``, where janus's
    own ``check_error`` converts it exactly as it converts the exception of a
    deterministic ``py_call`` callback. ``x`` is the wire's control namespace,
    so no encoded atom can be read as one.
    """
    return ["x", "raise", type(error).__name__, error]


def stream_reraise(error: BaseException) -> None:
    """Raise what a stream carried out, back on the Python side of the crossing.

    Called from Prolog with the object ``stream_failure`` put in the frame, so
    the exception is raised inside an ordinary ``py_call``: janus maps
    ``KeyboardInterrupt`` and ``SystemExit`` onto their unwind forms and every
    other class onto ``error(python_error(Class, Object), context(python_stack
    (Stack), _))``, and the live object stays reachable for
    ``metta_py_original_exception/2`` to re-raise at the outer door.
    """
    raise error


def guarded(
    stream: Iterable[Any],
    translate: Callable[[BaseException], BaseException] | None = None,
) -> Iterator[Any]:
    """One stream, made total: it yields items and never raises into py_iter.

    A failure ends the stream with ``stream_failure``'s frame. ``translate``
    is the owning seam's chance to say whose failure it was before the
    exception crosses; it may not itself raise.
    """
    try:
        yield from stream
    except GeneratorExit:
        raise
    except BaseException as error:
        # Every class, because every class poisons the crossing equally: the
        # narrower `except Exception` these doors used to carry is exactly
        # what let KeyboardInterrupt through to py_iter.
        if _failed_during_generator_close(error):
            raise
        yield stream_failure(error if translate is None else translate(error))


def guarding(door: Callable[..., Iterable[Any]]) -> Callable[..., Iterator[Any]]:
    """Declare that janus pulls this door's stream through ``py_iter``.

    The decorator form of ``guarded``, for the doors the shim names directly.
    """

    @functools.wraps(door)
    def crossing(*arguments: Any, **keywords: Any) -> Iterator[Any]:
        return guarded(door(*arguments, **keywords))

    return crossing

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
