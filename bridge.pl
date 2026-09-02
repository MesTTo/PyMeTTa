% Purpose: MeTTa's Python surface. `py-atom` RESOLVES where `py-call` APPLIES,
%   and everything else follows from that split: a Python callable becomes a
%   value MeTTa can hold, pass and apply, an attribute can be read without
%   calling it, a dotted path of any depth resolves, and Python's containers
%   can be built from MeTTa rather than only received.
% Assumes:
%   - janus is present. Every predicate here calls Python on its first use and
%     none of them runs at load time, so a program that never touches Python
%     pays only this file's load [tested: a_name_resolves_to_an_object].
%   - metta_py.py sits beside this file and imports nothing from the
%     `metta` package, because the engine runs with janus alone.
% Guarantees:
%   - values crossing this surface stay OBJECTS. Nothing is flattened, drained
%     or stringified on the way back, so a generator keeps its laziness and a
%     million-element array costs the same as a small one
%     [measured 2026-08-16: a handle is O(1) where converting 100,000 elements
%     is 1,905 us, and the gap grows with the data]
%     [tested: iteration_is_lazy].
%   - a resolved callable is applicable in head position, through the engine's
%     seam:grounded_apply/3 seam rather than through anything Python-specific
%     [tested: a_resolved_callable_is_applicable], and a grounded value that is
%     not an operation stays unreduced rather than raising
%     [tested: a_grounded_value_that_is_not_callable_stays_unreduced].
%   - a Python tuple has one default structural answer at both host doors,
%     while an explicit Grounded reading is retained as a Python object
%     reference [tested: test_a_python_tuple_answers_the_same_through_both_doors;
%     commit=89374a7ed8eec75e26ea595f2c6e55665f80d6fc].
%   - a py-atom type declaration follows its value through a Python round trip
%     without a process-global Prolog fact owning the Python object [tested:
%     test_a_py_atom_declaration_dies_with_its_grounded_value;
%     commit=bbf02dd309d15e178a9c83d03b749eb7170b6a20].
% Fails when:
%   - a name does not resolve, which raises rather than answering nothing: a
%     typo in a module path is a mistake, not an empty result.
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- use_module(library(janus)).
%crypto_data_hash/3 names a Python import's cached module key below. It used
%to arrive through engine/filereader.pl's import into the one namespace the
%whole engine shared; a binding declares what it calls, so it is declared here
%[measured 2026-08-22, under NO_AUTOLOAD=1 once the loader became a module].
:- use_module(library(crypto), [crypto_data_hash/3]).

:- multifile seam:grounded_apply/3.
:- multifile seam:grounded_numeric/1.
:- multifile seam:grounded_numeric_operation/3.
:- multifile seam:grounded_structure/2.
:- multifile seam:grounded_text/2.

%This surface is hyperon-experimental's, and this engine had none of it: `py-atom`,
%`py-dot`, `py-list`, `py-tuple`, `py-dict` and `Kwargs` are what the language's
%own tutorials teach, and every one of them ran unreduced here
%[source: metta-lang-docs/learn__tutorials__python_use__py_atom.md].
%
%`py-call` stays exactly as it is, and the reason is not taste: it is UPSTREAM
%MeTTa's, so it is one of the few things here that carries a compatibility
%constraint. It appears nowhere in those tutorials and it converts by janus's
%defaults, which is why a dict arrives as an atom and a generator arrives
%drained. This surface has no such constraint and does not repeat any of it.

%The bridge module lives beside this file, and janus's own py_add_lib_dir/1 is
%how a library ships Python for itself. Deferred to first use rather than run at
%load time, so an engine that never calls Python never imports anything.
%The directory is captured at LOAD time, because prolog_load_context/2 has
%nothing to say once loading is over and this runs on first use.
:- dynamic metta_py_ready/0.
:- dynamic metta_py_dir/1.
:- prolog_load_context(directory, Dir), assertz(metta_py_dir(Dir)).

metta_py_bridge :- metta_py_ready, !.
metta_py_bridge :- metta_py_dir(Dir),
                   py_add_lib_dir(Dir),
                   assertz(metta_py_ready).

