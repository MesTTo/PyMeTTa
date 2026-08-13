% Purpose: Prolog side of the petta Python library. Adds tagged term encoding,
%   per-directive structured runs, space operations, Python-backed MeTTa
%   functions (deterministic and nondeterministic), evaluation, and proof-tree
%   derivations on top of an unmodified PeTTa engine. Consulted after
%   src/main.pl; only adds predicates, never redefines engine ones.
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- use_module(library(janus)).
:- use_module(library(lists)).
:- use_module(library(apply)).

%The engine asserts translated_from/2 without declaring it, so a read before
%the first equation would raise existence rather than finding nothing:
:- dynamic translated_from/2.

%%%%%%%%%% Wire encoding %%%%%%%%%%
%
% janus maps both a Prolog atom and a Prolog string to a Python str, and maps
% the booleans to strings too, so a bare term crossing the boundary loses its
% metatype. Every term crosses tagged instead: ["s",Name] symbol, ["g",Text]
% string, ["n",N] number, ["b",true|false] boolean, ["v",Name] variable,
% ["e",[...]] expression, ["o",Ref] Python object reference. The tag list
% itself is nested lists, which janus converts natively in both directions.

%Encode a Prolog term as a tagged wire term:
petta_py_encode(T, ["v", Name]) :- var(T), !, term_to_atom(T, A), atom_string(A, Name).
petta_py_encode(T, ["o", T])    :- py_is_object(T), !.
petta_py_encode(T, ["b", T])    :- ( T == true ; T == false ), !.
petta_py_encode(T, ["n", T])    :- number(T), !.
petta_py_encode(T, ["g", T])    :- string(T), !.
petta_py_encode(T, ["s", S])    :- atom(T), !, atom_string(T, S).
petta_py_encode(T, ["e", Es])   :- is_list(T), !, maplist(petta_py_encode, T, Es).
petta_py_encode([H|T], ["e", [["s", "cons"], EH, ET]]) :- !,
    petta_py_encode(H, EH),
    petta_py_encode(T, ET).
%A non-list compound prints as (f a b) under swrite, so it encodes the same way:
petta_py_encode(T, ["e", [["s", FS] | Es]]) :-
    compound(T),
    T =.. [F|Args],
    atom(F), !,
    atom_string(F, FS),
    maplist(petta_py_encode, Args, Es).
%Anything else (a blob, a dict) is carried as text, the printer's last resort:
petta_py_encode(T, ["g", S]) :- term_string(T, S).

%Encode with an explicit Name-Var list, so parsed variables keep their names:
petta_py_encode_named(T, Pairs, ["v", Name]) :-
    var(T), !,
    ( petta_py_var_name(Pairs, T, N) -> atom_string(N, Name)
    ; term_to_atom(T, A), atom_string(A, Name) ).
petta_py_encode_named(T, Pairs, ["e", Es]) :-
    is_list(T), !,
    petta_py_encode_named_list(T, Pairs, Es).
petta_py_encode_named(T, _, W) :- petta_py_encode(T, W).

petta_py_encode_named_list([], _, []).
petta_py_encode_named_list([T|Ts], Pairs, [E|Es]) :-
    petta_py_encode_named(T, Pairs, E),
    petta_py_encode_named_list(Ts, Pairs, Es).

petta_py_var_name([N-V|_], T, N) :- V == T, !.
petta_py_var_name([_|Pairs], T, N) :- petta_py_var_name(Pairs, T, N).

%A tag arrives back as an atom or a string depending on the sender; accept both:
petta_py_tag(T, T) :- atom(T), !.
petta_py_tag(T, A) :- string(T), atom_string(A, T).

%Booleans cross from Python as janus @(true)/@(false), as atoms, or as text:
petta_py_bool(B, true)  :- B == true, !.
petta_py_bool(B, false) :- B == false, !.
petta_py_bool(B, true)  :- B == '@'(true), !.
petta_py_bool(B, false) :- B == '@'(false), !.
petta_py_bool(B, true)  :- B == "true", !.
petta_py_bool(_, false).

%Decode a tagged wire term; every v tag becomes its own fresh variable:
petta_py_decode([T, Obj], Obj)  :- petta_py_tag(T, o), !.
petta_py_decode([T, S], A)      :- petta_py_tag(T, s), !, atom_string(A, S).
petta_py_decode([T, S], Str)    :- petta_py_tag(T, g), !,
    ( string(S) -> Str = S ; atom_string(S, Str) ).
petta_py_decode([T, N], N)      :- petta_py_tag(T, n), !.
petta_py_decode([T, B], A)      :- petta_py_tag(T, b), !, petta_py_bool(B, A).
petta_py_decode([T, _], _)      :- petta_py_tag(T, v), !.
petta_py_decode([T, Es], Term)  :- petta_py_tag(T, e), !,
    maplist(petta_py_decode, Es, Term).

