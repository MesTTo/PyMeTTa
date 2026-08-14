% Purpose: provide PeTTa's Prolog runtime, builtins, type system, evaluator,
%   imports, function registration, and named-space execution context.
% Open Obligations:
%   To Do: Resolve the remaining runtime findings in ai-prolog-review.md.
%   Hacks: None
%   Future Enhancements: None

%%%%%%%%%% Dependencies %%%%%%%%%%
%Asserted at runtime (git imports, the CLI driver); declared so a
%reference before the first assert fails instead of erring undefined.
:- dynamic library_path/1, working_dir/1.
library(X, Path) :- standard_library_path(Base), atomic_list_concat([Base, '/', X], Path).
library(X, Y, Path) :- library_path(Base), atom_concat(_, X, Base), atomic_list_concat([Base, '/', Y], Path).
:- prolog_load_context(directory, Source),
   directory_file_path(Source, '..', Parent),
   directory_file_path(Parent, 'lib', LibPath),
   asserta(standard_library_path(LibPath)).
:- autoload(library(uuid)).
:- use_module(library(random)).
:- use_module(library(janus)).
:- use_module(library(error)).
:- use_module(library(listing)).
:- use_module(library(aggregate)).
:- use_module(library(thread)).
:- use_module(library(lists)).
:- use_module(library(yall), except([(/)/3])).
:- use_module(library(apply)).
:- use_module(library(apply_macros)).
:- use_module(library(process)).
:- use_module(library(filesex)).
:- current_prolog_flag(argv, Argv),
  ( member(mork, Argv) -> ensure_loaded([ext_points, parser, translator, specializer, filereader, '../mork_ffi/morkspaces', spaces, tracer])
                        ; ensure_loaded([ext_points, parser, translator, specializer, filereader, spaces, tracer])).

%%%%%%%%%% Standard Library for MeTTa %%%%%%%%%%

%%% Representation and parsing conversions: %%%
id(X, X).
repr(Term, R) :- swrite(Term, R).
repra(Term, R) :- term_to_atom(Term, R).
parse(Str, R) :- sread(Str, R).

%%% Arithmetic & Comparison: %%%
'+'(A,B,R)  :- R is A + B.
'-'(A,B,R)  :- R is A - B.
'*'(A,B,R)  :- R is A * B.
'/'(A,B,R)  :- R is A / B.
'%'(A,B,R)  :- R is A mod B.
'<'(A,B,R)  :- (A<B -> R=true ; R=false).
'>'(A,B,R)  :- (A>B -> R=true ; R=false).
'=='(A,B,R) :- (A==B -> R=true ; R=false).
'!='(A,B,R) :- (A==B -> R=false ; R=true).
'='(A,B,R) :-  (A=B -> R=true ; R=false).
'=?'(A,B,R) :- (\+ \+ A=B -> R=true ; R=false).
'=alpha'(A,B,R) :- (A =@= B -> R=true ; R=false).
'=@='(A,B,R) :- (A =@= B -> R=true ; R=false).
'<='(A,B,R) :- (A =< B -> R=true ; R=false).
'>='(A,B,R) :- (A >= B -> R=true ; R=false).
min(A,B,R)  :- R is min(A,B).
max(A,B,R)  :- R is max(A,B).
exp(Arg,R) :- R is exp(Arg).
:- use_module(library(clpfd)).
'#+'(A, B, R) :- R #= A + B.
'#-'(A, B, R) :- R #= A - B.
'#*'(A, B, R) :- R #= A * B.
'#div'(A, B, R) :- R #= A div B.
'#//'(A, B, R) :- R #= A // B.
'#mod'(A, B, R) :- R #= A mod B.
'#min'(A, B, R) :- R #= min(A,B).
'#max'(A, B, R) :- R #= max(A,B).
'#<'(A, B, true)  :- A #< B, !.
'#<'(_, _, false).
'#>'(A, B, true)  :- A #> B, !.
'#>'(_, _, false).
'#='(A, B, true)  :- A #= B, !.
'#='(_, _, false).
'#\\='(A, B, true)  :- A #\= B, !.
'#\\='(_, _, false).
'pow-math'(A, B, Out) :- Out is A ** B.
'sqrt-math'(A, Out)   :- Out is sqrt(A).
'abs-math'(A, Out)    :- Out is abs(A).
'log-math'(Base, X, Out) :- Out is log(X) / log(Base).
'exp-math'(A, Out)    :- Out is exp(A).
'trunc-math'(A, Out)  :- Out is truncate(A).
'ceil-math'(A, Out)   :- Out is ceil(A).
'floor-math'(A, Out)  :- Out is floor(A).
'round-math'(A, Out)  :- Out is round(A).
'sin-math'(A, Out)  :- Out is sin(A).
'cos-math'(A, Out)  :- Out is cos(A).
'tan-math'(A, Out)  :- Out is tan(A).
'asin-math'(A, Out) :- Out is asin(A).
'acos-math'(A, Out) :- Out is acos(A).
'atan-math'(A, Out) :- Out is atan(A).
'isnan-math'(A, Out) :- ( A =:= A -> Out = false ; Out = true ).
'isinf-math'(A, Out) :- ( ( A =:= 1.0Inf ; A =:= -1.0Inf ) -> Out = true ; Out = false ).
'min-atom'(List, Out) :- non_list(List), !, Out = [].
'min-atom'(List, Out) :- min_list(List, Out).
'max-atom'(List, Out) :- non_list(List), !, Out = [].
'max-atom'(List, Out) :- max_list(List, Out).