%Everything crosses as an OBJECT. That is the whole policy of this surface and
%it is why it composes: resolving gives an atom, applying an atom gives an
%atom, and a program says when it wants MeTTa data by asking for it. Current
%Janus converts None and only exact bool, int, float, str and tuple values
%under this option; primitive subclasses remain references, which is the
%identity law this bridge requires [tested:
%extensions/python/tests/ch03_atoms_and_expressions/test_identity_wire.py;
%commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f].
metta_py_opts([py_object(true), py_string_as(string)]).

metta_py_call(Call, Goal, Result) :-
    metta_py_bridge,
    metta_py_opts(Opts),
    metta_py_guard(Call, py_call(metta_py:Goal, Raw, Opts)),
    metta_py_result(Raw, Result).

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
%program's own (catch ...) cannot eat the signal either" [source:
%extensions/python/tests/ch07_control_flow/test_control_signals.py].
%KeyboardInterrupt arrives from Python as an ordinary python_error and would
%have been converted into a catchable one, which is the same hole by another
%door.
metta_py_guard(Call, Goal) :-
    catch(Goal, Error, metta_py_failure(Call, Error)).

metta_py_failure(_, Error) :- control_exception(Error), !, throw(Error).
metta_py_failure(_, error(python_error(Class, _), _)) :-
    metta_py_signal_class(Class), !,
    throw(metta_host_interrupted).
metta_py_failure(Call, error(python_error(Class, Value), _)) :- !,
    metta_py_exception_message(Value, Message),
    throw(error(python_error(Class, Message),
                context(Call, 'while calling Python'))).
metta_py_failure(_, Error) :- throw(Error).

metta_py_signal_class('KeyboardInterrupt').
metta_py_signal_class('SystemExit').

:- multifile prolog:message//1.