%Decode sharing variables by name, so the $x in a head and in a body unify.
%Bindings comes back as Name-Var pairs for reading answers off a query:
petta_py_decode_shared(Tagged, Term, Bindings) :-
    petta_py_decode_shared_(Tagged, Term, [], Bindings).

petta_py_decode_shared_([T, Name0], Var, B0, B) :- petta_py_tag(T, v), !,
    ( string(Name0) -> atom_string(Name, Name0) ; Name = Name0 ),
    %The anonymous variable is fresh at every occurrence and never binds,
    %exactly as the reader treats $_ in source; recording it would make two
    %underscores constrain each other.
    ( Name == '_' -> Var = _, B = B0
    ; memberchk(Name-Var, B0) -> B = B0
    ; B = [Name-Var|B0] ).
petta_py_decode_shared_([T, Es], Term, B0, B) :- petta_py_tag(T, e), !,
    foldl_decode(Es, Term, B0, B).
petta_py_decode_shared_(Tagged, Term, B, B) :- petta_py_decode(Tagged, Term).

foldl_decode([], [], B, B).
foldl_decode([E|Es], [T|Ts], B0, B) :-
    petta_py_decode_shared_(E, T, B0, B1),
    foldl_decode(Es, Ts, B1, B).

%%%%%%%%%% Errors %%%%%%%%%%
%
% Some exceptions are control signals rather than errors; converting one into a
% value would swallow the very signal its thrower waits for.
petta_py_control_exception(inference_limit_exceeded).
petta_py_control_exception(time_limit_exceeded).
petta_py_control_exception('$aborted').
petta_py_control_exception(error(resource_error(_), _)).

%%%%%%%%%% Run and load %%%%%%%%%%
%
% The engine's own pipeline is strip/3, top_forms//2, parse_form/2 then
% process_form/3, and process_metta_string/3 flattens every directive's answers
% into one list at the end. These entry points run the identical pipeline and
% keep the grouping instead: one answer list per ! directive, in source order.

%Reader failures carry their own functor, petta_syntax_error/1, so the
%Python side classifies by structure rather than by hunting the words
%"syntax error" in arbitrary messages (a SQL error saying them is not a
%MeTTa reader refusal).
petta_py_tag_reader(Goal) :-
    catch(Goal, Caught,
          ( ( Caught = error(syntax_error(M), _) ; Caught = syntax_error(M) )
            -> throw(error(petta_syntax_error(M), none))
          ; throw(Caught) )).

petta_py_run(Source, Space, Groups) :-
    petta_py_ensure_working_dir,
    ( string(Source) -> S = Source ; atom_string(Source, S) ),
    string_codes(S, Cs),
    strip(Cs, 0, Codes),
    petta_py_tag_reader(( phrase(top_forms(Forms, 1), Codes),
                          maplist(parse_form, Forms, Parsed) )),
    petta_py_process_forms(Parsed, Space, Groups), !.

%The CLI asserts working_dir/1 from the file it loads, and import! reads it
%unconditionally, so a string run needs one too; the process's own directory
%is the honest analogue of "the file's directory" for source with no file:
petta_py_ensure_working_dir :-
    ( catch(working_dir(_), _, fail) -> true
    ; working_directory(Dir, Dir),
      assertz(working_dir(Dir)) ).

%Run with named host values: each Name-Value pair substitutes the bare
%symbol Name throughout the parsed forms before anything runs, the local-
%variable reading a dataframe gets in embedded SQL. Values arrive on the
%wire, objects boxed, so identity crosses whole.
petta_py_run_using(Source, Space, Pairs, Groups) :-
    petta_py_ensure_working_dir,
    ( string(Source) -> S = Source ; atom_string(Source, S) ),
    string_codes(S, Cs),
    strip(Cs, 0, Codes),
    petta_py_tag_reader(( phrase(top_forms(Forms, 1), Codes),
                          maplist(parse_form, Forms, Parsed0) )),
    maplist(petta_py_using_pair, Pairs, Bindings),
    maplist(petta_py_substitute_form(Bindings), Parsed0, Parsed),
    petta_py_process_forms(Parsed, Space, Groups), !.

petta_py_using_pair([Name0, Wire], Name-Value) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    petta_py_decode_shared(Wire, Value, _).

petta_py_substitute_form(Bindings, parsed(Kind, N, Term0), parsed(Kind, N, Term)) :- !,
    petta_py_substitute(Bindings, Term0, Term).
petta_py_substitute_form(Bindings, Term0, Term) :-
    petta_py_substitute(Bindings, Term0, Term).

petta_py_substitute(_, T, T) :- var(T), !.
petta_py_substitute(Bindings, T, V) :- atom(T), memberchk(T-V, Bindings), !.
petta_py_substitute(Bindings, T, Out) :- is_list(T), !,
    maplist(petta_py_substitute(Bindings), T, Out).
