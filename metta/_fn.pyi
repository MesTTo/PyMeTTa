# Purpose: declare every generated fn attribute to static type checkers.
# Guarantees:
#   - every safe runtime alias is explicit and no dynamic Any fallback exists
#     [tested: test_the_fn_namespace_is_generated; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
#   - operator word aliases are explicit members generated from the runtime
#     catalog [tested: test_operator_words_precede_the_mechanical_name_map;
#     commit=8ec44dec3cafba5981e7cf712749cca0e1bdcc45]
#   - catalog-row documentation is attached to explicit members for static
#     help [tested: test_generated_fn_help_is_offline; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
#   - INTERNAL names have no static member while their exact runtime bracket
#     door remains available [tested:
#     test_internal_catalog_names_stay_exact_but_leave_public_outputs;
#     commit=8779452fed89853c3f77c3469f7a6ec7b12e9efa]
# Open Obligations:
#   To Do: None
#   Hacks: None
#   Future Enhancements: None.

from collections.abc import Callable
from typing import Final

from .atoms import Expression, Symbol

class _FunctionNamespace:
    abs_math: Symbol
    "abs-math: (-> Number Number)\n\nPython's builtin `abs`."
    acos_math: Symbol
    "acos-math: (-> Number Number)\n\n`math.acos`."
    add: Symbol
    "+: (-> Number Number Number)\n\nPython's own operator. On atoms the same operator builds `(+ ...)` instead of computing, which is how a compiled body reaches the MeTTa function."
    add_atom: Symbol
    "add-atom: (-> SpaceType Atom (->))\n\n`space += atom`, the container protocol. A plain Python tuple encodes to an expression on the way in, so a fact needs no builder ceremony. Bare symbols, grounded values, and empty expressions cross when engine `add-atom` accepts them too."
    add_atoms: Symbol
    "add-atoms: (-> SpaceType Expression (->))\n\nThe same `+=` door, once per fact: anything that yields tuples is a fact stream. Lists, outer tuples of rows, generators, SQL cursors, and dataframe row iterators each write one atom per yielded item; a built Expression is always one atom."
    add_reduct: Symbol
    "add-reduct: (-> SpaceType %Undefined% (->))\n\nThere is no second door: `+=` adds what you give it, so adding a REDUCT is explicit composition, `space += m.eval(term)[0]`. Bare grounded answers use that door directly; this row wraps the evaluated sum only to retain its `total` relation head."
    add_reducts: Symbol
    "add-reducts: (-> SpaceType %Undefined% (->))\n\nThe plural of the same composition: evaluate, then write the answers."
    add_translator_rule: Symbol
    add_typing_rule: Symbol
    alpha_unique: Symbol
    alpha_unique_atom: Symbol
    and_then: Symbol
    annotation: Symbol
    append: Symbol
    argv: Symbol
    asin_math: Symbol
    "asin-math: (-> Number Number)\n\n`math.asin`."
    atan_math: Symbol
    "atan-math: (-> Number Number)\n\n`math.atan`."
    atom_subst: Symbol
    "atom-subst: (-> Atom (:Atom Variable) Atom Atom)\n\nApplying a substitution to a template, which `Atom.map` does over the whole term. Section 9e wants the bindings object to carry it, `b.apply(template)`; `metta.Bindings` has no such method yet, so the walker is the spelling."
    atomically: Symbol
    bind: Symbol
    "bind!: (-> Symbol %Undefined% (->))\n\nA Python name binding. `space = metta.space(...)` is exactly what a token binding was for, and Python's own scoping rules then apply."
    bit_and: Symbol
    bit_not: Symbol
    bit_or: Symbol
    bit_shift_left: Symbol
    bit_shift_right: Symbol
    bit_xor: Symbol
    call: Symbol
    car_atom: Symbol
    "car-atom: (-> Expression %Undefined%)\n\nIndexing. An expression is a sequence in Python, so its head is `e[0]`."
    case: Symbol
    "case: (-> Atom Expression %Undefined%)\n\nPython's `match` statement. A bare variable arm is `case _`."
    catch: Symbol
    cdr_atom: Symbol
    "cdr-atom: (-> Expression Expression)\n\nSlicing. `e[1:]` answers a Python tuple today rather than an Expression, which prints the same and is the T6 friction section 9e names as this bucket's one prerequisite."
    ceil_math: Symbol
    "ceil-math: (-> Number Number)\n\n`math.ceil`, which answers an integer in Python 3 where a float-preserving float."
    chain: Symbol
    "chain: (-> Atom Variable Atom %Undefined%)\n\nPython assignment. Chain executes one instruction, binds, substitutes and continues, which is exactly `x = m.eval(t)[0]` followed by use of `x`."
    change_state: Symbol
    "change-state!: (-> (StateMonad $tcso) $tcso Bool)\n\nAssigning `state.value` writes the same typed engine cell and reading it back returns the replacement. The WRITE answers True rather than the cell, which is upstream's own answer -- `'change-state!'(Var, Value, true)` [source: PeTTa@ae66fa8 src/metta.pl:265] -- so the read is a separate step here as it is in Python."
    collapse: Symbol
    "collapse: (-> Atom Atom)\n\n`list()` is the everyday spelling, materialising the answers; `tuple()` is the same act when you want MeTTa's own `( )` atom back, which is what collapse answers."
    collapse_bind: Symbol
    "collapse-bind: (-> Atom Expression)\ncollapse-bind: (TU Expression)\n\nThe deep-tier collapse that keeps each alternative's BINDINGS, `((a (bindings ...)) ...)`. It belongs to the bindings-carrying tier, never to the surface; MeTTa's engine has the bindings carrier (`answer_bindings`) but not this instruction."
    cons: Symbol
    cons_atom: Symbol
    "cons-atom: (-> Atom Expression Atom)\n\nConstruction: call the head, or rebuild from head and tail with `*`."
    context_space: Symbol
    "context-space: (-> SpaceType)\n\nThe space a program is currently in, which in Python is the handle it holds; `metta.current_space()` is the door for code that did not receive one, and it follows Python's own `current_thread` and `current_task` convention, so the Python word wins over the instruction's name. The row asks both sides for the current space's atoms."
    cos_math: Symbol
    "cos-math: (-> Number Number)\n\n`math.cos`."
    current_time: Symbol
    cut: Symbol
    declare_post_add: Symbol
    declare_pre_add: Symbol
    decons: Symbol
    decons_atom: Symbol
    "decons-atom: (-> Expression Atom)\n\nStarred unpacking, which is the same act in one line: `head, *tail = e`."
    defined_name: Symbol
    dif: Symbol
    documented: Symbol
    documented_space: Symbol
    elapsed: Symbol
    empty: Symbol
    eq: Symbol
    "==: (-> $t $t Bool)\n\nPython's own operator, and atoms compare structurally under it."
    error_payload: Symbol
    eval: Symbol
    "eval: (-> Atom Atom)\n\nONE step. `m.eval(term)` is the same one step and answers every result, and `space.eval(term)` is `evalc`, the same step in a named space."
    evalc: Symbol
    "evalc: (-> Atom SpaceType Atom)\n\nOne step WITH an explicit context space, which is `space.eval(term)`: the signature IS term plus space."
    exclude_item: Symbol
    exp: Symbol
    exp_math: Symbol
    explain: Symbol
    filter_atom: Symbol
    "filter-atom: (-> Expression Variable Atom Expression)\nfilter-atom: (-> Expression Expression Expression)\n\nA comprehension with an `if`, or `filter`."
    first: Symbol
    first_from_pair: Symbol
    floor_div: Symbol
    floor_math: Symbol
    "floor-math: (-> Number Number)\n\n`math.floor`, the same integer-against-float difference as `ceil-math`."
    foldall: Symbol
    foldl: Symbol
    foldl_atom: Symbol
    "foldl-atom: (-> Expression Atom Variable Variable Atom %Undefined%)\nfoldl-atom: (-> Expression Atom Expression %Undefined%)\n\n`functools.reduce` with an initial value is the same finite left fold. For a change stream, `m.events().fold(..., under=algebra)` makes the algebra itself the step; `into=State(...)` is the running-gauge form."
    for_each_in_atom: Symbol
    "for-each-in-atom: (-> Expression Atom (->))\n\nA `for` statement. It is called for its effect, so the row prints and answers the unit. Python's `for` has no value at all, and the concept map says `None` IS the unit, but `metta.ground(None)` renders `<NoneType>` rather than `()` today, so a row that wants the unit writes it [measured 2026-08-22]."
    forall: Symbol
    format_args: Symbol
    "format-args: (-> String Expression String)\n\nAn f-string. MeTTa's `{}` holes are Python's own interpolation."
    format_time: Symbol
    function: Symbol
    "function: (-> Atom Atom)\n\nThe core's function frame, which `return` closes. MeTTa's compiled definitions do not go through this instruction and it is not implemented."
    ge: Symbol
    ">=: (-> Number Number Bool)\n\nPython's own operator."
    get_atoms: Symbol
    "get-atoms: (-> SpaceType Atom)\n\n`space.atoms()`, or `for atom in space` when you want to walk them."
    get_doc: Symbol
    "get-doc: (-> SpaceType Atom %Undefined%)\n\nPython's builtin `help`, over the docstring a decorated function already carries. This engine answers nothing here because no documentation atoms are written yet, which is the doc-vocabulary gap."
    get_doc_space: Symbol
    get_metatype: Symbol
    "get-metatype: (-> Atom Atom)\n\nPython's own builtin `type`: the four atom classes ARE the four metatypes, so `type(a).__name__` is the metatype by construction."
    get_state: Symbol
    "get-state: (-> (StateMonad $tgso) $tgso)\n\nReading the cell is the typed handle's `state.value` property."
    get_type: Symbol
    "get-type: (-> Atom %Undefined%)\n\nDeclared types are space-relative, so `space.type(atom)` asks the space. Class declarations use the consolidated `@space.define` decorator."
    get_type_space: Symbol
    "get-type-space: (-> SpaceType Atom Atom)\n\nThe same question asked of a named space through that handle's `space.type(atom)` method."
    git_import: Symbol
    "git-import!: (-> String String Atom)\n\npip and `importlib`. Fetching a dependency is packaging's job, the module catalog IS Python packaging, and a boot manifest names the distribution."
    gt: Symbol
    ">: (-> Number Number Bool)\n\nPython's own operator."
    has_declared_type: Symbol
    help: Symbol
    "help!: (-> Atom (->))\nhelp!: (-> (->))\n\nPython's builtin `help`, which is the same act on the same docstring."
    hyperpose: Symbol
    id: Symbol
    "id: (-> $t $t)\n\nThe identity function, which Python writes as the value itself."
    if_equal: Symbol
    "if-equal: (-> Atom Atom Atom Atom %Undefined%)\n\nA conditional expression over `==`."
    if_equal2: Symbol
    if_error: Symbol
    "if-error: (-> Atom Atom Atom %Undefined%)\n\n`try`/`except`, or a conditional over the value. It is the railway combinator over Error atoms."
    implies: Symbol
    include: Symbol
    "include: (-> Atom %Undefined%)\n\n`space.load(path)` reads a file into that space, which is what include does; Python's own `import` is the spelling for a Python module."
    index_atom: Symbol
    "index-atom: (-> Expression Number Atom)\n\nIndexing again, with the index you want."
    inferences: Symbol
    intersection: Symbol
    "intersection: (-> Atom Atom %Undefined%)\n\n`collections.Counter` IS the multiset algebra, and `&` is its intersection."
    intersection_atom: Symbol
    "intersection-atom: (-> Expression Expression Atom)\n\n`Counter` over children, answering an expression."
    is_alpha_member: Symbol
    is_expr: Symbol
    is_function: Symbol
    "is-function: (-> Type Bool)\n\nAsking whether a type is an arrow. In Python the same question is asked of the annotation, and `m.is_function(name)` asks it of a defined name."
    is_ground: Symbol
    is_member: Symbol
    is_space: Symbol
    is_var: Symbol
    isinf_math: Symbol
    "isinf-math: (-> Number Bool)\n\n`math.isinf`."
    isnan_math: Symbol
    "isnan-math: (-> Number Bool)\n\n`math.isnan`."
    last: Symbol
    le: Symbol
    "<=: (-> Number Number Bool)\n\nPython's own operator."
    length: Symbol
    let: Symbol
    "let: (-> Atom %Undefined% Atom %Undefined%)\n\nAssignment. It reads in MeTTa's own order, bind then use, which is why plain assignment and not the walrus is the taught spelling."
    library: Symbol
    log_math: Symbol
    "log-math: (-> Number Number Number)\n\n`math.log(x, base)`, with the arguments the other way round: MeTTa takes the base first."
    lt: Symbol
    "<: (-> Number Number Bool)\n\nPython's own operator."
    map_atom: Symbol
    "map-atom: (-> Expression Variable Atom Expression)\nmap-atom: (-> Expression Expression Expression)\n\nA comprehension, or `map`. The variable and the template are the comprehension's own binder and body."
    maplist: Symbol
    match: Symbol
    "match: (-> SpaceType Atom Atom %Undefined%)\n\n`space[pattern]` is the subscript door and `space.match(pattern)` the named one; the TEMPLATE is built in Python from the answer's bindings. `under=counting|tropical|prov|ranked` changes the annotation algebra; `answers(call, under=...)` is its call twin, `with metta.under(...)` scopes the default, and an annotated answer exposes `.annotation`, `.why()` and `.under(other)` without a re-query. `metta.algebra(...)` constructs arbitrary carriers while remaining their namespace."
    match_types: Symbol
    max: Symbol
    max_atom: Symbol
    "max-atom: (-> %Undefined% Number)\n\nPython's builtin `max` over the children."
    member: Symbol
    metta: Symbol
    "metta: (-> Atom Type SpaceType Atom)\n\nThe full interpreter, which is what CALLING does: a defined object called from Python evaluates, and `m.eval` on a built term is the same act."
    metta_thread: Symbol
    min: Symbol
    min_atom: Symbol
    "min-atom: (-> %Undefined% Number)\n\nPython's builtin `min` over the children."
    mm2_exec: Symbol
    mod: Symbol
    "%: (-> Number Number Number)\n\nPython's own operator. Both take the sign of the divisor for a positive divisor; a Euclidean `%` differs on a NEGATIVE divisor, which parts them and `mod-floor` is the name for Python's convention."
    mork_add_atoms: Symbol
    mork_flush: Symbol
    msort: Symbol
    mul: Symbol
    "*: (-> Number Number Number)\n\nPython's own operator."
    ne: Symbol
    neg: Callable[[object], Expression]
    new_space: Symbol
    "new-space: (-> SpaceType)\n\n`metta.space()`. A constructor call is Python's own spelling for `make me a fresh one`, and the row asks the fresh space for its atoms because the NAME a space gets differs per engine."
    new_state: Symbol
    "new-state: (-> $t (StateMonad $t))\n\n`metta.State[T](value, space=space)` creates the typed Python handle. The row reads `.value` because the engine cell itself is deliberately hidden behind that handle. An event `fold(..., into=state)` passes this same process-shared cell to its step; individual reads and writes are thread-safe, but a compound read-modify-write needs coordination."
    noeval: Symbol
    "noeval: (-> Atom Atom)\n\nThe same point as `quote`: a built term is already unevaluated."
    nop: Symbol
    "nop: (-> (%Rest% %Undefined%) (->))\n\nPython's `pass`, or simply not writing the call. It answers the unit."
    noreduce_eq: Symbol
    "noreduce-eq: (-> Atom Atom Bool)\n\nComparing two atoms WITHOUT reducing them is what Python's `==` on atoms already does: building a term never evaluates it."
    not_provable: Symbol
    once: Symbol
    or_else: Symbol
    parse: Symbol
    parse_command: Symbol
    pow: Symbol
    "pow-math: (-> Number Number Number)\n\nPython's `**` operator. MeTTa answers a float where Python's integer power answers an integer, so the row raises a float."
    pow_math: Symbol
    "pow-math: (-> Number Number Number)\n\nPython's `**` operator. MeTTa answers a float where Python's integer power answers an integer, so the row raises a float."
    pragma: Symbol
    pretty_atom: Symbol
    println: Symbol
    "println!: (-> %Undefined% Bool)\n\nPython's `print`. It answers True rather than unit, which is upstream's own answer: `'println!'(Arg, true)` [source: PeTTa@ae66fa8 src/metta.pl:212]."
    prog1: Symbol
    progn: Symbol
    py_at: Symbol
    py_atom: Symbol
    py_call: Symbol
    py_container_kind: Symbol
    py_dict: Symbol
    py_dict_pairs: Symbol
    py_dot: Symbol
    py_eq: Symbol
    py_format: Symbol
    py_global_read: Symbol
    py_global_write: Symbol
    py_in: Symbol
    py_iter: Symbol
    py_len: Symbol
    py_list: Symbol
    py_operator: Symbol
    py_range: Symbol
    py_repr: Symbol
    py_round: Symbol
    py_set: Symbol
    py_set_pairs: Symbol
    py_slice: Symbol
    py_str: Symbol
    py_str_join: Symbol
    py_truthy: Symbol
    py_tuple: Symbol
    quote: Symbol
    "quote: (-> Atom Atom)\n\nThere is nothing to quote: building a term at the `S.` door never evaluates it, so the quoting question does not arise. `S.quote(x)` builds the term itself where a program needs the constructor."
    random_float: Symbol
    random_int: Symbol
    read_form: Symbol
    readln: Symbol
    reduce: Symbol
    register_token: Symbol
    remove_atom: Symbol
    "remove-atom: (-> SpaceType Atom Bool)\n\nDrains every atom that unifies and answers True either way. `del space[pattern]` is this door, and raises when the pattern matches nothing as Python's `del` does; `subtract-atom` is the one-occurrence grain beside it, which `space -= atom` and `space.remove(atom)` both spell."
    remove_translator_rule: Symbol
    remove_typing_rule: Symbol
    repr: Symbol
    repra: Symbol
    require_extension: Symbol
    residual_goals: Symbol
    return_on_error: Symbol
    "return-on-error: (-> Atom Atom %Undefined%)\n\nEarly return, which is Python's own `return` inside an `if`. Indexing needs the guard because a leaf atom is not indexable here."
    reverse: Symbol
    round_math: Symbol
    "round-math: (-> Number Number)\n\nNOT Python's `round`: `round` breaks a tie to the EVEN neighbour, so `round(2.5)` is 2 where MeTTa answers 3. Half away from zero is `math.floor(x + 0.5)` for a positive number."
    sealed: Symbol
    "sealed: (-> Expression Atom Atom)\n\nFreshening every variable except a named few, the hygiene primitive under rule emission. The Python surface makes most uses unnecessary by construction, because a parameter-scoped rule is fresh per rule, so the row shows the law spelling."
    second_from_pair: Symbol
    sin_math: Symbol
    "sin-math: (-> Number Number)\n\n`math.sin`."
    size_atom: Symbol
    "size-atom: (-> Expression Number)\n\n`len`. Both count CHILDREN, so `(f a b)` is 3 either way."
    sleep: Symbol
    sort: Symbol
    sort_atom: Symbol
    sort_strings: Symbol
    "sort-strings: (-> Expression Expression)\n\nPython's builtin `sorted`. A tuple goes back in as one expression."
    space_admission_verdict: Symbol
    space_atom_count: Symbol
    space_contains: Symbol
    sqrt_math: Symbol
    "sqrt-math: (-> Number Number)\n\n`math.sqrt`."
    sread: Symbol
    sub: Symbol
    "-: (-> Number Number Number)\n\nPython's own operator."
    subtract_atom: Symbol
    "subtract-atom: (-> SpaceType Atom Bool)\n\nTakes ONE unifying occurrence and answers whether one was there, the multiset subtraction `remove-atom` gave up when it took upstream's draining law. `space -= atom` is this door, because Python's in-place difference over a multiset is `collections.Counter`'s, which subtracts the multiplicity given rather than clearing the key, and `space.remove(atom)` is the same grain reporting what it found. An unbound atom is refused by name rather than read as every atom at once."
    subtraction: Symbol
    "subtraction: (-> Atom Atom %Undefined%)\n\n`Counter` again, with `-`."
    subtraction_atom: Symbol
    "subtraction-atom: (-> Expression Expression Atom)\n\n`Counter` over children, answering an expression."
    super: Symbol
    superpose: Symbol
    "superpose: (-> Expression %Undefined%)\n\nNondeterminism has no primitive of its own because Python's iteration IS it: a list of values is a multiset of answers, and `yield` is the same act inside a compiled body. `space.sample(q, k=10, seed=7)` is the weighted choice door, with replacement and implicit `(rate n)` weights."
    superpose_bind: Symbol
    "superpose-bind: (-> Expression Atom)\n\nThe inverse of `collapse-bind`: it restores each alternative WITH its recorded bindings, which is a different operation from `superpose`."
    switch: Symbol
    "switch: (-> %Undefined% Expression %Undefined%)\n\nPython's `match` statement again. `switch` differs from `case` only in evaluating its subject first, which a Python expression does anyway."
    take: Symbol
    tan_math: Symbol
    "tan-math: (-> Number Number)\n\n`math.tan`."
    test: Symbol
    test_no_answer: Symbol
    throw: Symbol
    timeout: Symbol
    top: Symbol
    trace: Symbol
    "trace!: (-> %Undefined% Atom %Undefined%)\n\n`print` or `logging` beside the value; `m.trace()` is the engine's own reduction trace, a different and deeper thing."
    transaction: Symbol
    truediv: Symbol
    "/: (-> Number Number Number)\n\nPython's `/` is true division, and so is this engine's. An integer `/` is EUCLIDEAN by its own ruling, so `(/ 7 2)` is 3 there and 3.5 here; on floats all three agree."
    trunc_math: Symbol
    "trunc-math: (-> Number Number)\n\n`math.trunc`, or `int` on a float."
    type_cast: Symbol
    type_cast_holds: Symbol
    undeclare_post_add: Symbol
    undeclare_pre_add: Symbol
    undocumented: Symbol
    undocumented_space: Symbol
    unify: Symbol
    "unify: (-> Atom Atom Atom Atom %Undefined%)\n\nStructural unification. `metta.unify(a, b)` symmetrically answers one substitution keyed by the VARIABLES, which is what `atom.subs` takes, or `None`; `metta.unify(a, b, then, els)` evaluates the engine conditional, running `then` once per binding set and `els` only when none exists. A compiled body lowers the same four-argument call directly to the engine form."
    union: Symbol
    "union: (-> Atom Atom %Undefined%)\n\nMultiset union over nondeterministic answers, which is concatenation: answers are iterables and `+` joins them."
    union_atom: Symbol
    "union-atom: (-> Expression Expression Atom)\n\nThe same act over an expression's children; a tuple goes back in as one expression."
    unique: Symbol
    "unique: (-> Atom %Undefined%)\n\n`dict.fromkeys` is Python's order-preserving dedupe."
    unique_atom: Symbol
    "unique-atom: (-> Expression Atom)\n\n`dict.fromkeys` over children."
    unquote: Symbol
    "unquote: (-> %Undefined% %Undefined%)\n\nReducing a quoted term is `m.eval`, primitive 4."
    unregister_token: Symbol
    with_pragma: Symbol
    with_seed: Symbol
    xor: Symbol
    "xor: (-> Bool Bool Bool)\n\nPython's `^` on booleans."
    def __getitem__(self, name: str, /) -> Symbol: ...

fn: Final[_FunctionNamespace]
