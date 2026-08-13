"""Purpose: the MeTTa runtime surface. One class binds a space name to the
process's engine and offers running source, loading files, structured space
edits, conjunctive queries with guards, bounds, scoped assumptions and
preparation, evaluation, Python-backed operations, proof-tree derivations
and a why-not diagnostic, all in PeTTa's own semantics.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from . import ops as _ops_module
from ._engine import Runtime, runtime
from .atoms import Atom, Expr, Sym, Var, alpha_eq, encode, from_wire, parse, variables
from .derivation import Derivation
from .results import Rows

__all__ = ["MeTTa", "Prepared", "current_space"]


def current_space(default: str = "&self") -> str:
    """The space whose module the ENGINE is evaluating in right now.

    Callable from inside a registered operation, where it answers the space
    of the program that called it: janus re-enters the engine cleanly, so
    an operation can behave per-space without the space being an argument.
    Outside any evaluation it answers the default.
    """
    import petta as pkg

    if pkg.janus is None:
        return default
    row = pkg.janus.query_once("current_metta_space(S)")
    return str(row["S"]) if row else default

# @define bookkeeping is keyed (space name, function name) process-wide,
# because equations live in spaces, not in MeTTa instances: two instances
# bound to one space stack clauses of one function together.
_DEFINE_CLAUSES: dict[tuple[str, str], list[dict]] = {}
_DECLARED_DEFINES: dict[tuple[str, str], bool] = {}
_DEFINED_GENERATORS: set[tuple[str, str]] = set()


def _to_atom(value: Any) -> Atom:
    """Accept an Atom, MeTTa source text, or an encodable Python value."""
    if isinstance(value, Atom):
        return value
    if isinstance(value, str):
        return parse(value)
    return encode(value)


class MeTTa:
    """A space bound to the engine: the way in from Python.

    PeTTa keeps one engine per process; every MeTTa instance shares it. The
    default space is &self, the space the CLI itself uses, so source pasted
    from a .metta file behaves identically here. Named spaces isolate stored
    atoms; equations are process-wide, which is the engine's own rule.

        from petta import MeTTa, S, V

        m = MeTTa()
        m.run("(= (foo) boo) !(foo)")     # [[Sym('boo')]]
        m.add(S.Parent(S.Tom, S.Bob))
        m.query(S.Parent(V.x, S.Bob))     # Rows[x](Row(x=Sym('Tom')))
    """

    def __init__(
        self,
        space: str = "&self",
        *,
        verbose: bool = False,
        petta_path: str | None = None,
    ) -> None:
        if not space.startswith("&"):
            raise ValueError(
                f"a space name starts with &, as in &self or &kb; got {space!r}. "
                f"The prefix is load-bearing: is-space recognises it, and a $ "
                f"name would read back as a variable."
            )
        self._rt: Runtime = runtime(petta_path=petta_path, verbose=verbose)
        self._space = space
        self._ephemeral = False

    # ------------------------------------------------------------------ naming

    @property
    def space_name(self) -> str:
        return self._space

    def space(self, name: str) -> "MeTTa":
        """Another space on the same engine."""
        return MeTTa(name)

    def fresh_space(self) -> "MeTTa":
        """An anonymous space with a name nothing else is using.

        Works as a context manager: leaving the block drops the space, so a
        churn of short-lived spaces reuses names instead of growing the
        engine's module table.

            with m.fresh_space() as scratch:
                scratch.add(...)
        """
        row = self._rt.must("petta_py_new_space(Name)")
        fresh = MeTTa(row["Name"])
        fresh._ephemeral = True
        return fresh

    def drop(self) -> None:
        """Clear this space and release its name for reuse. Dropping a
        foreign space releases the binding and leaves the provider's own
        data alone; &self, the engine's own space, is cleared but its name
        never released. Subscriptions on the space cancel with it: a
        pooled name reused later must not deliver to the old life's
        watchers."""
        from .foreign import PROVIDERS, unregister_provider
        from .subscribe import _SUBSCRIPTIONS

        for subscription in [
            s for s in _SUBSCRIPTIONS if s.space == self._space
        ]:
            subscription.cancel()
        if self._space in PROVIDERS:
            unregister_provider(self._rt, self._space)
        self.clear()
        if self._space != "&self":
            self._rt.must("petta_py_release_space(Space)", Space=self._space)

    def __enter__(self) -> "MeTTa":
        if not self._ephemeral:
            raise TypeError(
                f"{self._space} was not created by fresh_space(); only an "
                f"anonymous space scopes to a with-block, since leaving the "
                f"block drops it. Call drop() deliberately for a named one."
            )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.drop()

    def __repr__(self) -> str:
        return f"MeTTa({self._space!r})"

    # ----------------------------------------------------------------- running

    def run(self, source: str, using: dict[str, Any] | None = None) -> list[list[Atom]]:
        """Run MeTTa source: one list of answers per ! directive.

        The pipeline is the engine's own reader, compiler and evaluator, so
        the answers are exactly what the CLI would print, kept grouped per
        directive instead of flattened. Equations and facts in the source
        land in this space.

        `using` names Python values the source refers to by bare symbol,
        the way DuckDB reads a local dataframe by its variable name:

            m.run("!(py-len graph)", using={"graph": my_graph})

        Each named symbol substitutes to its value (objects by identity),
        after reading, before anything runs.
        """
        if not using:
            row = self._rt.must(
                "petta_py_run(Src, Space, Groups)", Src=source, Space=self._space
            )
        else:
            pairs = [[name, encode(value).to_wire()] for name, value in using.items()]
            row = self._rt.must(
                "petta_py_run_using(Src, Space, Pairs, Groups)",
                Src=source,
                Space=self._space,
                Pairs=pairs,
            )
        return [[from_wire(w) for w in group] for group in row.get("Groups", [])]

    def save(self, path: str) -> int:
        """Write every stored atom of this space, equations included, as
        MeTTa source load() reads back; answers how many. Atoms carrying
        live host objects cannot survive a file and are refused."""
        atoms = self.atoms()
        lines = []
        for atom in atoms:
            if not _serializable(atom):
                raise ValueError(
                    f"{atom} carries a live Python object; a file cannot "
                    f"hold it. Remove it, or persist its data explicitly."
                )
            lines.append(str(atom))
        with open(path, "w") as handle:
            handle.write("\n".join(lines) + ("\n" if lines else ""))
        return len(atoms)

    def load(self, path: str) -> list[list[Atom]]:
        """Load a .metta file the way the CLI does, working directory included."""
        row = self._rt.must("petta_py_load(File, Space, Groups)", File=str(path), Space=self._space)
        return [[from_wire(w) for w in group] for group in row.get("Groups", [])]

    def parse(self, source: str) -> Atom:
        """Read one form into an atom without evaluating it."""
        return parse(source)

    # ------------------------------------------------------------- space edits

    def add(self, *atoms: Any) -> None:
        """Add atoms to this space, one engine round-trip for the lot.
        An (= ...) atom compiles as an equation. A stored atom is an
        expression, the engine's own storage shape, so anything else is
        refused here rather than failing silently inside."""
        wires = []
        for a in atoms:
            atom = _to_atom(a)
            if not isinstance(atom, Expr):
                raise TypeError(
                    f"a stored atom is an expression; {atom!r} is "
                    f"{atom.metatype}. Wrap a bare value in structure, as in "
                    f"(value {atom})."
                )
            wires.append(atom.to_wire())
        if not wires:
            return
        if len(wires) == 1:
            self._rt.do_must("petta_py_add", self._space, wires[0])
        else:
            self._rt.do_must("petta_py_add_many", self._space, wires)

    def add_table(self, head: Any, data: Any) -> int:
        """Any tabular source as facts (head v1 .. vn); answers how many.

            m.add_table("edge", polars_frame)         # or a pandas frame
            m.add_table("edge", {"src": [...], "dst": [...]})
            m.add_table("edge", [("a", "b"), ("b", "c")])

        The source is read by the interface it offers, never by library:
        iter_rows() (polars), itertuples() (pandas), a mapping of columns,
        or any iterable of row sequences. A mapping's fact positions are
        its own key order, and columns of unequal length are a hard error
        rather than a silent truncation. The reverse direction is
        rows.table(), the dict every DataFrame constructor takes."""
        import collections.abc as _abc

        head_atom = _to_atom(head)
        if hasattr(data, "iter_rows"):
            rows = data.iter_rows()
        elif hasattr(data, "itertuples"):
            rows = data.itertuples(index=False)
        elif isinstance(data, _abc.Mapping):
            rows = zip(*data.values(), strict=True)
        elif isinstance(data, _abc.Iterable):
            rows = iter(data)
        else:
            raise TypeError(
                f"add_table reads iter_rows(), itertuples(), a mapping of "
                f"columns, or an iterable of rows; "
                f"{type(data).__name__} offers none of those"
            )
        facts = [
            Expr([head_atom, *(encode(value) for value in row)]) for row in rows
        ]
        self.add(*facts)
        return len(facts)

    def remove(self, atom: Any) -> bool:
        """Remove an atom, engine semantics: an equation removal reports
        whether it existed; a plain atom removal removes every copy."""
        removed = self._rt.apply_must(
            "petta_py_remove", self._space, _to_atom(atom).to_wire()
        )
        result = from_wire(removed)
        return bool(getattr(result, "value", True))

    def atoms(self) -> list[Atom]:
        """Every stored atom in this space."""
        wires = self._rt.apply_must("petta_py_atoms", self._space)
        return [from_wire(w) for w in wires]

    def count(self) -> int:
        row = self._rt.once("petta_py_count(Space, N)", Space=self._space)
        return int(row["N"])

    def __len__(self) -> int:
        return self.count()

    def __contains__(self, atom: Any) -> bool:
        return self._rt.do(
            "petta_py_contains", self._space, _to_atom(atom).to_wire()
        )

    def clear(self) -> None:
        """Remove everything stored here, compiled equations included."""
        self._rt.must("petta_py_clear(Space)", Space=self._space)
        # The @define bookkeeping follows the equations it describes.
        for registry in (_DEFINE_CLAUSES, _DECLARED_DEFINES):
            for key in [k for k in registry if k[0] == self._space]:
                del registry[key]
        for key in [k for k in _DEFINED_GENERATORS if k[0] == self._space]:
            _DEFINED_GENERATORS.discard(key)
        # Reflection facts describing this space follow it too, so a pooled
        # name reused later does not inherit another life's story. One
        # engine crossing removes them all; per-fact crossings measured
        # 64ms for 10,000 defines.
        from .ops import REFLECTION_SPACE

        if self._space != REFLECTION_SPACE:
            self._rt.must(
                "petta_py_reflect_clear_defined(Space)", Space=self._space
            )

    def __iadd__(self, atom: Any) -> "MeTTa":
        self.add(atom)
        return self

    # ----------------------------------------------------------------- queries

    def query(
        self,
        *patterns: Any,
        where: Any | None = None,
        limit: int | None = None,
    ) -> Rows:
        """Match patterns against this space as one conjunction.

        Variables shared between patterns join, the engine's own match/4
        doing the joining. Columns are the variable names in first
        appearance order. `where` is a guard term over the same variables,
        evaluated per join and required true, so restrictions a pattern
        cannot spell (an inequality) compose onto the match:

            m.query(S.person(V.name, V.age), where=V.age >= 18)

        `limit` bounds the answers, the engine stopping at the count
        rather than trimming afterwards.

            m.query(S.Edge(V.x, V.y), S.Edge(V.y, V.z))
        """
        if limit is not None and limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")
        atoms = [_to_atom(p) for p in patterns]
        columns: list[str] = []
        for a in atoms:
            for name in variables(a):
                # `_` is anonymous: fresh at every occurrence, never a column.
                if name != "_" and name not in columns:
                    columns.append(name)
        wires = [a.to_wire() for a in atoms]
        if where is not None:
            answered = self._rt.apply_must(
                "petta_py_query_guarded_all",
                self._space, wires, _to_atom(where).to_wire(), columns, limit or 0,
            )
        elif limit is not None:
            answered = self._rt.apply_must(
                "petta_py_query_limit_all", self._space, wires, columns, limit
            )
        else:
            answered = self._rt.apply_must(
                "petta_py_query_all", self._space, wires, columns
            )
        decoded = [tuple(from_wire(v) for v in r) for r in answered]
        return Rows(tuple(columns), decoded)

    def assuming(self, *facts: Any) -> "_Assuming":
        """Facts held only inside a with-block: the assumptions reading of
        a what-if query, added on entry, removed on exit, exceptions
        included.

            with m.assuming(S.closed(S.bridge)):
                detour = m.query(S.route(V.r), where=...)
        """
        return _Assuming(self, [_to_atom(f) for f in facts])

    def prepare(self, *patterns: Any, where: Any | None = None) -> "Prepared":
        """A query whose shape is fixed and whose facts are not: the wire
        form and columns build once, and each solve() may bring per-call
        facts (given=) that leave nothing behind.

            route = m.prepare(S.path(V.a, V.b), where=V.a != ...)
            route.solve()
            route.solve(given=[S.edge(S.x, S.y)])
        """
        return Prepared(self, [_to_atom(p) for p in patterns],
                        None if where is None else _to_atom(where))

    # -------------------------------------------------------------- evaluation

    def eval(self, target: Any) -> list[Atom]:
        """Evaluate a term, returning every answer.

        This is what !(...) runs, minus the printing: the engine's
        translate_expr over the term, then its goals. Nondeterminism means
        the list can hold any number of answers, including none.
        """
        wires = self._rt.apply_must(
            "petta_py_eval_all", self._space, _to_atom(target).to_wire()
        )
        return [from_wire(w) for w in wires]

    # -------------------------------------------------------------- operations

    def op(
        self,
        fn: Callable | None = None,
        *,
        name: str | None = None,
        typed: bool = True,
        raw: bool = False,
        pass_atoms: bool = False,
        arities: list[int] | None = None,
    ):
        """Register a Python callable as a MeTTa function, decorator-style.

            @m.op
            def double(x: int) -> int:
                return 2 * x                    # !(double 21) -> 42

            @m.op
            def neighbours(n: int):
                yield n - 1                     # a generator is nondeterministic
                yield n + 1

        Annotations become a (: ...) declaration unless typed=False. A raw
        operation skips the wire encoding both ways, which suits tensor and
        number work; symbols reach it as plain strings, so keep raw off when
        the symbol-string distinction matters. pass_atoms hands the callable
        Atom objects instead of decoded Python values.
        """

        def apply(f: Callable) -> Callable:
            return _ops_module.register(
                self._rt,
                f,
                name=name,
                typed=typed,
                raw=raw,
                pass_atoms=pass_atoms,
                space=self._space,
                arities=arities,
            )

        return apply(fn) if fn is not None else apply

    def unregister(self, name: str) -> None:
        """Remove a registered operation, every arity of it."""
        _ops_module.unregister(self._rt, name)

    # -------------------------------------------------------------- inspection

    def builtins(self) -> list[str]:
        """Every function name the engine has registered."""
        return self._rt.builtins()

    def is_function(self, name: str) -> bool:
        return bool(self._rt.once("petta_py_is_function(Name)", Name=name))

    def is_function_here(self, name: str) -> bool:
        """Whether a function would answer from THIS space: it has clauses
        this space's module sees, its own or the shared ones in user.
        Another space's equations are invisible here and do not count."""
        return bool(
            self._rt.once(
                "petta_py_function_visible(Space, Name)", Space=self._space, Name=name
            )
        )

    def arities(self, name: str) -> list[int]:
        """Compiled predicate arities for a name: MeTTa arity plus one each."""
        row = self._rt.once("petta_py_arities(Name, As)", Name=name)
        return list(row.get("As", []))

    # ----------------------------------------------------------- subscriptions

    def subscribe(
        self,
        pattern: Any,
        callback: Callable | None = None,
        *,
        on: str = "add",
    ):
        """A standing query on this space: every added (or removed, or
        both) atom unifying with the pattern becomes an Event.

            seen = []
            sub = m.subscribe(S.order(V.id), lambda e: seen.append(e))
            m.add(S.order(1))          # seen[0].bindings["id"] == 1
            sub.cancel()

        With a callback, delivery is synchronous, inside the write that
        caused it (the callback may write back; the engine re-enters
        cleanly; an infinite add-triggers-add loop is the author's own).
        Without one, events queue on the subscription and drain() empties
        them: the mailbox reading. Removal events for plain atoms may fire
        for atoms that were never stored, since the engine's removal is
        retractall; re-check the space rather than trust the event.
        """
        from .subscribe import subscribe as _subscribe

        return _subscribe(self._rt, self._space, _to_atom(pattern), callback, on)

    # ------------------------------------------------------------- diagnostics

    def derivation(self, target: Any, depth: int = 30) -> list[Derivation]:
        """Every proof of an answer, as trees in MeTTa terms.

        Each tree names the equations that fired and the stored atoms at the
        leaves, read from the translated_from links the engine keeps for
        every compiled clause. Meta-interpreted, so slower than evaluation;
        a diagnostic, not an evaluation path. Depth bounds the SEARCH, and
        an evaluation error inside a proof surfaces as itself rather than
        as an empty proof list.
        """
        if depth <= 0:
            raise ValueError(
                f"derivation depth must be positive, got {depth}: a zero "
                f"budget would answer no proofs for everything"
            )
        rows = self._rt.iter(
            "petta_py_derivation(Space, W, D, T)",
            Space=self._space,
            W=_to_atom(target).to_wire(),
            D=depth,
        )
        return [Derivation.from_atom(from_wire(r["T"])) for r in rows]

    def why(self, pattern: Any) -> str:
        """Why a pattern matches nothing here, in words.

        Checks the cheap explanations in order: unknown function, wrong
        arity, no stored atoms with that head. Honest when it cannot tell.
        """
        atom = _to_atom(pattern)
        if not isinstance(atom, Expr) or not atom.children:
            return f"{atom} is not an expression pattern"
        head = atom.head
        if not isinstance(head, Sym):
            return f"the pattern head {head} is not a symbol"
        name = head.name
        stored = [
            a
            for a in self.atoms()
            if isinstance(a, Expr) and isinstance(a.head, Sym) and a.head.name == name
        ]
        if stored:
            sizes = sorted({len(a) for a in stored})
            if len(atom) not in sizes:
                return (
                    f"{name} atoms here have {sizes} elements; the pattern has "
                    f"{len(atom)}"
                )
            return (
                f"{len(stored)} {name} atom(s) exist here but none unifies with "
                f"{atom}"
            )
        if self.is_function(name):
            return (
                f"no {name} atoms are stored here; {name} is a function, so its "
                f"answers come from evaluation, not matching: try eval"
            )
        return f"nothing here is headed by {name}, and no function has that name"

    # ------------------------------------------------------------ definitions

    def define(self, fn: Callable):
        """Compile a Python function into MeTTa equations, decorator-style.

        Written for whoever is fluent in Python rather than s-expressions:
        the body is read as syntax and lowered deterministically, refusals
        name the construct, the line and what to write instead, and the
        original stays reachable as .py, a twin the equations can be checked
        against on any ground input.

            @m.define
            def fact(n):
                if n == 0:
                    return 1
                return n * fact(n - 1)

            m.run("!(fact 5)")          # [[120]]
            fact.py(5)                  # 120, ordinary Python

        A generator compiles to nondeterminism (each yield one answer), a
        lambda to the engine's own |->, a comprehension to map-atom and
        filter-atom, and match(Pattern(x, y), template) to a match against
        the running space, lowercase free names in the pattern binding as
        variables.
        """
        from ._ops import REGISTRY
        from .define import (
            Defined,
            canonical_aux,
            compile_function,
            hazard_twin,
            twin_dispatcher,
        )
        from .errors import CompileError
        from .ops import (
            class_declarations,
            declaration_exprs,
            referenced_classes,
            resolved_annotations,
        )

        def nondet(called: str) -> bool:
            for spelling in (called, called.replace("_", "-")):
                operation = REGISTRY.get(spelling)
                if operation is not None and operation.kind in ("many", "raw_many"):
                    return True
                if (self._space, spelling) in _DEFINED_GENERATORS:
                    return True
            return False

        # The equation's name follows the operation rule: underscores read
        # as hyphens, one policy across both decorators.
        name = fn.__name__.replace("_", "-")
        compiled = compile_function(
            fn, known=self.is_function, nondet=nondet, metta_name=name
        )
        params, patterns, body = compiled.params, compiled.patterns, compiled.body
        # Clause stacking is per (space, name), process-wide: equations live
        # in the space, not in whichever MeTTa instance happened to add them.
        earlier = _DEFINE_CLAUSES.setdefault((self._space, name), [])
        first_clause = not earlier
        if not earlier and self.is_function_here(name):
            raise CompileError(
                f"{name!r} is already a function this space answers (an "
                f"engine builtin, an operation, or an equation): defining it "
                f"would stack a clause onto it and the existing definition "
                f"would keep answering first. Pick another name, or add the "
                f"equation deliberately with m.run.",
                construct="name collision",
            )
        if patterns and any(not clause["patterns"] for clause in earlier):
            raise CompileError(
                f"a clause of {name} with a literal head comes after the "
                f"general clause, which already matches everything; define "
                f"the general clause last",
                construct="clause order",
            )
        # MeTTa equations are alternatives, and a Python author stacking
        # clauses means first-match, so each clause is guarded against every
        # earlier literal head it would otherwise also answer for. The guard
        # is ordinary MeTTa, visible in .source(), never a hidden rule.
        body = _guard_against(
            body, [clause["patterns"] for clause in earlier], patterns, params
        )
        head = Expr(
            [Sym(name), *(patterns.get(p, Var(p)) for p in params)]
        )
        equation = Expr([Sym("="), head, body])
        dispatcher = twin_dispatcher(fn)
        # Idempotence compares with auxiliary helper names canonicalized:
        # every compilation serials its helpers, so the same source re-run
        # must be recognized through the renaming.
        canonical = canonical_aux(equation, name)
        clause_twin = (
            hazard_twin(name, compiled.hazards) if compiled.hazards else compiled.twin
        )
        replaced = None
        for position, clause in enumerate(earlier):
            if alpha_eq(canonical_aux(clause["equation"], name), canonical):
                # The identical clause again, a re-run cell or module
                # reload: adding it would duplicate answers, so it stands.
                return Defined(
                    name, params, body, dispatcher, self,
                    patterns=patterns, runtime_ops=compiled.runtime_ops,
                )
            if clause["patterns"] == patterns:
                replaced = position
        if replaced is not None:
            # The same head with a new body is a redefinition of that
            # clause, the notebook reading; the old equation goes, the new
            # one takes its place in both the space and the twin dispatch.
            self.remove(earlier[replaced]["equation"])
            earlier[replaced] = {"patterns": dict(patterns), "equation": equation}
            dispatcher.clauses[replaced] = clause_twin
        else:
            earlier.append({"patterns": dict(patterns), "equation": equation})
            dispatcher.clauses.append(clause_twin)
        for helper_equation in compiled.aux:
            self.add(helper_equation)
        self.add(equation)
        if first_clause:
            # The function reflects into the library's own space, one fact
            # per (space, name), following the space through clear().
            self._rt.must(
                "petta_py_add(Space, W)",
                Space=_ops_module.REFLECTION_SPACE,
                W=Expr([Sym("defined"), Sym(self._space), Sym(name)]).to_wire(),
            )
        # Annotations declare the type, exactly as they do for operations,
        # once per name so stacked clauses do not repeat the declaration.
        annotated = resolved_annotations(fn)
        if any(k != "return" for k in annotated) and not _DECLARED_DEFINES.get(
            (self._space, name)
        ):
            import inspect as _inspect

            annotations = [
                annotated.get(p, _inspect.Parameter.empty) for p in params
            ]
            ret_annotation = annotated.get("return", _inspect.Parameter.empty)
            for declaration in declaration_exprs(name, annotations, ret_annotation):
                self.add(declaration)
            for cls in referenced_classes([*annotations, ret_annotation]):
                for extra in class_declarations(cls):
                    self.add(extra)
            _DECLARED_DEFINES[(self._space, name)] = True
        if compiled.generator:
            _DEFINED_GENERATORS.add((self._space, name))
        return Defined(
            name, params, body, dispatcher, self,
            patterns=patterns, runtime_ops=compiled.runtime_ops,
        )

    def type(self, cls: type | None = None, *, accessors: bool = True):
        """Declare a Python class INTO this space, decorator-style: the
        (: ...) declarations land as atoms, and an expression-image class
        (a dataclass, a NamedTuple) also gains one accessor equation per
        field, so the structure is not merely visible but reasoned over.

            @m.type
            @dataclass
            class Person:
                name: str
                age: int

            m.add(encode := petta.convert.project(Person("Ada", 36)).atom)
            m.run("!(Person-age (Person \\"Ada\\" 36))")     # [[36]]

        An Enum declares its members; get-type sees them all. Returns the
        class, so it stacks under @dataclass.
        """
        from . import convert as _convert

        def apply(target: type) -> type:
            registration = _convert.ensure_registered(target)
            for declaration in _convert.declarations(target):
                self.add(declaration)
            if (
                accessors
                and registration.image == "expression"
                and registration.fields
            ):
                constructor = registration.type_name
                fields = registration.fields
                variables = [Var(f"f{i}") for i in range(1, len(fields) + 1)]
                for position, field_name in enumerate(fields):
                    head = Expr(
                        [
                            Sym(f"{constructor}-{field_name}"),
                            Expr([Sym(constructor), *variables]),
                        ]
                    )
                    self.add(Expr([Sym("="), head, variables[position]]))
            return target

        return apply(cls) if cls is not None else apply

    def fn(self, name: str) -> "_EngineFunction":
        """Any engine function as an ordinary Python callable.

            car = m.fn("car-atom")
            car(m.parse("(1 2 3)"))     # 1
            m.fn("superpose").all(expr(1, 2, 3))   # [1, 2, 3]

        Calling expects exactly one answer and raises otherwise, the loud
        reading; .all returns every answer, nondeterminism included.
        """
        return _EngineFunction(self, name)

    # ---------------------------------------------------------- integrations

    def integrate(self, target: Any) -> str:
        """Install a library integration; see petta.integrate."""
        from . import integrate as _integrate

        return _integrate.integrate(self, target)

    def register_space(self, name: str, provider: Any) -> Any:
        """A space answered by Python: matches, adds and removals route to
        the provider, so a table, a dataframe or a service is matchable the
        way stored atoms are. See petta.foreign.SpaceProvider."""
        from .foreign import register_provider

        register_provider(self._rt, name, provider)
        return provider

    def unregister_space(self, name: str) -> None:
        from .foreign import unregister_provider

        unregister_provider(self._rt, name)

    # ------------------------------------------------------------ interop

    @property
    def runtime(self) -> Runtime:
        """The engine bridge itself, for callers going under the surface."""
        return self._rt