petta_py_substitute(_, T, T).

petta_py_process_forms([], _, []).
petta_py_process_forms([P|Ps], Space, Out) :-
    process_form(Space, P, Results),
    ( P = parsed(runnable, _, _)
      -> maplist(petta_py_encode, Results, Encoded),
         Out = [Encoded|Rest]
    ; Out = Rest ),
    petta_py_process_forms(Ps, Space, Rest).

%Load a file the way the CLI does, working_dir included, keeping the
%grouping. The directory holds only for THIS load: whatever working_dir the
%process had comes back afterwards, exceptions included, so one load never
%changes where every later run resolves its relative imports from.
petta_py_load(File, Space, Groups) :-
    ( atom(File) -> FA = File ; atom_string(FA, File) ),
    file_directory_name(FA, Dir),
    catch(findall(W, working_dir(W), Saved), _, Saved = []),
    setup_call_cleanup(
        ( retractall(working_dir(_)), assertz(working_dir(Dir)) ),
        ( read_file_to_string(FA, S, []),
          petta_py_run(S, Space, Groups) ),
        ( retractall(working_dir(_)),
          forall(member(W, Saved), assertz(working_dir(W))) )).

%%%%%%%%%% Parse and print %%%%%%%%%%

%Read one form into a tagged term, keeping variable names. sread/2 discards the
%name map its own DCG builds; calling sexpr//3 directly keeps it:
petta_py_parse(Source, Tagged) :-
    ( string(Source) -> S = Source ; atom_string(Source, S) ),
    atom_string(A, S),
    atom_codes(A, Cs),
    ( phrase(sexpr(Term, [], VarMap), Cs)
      -> petta_py_encode_named(Term, VarMap, Tagged)
    ; format(atom(Msg), 'Parse error in form: ~w', [S]),
      throw(error(petta_syntax_error(Msg), none)) ).

%Print a tagged term the way PeTTa prints it:
petta_py_swrite(Tagged, String) :-
    petta_py_decode_shared(Tagged, Term, _),
    swrite(Term, String).

%%%%%%%%%% Space operations %%%%%%%%%%
%
% Writes go through PeTTa's own 'add-atom'/3 and 'remove-atom'/3, so an
% equation takes the engine's function path (register_fun, arity,
% translate_clause, invalidation) exactly as one read from a file does, and
% removal keeps the engine's own semantics (a plain atom removal is retractall).

petta_py_add(Space, Tagged) :-
    petta_py_decode_shared(Tagged, Term, _),
    'add-atom'(Space, Term, _).

petta_py_add_many(Space, TaggedList) :-
    forall(member(T, TaggedList), petta_py_add(Space, T)).

petta_py_remove(Space, Tagged, Removed) :-
    petta_py_decode_shared(Tagged, Term, _),
    'remove-atom'(Space, Term, Removed0),
    petta_py_encode(Removed0, Removed).

petta_py_atoms(Space, Encoded) :-
    findall(E, ('get-atoms'(Space, P), petta_py_encode(P, E)), Encoded).

petta_py_count(Space, Count) :-
    aggregate_all(count, 'get-atoms'(Space, _), Count).

petta_py_contains(Space, Tagged) :-
    petta_py_decode_shared(Tagged, Pattern, _),
    match(Space, Pattern, found, found), !.

%Clear a space: a foreign space's provider owns its storage, so the
%provider clears (or refuses, loudly, when it cannot); a native space
%removes equations first through the engine's own removal, which erases
%their compiled clauses, then any remaining stored atoms:
petta_py_clear(Space) :-
    metta_foreign_space(Space), !,
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_clear(SpaceStr), _).
petta_py_clear(Space) :-
    findall(Eq, ('get-atoms'(Space, Eq), Eq = [=, _, _]), Eqs),
    forall(member(Eq, Eqs), 'remove-atom'(Space, Eq, _)),
    forall(( current_predicate(Space/Arity),
             functor(Head, Space, Arity) ),
           retractall(Head)).

%Fresh space names for callers that want an anonymous space. The & prefix is
%load-bearing: 'is-space' recognises it, and a $ name would read as a variable.
%A released name goes back into a pool and is handed out again, because a
%space's module cannot be destroyed (SWI keeps modules for the process), so
%reuse is what keeps a churn of short-lived spaces from growing the module
%table forever. A candidate that already holds anything, foreign
%registrations included, is skipped: fresh means fresh.
:- dynamic petta_py_space_counter/1.
:- dynamic petta_py_free_space/1.
petta_py_space_counter(0).

petta_py_new_space(Name) :-
    ( retract(petta_py_free_space(Name))
      -> true
    ; petta_py_next_space(Name) ).