%%% Random Generators: %%%
'random-int'(Min, Max, Result) :- random_between(Min, Max, Result).
'random-int'('&rng', Min, Max, Result) :- random_between(Min, Max, Result).
'random-float'(Min, Max, Result) :- random(R), Result is Min + R * (Max - Min).
'random-float'('&rng', Min, Max, Result) :- random(R), Result is Min + R * (Max - Min).

%%% Boolean Logic: %%%
bool(true).
bool(false).
and(A,B,C) :- bool(A), bool(B), ( A == true -> C = B ; A == false -> C = false ).
or(A,B,C) :- bool(A), bool(B), ( A == true -> C = true ; A == false -> C = B ).
not(A,B) :- bool(A), ( A == true -> B = false ; A == false -> B = true ).
xor(A,B,C) :- bool(A), bool(B), ( A == B -> C = false ; C = true ).
implies(A,B,C) :- bool(A), bool(B), ( A == true -> ( B == true  -> C = true ; B == false -> C = false )
                                                 ; A == false -> C = true ).

%%% Nondeterminism: %%%
superpose(L,X) :- member(X,L).
empty(_) :- fail.

%%% Lists / Tuples: %%%
'cons-atom'(H, T, [H|T]).
'decons-atom'([H|T], [H|[T]]).
'first-from-pair'([A, _], A).
first([A, _], A).
'second-from-pair'([_, A], A).
'unique-atom'(A, B) :- non_list(A), !, B = [].
'unique-atom'(A, B) :- list_to_set(A, B).

%%% Alpha-equivalence unique atom %%%
'alpha-unique-atom'(A, B) :- non_list(A), !, B = [].
'alpha-unique-atom'(A, B) :- alpha_list_to_set(A, B).

alpha_list_to_set(List, Set) :-
    empty_assoc(Seen0),
    alpha_list_to_set_assoc(List, Seen0, Set).

alpha_list_to_set_assoc([], _, []).
alpha_list_to_set_assoc([H|T], SeenIn, R) :-
    copy_term(H, HCopy),
    numbervars(HCopy, 0, _),
    term_hash(HCopy, Key),
    ( get_assoc(Key, SeenIn, _) ->
        alpha_list_to_set_assoc(T, SeenIn, R)
    ;
        put_assoc(Key, SeenIn, true, SeenOut),
        R = [H|RT],
        alpha_list_to_set_assoc(T, SeenOut, RT)
    ).

%A term that can never become a list, no matter how it gets instantiated:
non_list(X) :- atomic(X), X \== [].
non_list(X) :- compound(X), X \= [_|_].

