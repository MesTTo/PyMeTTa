"""Purpose: the MeTTa runtime surface. One class binds a space name to the
process's engine and offers running source, loading files, structured space
edits, conjunctive queries, evaluation, Python-backed operations, proof-tree
derivations and a why-not diagnostic, all in PeTTa's own semantics.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from . import ops as _ops_module
from ._engine import Runtime, runtime
from .atoms import Atom, Expr, Sym, Var, encode, from_wire, parse, variables
from .derivation import Derivation
from .results import Rows

__all__ = ["MeTTa"]


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
        self._declared_defines: dict[str, bool] = {}
        self._define_clauses: dict[str, list[dict]] = {}

    # ------------------------------------------------------------------ naming

    @property
    def space_name(self) -> str:
        return self._space

    def space(self, name: str) -> "MeTTa":
        """Another space on the same engine."""
        return MeTTa(name)

    def fresh_space(self) -> "MeTTa":
        """An anonymous space with a name nothing else is using."""
        row = self._rt.once("petta_py_new_space(Name)")
        return MeTTa(row["Name"])

    def __repr__(self) -> str:
        return f"MeTTa({self._space!r})"

    # ----------------------------------------------------------------- running

    def run(self, source: str) -> list[list[Atom]]:
        """Run MeTTa source: one list of answers per ! directive.

        The pipeline is the engine's own reader, compiler and evaluator, so
        the answers are exactly what the CLI would print, kept grouped per
        directive instead of flattened. Equations and facts in the source
        land in this space.
        """
        row = self._rt.once("petta_py_run(Src, Space, Groups)", Src=source, Space=self._space)
        return [[from_wire(w) for w in group] for group in row.get("Groups", [])]

    def load(self, path: str) -> list[list[Atom]]:
        """Load a .metta file the way the CLI does, working directory included."""
        row = self._rt.once("petta_py_load(File, Space, Groups)", File=str(path), Space=self._space)
        return [[from_wire(w) for w in group] for group in row.get("Groups", [])]

    def parse(self, source: str) -> Atom:
        """Read one form into an atom without evaluating it."""
        return parse(source)

    # ------------------------------------------------------------- space edits

    def add(self, *atoms: Any) -> None:
        """Add atoms to this space. An (= ...) atom compiles as an equation."""
        for a in atoms:
            self._rt.once(
                "petta_py_add(Space, W)", Space=self._space, W=_to_atom(a).to_wire()
            )

    def remove(self, atom: Any) -> bool:
        """Remove an atom, engine semantics: an equation removal reports
        whether it existed; a plain atom removal removes every copy."""
        row = self._rt.once(
            "petta_py_remove(Space, W, R)", Space=self._space, W=_to_atom(atom).to_wire()
        )
        result = from_wire(row["R"])
        return bool(getattr(result, "value", True))

    def atoms(self) -> list[Atom]:
        """Every stored atom in this space."""
        row = self._rt.once("petta_py_atoms(Space, Ws)", Space=self._space)
        return [from_wire(w) for w in row.get("Ws", [])]

    def count(self) -> int:
        row = self._rt.once("petta_py_count(Space, N)", Space=self._space)
        return int(row["N"])

    def __len__(self) -> int:
        return self.count()

    def __contains__(self, atom: Any) -> bool:
        row = self._rt.once(
            "petta_py_contains(Space, W)", Space=self._space, W=_to_atom(atom).to_wire()
        )
        return bool(row)

    def clear(self) -> None:
        """Remove everything stored here, compiled equations included."""
        self._rt.once("petta_py_clear(Space)", Space=self._space)

    def __iadd__(self, atom: Any) -> "MeTTa":
        self.add(atom)
        return self

    # ----------------------------------------------------------------- queries

    def query(self, *patterns: Any) -> Rows:
        """Match patterns against this space as one conjunction.

        Variables shared between patterns join, the engine's own match/4
        doing the joining. Columns are the variable names in first
        appearance order.

            m.query(S.Edge(V.x, V.y), S.Edge(V.y, V.z))
        """
        atoms = [_to_atom(p) for p in patterns]
        columns: list[str] = []
        for a in atoms:
            for name in variables(a):
                if name not in columns:
                    columns.append(name)
        row = self._rt.once(
            "petta_py_query_all(Space, Ps, Names, Rows)",
            Space=self._space,
            Ps=[a.to_wire() for a in atoms],
            Names=columns,
        )
        decoded = [tuple(from_wire(v) for v in r) for r in row.get("Rows", [])]
        return Rows(tuple(columns), decoded)

    # -------------------------------------------------------------- evaluation

    def eval(self, target: Any) -> list[Atom]:
        """Evaluate a term, returning every answer.

        This is what !(...) runs, minus the printing: the engine's
        translate_expr over the term, then its goals. Nondeterminism means
        the list can hold any number of answers, including none.
        """
        row = self._rt.once(
            "petta_py_eval_all(Space, W, Es)",
            Space=self._space,
            W=_to_atom(target).to_wire(),
        )
        return [from_wire(w) for w in row.get("Es", [])]

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

    def arities(self, name: str) -> list[int]:
        """Compiled predicate arities for a name: MeTTa arity plus one each."""
        row = self._rt.once("petta_py_arities(Name, As)", Name=name)
        return list(row.get("As", []))

    # ------------------------------------------------------------- diagnostics

    def derivation(self, target: Any, depth: int = 30) -> list[Derivation]:
        """Every proof of an answer, as trees in MeTTa terms.

        Each tree names the equations that fired and the stored atoms at the
        leaves, read from the translated_from links the engine keeps for
        every compiled clause. Meta-interpreted, so slower than evaluation;
        a diagnostic, not an evaluation path.
        """
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
        from .define import Defined, compile_function
        from .errors import CompileError
        from .ops import metta_type_for

        params, patterns, body, twin = compile_function(fn, known=self.is_function)
        name = fn.__name__
        earlier = self._define_clauses.setdefault(name, [])
        if patterns and any(not e for e in earlier):
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
        body = _guard_against(body, earlier, patterns, params)
        earlier.append(dict(patterns))
        head = Expr(
            [Sym(name), *(patterns.get(p, Var(p)) for p in params)]
        )
        self.add(Expr([Sym("="), head, body]))
        # Annotations declare the type, exactly as they do for operations,
        # once per name so stacked clauses do not repeat the declaration.
        annotated = fn.__annotations__
        if any(k != "return" for k in annotated) and not self._declared_defines.get(name):
            arg_types = [
                Sym(metta_type_for(annotated[p])) if p in annotated else Sym("%Undefined%")
                for p in params
            ]
            ret = Sym(metta_type_for(annotated["return"])) if "return" in annotated else Sym("%Undefined%")
            self.add(Expr([Sym(":"), Sym(name), Expr([Sym("->"), *arg_types, ret])]))
            self._declared_defines[name] = True
        return Defined(name, params, body, twin, self, patterns=patterns)

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
