% Purpose: MeTTa's Python surface. `py-atom` RESOLVES where `py-call` APPLIES,
%   and everything else follows from that split: a Python callable becomes a
%   value MeTTa can hold, pass and apply, an attribute can be read without
%   calling it, a dotted path of any depth resolves, and Python's containers
%   can be built from MeTTa rather than only received.
% Assumes:
%   - janus is present. Every predicate here calls Python on its first use and
%     none of them runs at load time, so a program that never touches Python
%     pays only this file's load [tested: a_name_resolves_to_an_object].
%   - src/petta_py.py sits beside this file and imports nothing from the
%     `petta` package, because the engine runs with janus alone.
% Guarantees:
%   - values crossing this surface stay OBJECTS. Nothing is flattened, drained
%     or stringified on the way back, so a generator keeps its laziness and a
%     million-element array costs the same as a small one
%     [measured 2026-08-16: a handle is O(1) where converting 100,000 elements
%     is 1,905 us, and the gap grows with the data]
%     [tested: iteration_is_lazy].
%   - a resolved callable is applicable in head position, through the engine's
%     metta_grounded_apply/3 seam rather than through anything Python-specific
%     [tested: a_resolved_callable_is_applicable], and a grounded value that is
%     not an operation stays unreduced rather than raising
%     [tested: a_grounded_value_that_is_not_callable_stays_unreduced].
% Fails when:
%   - a name does not resolve, which raises rather than answering nothing: a
%     typo in a module path is a mistake, not an empty result.
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- multifile metta_grounded_apply/3.
:- multifile metta_grounded_structure/2.
:- multifile metta_grounded_text/2.

%This surface is hyperon-experimental's, and PeTTa had none of it: `py-atom`,
%`py-dot`, `py-list`, `py-tuple`, `py-dict` and `Kwargs` are what the language's
%own tutorials teach, and every one of them ran unreduced here
%[source: metta-lang-docs/learn__tutorials__python_use__py_atom.md].
%
%`py-call` stays exactly as it is, and the reason is not taste: it is UPSTREAM
%PeTTa's, so it is one of the few things here that carries a compatibility
%constraint. It appears nowhere in those tutorials and it converts by janus's
%defaults, which is why a dict arrives as an atom and a generator arrives
%drained. This surface has no such constraint and does not repeat any of it.

%The bridge module lives beside this file, and janus's own py_add_lib_dir/1 is
%how a library ships Python for itself. Deferred to first use rather than run at
%load time, so an engine that never calls Python never imports anything.
%The directory is captured at LOAD time, because prolog_load_context/2 has
%nothing to say once loading is over and this runs on first use.
:- dynamic petta_py_ready/0.
:- dynamic petta_py_dir/1.
:- prolog_load_context(directory, Dir), assertz(petta_py_dir(Dir)).

petta_py_bridge :- petta_py_ready, !.
petta_py_bridge :- petta_py_dir(Dir),
                   py_add_lib_dir(Dir),
                   assertz(petta_py_ready).

%Everything crosses as an OBJECT. That is the whole policy of this surface and
%it is why it composes: resolving gives an atom, applying an atom gives an atom,
%and a program says when it wants MeTTa data by asking for it. janus converts
%None, True, False, int, float, str and tuple regardless of this flag, so a
%scalar answer is still a scalar [measured 2026-08-16].
petta_py_opts([py_object(true), py_string_as(string)]).

petta_py(Call, Goal, Result) :-
    petta_py_bridge,
    petta_py_opts(Opts),
    petta_py_guard(Call, py_call(petta_py:Goal, Raw, Opts)),
    petta_py_result(Raw, Result).

%%%% Failure %%%%