def _serializable(atom: Atom) -> bool:
    from .atoms import Gnd

    stack = [atom]
    while stack:
        current = stack.pop()
        if isinstance(current, Gnd) and not isinstance(
            current.value, (bool, int, float, str)
        ):
            return False
        if isinstance(current, Expr):
            stack.extend(current.children)
    return True


def _guard_against(body: Atom, earlier: list, patterns: dict, params: list) -> Atom:
    """The current clause's body, declining every earlier literal head.

    For each earlier clause, the inputs it claims are the positions it fixed
    with literals; when this clause leaves all of those positions variable,
    the two overlap, and this clause answers (empty) there, so dispatch reads
    first-match the way the stacked Python reads.
    """
    from .atoms import Gnd

    for earlier_patterns in earlier:
        if not earlier_patterns:
            continue
        overlapping = all(
            p not in patterns or patterns[p] == v for p, v in earlier_patterns.items()
        )
        contested = [p for p in earlier_patterns if p not in patterns]
        if not overlapping or not contested:
            continue
        condition: Atom | None = None
        for p in contested:
            test = Expr([Sym("=="), Var(p), earlier_patterns[p]])
            condition = test if condition is None else Expr([Sym("and"), condition, test])
        body = Expr([Sym("if"), condition, Expr([Sym("empty")]), body])
    return body