'sort-atom'(List, Sorted) :- non_list(List), !, Sorted = [].
'sort-atom'(List, Sorted) :- msort(List, Sorted).
'size-atom'(List, Size) :- non_list(List), !, Size = [].
'size-atom'(List, Size) :- length(List, Size).
'car-atom'([H|_], H) :- !.
'car-atom'(_, []).
'cdr-atom'([_|T], T) :- !.
'cdr-atom'(_, []).
decons([H|T], [H|[T]]).
cons(H, T, [H|T]).
'index-atom'(_, Index, _) :- nonvar(Index), \+ integer(Index), !, fail.
'index-atom'(List, Index, Elem) :- nth0(Index, List, Elem).
member(X, L, true) :- member(X, L).
'is-member'(X, List, true) :- member(X, List).
'is-member'(X, List, false) :- \+ member(X, List).

member_alpha(X, [H|_]) :- (var(X) -> var(H) ; true), X = H, !.
member_alpha(X, [_|T]) :- member_alpha(X, T).

'is-alpha-member'(X, List, true) :- member_alpha(X, List), !.
'is-alpha-member'(_, _, false).

'exclude-item'(A, L, R) :- exclude(==(A), L, R).

%Multisets:
'subtraction-atom'([], _, []).
'subtraction-atom'([H|T], B, Out) :- ( select(H, B, BRest) -> 'subtraction-atom'(T, BRest, Out)
                                                            ; Out = [H|Rest],
                                                              'subtraction-atom'(T, B, Rest) ).
'union-atom'(A, B, Out) :- append(A, B, Out).
'intersection-atom'(A, B, Out) :- ( non_list(A) ; non_list(B) ), !, Out = [].
'intersection-atom'([], _, []).
'intersection-atom'([H|T], B, Out) :- ( select(H, B, BRest) -> Out = [H|Rest],
                                                              'intersection-atom'(T, BRest, Rest)
                                                            ; 'intersection-atom'(T, B, Out) ).

%%% Type system: %%%

%The space whose ':' declarations are in scope. A space's compiled clauses live
%in a module named after it, and space_module/2 is '&self' -> user and the
%identity otherwise, so inverting it recovers the space with no extra state to
%keep.
%
%Without this, get-type consulted '&self' literally, and a declaration made in
%any other space was invisible to it. That is not an edge case: every space
%PyPeTTa creates is a named one, so `(: a A)` written there answered
%'%Undefined%' no matter what.
current_metta_space(Space) :- current_metta_module(Module),
                              ( Module == user -> Space = '&self' ; Space = Module ).

%A ':' declaration in scope here: this space's, and &self's, since &self is the
%shared space. That is the rule fun_here/1 already applies to functions.
type_declaration(X, T) :- current_metta_module(Module),
                          type_declaration_in(Module, X, T).

type_declaration_in(user, X, T) :- !, match('&self', [':', X, T], T, _).
type_declaration_in(Module, X, T) :- (   match(Module, [':', X, T], T, _)
                                     ;   match('&self', [':', X, T], T, _) ).

%&self is always the engine's native space. Keeping its lookup direct avoids
%the provider and module-dispatch layers on every recursive type probe.
get_function_type([F|Args], T) :- nonvar(F),
                                  catch('&self'(':', F, [->|Ts]), E, recover_failure(E)),
                                  append(As,[T],Ts),
                                  maplist('get-type', Args, As).
get_function_type_in(Module, [F|Args], T) :- Module \== user,
                                             nonvar(F),
                                             type_declaration_in(Module, F, [->|Ts]),
                                             append(As,[T],Ts),
                                             maplist(Module:'get-type', Args, As).

:- dynamic 'get-type'/2.
%A type query executed in a named space reads the scoped MeTTa module once,
%then keeps that module through the candidate loop. Translation, evaluation,
%and host calls all establish the same scoped state through with_metta_module/2.
'get-type'(X, T) :- current_metta_module(Module),
                    ( ( Module == user -> get_type_candidate(X, T)
                                         ; get_type_candidate_in(Module, X, T) )
                      *-> true ; T = '%Undefined%' ).