%A Python exception becomes a MeTTa error rather than janus's term, and the
%shape is the engine's own: (Error Formal Context), with the failing MeTTa call
%as the context. Both slots have to hold something a program can read, and
%janus's holds neither: the formal carries the live exception OBJECT and the
%context a live traceback object, so `(catch (boom))` answered
%
%  (Error (python_error ZeroDivisionError ZeroDivisionError('division by zero'))
%         (context $_ (python_stack <traceback object at 0x7da166550>)))
%
%which names an address, cannot be compared, and says nothing about which MeTTa
%call failed. It now answers
%
%  (Error (python_error ZeroDivisionError "division by zero") (<callable> 1 0))
%
%so a program branches on the class, reads the message, and sees its own call.
%
%A control signal is NOT converted. An interrupt, a time limit and an inference
%limit stay uncatchable, which is a guarantee the engine makes and tests: "A
%program's own (catch ...) cannot eat the signal either"
%[source: python/tests/test_control_signals.py]. KeyboardInterrupt arrives from
%Python as an ordinary python_error and would have been converted into a
%catchable one, which is the same hole by another door.
petta_py_guard(Call, Goal) :-
    catch(Goal, Error, petta_py_failure(Call, Error)).

petta_py_failure(_, Error) :- control_exception(Error), !, throw(Error).
petta_py_failure(_, error(python_error(Class, _), _)) :-
    petta_py_signal_class(Class), !,
    throw(petta_py_interrupted).
petta_py_failure(Call, error(python_error(Class, Value), _)) :- !,
    petta_py_exception_message(Value, Message),
    throw(error(python_error(Class, Message),
                context(Call, 'while calling Python'))).
petta_py_failure(_, Error) :- throw(Error).

petta_py_signal_class('KeyboardInterrupt').
petta_py_signal_class('SystemExit').

:- multifile prolog:message//1.

%What an UNCAUGHT one prints. janus's own rendering names the Python function,
%the Python file and the Python line, and no MeTTa call at all, so a failure
%three levels down a MeTTa program pointed only at Python and the reader had to
%guess which call reached it.
%
%The guard is the trap this file inherits from the engine's own message
%clauses: janus throws python_error/2 with an UNBOUND context, so a head that
%binds the context would claim every ordinary janus error and rename it. Two
%things separate ours: petta_error_context/3 reads a context WITHOUT writing to
%it, which is the engine's own guard against exactly this, and the message has
%already been rendered to a string where janus's second argument is the live
%exception object [tested: a_python_failure_names_the_metta_call].
prolog:message(error(python_error(Class, Message), Context)) -->
    { petta_error_context(Context, Call, 'while calling Python'),
      string(Message),
      swrite(Call, CallText) },
    [ 'Python ~w in ~w'-[Class, CallText], nl, '  ~w'-[Message] ],
    python_unbound_argument(Call).