petta_py_next_space(Name) :-
    retract(petta_py_space_counter(N)),
    N1 is N + 1,
    assertz(petta_py_space_counter(N1)),
    atom_concat('&pyspace_', N1, Candidate),
    ( petta_py_space_untouched(Candidate)
      -> Name = Candidate
    ; petta_py_next_space(Name) ).

petta_py_space_untouched(Name) :-
    \+ petta_py_foreign(Name),
    \+ ( current_predicate(Name/Arity),
         functor(Head, Name, Arity),
         clause(Head, _, _) ).

%Release a space: everything cleared, the name pooled for reuse.
petta_py_release_space(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    petta_py_clear(Name),
    ( petta_py_free_space(Name) -> true ; assertz(petta_py_free_space(Name)) ).

%%%%%%%%%% Query %%%%%%%%%%
%
% A query is a list of patterns run as one conjunction through the engine's own
% match/4, its native [','|Patterns] form, so joins are the matcher's joins.
% VarNames selects which variables come back, as one row per answer.

petta_py_query(Space, PatternsTagged, VarNames, Row) :-
    petta_py_decode_shared(["e", PatternsTagged], Patterns, Bindings),
    petta_py_match_goal(Space, Patterns, Goal),
    call(Goal),
    petta_py_row(VarNames, Bindings, Row).

petta_py_match_goal(Space, [P], match(Space, P, answered, answered)) :- !.
petta_py_match_goal(Space, Ps, match(Space, [','|Ps], answered, answered)).

petta_py_query_all(Space, PatternsTagged, VarNames, Rows) :-
    findall(Row, petta_py_query(Space, PatternsTagged, VarNames, Row), Rows).

%A query with a guard and a bound: the guard decodes IN THE SAME variable
%scope as the patterns, so $age in both is one variable; after the match
%joins, the guard evaluates in the space's module and must answer true.
%Limit 0 means every answer.
petta_py_query_guarded(Space, PatternsTagged, GuardTagged, VarNames, Row) :-
    petta_py_decode_shared(["e", [GuardTagged | PatternsTagged]], [Guard | Patterns], Bindings),
    petta_py_match_goal(Space, Patterns, Goal),
    petta_py_module(Space, Module),
    call(Goal),
    petta_py_in_module(Module, ( translate_expr(Guard, Goals, Out),
                                 petta_py_call_goals(Module, Goals) )),
    Out == true,
    petta_py_row(VarNames, Bindings, Row).

petta_py_query_guarded_all(Space, PatternsTagged, GuardTagged, VarNames, Limit, Rows) :-
    Query = petta_py_query_guarded(Space, PatternsTagged, GuardTagged, VarNames, Row),
    ( Limit > 0
      -> findall(Row, limit(Limit, Query), Rows)
    ; findall(Row, Query, Rows) ).

petta_py_query_limit_all(Space, PatternsTagged, VarNames, Limit, Rows) :-
    findall(Row, limit(Limit, petta_py_query(Space, PatternsTagged, VarNames, Row)), Rows).

%A row holds one encoded value per requested name; a variable the answer left
%unbound comes back as itself:
petta_py_row([], _, []).
petta_py_row([Name0|Names], Bindings, [Value|Values]) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    ( memberchk(Name-V, Bindings) -> petta_py_encode(V, Value)
    ; Value = ["v", Name0] ),
    petta_py_row(Names, Bindings, Values).

%%%%%%%%%% Space modules %%%%%%%%%%
%
% On an engine carrying the per-space-equation patch, a space's compiled
% clauses live in a module named after it and space_module/2 says which; a
% stock engine keeps everything in user. Asking rather than assuming keeps
% this shim loadable on both.

petta_py_module(Space, Module) :-
    ( current_predicate(space_module/2) -> space_module(Space, Module)
    ; Module = user ).

petta_py_in_module(Module, Goal) :-
    ( current_predicate(with_metta_module/2) -> with_metta_module(Module, Goal)
    ; call(Goal) ).

%%%%%%%%%% Evaluation %%%%%%%%%%
%
% Evaluation is the engine's own translate_expr/3 over the term, then its
% goals, exactly what a ! directive runs: compiled and called in the space's
% module, so the space's own equations answer. Answers enumerate on
% backtracking.

petta_py_eval(Space, Tagged, Encoded) :-
    petta_py_decode_shared(Tagged, Term, _),
    petta_py_module(Space, Module),
    ( petta_py_direct_goal(Module, Term, Goal, Out)
      -> petta_py_in_module(Module, call(Module:Goal))
    ; petta_py_in_module(Module, ( translate_expr(Term, Goals, Out),
                                   petta_py_call_goals(Module, Goals) )) ),
    petta_py_encode(Out, Encoded).

%The fast path: a flat call of a compiled function whose arguments are all
%plain data needs no translation, just the call. translate_expr costs two
%orders more than the call itself on such terms, and they are what an API
%client evaluates all day. Anything with structure or evaluable arguments
%(a special form, a nested call, a symbol that names a function) takes the
%translator, whose judgment stays authoritative.
%Every head translate_expr treats structurally (its HV == chain and the
%stream rewrites): these must always take the translator, whatever their
%arguments look like.
petta_py_special('add-atom').     petta_py_special('and-then').
petta_py_special(call).           petta_py_special(case).
petta_py_special(catch).          petta_py_special(chain).
petta_py_special(collapse).       petta_py_special(cut).
petta_py_special(eval).           petta_py_special('filter-atom').
petta_py_special(foldall).        petta_py_special('foldl-atom').
petta_py_special(forall).         petta_py_special(hyperpose).
petta_py_special(if).             petta_py_special(let).
petta_py_special('let*').         petta_py_special('map-atom').
petta_py_special(match).          petta_py_special(once).
petta_py_special('or-else').      petta_py_special(prog1).
petta_py_special(progn).          petta_py_special(quote).
petta_py_special(reduce).         petta_py_special('remove-atom').
petta_py_special(sealed).         petta_py_special(superpose).
petta_py_special(test).           petta_py_special(transaction).
petta_py_special(translatePredicate).
petta_py_special(with_mutex).     petta_py_special('trace!').
petta_py_special(unique).         petta_py_special('alpha-unique').
petta_py_special(union).          petta_py_special(intersection).
petta_py_special(subtraction).

petta_py_direct_goal(Module, [F|Args], Goal, Out) :-
    atom(F),
    fun(F),
    \+ petta_py_special(F),
    petta_py_plain_args(Args),
    length(Args, N),
    Arity is N + 1,
    arity(F, Arity),
    current_predicate(Module:F/Arity),
    append(Args, [Out], Full),
    Goal =.. [F|Full].

petta_py_plain_args([]).
petta_py_plain_args([A|As]) :-
    ( number(A) -> true
    ; string(A) -> true
    ; A == true -> true
    ; A == false -> true
    ; atom(A), \+ fun(A) -> true
    ; py_is_object(A) ),
    petta_py_plain_args(As).

petta_py_call_goals(_, []).
petta_py_call_goals(Module, [G|Gs]) :-
    call(Module:G),
    petta_py_call_goals(Module, Gs).

petta_py_eval_all(Space, Tagged, Encoded) :-
    findall(E, petta_py_eval(Space, Tagged, E), Encoded).

%%%%%%%%%% Python-backed MeTTa functions %%%%%%%%%%
%
% A registered operation is an ordinary MeTTa function whose body lives in
% Python. Arguments cross encoded so Python sees real atoms; results cross
% back encoded. kind det calls once; kind many enumerates a Python iterator
% through py_iter/2, which is genuine nondeterminism. The raw kinds skip the
% encoding for speed and receive janus's default conversion instead, which
% suits operations over object references such as tensors.

:- dynamic petta_py_op_spec/3.

%An operation that answers nothing sends the declined sentinel, which turns
%into failure here: the semidet reading of a Python None or a raised Decline.
petta_py_declined(TR) :- TR = [T, D], petta_py_tag(T, x), petta_py_tag(D, declined).

petta_py_dispatch_det(Name, Args, Result) :-
    maplist(petta_py_encode, Args, TA),
    py_call(petta_ops:dispatch(Name, TA), TR),
    \+ petta_py_declined(TR),
    petta_py_decode_shared(TR, Result, _).

petta_py_dispatch_many(Name, Args, Result) :-
    maplist(petta_py_encode, Args, TA),
    py_iter(petta_ops:dispatch_many(Name, TA), TR),
    petta_py_decode_shared(TR, Result, _).

%Raw results skip the wire encoding, so a Python boolean arrives as janus's
%@(true)/@(false); normalize to the language booleans exactly as 'py-call'
%does, so raw operations compose with if, and, or:
petta_py_raw_norm('@'(true), true) :- !.
petta_py_raw_norm('@'(false), false) :- !.
petta_py_raw_norm(R, R).

%A raw None is janus's @(none); it reads as no answer, the same semidet rule
%the encoded path applies, since MeTTa has no None value to hand back:
petta_py_dispatch_raw_det(Name, Args, Result) :-
    py_call(petta_ops:dispatch_raw(Name, Args), R0),
    R0 \== '@'(none),
    petta_py_raw_norm(R0, Result).

petta_py_dispatch_raw_many(Name, Args, Result) :-
    py_iter(petta_ops:dispatch_raw_many(Name, Args), R0),
    R0 \== '@'(none),
    petta_py_raw_norm(R0, Result).

%Register every arity of a Python-backed function in one step, checked
%before anything mutates: a name whose compiled predicate would collide
%with a static procedure ((+)/3, say) throws HERE, with no state touched,
%and every previously registered arity of the name is replaced rather than
%left behind for calls the new callable no longer serves.
petta_py_register_op_set(Name0, Arities, Kind) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    %The probe is the same assert the registration will do, on a clause that
    %can never run; the engine's own permission error surfaces here, before
    %any existing registration has been touched. predicate_property cannot
    %stand in for it: autoloadable names report static yet accept clauses.
    forall(member(A, Arities),
           ( PredArity is A + 1,
             functor(Probe, Name, PredArity),
             ( petta_py_op_spec(Name, A, _) -> true
             ; setup_call_cleanup(assertz((Probe :- fail), Ref),
                                  true,
                                  erase(Ref)) ) )),
    forall(petta_py_op_spec(Name, Old, _), petta_py_unregister_op(Name, Old)),
    forall(member(A, Arities), petta_py_register_op(Name, A, Kind)).

%Register a Python-backed function of the given MeTTa arity. The compiled
%predicate carries one extra output argument, the engine's own convention:
petta_py_register_op(Name0, Arity, Kind) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    petta_py_unregister_op(Name, Arity),
    length(Args, Arity),
    append(Args, [Result], HeadArgs),
    Head =.. [Name | HeadArgs],
    petta_py_op_body(Kind, Name, Args, Result, Body),
    assertz((Head :- Body)),
    assertz(petta_py_op_spec(Name, Arity, Kind)),
    register_fun(Name),
    PredArity is Arity + 1,
    ( arity(Name, PredArity) -> true ; assertz(arity(Name, PredArity)) ),
    forall(metta_on_function_changed(Name), true).

petta_py_op_body(det,      Name, Args, R, petta_py_dispatch_det(Name, Args, R)).
petta_py_op_body(many,     Name, Args, R, petta_py_dispatch_many(Name, Args, R)).
petta_py_op_body(raw_det,  Name, Args, R, petta_py_dispatch_raw_det(Name, Args, R)).
petta_py_op_body(raw_many, Name, Args, R, petta_py_dispatch_raw_many(Name, Args, R)).

%Remove one registered arity of an operation, leaving other arities alone.
%When nothing defines the name any more, forget the function entirely, the
%same forgetting 'remove-atom'/3 does when a last equation goes: fun/1 and
%arity/2 retract, so the next compile treats the name as data again:
petta_py_unregister_op(Name0, Arity) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    PredArity is Arity + 1,
    ( petta_py_op_spec(Name, Arity, _)
      -> functor(Head, Name, PredArity),
         retractall(Head),
         retractall(petta_py_op_spec(Name, Arity, _)),
         retractall(arity(Name, PredArity))
    ; true ),
    ( \+ ( current_predicate(Name/A), functor(H2, Name, A), clause(H2, _, _) )
      -> retractall(fun(Name)),
         retractall(arity(Name, _)),
         metta_on_function_removed(Name)
    ; true ).

%Every function name the engine has registered, for completion and docs:
petta_py_builtins(Names) :-
    findall(S, ( fun(N), atom_string(N, S) ), Names).

petta_py_is_function(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name).

%Whether a function ANSWERS from this space: it has clauses its module can
%see, its own or inherited from user. Another space's equations live in that
%space's module and are invisible here, so they do not count.
petta_py_function_visible(Space0, Name0) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name),
    petta_py_module(Space, Module),
    catch(( current_predicate(Module:Name/Arity),
            functor(Head, Name, Arity),
            clause(Module:Head, _, _) ),
          _, fail), !.