get_type_candidate(X, 'Number')   :- number(X), !.
get_type_candidate(X, _) :- var(X), !.
get_type_candidate(X, 'String')   :- string(X), !.
get_type_candidate(true, 'Bool')  :- !.
get_type_candidate(false, 'Bool') :- !.
%Only PyObject blobs can be Janus references. The blob guard avoids calling
%into Janus, and initializing Python, while typing ordinary MeTTa values;
%py_is_object/1 still validates a live reference and reports a freed one.
get_type_candidate(X, T) :- atomic(X), \+ atom(X),
                            blob(X, 'PyObject'), py_is_object(X), py_object_type(X, T).
get_type_candidate(X, T) :- get_function_type(X,T).
get_type_candidate(X, T) :- \+ get_function_type(X, _),
                            is_list(X),
                            maplist('get-type', X, T).
get_type_candidate(X, T) :- catch('&self'(':', X, T), E, recover_failure(E)),
                            acyclic_term(T).

get_type_candidate_in(_, X, 'Number')   :- number(X), !.
get_type_candidate_in(_, X, _) :- var(X), !.
get_type_candidate_in(_, X, 'String')   :- string(X), !.
get_type_candidate_in(_, true, 'Bool')  :- !.
get_type_candidate_in(_, false, 'Bool') :- !.
get_type_candidate_in(_, X, T) :- atomic(X), \+ atom(X),
                                  blob(X, 'PyObject'), py_is_object(X), py_object_type(X, T).
get_type_candidate_in(Module, X, T) :- get_function_type_in(Module, X, T).
get_type_candidate_in(Module, X, T) :- \+ get_function_type_in(Module, X, _),
                                       is_list(X),
                                       maplist(Module:'get-type', X, T).
get_type_candidate_in(Module, X, T) :- type_declaration_in(Module, X, T).
%A grounded Python object is Grounded, and its Python classes are its types:
%every class on the object's method resolution order short of object itself is
%a candidate, so a torch Linear is a Linear and a Module, in the same way
%MeTTa's own types are nondeterministic. This is what lets a declared
%(-> Tensor Tensor Tensor) hold for values the host created.
%A bridge that knows how to read the object answers with every type name at
%once, protocols included, as plain text the boundary cannot damage; without
%one, the class walk below runs, plus any engine-side extra types:
py_object_type(X, T) :- ( catch_recover(py_object_type_names(X, Names), fail)
                          -> member(N, Names),
                             ( atom(N) -> T = N ; atom_string(T, N) )
                        ; py_object_class_type(X, T) ).

py_object_class_type(X, T) :- py_call(builtins:type(X), Class),
                              py_call(builtins:getattr(Class, '__mro__'), MRO),
                              py_call(builtins:list(MRO), Classes),
                              member(C, Classes),
                              py_call(builtins:getattr(C, '__name__'), Name),
                              ( atom(Name) -> T = Name ; atom_string(T, Name) ),
                              T \== object.
%A protocol the object satisfies may name a type too, through the extension
%point, so (-> DLTensor ...) holds for every array library at once:
py_object_class_type(X, T) :- py_object_extra_type(X, T).

'get-metatype'(X, 'Variable') :- var(X), !.
'get-metatype'(X, 'Grounded') :- number(X), !.
'get-metatype'(X, 'Grounded') :- string(X), !.
'get-metatype'(true,  'Grounded') :- !.
'get-metatype'(false, 'Grounded') :- !.
'get-metatype'(X, 'Grounded') :- blob(X, 'PyObject'), py_is_object(X), !.
'get-metatype'(X, 'Grounded') :- atom(X), fun(X), !.  % e.g., '+' is a registered fun/1
'get-metatype'(X, 'Expression') :- is_list(X), !.     % e.g., (+ 1 2), (a b)
'get-metatype'(X, 'Symbol') :- atom(X), !.            % e.g., a