%The failure a Python operation gives when asked to run BACKWARDS reads as a
%Python internals error. `(let (pconcat $h $t) (1 2 3) ...)` puts the operation
%in a pattern position, the unbound variables cross, and Python says "Value
%after * must be an iterable, not Var", from which nothing points at the actual
%mistake. Naming the positions does.
%
%It is a note on a failure that has already happened rather than a check before
%the call, and that distinction is the whole design. An unbound argument is not
%an error in itself: _decode_arg says so in as many words, "symbols, variables
%and expressions stay atoms, which is the structure an operation may want to
%inspect", so an operation written to take a pattern apart is a legitimate one
%and refusing before the call would break it. Only the operations that cannot
%serve the position fail, and only those get the note
%[tested: test_an_unbound_argument_is_named_when_python_fails].
python_unbound_argument(Call) -->
    { is_list(Call), Call = [_|Arguments],
      findall(Position,
              ( nth1(Position, Arguments, Argument), \+ ground(Argument) ),
              Positions),
      Positions \== [] },
    !,
    { unbound_argument_phrase(Positions, Phrase) },
    [ nl, '  ~w unbound, so the operation ran in a pattern position; a \c
           Python operation runs forwards only'-[Phrase] ].
python_unbound_argument(_) --> [].

unbound_argument_phrase([Position], Phrase) :- !,
    format(atom(Phrase), 'argument ~w was', [Position]).
unbound_argument_phrase(Positions, Phrase) :-
    atomic_list_concat(Positions, ', ', Listed),
    format(atom(Phrase), 'arguments ~w were', [Listed]).

%str() of the exception, which is the message without the class name repeated.
%Rendering can itself fail, a __str__ raising being the obvious way, and the
%error being reported must not be replaced by the error of reporting it.
petta_py_exception_message(Value, Message) :-
    petta_py_opts(Opts),
    (   catch(py_call(builtins:str(Value), Text, Opts), _, fail)
    ->  Message = Text
    ;   Message = "the exception's own __str__ raised"
    ).

%%%% What a Python value IS, once it is in MeTTa %%%%

%janus converts three constants no matter what py_object(true) says, and hands
%each of them back in a spelling that is janus's rather than MeTTa's. These are
%the only three, and each has an exact MeTTa counterpart already
%[measured 2026-08-16: None, True and False are the whole of it; int, float and
%str already arrive as themselves].
%
%None is the UNIT value, `()`, and not `Empty`. The difference decides whether
%a method called for effect works at all: `Empty` is a Symbol meaning no answer,
%so `(let $x ((py-dot lst append) 3) ...)` would FAIL for every one of the many
%Python methods that return None, while `()` is an Expression of size 0 that a
%let binds [measured 2026-08-16: (get-metatype ()) is Expression, (get-metatype
%Empty) is Symbol, (== () Empty) is false].
%
%It is also the language's own answer for an operation that runs for effect:
%"bind! returns the unit value () similar to println! or add-atom"
%[source: the language's Working with spaces]. hyperon-experimental reaches it
%independently, which is worth recording because this did not come from there:
%`if result is None: return [Atoms.UNIT]` in python/hyperon/atoms.py, and
%UNIT_ATOM is `metta_const!(())`, asserted equal to `Atom::expr([])`, in
%lib/src/metta/mod.rs.
petta_py_result('@'(none), Unit) :- !, Unit = [].
petta_py_result('@'(true), true) :- !.
petta_py_result('@'(false), false) :- !.
petta_py_result(Value, Value).

%%%% The structural view %%%%

%A Python tuple crosses as the Prolog compound -/N, which is janus's encoding
%and is faithful in BOTH directions: `(1, (2, 3))` is `1-(2-3)`, and handing
%`1-2` back to Python yields a real tuple, class and all
%[measured 2026-08-16]. So the tuple needs no handle and no rebuilding, and its
%structural reading costs no crossing at all: the elements are already there.
%
%That reading is what makes `(car-atom (py-atom "(1, 2)"))` answer 1 while the
%same value still passes into Python as a tuple. Neither reading is a separate
%answer; see metta_grounded_structure/2 in src/ext_points.pl.
%
%Elements are normalized because the VIEW is MeTTa's reading of the value: a
%None inside a tuple reads as `()` here. The carrier itself is left exactly as
%janus made it, because that is what has to go back.
metta_grounded_structure(Tuple, Elements) :-
    petta_py_tuple_arguments(Tuple, Raw),
    maplist(petta_py_result, Raw, Elements).

%And a Python object that IS a sequence, which costs a crossing because the
%elements live on the other side. PEP 634's rule decides which objects qualify;
%src/petta_py.py carries it.
%
%The length is asked first and separately. A pattern of fixed shape is rejected
%by its length without pulling a single element, so matching `($x $y)` against
%a million-element list costs one crossing rather than a million.
metta_grounded_structure(Obj, Elements) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    petta_py_bridge,
    py_call(petta_py:sequence_length(Obj), Length),
    Length >= 0,
    (   is_list(Elements)
    ->  length(Elements, Length)
    ;   true
    ),
    findall(E, 'py-iter'(Obj, E), Elements).

%The arity check comes FIRST and separately, because
%compound_name_arguments/3 BUILDS the argument list before it can report the
%name, so asking it about a compound that is not a tuple allocates a list per
%call and throws it away. compound_name_arity/3 reads the functor and allocates
%nothing, and this is consulted for every term the writer meets that is not a
%MeTTa expression.
%
%An earlier version of this comment put a number on that, 402 million
%instructions on alpha-unique. The number was wrong and is withdrawn: that
%benchmark was bimodal at the time and the measurement was cluster assignment
%rather than cause [see python/benchmarks/baseline.json, alpha-unique's
%instruction_noise_comment]. Doing less work before failing is still right; it
%is just not worth 10%.
petta_py_tuple_arguments(Tuple, Arguments) :-
    compound(Tuple),
    compound_name_arity(Tuple, -, _),
    compound_name_arguments(Tuple, -, Arguments).

%%%% Display %%%%

%repr, so a Python value says what it is instead of naming an address. A tuple
%is rendered here rather than crossing for it, because -/N already holds the
%elements and Python would only spell them back.
metta_grounded_text(Tuple, Text) :-
    petta_py_tuple_arguments(Tuple, Raw),
    !,
    maplist(petta_py_element_text, Raw, Parts),
    atomic_list_concat(Parts, ', ', Inner),
    (   Raw = [_]
    ->  format(string(Text), "(~w,)", [Inner])   %Python's own 1-tuple spelling
    ;   format(string(Text), "(~w)", [Inner])
    ).
metta_grounded_text(Obj, Text) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    petta_py_bridge,
    py_call(petta_py:render(Obj), Text).

petta_py_element_text(Element, Text) :-
    (   metta_grounded_text(Element, Text0)
    ->  Text = Text0
    ;   swrite(Element, Text)
    ).

%%%% Resolution %%%%

%(py-atom numpy.absolute)          a module attribute
%(py-atom numpy.random.randint)    an attribute of a submodule, any depth
%(py-atom len)                     a builtin
%(py-atom "[1, 2, 3]")             a Python EXPRESSION, evaluated
%
%A STRING argument is an expression and a SYMBOL is a name, which is the
%distinction the language's own surface draws and the reason both fit in one
%operator.
'py-atom'(Spec, Result) :- petta_py_resolve(Spec, Result).

%(py-atom f Type) DECLARES what the resolved atom is, and the declaration is
%kept rather than accepted and dropped. Everything arriving from Python is
%%Undefined% otherwise, so a Python function could not participate in typed
%dispatch, be checked, or be reported by get-type as anything at all.
%
%It goes through py_object_extra_type/2, the extension point that already
%exists for exactly this: "a protocol the object satisfies may name a type".
%A declared type is one more candidate beside the object's own class walk,
%so `(get-type (py-atom numpy.absolute (-> Number Number)))` answers the
%declaration AND the object still answers its Python classes.
%A declared type of `Expression` or `Grounded` says which READING is wanted, and
%those are the language's own metatypes rather than anything invented here.
%Grounded is a live reference: identity kept, mutations visible, O(1) to hold,
%and every structural read of it crosses. Expression is a snapshot: it costs the
%whole value once and is ordinary MeTTa data afterwards, so it destructures,
%unifies and stores like anything else. That is the materialised-view trade, and
%it is why janus converts exactly Python's IMMUTABLE types by itself: for a
%value that cannot change the two readings are the same value, which is why a
%tuple needs no choice here.
%
%The lazy reading in between is `py-iter`, which is `superpose` for a Python
%sequence, and `(collapse (py-iter x))` is its `collapse`. Nothing here is a new
%way to say something MeTTa could not already say.
'py-atom'(Spec, Type, Result) :-
    petta_py_resolve(Spec, Resolved),
    (   var(Type)
    ->  Result = Resolved
    ;   Type == 'Expression'
    ->  petta_py_materialize(Resolved, Result)
    ;   Result = Resolved,
        assert_declared_python_type(Result, Type)
    ).

%The snapshot, all the way down: every level that has a structural view becomes
%an expression, and a value that has none is a leaf and stays itself. A numpy
%array is a Sequence so it materializes; a dict, a set and an arbitrary object
%are leaves.
%
%Deep rather than one level, because a declared Expression that turned out to
%hold handles one layer down would be neither reading. One level is spelled
%`(collapse (py-iter x))` and is still there for anyone who wants it.
petta_py_materialize(Value, Expression) :-
    petta_py_materialize_(Value, [], Expression).

petta_py_materialize_(Value, Seen, Expression) :-
    (   metta_grounded_structure(Value, Elements)
    ->  petta_py_cycle_check(Value, Seen, Deeper),
        maplist(petta_py_materialize_r(Deeper), Elements, Expression)
    ;   Expression = Value
    ).

petta_py_materialize_r(Seen, Value, Expression) :-
    petta_py_materialize_(Value, Seen, Expression).

%A Python container may hold itself, and materializing one is not a slow answer
%but no answer: it recurses until the stack goes. Say so instead, because the
%value is fine and only this reading of it is impossible.
petta_py_cycle_check(Value, Seen, [Id|Seen]) :-
    (   python_object_blob(Value),
        py_is_object(Value)
    ->  py_call(builtins:id(Value), Id),
        (   memberchk(Id, Seen)
        ->  throw(error(petta_cyclic_python_value(Value),
                        context('py-atom'/3,
                                'a value that contains itself has no \c
                                 Expression reading; hold it as Grounded')))
        ;   true
        )
    ;   Id = Value            %a tuple is finite by construction
    ).

:- dynamic petta_py_declared_type/2.
:- multifile py_object_extra_type/2.

%Keyed on the object, and recorded once: resolving the same name twice gives
%the same Python object, so a repeated (py-atom f T) must not stack duplicate
%type candidates and make get-type answer twice.
assert_declared_python_type(Obj, Type) :-
    (   petta_py_declared_type(Obj, Existing), Existing == Type
    ->  true
    ;   assertz(petta_py_declared_type(Obj, Type))
    ).

py_object_extra_type(Obj, Type) :- petta_py_declared_type(Obj, Type).

petta_py_resolve(Spec, Result) :-
    (   string(Spec)
    ->  petta_py(['py-atom', Spec], evaluate(Spec), Result)
    ;   atom(Spec)
    ->  petta_py(['py-atom', Spec], resolve(Spec), Result)
    ;   throw(error(type_error(python_name, Spec),
                    context('py-atom'/2,
                            'a symbol names a Python object and a string is a \c
                             Python expression')))
    ).

%(py-dot obj attr) READS an attribute. py-call's `.name` spelling always calls,
%so a property, a bound method taken as a value, or a plain field needed
%getattr by hand.
'py-dot'(Obj, Attr, Result) :- petta_py(['py-dot', Obj, Attr], dot(Obj, Attr), Result).

%%%% Construction %%%%

%MeTTa could receive Python's containers and not build them. `(py-list (1 2 3))`
%and its siblings close that, and they take a MeTTa expression rather than a
%variadic call so that a computed list works: `(py-list (collapse (foo)))`.
'py-list'(Items, Result) :- petta_py_items(Items, 'py-list', List),
                            petta_py(['py-list', Items], build_list(List), Result).
'py-tuple'(Items, Result) :- petta_py_items(Items, 'py-tuple', List),
                             petta_py(['py-tuple', Items], build_tuple(List), Result).
'py-dict'(Pairs, Result) :- petta_py_items(Pairs, 'py-dict', List),
                            maplist(petta_py_pair, List, Converted),
                            petta_py(['py-dict', Pairs], build_dict(Converted), Result).

petta_py_items(Items, Who, List) :-
    (   is_list(Items)
    ->  maplist(py_arg_norm, Items, List)
    ;   throw(error(type_error(expression, Items),
                    context(Who/2, 'takes one expression of items')))
    ).

petta_py_pair(Pair, [Key, Value]) :-
    (   Pair = [Key0, Value0]
    ->  py_arg_norm(Key0, Key), py_arg_norm(Value0, Value)
    ;   throw(error(type_error(pair, Pair),
                    context('py-dict'/2, 'takes two-element pairs')))
    ).

%%%% Application %%%%

%A resolved callable applied in head position, which is what makes the surface
%higher-order: `((py-atom numpy.absolute) -5)`, a Python function passed to
%map-atom, a torch module held in a space.
%
%The engine consults this only for a head that is neither a function name nor a
%partial application, so an ordinary MeTTa call never reaches it. Failing is how
%a grounded value that is NOT an operation stays unreduced, which is what a
%value should do.
metta_grounded_apply(Obj, Args, Result) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    petta_py_bridge,
    py_call(petta_py:is_callable(Obj), @true),
    petta_py_split_kwargs(Args, Positional0, Kwargs),
    maplist(py_arg_norm, Positional0, Positional),
    petta_py_opts(Opts),
    petta_py_guard([Obj|Args],
                   py_call(petta_py:apply(Obj, Positional, Kwargs), Raw, Opts)),
    petta_py_result(Raw, Result).

:- multifile metta_grounded_applicable/1.

%The same blob-first guard protects every runtime probe in this file
%(structure, text, apply, the cycle check), because each of them is
%consulted with plain engine terms on ordinary paths: a nested-call data
%shape reaches metta_grounded_apply/3, and probing its list head with
%py_is_object/1 booted CPython inside examples/spaces/matchnested.metta,
%~104M instructions for a four-atom program [measured 2026-08-17].
%The blob test comes FIRST because it is the one that costs nothing:
%py_is_object/1 "fails silently" on a non-object [source: janus.pl doc,
%py_is_object/1], but janus initialises lazily on its first call, so
%probing a plain integer here booted CPython, ~104M instructions, inside
%typed-call TRANSLATION of every literal argument. The types_dependent
%example paid 3.4x upstream's whole run for it [measured 2026-08-17:
%148.2M net instructions to 44M after this guard]. blob/2 is SWI-side
%introspection and never touches janus.
metta_grounded_applicable(Obj) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    petta_py_bridge,
    py_call(petta_py:is_callable(Obj), @true).

%(Kwargs (start 2) (stop 10)) in the argument list, which is the language's own
%spelling. Anything before it is positional.
petta_py_split_kwargs(Args, Positional, Kwargs) :-
    (   append(Positional, [['Kwargs'|Pairs]], Args)
    ->  maplist(petta_py_kwarg, Pairs, Converted),
        dict_pairs(Kwargs, py, Converted)
    ;   Positional = Args, Kwargs = py{}
    ).

%The pair arrives unevaluated, so the NAME is a name and the VALUE is whatever
%was written. Evaluating the value here is what keeps `(Kwargs (n (+ 1 2)))`
%meaning 3 while `(Kwargs (reverse true))` still means the keyword `reverse`.
petta_py_kwarg([Name, Value0], Name-Value) :-
    !,
    (   is_list(Value0), Value0 \== []
    ->  reduce(Value0, Evaluated, _)
    ;   Evaluated = Value0
    ),
    py_arg_norm(Evaluated, Value).
petta_py_kwarg(Other, _) :-
    throw(error(type_error(keyword_argument, Other),
                context('Kwargs'/1, 'takes (name value) pairs'))).

%%%% Iteration %%%%

%(py-iter obj) yields one element at a time, nondeterministically, which is
%MeTTa's own way of expressing a sequence and the reason nothing here has to be
%drained: `(collapse (py-iter x))` is the whole list when a program wants it,
%`(car-atom (collapse ...))` is one step, and an infinite iterator still works
%under a bound.
%
%py_iter/2 is janus's lazy path and backtracks with one-item lookahead.
'py-iter'(Obj, Element) :-
    petta_py_bridge,
    petta_py_opts(Opts),
    petta_py_guard(['py-iter', Obj], py_iter(petta_py:iterate(Obj), Raw, Opts)),
    petta_py_result(Raw, Element).