petta_py_arities(Name0, As) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    findall(A, arity(Name, A), As).

%%%%%%%%%% Derivation trees %%%%%%%%%%
%
% The classic three-clause proof-tree meta-interpreter, rendered in MeTTa
% terms: every compiled clause remembers its source equation through
% translated_from/2, so each node names the equation that fired, a stored atom
% is a leaf, and a builtin call is an opaque leaf. Depth-bounded, because a
% meta-interpreted search should fail loudly rather than loop silently.

petta_py_derivation(Space, Tagged, Depth, TreeTagged) :-
    petta_py_decode_shared(Tagged, Term, _),
    Term = [F|Args],
    atom(F),
    append(Args, [Out], FullArgs),
    Goal =.. [F|FullArgs],
    petta_py_module(Space, Module),
    petta_py_in_module(Module, petta_py_solve(Module, Goal, Depth, Tree)),
    petta_py_encode_tree(Tree, [F|Args], Out, TreeTagged).

petta_py_solve(_, _, D, _) :- D =< 0, !, fail.
petta_py_solve(_, true, _, []) :- !.
petta_py_solve(M, (A, B), D, Tree) :- !,
    petta_py_solve(M, A, D, TA),
    petta_py_solve(M, B, D, TB),
    append(TA, TB, Tree).