'is-var'(A,R) :- var(A) -> R=true ; R=false.
'is-ground'(A,R) :- ground(A) -> R=true ; R=false.
'is-expr'(A,R) :- is_list(A) -> R=true ; R=false.
'is-space'(A,R) :- atom(A), atom_concat('&', _, A) -> R=true ; R=false.

%%% Diagnostics / Testing: %%%
:- multifile prolog:error_message//1.

prolog:error_message(petta_test_failed(Actual, Expected)) -->
    [ 'MeTTa test failed: ~p does not match ~p'-[Actual, Expected] ].
prolog:error_message(petta_assertion_failed(Goal)) -->
    [ 'MeTTa assertion failed: ~p'-[Goal] ].

'println!'(Arg, true) :- swrite(Arg, RArg),
                         format('~w~n', [RArg]).

'readln!'(Out) :- read_line_to_string(user_input, Str),
                  sread(Str, Out).

test(A,B,true) :- (A =@= B -> E = '✅' ; E = '❌'),
                  swrite(A, RA),
                  swrite(B, RB),
                  format("is ~w, should ~w. ~w ~n", [RA, RB, E]),
                  ( A =@= B -> true
                  ; throw(error(petta_test_failed(A, B),
                                context(test/3, 'MeTTa test values differ'))) ).

assert(Goal, true) :- ( call(Goal) -> true
                                    ; swrite(Goal, RG),
                                      format("Assertion failed: ~w~n", [RG]),
                                      throw(error(petta_assertion_failed(Goal),
                                                  context(assert/2, 'MeTTa assertion failed'))) ).

%%% The running space: %%%
% (context-space) answers the space whose module the current goal runs in,
% so a program loaded into a named space reaches its own atoms the way a
% program in &self writes (match &self ...); outside any named space the
% answer is &self.
'context-space'(Space) :- ( current_metta_space(Space) -> true ; Space = '&self' ).

%%% Time Retrieval: %%%
'current-time'(Time) :- get_time(Time).
'format-time'(Format, TimeString) :- get_time(Time), format_time(atom(TimeString), Format, Time).

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
py_arg_norm(X, X).
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
                                                py_call(M:Call0, R0, Opts), py_bool_norm(R0, Result)
                                              ; ( Args == []                      % bare "fun"
                                                  -> compound_name_arguments(Call0, A, [])
                                                   ; Call0 =.. [A|Args] ),
                                                py_call(builtins:Call0, R0, Opts), py_bool_norm(R0, Result) ).

%%% States: %%%
'bind!'(A, ['new-state', B], C) :- 'change-state!'(A, B, C).
'change-state!'(Var, Value, true) :- nb_setval(Var, Value).
'get-state'(Var, Value) :- nb_getval(Var, Value).

%%% Eval: %%%
eval(C, Out) :- translate_expr(C, Goals, Out),
                call_goals(Goals).

call_goals([]).
call_goals([G|Gs]) :- call(G), 
                      call_goals(Gs).

%As call_goals/1, but in a named module, so a form run against a space reaches
%that space's own equations. call/1 resolves in the module its clause was
%compiled in, which is why the module has to be named rather than inherited.
%The space's module is in force while the goals run, not only while they were
%compiled. Anything consulting the current space at call time needs it: get-type
%does, so without this a `(: a A)` written in a named space was invisible to
%`!(get-type a)` even though the two ran in the same space.
call_goals_in(Module, Goals) :- with_metta_module(Module, call_goals_in_(Module, Goals)).

call_goals_in_(_, []).
call_goals_in_(Module, [G|Gs]) :- call(Module:G),
                                  call_goals_in_(Module, Gs).

%%% Higher-Order Functions: %%%
'foldl-atom'([], Acc, _Func, Acc).
'foldl-atom'([H|T], Acc0, Func, Out) :- reduce([Func,Acc0,H], Acc1),
                                        'foldl-atom'(T, Acc1, Func, Out).

'map-atom'([], _Func, []).
'map-atom'([H|T], Func, [R|RT]) :- reduce([Func,H], R),
                                   'map-atom'(T, Func, RT).

'filter-atom'([], _Func, []).
'filter-atom'([H|T], Func, Out) :- ( reduce([Func,H], true) -> Out = [H|RT]
                                                             ; Out = RT ),
                                   'filter-atom'(T, Func, RT).