class _Assuming:
    """Facts scoped to a with-block; see MeTTa.assuming."""

    __slots__ = ("_space", "_facts")

    def __init__(self, space: MeTTa, facts: list[Atom]) -> None:
        self._space = space
        self._facts = facts

    def __enter__(self) -> MeTTa:
        self._space.add(*self._facts)
        return self._space

    def __exit__(self, exc_type, exc, tb) -> None:
        for fact in self._facts:
            self._space.remove(fact)


class Prepared:
    """A prepared query: pattern wires and columns built once, solved many
    times, optionally with per-call facts. The ladder the clingo API walks
    (assumptions per solve, inputs per session, rules added), with the rung
    clingo lacks: rules REMOVED, since this engine erases clauses whole.

        route = m.prepare(S.path(V.a, V.b))
        route.solve()
        route.solve(given=[S.edge(S.a, S.b)])   # facts for this call only
    """

    __slots__ = ("_space", "_patterns", "_where", "_wires", "_guard", "columns")

    def __init__(self, space: MeTTa, patterns: list[Atom], where: Atom | None) -> None:
        self._space = space
        self._patterns = patterns
        self._where = where
        self._wires = [p.to_wire() for p in patterns]
        self._guard = None if where is None else where.to_wire()
        columns: list[str] = []
        for pattern in patterns:
            for name in variables(pattern):
                if name != "_" and name not in columns:
                    columns.append(name)
        self.columns = tuple(columns)

    def solve(self, given: list | None = None, limit: int | None = None) -> Rows:
        """Answers now, with `given` facts present for this call alone."""
        if not given:
            return self._run(limit)
        with self._space.assuming(*given):
            return self._run(limit)

    def _run(self, limit: int | None) -> Rows:
        rt = self._space.runtime
        if self._guard is not None:
            row = rt.once(
                "petta_py_query_guarded_all(Space, Ps, G, Names, Limit, Rows)",
                Space=self._space.space_name,
                Ps=self._wires,
                G=self._guard,
                Names=list(self.columns),
                Limit=limit or 0,
            )
        elif limit is not None:
            row = rt.once(
                "petta_py_query_limit_all(Space, Ps, Names, Limit, Rows)",
                Space=self._space.space_name,
                Ps=self._wires,
                Names=list(self.columns),
                Limit=limit,
            )
        else:
            row = rt.once(
                "petta_py_query_all(Space, Ps, Names, Rows)",
                Space=self._space.space_name,
                Ps=self._wires,
                Names=list(self.columns),
            )
        decoded = [tuple(from_wire(v) for v in r) for r in row.get("Rows", [])]
        return Rows(self.columns, decoded)

    def __repr__(self) -> str:
        shown = ", ".join(str(p) for p in self._patterns)
        return f"<prepared {shown} -> {', '.join(self.columns)}>"


class _EngineFunction:
    """One engine function, callable the way Python callables are."""

    __slots__ = ("_space", "_name")

    def __init__(self, space: MeTTa, name: str) -> None:
        self._space = space
        self._name = name

    def _term(self, args: tuple) -> Expr:
        return Expr([Sym(self._name), *(encode(a) for a in args)])

    def __call__(self, *args: Any) -> Any:
        answers = self._space.eval(self._term(args))
        if len(answers) != 1:
            raise ValueError(
                f"({self._name} ...) answered {len(answers)} results; calling "
                f"expects exactly one. Use .all(...) for every answer."
            )
        return answers[0]

    def all(self, *args: Any) -> list:
        return self._space.eval(self._term(args))

    def __repr__(self) -> str:
        return f"<engine function {self._name} on {self._space.space_name}>"