%A clause compiled from a MeTTa equation is a step worth showing, and its body
%is walked further. Everything else, engine machinery and space facts alike, is
%called whole and appears as one leaf, so the tree stays in MeTTa terms. The
%lookup is module-qualified: a named space's equations live in its module, and
%clause/3 falls back to user through module inheritance for the rest. Only the
%clause INSPECTION is guarded (an uninspectable goal is an opaque leaf); a
%body or builtin that ERRS propagates, because (/ 1 0) failing into "no
%proof" would be a lie about why:
petta_py_solve(M, Goal, D, Tree) :-
    \+ predicate_property(M:Goal, built_in),
    catch(clause(M:Goal, Body, Ref), _, fail),
    ( translated_from(Ref, Source)
      -> D1 is D - 1,
         petta_py_solve(M, Body, D1, Sub),
         Tree = [step(Goal, Source, Sub)]
    ; call(M:Body),
      petta_py_leaf(Goal, Tree) ).
petta_py_solve(M, Goal, _, [builtin(Goal)]) :-
    predicate_property(M:Goal, built_in), !,
    call(M:Goal).

%A match over a space names the atom it found; anything else names its goal:
petta_py_leaf(match(Space, Pattern, _, _), [fact(Space, Pattern)]) :- !.
petta_py_leaf(Goal, [fact('&self', Fact)]) :-
    functor(Goal, Space, _),
    atom_concat('&', _, Space), !,
    Goal =.. [Space|Fact].