%%% Prolog interop: %%%
argv(K, Arg) :- current_prolog_flag(argv, Argv), nth0(K, Argv, A), ( atom_number(A, N) -> Arg = N ; Arg = A ).
import_prolog_function(N, true) :- register_fun(N).

%A Prolog library loaded from MeTTa belongs to the process, not to a space. Its
%predicates are builtins once loaded, register_fun/1 reads their arity out of
%user, and every space has to be able to call them. SWI loads a file into the
%module the load runs in, and under per-space equations a runnable form runs in
%its space's module, so a library imported inside a named space would define
%itself where register_fun/1 cannot see it: the arities never register and every
%call to it compiles to a partial application instead. In &self the load module
%already is user, so this states that behaviour rather than adding a rule.
consult_global(File) :- user:consult(File).
use_module_global(File) :- user:use_module(File).
'Predicate'([F|Args], Term) :- Term =.. [F|Args].
callPredicate(G, true) :- call(G).
assertzPredicate(G, true) :- assertz(G).
assertaPredicate(G, true) :- asserta(G).
retractPredicate(G, true) :- retract(G), !.
retractPredicate(_, false).

%%% Library / Import: %%%
ensure_metta_ext(Path, Path) :- file_name_extension(_, gz, Path), !.
ensure_metta_ext(Path, Path) :- file_name_extension(_, metta, Path), !.
ensure_metta_ext(Path, PathWithExt) :- file_name_extension(Path, metta, PathWithExt).

import_file_string(File, File) :- string(File), !.
import_file_string(File, SFile) :- atom_string(File, SFile).

resolve_metta_import_path(SFile, Base, CanonPath) :-
    ( Candidate = SFile ; atomic_list_concat([Base, '/', SFile], Candidate) ),
    ensure_metta_ext(Candidate, PathWithExt),
    absolute_file_name(PathWithExt, CanonPath,
                       [access(read), file_errors(fail)]), !.
resolve_metta_import_path(SFile, _, _) :-
    ensure_metta_ext(SFile, RequestedPath),
    throw(error(existence_error(source_sink, RequestedPath),
                context(RequestedPath, 'while importing file'))).

resolve_python_import_path(SFile, Base, CanonPath) :-
    absolute_file_name(SFile, CanonPath,
                       [relative_to(Base), access(read), file_errors(fail)]), !.
resolve_python_import_path(SFile, _, _) :-
    throw(error(existence_error(source_sink, SFile),
                context(SFile, 'while importing file'))).

%The loaded marker is a clause owned by the target space. Its non-true body
%keeps it out of get-atoms/2, while a space clear still retracts it with every
%other Space/N clause. Thus one space life skips an already loaded canonical
%file, a loading marker breaks cycles, and a cleared pooled name reloads all
%forms in its next life.
import_life_marker(_) :- fail.

import_marker_head(Space, CanonPath, Head) :-
    Head =.. [Space, '$petta_import'(CanonPath)].

import_marker_clause(Space, CanonPath, State, Ref) :-
    import_marker_head(Space, CanonPath, Head),
    clause(Head, import_life_marker(State), Ref).

claim_import(Space, CanonPath, skip, _) :-
    import_marker_clause(Space, CanonPath, loaded, _), !.
claim_import(Space, CanonPath, skip, _) :-
    import_marker_clause(Space, CanonPath, loading, _), !.
claim_import(Space, CanonPath, load, Ref) :-
    import_marker_head(Space, CanonPath, Head),
    assertz((Head :- import_life_marker(loading)), Ref).

erase_import_marker(Ref) :-
    ( clause_property(Ref, erased) -> true ; erase(Ref) ).

mark_import_loaded(Space, CanonPath, LoadingRef) :-
    erase_import_marker(LoadingRef),
    import_marker_head(Space, CanonPath, Head),
    assertz((Head :- import_life_marker(loaded))).