%What an UNCAUGHT one prints. janus's own rendering names the Python function,
%the Python file and the Python line, and no MeTTa call at all, so a failure
%three levels down a MeTTa program pointed only at Python and the reader had to
%guess which call reached it.
%
%The guard is the trap this file inherits from the engine's own message
%clauses: janus throws python_error/2 with an UNBOUND context, so a head that
%binds the context would claim every ordinary janus error and rename it. Two
%things separate ours: metta_error_context/3 reads a context WITHOUT writing to
%it, which is the engine's own guard against exactly this, and the message has
%already been rendered to a string where janus's second argument is the live
%exception object [tested: a_python_failure_names_the_metta_call].
prolog:message(error(python_error(Class, Message), Context)) -->
    { metta_error_context(Context, Call, 'while calling Python'),
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
metta_py_exception_message(Value, Message) :-
    metta_py_opts(Opts),
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
metta_py_result('@'(none), Unit) :- !, Unit = [].
metta_py_result('@'(true), true) :- !.
metta_py_result('@'(false), false) :- !.
metta_py_result(Value, Value).

%%%% The structural view %%%%

%A Python tuple crosses by default as the Prolog compound -/N, which is
%janus's encoding and is faithful in BOTH directions: `(1, (2, 3))` is
%`1-(2-3)`, and handing `1-2` back to Python yields a real tuple, class and all
%[measured 2026-08-16]. Its default structural reading therefore costs no
%crossing: the elements are already there. An explicit Grounded request takes
%a separate path below, because Janus converts an exact tuple even when
%py_object(true) asks for a reference.
%
%That reading is what makes `(car-atom (py-atom "(1, 2)"))` answer 1 while the
%same value still passes into Python as a tuple. Neither reading is a separate
%answer; see seam:grounded_structure/2 in engine/ext_points.pl.
%
%Elements are normalized because the VIEW is MeTTa's reading of the value: a
%None inside a tuple reads as `()` here. The carrier itself is left exactly as
%janus made it, because that is what has to go back.
seam:grounded_structure(Tuple, Elements) :-
    metta_py_tuple_arguments(Tuple, Raw),
    maplist(metta_py_result, Raw, Elements).

%And a Python object that IS a sequence, which costs a crossing because the
%elements live on the other side. PEP 634's rule decides which objects qualify;
%engine/metta_py.py carries it.
%
%The length is asked first and separately. A pattern of fixed shape is rejected
%by its length without pulling a single element, so matching `($x $y)` against
%a million-element list costs one crossing rather than a million.
seam:grounded_structure(Obj, Elements) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    metta_py_bridge,
    py_call(metta_py:sequence_length(Obj), Length),
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
%rather than cause [see extensions/python/benchmarks/baseline.json, alpha-unique's
%instruction_noise_comment]. Doing less work before failing is still right; it
%is just not worth 10%.
metta_py_tuple_arguments(Tuple, Arguments) :-
    compound(Tuple),
    compound_name_arity(Tuple, -, _),
    compound_name_arguments(Tuple, -, Arguments).

%%%% Display %%%%

%repr, so a Python value says what it is instead of naming an address. The
%converted -/N tuple is the exception: it is the ordinary MeTTa expression its
%structural reading already supplies, so the engine and the library expose the
%same value and both spell the empty tuple as one empty expression answer.
%The elements render through the display writer: a nested opaque host value
%(a list inside a tuple) has a repr but no round-trip text, and a display
%is presentation, exactly as the answer printers already treat it.
seam:grounded_text(Tuple, Text) :-
    metta_py_tuple_arguments(Tuple, Raw),
    !,
    maplist(metta_py_result, Raw, Elements),
    sdisplay(Elements, Text).
seam:grounded_text(Obj, Text) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    metta_py_bridge,
    py_call(metta_py:render(Obj), Text).

%%%% Resolution %%%%

%(py-atom numpy.absolute)          a module attribute
%(py-atom numpy.random.randint)    an attribute of a submodule, any depth
%(py-atom len)                     a builtin
%(py-atom "[1, 2, 3]")             a Python EXPRESSION, evaluated
%
%A STRING argument is an expression and a SYMBOL is a name, which is the
%distinction the language's own surface draws and the reason both fit in one
%operator.
'py-atom'(Spec, Result) :- metta_py_resolve(Spec, Result).

%(py-atom f Type) DECLARES what the resolved atom is, and the declaration is
%kept rather than accepted and dropped. Everything arriving from Python is
%%Undefined% otherwise, so a Python function could not participate in typed
%dispatch, be checked, or be reported by get-type as anything at all.
%
%It goes through seam:grounded_extra_type/2, the extension point that already
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
    (   nonvar(Type), Type == 'Grounded'
    ->  metta_py_resolve_grounded(Spec, Resolved)
    ;   metta_py_resolve(Spec, Resolved)
    ),
    (   var(Type)
    ->  Result = Resolved
    ;   Type == 'Expression'
    ->  metta_py_materialize(Resolved, Result)
    ;   metta_py_declare_type(Resolved, Type, Result)
    ).

%The snapshot, all the way down: every level that has a structural view becomes
%an expression, and a value that has none is a leaf and stays itself. A numpy
%array is a Sequence so it materializes; a dict, a set and an arbitrary object
%are leaves.
%
%Deep rather than one level, because a declared Expression that turned out to
%hold handles one layer down would be neither reading. One level is spelled
%`(collapse (py-iter x))` and is still there for anyone who wants it.
metta_py_materialize(Value, Expression) :-
    metta_py_materialize_(Value, [], Expression).

metta_py_materialize_(Value, Seen, Expression) :-
    (   seam:grounded_structure(Value, Elements)
    ->  metta_py_cycle_check(Value, Seen, Deeper),
        maplist(metta_py_materialize_r(Deeper), Elements, Expression)
    ;   Expression = Value
    ).

metta_py_materialize_r(Seen, Value, Expression) :-
    metta_py_materialize_(Value, Seen, Expression).

%A Python container may hold itself, and materializing one is not a slow answer
%but no answer: it recurses until the stack goes. Say so instead, because the
%value is fine and only this reading of it is impossible.
metta_py_cycle_check(Value, Seen, [Id|Seen]) :-
    (   python_object_blob(Value),
        py_is_object(Value)
    ->  py_call(builtins:id(Value), Id),
        (   memberchk(Id, Seen)
        ->  throw(error(metta_cyclic_python_value(Value),
                        context('py-atom'/3,
                                'a value that contains itself has no \c
                                 Expression reading; hold it as Grounded')))
        ;   true
        )
    ;   Id = Value            %a tuple is finite by construction
    ).

:- multifile seam:grounded_extra_type/2.

%A weak-referenceable value is the key of a Python-side weak identity record;
%a list, dict or other value weakref cannot observe carries the declaration in
%the same transparent envelope as the engine atom. Neither form needs the
%process-global dynamic fact that retained every declared object. Type text is
%read back for every query so variables are fresh and repeated occurrences
%still share, as an asserted clause did [source:
%extensions/python/metta/_atoms_core.py, boxed()'s weak identity cache;
%commit=af5821f5ffb7ce186e516706f003d02f5c1d3b4a].
metta_py_declare_type(Obj, _Type, Declared) :-
    \+ python_object_blob(Obj),
    !,
    Declared = Obj.
metta_py_declare_type(Obj, Type, Declared) :-
    term_string(Type, Text, [quoted(true)]),
    metta_py_call(['py-atom', Obj, Type], declare_type(Obj, Text), Declared).

seam:grounded_extra_type(Obj, Type) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    metta_py_bridge,
    py_call(metta_py:declared_type_texts(Obj), Texts, [py_string_as(string)]),
    member(Text, Texts),
    term_string(Type, Text).

%The class walk, this host's clause of the fallback seam: every visible class
%on the value's MRO except object, each a type candidate, which is what lets a
%torch Linear be a Linear and a Module at once. The helper removes transport
%Box and Grounded-tuple carrier layers before walking, because neither is a
%type of the MeTTa value. It lived in the engine and called the host directly,
%which is exactly the line the seam exists to draw; the engine asks
%seam:grounded_class_type/2 and this bridge answers for the values it created
%[tested: metta_object_types,
%test_a_python_tuple_answers_the_same_through_both_doors].
:- multifile seam:grounded_class_type/2.
seam:grounded_class_type(X, T) :-
    metta_py_bridge,
    py_call(metta_py:class_names(X), Names, [py_string_as(string)]),
    member(Name, Names),
    ( atom(Name) -> T = Name ; atom_string(T, Name) ).

%The standard numeric tower is the admission rule, rather than an MRO class
%name: numpy.int64 is a Number without inheriting builtins.int. Execution goes
%through one guarded bridge call so Python owns reflected-operator selection and
%the result remains a reference under metta_py_opts/1.
seam:grounded_numeric(X) :-
    python_object_blob(X),
    metta_py_bridge,
    py_call(metta_py:is_numeric(X), @true).

seam:grounded_numeric_operation(Operation, Arguments, Result) :-
    member(Operand, Arguments),
    python_object_blob(Operand), !,
    metta_py_call([Operation|Arguments],
             numeric_operation(Operation, Arguments), Result).

metta_py_resolve(Spec, Result) :-
    (   string(Spec)
    ->  metta_py_call(['py-atom', Spec], evaluate(Spec), Result)
    ;   atom(Spec)
    ->  metta_py_call(['py-atom', Spec], resolve(Spec), Result)
    ;   throw(error(type_error(python_name, Spec),
                    context('py-atom'/2,
                            'a symbol names a Python object and a string is a \c
                             Python expression')))
    ).

%Janus deliberately converts instances of the exact tuple base class even
%under py_object(true). The Python helper returns a tuple subclass holding the
%exact value, which Janus therefore carries as a reference. Every bridge call
%unwraps it before applying Python, so Grounded means a handle without changing
%the value Python receives.
metta_py_resolve_grounded(Spec, Result) :-
    (   string(Spec)
    ->  metta_py_call(['py-atom', Spec, 'Grounded'],
                 evaluate_grounded(Spec), Result)
    ;   atom(Spec)
    ->  metta_py_call(['py-atom', Spec, 'Grounded'],
                 resolve_grounded(Spec), Result)
    ;   throw(error(type_error(python_name, Spec),
                    context('py-atom'/3,
                            'a symbol names a Python object and a string is a \c
                             Python expression')))
    ).

%(py-dot obj attr) READS an attribute. py-call's `.name` spelling always calls,
%so a property, a bound method taken as a value, or a plain field needed
%getattr by hand.
'py-dot'(Obj, Attr, Result) :- metta_py_call(['py-dot', Obj, Attr], dot(Obj, Attr), Result).

%%%% Construction %%%%

%MeTTa could receive Python's containers and not build them. `(py-list (1 2 3))`
%and its siblings close that, and they take a MeTTa expression rather than a
%variadic call so that a computed list works: `(py-list (collapse (foo)))`.
'py-list'(Items, Result) :- metta_py_items(Items, 'py-list', List),
                            metta_py_call(['py-list', Items], build_list(List), Result).
'py-tuple'(Items, Result) :- metta_py_items(Items, 'py-tuple', List),
                             metta_py_call(['py-tuple', Items], build_tuple(List), Result).
'py-dict'(Pairs, Result) :- metta_py_items(Pairs, 'py-dict', List),
                            maplist(metta_py_pair, List, Converted),
                            metta_py_call(['py-dict', Pairs], build_dict(Converted), Result).

metta_py_items(Items, Who, List) :-
    (   is_list(Items)
    ->  maplist(py_arg_norm, Items, List)
    ;   throw(error(type_error(expression, Items),
                    context(Who/2, 'takes one expression of items')))
    ).

metta_py_pair(Pair, [Key, Value]) :-
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
seam:grounded_apply(Obj, Args, Result) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    metta_py_bridge,
    py_call(metta_py:is_callable(Obj), @true),
    metta_py_split_kwargs(Args, Positional0, Kwargs),
    maplist(py_arg_norm, Positional0, Positional),
    metta_py_opts(Opts),
    metta_py_guard([Obj|Args],
                   py_call(metta_py:apply(Obj, Positional, Kwargs), Raw, Opts)),
    metta_py_result(Raw, Result).

:- multifile seam:grounded_applicable/1.

%The same blob-first guard protects every runtime probe in this file
%(structure, text, apply, the cycle check), because each of them is
%consulted with plain engine terms on ordinary paths: a nested-call data
%shape reaches seam:grounded_apply/3, and probing its list head with
%py_is_object/1 booted CPython inside examples/ch04-spaces-and-matching/04-02-patterns-and-bindings/02-matchnested.metta,
%~104M instructions for a four-atom program [measured 2026-08-17].
%The blob test comes FIRST because it is the one that costs nothing:
%py_is_object/1 "fails silently" on a non-object [source: janus.pl doc,
%py_is_object/1], but janus initialises lazily on its first call, so
%probing a plain integer here booted CPython, ~104M instructions, inside
%typed-call TRANSLATION of every literal argument. The types_dependent
%example paid 3.4x upstream's whole run for it [measured 2026-08-17:
%148.2M net instructions to 44M after this guard]. blob/2 is SWI-side
%introspection and never touches janus.
seam:grounded_applicable(Obj) :-
    python_object_blob(Obj),
    py_is_object(Obj),
    metta_py_bridge,
    py_call(metta_py:is_callable(Obj), @true).

%(Kwargs (start 2) (stop 10)) in the argument list, which is the language's own
%spelling. Anything before it is positional.
metta_py_split_kwargs(Args, Positional, Kwargs) :-
    (   append(Positional, [['Kwargs'|Pairs]], Args)
    ->  maplist(metta_py_kwarg, Pairs, Converted),
        dict_pairs(Kwargs, py, Converted)
    ;   Positional = Args, Kwargs = py{}
    ).

%The pair arrives unevaluated, so the NAME is a name and the VALUE is whatever
%was written. Evaluating the value here is what keeps `(Kwargs (n (+ 1 2)))`
%meaning 3 while `(Kwargs (reverse true))` still means the keyword `reverse`.
metta_py_kwarg([Name, Value0], Name-Value) :-
    !,
    (   is_list(Value0), Value0 \== []
    ->  reduce(Value0, Evaluated, _)
    ;   Evaluated = Value0
    ),
    py_arg_norm(Evaluated, Value).
metta_py_kwarg(Other, _) :-
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
    metta_py_bridge,
    metta_py_opts(Opts),
    metta_py_guard(['py-iter', Obj], py_iter(metta_py:iterate(Obj), Raw, Opts)),
    metta_py_result(Raw, Element).


%%%% The Python surface the engine used to carry %%%%
%
%Everything below moved here from engine/metta.pl: the boolean codec at the
%janus boundary, the py-call operator, the import-as alias table and its
%form rewriter, and the .py import machinery. The engine reaches all of it
%through declared seams (seam:host_import/1, seam:form_rewriter/1,
%seam:extension_builtin/2) and publishes the services this file calls back
%(import_when/4, resolve_existing_import_path/3, current_working_dir/1,
%import_file_string/2, throw_missing_import/1, refuse_unbound_input/2), so
%an engine with no host loaded has no clause at any of the seams and pays
%one failed lookup where each would fire.

%This host's builtins, registered by the engine's own directive after its
%builtin list, from these declarations rather than from a list there that
%would name the host.
%
%The second argument is the effect class, and it is a REVIEW rather than a
%default. It used to be missing, because seam:host_builtin/1 had no room for
%one, so all seven were classified by name in engine/metta/effects.pl's
%metta_builtin_effect_override list instead -- a list inside the engine naming
%a host's predicates, which is the one thing EXTENDING.md promises an extension
%author never has to force, and which MORK stopped needing when its own seam
%grew this argument. The classification does not change; where it lives does.
%
%All seven are oracleIO, and honestly so: every one crosses into a Python
%runtime through metta_py_call/3, which the engine cannot bound. py-call, and
%py-atom over a string, run whatever the DATA names. py-dot resolves an
%attribute chosen at run time, which may be a property, __getattr__, or a
%descriptor. py-iter drives __iter__ and __next__. py-list, py-tuple and
%py-dict look structural and are not: they build a live Python object whose
%IDENTITY is observable, so two calls with equal arguments answer distinct
%objects and none of them is pureStructural; py-dict additionally hashes its
%keys, which runs __hash__ on whatever was handed in. A weaker class here would
%let a world admit them and be wrong; oracleIO says reviewed and unbounded
%rather than nobody looked.
:- multifile seam:extension_builtin/2.
seam:extension_builtin('py-call',  oracleIO).
seam:extension_builtin('py-atom',  oracleIO).
seam:extension_builtin('py-dot',   oracleIO).
seam:extension_builtin('py-list',  oracleIO).
seam:extension_builtin('py-tuple', oracleIO).
seam:extension_builtin('py-dict',  oracleIO).
seam:extension_builtin('py-iter',  oracleIO).

%This host claims an import whose source is a .py file, and does the whole
%job through the engine's own published lifecycle.
:- multifile seam:host_import/1.
seam:host_import(File) :-
    python_import_file(File),
    resolve_python_import_path(File, CanonPath),
    import_when(not_loaded, '$python', CanonPath,
                load_python_source(CanonPath)).

%%% Python bindings: %%%
% janus converts Python booleans to @(true)/@(false); normalize them to the
% language booleans, through lists too, so py-call results compose with if,
% and, or, == whether the boolean is the answer or sits inside one.
py_bool_norm('@'(true), true) :- !.
py_bool_norm('@'(false), false) :- !.
py_bool_norm(L, L1) :- is_list(L), !, maplist(py_bool_norm, L, L1).
py_bool_norm(R, R).
% The same conversion outward: the language booleans are the atoms true and
% false, which janus would pass as the strings 'true' and 'false'; map them
% (through lists too) to @(true)/@(false) so Python receives real booleans.
py_arg_norm(true, '@'(true)) :- !.
py_arg_norm(false, '@'(false)) :- !.
py_arg_norm(L, L1) :- is_list(L), !, maplist(py_arg_norm, L, L1).
%A crossed host value is carried in a metta Box, and the goal-term call
%route hands janus the reference AS WRITTEN, so the callee received the
%envelope: setattr on a crossed object raised 'Box' object has no
%attribute foo [measured 2026-08-25, integration/python.py]. The blob
%test costs nothing on ordinary terms and keeps this off every
%non-object argument; metta_py:unboxed/1 is _unwrap, the same law
%apply/3 already runs on its own route.
py_arg_norm(X, Y) :- python_object_blob(X), py_is_object(X), !,
                     metta_py_bridge,
                     py_call(metta_py:unboxed(X), Y, [py_object(true)]).
py_arg_norm(X, X).

:- dynamic python_import_alias/2.
python_call_module(Name, ModuleKey) :- python_import_alias(Name, ModuleKey), !.
python_call_module(Name, Name).
%The rewrite below only ever changes a spec that python_import_alias/2 names,
%so with no alias registered it is the identity, and its whole effect is to
%rebuild the term through maplist/3. The loader runs it over every form it
%reads, which measured at 71 inferences per form on a program that never
%touches Python. Ask first.
bind_python_calls(Term, Bound) :-
    ( python_import_alias(_, _)
      -> bind_python_calls_(Term, Bound)
       ; Bound = Term ).

bind_python_calls_(Term, Term) :- var(Term), !.
bind_python_calls_(Term, Term) :- atomic(Term), !.
bind_python_calls_([Call, [Spec|Args]], ['py-call', [BoundSpec|BoundArgs]]) :-
    Call == 'py-call', !,
    bind_python_call_spec(Spec, BoundSpec),
    maplist(bind_python_calls_, Args, BoundArgs).
bind_python_calls_(Terms, BoundTerms) :-
    maplist(bind_python_calls_, Terms, BoundTerms).

bind_python_call_spec(Spec, BoundSpec) :-
    atom(Spec),
    atomic_list_concat([Module, Function], '.', Spec),
    Module \== '',
    python_import_alias(Module, ModuleKey), !,
    atomic_list_concat([ModuleKey, Function], '.', BoundSpec).
bind_python_call_spec(Spec, Spec).
%py-call is UPSTREAM PeTTa's, which is why it does not move. It converts by
%janus's defaults and those defaults are wrong in four ways a program cannot
%work around: a dict arrives as the ATOM 'py{a:1}', so py-len answers 11 for
%two keys; a generator is DRAINED, so asking for its first element runs every
%side effect and an infinite one cannot cross; a file handle becomes a
%one-element list of its text; and a Python str becomes a Symbol, so
%`(== "abc" (py-call (str "abc")))` is False and a (-> String Number)
%parameter rejects it.
%
%Every one of those is fixed in extensions/python/bridge.pl, which is the language's own
%surface rather than this one: `py-atom` RESOLVES where this APPLIES, and that
%split is what makes a Python callable a value. Reach for that. Changing this
%operator's defaults was tried and measured and it works, and it changes what
%every program written against upstream sees, so it stays as upstream has it.
%The DECLARED arity, which is the one the type surface names and the one a
%program writes. py-call is also registered at 3, and guarding that form too
%was measured and dropped: it costs 6 inferences on the handle-round-trip
%benchmark, 2 over that counter's own 4-inference allowance, to name an
%operation in a spelling the type surface does not declare. So
%(py-call $u opts) still raises a context-less instantiation_error
%[measured 2026-08-19], the same residue engine/parser.pl's sread carries.
'py-call'(SpecList, _) :- var(SpecList), !, refuse_unbound_input('py-call', 1).
'py-call'(SpecList, Result) :- 'py-call'(SpecList, Result, []).
'py-call'([Spec|Args0], Result, Opts) :- ( string(Spec) -> atom_string(A, Spec) ; A = Spec ),
                                        must_be(atom, A),
                                        maplist(py_arg_norm, Args0, Args),
                                        ( sub_atom(A, 0, 1, _, '.')         % ".method"
                                          -> sub_atom(A, 1, _, 0, Fun),
                                             Args = [Obj|Rest],
                                             ( py_is_object(Obj)            % on a Python object reference
                                               -> ( Rest == []
                                                    -> compound_name_arguments(Meth, Fun, [])
                                                     ; Meth =.. [Fun|Rest] ),
                                                  py_call(Obj:Meth, R0, Opts), py_bool_norm(R0, Result)
                                                ; py_call(builtins:type(Obj), Ty), % on a converted value (str, int, ...)
                                                  Call =.. [Fun, Obj|Rest],
                                                  py_call(Ty:Call, R0, Opts), py_bool_norm(R0, Result) )
                                           ; atomic_list_concat([M,F], '.', A) % "mod.fun"
                                             -> ( Args == []
                                                  -> compound_name_arguments(Call0, F, [])
                                                   ; Call0 =.. [F|Args] ),
                                                python_call_module(M, PyModule),
                                                py_call(PyModule:Call0, R0, Opts), py_bool_norm(R0, Result)
                                              ; ( Args == []                      % bare "fun"
                                                  -> compound_name_arguments(Call0, A, [])
                                                   ; Call0 =.. [A|Args] ),
                                                py_call(builtins:Call0, R0, Opts), py_bool_norm(R0, Result) ).

python_import_file(File) :- import_file_string(File, SFile),
                            file_name_extension(_, py, SFile).

resolve_python_import_path(File, CanonPath) :-
    import_file_string(File, SFile),
    python_import_file(SFile),
    current_working_dir(Base),
    ( resolve_existing_import_path(Base, SFile, CanonPath)
      -> true
       ; throw_missing_import(File) ).

python_module_names(CanonPath, ModuleKey, ModuleName) :-
    crypto_data_hash(CanonPath, Hash, [algorithm(sha256)]),
    atom_concat('_metta_import_', Hash, ModuleKey),
    file_base_name(CanonPath, BaseName),
    file_name_extension(ModuleName, _, BaseName).

python_sibling_module_names(ParentDir, ModuleNames) :-
    directory_files(ParentDir, Entries),
    findall(ModuleName,
            ( member(Entry, Entries),
              file_name_extension(ModuleName, py, Entry) ),
            Names),
    sort(Names, ModuleNames).

save_python_module(Name, module_state(Name, true, Module)) :-
    py_call(sys:modules:'__contains__'(Name), @(true)), !,
    py_call(sys:modules:pop(Name), Module, [py_object(true)]).
save_python_module(Name, module_state(Name, false, @(none))).

restore_python_module(module_state(Name, true, Module)) :- !,
    py_call(sys:modules:'__setitem__'(Name, Module), _).
restore_python_module(module_state(Name, false, _)) :-
    clear_python_module(Name).

clear_python_module(Name) :-
    ( py_call(sys:modules:'__contains__'(Name), @(true))
      -> py_call(sys:modules:pop(Name), _)
       ; true ).

with_saved_python_modules([], Goal) :-
    call(Goal).
with_saved_python_modules([Name|Names], Goal) :-
    setup_call_cleanup(
        save_python_module(Name, State),
        with_saved_python_modules(Names, Goal),
        restore_python_module(State)).

load_python_source(CanonPath) :-
    python_module_names(CanonPath, ModuleKey, ModuleName),
    py_call(sys:path:copy(), PreviousPath),
    file_directory_name(CanonPath, ParentDir),
    python_sibling_module_names(ParentDir, SiblingNames),
    with_saved_python_modules(
        SiblingNames,
        load_python_source_in_context(CanonPath, ModuleKey, ModuleName,
                                      ParentDir, PreviousPath)),
    retractall(python_import_alias(ModuleName, _)),
    assertz(python_import_alias(ModuleName, ModuleKey)),
    (   seam:form_rewriter(bind_python_calls)
    ->  true
    ;   assertz(seam:form_rewriter(bind_python_calls))
    ).

load_python_source_in_context(CanonPath, ModuleKey, ModuleName, ParentDir,
                              PreviousPath) :-
    catch(load_python_module(CanonPath, ModuleKey, ModuleName, ParentDir,
                             PreviousPath),
          Error,
          ( clear_python_module(ModuleKey),
            throw(Error) )).

load_python_module(CanonPath, ModuleKey, ModuleName, ParentDir,
                   PreviousPath) :-
    py_call(importlib:util:spec_from_file_location(ModuleKey, CanonPath), Spec),
    py_call(importlib:util:module_from_spec(Spec), Module),
    py_call(sys:modules:'__setitem__'(ModuleKey, Module), _),
    py_call(sys:modules:'__setitem__'(ModuleName, Module), _),
    setup_call_cleanup(
        py_call(sys:path:insert(0, ParentDir), _),
        py_call(Spec:loader:exec_module(Module), _),
        restore_python_path(PreviousPath)).

restore_python_path(PreviousPath) :-
    py_call(sys:path:clear(), _),
    py_call(sys:path:extend(PreviousPath), _).

%Whether a value is a live object of THIS host: the blob guard avoids
%calling into janus, and initializing Python, for ordinary MeTTa values,
%and py_is_object/1 still validates a live reference and reports a freed
%one. The blob SWI registers is named `py`, and an earlier guard asked for
%'PyObject' only, so it never held and (get-type <a python object>)
%answered %Undefined% in an engine without the library; both names are
%accepted so the guard cannot break again when one of them changes
%[measured 2026-08-16].
:- multifile seam:host_object/1.
seam:host_object(X) :- python_object_blob(X), py_is_object(X).

python_object_blob(X) :- blob(X, Blob), python_object_blob_name(Blob).

python_object_blob_name(py).
python_object_blob_name('PyObject').

%This host's transport-failure shape, and the reason text for an error it
%threw: janus wraps a Python exception as python_error(Class, Value), and
%the value may be a live exception object only this bridge can render.
:- multifile seam:host_transport_failure/1.
seam:host_transport_failure(error(python_error('TransportFailure', _), _)).

:- multifile seam:host_error_reason/2.
seam:host_error_reason(error(python_error(Class, Message0), _), Reason) :-
    (   string(Message0) -> Message = Message0
    ;   metta_py_exception_message(Message0, Message)
    ),
    format(string(Reason), "~w: ~w", [Class, Message]).