petta_py_leaf(Goal, [builtin(Goal)]).

%The tree crosses as nested tagged expressions:
%  (derivation Conclusion Steps...) with each step
%  (step Conclusion (= Head Body) Substeps...) or (fact Atom) or (builtin Text).
petta_py_encode_tree(Steps, Root, Out, ["e", [["s", "derivation"], RootE | StepEs]]) :-
    petta_py_encode([Root, '=', Out], ["e", [R, _, O]]),
    RootE = ["e", [["s", "answer"], R, O]],
    maplist(petta_py_encode_step, Steps, StepEs).

petta_py_encode_step(step(Goal, Source, Sub), ["e", [["s", "step"], GoalE, SourceE | SubEs]]) :-
    petta_py_encode(Goal, GoalE0),
    petta_py_goal_term(GoalE0, GoalE),
    petta_py_encode(Source, SourceE),
    maplist(petta_py_encode_step, Sub, SubEs).
petta_py_encode_step(fact(Space, Fact), ["e", [["s", "fact"], SpaceE, FactE]]) :-
    petta_py_encode(Space, SpaceE),
    petta_py_encode(Fact, FactE).
petta_py_encode_step(builtin(Goal), ["e", [["s", "builtin"], ["g", Text]]]) :-
    term_string(Goal, Text).

%A compiled goal f(A1..An,Out) renders as the call (f A1..An) with its answer:
petta_py_goal_term(["e", [F | ArgsAndOut]], ["e", [["s", "call"], ["e", [F|Args]], Out]]) :-
    append(Args, [Out], ArgsAndOut), !.
petta_py_goal_term(E, ["e", [["s", "call"], E, ["s", "?"]]]).

%%%%%%%%%% Foreign spaces %%%%%%%%%%
%
% A space whose atoms live in a Python provider: a database, a dataframe, an
% API. The engine's hooks route match, add, remove and get-atoms here; the
% provider enumerates candidate atoms for a pattern, and unification against
% the pattern happens in Prolog, so the provider may over-approximate freely
% and soundness stays the engine's. Registration is dynamic, from Python.

:- multifile metta_foreign_space/1.
:- multifile metta_foreign_match/2.
:- multifile metta_foreign_add/2.
:- multifile metta_foreign_remove/3.
:- multifile metta_foreign_atoms/2.

:- dynamic petta_py_foreign/1.

metta_foreign_space(Space) :- petta_py_foreign(Space).

metta_foreign_match(Space, Pattern) :-
    petta_py_encode(Pattern, W),
    atom_string(Space, SpaceStr),
    py_iter(petta_ops:foreign_match(SpaceStr, W), CW),
    petta_py_decode_shared(CW, Candidate, _),
    Pattern = Candidate.

metta_foreign_atoms(Space, Atom) :-
    atom_string(Space, SpaceStr),
    py_iter(petta_ops:foreign_atoms(SpaceStr), CW),
    petta_py_decode_shared(CW, Atom, _).

metta_foreign_add(Space, Term) :-
    petta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_add(SpaceStr, W), _).

metta_foreign_remove(Space, Term, Removed) :-
    petta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_remove(SpaceStr, W), R0),
    petta_py_bool(R0, Removed).

petta_py_register_foreign(Space0) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    ( petta_py_foreign(Space) -> true ; assertz(petta_py_foreign(Space)) ).

petta_py_unregister_foreign(Space0) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    retractall(petta_py_foreign(Space)).

%%%%%%%%%% Subscriptions %%%%%%%%%%
%
% Standing queries: when Python has subscribers, every space write crosses
% to petta_ops for pattern matching and callbacks, synchronously, inside
% the write. The guard is one dynamic flag, so an unsubscribed process
% pays a single failed lookup per write and nothing more.