run_new_import(Space, CanonPath, LoadingRef, Goal) :-
    catch(( once(Goal)
            -> mark_import_loaded(Space, CanonPath, LoadingRef)
             ; throw(error(import_error(loader_failed),
                           context(CanonPath, 'import loader failed'))) ),
          Error,
          ( erase_import_marker(LoadingRef), throw(Error) )).

:- meta_predicate import_once(+, +, 0).
import_once(Space, CanonPath, Goal) :-
    claim_import(Space, CanonPath, Action, LoadingRef),
    ( Action == skip -> true
    ; run_new_import(Space, CanonPath, LoadingRef, Goal) ).

rethrow_import_target_error(_, Error) :- control_exception(Error), !,
                                         throw(Error).
rethrow_import_target_error(_, Error) :-
    Error = error(_, context(Source, _)),
    ( atom(Source) ; string(Source) ),
    exists_file(Source), !,
    throw(Error).
rethrow_import_target_error(CanonPath, error(Type, _)) :- !,
    throw(error(Type, context(CanonPath, 'while importing file'))).
rethrow_import_target_error(CanonPath, Error) :-
    throw(error(import_error(Error), context(CanonPath, 'while importing file'))).

:- meta_predicate import_target(+, +, 0).
import_target(Space, CanonPath, Goal) :-
    catch(import_once(Space, CanonPath, Goal),
          Error,
          rethrow_import_target_error(CanonPath, Error)).

%Missing targets, loader failures, and loader errors name the target and
%surface to the caller; none is a recovery case. A failed load clears its
%loading marker so a corrected file can be retried. Control exceptions keep
%flying unchanged.
'import!'(Space, File, true) :- importer_helper(Space, File).
importer_helper(Space, File) :-
    import_file_string(File, SFile),
    working_dir(Base),
    ( file_name_extension(_, py, SFile)
      -> resolve_python_import_path(SFile, Base, CanonPath),
         file_directory_name(CanonPath, Dir),
         file_base_name(CanonPath, BaseName),
         file_name_extension(ModuleName, py, BaseName),
         import_target(Space, CanonPath,
                       ( py_call(sys:path:append(Dir), _),
                         py_call(builtins:'__import__'(ModuleName), _) ))
       ; resolve_metta_import_path(SFile, Base, CanonPath),
         import_target(Space, CanonPath,
                       transaction(load_metta_file(CanonPath, _, Space))) ).

:- dynamic translator_rule/1.
'add-translator-rule!'(HV, true) :- ( translator_rule(HV)
                                      -> true ; assertz(translator_rule(HV)) ).

'remove-translator-rule!'(HV, true) :- retractall(translator_rule(HV)).

%%% Registration: %%%
:- dynamic fun/1, arity/2.
register_fun(N) :- fun(N), !.
register_fun(N) :- assertz(fun(N)),
                   forall((current_predicate(N/Arity), \+ (current_op(_, _, N), Arity =< 2)),
                          (arity(N, Arity) -> true ; assertz(arity(N, Arity)))).

%The module whose equations are in scope while a term is compiled or run. The
%default is user, so nothing changes for a program that only ever uses &self.
current_metta_module(Module) :-
    ( nb_current('$petta_module', M) -> Module = M ; Module = user ).

with_metta_module(Module, Goal) :-
    current_metta_module(Previous),
    setup_call_cleanup(b_setval('$petta_module', Module),
                       Goal,
                       b_setval('$petta_module', Previous)).

%Control signals pass through every recovery catch: a caught abort, limit,
%alarm, or interrupt is a stopped program pretending it succeeded. This is
%the KeyboardInterrupt-outside-Exception design; a swallowed limit signal
%also DISARMS call_with_inference_limit for the rest of the call, measured
%as six million inferences spent under a thousand-inference budget when a
%recovery catch ate the signal mid-translation.
control_exception(time_limit_exceeded).
control_exception(inference_limit_exceeded).
control_exception(petta_py_interrupted).
control_exception('$aborted').
control_exception(error(petta_py_time_limit(_), _)).
control_exception(error(petta_py_inference_limit(_), _)).
control_exception(error(resource_error(_), _)).