:- multifile metta_on_atom_added/2.
:- multifile metta_on_atom_removed/2.
:- dynamic petta_py_subscriptions_on/0.

metta_on_atom_added(Space, Term) :-
    petta_py_subscriptions_on,
    atom(Space),
    petta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:atom_added(SpaceStr, W), _).

metta_on_atom_removed(Space, Term) :-
    petta_py_subscriptions_on,
    atom(Space),
    petta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:atom_removed(SpaceStr, W), _).

petta_py_subscriptions(Enabled) :-
    ( Enabled == true
      -> ( petta_py_subscriptions_on -> true ; assertz(petta_py_subscriptions_on) )
    ; retractall(petta_py_subscriptions_on) ).

%%%%%%%%%% Protocol types for host objects %%%%%%%%%%
%
% The engine asks py_object_extra_type/2 for names beyond an object's own
% classes; the answer comes from the Python-side protocol registry, so a
% library teaches typing without touching Prolog.

:- multifile py_object_type_names/2.

%Values cross the boundary boxed so janus cannot rewrite them; the names
%are computed on the held value, in Python, and cross as plain text: the
%classes off the method resolution order, then every satisfied protocol.
py_object_type_names(X, Names) :-
    py_is_object(X),
    py_call(petta_ops:type_names(X), Names).

%(context-space) lives in the engine now (src/metta.pl); the shim keeps
%nothing to add for it.

%%%%%%%%%% Retranslation on late definitions %%%%%%%%%%
%
% The engine decides call-against-data per equation at compile time, so a
% body mentioning a name that only becomes a function later stays data: the
% classic case is (= (f) (g)) in one run and (= (g) 5) in the next, and the
% Python case is an operation registered after equations that call it.
% Both paths that define a function fire the metta_on_function_changed/1
% extension point; this multifile clause walks the live equations whose
% bodies mention the changed name and retranslates them in their own module,
% so the compile-time decision is refreshed rather than stale.

:- multifile metta_on_function_changed/1.
:- multifile metta_on_function_removed/1.

metta_on_function_changed(Name) :-
    forall(petta_py_stale_equation(Name, Module, Ref, Source),
           petta_py_retranslate(Module, Ref, Source)),
    ( catch(invalidate_specializations(Name), _, true) -> true ; true ).

%A fully removed function refreshes the other way: a mention that compiled as
%a call goes back to data, since the name no longer names a function.
metta_on_function_removed(Name) :-
    forall(petta_py_stale_equation(Name, Module, Ref, Source),
           petta_py_retranslate(Module, Ref, Source)).

petta_py_stale_equation(Name, Module, Ref, Source) :-
    translated_from(Ref, Source),
    Source = [=, [Head|_], Body],
    Head \== Name,
    once(petta_py_mentions(Body, Name)),
    catch(clause(_, _, Ref), _, fail),
    ( catch(clause_property(Ref, module(M)), _, fail) -> Module = M
    ; Module = user ).

petta_py_mentions(T, _) :- var(T), !, fail.
petta_py_mentions(T, Name) :- T == Name, !.
petta_py_mentions(T, Name) :- is_list(T), member(X, T), petta_py_mentions(X, Name), !.

petta_py_retranslate(Module, OldRef, Source) :-
    Source = [=, [F|Args], Body],
    erase(OldRef),
    retractall(translated_from(OldRef, _)),
    petta_py_drop_fun_meta(F, Args, Body),
    petta_py_in_module(Module, once(translate_clause(Source, Clause))),
    assertz(Module:Clause, NewRef),
    assertz(translated_from(NewRef, Source)).

%translate_clause/2 pushes a fun_meta entry per compile; dropping the stale
%one first keeps the specializer's meta-clause list one entry per equation:
petta_py_drop_fun_meta(F, Args, Body) :-
    catch(nb_getval(F, Prev), _, Prev = []),
    ( petta_py_select_meta(Prev, Args, Body, Rest)
      -> ( Rest == [] -> nb_delete(F) ; nb_setval(F, Rest) )
    ; true ).

petta_py_select_meta([fun_meta(A, B)|Rest], Args, Body, Rest) :-
    (A - B) =@= (Args - Body), !.
petta_py_select_meta([Keep|Tail], Args, Body, [Keep|Rest]) :-
    petta_py_select_meta(Tail, Args, Body, Rest).

%%%%%%%%%% Silence %%%%%%%%%%
%
% filereader.pl decides silent/1 from the CLI argv at load time; a library run
% has no argv, so the bridge sets it explicitly. Retract first, because two
% contradictory silent/1 clauses would leave the engine on whichever is first.
petta_py_set_silent(Silent) :-
    retractall(silent(_)),
    assertz(silent(Silent)).