%The evaluator's catch-all: real errors take the recovery, control
%signals keep flying.
:- meta_predicate catch_recover(0, 0).
catch_recover(Goal, Recovery) :-
    catch(Goal, E, ( control_exception(E) -> throw(E) ; call(Recovery) )).

%The hot recovery case needs no meta-call or compound handler term. Real
%errors fail the candidate; control signals retain catch_recover/2 semantics.
recover_failure(E) :- ( control_exception(E) -> throw(E) ; fail ).

%Whether a symbol is callable from where we are: a process-wide function that
%no named equation module claims, a function this module defines, or one &self
%defines, since &self is shared. fun_scoped/1 summarizes non-user fun_in/2
%claims. A builtin or user-only function is therefore unambiguous in every
%space and avoids a current-module read in higher-order loops.
fun_here(F) :- fun(F), \+ fun_scoped(F), !.
fun_here(F) :- current_metta_module(Module), fun_here_in(Module, F).

fun_here_in(Module, F) :- (   fun_in(Module, F) -> true
                          ;   Module \== user, fun_in(user, F) ).

%Register a function and record which module its clauses live in. fun/1 stays
%global because the translator consults it at compile time to decide whether a
%head is a call or data, and that decision has to hold wherever the term is
%compiled; fun_in/2 says where the clauses actually are, so a caller can ask
%whether *this* space defines a symbol rather than whether any space does.
:- dynamic fun_in/2, fun_scoped/1.
register_fun_in(Module, N) :- register_fun(N),
                              ( fun_in(Module, N) -> true ; assertz(fun_in(Module, N)) ),
                              ( Module == user -> true
                              ; fun_scoped(N) -> true
                              ; assertz(fun_scoped(N)) ).

unregister_fun_in(Module, N) :- retractall(fun_in(Module, N)),
                                ( fun_in(Other, N), Other \== user
                                  -> true ; retractall(fun_scoped(N)) ).

unregister_fun_everywhere(N) :- retractall(fun_in(_, N)),
                                retractall(fun_scoped(N)).
:- maplist(register_fun, [superpose, empty, let, 'let*', '+','-','*','/', '%', min, max, 'change-state!', 'get-state', 'bind!',
                          '<','>','==', '!=', '=', '=?', '<=', '>=', and, or, xor, implies, not, sqrt, exp, log, cos, sin,
                          'first-from-pair', 'second-from-pair', 'car-atom', 'cdr-atom', 'unique-atom', 'alpha-unique-atom',
                          repr, repra, parse, 'println!', 'readln!', test, assert, 'mm2-exec', 'mork-add-atoms', 'mork-flush', atom_concat, atom_chars, copy_term, term_hash,
                          foldl, first, last, append, length, 'size-atom', sort, msort, member, 'is-member', 'is-alpha-member', 'exclude-item', list_to_set, maplist, eval, reduce, 'import!',
                          'add-atom', 'remove-atom', 'get-atoms', match, 'is-var', 'is-ground', 'is-expr', 'is-space', 'get-mettatype',
                          decons, 'decons-atom', 'py-call', 'get-type', 'get-metatype', '=alpha', concat, sread, cons, reverse,
                          '#+','#-','#*','#div','#//','#mod','#min','#max','#<','#>','#=','#\\=','set_hook',
                          'union-atom', 'cons-atom', 'intersection-atom', 'subtraction-atom', 'index-atom', id,
                          'pow-math', 'sqrt-math', 'sort-atom','abs-math', 'log-math', 'exp-math', 'trunc-math', 'ceil-math',
                          'floor-math', 'round-math', 'sin-math', 'cos-math', 'tan-math', 'asin-math','random-int','random-float',
                          'acos-math', 'atan-math', 'isnan-math', 'isinf-math', 'min-atom', 'max-atom',
                          'foldl-atom', 'map-atom', 'filter-atom','current-time','format-time', 'context-space', library, exists_file,
                          import_prolog_function, 'Predicate', callPredicate, assertaPredicate, assertzPredicate, retractPredicate,
                          'add-translator-rule!', 'remove-translator-rule!', argv]).
