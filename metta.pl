% Purpose: provide PeTTa's Prolog runtime, builtins, type system, evaluator,
%   imports, function registration, and named-space execution context.
% Guarantees:
%   - petta_handles_route/5 routes a query by the most specific matching
%     (handles ...) entry in &petta, where specificity is pattern
%     subsumption first and adornment-set inclusion between renaming-equal
%     patterns, disagreeing maximal ties throw petta_contract_conflict/4
%     naming both entries and the query, and a context with no entries
%     fails in one indexed probe [tested 2026-08-17: metta_handles_route]
%     [measured 2026-08-17: 15 inferences per undeclared-context miss].
%   - get-type/2 returns each derived type once, while has_type/2 uses one
%     witness for a fixed expected type [tested 2026-08-15:
%     metta_type_answers, translator_typed_checks].
%   - Import lifecycle state is separate from atom storage, so wildcard atom
%     removal cannot make a loaded source run twice [tested 2026-08-15:
%     filereader_import_lifecycle].
%   - Host failures from builtins retain their ISO error class and name the
%     written MeTTa operation [tested 2026-08-15:
%     metta_operation_errors, translator_evaluation_errors]. Integer
%     arithmetic pays nothing for this and float arithmetic pays one
%     inference per call, because only the integer pair takes the guarded
%     fast path [measured 2026-08-15: 300,000 and 400,000 inferences per
%     100,000 calls, against 300,000 unguarded]. Whole-corpus cost is
%     +2.1% instructions on examples/performance/scale.metta
%     [measured 2026-08-15].
%   - is-alpha-member/3 tests unifiability without retaining bindings in its
%     arguments [tested 2026-08-15: metta_alpha_membership].
%   - alpha-unique-atom/2 confirms identity inside each term-hash bucket, so a
%     hash collision cannot remove an inequivalent term [tested 2026-08-15:
%     metta_alpha_unique].
%   - get-metatype/2 classifies every Prolog term used as a MeTTa value
%     [tested 2026-08-14: metta_metatypes].
%   - petta_transaction/1 answers everything its body answers, and every
%     answer's writes commit or roll back together [tested 2026-08-19:
%     python/tests/test_atomic_forms.py::test_a_transaction_preserves_every_answer_of_its_body].
%   - Every guarded_input_position/3 refuses an unbound argument and names the
%     MeTTa operation, so no builtin binds the caller's variable, invents an
%     answer, runs away or reports a host predicate [tested 2026-08-19:
%     builtin_input_guards:every_builtin_refuses_an_unbound_input_by_name,
%     python/tests/test_builtin_inputs.py::test_a_raising_builtin_names_the_metta_operation_not_the_host_predicate].
%   - ==/3 and !=/3 refuse two operands of known and different types and
%     answer for every other pair, at no cost on two numbers [tested
%     2026-08-19:
%     python/tests/test_equality.py::test_cross_kind_equality_answers_what_the_arbiter_answers]
%     [measured 2026-08-19: 4487.45 inferences per thousand-iteration loop,
%     unchanged].
%   - %Undefined% is consistent with every type in both directions, so a call
%     site refuses only a PROVEN conflict, while has_declared_type/2 demands a
%     witness for a contract [tested 2026-08-19:
%     python/tests/test_gradual_typing.py::test_an_unknown_type_is_consistent_with_every_declared_type,
%     python/tests/test_answer_protocol.py::test_admission_types_the_pool].
%   - An expression no arrow types reads element-wise, and the tuple it reads
%     is %Undefined% as soon as one member's type is [tested 2026-08-19:
%     metta_type_answers:a_tuple_with_an_untyped_member_is_undefined].
%   - get-type/2 and get-type-space/3 answer from declarations without running
%     the inspected expression, so inspection has no effects of its own
%     [tested 2026-08-19:
%     python/tests/test_type_inspection.py::test_get_type_does_not_run_its_arguments_effects].
%   - builtin_type_declaration/2 rows are the union of lib_builtin_types.metta
%     and the prelude's, with each row written once and evicted only by the
%     register that wrote it [tested 2026-08-19:
%     metta_builtin_type_surface:a_shared_declaration_is_evicted_only_from_the_register_that_wrote_it].
%   - Test assertions distinguish no answer from one empty-expression answer
%     [tested 2026-08-14: translator_test_answers].
%   - petta_assertion_failure/4 classifies the three assertion formals, so a
%     harness tells a false claim from a broken engine by TYPE rather than by
%     reading the message [tested 2026-08-19:
%     python/tests/test_assertion_failures.py::test_a_failing_assertion_is_a_different_exception_from_an_engine_fault].
%   - Runtime builtins reject prebound outputs that they would not produce
%     [tested 2026-08-14: metta_builtin_outputs].
%   - Function registration performed by a source load participates in that
%     load's rollback [tested 2026-08-14: filereader_source_rollback].
%   - Python source imports restore sibling modules and sys.path after setup
%     or execution errors [tested 2026-08-14:
%     metta_python_import_cleanup].
%   - Every py_object_extra_type/2 clause is consulted whether or not a host
%     bridge answers py_object_type_names/2, so a (py-atom f Type)
%     declaration survives the Python library being loaded [tested 2026-08-18:
%     python/tests/test_ops.py::test_a_declared_type_survives_the_library_being_loaded]
%     [measured 2026-08-18: +2 inferences per get-type on a Python object and
%     0 on every other value].
%   - The engine loads and runs the full examples/ corpus with
%     set_prolog_flag(autoload, false) already in effect: the
%     directory_file_path/3 directive below needs library(filesex) before
%     the rest of this section's use_module block would otherwise supply
%     it, and next_lambda_name/1 (translator.pl) needs library(gensym) for
%     every foldl-atom/map-atom/filter-atom/'|->' compile, both silently
%     supplied by autoload before now [measured 2026-08-18: NO_AUTOLOAD=1
%     sh test.sh, 200/200 examples; run.sh's own header has the mechanism].
%     Cost: +1.50% instructions:u on a bare boot (swipl -s src/metta.pl,
%     no backends), +0.54% with backends loaded too, +0.14% over a full
%     example run that also exercises the opt-in libraries' own fixes
%     (lib/lib_constraints.pl, lib/lib_memo.pl) [measured 2026-08-18:
%     interleaved min-of-3, perf stat -e instructions:u, spread under
%     0.003% within each side].
% Open Obligations:
%   To Do: check.sh does not yet gate autoload=false; the exact line is
%     `run GATE   no-autoload  sh -c "cd '$HERE' && NO_AUTOLOAD=1 sh
%     test.sh"`, reusing test.sh's own parallel runner and skip list
%     unchanged (check.sh is single-owner, so this is not wired in here).
%   Hacks: None
%   Future Enhancements: None

%%%%%%%%%% Dependencies %%%%%%%%%%
%directory_file_path/3 is library(filesex)'s, not a built-in, and the
%directive a few lines down calls it immediately at load time to compute
%standard_library_path/1, before the rest of this section's use_module
%block would otherwise supply it. Autoload papers over the ordering when
%it is on; with autoload=false the directive fails on an unknown
%procedure and standard_library_path/1 is never asserted, which then
%aborts the boot at load_builtin_type_surface's first (library ...) call.
%So this one import has to come first, ahead of even the section header's
%own first clause.
:- use_module(library(filesex)).
library(X, Path) :- standard_library_path(Base),
                    directory_file_path(Base, X, Path).
%A named library directory, git-fetched or registered. A library that
%pip-installs is under neither: standard_library_path/1 is one directory,
%<src>/../lib, so (library fast.pl) cannot reach a package's own files and a
%downstream library has to pass absolute paths, which is what
%lib/minimal_metta_lib.py does with os.path.dirname(os.path.abspath(__file__)).
%
%SWI already owns the answer. file_search_path/2 is a "dynamic multifile hook
%predicate used to specify path aliases ... called by absolute_file_name/3 to
%search files specified as Alias(Name)" [source: SWI-Prolog 10.1 Reference
%Manual, section 4.36], it composes (the second argument may be another
%alias), and every SWI tool that understands an alias understands one
%registered here. So a package registers its directory once and
%(library pettorch fast.pl) resolves
%[tested: a_registered_library_path_resolves].
library(X, Y, Path) :- git_library_path(X, Base), !,
                       directory_file_path(Base, Y, Path).
library(X, Y, Path) :- Spec =.. [X, Y],
                       (   absolute_file_name(Spec, Resolved,
                                              [access(read), file_errors(fail)])
                       ->  Path = Resolved
                       ;   refuse_unresolved_library(X, Y)
                       ).

%An alias that resolves to nothing RAISES rather than failing, and the
%distinction is CPython's: returning None from find_spec means "not mine, keep
%looking" and raising means "definitively absent", because "the latter
%indicates that the meta path search should continue, while raising an
%exception terminates it immediately" [source: CPython, the import system,
%finders and loaders].
%
%Failing was the keep-looking signal with nothing left to look with, so
%(import! &self (library imp3 plain)) with the extension forgotten answered
%the empty set, imported nothing, and left every name from that file
%undefined. That surfaces much later as an expression evaluating to itself,
%which is the hardest failure in this language to trace back to its cause. A
%plain path that is absent already raised and named itself; this is the same
%rule reaching the alias form
%[tested: an_unresolvable_library_alias_raises].
refuse_unresolved_library(Alias, File) :-
    findall(Directory, file_search_path(Alias, Directory), Directories),
    throw(error(petta_unresolved_library(Alias, File, Directories),
                context(library/3, 'no readable file of that name'))).

prolog:error_message(petta_unresolved_library(Alias, File, [])) -->
    [ '(library ~w ~w) does not resolve: nothing is registered under the \c
       alias ~w. Register the directory with register_metta_library_path, or \c
       import the file by path.'-[Alias, File, Alias] ].
prolog:error_message(petta_unresolved_library(Alias, File, Directories)) -->
    [ '(library ~w ~w) does not resolve: no readable ~w under ~w. Check the \c
       spelling, and that the file carries its extension.'
      -[Alias, File, File, Directories] ].

%Register a directory under a name, so a Python package can point MeTTa at
%the Prolog and MeTTa files it ships beside itself. Idempotent, and a
%directory that is not there is refused where the caller can still act on it
%rather than at the first import that needs it.
register_metta_library_path(Alias, Directory0, true) :-
    must_be(atom, Alias),
    ( atom(Directory0) -> Directory = Directory0 ; atom_string(Directory, Directory0) ),
    (   exists_directory(Directory)
    ->  true
    ;   throw(error(existence_error(directory, Directory),
                    context(register_metta_library_path/3,
                            'a library path must be a directory that exists')))
    ),
    (   user:file_search_path(Alias, Directory)
    ->  true
    ;   assertz(user:file_search_path(Alias, Directory))
    ).
:- prolog_load_context(directory, Source),
   directory_file_path(Source, '..', Parent),
   directory_file_path(Parent, 'lib', LibPath),
   asserta(standard_library_path(LibPath)).
:- autoload(library(uuid)).
:- use_module(library(crypto)).
:- use_module(library(random)).
:- use_module(library(janus)).
:- use_module(library(error)).
:- use_module(library(listing)).
:- use_module(library(aggregate)).
%distinct/2, which 'defined-name'/1 and 'undocumented-space'/2 call to
%dedupe function names read off a space's own equation atoms
%[measured 2026-08-18: examples/libraries/doc_lib.metta under
%NO_AUTOLOAD=1, existence_error(procedure,distinct/2)].
:- use_module(library(solution_sequences)).
:- use_module(library(thread)).
%alarm/4 and remove_alarm/1, which metta_timeout/2 uses instead of
%call_with_time_limit/2 so a bounded goal keeps its answers.
:- use_module(library(time)).
%wrap_predicate/4, for making the pragma bound free when no bound is set.
:- use_module(library(prolog_wrap)).
%library(thread) does not declare its own dependency on option/2, and nothing
%else loaded here pulls library(option) in, so jobs/2 resolved it by autoload
%on the first concurrent_and/3 call [verified 2026-08-15: swi_option is absent
%until something touches option/2]. Loading it up front keeps lazy loading off
%the concurrent path. An `Unknown procedure: thread:option/2` was reported once
%under concurrent hyperpose; a race was NOT reproduced in 12 runs of 24 workers
%entering concurrent_and/2 on a barrier, so treat this as cheap hardening and
%not as a diagnosed fix.
:- use_module(library(option)).
:- use_module(library(lists)).
:- use_module(library(yall), except([(/)/3])).
:- use_module(library(apply)).
:- use_module(library(apply_macros)).
%next_lambda_name/1 (translator.pl) calls gensym/2 to name every compiled
%closure: '|->' itself and, through collection_closure/3, every inline body
%argument of foldl-atom, map-atom and filter-atom. Nothing else loaded here
%pulls library(gensym) in, so today it resolves by autoload on the first
%such compile. With autoload=false that call raises
%existence_error(procedure,gensym/2) from inside the engine's own prelude
%(src/prelude.metta's type-cast-holds is the one equation there that uses
%foldl-atom with an inline body), and SWI's OWN initialization-error
%reporting then masks that primary error: building a source-location
%diagnostic for it calls into library(prolog_clause)'s
%inlined_unification/7, which has its own undeclared, autoload-only
%dependency on nth1/3, so THAT is the only message that ends up printed.
%The visible symptom is "Unknown procedure: prolog_clause:nth1/3" from
%deep inside SWI's shipped library; the actual missing dependency is this
%one, in the engine's own source, and fixing it here removes the secondary
%failure too because the primary error it was papering over never occurs.
:- use_module(library(gensym)).
:- use_module(library(process)).

%Which module the ENGINE's own predicates live in, asked of SWI at load time
%rather than written down. Two different jobs were both spelled `user` and
%only one of them is about the engine:
%
%  - `user` is the HOST module. SWI resolves file_search_path/2 and
%    thread_message_hook/3 there, consult/1 puts a consulted file there, and
%    janus resolves goal text there [source: SWI-Prolog 10.1 Reference
%    Manual, section 6.11 and its footnote "Unfortunately some hooks are
%    traditionally defined in the user module"]. Those sites go on naming
%    `user`, because that is the name of the thing they mean.
%  - THIS is where the engine's own clauses are, which is wherever this file
%    was consulted. Every wrap_predicate/4 target and every clause/2 read of
%    the engine's own compilation tables follows it.
%
%The two answers coincide today. They stop coinciding the moment a host
%consults the engine into a module of its own, and asking rather than writing
%is what makes that a supported thing rather than a silent breakage
%[tested: metta_engine_module].
:- dynamic petta_engine_module/1.
:- prolog_load_context(module, EngineModule),
   (   petta_engine_module(EngineModule) -> true
   ;   assertz(petta_engine_module(EngineModule))
   ).

%The module the base tier compiles into, written ONCE and read everywhere:
%current_metta_module/1's default, reduce/3's dispatch, fun_here_in/2's shared
%tier and the type family's &self clause all ask for it.
%
%Declared here, before the files that read it are compiled, so the expansion
%below applies to them. spaces.pl owns the mapping this is the '&self' case of
%and asserts the same answer into its cache; the plunit test named below is
%what keeps the two from drifting
%[tested: spaces_execution_modules:the_written_self_module_is_the_mapped_one].
metta_self_module('$petta_exec:&self').

%And the prefix the mapping is built from, written once for the same reason
%and read the same way. space_module/2 builds a module name with it,
%metta_module_space/2 strips it, and with_metta_module/2 tests for it.
metta_exec_module_prefix('$petta_exec:').

%And read for FREE. A one-clause fact still costs an inference per call, and
%these are the hottest paths in the engine: reduce/3 reads it on every
%dispatch and current_metta_module/1 on every compile and every runnable form.
%goal_expansion/2 replaces the call with the unification it performs, which
%SWI folds into the clause, so the name stays written in one place and the
%read costs nothing [measured 2026-08-19: annotated-relation 483,019 -> 479,523
%inferences, back to its pre-Phase-11 baseline; py-method-call
%1,696,849,495 -> 1,657,043,976 instructions:u].
%
%A unification rather than `true` with the argument bound at expansion time,
%because most callers use this as a TEST on a module they already hold
%(`metta_self_module(Module), !` selects the &self clause of the type family)
%and binding their variable at compile time would make every module answer
%yes.
goal_expansion(metta_self_module(Module), Module = '$petta_exec:&self').
goal_expansion(metta_exec_module_prefix(Prefix), Prefix = '$petta_exec:').

:- ensure_loaded([ext_points, parser, translator, specializer, filereader,
                  '../lib/lib_gitimport', spaces, tracer, duals, python]).

%%%% Native backends %%%%
%
%A native backend is a space provider whose implementation is a shared library
%rather than Prolog. Once loaded it is a foreign space like any other and this
%file knows nothing more about it; what it needs from the engine is somewhere
%to be loaded FROM, and that is all this does.
%
%One backend used to be named here instead, twice: `'../mork_ffi/morkspaces'`
%in a second copy of the whole load list, and its three builtin names in a
%second argv test further down. So a second native backend could not be added
%without editing this file, which is the one thing EXTENDING.md promises an
%extension author never has to do, and MORK was reaching the engine through a
%door no other provider had. It goes through the seam now like everyone else.
%
%A backend is a file in backends/. Loading one is consulting that file, and
%what it pulls in, where its build artefacts are, and whether they are present
%at all is the backend's own business: a backend that is not built loads
%nothing and says nothing, and one that is built and broken raises, which is
%the split every host wants and none of them should have to implement.
%
%The engine's own position is fixed rather than the backend's: they load after
%everything, because a provider is reached through metta_foreign_space/1 and
%not through clause order. That was true before this change and is what made it
%safe [verified 2026-08-16: moved, whole gate green including the MORK tests].
:- prolog_load_context(directory, Src),
   current_prolog_flag(argv, Argv),
   (   memberchk(backends, Argv)
   ->  directory_file_path(Src, '../backends/*.pl', Pattern),
       expand_file_name(Pattern, Found),
       msort(Found, Files),
       forall(member(File, Files), ensure_loaded(File))
   ;   true
   ).

%%%%%%%%%% Standard Library for MeTTa %%%%%%%%%%

%%% Representation and parsing conversions: %%%
id(X, X).
%noeval is the Atom mask on both sides: the declaration in
%lib/lib_builtin_types.metta stops the argument being reduced on the way in and
%its Atom return type stops the answer being reduced on the way out, so the
%body is the identity and the types are the whole implementation. That is how
%the reference defines it [source: metta-lang-docs, types_basics/metatypes:
%"This is the way noeval function is implemented"].
noeval(X, X).
repr(Term, R) :- swrite(Term, Text), R = Text.
repra(Term, R) :- term_to_atom(Term, R).
parse(Str, _) :- var(Str), !, refuse_unbound_input(parse, 1).
parse(Str, R) :- sread(Str, R).

%%% Arithmetic & Comparison: %%%
%An arithmetic operand is a number. Everything else is refused here, before
%is/2 applies Prolog's own coercion rules to it.
%
%Two things came through that door. A MeTTa expression IS a Prolog list, and
%SWI reads a one-element list as a character code, so (+ 1 (g)) quietly
%answered 104, the code of g, and (* 2 (z)) answered 244: a symbol's SPELLING
%became a number, while the two-element case raised.
%
%Worse, Prolog's evaluable atoms silently outranked MeTTa. With (= pi 3.14)
%defined, (+ 1 pi) answered 4.141592653589793 from SWI's constant rather than
%4.14 from the user's own equation. A constant belongs in a MeTTa library as
%an ordinary rewrite, (= (my-pi) 3.14), which reduces before arithmetic sees
%it and now wins because nothing shadows it.
%
%Nobody chose either behaviour; both fall out of is/2. The whole corpus, 169
%programs including the ones passing inf and nan around, is unaffected
%[tested: metta_arithmetic_operands].
%An unbound operand is left to is/2, which raises instantiation_error for it,
%the answer Prolog and ISO both give; refusing it as a type error here would
%report a missing value as a wrong one.
%Both operands in one call: the inline type tests are free, the call is not,
%so checking them separately cost two inferences per operation instead of one
%[measured 2026-08-15: alpha-unique +200,010 against +100,005].
metta_arith_operands(Op, A, B) :-
    ( var(A) -> true ; number(A) -> true ; throw_metta_type_error(Op, number, A) ),
    ( var(B) -> true ; number(B) -> true ; throw_metta_type_error(Op, number, B) ).

%The four operators run BACKWARDS over integers: exactly one unbound
%argument among integers solves for it, so (let 4 (- $x 1) $x) answers 5
%and (unify 6 (* $x 2) ...) binds 3, the WAM plus/3 reading MeTTaLog
%compiles to. The ground fast path is untouched and stays first;
%petta_int_solve sits BEHIND the ground-number path, so ground floats
%never meet it (annotated-relation measured +1 inference per float op
%with the solver between the paths, and par with it behind them
%[measured 2026-08-18]); strings and the two-var case behave exactly as
%before (two unbound arguments stay an instantiation error: bounded
%solving is this file's job, constraint propagation is
%lib_constraints'). Multiplicative
%backward modes are exact-division only, and a non-divisible pair FAILS
%rather than errors, the relational reading: no integer solves it.
'+'(A,B,R)  :- ( integer(A), integer(B) -> R is A + B
                ; number(A), number(B)
                  -> catch(R is A + B, E, rethrow_metta_operation_error('+', E))
                ; petta_int_solve('+', A, B, R, Verdict) -> Verdict == solved
                ; metta_arith_operands('+', A, B),
                  catch(R is A + B, E, rethrow_metta_operation_error('+', E)) ).
'-'(A,B,R)  :- ( integer(A), integer(B) -> R is A - B
                ; number(A), number(B)
                  -> catch(R is A - B, E, rethrow_metta_operation_error('-', E))
                ; petta_int_solve('-', A, B, R, Verdict) -> Verdict == solved
                ; metta_arith_operands('-', A, B),
                  catch(R is A - B, E, rethrow_metta_operation_error('-', E)) ).
'*'(A,B,R)  :- ( integer(A), integer(B) -> R is A * B
                ; number(A), number(B)
                  -> catch(R is A * B, E, rethrow_metta_operation_error('*', E))
                ; petta_int_solve('*', A, B, R, Verdict) -> Verdict == solved
                ; metta_arith_operands('*', A, B),
                  catch(R is A * B, E, rethrow_metta_operation_error('*', E)) ).
'/'(A,B,R)  :- ( integer(A), integer(B), B =\= 0 -> R is A / B
                ; number(A), number(B)
                  -> catch(R is A / B, E, rethrow_metta_operation_error('/', E))
                ; petta_int_solve('/', A, B, R, Verdict) -> Verdict == solved
                ; metta_arith_operands('/', A, B),
                  catch(R is A / B, E, rethrow_metta_operation_error('/', E)) ).

%One unbound slot among integers: the verdict says whether the mode
%applied at all (fail: not this shape, fall through to the float/error
%path) and whether it solved (none: the mode fits but no integer answers
%it, so the operator FAILS, the relational reading of (* $x 2) = 7).
%plus/3 carries the additive family in C.
petta_int_solve('+', A, B, R, solved) :-
    ( var(A), integer(B), integer(R) -> plus(A, B, R)
    ; var(B), integer(A), integer(R) -> plus(A, B, R)
    ).
petta_int_solve('-', A, B, R, solved) :-
    ( var(A), integer(B), integer(R) -> plus(B, R, A)
    ; var(B), integer(A), integer(R) -> plus(B, R, A)
    ).
petta_int_solve('*', A, B, R, Verdict) :-
    ( var(A), integer(B), integer(R), B =\= 0
    ->  ( 0 =:= R mod B -> A is R // B, Verdict = solved ; Verdict = none )
    ; var(B), integer(A), integer(R), A =\= 0
    ->  ( 0 =:= R mod A -> B is R // A, Verdict = solved ; Verdict = none )
    ).
petta_int_solve('/', A, B, R, Verdict) :-
    ( var(A), integer(B), integer(R)
    ->  A is R * B, Verdict = solved
    ; var(B), integer(A), integer(R), R =\= 0
    ->  ( 0 =:= A mod R -> B is A // R, Verdict = solved ; Verdict = none )
    ).
'%'(A,B,R)  :- ( integer(A), integer(B), B =\= 0 -> R is A mod B
                ; metta_arith_operands('%', A, B),
                  catch(R is A mod B, E, rethrow_metta_operation_error('%', E)) ).
'<'(A,B,R)  :- ( number(A), number(B) -> (A<B -> R=true ; R=false)
                ; metta_arith_operands('<', A, B),
                  catch((A<B -> R=true ; R=false), E,
                        rethrow_metta_operation_error('<', E)) ).
'>'(A,B,R)  :- ( number(A), number(B) -> (A>B -> R=true ; R=false)
                ; metta_arith_operands('>', A, B),
                  catch((A>B -> R=true ; R=false), E,
                        rethrow_metta_operation_error('>', E)) ).
%(-> $a $a Bool): ONE type variable, so the two operands must have a
%consistent type, and a comparison across two known and different kinds is
%refused rather than answered. `!(== 1 "S")` answered False, which is the
%answer for two Numbers that differ, so a conditional took the else branch and
%nothing said the question was meaningless. `=alpha` is the comparison that
%accepts anything, and it is declared (-> Atom Atom Bool) for that reason.
%
%Measured 2026-08-19 on hyperon 0.2.10 and on the LeaTTa mechanised
%interpreter, byte-identical across both: (== 1 "S"), (== True 1),
%(== xnum ystr) and (== xnum "s") are BadArgType, while (== 1 a),
%(== a "a"), (== xnum 1), (== xnum undeclared) and (== 1 (foo)) are False and
%(== 1 1), (== "S" "S") and (== () ()) are True. The unknown side is what
%makes the False cases False: nothing is known about `a`, so nothing is
%contradicted.
%Two numbers inline, the shape '<'/3 above already uses, because that is what
%a loop compares and the guard must not be felt there.
'=='(A,B,R) :- ( number(A), number(B) -> (A==B -> R=true ; R=false)
                ; comparable_operands('==', A, B),
                  (A==B -> R=true ; R=false) ).
'!='(A,B,R) :- ( number(A), number(B) -> (A==B -> R=false ; R=true)
                ; comparable_operands('!=', A, B),
                  (A==B -> R=false ; R=true) ).
%The guard the declaration above states, enforced at the predicate's own door
%rather than through typed dispatch, which is what runtime_type_guarded/1
%means and what keeps the cost near zero: the common case is two literals and
%a first-argument-indexed type lookup.
%
%EXPRESSIONS ARE EXCLUDED, because the two references disagree about them and
%nothing here should pick a side that neither of them agrees on. Measured
%2026-08-19: hyperon answers False for (== () 1), (== "s" ()) and
%(== (1 2) (1 2 3)) while LeaTTa raises BadArgType for the first two and
%answers False for the third. Both answer False for (== (1 2 3) ()) and
%(== (1 2) (a b)), which is the shape a MeTTa program actually writes, so the
%collapse-and-compare idiom is untouched either way.
%TWO TIERS, because asking the type system costs 26 inferences and a program
%compares literals in a loop. Two operands of the same intrinsic kind settle
%it with one type test and no lookup, which is the case a loop writes; only a
%pair the kinds do not settle pays for a declaration
%[measured 2026-08-19: a thousand-iteration == loop is 4487.45 inferences
%unguarded, 30514.55 with the lookup on every call, and 4990.45 with this
%tier in front, so the guard costs 0.50 inferences per comparison instead
%of 26.03].
comparable_operands(Operation, A, B) :-
    (   same_intrinsic_kind(A, B)
    ->  true
    ;   is_list(A)
    ->  true
    ;   is_list(B)
    ->  true
    ;   current_metta_module(Module),
        \+ ( has_type_in(Module, A, Type), has_type_in(Module, B, Type) )
    ->  once(has_type_in(Module, A, Expected)),
        throw_metta_type_error(Operation, Expected, B)
    ;   true
    ).

%Fails when the kinds DIFFER and when they do not decide, so an undecided
%pair falls through to the declarations rather than being waved past.
same_intrinsic_kind(A, B) :- number(A), !, number(B).
same_intrinsic_kind(A, B) :- string(A), !, string(B).
same_intrinsic_kind(A, B) :- metta_boolean(A), !, metta_boolean(B).

metta_boolean(true).
metta_boolean(false).

'='(A,B,R) :-  (A=B -> R=true ; R=false).
'=?'(A,B,R) :- (\+ \+ A=B -> R=true ; R=false).
'=alpha'(A,B,R) :- (A =@= B -> R=true ; R=false).
'=@='(A,B,R) :- (A =@= B -> R=true ; R=false).
'<='(A,B,R) :- ( number(A), number(B) -> (A =< B -> R=true ; R=false)
                ; metta_arith_operands('<=', A, B),
                  catch((A =< B -> R=true ; R=false), E,
                        rethrow_metta_operation_error('<=', E)) ).
'>='(A,B,R) :- ( number(A), number(B) -> (A >= B -> R=true ; R=false)
                ; metta_arith_operands('>=', A, B),
                  catch((A >= B -> R=true ; R=false), E,
                        rethrow_metta_operation_error('>=', E)) ).
min(A,B,R)  :- ( integer(A), integer(B) -> R is min(A,B)
                ; metta_arith_operands(min, A, B),
                  catch(R is min(A,B), E,
                        rethrow_metta_operation_error(min, E)) ).
max(A,B,R)  :- ( integer(A), integer(B) -> R is max(A,B)
                ; metta_arith_operands(max, A, B),
                  catch(R is max(A,B), E,
                        rethrow_metta_operation_error(max, E)) ).
exp(Arg,R) :- catch(R is exp(Arg), E,
                    rethrow_metta_operation_error(exp, E)).
:- use_module(library(clpfd)).
'#+'(A, B, R) :- catch(R #= A + B, E,
                       rethrow_metta_operation_error('#+', E)).
'#-'(A, B, R) :- catch(R #= A - B, E,
                       rethrow_metta_operation_error('#-', E)).
'#*'(A, B, R) :- catch(R #= A * B, E,
                       rethrow_metta_operation_error('#*', E)).
'#div'(A, B, R) :- catch(R #= A div B, E,
                         rethrow_metta_operation_error('#div', E)).
'#//'(A, B, R) :- catch(R #= A // B, E,
                        rethrow_metta_operation_error('#//', E)).
'#mod'(A, B, R) :- catch(R #= A mod B, E,
                         rethrow_metta_operation_error('#mod', E)).
'#min'(A, B, R) :- catch(R #= min(A,B), E,
                         rethrow_metta_operation_error('#min', E)).
'#max'(A, B, R) :- catch(R #= max(A,B), E,
                         rethrow_metta_operation_error('#max', E)).
'#<'(A, B, true)  :- catch(A #< B, E,
                           rethrow_metta_operation_error('#<', E)), !.
'#<'(A, B, false) :- catch(A #>= B, E,
                           rethrow_metta_operation_error('#<', E)).
'#>'(A, B, true)  :- catch(A #> B, E,
                           rethrow_metta_operation_error('#>', E)), !.
'#>'(A, B, false) :- catch(A #=< B, E,
                           rethrow_metta_operation_error('#>', E)).
'#='(A, B, true)  :- catch(A #= B, E,
                           rethrow_metta_operation_error('#=', E)), !.
'#='(A, B, false) :- catch(A #\= B, E,
                           rethrow_metta_operation_error('#=', E)).
'#\\='(A, B, true)  :- catch(A #\= B, E,
                              rethrow_metta_operation_error('#\\=', E)), !.
'#\\='(A, B, false) :- catch(A #= B, E,
                              rethrow_metta_operation_error('#\\=', E)).
%The other two comparisons of the same family. Four of the six were defined and
%these two were not, and nothing in examples/ or lib/ used any of them, so
%nothing noticed.
%
%The absence was quiet rather than loud, and that part is the language working
%correctly: an expression whose head has no definition is DATA, so (#=< 1 2)
%answered (#=< 1 2). A symbol is data or a function depending on whether
%something defines it, which is what makes an undefined name usable as a term
%at all. The defect was the incomplete family, not the way it showed.
'#=<'(A, B, true)  :- catch(A #=< B, E,
                            rethrow_metta_operation_error('#=<', E)), !.
'#=<'(A, B, false) :- catch(A #> B, E,
                            rethrow_metta_operation_error('#=<', E)).
'#>='(A, B, true)  :- catch(A #>= B, E,
                            rethrow_metta_operation_error('#>=', E)), !.
'#>='(A, B, false) :- catch(A #< B, E,
                            rethrow_metta_operation_error('#>=', E)).

'pow-math'(A, B, Out) :- catch(Out is A ** B, E,
                               rethrow_metta_operation_error('pow-math', E)).
'sqrt-math'(A, Out) :- catch(Out is sqrt(A), E,
                             rethrow_metta_operation_error('sqrt-math', E)).
'abs-math'(A, Out) :-
    ( integer(A) -> Out is abs(A)
    ; catch(Out is abs(A), E,
            rethrow_metta_operation_error('abs-math', E)) ).
'log-math'(Base, X, Out) :- catch(Out is log(X) / log(Base), E,
                                  rethrow_metta_operation_error('log-math', E)).
'exp-math'(A, Out) :- catch(Out is exp(A), E,
                            rethrow_metta_operation_error('exp-math', E)).
'trunc-math'(A, Out) :- catch(Out is truncate(A), E,
                              rethrow_metta_operation_error('trunc-math', E)).
'ceil-math'(A, Out) :- catch(Out is ceil(A), E,
                             rethrow_metta_operation_error('ceil-math', E)).
'floor-math'(A, Out) :- catch(Out is floor(A), E,
                              rethrow_metta_operation_error('floor-math', E)).
'round-math'(A, Out) :- catch(Out is round(A), E,
                              rethrow_metta_operation_error('round-math', E)).
'sin-math'(A, Out) :- catch(Out is sin(A), E,
                            rethrow_metta_operation_error('sin-math', E)).
'cos-math'(A, Out) :- catch(Out is cos(A), E,
                            rethrow_metta_operation_error('cos-math', E)).
'tan-math'(A, Out) :- catch(Out is tan(A), E,
                            rethrow_metta_operation_error('tan-math', E)).
'asin-math'(A, Out) :- catch(Out is asin(A), E,
                             rethrow_metta_operation_error('asin-math', E)).
'acos-math'(A, Out) :- catch(Out is acos(A), E,
                             rethrow_metta_operation_error('acos-math', E)).
'atan-math'(A, Out) :- catch(Out is atan(A), E,
                             rethrow_metta_operation_error('atan-math', E)).
'isnan-math'(A, Out) :-
    catch(( A =:= A -> Out = false ; Out = true ), E,
          rethrow_metta_operation_error('isnan-math', E)).
'isinf-math'(A, Out) :-
    catch(( ( A =:= 1.0Inf ; A =:= -1.0Inf )
            -> Out = true ; Out = false ), E,
          rethrow_metta_operation_error('isinf-math', E)).
%must_be/2 walks the list a second time with a type check per element, so a
%numeric list costs 3x what min_list alone does [measured 2026-08-15: 20 calls
%over 50,000 elements, 3,000,220 against 1,000,060 inferences]. That buys
%'min-atom': Type error: `number' expected, found `a' in place of a leaked
%lists:min_list/3, which is the trade this file makes everywhere.
'min-atom'(List, Out) :- non_list(List), !, Out = [].
'min-atom'(List, Out) :- catch(( must_be(list(number), List),
                                min_list(List, Out) ), E,
                              rethrow_metta_operation_error('min-atom', E)).
'max-atom'(List, Out) :- non_list(List), !, Out = [].
'max-atom'(List, Out) :- catch(( must_be(list(number), List),
                                max_list(List, Out) ), E,
                              rethrow_metta_operation_error('max-atom', E)).

%%% Random Generators: %%%
'random-int'(Min, Max, Result) :-
    ( integer(Min), integer(Max), Min =< Max
      -> random_between(Min, Max, Result)
       ; catch(random_between(Min, Max, Result), E,
               rethrow_metta_operation_error('random-int', E)) ).
'random-int'('&rng', Min, Max, Result) :-
    ( integer(Min), integer(Max), Min =< Max
      -> random_between(Min, Max, Result)
       ; catch(random_between(Min, Max, Result), E,
               rethrow_metta_operation_error('random-int', E)) ).
'random-float'(Min, Max, Result) :-
    catch(( random(R), Result is Min + R * (Max - Min) ), E,
          rethrow_metta_operation_error('random-float', E)).
'random-float'('&rng', Min, Max, Result) :-
    catch(( random(R), Result is Min + R * (Max - Min) ), E,
          rethrow_metta_operation_error('random-float', E)).

%%% Boolean Logic: %%%
bool(true).
bool(false).
%An unbound argument ENUMERATES the booleans, so and(A, B, C) with all three
%open answers the whole truth table. That is deliberate and pinned by
%metta_operation_errors:boolean_operations_remain_relational, which is why
%these positions are relational_input_position/2 rather than guarded ones.
boolean_argument(_, _, Value) :- var(Value), !, bool(Value).
boolean_argument(_, _, true) :- !.
boolean_argument(_, _, false) :- !.
boolean_argument(Operation, _, Culprit) :-
    throw_metta_type_error(Operation, boolean, Culprit).

and(A,B,C) :- boolean_argument(and, 1, A), boolean_argument(and, 2, B),
              ( A == true -> C = B ; A == false -> C = false ).
or(A,B,C) :- boolean_argument(or, 1, A), boolean_argument(or, 2, B),
             ( A == true -> C = true ; A == false -> C = B ).
not(A,B) :- boolean_argument(not, 1, A),
            ( A == true -> B = false ; A == false -> B = true ).
xor(A,B,C) :- boolean_argument(xor, 1, A), boolean_argument(xor, 2, B),
              ( A == B -> C = false ; C = true ).
implies(A,B,C) :- boolean_argument(implies, 1, A),
                  boolean_argument(implies, 2, B),
                  ( A == true -> ( B == true  -> C = true
                                 ; B == false -> C = false )
                              ; A == false -> C = true ).

%%% Nondeterminism: %%%
superpose(L, _) :- var(L), !, refuse_unbound_input(superpose, 1).
superpose(L,X) :- member(X,L).
empty(_) :- fail.

%%% Lists / Tuples: %%%
'cons-atom'(H, T, [H|T]).
%The grounded reading goes FIRST and fails fast, rather than after the cons
%clause, because the cons clause has no cut: a variable-headed clause behind it
%stays a candidate that indexing cannot rule out, so every decons of a real
%list left a choicepoint, in loops that recurse on exactly this
%[tested: decons_atom_is_total]. non_list/1 is false for both list shapes, so a
%list pays two inferences and reaches the same clauses in the same order.
'decons-atom'(Term, _) :- var(Term), !, refuse_unbound_input('decons-atom', 1).
'decons-atom'(Term, Out) :- non_list(Term), !,
                            grounded_list_view(Term, [H|T]), !, Out = [H|[T]].
%The second cut prunes the SEAM's remaining providers, which the first one
%cannot: it fires on non_list/1, before the seam has been consulted at all, so
%without this every decons of a grounded value carried a live choice point into
%whatever loop it was in [tested: a_tuple_reads_as_an_expression]. It belongs
%here, at the one caller whose own cut comes too early, rather than in the seam:
%making the seam itself deterministic costs 400 million instructions on
%alpha-unique, 10.7%, for reasons that outlive this comment
%[measured 2026-08-16, ai-design-grounded-view.md records the reproduction].
'decons-atom'([H|T], [H|[T]]).
%The empty expression answers an error rather than nothing, so decons-atom is
%TOTAL. Failing here is not "no decomposition", it is the whole continuation
%vanishing: (chain (decons-atom ()) $l TEMPLATE) never runs its template and
%the branch after it is unreachable. That cost the specification's own Turing
%machine both of its blank-cell arms and mm-switch its "no case matched" arm,
%and nothing in either program said why [source: lib/minimal_metta_lib.metta,
%recorded there as C1b and C1d].
%
%The shape is the reference implementation's, because PeTTa had no considered
%answer here to keep: failing was the absence of a clause rather than a
%decision. LeaTTa's conformance evidence pins it to the Rust interpreter,
%lib/src/metta/interpreter.rs:1750-1758, which tests the empty case as an
%execution error, and records the byte-identical output
%[source: /home/user/Dev/LeaTTa/tests/semantics/metaprogramming/EVIDENCE.md,
%M06 "Empty deconstruction is an error"].
%
%Three elements, which the callers need. lib_measure.metta and lib_soft.metta
%destructure with (let ($h $t) (decons-atom $ps) ...) and rely on the empty
%case not matching; a two-element error would bind $h to Error and answer a
%wrong result in silence, where a three-element one still fails to unify and
%those loops terminate exactly as before [tested: decons_atom_is_total, the_empty_error_does_not_destructure_as_a_pair].
'decons-atom'([], ['Error', ['decons-atom', []],
                   "expected: (decons-atom (: <expr> Expression)), \c
                    found: (decons-atom ())"]).
'first-from-pair'(Pair, _) :- var(Pair), !, refuse_unbound_input('first-from-pair', 1).
'first-from-pair'([A, _], A).
first(Pair, _) :- var(Pair), !, refuse_unbound_input(first, 1).
first([A, _], A).
'second-from-pair'(Pair, _) :- var(Pair), !, refuse_unbound_input('second-from-pair', 1).
'second-from-pair'([_, A], A).
'unique-atom'(A, _) :- var(A), !, refuse_unbound_input('unique-atom', 1).
'unique-atom'(A, B) :- non_list(A), !, B = [].
'unique-atom'(A, B) :- list_to_set(A, B).

%%% Alpha-equivalence unique atom %%%
'alpha-unique-atom'(A, _) :- var(A), !, refuse_unbound_input('alpha-unique-atom', 1).
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
    alpha_bucket_insert(Key, HCopy, SeenIn, SeenOut, IsNew),
    ( IsNew == false ->
        alpha_list_to_set_assoc(T, SeenIn, R)
    ;
        R = [H|RT],
        alpha_list_to_set_assoc(T, SeenOut, RT)
    ).

%A term hash selects a small bucket. Identity inside the bucket decides alpha
%equivalence, because canonical terms produced above are ground.
alpha_bucket_insert(Key, Term, SeenIn, SeenOut, IsNew) :-
    ( get_assoc(Key, SeenIn, Bucket) ->
        ( memberchk_eq(Term, Bucket) ->
            SeenOut = SeenIn,
            IsNew = false
        ;
            put_assoc(Key, SeenIn, [Term|Bucket], SeenOut),
            IsNew = true
        )
    ;
        put_assoc(Key, SeenIn, [Term], SeenOut),
        IsNew = true
    ).

%A term that can never become a list, no matter how it gets instantiated:
non_list(X) :- atomic(X), X \== [].
non_list(X) :- compound(X), X \= [_|_].

%%%%%%%%%% An unbound argument where a value is required %%%%%%%%%%
%
%A structural operation READS a term; it does not solve for one. An unbound
%variable in a position the engine's own type surface declares Expression,
%Number, String, Symbol or Bool is a program error, and letting one through
%produced four different silent wrongs at once, measured 2026-08-19 by a
%probe generated over every such position:
%
%  - 28 positions BOUND THE CALLER'S VARIABLE. (car-atom $u) unified $u with
%    [H|_] through the head and answered the fresh H, so the caller's own
%    variable came back a list it never wrote.
%  - 13 answered a fresh variable and 12 answered a value derived from
%    nothing, (union-atom (a b) $u) answering the partial list (a b|_).
%  - 2 EXHAUSTED THE STACK. (subtraction-atom $u (a b)) reaches a list walk
%    with both ends open and enumerates every list there is.
%  - 7 raised, but named a HOST predicate the MeTTa program never wrote:
%    (sort-atom $u) said `msort/2`, (sread $u) said `atom_codes/2`.
%
%The POSITIONS are read off builtin_type_declaration/2 rather than listed, so
%declaring a type for a new builtin strengthens its guard in the same stroke
%and the table and the guards cannot drift apart. The probe in
%python/tests/test_builtin_inputs.py enumerates the same table.
%
%Each guard is a LEADING clause on a var first argument, and it costs nothing
%where it would be felt: 'car-atom'([1,2], _) is 2.0000 inferences per call
%with the guard and 2.0000 without, over 200,000 calls, and a MeTTa walk over
%a ten-element list through cdr-atom is 1052.23 inferences either way
%[measured 2026-08-19, both directly and through the engine's own counter].
%A bound argument does not reach the clause.
strict_input_type('Expression').
strict_input_type('Number').
strict_input_type('String').
strict_input_type('Symbol').
strict_input_type('Bool').

%The constraint family is RELATIONAL by design: (#+ $a 2 $r) is a constraint
%to post rather than a call to run, and an unbound argument there is the whole
%point. Both directions are pinned by metta.plt's relational_arithmetic unit.
relational_builtin('#+').   relational_builtin('#-').
relational_builtin('#*').   relational_builtin('#div').
relational_builtin('#mod'). relational_builtin('#min').
relational_builtin('#max'). relational_builtin('#<').
relational_builtin('#>').   relational_builtin('#//').

%One POSITION can be relational where the rest of the predicate is not, and
%the type surface cannot say so because it names a type and not a mode.
%(index-atom (a b) $i) enumerates 0-a and 1-b, which is deliberate and is
%pinned by metta.plt's metta_index_atom unit.
relational_input_position('index-atom', 2).
%and, or, not, xor and implies ENUMERATE the booleans for an open argument,
%so and(A, B, C) with all three open answers the whole truth table
%[tested: metta_operation_errors:boolean_operations_remain_relational].
relational_input_position(and, 1).      relational_input_position(and, 2).
relational_input_position(or, 1).       relational_input_position(or, 2).
relational_input_position(not, 1).
relational_input_position(xor, 1).      relational_input_position(xor, 2).
relational_input_position(implies, 1).  relational_input_position(implies, 2).
%cons builds a PATTERN, and an open tail is what makes it one: the engine's
%own prelude writes (cons Error $_) to test whether a value is an error
%[source: src/prelude.metta, if-error]. cons-atom is the same operation under
%its MeTTa name.
relational_input_position(cons, 2).
relational_input_position('cons-atom', 2).

%A position PeTTa promises to refuse. A name lent to MeTTa from SWI (msort,
%append, sort, maplist, length) keeps Prolog's own relational behaviour and
%its own errors, because under that name it IS the Prolog predicate; that is
%a boundary rather than an omission, and imported_from/1 is where the engine
%already records it.
guarded_input_position(Name, Arity, Position) :-
    builtin_type_declaration(Name, ['->'|Chain]),
    \+ relational_builtin(Name),
    append(Inputs, [_], Chain),
    nth1(Position, Inputs, Type),
    nonvar(Type),
    strict_input_type(Type),
    length(Chain, Arity),
    functor(Head, Name, Arity),
    predicate_property(Head, defined),
    \+ predicate_property(Head, imported_from(_)),
    \+ relational_input_position(Name, Position),
    \+ unguarded_input_position(Name, Position).

%The three positions this rule does NOT yet cover, named rather than hidden.
%Each predicate lives in a file the change that added this guard does not
%own, and each is measured 2026-08-19: get-atoms/2 and match/4 are in
%src/spaces.pl and raise an instantiation_error with no context at all, so a
%program is told a value is missing and not which one; sread/2 is in
%src/parser.pl and raises naming system:atom_codes/2, a predicate the MeTTa
%program never wrote. parse/2 is the same operation under PeTTa's own name
%and IS guarded, so the gap is the direct sread call only.
unguarded_input_position('get-atoms', 1).
unguarded_input_position(match, 1).
%git-import!/2 is in lib/lib_gitimport.pl and sleep/2 in a library too; both
%raise an instantiation_error with no context, so the program is told a value
%is missing and not which operation wanted it [measured 2026-08-19].
unguarded_input_position('git-import!', 1).
unguarded_input_position(sleep, 1).
unguarded_input_position(sread, 1).
%A fourth of the same shape: add-reduct/3 refuses, and by name, but names the
%operation it DELEGATES to. `!(add-reduct $u a)` answers
%(Error (add-atom $u a) "add-atom expects a space as the first argument"), so
%a program that wrote add-reduct is told about add-atom. src/spaces.pl again.
unguarded_input_position('add-reduct', 1).

%Names the MeTTa operation and the argument, in the program's own vocabulary.
%The formal stays ISO so a MeTTa (catch ...) and the Python boundary can both
%read it, exactly as throw_metta_type_error/3 keeps its own.
refuse_unbound_input(Operation, Position) :-
    throw(error(petta_unbound_input(Operation, Position),
                context(Operation, 'invalid MeTTa operation argument'))).

:- multifile prolog:error_message//1.
%The operation's own name is the CONTEXT's to print, exactly as it is for
%`+: number expected, found "s"`, so it is not repeated here.
prolog:error_message(petta_unbound_input(_, Position)) -->
    [ 'a value expected in argument ~w, found an unbound variable'-[Position] ].

%%% Taking an expression apart, and the grounded values that also read as one.
%
%Each of these grew ONE clause, placed after the cut that a real list takes, so
%a MeTTa expression costs exactly what it did before and only a term that is
%not a list ever asks whether it has a structural view. The SWI manual's rule
%for it: these predicates stay under ten clauses, so selection is "a linear
%scan for a possible matching clause" on the primary index argument, and the
%variable-headed clause that was already here is what decides that, not the new
%one [source 2026-08-16, SWI-Prolog 10.1 Reference Manual 2.17].
'sort-atom'(List, _) :- var(List), !, refuse_unbound_input('sort-atom', 1).
'sort-atom'(List, Sorted) :- non_list(List), !,
                             ( grounded_list_view(List, View) -> msort(View, Sorted) ; Sorted = [] ).
'sort-atom'(List, Sorted) :- msort(List, Sorted).
'size-atom'(List, _) :- var(List), !, refuse_unbound_input('size-atom', 1).
'size-atom'(List, Size) :- non_list(List), !,
                           ( grounded_list_view(List, View) -> length(View, Size) ; Size = [] ).
'size-atom'(List, Size) :- length(List, Size).
'car-atom'(Term, _) :- var(Term), !, refuse_unbound_input('car-atom', 1).
'car-atom'([H|_], H) :- !.
'car-atom'(Term, Out) :- grounded_list_view(Term, [H|_]), !, Out = H.
'car-atom'(Term, []) :- \+ Term = [_|_].
'cdr-atom'(Term, _) :- var(Term), !, refuse_unbound_input('cdr-atom', 1).
'cdr-atom'([_|T], T) :- !.
'cdr-atom'(Term, Out) :- grounded_list_view(Term, [_|T]), !, Out = T.
'cdr-atom'(Term, []) :- \+ Term = [_|_].
decons(Term, _) :- var(Term), !, refuse_unbound_input(decons, 1).
decons([H|T], [H|[T]]).
cons(H, T, [H|T]).
'index-atom'(List, _, _) :- var(List), !, refuse_unbound_input('index-atom', 1).
'index-atom'(_, Index, Elem) :- nonvar(Index), \+ integer(Index), !,
                                Elem = [].
'index-atom'(List, Index, Elem) :- var(Index), !,
                                  indexable_list(List, View),
                                  nth0(Index, View, Elem).
'index-atom'(List, Index, Elem) :-
    indexable_list(List, View),
    ( nth0(Index, View, Value) -> Elem = Value ; Elem = [] ).

indexable_list(List, List) :- is_list(List), !.
indexable_list(Term, View) :- grounded_list_view(Term, View), !.
indexable_list(List, List).

%A grounded value's own reading of itself as an expression, asked only of terms
%that are not expressions already. Nothing here knows Python: the provider is
%whoever loaded one, and with none loaded this is a single failing call.
%once/1 because this is an OWNERSHIP seam: a value has one structural reading,
%and whichever provider recognises it is the one that answers. Without it every
%caller inherits the choice point of the providers that have not been tried,
%and a caller whose own cut comes BEFORE this call cannot prune it: decons-atom
%cuts on non_list/1 first, so every decons of a Python tuple carried a live
%choice point into whatever loop it was in
%[tested: a_tuple_reads_as_an_expression].
grounded_list_view(Term, View) :-
    nonvar(Term),
    (   metta_grounded_structure(Term, View)
    ->  true
    ;   compound(Term),
        compound_name_arguments(Term, Name, Arguments),
        View = [Name|Arguments]
    ).

%The fallback above is the writer's rule read backwards. A Prolog compound
%already PRINTS as `(name arg ...)`, which is how an error reaches a program:
%`(catch (f))` answers `(Error (python_error ZeroDivisionError "division by
%zero") (context ...))`, and every part of that after `Error` was a compound. So
%it printed as an expression and refused to behave as one, `car-atom` of the
%formal answering `()` and a `let` over it matching nothing. A program could see
%that a call failed and could not ask WHAT failed, which is most of what an
%error is for.
%
%A provider is asked first and can disagree: a Python tuple is -/N and reads as
%its elements NORMALIZED, so a None inside one reads as `()` rather than as
%janus's spelling of it.
member(_, L, _) :- var(L), !, refuse_unbound_input(member, 2).
member(X, L, true) :- member(X, L).
'is-member'(_, List, _) :- var(List), !, refuse_unbound_input('is-member', 2).
'is-member'(X, List, true) :- member(X, List).
'is-member'(X, List, false) :- \+ member(X, List).

%"Alpha" is historical. This predicate tests unifiability, with a bare query
%variable matching only a variable list element. Double negation at the public
%boundary keeps that test's bindings private; it is deliberately not =@=/2.
member_alpha(X, [H|_]) :- (var(X) -> var(H) ; true), X = H, !.
member_alpha(X, [_|T]) :- member_alpha(X, T).

'is-alpha-member'(_, List, _) :- var(List), !,
                                 refuse_unbound_input('is-alpha-member', 2).
'is-alpha-member'(X, List, true) :- \+ \+ member_alpha(X, List), !.
'is-alpha-member'(X, List, false) :- \+ member_alpha(X, List).

'exclude-item'(_, L, _) :- var(L), !, refuse_unbound_input('exclude-item', 2).
'exclude-item'(A, L, R) :- exclude(==(A), L, R).

%Remove the first element identical to X, keeping the rest in order. select/3
%unifies instead, which both answers wrongly and binds the caller's variables:
%(subtraction-atom ($x) (a)) came back () with $x bound to a. PeTTa's own
%formalisation removes by equality, in leanPeTTa/StreamOps.lean:
%  removeFirstEq (x : Pattern) : List Pattern -> Option (List Pattern)
%    | y :: ys => if y == x then some ys else ...
select_eq(X, [Y|Ys], Ys) :- X == Y, !.
select_eq(X, [Y|Ys], [Y|Rest]) :- select_eq(X, Ys, Rest).

%Multisets. Keep the variable-headed non-list fallback last so list calls use
%the first argument index. Over 100,000 two-element calls this reduced each
%operation from 2,200,002 to 1,400,002 inferences [measured: 800,000 fewer
%inferences per operation, 2026-08-15]. The list clauses still handle a
%non-list right operand before recursing, preserving the empty-tuple result.
'subtraction-atom'(A, B, _) :- ( var(A) -> refuse_unbound_input('subtraction-atom', 1)
                               ; var(B) -> refuse_unbound_input('subtraction-atom', 2)
                               ; fail ).
'subtraction-atom'([], _, []) :- !.
'subtraction-atom'([H|T], B, Out) :- !,
    ( non_list(B) -> Out = []
    ; select_eq(H, B, BRest) -> 'subtraction-atom'(T, BRest, Out)
    ; Out = [H|Rest],
      'subtraction-atom'(T, B, Rest) ).
'subtraction-atom'(A, B, Out) :- ( non_list(A) ; non_list(B) ), !, Out = [].
%The guard its two siblings already have, and it leads rather than trails
%because append/3 succeeds on a non-list right operand: (union-atom (a) b)
%built the improper list [a|b], printed as (cons a b), which is not a tuple
%and cannot be consumed by any tuple operation. A non-list left operand
%failed silently. The empty-tuple answer is this family's settled convention.
%
%non_list/1 is false for an unbound argument, which is load-bearing: lib_roman
%calls (union-atom $xs ($x)) with $xs unbound to SPLIT a list, so append/3
%must still be reached in its relational modes
%[tested: metta_set_operations, examples/libraries/roman_test.metta].
'union-atom'(A, B, _) :- ( var(A) -> refuse_unbound_input('union-atom', 1)
                         ; var(B) -> refuse_unbound_input('union-atom', 2)
                         ; fail ).
'union-atom'(A, B, Out) :- ( non_list(A) ; non_list(B) ), !, Out = [].
'union-atom'(A, B, Out) :- append(A, B, Out).
'intersection-atom'(A, B, _) :- ( var(A) -> refuse_unbound_input('intersection-atom', 1)
                                ; var(B) -> refuse_unbound_input('intersection-atom', 2)
                                ; fail ).
'intersection-atom'([], _, []) :- !.
'intersection-atom'([H|T], B, Out) :- !,
    ( non_list(B) -> Out = []
    ; select_eq(H, B, BRest) -> Out = [H|Rest],
                                'intersection-atom'(T, BRest, Rest)
    ; 'intersection-atom'(T, B, Out) ).
'intersection-atom'(A, B, Out) :- ( non_list(A) ; non_list(B) ), !, Out = [].

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
                              metta_module_space(Module, Space).

%A ':' declaration in scope here: this space's, and &self's, since &self is the
%shared space. That is the rule fun_here/1 already applies to functions.
type_declaration(X, T) :- current_metta_module(Module),
                          type_declaration_in(Module, X, T).

%The prelude tier comes LAST in each clause, so a declaration a program
%writes for the same name wins over the engine's prelude, the order the
%type surface already keeps for get-type. The my-if tutorial mechanism is
%what this tier carries: an Atom parameter declared in src/prelude.metta
%masks that argument at every call site, which is how the prelude's
%assertEqualToResult receives its expected set unevaluated.
%In the user clause the prelude branch comes FIRST, and the order is
%about determinism, not precedence: a first-arg-indexed lookup fails
%fast for every ordinary name, and the disjunction is then EXHAUSTED
%when match/4 yields its last solution, so a raw first-solution caller
%(filereader.plt calls type_declaration/2 bare) is left with exactly the
%choicepoint profile this predicate had before the prelude existed.
%Precedence still belongs to the user because eviction removes the
%prelude's rows the moment &self defines or declares the name, so the
%two stores answer together only when the user has said nothing.
%A module and the space it serves used to be the same atom for every space but
%&self, so a module could be handed to match/4 where a SPACE was asked for.
%They are different atoms now, and metta_module_space/2 is the one step
%between them.
type_declaration_in(Module, X, T) :- metta_self_module(Module), !,
                                     (   prelude_type_declaration(X, T)
                                     ;   match('&self', [':', X, T], T, _) ).
type_declaration_in(Module, X, T) :- metta_module_space(Module, Space),
                                     (   prelude_type_declaration(X, T)
                                     ;   match(Space, [':', X, T], T, _)
                                     ;   match('&self', [':', X, T], T, _) ).

%A declaration that is not an arrow types the SYMBOL and cannot type a call to
%it, and nothing said so. `(: inc Number)` beside `(= (inc $x) (+ $x 1))`
%compiles the call site as bare `inc("s", A)`, so the string travels into `+`
%and the program dies inside arithmetic with `+: number expected`; the same
%file written `(: inc (-> Number Number))` compiles
%`once(has_type("s",'Number') *-> true ; get-metatype(...))` around the call
%and refuses it at inc's own door [reproduced 2026-08-16, both goals are in
%filereader_untypable_declaration].
%
%So this refuses rather than warns. The defect is not that the declaration is
%wrong, it is that the declaration LOOKS like it types the function, does not,
%and every diagnostic the author then gets points somewhere else entirely.
%
%The condition is semantic, not spelling. A first draft rejected any type
%whose head merely LOOKED like a mistyped arrow, and this repository is its
%own counter-example: lib_nars.metta writes NARS inheritance as `(--> $a $b)`
%and lib_combinatorics.metta writes a lambda as `(|-> ...)`, 95 and 48
%occurrences, every one of them a deliberate atom in a data position. What
%decides here is whether the name has an arrow declaration AT ALL, which
%neither of those ever claims to be.
%
%One arrow among several declarations is enough, because MeTTa lets a name
%carry more than one. `%Undefined%` is the engine's own way of writing
%"deliberately untyped" and is not an offender, and neither is a variable,
%which a later binding may still fill.
%
%Judged over a name's WHOLE set of declarations, which is why the caller is
%the source loader and not add-atom/3. A build that writes `(: f Number)` and
%`(: f (-> Number Number))` as two atoms passes through a state where only the
%first is stored, and refusing there refuses a program that is about to be
%correct. Declarations that reach a space by any other route are named by
%space.lint(), which reads the finished space instead of an intermediate one.
untypable_declarations(Types, Offender) :-
    Types \== [],
    \+ ( member(Arrow, Types), nonvar(Arrow), Arrow = [->|_] ),
    member(Offender, Types),
    nonvar(Offender),
    Offender \== '%Undefined%'.

%The context is `none` rather than an unbound variable so that a file load
%replaces it with the filename: rethrow_metta_file_error/2 leaves an error
%whose context already unifies with context(_, _) exactly as it found it, and
%an unbound context unifies with anything.
refuse_untypable_declaration(Name, Types) :-
    (   untypable_declarations(Types, Offender)
    ->  throw(error(petta_untypable_declaration(Name, Offender), none))
    ;   true ).

%&self is always the engine's native space. Its fixed private storage module
%keeps this recursive type probe on a compiled direct call, with no provider
%dispatch or exception handler.
%The soft cut is the precedence rule: a program that declares an arrow for a
%name is answered from its own space and the engine's surface is never
%consulted, and only a name the program says nothing about falls through to
%the engine's. The engine's arrows have to be here at all because get-type
%stopped evaluating its argument, so an application now reaches this probe as
%written: without the fallthrough (get-type (+ 1 2)) typed ELEMENT-WISE and
%answered ((-> Number Number Number) Number Number) where it used to answer
%Number, and the arbiter answers ErrorType for (get-type (Error Foo Boo))
%from exactly this route [source: LeaTTa
%tests/semantics/types-meta/30_evaluation_control.metta].
get_function_type([F|Args], T) :- nonvar(F),
                                  (   '$petta_atoms:&self':'&self'(':', F, [->|Ts0])
                                  *-> Ts = Ts0
                                  ;   builtin_type_declaration(F, [->|Ts])
                                  ),
                                  append(As,[T],Ts),
                                  metta_self_module(Self),
                                  maplist(has_type_in(Self), Args, As).
get_function_type_in(Module, [F|Args], T) :- \+ metta_self_module(Module),
                                             nonvar(F),
                                             (   type_declaration_in(Module, F, [->|Ts0])
                                             *-> Ts = Ts0
                                             ;   builtin_type_declaration(F, [->|Ts])
                                             ),
                                             append(As,[T],Ts),
                                             maplist(has_type_in(Module), Args, As).

%A `get-type` equation compiles into the module of the space that wrote it, so
%&self's rule predicate lives in &self's module and this declaration goes
%there: without it get_type_rule_in/3's last clause raises existence_error on
%the first (get-type ...) of a program that never defined a rule.
:- metta_self_module(Self), dynamic(Self:get_type_rule/2).
%get-type is the user-facing set boundary. Candidate derivations may overlap,
%for example an expression can be typed both element-wise and by an explicit
%declaration. Collecting candidates and retaining each first occurrence removes
%those duplicate answers without changing the declared type order.
%Internal checks call has_type/2 instead: a fixed expected type stops at its
%first witness, while an unbound shared type variable still enumerates the
%distinct choices needed to make later arguments consistent.
'get-type'(X, T) :- current_metta_module(Module),
                    type_answers(Module, X, Types),
                    member(T, Types).

has_type(X, T) :- current_metta_module(Module),
                  has_type_in(Module, X, T).

%The first-witness shortcut is only sound for a GROUND expected type. A
%parametric one such as (Pair $t) is nonvar but still carries a variable the
%later arguments must agree on, and once/1 commits to whichever witness came
%first: with (: p1 (Pair A)), (: p1 (Pair B)) and (: p2 (Pair B)) declared,
%(samepair p1 p2) answered nothing while (samepair p2 p1) answered True, from
%one symmetric definition [tested: a_parametric_expected_type_enumerates_its_witnesses].
%The widened list is consulted only AFTER the direct one has failed, which is
%where every subtype answer lives anyway: a value whose declared type already
%matches never pays for the graph, and a program with no (:< ...) edge pays one
%failing indexed query on the branch that was going to fail regardless. This is
%the check an argument goes through, so `(: Rex Dog)` with `(:< Dog Animal)`
%now satisfies a parameter of type Animal
%[tested: an_argument_is_accepted_through_its_supertype].
%%Undefined% is the GRADUAL type and it is compatible with everything, in
%both directions. A parameter declared %Undefined% accepts any argument, and
%an argument whose type is %Undefined% satisfies any parameter: nothing is
%known about it, so no violation is provable and gradual typing lets it
%through. This engine had both directions backwards. `%Undefined%` as the
%expected type demanded that the value be UNTYPED, so
%(: tensor (-> %Undefined% DLTensor)) refused 1.0 and typed its own
%application element-wise; and a value with no declaration failed a concrete
%parameter, so (== 1 a) had no answer through a shared type variable.
%
%Measured 2026-08-19 on hyperon 0.2.10 and on the LeaTTa mechanised
%interpreter, byte-identical across both: with (: f2 (-> Number Number)) and
%(: g2 (-> %Undefined% Number)), (f2 a), (f2 (undeclared-call)), (g2 "s") and
%(g2 1) all answer, while (f2 "s") is a BadArgType. String is KNOWN and it is
%not Number; `a` is not known to be anything.
%
%The second direction is checked last, on the branch that was going to fail
%anyway, so a value whose declared type already matches never pays for it.
has_type_in(Module, X, T) :-
    ( ground(T)
      -> ( T == '%Undefined%'
           -> true
            ; (   type_witness_in(Module, X, T)
              ->  true
              ;   type_answers(Module, X, Types),
                  Types == ['%Undefined%']
              ) )
       ; any_super_type_edge(Module)
         -> type_answers(Module, X, Types),
            member(T, Types)
        ; % No (:< ...) edge anywhere: the full set's order IS candidate
          % order, so the answers can stream, deduplicated by variance
          % exactly as unique_type_answers decides, first occurrence kept,
          % and a checking caller's soft cut stops at its first witness
          % instead of paying findall plus dedup for the whole set. On
          % nilbc's 797k nonground-type judgements the materialized set
          % was the remaining hot block [measured 2026-08-17, profile/2].
          % The seen-list is a per-call compound mutated with nb_setarg,
          % which library(solution_sequences) distinct/2 also does
          % underneath but with a per-call hash table whose setup cost
          % 1.6x the whole findall it replaced at one or two candidates
          % per call [measured 2026-08-17: 17.6e9 to 28.4e9 and back].
          (   lazy_unique_candidate(Module, X, C)
          *-> T = C
          ;   T = '%Undefined%'
          ) ).

%A WITNESS that X has type T, which is the other question a caller can ask
%and is not the same one. has_type_in/3 asks whether X's type is CONSISTENT
%with T and lets an unknown through, because a call site may not refuse what
%it cannot prove wrong. A gate asks whether X is KNOWN to be a T, and an
%unknown must not pass one: `(admits &pool Space)` is a contract, and an atom
%nothing declares is not evidence of a Space
%[tested: python/tests/test_answer_protocol.py::test_admission_types_the_pool].
type_witness_in(Module, X, T) :-
    (   once(type_candidate_in(Module, X, T))
    ->  true
    ;   satisfies_metatype(X, T)
    ->  true
    ;   type_answers(Module, X, Types),
        once(( member(Widened, Types), Widened == T ))
    ).

has_declared_type(X, T) :- current_metta_module(Module),
                           type_witness_in(Module, X, T).

%The first clause is the whole common case and pays no bookkeeping at
%all: a deterministic check derives one candidate and commits. Only a
%caller that actually RETRIES reaches the second clause, which re-seeds
%the seen-list with the first candidate and streams the rest, so a
%variant repeat of the first is excluded exactly as it was when the
%whole set was materialized.
lazy_unique_candidate(Module, X, Candidate) :-
    once(type_candidate_in(Module, X, Candidate)).
lazy_unique_candidate(Module, X, Candidate) :-
    once(type_candidate_in(Module, X, First)),
    duplicate_term(First, Seed),
    State = seen([Seed]),
    type_candidate_in(Module, X, Candidate),
    arg(1, State, Seen),
    \+ ( member(Previous, Seen), Previous =@= Candidate ),
    duplicate_term(Candidate, Kept),
    nb_setarg(1, State, [Kept|Seen]).

type_answers(Module, X, Types) :-
    findall(Type, type_candidate_in(Module, X, Type), Candidates),
    unique_type_answers(Candidates, Unique),
    widen_to_super_types(Module, X, Unique, Widened),
    ( Widened == [] -> Types = ['%Undefined%'] ; Types = Widened ).

%%%% Subtyping: (:< Sub Super) %%%%
%
%`:<` is upstream's spelling, SUB_TYPE_SYMBOL at lib/src/metta/mod.rs:22, and
%the arrow points from the subtype to the supertype, which is why it is not
%`:>`. Read `(:< Dog Animal)` as "Dog is below Animal".
%
%The mechanism is not what the name suggests, and getting that wrong is the
%whole of why this took a rewrite rather than a rule. Upstream never DECIDES a
%subtyping relation while checking an argument: it WIDENS the argument's type
%LIST, and the ordinary type check then runs unchanged against the wider list.
%So the matcher learns nothing about subtyping, and `get-type` is the surface
%where it shows [source: /home/user/Dev/LeaTTa/ai-report-subtype-graph.md,
%against pinned hyperon 0.2.10 at 3f76dc4].
%
%What is NOT widened: a grounded literal's built-in type and an application's
%return type, because upstream's get_atom_types_internal queries the space only
%for symbols and expressions. So `(:< Number Foo)` leaves `(get-type 1)` at
%Number, and `(: f (-> A B))` with `(:< B C)` leaves `(get-type (f a))` at B.
%Two phases, because the ORDER is observable through collapse and upstream's
%is not the order one pass produces: tuple products first, then the direct
%declarations already widened, then one more widening over the whole list. With
%(: (a b) D), (:< (A B) C) and (:< D E) that answers ((A B) D E C), where a
%single pass over the whole list answers ((A B) D C E)
%[source: LeaTTa ai-report-subtype-graph.md, get_tuple_types].
widen_to_super_types(Module, X, Types0, Types) :-
    (   widening_applies_to(Module, X),
        any_super_type_edge(Module)
    ->  findall(Declared, type_declaration_in(Module, X, Declared), Directs),
        partition(type_already_listed(Directs), Types0, Direct, Products),
        add_super_types(Module, Direct, DirectWidened),
        append(Products, DirectWidened, Combined),
        add_super_types(Module, Combined, Types)
    ;   Types = Types0
    ).

%The dispatch mirrors type_candidate_in/3's, which sends the `user` module to
%the /2 predicates and every named space to the /3 ones. Asking the /3 one
%about `user` simply fails, so an application's return type was widened when it
%must not be: (: f (-> A B)) with (:< B C) answered (B C) for (get-type (f a))
%where upstream answers (B) [tested: an_application_return_type_is_not_widened].
widening_applies_to(Module, X) :-
    \+ number(X),
    \+ string(X),
    X \== true,
    X \== false,
    \+ application_return_type(Module, X).

application_return_type(Module, X) :- metta_self_module(Module), !, get_function_type(X, _).
application_return_type(Module, X) :- get_function_type_in(Module, X, _).

%One indexed query rather than one per type: with no edge declared anywhere,
%which is every program that does not use the feature, this is the whole cost.
%The native probe peeks the storage clause directly instead of walking the
%match/4 chain: first-argument indexing answers an empty ':<' bucket in a
%few instructions, where the chain cost ~25 inferences 797k times on
%nilbc's type resolutions [measured 2026-08-17, profile/2]. A space
%served by a foreign provider keeps the full chain, because its edges do
%not live in a storage module.
any_super_type_edge(Module) :-
    (   metta_self_module(Module)
    ->  native_edge_probe('&self')
    ;   metta_module_space(Module, Space),
        metta_foreign_space(Space)
    ->  \+ \+ super_type_in(Module, _, _)
    ;   metta_module_space(Module, Space2),
        native_edge_probe(Space2)
    ->  true
    ;   %A native name with no storage module yet holds no clauses, so
        %only &self can carry an edge for it; probing the full match
        %chain here instead cost a fresh python space +400k inferences on
        %alpha-unique's counter before its first native write [measured
        %2026-08-17]. A provider that plugs in through raw multifile
        %match/4 clauses without metta_foreign_space/1 is outside this
        %probe, and outside the seam's documented contract (EXTENDING.md:
        %"Do not add raw match/4 clauses instead"); declaring the seam is
        %what buys module-local edge service.
        native_edge_probe('&self')
    ).

native_edge_probe(Space) :-
    native_storage_module_cache(Space, StorageModule),
    (   Space == '&self'
    ->  \+ \+ clause(StorageModule:'&self'(':<', _, _), _)
    ;   Head =.. [Space, ':<', _, _],
        \+ \+ clause(StorageModule:Head, _)
    ).

super_type_in(Module, T, S) :- metta_self_module(Module), !,
                               match('&self', [':<', T, S], S, _).
super_type_in(Module, T, S) :- metta_module_space(Module, Space),
                               (   match(Space, [':<', T, S], S, _)
                               ;   match('&self', [':<', T, S], S, _) ).

%add_super_types, round by round: each round asks for the supertypes of exactly
%what the PREVIOUS round appended, and appends every one that was not present
%in the list AS IT STOOD WHEN THE ROUND BEGAN.
%
%That last clause is why the diamond A<:B, A<:C, B<:D, C<:D answers
%(A B C D D) and not (A B C D). Both B and C reach D in the same round, and
%presence is checked against the list from before the round, so D is appended
%twice. It is a parity artifact and it is reproduced deliberately: answering
%more tidily than the arbiter is still answering differently
%[tested: the_diamond_reproduces_upstreams_duplicate].
%
%The three clauses below are upstream's own, read from the source rather than
%inferred from its behaviour [source 2026-08-16,
%hyperon-experimental lib/src/metta/types.rs:49-63]:
%
%    sub_types.iter().skip(from)          the frontier is only the last round
%    if !sub_types.contains(&typ)         checked BEFORE this round appends
%    add_super_types(space, sub_types, sub_types.len())   recurse over the new
%
%and the spelling is `:<` at lib/src/metta/mod.rs:22, `SUB_TYPE_SYMBOL`. There
%is no `:>` in that source: the arrow points from the subtype UP to the
%supertype, so `(:< Dog Animal)` is "Dog is below Animal".
add_super_types(Module, Types, Widened) :-
    super_type_rounds(Module, Types, Types, Widened).

super_type_rounds(_, [], Widened, Widened) :- !.
super_type_rounds(Module, Frontier, Accumulated, Widened) :-
    findall(Super,
            ( member(Type, Frontier), super_type_in(Module, Type, Super) ),
            Supers),
    exclude(type_already_listed(Accumulated), Supers, Fresh),
    (   Fresh == []
    ->  Widened = Accumulated
    ;   append(Accumulated, Fresh, Grown),
        super_type_rounds(Module, Fresh, Grown, Widened)
    ).

type_already_listed(Listed, Type) :- member(Present, Listed), Present == Type.

%Alpha-equivalent polymorphic types are one answer, first occurrence
%kept, which preserves derivation order (observable through collapse).
%The equivalence is =@=, variance, the same relation canonical
%numbervars keys decide: (List $x) repeats (List $y) and (F $x $x) does
%not repeat (F $x $y). The earlier implementation built a numbervars
%copy of every candidate and keysorted twice; candidate lists are almost
%always one or two entries, and on nilbc's 797k resolutions the copies
%and sorts were ~40% of the whole type-resolution profile [measured
%2026-08-17, profile/2], so the quadratic identity walk with the
%C-implemented =@= is the faster shape at every realistic length.
unique_type_answers(Candidates, Unique) :-
    variant_unique_(Candidates, [], Unique).

variant_unique_([], _, []).
variant_unique_([Type|Types], Seen, Out) :-
    (   member(Present, Seen), Present =@= Type
    ->  variant_unique_(Types, Seen, Out)
    ;   Out = [Type|Rest],
        variant_unique_(Types, [Type|Seen], Rest)
    ).

type_candidate_in(Module, X, T) :- metta_self_module(Module),
                                   get_type_candidate(X, T).
type_candidate_in(Module, X, T) :- \+ metta_self_module(Module),
                                   get_type_candidate_in(Module, X, T).
type_candidate_in(Module, X, T) :- get_type_rule_in(Module, X, T).

%A `get-type` equation compiles to get_type_rule/2 in the module of the space
%that wrote it, &self's included: the second clause is that space's own rule
%and reads &self's module by name rather than calling it unqualified, which
%before Phase 11 was the same thing and is not any more.
get_type_rule_in(Module, X, T) :- \+ metta_self_module(Module),
                                  fun_in(Module, 'get-type'),
                                  Module:get_type_rule(X, T).
get_type_rule_in(_, X, T) :- metta_self_module(Self), Self:get_type_rule(X, T).

python_object_blob(X) :- blob(X, Blob), python_object_blob_name(Blob).

python_object_blob_name(py).
python_object_blob_name('PyObject').

get_type_candidate(X, 'Number')   :- number(X), !.
get_type_candidate(X, _) :- var(X), !.
get_type_candidate(X, 'String')   :- string(X), !.
get_type_candidate(true, 'Bool')  :- !.
get_type_candidate(false, 'Bool') :- !.
%Only Python blobs can be Janus references. The blob guard avoids calling into
%Janus, and initializing Python, while typing ordinary MeTTa values;
%py_is_object/1 still validates a live reference and reports a freed one.
%
%The blob SWI registers is named `py`, and this asked for 'PyObject', so the
%guard never held and every clause behind it was unreachable: in an engine
%without the Python library loaded, `(get-type <a python object>)` answered
%%Undefined% rather than the object's classes. The library has its own bridge
%and hid it [measured 2026-08-16: `(Puppy Dog Animal)` through the library,
%%Undefined% through run.sh]. Both names are accepted so the guard cannot
%break again when one of them changes.
get_type_candidate(X, T) :- atomic(X), \+ atom(X),
                            python_object_blob(X), py_is_object(X),
                            py_object_type(X, T).
get_type_candidate(X, T) :- get_function_type(X,T).
get_type_candidate(X, T) :- \+ get_function_type(X, _),
                            is_list(X),
                            metta_self_module(Self),
                            maplist(has_type_in(Self), X, Members),
                            tuple_type(Members, T).
get_type_candidate(X, T) :- '$petta_atoms:&self':'&self'(':', X, T),
                            acyclic_term(T).
get_type_candidate(X, T) :- builtin_type_declaration(X, T).

get_type_candidate_in(_, X, 'Number')   :- number(X), !.
get_type_candidate_in(_, X, _) :- var(X), !.
get_type_candidate_in(_, X, 'String')   :- string(X), !.
get_type_candidate_in(_, true, 'Bool')  :- !.
get_type_candidate_in(_, false, 'Bool') :- !.
get_type_candidate_in(_, X, T) :- atomic(X), \+ atom(X),
                                  python_object_blob(X), py_is_object(X),
                                  py_object_type(X, T).
get_type_candidate_in(Module, X, T) :- get_function_type_in(Module, X, T).
get_type_candidate_in(Module, X, T) :- \+ get_function_type_in(Module, X, _),
                                       is_list(X),
                                       maplist(has_type_in(Module), X, Members),
                                       tuple_type(Members, T).

get_type_candidate_in(Module, X, T) :- type_declaration_in(Module, X, T).
get_type_candidate_in(_, X, T) :- builtin_type_declaration(X, T).

%An expression no arrow types is read ELEMENT-WISE, and the tuple it reads is
%%Undefined% as soon as one member's type is. Nothing is known about a tuple
%one of whose components is unknown, so reporting the shape while a hole sits
%inside it claims more than was derived: `(get-type (some-undeclared-call))`
%answered `(%Undefined%)`, a one-element tuple, where the answer is that
%nothing is known at all.
%
%Recursion falls out of the bottom-up walk rather than being written: an inner
%tuple carrying a hole is itself %Undefined%, so the outer one collapses too.
%Measured 2026-08-19 on hyperon 0.2.10 and on the LeaTTa mechanised
%interpreter, byte-identical across both: `(typed-sym (typed-sym typed-sym))`
%is `(Number (Number Number))` and `(typed-sym (typed-sym aa))` is
%%Undefined%, one undeclared symbol away.
%
%== rather than memberchk/2, because a member's type may still be an unbound
%variable and memberchk would BIND it to %Undefined% and answer yes.
tuple_type(Members, Type) :-
    (   member(Member, Members), Member == '%Undefined%'
    ->  Type = '%Undefined%'
    ;   Type = Members
    ).
%A grounded Python object is Grounded, and its Python classes are its types:
%every class on the object's method resolution order short of object itself is
%a candidate, so a torch Linear is a Linear and a Module, in the same way
%MeTTa's own types are nondeterministic. This is what lets a declared
%(-> Tensor Tensor Tensor) hold for values the host created.
%A bridge that knows how to read the object answers with every type name at
%once, protocols included, as plain text the boundary cannot damage; without
%one, the class walk below runs. What a bridge owns is the CLASS WALK and
%nothing else, so the engine-side extra types are a second clause rather than
%a branch of this one.
%No catch here, deliberately. A bridge whose py_object_type_names/2 clause
%THROWS is the registrant's bug, and reading the throw as "no bridge answered"
%ran the class walk instead: one broken protocol predicate silently destroyed
%typing for every host object in the process, and get-type answered Box, the
%envelope's own class, for all of them. python/petta/_ops.py says the rule in
%as many words for the same probe on the Python side: "A broken probe is the
%registrant's bug: surface it with the protocol's name attached, never as a
%type quietly missing." The fallback is for a bridge that is ABSENT, which is
%an ordinary configuration and stays one [tested: metta_object_types].
py_object_type(X, T) :- ( py_object_type_names(X, Names)
                          -> member(N, Names),
                             ( atom(N) -> T = N ; atom_string(T, N) )
                        ; py_object_class_type(X, T) ).
%A protocol the object satisfies may name a type too, and so may a
%(py-atom f Type) declaration, both through py_object_extra_type/2, so a
%declared (-> DLTensor ...) holds for every array library at once. This is a
%DECLARATION seam, where every clause has to stay reachable, and not an
%ownership one [source: src/ext_points.pl, ext_point_every_clause_runs/1]. It
%used to hang off py_object_class_type/2, which is the ELSE arm above, and
%the shipped library answers the bridge for every Python object: the arm was
%dead in that configuration and a declared type was accepted and then
%dropped. `(py-atom math.pow (-> Number Number Number))` answered
%`(builtin_function_or_method)` through the library and
%`(builtin_function_or_method (-> Number Number Number))` through run.sh
%[measured 2026-08-18]
%[tested: python/tests/test_ops.py::test_a_declared_type_survives_the_library_being_loaded].
%Two relations rather than one wider if-then-else, for the reason Sterling and
%Shapiro give for lifting entitlement/2 out of pension/2: a cut that picks a
%default correctly still prevents the alternatives being found
%[source: The Art of Prolog 2nd ed, 11.5 "Default Rules", pp 206-207].
py_object_type(X, T) :- py_object_extra_type(X, T).

py_object_class_type(X, T) :- py_call(builtins:type(X), Class),
                              py_call(builtins:getattr(Class, '__mro__'), MRO),
                              py_call(builtins:list(MRO), Classes),
                              member(C, Classes),
                              py_call(builtins:getattr(C, '__name__'), Name),
                              ( atom(Name) -> T = Name ; atom_string(T, Name) ),
                              T \== object.

%Computed from the VALUE and then unified, rather than dispatched on the answer.
%The clauses below are ordered and cut on X, so they are only correct when the
%second argument arrives unbound; with it bound, an earlier clause whose head
%names a different metatype simply does not unify and the catch-all at the
%bottom claims the call. That made `(get-metatype foo Grounded)` SUCCEED for a
%symbol, and both callers ask with it bound: has_type/2 and the type guard the
%translator compiles around every declared parameter, so a parameter declared
%`Grounded` accepted anything at all
%[tested: a_grounded_parameter_admits_an_unknown_and_refuses_a_declared_other].
'get-metatype'(X, Metatype) :- metatype_of(X, Computed), Metatype = Computed.

metatype_of(X, 'Variable') :- var(X), !.
metatype_of(X, 'Grounded') :- number(X), !.
metatype_of(X, 'Grounded') :- string(X), !.
metatype_of(true,  'Grounded') :- !.
metatype_of(false, 'Grounded') :- !.
metatype_of(X, 'Grounded') :- python_object_blob(X), py_is_object(X), !.
metatype_of(X, 'Grounded') :- atom(X), fun(X), !.  % e.g., '+' is a registered fun/1
metatype_of(X, 'Expression') :- is_list(X), !.     % e.g., (+ 1 2), (a b)
metatype_of(X, 'Symbol') :- atom(X), !.            % e.g., a
metatype_of(_, 'Grounded').                        % e.g., partial(f,[1]), f(1)

%A parameter declared with a METATYPE accepts any atom of that kind, which is
%what makes a variadic constructor declarable: a container has no fixed arity
%and the language's answer for that is `Expression`, which is how HE declares
%`(: superpose (-> Expression Atom))`. Before this, no metatype checked in a
%parameter position at all, so `(: PyList (-> Expression PyList))` typed a call
%to it as the tuple product of its arguments rather than as PyList.
%
%`Atom` accepts everything, and the mechanism is NOT the subtype relation `:<`
%spells even though the tutorial's wording invites that reading. It is one
%equality with a wildcard, and the arbiter quotes the line:
%
%    *typ == ATOM_TYPE_ATOM || *typ == get_meta_type(atom)
%
%[source: LeaTTa tests/semantics/types-meta/00_metatypes.metta, quoting
%hyperon-experimental@3f76dc4 lib/src/metta/types.rs:606-617]. So the check is
%"the parameter is Atom, or it equals this value's metatype", which is what the
%two clauses below are. The tutorial line calling Atom "a supertype for Symbol,
%Expression, Variable, Grounded" is recorded there as tutorial prose that
%"records intent only", and taking it literally would have routed metatypes
%through add_super_types, where they do not belong: no widening happens and
%nothing declares an edge [tested: metta_metatype_parameters]. Issue #611 is
%the developers' own phrasing of the same thing, "Atom is the metatype that is
%the sum of Symbol, Variable, Grounded and Expression".
%
%This is consulted only after the declared types have failed, so a value with a
%matching declaration answers exactly as it did, and a program using none of
%these names never reaches it.
satisfies_metatype(_, 'Atom') :- !.
satisfies_metatype(X, Metatype) :-
    metatype_name(Metatype),
    'get-metatype'(X, Metatype).

metatype_name('Symbol').
metatype_name('Variable').
metatype_name('Grounded').
metatype_name('Expression').

%%%% Walking a compiled body for the effects a cache would hide %%%%
%
%One walk, shared by everything that may hand back a CACHED answer later.
%Tabling and memoization both do, and both were written with their own idea of
%what is safe: tabling's followed calls and treated everything it did not
%recognise as inert, and memoization's had nothing at all beyond a deny-list of
%names a library could mark volatile. The same body was sound for one and
%unsound for the other with no way to compare the two judgements.
%
%What it answers is the SPACE READS reachable from a root, as read/3 terms, and
%what it refuses is any goal not known pure. The reads are reported rather than
%interpreted, because interpreting them is exactly where the two callers
%differ: tabling resolves each to a storage predicate and invalidates the table
%when that predicate changes, and memoization has no such machinery, so a read
%it cannot invalidate on is a refusal there and ordinary work here.
%
%[source: ai-metta-python-seams.md item 1, which measured the fail-open default
%accepting seven impure categories and caching four of them wrongly].
metta_effect_walk(Module, Roots, Reads) :-
    metta_effect_walk_(Module, Roots, [], [], Raw),
    sort(Raw, Reads).

metta_effect_walk_(_, [], _, Reads, Reads).
metta_effect_walk_(Module, [PI|Rest], Seen, Reads0, Reads) :-
    memberchk(PI, Seen), !,
    metta_effect_walk_(Module, Rest, Seen, Reads0, Reads).
metta_effect_walk_(Module, [Name/Arity|Rest], Seen, Reads0, Reads) :-
    functor(Head, Name, Arity),
    findall(Body, catch(clause(Module:Head, Body), _, fail), Bodies),
    foldl(metta_effect_body(Module), Bodies, Rest-Reads0, Next-Reads1),
    metta_effect_walk_(Module, Next, [Name/Arity|Seen], Reads1, Reads).

metta_effect_body(Module, Body, Queue0-Reads0, Queue-Reads) :-
    findall(Goal, metta_effect_goal(Body, Goal), Goals),
    foldl(metta_effect_classify(Module), Goals, Queue0-Reads0, Queue-Reads).

%The goals of a compiled body, conjunctions and control constructs opened. A
%construct NOT opened here is judged as one goal, which under a refusing
%default means refused: catch/3 was missing and hid everything inside it.
%A control construct is inert BECAUSE its goal arguments were walked, and not
%because its name is on a list. Those are two different claims and treating
%them as one is what let `collapse` through: the walk descended wrappers only
%at arity ONE, so the findall/3 the translator emits for collapse and the
%forall/2 it emits for forall fell to the catch-all, and then a name list said
%both were inert. A body refused in the open was accepted one word inside a
%collapse, and cached a random draw
%[tested: lib_tabling_purity:an_impure_goal_is_refused_inside_every_wrapper].
%
%So the shape changed rather than the list. metta_effect_construct/2 says which
%ARGUMENTS of a construct hold goals, the walk yields those and nothing for the
%construct itself, and a construct that is not there is a leaf that gets
%refused by name. This is cut_in_clause_scope/1's closed shape, where an
%unrecognised construct cannot silently become harmless; the open shape had
%already missed catch/3 once before it missed these two.
metta_effect_goal(Body, _) :- var(Body), !, fail.
metta_effect_goal(Construct, Goal) :-
    compound(Construct),
    metta_effect_construct(Construct, Inners), !,
    member(Inner, Inners),
    metta_effect_goal(Inner, Goal).
metta_effect_goal(Goal, Goal).

%Every goal-bearing argument of each control construct a compiled body can
%contain. Written as the construct's own shape rather than as name and arity,
%so an argument that is a TEMPLATE rather than a goal cannot be walked as one:
%findall/3 holds a goal in argument two and terms in one and three.
%
%What is deliberately NOT here is as load-bearing as what is. foldall/4,
%with_mutex/2 and transaction/1 are refused today purely by being absent, and
%that stays: a refusal is loud and someone fixes it, where a wrong entry here
%is a silent wrong answer. This is the allow-list asymmetry the seam is built
%on, applied to the walk as well as to the names.
metta_effect_construct((A, B), [A, B]).
metta_effect_construct((A ; B), [A, B]).
metta_effect_construct((A -> B), [A, B]).
metta_effect_construct((A *-> B), [A, B]).
metta_effect_construct(\+ A, [A]).
metta_effect_construct(call(A), [A]).
metta_effect_construct(once(A), [A]).
metta_effect_construct(catch(A, _, Recovery), [A, Recovery]).
metta_effect_construct(findall(_, A, _), [A]).
metta_effect_construct(forall(A, B), [A, B]).
%take/2's own two forms. metta_take_match/4 is a bounded match and reports as
%the read it is, which metta_effect_classify/4 does from the shape below.
metta_effect_construct(metta_take(_, A), [A]).
%top's plain form likewise calls its goal; metta_top_match/4 is a read the
%classifier judges from its shape as it does the bounded take.
metta_effect_construct(metta_top(_, A, _), [A]).
%Anything else that CALLS one of its arguments, read from SWI's own
%meta_predicate declaration rather than from a list here. This clause is last,
%so every construct above keeps its exact handling and this catches the rest.
%
%It exists because a list of meta-predicates drifts the same way the list of
%control constructs did, and had: maplist/3 and foldl/4 are what the collection
%forms compile to, `maplist` and `foldl` are ALSO MeTTa builtins declared pure,
%and the classifier judges by NAME, so the wrapper was inert and what it called
%was never looked at. `(map-atom $l $x (random-int 1 1000000))` tabled clean
%and answered one draw twice [measured 2026-08-17], which is the collapse
%defect in two more wrappers.
%
%SWI says which argument is called and how many arguments it is called WITH:
%maplist(2,?,?) is argument one applied to two more, foldl(3,+,+,-) to three.
%Reading that covers include/3, exclude/3 and whatever a library adds next,
%none of which anyone would have listed.
metta_effect_construct(Meta, [Goal]) :-
    functor(Meta, Name, Arity),
    functor(Head, Name, Arity),
    predicate_property(Head, meta_predicate(Spec)),
    arg(Position, Spec, Extra),
    integer(Extra),
    arg(Position, Meta, Closure),
    nonvar(Closure),
    metta_effect_closure(Closure, Extra, Goal).

%A closure applied to the arguments its meta-predicate will add. The already
%bound arguments are KEPT, which is what makes the two-step case work:
%include/3 holds metta_condition_holds(lambda_3), and losing that would leave
%the walk classifying metta_condition_holds/2 and never reaching the lambda.
metta_effect_closure(Closure, Extra, Goal) :-
    (   atom(Closure)
    ->  Name = Closure, Bound = []
    ;   compound(Closure), Closure =.. [Name|Bound]
    ),
    length(Added, Extra),
    append(Bound, Added, Args),
    Goal =.. [Name|Args].

%A space read is REPORTED; a call to another MeTTa function is followed; a
%known-pure operation is inert; anything else is refused.
metta_effect_classify(_, Goal, Queue-Reads, Queue-Reads) :-
    var(Goal), !.
metta_effect_classify(_, match(Space, Pattern, _, _), Queue-Reads0,
                      Queue-[read(match, Space, Pattern)|Reads0]) :- !.
metta_effect_classify(_, 'get-atoms'(Space, Pattern), Queue-Reads0,
                      Queue-[read('get-atoms', Space, Pattern)|Reads0]) :- !.
%A bridge's dispatch goal is classified under the OPERATION's name, not the
%dispatcher's. Ahead of the generic compound clause because that clause would
%read the functor and refuse petta_py_dispatch_det/3, naming an internal the
%program never wrote and advising a declaration that could not be matched.
metta_effect_classify(_, Dispatch, Queue-Reads, Next-Reads) :-
    compound(Dispatch),
    metta_effect_operation_name(Dispatch, Name, Arity), !,
    (   metta_effect_inert(Name)
    ->  Next = Queue
    ;   throw(error(metta_impure_goal(Name/Arity), none))
    ).

%reduce/3 is the engine's RUNTIME dispatcher: it takes a MeTTa term and calls
%whatever function heads it, so refusing it by its own name says nothing about
%the program. `(forall (gen $k) True)` compiles its generator and its test to
%two reduce/3 goals, and once forall/2 was descended, a wholly pure body was
%refused as `reduce/3`.
%
%The head is fixed while COMPILING for every template a source program can
%write, so the call it reaches is known here and is classified exactly as a
%direct call to it would be. A head that is a VARIABLE is a higher-order call
%whose target is decided by a value the walk cannot see, and that is refused
%under its own description rather than the dispatcher's
%[tested: lib_tabling_purity:a_pure_body_inside_a_wrapper_still_tables,
%a_higher_order_call_is_refused_as_one].
metta_effect_classify(Module, reduce(Template, _, _), Queue, Next) :- !,
    metta_effect_reduced(Module, Template, Queue, Next).


%A BUILTIN is judged by declaration and a USER function by its body, and the
%order matters twice over. A builtin's implementation is engine Prolog nobody
%can declare pure, so following it reports the wrong thing: `(py-call ...)` was
%refused as `must_be/2`, `(println! ...)` as `swrite/2` and `(get-state ...)` as
%`nb_getval/2`, each naming an internal the program never wrote. And following
%it is wasted work, because the answer was already decided by whether the name
%is on the allow-list.
metta_effect_classify(Module, Goal, Queue-Reads, Next-Reads) :-
    compound(Goal), !,
    functor(Goal, Name, Arity),
    (   builtin_fun(Name)
    ->  (   metta_effect_inert(Name)
        ->  Next = Queue
        ;   throw(error(metta_impure_goal(Name/Arity), none))
        )
    ;   fun(Name), current_predicate(Module:Name/Arity)
    ->  Next = [Name/Arity|Queue]
    ;   metta_effect_inert(Name)
    ->  Next = Queue
    ;   throw(error(metta_impure_goal(Name/Arity), none))
    ).
metta_effect_classify(_, Goal, Queue-Reads, Queue-Reads) :-
    atom(Goal), metta_effect_inert(Goal), !.
metta_effect_classify(_, Goal, _, _) :-
    functor(Goal, Name, Arity),
    throw(error(metta_impure_goal(Name/Arity), none)).

%A template that is not a call reaches nothing: a number, a string, a symbol
%and the empty list are data whatever surrounds them.
metta_effect_reduced(_, Template, Queue, Queue) :-
    ( var(Template) ; \+ Template = [_|_] ), !.
metta_effect_reduced(Module, [Head|Args], Queue, Next) :-
    length(Args, ArgCount),
    Arity is ArgCount + 1,
    (   atom(Head)
    ->  functor(Call, Head, Arity),
        metta_effect_classify(Module, Call, Queue, Next)
    ;   var(Head)
    ->  throw(error(metta_higher_order_goal(Arity), none))
    ;   %A number or a string in head position is not a call: reduce/3 reaches
        %its last case and leaves the term unevaluated, so `(1 2)` is data and
        %refusing it would refuse every list literal in a cached body.
        Next = Queue
    ).

metta_effect_inert(Name) :- metta_pure_operation(Name), !.
metta_effect_inert(Name) :- metta_effect_control(Name), !.
metta_effect_inert(Name) :- metta_effect_prolog_primitive(Name).

%Only the three that are LEAVES. Every compound control construct used to be
%here too, and that list was the second half of the collapse defect: a name on
%it was inert whether or not the walk had descended it, so adding a construct
%to the walk and forgetting the name was safe while the reverse was silently
%unsound. Now the walk is the only thing that makes a construct inert, and
%these three have no goal arguments to walk.
metta_effect_control(true).  metta_effect_control(fail).  metta_effect_control(!).

%The Prolog primitives a compiled body contains that are not MeTTa operations:
%the type tests the translator emits around a typed parameter, unification and
%arithmetic. Each inspects its arguments and does nothing else.
metta_effect_prolog_primitive(integer).  metta_effect_prolog_primitive(number).
metta_effect_prolog_primitive(float).    metta_effect_prolog_primitive(atom).
metta_effect_prolog_primitive(atomic).   metta_effect_prolog_primitive(compound).
metta_effect_prolog_primitive(string).   metta_effect_prolog_primitive(is_list).
metta_effect_prolog_primitive(var).      metta_effect_prolog_primitive(nonvar).
metta_effect_prolog_primitive(ground).   metta_effect_prolog_primitive(is).
%What `let` compiles to. Found by running every impure body through every
%wrapper rather than by reading: under `take` the occurs check precedes the
%impure goal, so the refusal fired on this and named it, which is the same
%false refusal atom_string/2 gave before it was listed. Unification with an
%occurs check inspects and binds and does nothing a cache could hide.
metta_effect_prolog_primitive(unify_with_occurs_check).
%What every computed collapse compiles to beside its findall: the Empty
%prune is a read-free list transformation, and leaving it unlisted
%refused a pure body one word inside a collapse
%[tested: a_pure_body_inside_a_wrapper_still_tables].
metta_effect_prolog_primitive(petta_prune_empty).
metta_effect_prolog_primitive('=@=').    metta_effect_prolog_primitive('\\==').
metta_effect_prolog_primitive(nth0).     metta_effect_prolog_primitive(nth1).
metta_effect_prolog_primitive(between).  metta_effect_prolog_primitive(succ).
metta_effect_prolog_primitive('=<').     metta_effect_prolog_primitive('>=').
metta_effect_prolog_primitive('=:=').    metta_effect_prolog_primitive('=\\=').
metta_effect_prolog_primitive(atom_string).   metta_effect_prolog_primitive(atom_number).
metta_effect_prolog_primitive(atom_codes).    metta_effect_prolog_primitive(atom_length).
metta_effect_prolog_primitive(number_codes).  metta_effect_prolog_primitive(string_codes).
metta_effect_prolog_primitive(string_concat).  metta_effect_prolog_primitive(sub_atom).
metta_effect_prolog_primitive(functor).        metta_effect_prolog_primitive(arg).
metta_effect_prolog_primitive(compound_name_arguments).
metta_effect_prolog_primitive(compound_name_arity).

:- multifile prolog:error_message//1.
%The higher-order case, which no declaration can answer: nothing names the
%function, so there is nothing to declare pure. Saying so is the difference
%between an author declaring the right thing and an author declaring
%reduce/3 and watching nothing change.
prolog:error_message(metta_higher_order_goal(Arity)) -->
    [ 'caching refuses a call of arity ~w whose function is a value rather \c
       than a name. Which function it reaches is decided while the program \c
       RUNS, so no declaration can say whether a cached answer would hide \c
       anything. Name the function, or do not cache this one'-[Arity] ].

prolog:error_message(metta_impure_goal(Name/Arity)) -->
    [ 'caching refuses ~w/~w: nothing declares it pure, and a cached answer \c
       would hide whatever it does. Declare it with metta_pure_operation/1 if \c
       it only inspects its arguments, or do not cache this function'
      -[Name, Arity] ].

%%%% Which operations a cache may hide %%%%
%
%The engine's own answer to metta_pure_operation/1: an operation with no effect
%a cached result could hide. Anything that reads or writes a space, reads or
%writes state, prints, draws at random, reads the clock, crosses to a host, or
%evaluates something else is ABSENT, and absence is a refusal rather than a
%default.
%
%The list is deliberately shorter than "everything that looks harmless". A name
%missing here produces a loud refusal that someone adds a line for; a name
%wrongly present produces a silent wrong answer, which is what the fail-open
%default it replaces was producing.
:- multifile metta_pure_operation/1.
:- dynamic metta_host_pure_operation/1.

%A HOST's own declarations, at run time. It was multifile only, so a library
%file could add a name when it loaded and a running process could add none at
%all: register_op(len, name="size") gave an operation nothing could ever
%declare pure, and the refusal's advice, "declare it with
%metta_pure_operation/1", was unreachable by any route.
%
%It is a SEPARATE predicate rather than more clauses of this one, and that is
%not tidiness. The five clauses below are RULES with a variable head, so
%retractall(metta_pure_operation(foo)), which is how a registration withdraws
%one declaration, unifies with every one of them: five clauses to zero and
%metta_pure_operation('+') true to false, from registering any operation at
%all [measured 2026-08-17]. Retracting from here cannot reach them.
metta_pure_operation(Name) :- metta_host_pure_operation(Name).

%The same claim made from INSIDE MeTTa: (effect Name immutable) added to
%&petta is what register_op(pure=True) asserts from Python, read from the
%space's own storage at judgement time. The walk runs when a cache is
%declared, never on the call path, so consulting storage here costs nothing
%per call and installs no atom hook, which is what keeps every space's bulk
%add path fast.
metta_pure_operation(Name) :-
    atom(Name),
    petta_contract_fact([effect, Name, immutable]).

%One contract atom, read from &petta's native storage. A space atom
%[H|Args] is stored as Space(H, Args...) in the space's storage module, the
%resolution the tabling walk documents; a space that has never been written
%has no storage module yet, and that absence reads as "not declared".
petta_contract_fact(Args) :-
    native_storage_module('&petta', Module),
    Goal =.. ['&petta'|Args],
    catch(call(Module:Goal), error(existence_error(procedure, _), _), fail).

%The deliberate override: (cache Name unchecked) in &petta says the CALLER
%accepts stale answers for this function. lib_tabling and lib_memo consult
%it before their purity walk; a library's explicit volatile declaration
%still refuses, because the author's NO outranks the caller's insistence.
metta_cache_unchecked(Name) :-
    petta_contract_fact([cache, Name, unchecked]).

%(annotations Ctx Semiring) declares the semiring a context's answer
%annotations live in; silence is bool, the default at which everything
%vanishes. A context is ordered when its declared semiring carries an
%order, which is what (top k ...) needs; bool, bag and set do not.
petta_annotations(Ctx, Semiring) :-
    findall(Declared, petta_contract_fact([annotations, Ctx, Declared]),
            Declarations),
    sort(Declarations, Distinct),
    (   Distinct == []
    ->  Semiring = bool
    ;   Distinct = [Semiring]
    ->  true
    ;   Distinct = [First, Second|_],
        throw(error(petta_contract_conflict(Ctx, [annotations, Ctx, First],
                                            [annotations, Ctx, Second],
                                            [annotations, Ctx, Semiring]),
                    none))
    ).

petta_annotations_ordered(Ctx) :-
    petta_annotations(Ctx, Semiring),
    memberchk(Semiring, [ranked, prob]).

%(source Ctx Kind) declares a context's consumption discipline: repeated
%(the default, re-enumerable), linear (consume once; a second physical
%touch is a loud error, not a silent empty answer), and peek (reads do
%not consume, the provider's promise the conformance kit checks). The
%consumed mark is a prolog FLAG, process-global and transaction-immune,
%because a rolled-back transaction does not un-drain a generator.
petta_source(Ctx, Kind) :-
    (   petta_contract_fact([source, Ctx, Declared])
    ->  Kind = Declared
    ;   Kind = repeated
    ).

petta_source_guard(Space) :-
    \+ petta_ctx_declared(Space),
    !.
petta_source_guard(Space) :-
    (   petta_contract_storage(Module),
        Module:'&petta'(source, Space, linear)
    ->  atom_concat('$petta_consumed:', Space, Key),
        (   current_prolog_flag(Key, consumed)
        ->  throw(error(petta_source_discipline(Space, linear), none))
        ;   create_prolog_flag(Key, consumed, [keep(false)])
        )
    ;   true
    ).

petta_source_reset(Space) :-
    atom_concat('$petta_consumed:', Space, Key),
    (   current_prolog_flag(Key, _)
    ->  set_prolog_flag(Key, fresh)
    ;   true
    ).

:- multifile prolog:error_message//1.
prolog:error_message(petta_source_discipline(Ctx, linear)) -->
    [ '~w declares (source ~w linear) and this is its second \c
       consumption: the first drained it, so answering would be a silent \c
       empty set, exactly the wrong answer the declaration exists to \c
       refuse. Re-register the provider for a fresh source, or declare \c
       repeated for one that re-enumerates'-[Ctx, Ctx] ].

%The last answer's annotation, first-class: rides '$petta_answer_k'
%backtrackably, default 1, so (let $r (match &s P $r) (pair $r
%(annotation))) pairs each answer with its own k, a score under ranked
%and a source term under prov. Reading it OUTSIDE any answer reads the
%semiring's 1.
petta_annotation(K) :-
    (   catch(b_getval('$petta_answer_k', K0), _, fail)
    ->  K = K0
    ;   K = 1
    ).

%Combine two annotations along a conjunction, in the declared semiring:
%the polynomial provenance construction's product. Both 1 is the Boolean
%point and stays 1 without a write.
petta_k_times(1, K, K) :- !.
petta_k_times(K, 1, K) :- !.
petta_k_times(K1, K2, K) :-
    (   number(K1), number(K2)
    ->  K is K1 * K2
    ;   K = [times, K1, K2]
    ).

%%%% explain: the route as atoms (H3) %%%%
%
%(explain (match &s P T)) and (explain (op ...)) answer the declarations
%the seam would consult for that query, as atoms: which handles entry
%routes it and with what fidelity, whether a take bound would push,
%source, context world, annotations, emission, writes, error mode and
%merge strategy. The self-honesty law is the lane: what explain says is
%what instrumented execution then does, which answers the original
%complaint that the split was invisible.
petta_explain([match, Space, Pattern, _Template], Out) :-
    atom(Space), !,
    findall(Item, petta_explain_match_item(Space, Pattern, Item), Out).
petta_explain([Op|Args], Out) :-
    atom(Op), !,
    findall(Item, petta_explain_op_item(Op, Args, Item), Out).
petta_explain(Query, _) :-
    throw(error(type_error(explainable, Query),
                context(explain/1,
                        'explain covers (match <space> <pattern> <out>) \c
                         forms and operation calls'))).

petta_explain_match_item(Space, Pattern, [handles|Route]) :-
    (   catch(petta_handles_route(Space, Pattern, Entry, Fidelity, Det),
              _, fail)
    ->  Route = [Entry, Fidelity, Det]
    ;   Route = [none]
    ).
petta_explain_match_item(Space, Pattern, [pushes, Pushes]) :-
    (   nonvar(Space), metta_foreign_space(Space),
        catch(foreign_pushdown_class(Space, Pattern, exact), _, fail)
    ->  Pushes = 'True'
    ;   Pushes = 'False'
    ).
petta_explain_match_item(Space, _, [source, Kind]) :-
    petta_source(Space, Kind).
petta_explain_match_item(Space, _, [context, World]) :-
    petta_context_world(Space, World).
petta_explain_match_item(Space, _, [annotations, Semiring]) :-
    petta_annotations(Space, Semiring).
petta_explain_match_item(Space, _, [emits, Policy]) :-
    (   petta_emits(Space, Declared) -> Policy = Declared ; Policy = none ).
petta_explain_match_item(Space, _, [writes, Atomicity]) :-
    petta_writes(Space, Atomicity).
petta_explain_match_item(Space, Pattern, ['on-error', Mode]) :-
    (   catch(petta_on_error_mode(Space, Pattern, Declared), _, fail)
    ->  Mode = Declared
    ;   Mode = abort
    ).
petta_explain_match_item(_, Pattern, [merge, Policy]) :-
    (   catch(petta_merge_route(Pattern, Declared), _, fail)
    ->  Policy = Declared
    ;   Policy = depth
    ).

petta_explain_op_item(Op, _, [op, Op, Arity, Kind]) :-
    petta_contract_fact([op, Op, Arity, Kind]).
petta_explain_op_item(Op, _, [effect, Effect]) :-
    (   petta_contract_fact([effect, Op, Declared])
    ->  Effect = Declared
    ;   Effect = none
    ).
petta_explain_op_item(Op, _, [inverse, Inverse]) :-
    (   petta_contract_fact([inverse, Op]) -> Inverse = 'True'
    ;   Inverse = 'False' ).
petta_explain_op_item(Op, _, [annotations, Semiring]) :-
    petta_annotations(Op, Semiring).
petta_explain_op_item(Op, Args, ['on-error', Mode]) :-
    (   catch(petta_on_error_mode(Op, [Op|Args], Declared), _, fail)
    ->  Mode = Declared
    ;   Mode = abort
    ).

%(context Ctx closed-world|open-world) records what a context's absence
%means. The mechanically checkable part gates: negation as failure reads
%absence as falsity, which is sound only over a world the answerer
%actually holds whole, so a negated goal may consult a foreign context
%only when it declares closed-world. A native space IS the engine's own
%database and closed by construction; an undeclared foreign one refuses
%under negation loudly, because silently reading an open world's silence
%as falsity was the wrong answer.
petta_context_world(Ctx, World) :-
    (   petta_contract_fact([context, Ctx, Declared])
    ->  World = Declared
    ;   World = undeclared
    ).

petta_in_negation :-
    catch(b_getval('$petta_in_negation', true), _, fail).

petta_negation_world_guard(Space) :-
    (   petta_in_negation
    ->  (   petta_context_world(Space, 'closed-world')
        ->  true
        ;   throw(error(petta_negation_open_world(Space), none))
        )
    ;   true
    ).

:- multifile prolog:error_message//1.
prolog:error_message(petta_negation_open_world(Ctx)) -->
    [ 'a negated goal consulted ~w, which does not declare \c
       (context ~w closed-world). Negation as failure reads absence as \c
       falsity, and that is only sound over a world the answerer holds \c
       whole; declare closed-world if ~w is complete for what it \c
       serves'-[Ctx, Ctx, Ctx] ].

%%%% Declared bridges and admission (G5) %%%%
%
%(on Ctx Pattern Op) is an MCS bridge rule with a managed head: when an
%atom matching Pattern lands in Ctx, Op runs under the match's bindings.
%The subscribe callback is the special case this generalises. The heads
%are insert, retract and revise, and they route through the same write
%paths as direct writes, so a foreign target's capabilities and declared
%atomicity govern a bridged write exactly as a direct one. Bridges fire
%through the engine's own atom hooks, and the hook wrapper is installed
%only when petta_install_bridges/0 runs (the declaration sugar calls it),
%so an engine without bridges keeps the direct write path and its
%measured cost. A cascade is bounded: depth 32 throws naming the chain,
%because an unbounded insert loop is a bug, not a fixpoint.
petta_install_bridges :-
    (   petta_bridges_installed
    ->  true
    ;   assertz(petta_bridges_installed),
        assertz(( metta_on_atom_added(Space, Term) :-
                      petta_bridge_fire(Space, Term) )),
        enable_metta_atom_hook(added)
    ).

:- dynamic petta_bridges_installed/0.

petta_bridge_fire(Space, Term) :-
    forall(petta_contract_fact([on, Space, Pattern, Op]),
           petta_bridge_apply(Pattern, Term, Op)).

petta_bridge_apply(Pattern, Term, Op) :-
    (   Pattern = Term
    ->  petta_bridge_descend(Op)
    ;   true
    ).

petta_bridge_descend(Op) :-
    (   catch(b_getval('$petta_bridge_depth', Depth0), _, fail)
    ->  true
    ;   Depth0 = 0
    ),
    Depth is Depth0 + 1,
    (   Depth > 32
    ->  throw(error(petta_bridge_cascade(Op), none))
    ;   setup_call_cleanup(
            b_setval('$petta_bridge_depth', Depth),
            petta_bridge_op(Op),
            b_setval('$petta_bridge_depth', Depth0))
    ).

petta_bridge_op([insert, Target, Template]) :- !,
    metta_add_atom(Target, Template, _).
petta_bridge_op([retract, Target, Template]) :- !,
    metta_remove_atom(Target, Template, _).
petta_bridge_op([revise, Target, Old, New]) :- !,
    metta_remove_atom(Target, Old, _),
    metta_add_atom(Target, New, _).
petta_bridge_op(Op) :-
    throw(error(petta_bridge_unknown_op(Op), none)).

%(admits Pool Type) and (capacity Pool N): a pool is a space whose
%membership is typed by the ontology, so only atoms carrying the
%declared type enter, and whose size is bounded, an add beyond it
%refused loudly. Both are ordinary contract atoms checked BEFORE the
%write through a wrapper installed only when petta_install_admission/0
%runs, so an engine without pools keeps the direct write path.
petta_install_admission :-
    (   petta_admission_installed
    ->  true
    ;   assertz(petta_admission_installed),
        petta_engine_module(Engine),
        %The wrapper body is unqualified for the reason ext_points.pl's two
        %give: wrap_predicate/4 declares it `0` and SWI qualifies it with this
        %file's module, which is the engine's.
        (   wrap_predicate(Engine:metta_add_atom(Space, Term, _R),
                           petta_admission_guard, Wrapped,
                           ( petta_admission_check(Space, Term),
                             call(Wrapped) ))
        ->  true
        ;   throw(error(petta_atom_hook_install_failed(admission), none))
        )
    ).

:- dynamic petta_admission_installed/0.

petta_admission_check(Space, Term) :-
    forall(petta_contract_fact([admits, Space, Type]),
           %A witness, not consistency: an atom whose type nothing declares
           %is not evidence that it is one of these, and a contract that let
           %it in would admit everything a program never got round to
           %declaring.
           (   has_declared_type(Term, Type)
           ->  true
           ;   throw(error(petta_admission_refused(Space, Term, Type),
                           none))
           )),
    (   petta_contract_fact([capacity, Space, Limit])
    ->  findall(A, 'get-atoms'(Space, A), Held),
        length(Held, Count),
        (   Count < Limit
        ->  true
        ;   throw(error(petta_pool_full(Space, Limit), none))
        )
    ;   true
    ).

:- multifile prolog:error_message//1.
prolog:error_message(petta_bridge_cascade(Op)) -->
    [ 'a bridge cascade passed depth 32 at ~q: bridges firing bridges \c
       must reach a fixed point, and this chain does not'-[Op] ].
prolog:error_message(petta_bridge_unknown_op(Op)) -->
    [ 'the bridge operation ~q is not a managed head; the heads are \c
       (insert Ctx Atom), (retract Ctx Atom) and (revise Ctx Old \c
       New)'-[Op] ].
prolog:error_message(petta_admission_refused(Space, Term, Type)) -->
    [ '~w admits ~w-typed atoms and ~q does not carry that type; declare \c
       (: <atom> ~w) or widen the admission'-[Space, Type, Term, Type] ].
prolog:error_message(petta_pool_full(Space, Limit)) -->
    [ '~w declares (capacity ~w ~w) and holds that many already; this \c
       add is refused rather than silently growing the pool'-[Space,
                                                              Space,
                                                              Limit] ].

%(writes Ctx Atomicity) declares what a context's writes promise:
%transactional providers participate in the engine's transactions through
%the begin/commit/rollback hooks, best-effort is the author's declared
%acceptance of partial application, and atomic-single promises single
%writes only. Silence refuses a write inside a transaction loudly,
%because the old behaviour, a foreign write surviving a rolled-back
%transaction, was silent wrongness, not a floor worth keeping.
petta_writes(Ctx, Atomicity) :-
    (   petta_contract_fact([writes, Ctx, Declared])
    ->  Atomicity = Declared
    ;   Atomicity = undeclared
    ).

%The transaction form's runtime: SWI's transaction/1 for the engine's own
%database, with foreign participation coordinated around it. Providers
%enlist at their first write (petta_enlist_foreign/1, from
%foreign_write/3), and the registry is finished HERE: commit on success,
%rollback on failure or throw. A nested transaction runs inside the
%outer's registry, so providers see one begin and one finish per
%outermost transaction. Commit is single-coordinator: a provider whose
%commit throws leaves earlier commits standing, and the throw says so;
%two-phase commit is deliberately out of scope.
petta_transaction(Goal) :-
    term_variables(Goal, Vars),
    (   current_transaction(_)
    ->  transaction(petta_transaction_answers(Goal, Vars, Answers))
    ;   nb_setval('$petta_tx_enlisted', []),
        catch(( setup_call_cleanup(
                    b_setval('$petta_user_tx', true),
                    transaction(petta_transaction_answers(Goal, Vars, Answers)),
                    b_setval('$petta_user_tx', false))
            ->  Outcome = committed ; Outcome = failed ),
              Error,
              Outcome = threw(Error)),
        nb_getval('$petta_tx_enlisted', Enlisted),
        nb_setval('$petta_tx_enlisted', []),
        (   Outcome == committed
        ->  forall(member(Space, Enlisted), metta_foreign_commit(Space))
        ;   forall(member(Space, Enlisted),
                   catch(metta_foreign_rollback(Space), RollbackError,
                         print_message(error, RollbackError)))
        ),
        (   Outcome == committed -> true
        ;   Outcome == failed -> fail
        ;   Outcome = threw(E), throw(E)
        )
    ),
    member(Vars, Answers).

%COLLECT, COMMIT, THEN REPLAY, which is what preserving a body's answers
%costs. SWI's transaction/1 runs its goal as once/1 and cannot be made
%nondeterministic in place, so `(collapse (transaction (superpose (1 2 3))))`
%answered `(1)`: two of three answers gone and nothing said so
%[reproduced 2026-08-19]. Dropping answers is an OPACITY violation in the
%transactional-memory sense (Guerraoui and Kapalka, PPoPP 2008), since a
%reader of the transaction's result sees a state no serial execution of the
%body produces.
%
%Refusing a nondeterministic body was the other branch offered, and it is not
%implementable at a lower cost: knowing a Prolog goal is nondeterministic
%means running it to a second answer, at which point the answers are already
%in hand and refusing them throws away work already done. So the branch that
%CAN be built is the one that is also correct.
%
%The whole body runs inside the transaction, so every answer's writes commit
%or roll back together, and the replay happens after the commit, so a consumer
%that stops after the first answer cannot leave a transaction open. An
%answerless body fails the guard, which rolls the transaction back and fails
%petta_transaction/1 exactly as it did before.
%
%The cost is that the answers are materialized: a body with an unbounded
%answer set exhausts the stack here where it used to yield once. That is the
%honest price of atomicity over a whole answer set, and it raises a resource
%error rather than silently answering a prefix.
petta_transaction_answers(Goal, Vars, Answers) :-
    findall(Vars, Goal, Answers),
    Answers \== [].

%Only the USER's (transaction ...) form guards foreign writes: the
%engine's own internal transactions (a rule registration compiles inside
%one for atomic rollback of compiler state) keep their long-standing
%behaviour, which the foreign-rules suite pins. The flag is
%backtrackable and thread-local; the outermost user transaction sets it,
%a nested one runs inside it untouched.
petta_in_user_transaction :-
    catch(b_getval('$petta_user_tx', true), _, fail).

petta_enlist_foreign(Space) :-
    nb_getval('$petta_tx_enlisted', Enlisted),
    (   memberchk(Space, Enlisted)
    ->  true
    ;   metta_foreign_begin(Space),
        nb_setval('$petta_tx_enlisted', [Space|Enlisted])
    ).

:- multifile prolog:error_message//1.
prolog:error_message(petta_transaction_unsupported(Ctx, undeclared)) -->
    [ 'a transaction wrote to ~w, which declares nothing about its \c
       writes. The write cannot be rolled back with the transaction, and \c
       silently keeping it is the wrong answer this error replaces. \c
       Declare (writes ~w transactional) for a provider with \c
       begin/commit/rollback, or (writes ~w best-effort) to accept \c
       partial application deliberately'-[Ctx, Ctx, Ctx] ].
prolog:error_message(petta_transaction_unsupported(Ctx, 'atomic-single')) -->
    [ '~w declares (writes ~w atomic-single): single writes are atomic \c
       and transactions are not offered, so this transactional write is \c
       refused'-[Ctx, Ctx] ].

%(emits Ctx Policy) declares the order a context emits its own answers
%in; best-first is the promise (top k) needs before its bound may reach
%the provider, since the first k of a best-first emission ARE the k
%best. Distinct from (merge <pattern> <policy>), which is the ENGINE's
%strategy for merging answers across several contexts.
petta_emits(Ctx, Policy) :-
    petta_contract_fact([emits, Ctx, Policy]).

%%%% The handles route: declared fidelity per context and shape %%%%
%
%(handles Ctx Pattern Fidelity [Det]) atoms in &petta declare, per shape and
%instantiation, how faithful a context's own filtering is. Entries are
%patterns; a query is routed by the most specific entry that matches it,
%where (in $x) in an entry position matches only a bound argument. Two
%matching entries neither of which is more specific must agree on their
%claim, the critical-pair reading of MeTTa's own non-exclusive equations;
%disagreement is a loud conflict naming both. Consulted where the provider's
%own pushdown method used to be the only voice, and only at query time,
%never per answer.

%One entry of a shape-routed declaration head that matches Query: the
%stripped pattern and the adorned position paths feed the specificity
%comparison, and the entry as declared is what an error names, since that
%is the atom its author can find. The payload is whatever follows the
%shape in the declaration, [Fidelity, Det] for handles, [Mode] for
%on-error; one algorithm routes every per-shape declaration head.
petta_shape_entry(Head, Ctx, Query, entry(Stripped, Paths, Entry, Payload)) :-
    petta_shape_fact(Head, Ctx, Entry, Payload),
    petta_adorn_strip(Entry, Stripped, Requirements, Paths),
    subsumes_term(Stripped, Query),
    \+ \+ ( Stripped = Query,
            forall(member(Position, Requirements), nonvar(Position)) ).

petta_shape_fact(handles, Ctx, Entry, [Fidelity, Det]) :-
    (   petta_contract_fact([handles, Ctx, Entry, Fidelity, Det])
    ;   petta_contract_fact([handles, Ctx, Entry, Fidelity]), Det = none
    ).
petta_shape_fact('on-error', Ctx, Entry, [Mode]) :-
    petta_contract_fact(['on-error', Ctx, Entry, Mode]).
%(merge <pattern> <policy>) has no context: it is the ENGINE's strategy
%for merging answers across several contexts, keyed by the query shape,
%so it rides the shape route under one global key.
petta_shape_fact(merge, global, Entry, [Policy]) :-
    petta_contract_fact([merge, Entry, Policy]).

%Strip (in $x) wrappers, collecting the subterms that must arrive bound and
%the position path of each, root-to-leaf indices reversed. Requirements are
%checked against the query; paths are renaming-invariant, which is what the
%specificity order needs to compare two entries' adornments.
%The wrapper is recognised at expression POSITIONS only, by the literal atom
%in its head: the spine walk below never offers a list tail to this test.
%Offering tails was the bug this shape replaces, since a tail [X, Y] whose
%head is an entry variable unifies with the marker pattern, binds X to in,
%and mangles the entry into an open list that matches everything.
petta_adorn_strip(Term, Stripped, Requirements) :-
    petta_adorn_strip(Term, Stripped, Requirements, _).
petta_adorn_strip(Term, Stripped, Requirements, Paths) :-
    petta_adorn_strip(Term, [], Stripped, Requirements, Paths).

petta_adorn_strip(Var, _, Var, [], []) :- var(Var), !.
petta_adorn_strip(Term, Here, Inner, [Inner|Requirements], [Here|Paths]) :-
    Term = [Marker, Inner0], Marker == in, !,
    petta_adorn_strip(Inner0, Here, Inner, Requirements, Paths).
petta_adorn_strip(List, Here, Stripped, Requirements, Paths) :-
    List = [_|_], !,
    petta_adorn_strip_spine(List, 0, Here, Stripped, Requirements, Paths).
petta_adorn_strip(Atom, _, Atom, [], []).

petta_adorn_strip_spine(Var, _, _, Var, [], []) :- var(Var), !.
petta_adorn_strip_spine([], _, _, [], [], []).
petta_adorn_strip_spine([Head0|Tail0], Index, Here,
                        [Head|Tail], Requirements, Paths) :-
    petta_adorn_strip(Head0, [Index|Here], Head, HeadReqs, HeadPaths),
    Next is Index + 1,
    petta_adorn_strip_spine(Tail0, Next, Here, Tail, TailReqs, TailPaths),
    append(HeadReqs, TailReqs, Requirements),
    append(HeadPaths, TailPaths, Paths).

%The route: most specific matching entry, coherence-checked among the
%maximal ones. No entry means no claim, which is today's behaviour exactly.
petta_handles_route(Ctx, Query, Fidelity, Det) :-
    petta_handles_route(Ctx, Query, _, Fidelity, Det).

%The overwhelmingly common context has no such declarations and pays for
%this on every foreign match, so the emptiness answer must be nearly free:
%one indexed call per stored arity, against the storage module spaces.pl
%pre-creates with unknown set to fail, so a missing arity FAILS here in a
%handful of inferences instead of costing a thrown and caught existence
%error [measured 2026-08-17: the guard at 15 inferences per miss against
%137 through the catch-per-probe path]. The module name is computed once at
%load through native_storage_module/2, the single source of that mapping.
:- dynamic petta_contract_storage/1.
:- native_storage_module('&petta', Module),
   assertz(petta_contract_storage(Module)).

petta_shape_declared(handles, Ctx) :-
    petta_contract_storage(Module),
    (   Module:'&petta'(handles, Ctx, _, _)
    ->  true
    ;   Module:'&petta'(handles, Ctx, _, _, _)
    ->  true
    ).
petta_shape_declared('on-error', Ctx) :-
    petta_contract_storage(Module),
    Module:'&petta'('on-error', Ctx, _, _).
petta_shape_declared(merge, _) :-
    petta_contract_storage(Module),
    Module:'&petta'(merge, _, _).

petta_handles_route(Ctx, Query, Entry, Fidelity, Det) :-
    petta_shape_route(handles, Ctx, Query, Entry, [Fidelity, Det]).

%Route one query through one declaration head: the most specific matching
%entry, coherence-checked among the maximal ones, exactly evaluation's own
%dispatch of a call against equation heads.
petta_shape_route(Head, Ctx, Query, Entry, Payload) :-
    petta_shape_declared(Head, Ctx),
    findall(E, petta_shape_entry(Head, Ctx, Query, E), Entries),
    Entries \== [],
    petta_shape_maximal(Entries, Maximal),
    Maximal = [entry(_, _, Entry, Payload)|Rest],
    forall(member(entry(_, _, E2, P2), Rest),
           (   P2 == Payload
           ->  true
           ;   throw(error(petta_contract_conflict(Ctx, Entry, E2, Query),
                           none))
           )).

%The entries no other entry is strictly more specific than.
petta_shape_maximal(Entries, Maximal) :-
    findall(E,
            ( member(E, Entries),
              \+ ( member(Q, Entries),
                   petta_shape_stricter(Q, E) ) ),
            Maximal).

%Q strictly more specific than P: a strictly narrower pattern, or the same
%pattern up to renaming with strictly more positions required bound. The
%second clause is what makes the scan-only idiom coherent, (edge (in $a)
%$b) Refuse beside (edge $x $y) Exact: the adorned entry matches strictly
%fewer queries, so it wins the bound-subject overlap the way Mercury's
%mode-indexed determinism declarations discriminate on modes. A narrower
%pattern outranks any adornment difference, so requirements are compared
%only between renaming-equal patterns, where paths line up positionally.
petta_shape_stricter(entry(QP, _, _, _), entry(PP, _, _, _)) :-
    \+ QP =@= PP,
    subsumes_term(PP, QP),
    \+ subsumes_term(QP, PP), !.
petta_shape_stricter(entry(QP, QPaths, _, _), entry(PP, PPaths, _, _)) :-
    QP =@= PP,
    sort(QPaths, QSorted),
    sort(PPaths, PSorted),
    ord_subtract(PSorted, QSorted, []),
    QSorted \== PSorted.

%The declared error mode for one context and query shape; silence is
%abort, which is exactly today's behaviour.
petta_on_error_mode(Ctx, Query, Mode) :-
    petta_ctx_declared(Ctx),
    petta_shape_route('on-error', Ctx, Query, _, [Mode]).

%The declared cross-context merge strategy for one query shape; silence
%is depth, which is exactly today's behaviour.
petta_merge_route(Query, Policy) :-
    petta_shape_route(merge, global, Query, _, [Policy]).

%Transport failure is never any declared mode's to keep or empty: the
%backend is ABSENT rather than wrong, retrying is the caller's decision,
%and an absent backend has said nothing about the data. The Python side
%classifies at the crossing with isinstance, where subclassing is still
%visible, and re-raises under this one name.
petta_transport_failure(error(python_error('TransportFailure', _), _)).

%A kept error as the answer it becomes: MeTTa's own (Error <culprit>
%<reason>) shape, the culprit being the query pattern as asked, since the
%failed attempt's bindings were undone with the throw.
petta_error_answer(Pattern, error(python_error(Class, Message0), _),
                   ['Error', Pattern, Reason]) :-
    !,
    (   string(Message0) -> Message = Message0
    ;   petta_py_exception_message(Message0, Message)
    ),
    format(string(Reason), "~w: ~w", [Class, Message]).
petta_error_answer(Pattern, Error, ['Error', Pattern, Reason]) :-
    message_to_string(Error, Reason).

%Critical-pair coherence over a context's entries, for checking a
%declaration EAGERLY instead of on the first query that falls into an
%overlap. Knuth-Bendix's move: for every pair of entries the pair's most
%general common instance is itself routed, with the adorned positions
%marked bound so the most demanding instance is the one examined, and the
%route throws its own conflict if the pair is a disagreeing tie. An overlap
%one entry is strictly more specific over is not a conflict, which is why
%routing decides rather than a bare overlap test.
petta_handles_coherent(Ctx) :-
    findall(Pattern-Requirements,
            ( (   petta_contract_fact([handles, Ctx, Entry, _, _])
              ;   petta_contract_fact([handles, Ctx, Entry, _])
              ),
              petta_adorn_strip(Entry, Pattern, Requirements) ),
            Entries),
    forall(( append(_, [First|Rest], Entries), member(Second, Rest) ),
           petta_handles_pair_coherent(Ctx, First, Second)).

petta_handles_pair_coherent(Ctx, P1-R1, P2-R2) :-
    \+ \+ (   P1 = P2
          ->  term_variables(R1-R2, Unbound),
              maplist(=('$petta_bound'), Unbound),
              petta_handles_route(Ctx, P1, _, _)
          ;   true
          ).

:- multifile prolog:error_message//1.
prolog:error_message(petta_contract_conflict(Ctx, E1, E2, Witness)) -->
    [ 'two (handles ~w ...) entries match ~q and disagree: ~q and ~q. \c
       Make one more specific, or declare the overlap itself with its \c
       own entry'-[Ctx, Witness, E1, E2] ].
prolog:error_message(petta_refused_shape(Ctx, Pattern, Entry)) -->
    [ '~w declares (handles ... ~q Refuse) and this query is that shape: \c
       ~q. The context cannot answer it, and the declaration makes that \c
       loud here rather than a silent partial answer later'-[Ctx, Entry,
                                                             Pattern] ].

metta_pure_operation(Name) :- pure_arithmetic(Name).
metta_pure_operation(Name) :- pure_comparison(Name).
metta_pure_operation(Name) :- pure_structure(Name).
metta_pure_operation(Name) :- pure_inspection(Name).
metta_pure_operation(Name) :- pure_engine_helper(Name).

%The engine's own helpers that a compiled body calls. They inspect and raise;
%none of them writes anything a cache could hide.
pure_engine_helper(metta_arith_operands).
pure_engine_helper(throw_metta_type_error).
pure_engine_helper(rethrow_metta_operation_error).
pure_engine_helper(non_list).
pure_engine_helper(type_answers).
pure_engine_helper(satisfies_metatype).

pure_arithmetic('+').  pure_arithmetic('-').  pure_arithmetic('*').
pure_arithmetic('/').  pure_arithmetic('%').  pure_arithmetic(min).
pure_arithmetic(max).  pure_arithmetic(exp).
pure_arithmetic('abs-math').   pure_arithmetic('acos-math').
pure_arithmetic('asin-math').  pure_arithmetic('atan-math').
pure_arithmetic('ceil-math').  pure_arithmetic('cos-math').
pure_arithmetic('exp-math').   pure_arithmetic('floor-math').
pure_arithmetic('isinf-math'). pure_arithmetic('isnan-math').
pure_arithmetic('log-math').   pure_arithmetic('pow-math').
pure_arithmetic('round-math'). pure_arithmetic('sin-math').
pure_arithmetic('sqrt-math').  pure_arithmetic('tan-math').
pure_arithmetic('trunc-math').

pure_comparison('<').  pure_comparison('>').  pure_comparison('<=').
pure_comparison('>=').  pure_comparison('==').  pure_comparison('!=').
pure_comparison('=').  pure_comparison('=?').  pure_comparison('=alpha').
pure_comparison(dif).  pure_comparison(and).   pure_comparison(or).
pure_comparison(not).  pure_comparison(xor).   pure_comparison(implies).

pure_structure('car-atom').    pure_structure('cdr-atom').
pure_structure('cons-atom').   pure_structure('decons-atom').
pure_structure(cons).          pure_structure(decons).
pure_structure('size-atom').   pure_structure('index-atom').
pure_structure('sort-atom').   pure_structure('union-atom').
pure_structure('intersection-atom'). pure_structure('subtraction-atom').
pure_structure('unique-atom'). pure_structure('alpha-unique-atom').
pure_structure('map-atom').    pure_structure('filter-atom').
pure_structure('foldl-atom').  pure_structure('max-atom').
pure_structure('min-atom').    pure_structure('exclude-item').
pure_structure('first-from-pair'). pure_structure('second-from-pair').
pure_structure(first).  pure_structure(last).  pure_structure(append).
pure_structure(length). pure_structure(member). pure_structure('is-member').
pure_structure('is-alpha-member'). pure_structure(reverse).
pure_structure(sort).   pure_structure(msort).  pure_structure(list_to_set).
pure_structure(foldl).  pure_structure(maplist). pure_structure(superpose).
pure_structure(empty).  pure_structure(id).      pure_structure(noeval).
pure_structure(copy_term). pure_structure(term_hash).

pure_inspection('get-type').     pure_inspection('get-metatype').
pure_inspection('is-var').       pure_inspection('is-ground').
pure_inspection('is-expr').      pure_inspection('is-space').
pure_inspection(repr).           pure_inspection(repra).
pure_inspection(parse).          pure_inspection(sread).
pure_inspection(atom_chars).     pure_inspection(atom_concat).
pure_inspection(has_type).       pure_inspection(metatype_of).

'is-var'(A,R) :- var(A) -> R=true ; R=false.
'is-ground'(A,R) :- ground(A) -> R=true ; R=false.
'is-expr'(A,R) :- is_list(A) -> R=true ; R=false.
'is-space'(A,R) :- atom(A), atom_concat('&', _, A) -> R=true ; R=false.

%%% Diagnostics / Testing: %%%
:- multifile prolog:error_message//1.
:- multifile prolog:message//1.

prolog:error_message(petta_test_failed(Actual, Expected)) -->
    [ 'MeTTa test failed: ~p does not match ~p'-[Actual, Expected] ].
prolog:error_message(petta_assertion_failed(Goal)) -->
    [ 'MeTTa assertion failed: ~p'-[Goal] ].
prolog:error_message(petta_test_no_answer) -->
    [ 'MeTTa test expression produced no answer'-[] ].

%The three formals above are the program saying something FALSE, which is a
%different event from the engine breaking, and a harness has to be able to
%tell them apart without reading the sentence. This is the classifier that
%lets it: Form is the MeTTa operation that failed, Actual what it got and
%Expected what it wanted, both unbound where the form carries no such value.
%
%It lives beside the throwers rather than in the Python shim because the
%formals are the ENGINE's, so the two cannot drift: adding a fourth
%assertion form and forgetting this predicate leaves that form unclassified
%here, where it is read, rather than in a file the engine never loads
%[tested: python/tests/test_assertion_failures.py].
%
%Actual and Expected are handed out as WRITTEN MeTTa terms; a caller that
%has to cross them to another language converts them itself, because the
%conversion belongs to that boundary and not to the engine.
petta_assertion_failure(error(petta_test_failed(Actual, Expected), _),
                        test, Actual, Expected).
petta_assertion_failure(error(petta_test_no_answer, _), test, _, _).
petta_assertion_failure(error(petta_assertion_failed(Goal), _), assert, Goal, _).

prolog:error_message(petta_not_a_prolog_module(File)) -->
    [ '~w is not a Prolog module, so its exports cannot be imported under \c
       other names. Add :- module(name, [pred/arity, ...]) at its top, or \c
       register it without renaming.'-[File] ].
prolog:error_message(petta_not_exported(Module, Name, Exports)) -->
    [ '~w does not export ~w, so it cannot be imported under another name. \c
       It exports ~q.'-[Module, Name, Exports] ].
%The two names a Prolog registration cannot take, thrown by
%refuse_reserved_registration/1 below and rendered here so every
%prolog:error_message//1 clause in this file stays together.
prolog:error_message(permission_error(register, metta_builtin, Name)) -->
    [ '~w is a builtin, so registering a Prolog predicate under that name \c
       would replace the engine\'s own for every space in the process. A \c
       named space compiles its own clauses, so an equation there shadows \c
       the builtin for that space alone.'-[Name] ].
prolog:error_message(permission_error(register, metta_special_form, Name)) -->
    [ '~w is a special form, which the translator compiles directly, so a \c
       registration under that name could never be reached. Pick another \c
       name, or reach the predicate with (call (~w ...)), which needs no \c
       registration.'-[Name, Name] ].
prolog:error_message(petta_extension_api_mismatch(Name, Wanted, Ours)) -->
    [ '~w was written against extension seam ~w and this engine offers ~w. \c
       A major version differs, or the extension needs a hook this engine \c
       does not have yet.'-[Name, Wanted, Ours] ].
%Thrown by refuse_untypable_declaration/3 above. The type is written back
%through swrite/2 so the author sees the MeTTa they wrote rather than its
%Prolog list.
prolog:error_message(petta_untypable_declaration(Name, Type)) -->
    { swrite(Type, Written) },
    [ '(: ~w ~w) is not an arrow, so it types the symbol ~w and not a call \c
       to it: every (~w ...) compiles with no check at all, and a wrong \c
       argument surfaces wherever it finally breaks instead of here. Write \c
       (: ~w (-> ...)), or (: ~w %Undefined%) to say ~w is deliberately \c
       untyped.'-[Name, Written, Name, Name, Name, Name, Name] ].
prolog:error_message(petta_export_form(Text)) -->
    [ 'this is not an export declaration: ~w. An export is (: name (-> ...)) \c
       or (export name arity).'-[Text] ].
prolog:error_message(petta_load_failed(Summary)) -->
    [ 'the Prolog source did not load cleanly: ~w'-[Summary] ].
prolog:error_message(petta_name_owned_by_source(Name, Owner)) -->
    [ '~w is already registered from ~w. Two libraries defining one name \c
       destroy each other\'s predicate, because a consulted file REPLACES a \c
       static one of the same name and SWI only warns. Rename yours, or \c
       unregister the extension that owns it first.'-[Name, Owner] ].
prolog:error_message(permission_error(register, metta_function, Name)) -->
    [ '~w is already registered by another extension tier. Unregister it \c
       there first, or pick another name: two tiers sharing one name leaves \c
       whichever registered second in place and the other one\'s registry \c
       still claiming it.'-[Name] ].

%The value laid out for reading: (pretty-atom $x) answers the multi-line
%string swrite_pretty produces, so (println! (pretty-atom $big)) is the
%readable dump. Data in, data out; the printing stays println!'s job.
'pretty-atom'(Term, String) :- swrite_pretty(Term, String).

'println!'(Arg, Unit) :- swrite(Arg, RArg),
                        format('~w~n', [RArg]),
                        Unit = [].

%One line, one form. A form spanning two lines is a syntax error here, which
%is why 'read-form!'/1 exists beside it.
'readln!'(Out) :- read_line_to_string(user_input, Str),
                  sread(Str, Out).

%A whole form, however many lines it takes. Reads until the brackets balance,
%so a console accepts (= (f $x)<enter>(+ $x 1)) the way every other language's
%does, and an empty line re-prompts instead of erroring.
%
%This is CPython's InteractiveConsole half: the buffering and prompting sit
%here, and the decision, sread_command/2, is in the reader with no I/O at all,
%so a Jupyter kernel or an editor integration uses the same answer without
%this loop [source: CPython, the code module's split between
%InteractiveInterpreter and InteractiveConsole]
%[tested: parser_reads_a_form_across_lines].
'read-form!'(Out) :- read_form_lines("", Out).

%The decision on its own, with no I/O: (complete Term), incomplete, or a
%raise. A console that does its own reading asks this and keeps its own
%buffer.
%
%sread_command/2 answers the Prolog compound complete(Term), which is the
%right shape for a Prolog caller and the wrong one for a MeTTa program: it
%would arrive as an opaque term rather than as an expression to match on.
'sread-command'(Text, _) :- var(Text), !, refuse_unbound_input('sread-command', 1).
'sread-command'(Text, Result) :-
    sread_command(Text, Answer),
    ( Answer = complete(Term) -> Result = [complete, Term] ; Result = Answer ).

read_form_lines(Buffered, Out) :-
    read_line_to_string(user_input, Line),
    (   Line == end_of_file
    ->  ( Buffered == "" -> Out = end_of_file ; sread(Buffered, Out) )
    ;   ( Buffered == "" -> Text = Line
        ; string_concat(Buffered, "\n", WithBreak),
          string_concat(WithBreak, Line, Text) ),
        sread_command(Text, Result),
        ( Result = complete(Term) -> Out = Term
        ; read_form_lines(Text, Out) )
    ).

test(A,B,true) :- (A =@= B -> E = '✅' ; E = '❌'),
                  swrite(A, RA),
                  swrite(B, RB),
                  format("is ~w, should ~w. ~w ~n", [RA, RB, E]),
                  ( A =@= B -> true
                  ; throw(error(petta_test_failed(A, B),
                                context(test/3, 'MeTTa test values differ'))) ).

test_answer_value([], _) :-
    throw(error(petta_test_no_answer,
                context(test/3, 'expected a value but expression produced no answer'))).
test_answer_value([Actual], Actual) :- !.
test_answer_value(Results, Results).

'test-no-answer'(Results, Out) :-
    test(Results, [], Out).

%Resolved in the calling space's module for the same reason callPredicate/2 is:
%the goal may name a function the space itself defines, and those clauses are
%in that module and nowhere else.
assert(Goal, true) :- current_metta_module(Module),
                      ( call(Module:Goal) -> true
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

%get-type, run with the SELECTED space as the context: upstream's
%get-type-space (pinned stdlib.md:849-868). The library stub this
%replaces matched the literal &self and answered nothing for any named
%space; the engine's type machinery is module-parameterized already, so
%selection is one with_metta_module/2 around the ordinary get-type.
'get-type-space'(Space, _, _) :- var(Space), !,
                                 refuse_unbound_input('get-type-space', 1).
'get-type-space'(Space, X, T) :- space_module(Space, Module),
                                 with_metta_module(Module, 'get-type'(X, T)).

%%% Documentation, HE's vocabulary, first class %%%
%
%The design stays lib_doc's, which was already the right one:
%documentation is ATOMS IN A SPACE, (@doc name (@desc ...) ...) is data
%a program writes and can reason about, and retrieval is a match. What
%promotion adds is reach and a second tier: these are builtins now, no
%import, they resolve against the CURRENT context rather than literal
%&self, each has a -space twin selecting any space, and get-doc falls
%back to the engine's own register, where the prelude documents its
%vocabulary, so help! answers for engine forms too.
%
%The tier split is deliberate and asymmetric. RESOLVERS (get-doc,
%help!) consult the register, because "what does this name mean" wants
%an answer wherever the name comes from. ENUMERATORS (documented,
%defined-name, undocumented) are program-scoped and skip builtins,
%because "what have I documented" and "what did I forget" are questions
%about the program, and an engine that padded the answer with its own
%vocabulary would bury the user's gap under noise.
%
%The register branch comes FIRST in get-doc for the same determinism
%reason type_declaration_in orders its tiers: a first-arg-indexed miss
%is fast for ordinary names, and the disjunction is exhausted when
%match/4 ends, so raw first-solution callers keep match's own
%choicepoint profile.
:- dynamic prelude_doc_atom/2.

'get-doc'(Name, Doc) :- current_metta_space(Space),
                        'get-doc-space'(Space, Name, Doc).

%One shape per arity rather than one open-tailed pattern, the library's
%own load-bearing craft: @doc carries two, three or four parts depending
%on how much was written, and the engine's matcher walks proper lists,
%so an open tail matches nothing at all.
doc_shape(Name, ['@doc', Name, _]).
doc_shape(Name, ['@doc', Name, _, _]).
doc_shape(Name, ['@doc', Name, _, _, _]).

'get-doc-space'(Space, Name, Doc) :-
    doc_shape(Name, Doc),
    (   prelude_doc_atom(Name, Doc)
    ;   match(Space, Doc, Doc, _)
    ).

'help!'(Name, []) :-
    (   \+ 'get-doc'(Name, _)
    ->  swrite(Name, S),
        format("No documentation for ~w~n", [S])
    ;   forall('get-doc'(Name, Doc),
               ( swrite(Doc, DS), format("~w~n", [DS]) ))
    ).

documented(Name) :- current_metta_space(Space),
                    'documented-space'(Space, Name).

'documented-space'(Space, Name) :- doc_shape(Name, Doc),
                                   match(Space, Doc, Name, _).

%The library's exact semantics: every head of an equation THE SPACE
%HOLDS, once each. Enumerating the space's own atoms is what excludes
%builtins, engine-generated lambdas, and registered operations without
%any filter list: none of them stores an equation atom here.
'defined-name'(Name) :- current_metta_space(Space),
                        distinct(Name,
                                 ( get_native_atom(Space, [=, [Name|_], _]),
                                   atom(Name) )).

undocumented(Name) :- current_metta_space(Space),
                      'undocumented-space'(Space, Name).

'undocumented-space'(Space, Name) :-
    distinct(Name,
             ( get_native_atom(Space, [=, [Name|_], _]),
               atom(Name) )),
    \+ 'get-doc-space'(Space, Name, _).

%%% Time Retrieval: %%%
'current-time'(Time) :- get_time(Time).
'format-time'(Format, _) :- var(Format), !, refuse_unbound_input('format-time', 1).
'format-time'(Format, TimeString) :- get_time(Time), format_time(atom(TimeString), Format, Time).

%%% Filesystem tests: %%%
%
%SWI's exists_file/1 is a TEST, and the engine reads a registered predicate's
%LAST argument as the output, so registering the name bare made its only
%argument the answer slot: a path could never be passed in, and
%(exists_file "run.sh") raised function_input_arities(exists_file,[0]) while
%(exists_file) alone raised "Arguments are not sufficiently instantiated". A
%declared type for it, (-> %Undefined% Bool), said it took a path all the same.
%
%That silence is already on the record from the other side. lib_import.metta
%notes removing a former guard because "It made a missing file fail SILENTLY,
%with no answer", which is exactly what a zero-input registration does: the
%call site went and the registration stayed.
%
%The wrapper is sleep/2's shape below, and it answers false rather than
%FAILING, because a test that fails is indistinguishable from a test that was
%never reached, which is what made the original symptom so hard to read
%[tested: builtin_exists_file].
'exists_file'(Path, Result) :-
    (   ( atom(Path) ; string(Path) )
    ->  ( exists_file(Path) -> Result = true ; Result = false )
    ;   throw_metta_type_error(exists_file, 'a path as a symbol or string', Path)
    ).

%%% Time control: %%%
%Suspend this evaluation. In a thread, only this thread waits.
'sleep'(Seconds, true) :- must_be(number, Seconds), sleep(Seconds).

%Bound a goal by wall clock, keeping every answer.
%
%call_with_time_limit/2 runs its goal as once/1, so wrapping the goal directly
%would collapse a three-answer expression to one, the trap with_mutex/2 sets.
%The findall INSIDE the limit is what avoids that: the whole enumeration is
%bounded as one unit and member/2 hands the answers back.
%
%Do not be tempted to replace this with a raw alarm/4 around the goal to get
%lazy answers. It crashes: alarm/4 with throw/1 around a deeply recursive goal
%took SIGSEGV where call_with_time_limit/2 on the identical goal unwound
%cleanly [measured 2026-08-15, ai-tmp/pool/alarm.pl]. The cost of doing this
%safely is that answers are collected before the first is yielded, which for a
%deadline-bounded call is what you want anyway.
%
%A wall-clock bound is also the only one that survives concurrency. The
%inference limit counts the calling thread only, so it does not stop work a
%hyperpose branch or a spawned future is doing [measured 2026-08-15: a 50,000
%inference limit did not stop two branches spending six million].
%
%Expiry throws rather than failing, so a partial answer set is never mistaken
%for the whole one. time_limit_exceeded is already a control exception here.
:- meta_predicate metta_timeout(+, 0, ?),
                  metta_inferences(+, 0, ?),
                  metta_elapsed(0, ?, ?),
                  metta_with_pragmas(+, 0, ?),
                  petta_transaction(0).
%Why these seven: a runnable's goals run as call(Module:G), so a goal a
%special form passes to a HELPER used to lose the module on the way in,
%and the helper's findall called it back in user: every one of these
%forms was silently unusable in a named space, which is every space the
%Python surface creates ("Unknown procedure" for a function the space
%plainly defines). meta_predicate makes the call site wrap the goal
%argument as Module:Goal, the manual's own maplist example. metta_take/2
%and metta_top/3 take the same declaration beside their own clauses in
%spaces.pl, because a meta_predicate directive above a predicate defined
%in another file warns that it has no clauses. Baking the
%qualification at translate time was measured as the alternative and
%costs MORE where wrapper forms are retranslated per run
%(annotated-relation +2498 baked against +996 wrapped, over 500
%named-space evaluations); the wrap is free in user because an
%already-plain goal in a user-context call needs no module hop
%[source: SWI-Prolog 10.1 manual, ch. 6 defining a meta-predicate;
%measured 2026-08-18; tested spaces:wrapper_forms_run_in_named_spaces].

metta_timeout(Seconds, Goal, Value) :-
    must_be(number, Seconds),
    call_with_time_limit(Seconds, findall(Value, Goal, Values)),
    member(Value, Values).

%timeout's deterministic twin, the kwarg vocabulary at the language tier:
%(inferences N Expr) bounds Expr by engine steps, the same limit
%m.run(inferences=) applies one level up, so a program bounds its own
%subexpression and the bound stops at the same step on every machine.
%The whole answer set is computed under the bound, timeout's own rule, so
%a partial set is never mistaken for the whole one; expiry throws the
%reserved resource envelope the Python tier already classifies.
metta_inferences(Limit, Goal, Value) :-
    must_be(positive_integer, Limit),
    call_with_inference_limit(findall(Value, Goal, Values), Limit, Result),
    (   Result == inference_limit_exceeded
    ->  throw(error(petta_py_exception(inference_limit, Limit),
                    context(petta, inference_limit)))
    ;   true
    ),
    member(Value, Values).

%Time one answer and report what it cost, as (Value Seconds). Each answer is
%timed from the start of the call, so backtracking into a later answer reports
%the total spent reaching it rather than restarting the clock.
metta_elapsed(Goal, Value, [Value, Seconds]) :-
    get_time(Start),
    Goal,
    get_time(End),
    Seconds is End - Start.

%%% Interpreter pragmas: %%%
%MeTTa HE spells interpreter settings (pragma! <key> <value>). PeTTa had none,
%so this is the fallback-to-HE rule applied.
:- dynamic metta_pragma/2.

%An unrecognised key is a typo far more often than it is forward
%compatibility, so it is an error that names the keys that exist rather than a
%setting that silently never applies.
%HE's own keys are type-check, interpreter and max-stack-depth
%[source 2026-08-15: MeTTa HE stdlib reference, pragma!]. The two bounds are
%PeTTa's, and are the ones this engine can actually enforce.
metta_pragma_key('max-time', 'bound every runnable by wall-clock seconds').
metta_pragma_key('max-inferences', 'bound every runnable by inference count').
%These three are HE's. They are accepted so an HE program loads, and they are
%NOT enforced here; setting one changes nothing. Recorded rather than silently
%swallowed, and tracked in ai-todo-parallel.md B10.1.
metta_pragma_key('verify-specializations',
                 'check every specialization against the generic call once').
metta_pragma_key('max-stack-depth', 'HE spelling; accepted, NOT enforced').
metta_pragma_key('type-check', 'HE spelling; accepted, NOT enforced').
metta_pragma_key(interpreter, 'HE spelling; accepted, NOT enforced').

'pragma!'(Key, _, _) :- var(Key), !, refuse_unbound_input('pragma!', 1).
'pragma!'(Key, Value, true) :-
    (   metta_pragma_key(Key, _)
    ->  true
    ;   findall(K-D, metta_pragma_key(K, D), Known),
        throw(error(domain_error(metta_pragma_key, Key),
                    context('pragma!'/2, Known)))
    ),
    retractall(metta_pragma(Key, _)),
    (   Value == none
    ->  true
    ;   assertz(metta_pragma(Key, Value))
    ),
    sync_metta_pragma_bounds.

%pragma! scoped to one expression, MeTTaLog's with-pragma! adopted:
%each (key value) pair validates exactly as pragma! validates it, the
%previous values come back on every exit path, reversed so a key set
%twice in one scope restores its true pre-scope value, and the whole
%answer set is computed under the scope, timeout's own rule, so a later
%answer cannot escape it.
metta_with_pragmas(Settings, Goal, Value) :-
    must_be(list, Settings),
    maplist(petta_pragma_pair, Settings, Pairs),
    setup_call_cleanup(
        maplist(petta_apply_pragma, Pairs, Restores),
        %The global bounds wrap call_goals_in, one level above this body,
        %so the scope applies them itself: whatever bounds are in force
        %here, scoped ones included, bound this findall.
        run_under_pragmas(findall(Value, Goal, Values)),
        ( reverse(Restores, Undo),
          maplist(petta_restore_pragma, Undo) )),
    member(Value, Values).

petta_pragma_pair([Key, ValueIn], Key-ValueIn) :- !.
petta_pragma_pair(Other, _) :-
    throw(error(domain_error(metta_pragma_setting, Other),
                context('with-pragma!'/2,
                        'each setting is a (key value) pair'))).

petta_apply_pragma(Key-Value, Key-Previous) :-
    ( metta_pragma(Key, P) -> Previous = P ; Previous = none ),
    'pragma!'(Key, Value, _).

petta_restore_pragma(Key-Previous) :-
    'pragma!'(Key, Previous, _).

%A bound costs nothing until one is set. call_goals_in/2 runs every runnable
%form, so an unconditional wrapper there is paid by every directive: checking
%two pragmas on each one cost 5 inferences per directive against the
%run-source benchmark's 4-inference allowance [measured 2026-08-15]. Wrapping
%the predicate only while a bound is active is how ext_points.pl keeps atom
%hooks free when nobody is listening, and the same reasoning applies here.
sync_metta_pragma_bounds :-
    (   bounding_pragma_set
    ->  enable_metta_pragma_bounds
    ;   disable_metta_pragma_bounds
    ).

bounding_pragma_set :-
    (   metta_pragma('max-time', Seconds), number(Seconds), Seconds > 0
    ->  true
    ;   metta_pragma('max-inferences', Limit), integer(Limit), Limit > 0
    ).

enable_metta_pragma_bounds :-
    petta_engine_module(Engine),
    current_predicate_wrapper(Engine:call_goals_in(_, _), metta_pragma_bounds,
                              _, _), !.
enable_metta_pragma_bounds :-
    petta_engine_module(Engine),
    wrap_predicate(Engine:call_goals_in(_Module, _Goals), metta_pragma_bounds,
                   Wrapped, Engine:run_under_pragmas(Wrapped)).

disable_metta_pragma_bounds :-
    petta_engine_module(Engine),
    ( unwrap_predicate(Engine:call_goals_in/2, metta_pragma_bounds)
      -> true ; true ).

%What a bounded runnable form is wrapped in. Reading the pragmas here, rather
%than baking them into the compiled clause, means a pragma set later applies
%to everything after it and nothing before it.
%Expiry throws the RESERVED limit envelopes, the exact shapes
%petta_py_limited throws, so a pragma bound and a per-call kwarg bound
%classify identically one level up: TimeLimitError and
%InferenceLimitError rather than a generic engine error.
run_under_pragmas(Goal) :-
    (   metta_pragma('max-time', Seconds), number(Seconds), Seconds > 0
    ->  Timed = catch(call_with_time_limit(Seconds, Goal),
                      time_limit_exceeded,
                      throw(error(petta_py_exception(time_limit, Seconds),
                                  context(petta, time_limit))))
    ;   Timed = Goal
    ),
    (   metta_pragma('max-inferences', Limit), integer(Limit), Limit > 0
    ->  call_with_inference_limit(Timed, Limit, Result),
        (   Result == inference_limit_exceeded
        ->  throw(error(petta_py_exception(inference_limit, Limit),
                        context(petta, inference_limit)))
        ;   true
        )
    ;   call(Timed)
    ).

%%% MeTTa HE compatibility: %%%
%HE's metta/3 is (-> Atom Type SpaceType Atom), "run the MeTTa interpreter on
%an atom" in a named space. evalc/3 already is exactly that: PeTTa's eval is a
%full evaluation rather than minimal MeTTa's single rewriting step, which its
%own comment records, so this is the HE spelling over it. The Type argument is
%accepted and ignored, as it is for %Undefined% in HE.
'metta'(Atom, _Type, Space, Out) :- evalc(Atom, Space, Out).

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
%Every one of those is fixed in src/python.pl, which is the language's own
%surface rather than this one: `py-atom` RESOLVES where this APPLIES, and that
%split is what makes a Python callable a value. Reach for that. Changing this
%operator's defaults was tried and measured and it works, and it changes what
%every program written against upstream sees, so it stays as upstream has it.
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

%A FRESH SPACE, which PeTTa did not have. Spaces here are named and created on
%demand, so `(new-space)` reduced to nothing and `(bind! &s (new-space))` did
%nothing at all: the program worked anyway because `&s` doubles as a name, and
%that is an accident rather than a design. It answers a fresh unique name, so
%the form means what it says and bind! has something to bind.
:- dynamic petta_space_counter/1.

'new-space'(Space) :- gensym('&petta-space-', Space).

%%% States: %%%
'bind!'(Var, _, _) :- var(Var), !, refuse_unbound_input('bind!', 1).
'bind!'(Var, ['new-state', Value], []) :- !,
    ( atom(Var) -> nb_setval(Var, Value)
    ; catch(nb_setval(Var, Value), E,
            rethrow_metta_operation_error('bind!', E)) ).
%THE TOKEN FORM, which is what the specification says bind! is:
%"(-> Symbol %Undefined% (->)) ... Registers a new token which is replaced with
%an atom during the parsing of the rest of the program"
%[source: metta-lang-docs/corelib-stdlib-reference.md, bind!]. PeTTa had only
%the state-cell form above, so `(bind! six 6)` FAILED SILENTLY and the language's
%own idiom `(bind! abs (py-atom numpy.absolute))` then `(abs -5)` could not work.
%
%The state form keeps its own clause and registers no token, because PeTTa
%models a state cell by NAME: substituting the name away would take `get-state`
%with it.
'bind!'(Var, Value, []) :-
    ( atom(Var)
      -> true
      ;  throw(error(type_error(symbol, Var),
                     context('bind!'/2, 'a token name is a symbol'))) ),
    %"Atom, which is associated with the token AFTER REDUCTION", so the value is
    %evaluated before it is bound: `(bind! &s (new-space))` binds the space, not
    %the expression that makes one.
    ( is_list(Value) , Value \== []
      -> once(reduce(Value, Reduced, _))
      ;  Reduced = Value ),
    register_metta_token(Var, Reduced).

%A token, and the substitution that makes it one. Both are guarded on anything
%being registered at all, so a program that binds no token pays one indexed
%lookup per form it parses and nothing else.
:- dynamic metta_token/2.

register_metta_token(Name, Value) :-
    retractall(metta_token(Name, _)),
    assertz(metta_token(Name, Value)).

%ONE indexed lookup when no token is bound, which is what a token table costs
%and all it costs. A program that binds none pays that per parsed form and
%nothing else; the walk below runs only once something is registered.
substitute_bound_tokens(Term, Out) :-
    metta_token(_, _), !,
    substitute_bound_tokens_(Term, Out).
substitute_bound_tokens(Term, Term).

substitute_bound_tokens_(Term, Out) :- var(Term), !, Out = Term.
substitute_bound_tokens_(Term, Out) :- atom(Term), !,
                                       ( metta_token(Term, Bound)
                                         -> Out = Bound ; Out = Term ).
substitute_bound_tokens_(Term, Out) :- atomic(Term), !, Out = Term.
substitute_bound_tokens_(Term, Out) :- is_list(Term), !,
                                       maplist(substitute_bound_tokens_, Term, Out).
substitute_bound_tokens_(Term, Term).

%&self is the reserved token for the space the code lives in, upstream's
%own reading where &self is a tokenizer substitution for the running
%space. In the CLI the program space is literally named &self, so the
%walk is skipped outright there and nothing changes; a named space (a
%python-created one, or a (new-space) binding) gets its own name wherever
%its source says &self, which is what makes `!(add-atom &self ...)` and
%`(unify &self ...)` mean "this space" in library-hosted programs too.
%It substitutes where the engine's own bind! tokens substitute, the
%parsed-form rewrite, so stored data expressions keep their literal
%atoms exactly as they do for every other token.
substitute_self_('&self', Term, Term) :- !.
substitute_self_(Space, Term, Out) :-
    substitute_self_walk_(Term, Space, Out).

substitute_self_walk_(Term, Space, Out) :- atom(Term), !,
                                           ( Term == '&self'
                                             -> Out = Space ; Out = Term ).
substitute_self_walk_(Term, _, Out) :- atomic(Term), !, Out = Term.
substitute_self_walk_(Term, Space, Out) :-
    is_list(Term), !,
    substitute_self_list_(Term, Space, Out).
substitute_self_walk_(Term, _, Term).

substitute_self_list_([], _, []).
substitute_self_list_([Term|Terms], Space, [Out|Outs]) :-
    substitute_self_walk_(Term, Space, Out),
    substitute_self_list_(Terms, Space, Outs).

%Every rewrite a freshly parsed form gets before anything else reads it.
%The guards inline rather than calls to guarded predicates: each of
%those costs its own call on top of its lookup, and this runs on every
%form a source load parses. The &self walk is gated by a C substring
%probe of the form's own source text, so a form that never says &self
%pays a flat few inferences however large its data is: the unguarded
%walk cost alpha-unique's counter +12% and every runnable +10, caught by
%the gate.
rewrite_parsed_form(Space, FormStr, Term, Rewritten) :-
    (   Space == '&self'
    ->  Term1 = Term
    ;   string(FormStr)
    ->  (   sub_string(FormStr, _, _, _, "&self")
        ->  substitute_self_(Space, Term, Term1)
        ;   Term1 = Term
        )
    ;   atom(FormStr)
    ->  (   sub_atom(FormStr, _, _, _, '&self')
        ->  substitute_self_(Space, Term, Term1)
        ;   Term1 = Term
        )
    ;   %No source text to probe: walk, correctness over the shortcut.
        substitute_self_(Space, Term, Term1)
    ),
    (   python_import_alias(_, _)
    ->  bind_python_calls_(Term1, Bound)
    ;   Bound = Term1
    ),
    (   metta_token(_, _)
    ->  substitute_bound_tokens_(Bound, Rewritten)
    ;   Rewritten = Bound
    ).
'change-state!'(Var, Value, true) :-
    ( atom(Var) -> nb_setval(Var, Value)
    ; catch(nb_setval(Var, Value), E,
            rethrow_metta_operation_error('change-state!', E)) ).
'get-state'(Var, Value) :-
    catch(nb_getval(Var, Value), E,
          rethrow_metta_operation_error('get-state', E)).

%%% Eval: %%%
%eval runs its goals in the current space's module, for the same reason
%call_goals_in/2 and current_metta_space/1 exist: call/1 resolves a goal in the
%module its clause was compiled in, so a module-blind call/1 reaches only user.
%Without this, `!(eval (f 1))` on a function defined in any space other than
%&self raised `call_goals/1: Unknown procedure: f/2` while the same `!(f 1)`
%answered normally, and every named space PyPeTTa creates hit it. lib_he's
%`unify` and the ToResult asserts route their branches through eval, so they
%failed there too [tested: test_per_space.py::test_eval_uses_the_spaces_own_equations].
%There is no unset case any more: current_metta_module/1 answers &self's own
%module when nothing is in force, and a bare call/1 would resolve in the
%ENGINE's module, which is the parent and cannot see a space's clauses. The
%two-branch version and the call_goals/1 it needed are gone with it.
%Spelling the branch out here instead was measured and bought nothing
%[measured 2026-08-19: handle-round-trip 1,950,077 either way].
%eval takes its argument as written: &self resolved at the reader if the
%expression came from source, and a runtime-built term keeps its literal
%atoms, the same boundary stored data has. A substitution walk here re-ran
%the reader's work on every eval and found nothing.
eval(C0, Out) :- translate_runnable_expr(C0, Goals, Out),
                 current_metta_module(Module),
                 call_goals_in_(Module, Goals).

%evalc is eval in a space you name, the counterpart to context-space, which
%reports the space eval is already running in. Naming the space is the only
%way to reach another space's equations from MeTTa: import! loads a file into
%one, and everything else runs where it was written.
%
%The space argument selects the module the goals resolve in and nothing else.
%PeTTa's eval is a full evaluation of compiled goals rather than the single
%rewriting step of minimal MeTTa, and evalc keeps that, so the two agree
%everywhere except which space's equations answer
%[source: /home/user/Dev/LeaTTa/stdlib.md, evalc's SpaceType is the "Space to
%evaluate atom in its context"] [tested: metta_evalc].
%
%A space is an atom beginning with &, which is what is-space/2 tests, so an
%argument that is not one is a type error rather than a silently empty space.
%Like eval, evalc takes the expression as written: &self inside it named
%the space hosting the SOURCE (the reader pinned it there), not the space
%evalc is aimed at, so there is nothing left to substitute at run time.
evalc(C0, Space, Out) :- ( 'is-space'(Space, true)
                          -> true
                          ;  throw_metta_type_error(evalc, 'SpaceType', Space) ),
                        space_module(Space, Module),
                        with_metta_module(Module, eval(C0, Out)).

%Goals run in a named module, so a form run against a space reaches that
%space's own equations. call/1 resolves in the module its clause was
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
'foldl-atom'(L, _, _, _) :- var(L), !, refuse_unbound_input('foldl-atom', 1).
'foldl-atom'([], Acc, _Func, Acc).
'foldl-atom'([H|T], Acc0, Func, Out) :- reduce([Func,Acc0,H], Acc1, _),
                                        'foldl-atom'(T, Acc1, Func, Out).

'map-atom'(L, _, _) :- var(L), !, refuse_unbound_input('map-atom', 1).
'map-atom'([], _Func, []).
'map-atom'([H|T], Func, [R|RT]) :- reduce([Func,H], R, _),
                                   'map-atom'(T, Func, RT).

'filter-atom'(L, _, _) :- var(L), !, refuse_unbound_input('filter-atom', 1).
'filter-atom'([], _Func, []).
'filter-atom'([H|T], Func, Out) :- ( reduce([Func,H], true, _) -> Out = [H|RT]
                                                             ; Out = RT ),
                                   'filter-atom'(T, Func, RT).

%%% Prolog interop: %%%
argv(K, _) :- var(K), !, refuse_unbound_input(argv, 1).
argv(K, Arg) :- current_prolog_flag(argv, Argv), nth0(K, Argv, A), ( atom_number(A, N) -> Arg = N ; Arg = A ).
%A name with no predicate behind it is refused where the name is written.
%A registered name with no arity recorded compiles every call to it into a
%partial application rather than failing:
%!(import_prolog_functions_from_file "mylib.pl" (no-such-predicate)) reported
%success and !(no-such-predicate 1) answered (partial no-such-predicate (1)).
%A silent wrong answer is the worst outcome available here.
%
%The Python side refuses the same name in MeTTa.register_prolog for the same
%reason; this is the engine-level gate, so every route in gets it.
%
%register_fun_in(user, N), not register_fun/1: a registration that records no
%home module resolves only while NO named space has claimed the name, because
%fun_here/1's first clause is \+ fun_scoped(F). One named space defining an
%equation of the same name therefore turned every registered predicate into
%inert data in every space, with no error: !(rp-norm 3) answered (rp-norm 3).
%user is the module the clauses really are in, so this states where they live
%rather than adding a rule, and a named space that defines the name still
%shadows it, which is the behaviour that should happen
%[tested: a_registered_predicate_survives_a_named_space_claiming_its_name].
import_prolog_function(N, _) :- var(N), !,
                                refuse_unbound_input(import_prolog_function, 1).
import_prolog_function(N, true) :-
    import_prolog_function_at(N, scan).

%The DECLARED route knows the arity and registers that one, where the scan
%registers every arity current_predicate/1 can see. That difference is a
%defect when a declaration exists: `(: rc-scale (-> Number Number))` beside an
%internal `'rc-scale'/3` published BOTH, so `(rc-scale 3 7)` answered 21
%through a predicate the library never declared [reproduced 2026-08-16].
%
%The arity is already in hand at that moment. refuse_undeclared_arity/3
%computes it to check the predicate exists, so threading it out costs nothing
%and closes discovery on the route the whole metta_export design exists to
%make the good one. The scan stays for the legacy `names=` route, where
%nothing was declared and discovery is all there is
%[tested: a_declared_export_publishes_only_its_declared_arity].
import_prolog_function_at(N, Arity) :-
    must_be(atom, N),
    refuse_reserved_registration(N),
    refuse_absent_prolog_function(N),
    prolog_function_source(N, Source),
    claim_function_name(N, prolog, Source),
    %The clauses are the HOST's, in whatever module consult_global/1 put them
    %(`user`), and every space reaches them through the base chain. What is
    %registered here is the base TIER's claim on the name, which is &self's
    %module: fun_here_in/2 reads that claim as "callable from every space
    %unless a space of its own claims the name", and it is the same claim
    %register_op/2 makes on the Python side.
    metta_self_module(Self),
    register_fun_in(Self, N),
    (   Arity == scan
    ->  register_prolog_arities(N)
    ;   register_arity(N, Arity)
    ).

%The file the clauses in the database RIGHT NOW came from, read off a clause
%rather than off the predicate. predicate_property(file(F)) is the wrong
%question here and answers the wrong thing: after a second library redefines a
%static predicate it still reports the FIRST library's file, which is exactly
%the case this has to detect. A registration made from source held in memory
%has no file, and says so.
prolog_function_source(N, Source) :-
    (   current_predicate(N/Arity),
        functor(Head, N, Arity),
        nth_clause(Head, 1, Ref),
        clause_property(Ref, file(File))
    ->  Source = File
    ;   Source = unknown
    ).

%Two names a registration must not take, both of which it used to take
%silently while reporting success.
%
%A builtin, because a consulted predicate REPLACES the engine's static one for
%the whole process: registering a predicate named + made !(+ 1 2) answer
%whatever the library said, and the only diagnostic was SWI's redefinition
%warning on stderr, which no caller sees. The equation route already refuses
%exactly this at spaces.pl through petta_builtin_redefinition/3, so this is
%the same rule reaching the other road in rather than a new one.
%
%A special form, because translate_special_dl/5 is tried BEFORE function
%dispatch, so the registration compiles nothing and can never be reached:
%registering a predicate named if left !(if True 1 2) answering 1 from the
%translator and the library's clauses dead, with nothing said at any point.
%Accepting a registration that cannot run is telling the author their code is
%installed when it is not
%[tested: a_builtin_name_is_refused, a_special_form_name_is_refused].
refuse_reserved_registration(N) :-
    (   builtin_fun(N)
    ->  throw(error(permission_error(register, metta_builtin, N),
                    context(import_prolog_function/2,
                            'the engine defines this name')))
    ;   metta_special_form(N)
    ->  throw(error(permission_error(register, metta_special_form, N),
                    context(import_prolog_function/2,
                            'the translator compiles this name')))
    ;   true
    ).

%Who put a function's clauses where they are. fun/1 says a name IS a function
%and fun_in/2 says which module its clauses live in; neither says which tier
%put them there, and without that a registration from one tier silently took
%a name another tier owned. Registering a Prolog predicate over a live Python
%operation replaced it, left petta_py_op_spec/3 still claiming the name, and
%wedged it for the life of the process: the operation could not be
%unregistered, because retractall/1 on what was now a static predicate raised,
%and could not be re-registered either.
%
%Equations are deliberately not recorded here. Their origin is already
%answerable, from the space that holds the atom and from fun_in/2, and one
%assertion per compiled equation is a cost on the hot path for a fact that is
%already derivable [tested: a_name_another_tier_owns_is_refused,
%test_a_python_operation_is_not_silently_replaced].
:- dynamic metta_function_origin/3.   %metta_function_origin(Name, Tier, Detail)

refuse_other_tiers_name(Name, Tier) :-
    (   metta_function_origin(Name, Other, OtherDetail), Other \== Tier
    ->  throw(error(permission_error(register, metta_function, Name),
                    context(refuse_other_tiers_name/2,
                            owned_by(Other, OtherDetail))))
    ;   true
    ).

%The same refusal for two PROLOG sources, asked where it can still be acted
%on: before the source that would take the name has been read.
%
%claim_function_name/3 asks the same question after the consult and has to,
%because that is the only place the clobber can be DETECTED. But detection
%after the fact told the wrong author: B was refused by name and A, which did
%nothing, silently answered B's implementation from then on
%[reproduced 2026-08-16: `A before B: 20`, `B refused`, `A after: 30`]. This
%is the check moved to where refusing still prevents something, which is
%exactly why check_prolog_function_names/3 exists for builtins ten lines
%down, and it is the same error term so one diagnostic covers both positions.
refuse_other_sources_name(Name, Source) :-
    (   metta_function_origin(Name, prolog, Owner),
        Owner \== unknown, Source \== unknown, Owner \== Source
    ->  throw(error(petta_name_owned_by_source(Name, Owner),
                    context(refuse_other_sources_name/2,
                            'two Prolog sources claim one name')))
    ;   true
    ).

%unknown is not an identity, it is prolog_function_source/2 saying it could
%not tell, which is what a predicate installed by use_foreign_library/1
%answers: it has no clause with a file behind it. Two of them are not the same
%source and one is not a different source either, so comparing them decides
%nothing and refusing on one refuses a library re-registering itself
%[tested: test_a_compiled_library_registers_from_python]. A C predicate cannot
%take a name this way in silence regardless, because installing over a static
%predicate raises from SWI rather than warning.

%What a source is CALLED, for comparing one against another. A file is
%recorded under SWI's canonical absolute path, since that is what
%clause_property(file(F)) answers, and a caller passes whatever they typed; a
%load from memory has no file and is recorded under the name it loaded as, so
%it passes through unchanged.
canonical_prolog_source(Source, Canonical) :-
    (   absolute_file_name(Source, Resolved, [file_errors(fail), access(read)])
    ->  Canonical = Resolved
    ;   Canonical = Source
    ).

%Re-registering under the same tier is replacement, which is what register_op
%does on every call. Two different PROLOG SOURCES claiming one name is not
%replacement, it is two libraries destroying each other's predicate, so that
%is refused and the source that owns it is named.
%
%This fires AFTER the consult, and it has to, which is the shape of the
%problem rather than a shortcut. SWI does warn about the redefinition, on
%stderr, and it does not throw: "Redefined static procedure 'shared-norm'/2"
%is printed and the load continues, so no catch/3 can see it and the only
%reliable check is a positive one afterwards, asking whether the name still
%resolves to what its owner loaded. CPython reaches the same answer for the
%same reason and does it by name as a matter of course
%[source: CPython, PyCapsule_Import, "a high degree of certainty that the
%Capsule they load contains the correct C API"]. The clobber has happened by
%the time this raises; what it buys is that the author hears about it instead
%of shipping a library silently bound to someone else's code, and
%unregister_metta_extension/1 is how they take it back out
%[tested: two_sources_cannot_claim_one_name].
claim_function_name(Name, Tier, Detail) :-
    (   metta_function_origin(Name, Owner, OwnerDetail)
    ->  claim_over(Name, Owner, OwnerDetail, Tier, Detail)
    ;   assertz(metta_function_origin(Name, Tier, Detail))
    ).

claim_over(Name, Owner, _, Tier, Detail) :-
    Owner == Tier, Owner \== prolog, !,
    retractall(metta_function_origin(Name, _, _)),
    assertz(metta_function_origin(Name, Tier, Detail)).
claim_over(Name, prolog, Detail, prolog, Detail) :- !,
    retractall(metta_function_origin(Name, _, _)),
    assertz(metta_function_origin(Name, prolog, Detail)).
claim_over(Name, prolog, OwnerDetail, prolog, _) :- !,
    throw(error(petta_name_owned_by_source(Name, OwnerDetail),
                context(claim_function_name/3,
                        'two Prolog sources claim one name'))).
claim_over(Name, _, _, Tier, _) :-
    refuse_other_tiers_name(Name, Tier).

release_function_name(Name) :- retractall(metta_function_origin(Name, _, _)).

%%%% A library declares its own exports, in the file that implements them %%%%
%
%Registering one predicate took three statements in two languages: the name in
%a Python call, the arity discovered by scanning whatever current_predicate/1
%happened to hold, and the type in a third statement whose ordering against
%call-site compilation nothing checked. Nothing kept the three in agreement,
%and the arity was DISCOVERED rather than declared, so a library shipping a
%public 'vec-dot'/3 and an internal helper 'vec-dot'/2 published both.
%
%Every comparable runtime puts the export declaration in the file that
%implements it: PyMethodDef, R_CallMethodDef, ErlNifFunc, napi_property_
%descriptor, SWI's own module/2 export list. R had exactly this engine's
%mechanism, symbol discovery, and walked away from it, because "the use of
%registration allows R to ensure that code compiled into packages does not
%inadvertently call routines in other packages"
%[source: R Extensions manual, section 5.4].
%
%The declaration is MeTTa, in a string, rather than a new Prolog operator. The
%types are MeTTa types, the reader that parses them is the engine's own, and
%the MeTTa arity comes from the type chain, so the arity cannot disagree with
%the type it was written beside:
%
%    :- metta_extension(pettorch, [version('0.3.1')]).
%    :- metta_export("
%        (: vec-dot (-> Number Number Number))
%        (: shape-of (-> Atom Atom))
%        (export vec-helper 1)
%    ").
%
%(export Name Arity) is the form for a name whose type the author does not
%want to state; the arity is the MeTTa arity, one less than the predicate's.
%
%The directive records; the LOAD registers, once the file has finished and its
%predicates exist. consult_global/1 and its two siblings are the funnel every
%route enters through, so the MeTTa spelling, register_prolog and a bare
%consult all get this [tested: prolog_interface_exports].
:- dynamic pending_metta_export/3.     %pending_metta_export(File, Name, Type)
:- dynamic metta_extension_info/3.     %metta_extension_info(Extension, File, Options)
:- dynamic metta_extension_member/2.   %metta_extension_member(Extension, Name)

%The version of the extension SEAM a library was written against. A library
%built on today's ext_points.pl will be loaded into a later engine, and with
%nothing to check against a removed or renamed hook shows up as silence.
%
%Erlang's NIF loader is the model for the check: the major version must match
%and the minor must not be newer than the runtime's, or the load fails. The
%rule here is the same and stated the same way, because a library that
%declares nothing is the common case and must keep working: a declaration is
%checked, silence is not.
%
%The number moves when a seam a library can SEE changes: a hook removed or
%renamed, a hook's arguments changed, a refusal added where none was. Adding
%a hook moves the minor.
metta_extension_api_version(1, 0).

metta_extension(Name, Options) :-
    must_be(atom, Name),
    must_be(list, Options),
    check_extension_requirements(Name, Options),
    declaring_file(File),
    retractall(metta_extension_info(Name, File, _)),
    assertz(metta_extension_info(Name, File, Options)).

check_extension_requirements(Name, Options) :-
    (   memberchk(requires(Major-Minor), Options)
    ->  refuse_incompatible_extension(Name, Major, Minor)
    ;   true
    ).

refuse_incompatible_extension(Name, Major, Minor) :-
    metta_extension_api_version(OurMajor, OurMinor),
    (   Major =:= OurMajor, Minor =< OurMinor
    ->  true
    ;   throw(error(petta_extension_api_mismatch(Name, Major-Minor,
                                                 OurMajor-OurMinor),
                    context(metta_extension/2,
                            'this engine does not offer the seam the \c
                             extension was written against')))
    ).

metta_export(Source) :-
    declaring_file(File),
    parse_metta_source(Source, ParsedForms),
    forall(member(Parsed, ParsedForms), record_metta_export(File, Parsed)).

%The file a directive is running in. prolog_load_context/2 answers it during a
%consult; outside one, which is how a test or an inline snippet reaches here,
%the exports are keyed on a name of their own so they still register.
declaring_file(File) :-
    ( prolog_load_context(source, Source) -> File = Source ; File = 'petta_inline' ).

record_metta_export(File, parsed(_, Text, Term)) :-
    (   Term = [':', Name, Type], atom(Name), is_list(Type), Type = [->|_]
    ->  assertz(pending_metta_export(File, Name, Type))
    ;   Term = [export, Name, Arity], atom(Name), integer(Arity)
    ->  assertz(pending_metta_export(File, Name, arity(Arity)))
    ;   Term = [volatility, Name, Level], atom(Name),
        memberchk(Level, [volatile, stable, immutable])
    ->  declare_function_volatility(Name, Level)
    ;   Term = [determinism, Name, Mode], atom(Name),
        memberchk(Mode, [det, semidet, nondet])
    ->  declare_function_determinism(Name, Mode)
    ;   throw(error(petta_export_form(Text),
                    context(metta_export/1,
                            'an export is (: name (-> ...)), (export name arity), \c
                             (volatility name volatile|stable|immutable) or \c
                             (determinism name det|semidet|nondet)')))
    ).

%How much a caller may assume about a function's answers, and therefore what
%an optimiser or a cache is allowed to do with it. PostgreSQL's ladder,
%because purity is not a boolean and its three rungs are the ones that turn
%out to matter: VOLATILE "makes no assumptions", STABLE gives the same answer
%within one statement so repeated calls may fold to one, and IMMUTABLE gives
%the same answer forever so a call on constant arguments may be folded at
%plan time [source: PostgreSQL documentation, Function Volatility Categories].
%
%The gap this closes was demonstrated rather than imagined: lib_memo will
%happily cache a side-effecting registered predicate, because nothing records
%whether caching it is sound, and the second call then skips the effect.
%
%SILENCE STAYS PERMISSION. PostgreSQL's default is the pessimistic rung and
%this one's is not, deliberately: memoization here is already opt-in by the
%CALLER, so making an undeclared function refuse would break every existing
%(memoize f) without telling anyone anything they did not know. What was
%missing is the library's ability to say NO, and a declared `volatile` is
%that no [tested: a_volatile_function_refuses_memoization].
:- dynamic metta_function_volatility/2.

declare_function_volatility(Name, Level) :-
    retractall(metta_function_volatility(Name, _)),
    assertz(metta_function_volatility(Name, Level)).

%True when a cache may serve this function's answers.
metta_function_cacheable(Name) :- \+ metta_function_volatility(Name, volatile).

%How many answers a caller may expect. Only det is ENFORCED, by handing the
%predicate to SWI's own det/1, and it is worth having because a leaked choice
%point is invisible to the counter and expensive in reality: no-cut, cut and
%SSU dispatch all reported exactly 1,000,003 inferences while wall clock was
%0.1887, 0.0928 and 0.1128 [measured, ai-todo-fast-libraries.md B5]. Declaring
%it moves the failure to the library's own door instead of taxing every caller.
%
%Read det as EXACTLY one answer, not at most one: SWI raises "Deterministic
%procedure f/2 failed" as readily as it raises on a choice point, so a
%function whose empty answer set is a legitimate result is semidet and not det
%[measured 2026-08-16]. semidet and nondet are recorded rather than checked,
%because SWI has a directive for det alone; they are still read, by
%profile_extension, where they say whether a redo was intended.
:- dynamic metta_function_determinism/2.

declare_function_determinism(Name, Mode) :-
    retractall(metta_function_determinism(Name, _)),
    assertz(metta_function_determinism(Name, Mode)).

apply_declared_determinism(Name, Type) :-
    (   metta_function_determinism(Name, det)
    ->  declared_predicate_arity(Type, Arity),
        det(Name/Arity)
    ;   true
    ).

%The pending list is emptied BEFORE anything is checked, so a declaration
%that raises leaves no residue for the next load to pick up: without that, a
%file whose declaration named an arity it did not define left its exports
%pending and the next unrelated consult failed on them.
register_pending_exports :-
    findall(File-Name-Type, pending_metta_export(File, Name, Type), Pending),
    retractall(pending_metta_export(_, _, _)),
    ( Pending == [] -> true ; register_declared_exports(Pending) ).

%Every name is checked before any is registered, which is import_prolog_
%functions/2's rule reaching this route too: a declaration with one bad entry
%registers nothing.
register_declared_exports(Pending) :-
    catch(check_and_register_declared_exports(Pending), Error,
          ( undo_declared_exports(Pending), throw(Error) )).

check_and_register_declared_exports(Pending) :-
    forall(member(_-Name-_, Pending), refuse_reserved_registration(Name)),
    forall(member(_-Name-_, Pending), refuse_other_tiers_name(Name, prolog)),
    forall(member(File-Name-_, Pending),
           ( canonical_prolog_source(File, Source),
             refuse_other_sources_name(Name, Source) )),
    forall(member(_-Name-Type, Pending), refuse_undeclared_arity(Name, Type, _)),
    forall(member(File-Name-Type, Pending),
           ( refuse_undeclared_arity(Name, Type, Arity),
             import_prolog_function_at(Name, Arity),
             declare_export_type(Name, Type),
             apply_declared_determinism(Name, Type),
             record_extension_membership(File, Name) )).

%All or nothing, and "nothing" has to reach past the registrations to the
%SOURCE. Every refusal in here is post-load and cannot be otherwise, so every
%one of them needs the rollback: a file refused for a reserved name has
%already replaced the builtin's static predicate, and a file refused for a
%wrong arity has already brought in whatever else it defines.
%
%THE SHAPE: By the time anything here can fail the file's clauses are already in
%the database, and if one of them redefined a static predicate another library
%loaded, that library's clauses are gone: SWI prints "Redefined static
%procedure" and continues, so the damage lands before any check can speak.
%Leaving the file loaded after refusing it left the OTHER author's function
%silently answering this one's implementation.
%
%unload_file/1 is SWI's own way of taking a load back out, "Remove all clauses
%loaded from File" [source: SWI-Prolog 10.1 Reference Manual, unload_file/1],
%and it is what unregister_metta_extension/1 already uses for the same job.
%What it does NOT do is restore the incumbent's clauses, which nothing can:
%those were destroyed at compile time. What it buys is that the name is empty
%and loud rather than full and wrong, and the recovery is the documented one,
%re-registering the library that owned it
%[tested: a_computed_declaration_is_refused_and_its_source_unloaded].
%Release only what this source currently owns. A name it never reached has no
%origin to retract and a name another source owns is not this one's to release,
%so asking the registry who owns it now is both the test and the rollback list.
undo_declared_exports(Pending) :-
    forall(member(File-Name-_, Pending), undo_declared_export(File, Name)),
    findall(File, member(File-_-_, Pending), Files),
    sort(Files, Sources),
    forall(member(Source, Sources), unload_declared_source(Source)).

undo_declared_export(File, Name) :-
    canonical_prolog_source(File, Source),
    (   metta_function_origin(Name, prolog, Source)
    ->  forget_registered_function(Name)
    ;   true
    ).

%petta_inline is the name a declaration outside any load is keyed on, so there
%is no file to take back out.
unload_declared_source('petta_inline') :- !.
unload_declared_source(Source) :- catch(unload_file(Source), _, true).

%The MeTTa arity is the type chain's length less one, and the predicate's is
%one more than that: (-> Number Number Number) is two inputs and an output,
%so 'vec-dot'/3.
declared_predicate_arity([->|Types], Arity) :- !, length(Types, Arity).
declared_predicate_arity(arity(MettaArity), Arity) :- Arity is MettaArity + 1.

%Answers the arity it checked, so the caller can register THAT rather than
%rediscovering every arity the predicate happens to have.
refuse_undeclared_arity(Name, Type, Arity) :-
    declared_predicate_arity(Type, Arity),
    (   current_predicate(Name/Arity)
    ->  true
    ;   throw(error(existence_error(procedure, Name/Arity),
                    context(metta_export/1,
                            'the declaration names an arity this file does not define')))
    ).

declare_export_type(_, arity(_)) :- !.
declare_export_type(Name, Type) :-
    Declaration = [':', Name, Type],
    ( get_native_atom('&self', Declaration) -> true
    ; 'add-atom'('&self', Declaration, _) ).

%Two records, per EXTENSION and per FILE, because the two answer different
%questions and only one of them was being asked.
%
%An extension is optional here by design, which is why this clause ends in
%`; true`. The Python side then read what a registration produced by walking
%extension MEMBERSHIP, so a file carrying `metta_export` and no
%`metta_extension`, which is the natural shape for a single-file library,
%registered everything correctly and then reported failure: `is_function` true
%and the call answering 10, beside `ValueError: register_prolog needs the
%names to register` [reproduced 2026-08-16]. The state was right and the
%report was wrong, which is I15's wedged registry and I25's partial state
%inverted.
%
%The file record makes the lookup exact and leaves extensions optional, which
%is what the Prolog side already intended
%[tested: a_declared_export_without_an_extension_reports_its_names].
:- dynamic metta_file_export/2.

record_extension_membership(File, Name) :-
    (   metta_file_export(File, Name) -> true
    ;   assertz(metta_file_export(File, Name)) ),
    (   metta_extension_info(Extension, File, _)
    ->  ( metta_extension_member(Extension, Name) -> true
        ; assertz(metta_extension_member(Extension, Name)) )
    ;   true
    ).

%Everything one extension installed, gone. PostgreSQL's rule, and its reason:
%"PostgreSQL will not let you drop an individual object contained in an
%extension, except by dropping the whole extension", which is what stops a
%registry keeping a claim on a name it can no longer release. unload_file/1 is
%SWI's own mechanism for taking a consulted file's clauses back out, so the
%predicates go with the registrations rather than being left callable through
%a name nothing records [tested: an_extension_unloads_whole].
unregister_metta_extension(Extension) :-
    must_be(atom, Extension),
    loaded_extension_file(Extension, File),
    findall(Name, metta_extension_member(Extension, Name), Names),
    forall(member(Name, Names), forget_registered_function(Name)),
    retractall(metta_extension_member(Extension, _)),
    %The per-file record goes with them, or a re-registration of the same file
    %would report names that are no longer there.
    retractall(metta_file_export(File, _)),
    retractall(metta_extension_info(Extension, File, _)),
    ( File == 'petta_inline' -> true ; catch(unload_file(File), _, true) ).

%Its own predicate so the file is a head argument: read inline, the binding
%happens in one branch of an if-then-else whose other branch throws, and SWI's
%var_branches check cannot see that the other branch never returns.
loaded_extension_file(Extension, File) :-
    (   metta_extension_info(Extension, Recorded, _)
    ->  File = Recorded
    ;   throw(error(existence_error(metta_extension, Extension),
                    context(unregister_metta_extension/1,
                            'no extension of that name is loaded')))
    ).

forget_registered_function(Name) :-
    remove_sexp('&self', [':', Name, _]),
    release_function_name(Name),
    unregister_fun_everywhere(Name),
    retractall(fun(Name)),
    retractall(arity(Name, _)),
    forall(metta_on_function_removed(Name), true).

%Ask whether a whole list of names may be registered from Source, BEFORE
%Source is loaded. Order is the whole point: consulting a file that defines a
%builtin's name has already replaced the engine's static predicate by the time
%any per-name refusal could fire, so refusing afterwards left !(+ 1 2)
%answering the library's answer while reporting the registration as refused
%[tested: a_reserved_name_is_refused_before_the_source_loads].
%
%The name another SOURCE owns is refused here for exactly that reason and it
%was not: claim_function_name/3 refused it after the consult, which told the
%wrong author. B heard "already registered from A" and A, which did nothing,
%answered B's implementation from then on
%[tested: a_name_another_source_owns_is_refused_before_the_load].
check_prolog_function_names(Names, Source, true) :-
    prolog_function_name_list(Names, check_prolog_function_names/3),
    canonical_prolog_source(Source, Canonical),
    forall(member(N, Names), refuse_reserved_registration(N)),
    forall(member(N, Names), refuse_other_tiers_name(N, prolog)),
    forall(member(N, Names), refuse_other_sources_name(N, Canonical)).

%Register every name, or none. Validating inside the registration loop left a
%typo in the third name with the first two registered and callable, and the
%list of what had taken died inside the exception, so the caller could not
%learn what to undo. This is the shape petta_py_register_op_set already uses
%one file over: probe every name first, touch state only after
%[tested: a_typo_in_the_list_registers_nothing].
import_prolog_functions(Names, true) :-
    prolog_function_name_list(Names, import_prolog_functions/2),
    forall(member(N, Names), refuse_reserved_registration(N)),
    forall(member(N, Names), refuse_absent_prolog_function(N)),
    forall(member(N, Names), import_prolog_function(N, _)).

prolog_function_name_list(Names, Context) :-
    (   is_list(Names)
    ->  forall(member(N, Names), must_be(atom, N))
    ;   throw(error(type_error(list, Names),
                    context(Context, 'the names to register')))
    ).

refuse_absent_prolog_function(N) :-
    (   current_predicate(N/_)
    ->  true
    ;   throw(error(existence_error(procedure, N),
                    context(import_prolog_functions/2,
                            'no Prolog predicate of that name is loaded')))
    ).

%A Prolog library loaded from MeTTa belongs to the process, not to a space. Its
%predicates are builtins once loaded, register_fun/1 reads their arity out of
%user, and every space has to be able to call them. SWI loads a file into the
%module the load runs in, and under per-space equations a runnable form runs in
%its space's module, so a library imported inside a named space would define
%itself where register_fun/1 cannot see it: the arities never register and every
%call to it compiles to a partial application instead. In &self the load module
%already is user, so this states that behaviour rather than adding a rule.
consult_global(File) :- refuse_claimed_source_exports(File),
                        loading_loudly(user:consult(File)),
                        register_pending_exports.
use_module_global(File) :- refuse_claimed_source_exports(File),
                           loading_loudly(user:use_module(File)),
                           register_pending_exports.

%%%% Read the manifest before running the payload %%%%
%
%A source declares its exports INSIDE the file that implements them, which is
%the design the review argues for and the one that makes the arity and the
%type impossible to disagree. It also means the names are not known until the
%file has run, and by then a clause of the file has already replaced a static
%predicate another library loaded: SWI prints "Redefined static procedure" and
%CONTINUES, so the incumbent's clauses are gone before any refusal can speak.
%A directive cannot stop that either, because a directive that throws is
%reported and the load carries on [measured 2026-08-16: with the refusal in
%the metta_export/1 directive itself, `A AFTER refusal` still answered B's 30].
%
%So read the manifest out of the source WITHOUT running the source. This is
%PostgreSQL's control file, which the codebase already follows for the
%extension model: the file that says what an extension is gets read before the
%script that installs it. Python reads a package's entry points out of its
%metadata rather than by importing it, for the same reason.
%
%The scan is exact for a literal declaration, which is every one written by
%hand. It stops at the first term it cannot read, and does not run :- op/3, so
%a file that defines its own operators and declares exports below them is
%scanned only as far as the operator. Whatever the scan misses,
%register_declared_exports_or_undo/1 still catches after the load, with the
%rollback that is all that is left by then
%[tested: a_second_source_claiming_a_name_never_loads].
refuse_claimed_source_exports(Spec) :-
    (   absolute_file_name(Spec, File,
                           [file_type(prolog), access(read), file_errors(fail)])
    ->  setup_call_cleanup(open(File, read, In),
                           refuse_claimed_stream_exports(In, File),
                           close(In))
    ;   true
    ).

refuse_claimed_string_exports(Name, Text) :-
    setup_call_cleanup(open_string(Text, In),
                       refuse_claimed_stream_exports(In, Name),
                       close(In)).

refuse_claimed_stream_exports(In, File) :-
    canonical_prolog_source(File, Source),
    read_declarations(In, Declarations),
    findall(Name, member(export(Name), Declarations), Names),
    forall(member(Name, Names), refuse_reserved_registration(Name)),
    forall(member(Name, Names), refuse_other_tiers_name(Name, prolog)),
    forall(member(Name, Names), refuse_other_sources_name(Name, Source)).

%Everything a source DECLARES, read without running it: export(Name) for each
%name it publishes and extension(Name) for each extension it joins. Both
%consumers of the scan filter this rather than reading the file twice.
metta_source_declarations(Spec, Declarations) :-
    (   absolute_file_name(Spec, File,
                           [file_type(prolog), access(read), file_errors(fail)])
    ->  setup_call_cleanup(open(File, read, In),
                           read_declarations(In, Declarations),
                           close(In))
    ;   Declarations = []
    ).

metta_string_declarations(Text, Declarations) :-
    setup_call_cleanup(open_string(Text, In),
                       read_declarations(In, Declarations),
                       close(In)).

read_declarations(In, Declarations) :-
    (   read_one_declaration(In, Some)
    ->  read_declarations(In, Rest),
        append(Some, Rest, Declarations)
    ;   Declarations = []
    ).

%One term. quiet rather than dec10 on purpose: a syntax error here is not this
%predicate's to report, the consult that follows reports it properly and with
%the line, so the scan goes quiet and stops rather than printing a second copy.
read_one_declaration(In, Declarations) :-
    catch(read_term(In, Term, [syntax_errors(quiet), variable_names(_)]),
          _, fail),
    Term \== end_of_file,
    declaration_of(Term, Declarations).

declaration_of((:- metta_extension(Name, _)), [extension(Name)]) :-
    atom(Name), !.
declaration_of((:- metta_export(Text)), Names) :-
    ( string(Text) ; atom(Text) ),
    !,
    catch(parse_metta_source(Text, Forms), _, fail),
    findall(export(Name), claimed_export_name(Forms, Name), Names).
declaration_of(_, []).

%The two forms that CLAIM a name. volatility and determinism state a property
%of a name claimed elsewhere, so they are not a claim to refuse.
claimed_export_name(Forms, Name) :-
    member(parsed(_, _, Term), Forms),
    ( Term = [':', Name, [->|_]] ; Term = [export, Name, Arity], integer(Arity) ),
    atom(Name).

%The same load, importing chosen exports under chosen names. SWI's own import
%list carries the renaming, so two libraries that both export norm/2 can both
%be present: the second arrives as mylib-norm and neither is rebound. Without
%it SWI refuses the second import, prints "No permission to import
%libb:'norm'/2 into user (already imported from liba)" and CONTINUES, which
%leaves the incumbent protected and the newcomer silently bound to the
%incumbent's code. That is the one collision a name refusal cannot fix, since
%neither library is wrong and neither can be asked to change.
%
%Loaded twice on purpose: with an empty import list first, so the module
%exists and can be asked what it exports, and then with the renames built from
%those arities. A caller therefore writes two names and no arity.
use_module_global(File, Renames) :-
    %SWI reaches a plain file first and raises domain_error(module_header, _),
    %which says what is wrong and not what to do about it.
    catch(loading_loudly(user:use_module(File, [])),
          error(domain_error(module_header, _), _),
          throw(error(petta_not_a_prolog_module(File),
                      context(use_module_global/2,
                              'renaming imports needs a module')))),
    module_exports_of(File, Module, Exports),
    maplist(renamed_import(Module, Exports), Renames, Imports),
    loading_loudly(user:use_module(File, Imports)),
    register_pending_exports.

module_exports_of(File, Module, Exports) :-
    absolute_file_name(File, Resolved,
                       [file_type(prolog), access(read), file_errors(fail)]),
    (   module_property(Module, file(Resolved))
    ->  module_property(Module, exports(Exports))
    ;   throw(error(petta_not_a_prolog_module(File),
                    context(use_module_global/2,
                            'renaming imports needs a module')))
    ).

%A name the module does not export cannot be imported under any name, and
%saying so with the export list is the difference between fixing a typo and
%guessing at one.
renamed_import(Module, Exports, Rename, Name/Arity as To) :-
    rename_pair(Rename, From0, To0),
    petta_name_atom(From0, Name),
    petta_name_atom(To0, To),
    (   memberchk(Name/Arity, Exports)
    ->  true
    ;   throw(error(petta_not_exported(Module, Name, Exports),
                    context(use_module_global/2,
                            'a rename names an export')))
    ).

%A rename is written From-To in Prolog and arrives as [From, To] from Python,
%since Janus carries a list and not a pair. Clauses rather than an
%if-then-else, so the two names are bound on every branch that reaches a use.
rename_pair(From-To, From, To) :- !.
rename_pair([From, To], From, To) :- !.
rename_pair(Rename, _, _) :-
    throw(error(type_error(petta_rename, Rename),
                context(use_module_global/2,
                        'a rename is From-To or [From, To]'))).

petta_name_atom(Name0, Name) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ).

%The same load for source held in memory, which is how a library ships Prolog
%inline beside its Python. Name identifies the source location of the loaded
%clauses and is also what SWI removes clauses under when the same name is
%loaded again, so it has to be derived from the CONTENT: an address, which is
%what the caller used to pass, is reused by CPython the moment the string it
%named is freed, and the second registration then erased the first library's
%clauses [source: SWI-Prolog 10.1 Reference Manual, load_files/2, stream/1].
consult_string_global(Name, Text) :-
    refuse_claimed_string_exports(Name, Text),
    setup_call_cleanup(open_string(Text, In),
                       loading_loudly(user:load_files(Name, [stream(In)])),
                       close(In)),
    register_pending_exports.

%Raise what SWI would only have printed. A syntax error inside a consulted
%file goes through print_message/2 and the load then SUCCEEDS with the
%predicate undefined, so a library author's whole diagnostic was one line on
%stderr while the API reported success:
%  ERROR: .../lib.pl:1:28: Syntax error: Operator expected
%and register_prolog then said "no predicate named 'f' was defined by that
%source", which names the symptom and not the cause. Wrapping the load in
%catch/3 does not help, because these are printed rather than thrown.
%
%thread_message_hook/3 is SWI's own answer for exactly this, "intended to
%catch messages that may be produced by calling some goal without affecting
%other threads", and being thread-local is what lets a Pool worker load a file
%without collecting another worker's messages
%[source: SWI-Prolog 10.1 Reference Manual, section 4.11, message_hook/3].
%
%Only error-kind messages are collected. A warning is not a failed load:
%singleton variables are a style note, and the redefinition warning that
%matters is caught positively instead, by asking after the load whether each
%name resolves where it should [tested: a_syntax_error_in_a_library_raises].
:- thread_local petta_load_diagnostic/1, petta_watching_load/0.
:- multifile user:thread_message_hook/3.
user:thread_message_hook(Term, error, _Lines) :-
    petta_watching_load,
    message_to_string(Term, Text),
    assertz(petta_load_diagnostic(Text)),
    %Fail deliberately: SWI still prints the message with its full context,
    %and the throw below carries the summary a caller can act on.
    fail.

:- meta_predicate loading_loudly(0).
loading_loudly(Goal) :-
    setup_call_cleanup(( retractall(petta_load_diagnostic(_)),
                         assertz(petta_watching_load) ),
                       Goal,
                       retractall(petta_watching_load)),
    findall(Text, petta_load_diagnostic(Text), Diagnostics),
    retractall(petta_load_diagnostic(_)),
    (   Diagnostics == []
    ->  true
    ;   atomic_list_concat(Diagnostics, '; ', Summary),
        throw(error(petta_load_failed(Summary),
                    context(loading_loudly/1,
                            'the Prolog source reported an error while loading')))
    ).
%A predicate term headed by a space is a provider query, not a raw Prolog
%call into the module where native atoms happen to be stored. Other heads keep
%the Prolog interop constructor's original meaning.
metta_predicate_goal([Space|Pattern],
                     match(Space, Pattern, matched, matched)) :-
    atom(Space), atom_concat('&', _, Space), !.
metta_predicate_goal([F|Args], Term) :- Term =.. [F|Args].

'Predicate'(Parts, _) :- var(Parts), !, refuse_unbound_input('Predicate', 1).
'Predicate'(Parts, Term) :- metta_predicate_goal(Parts, Term).
%Resolved in the CALLING space's module, which reaches both directions of this
%seam: a host Prolog predicate through the module's base chain, and a MeTTa
%function this space compiled, which lives in that module and nowhere else.
%Called unqualified it resolved in the engine's own module, so
%`(callPredicate (Predicate (myAddMeTTa 241 $x)))` over a function the program
%had just defined raised Unknown procedure
%[tested: examples/integration/prologimport.metta].
%
%assertaPredicate/2 and its siblings deliberately do NOT follow: a clause a
%MeTTa program asserts is host Prolog, it belongs in the host tier where
%consult_global/1 puts a consulted file, and import_prolog_function/2 looks
%for it there.
callPredicate(G, true) :- current_metta_module(Module), call(Module:G).
assertzPredicate(G, true) :- assertz(G).
assertaPredicate(G, true) :- asserta(G).
retractPredicate(G, true) :- retract(G), !.
retractPredicate(_, false).

%%% Library / Import: %%%
ensure_metta_ext(Path, Path) :- file_name_extension(_, gz, Path), !.
ensure_metta_ext(Path, Path) :- file_name_extension(_, metta, Path), !.
ensure_metta_ext(Path, PathWithExt) :- file_name_extension(Path, metta, PathWithExt).

current_working_dir(Base) :- working_dir(Base), !.
current_working_dir(Base) :- absolute_file_name('.', Base, [file_type(directory)]).

import_file_string(File, SFile) :- string(File), !, SFile = File.
import_file_string(File, SFile) :- atom_string(File, SFile).

python_import_file(File) :- import_file_string(File, SFile),
                            file_name_extension(_, py, SFile).

resolve_existing_import_path(Base, RequestedPath, CanonPath) :-
    ( is_absolute_file_name(RequestedPath)
      -> absolute_file_name(RequestedPath, CanonPath,
                            [access(read), file_errors(fail)])
       ; absolute_file_name(RequestedPath, CanonPath,
                            [relative_to(Base), access(read), file_errors(fail)]) ),
    !.

throw_missing_import(File) :-
    throw(error(existence_error(source_sink, File), context('import!', File))).

resolve_metta_import_path(File, CanonPath) :-
    import_file_string(File, SFile),
    \+ python_import_file(SFile),
    current_working_dir(Base),
    ensure_metta_ext(SFile, RequestedPath),
    ( resolve_existing_import_path(Base, RequestedPath, CanonPath)
      -> true
       ; throw_missing_import(File) ).

resolve_python_import_path(File, CanonPath) :-
    import_file_string(File, SFile),
    python_import_file(SFile),
    current_working_dir(Base),
    ( resolve_existing_import_path(Base, SFile, CanonPath)
      -> true
       ; throw_missing_import(File) ).

:- dynamic imported_metta_source/2.
:- dynamic import_life/3.

%Import state cannot live as a clause of the space predicate: wildcard
%remove-atom retracts every unifying clause, including rules. Loading is
%visible while recursive imports run so cycles terminate; success changes the
%state to loaded. A full space clear owns removal of both states.
import_life_current(Space, CanonPath) :-
    atom(Space), !,
    import_life(Space, CanonPath, _).
import_life_current(_, _).

assert_import_life_marker(Space, CanonPath, Ref) :-
    atom(Space), !,
    assertz(import_life(Space, CanonPath, loading), Ref).
assert_import_life_marker(_, _, none).

erase_import_life_marker(none) :- !.
erase_import_life_marker(Ref) :-
    ( clause_property(Ref, erased) -> true ; erase(Ref) ).

finish_import_life(_, _, none, _) :- !.
finish_import_life(Space, CanonPath, Ref, exit) :- !,
    erase_import_life_marker(Ref),
    assertz(import_life(Space, CanonPath, loaded)).
finish_import_life(_, _, Ref, _) :-
    erase_import_life_marker(Ref).

run_with_import_life_marker(Space, CanonPath, Goal) :-
    setup_call_catcher_cleanup(
        assert_import_life_marker(Space, CanonPath, Ref),
        once(Goal),
        Catcher,
        finish_import_life(Space, CanonPath, Ref, Catcher)).

clear_import_life(Space, CanonPath) :-
    ( atom(Space) -> retractall(import_life(Space, CanonPath, _)) ; true ).

% Assert both markers before loading to break cycles. Retain them on success
% and retract them on failure. The recursive mutex serializes the loader graph.
import_once(Space, CanonPath, Goal) :-
    ( imported_metta_source(Space, CanonPath),
      import_life_current(Space, CanonPath)
      -> true
       ; retractall(imported_metta_source(Space, CanonPath)),
         clear_import_life(Space, CanonPath),
         run_with_loading_marker(
             imported_metta_source(Space, CanonPath),
             run_with_import_life_marker(Space, CanonPath, Goal)) ).

python_module_names(CanonPath, ModuleKey, ModuleName) :-
    crypto_data_hash(CanonPath, Hash, [algorithm(sha256)]),
    atom_concat('_petta_import_', Hash, ModuleKey),
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
    assertz(python_import_alias(ModuleName, ModuleKey)).

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

'import!'(Space, File, true) :- importer_helper(Space, File).
%`(: import! (-> Atom Atom Bool))` says both arguments arrive UNREDUCED, which
%is right: a module name is a name and evaluating it would look for a function
%called `lib_constraints`. So the forms a module name can take are resolved
%here rather than by the call site.
%
%`(library Name)` is the one form that needs it, and it used to work by
%accident: the call site evaluated the argument because the Atom mask was not
%honoured for builtins, so library/2 ran before import! ever saw it. With the
%mask honoured the form arrives whole, and resolving it is import!'s job.
importer_helper(Space, File0) :-
    resolve_module_form(File0, File),
    with_mutex(metta_loader, importer_helper_impl(Space, File)).

resolve_module_form(Form, Path) :-
    nonvar(Form), Form = [library, Name], !,
    library(Name, Path).
resolve_module_form(Form, Form).
importer_helper_impl(Space, File) :-
    ( python_import_file(File)
      -> resolve_python_import_path(File, CanonPath),
         import_once('$python', CanonPath, load_python_source(CanonPath))
       ; resolve_metta_import_path(File, CanonPath),
         import_once(Space, CanonPath,
                     load_imported_metta_file(CanonPath, _, Space)) ).

:- dynamic translator_rule/1.
'add-translator-rule!'(HV, _) :- var(HV), !,
                                 refuse_unbound_input('add-translator-rule!', 1).
'add-translator-rule!'(HV, true) :- ( translator_rule(HV)
                                      -> true ; assertz(translator_rule(HV)) ).

'remove-translator-rule!'(HV, _) :- var(HV), !,
                                    refuse_unbound_input('remove-translator-rule!', 1).
'remove-translator-rule!'(HV, true) :-
    must_be(nonvar, HV),
    retractall(translator_rule(HV)).

%%% Registration: %%%
:- dynamic fun/1, arity/2.
register_fun(N) :- must_be(atom, N),
                   ( fun(N) -> true
                   ; assertz(fun(N), Ref),
                     record_source_assertion(Ref),
                     repair_after_late_registration(N) ).

%The arities a loaded predicate is callable at, which is what a registration
%from Prolog has to record: every other route knows its arity from the
%equation head it just compiled and calls register_arity/2 with it directly.
%An operator's name answers current_predicate/1 at arities 1 and 2 whether or
%not a predicate of that name exists, so those two are not registrable.
%
%This walk used to live inside register_fun/1, guarded by "the name is new".
%A library registering 'norm'/3 for a name some space already defined at MeTTa
%arity 1 therefore recorded no arity at all, and incomplete_application_kind/3
%reads a missing arity as "not applied far enough", so (norm a b) compiled to a
%partial application. Reading it here instead means the arities are recorded
%for the registration that asked for them, whatever else knows the name
%[tested: a_registration_records_arities_for_a_name_that_is_already_a_function].
%Every arity the name is CALLABLE at, and callable means defined here rather
%than merely visible. The exclusion is not defensive: library(yall) exports
%//2 through //9 into user as its free-variables lambda, so probing
%current_predicate/1 alone recorded SEVEN arities for `/` where + and * have
%one. (/ 1 2 3) then compiled to a direct '/'(1,2,3,_) call, which is yall's
%lambda, and answered `type_error(lambda_free, 1)` where every other operator
%answers the engine's own function_input_arities naming the operator
%[tested: metta_registration_arities].
%
%imported_from/1 is the exact question, and the arity =< 2 clause below is the
%older half-answer to the same thing: it excluded 1/2 the TERM and nothing
%told it about 1/2 the lambda.
register_prolog_arities(N) :-
    forall(( current_predicate(N/Arity),
             \+ (current_op(_, _, N), Arity =< 2),
             \+ (current_op(_, _, N), imported_predicate(N, Arity)) ),
           register_arity(N, Arity)).

%Only for an OPERATOR, and the first attempt got that wrong: excluding every
%imported predicate dropped length/2, which is library(lists)'s and a
%perfectly good builtin, so (length ...) compiled to partial(length, [...])
%and four gates went red. An imported predicate is normal; an imported
%predicate whose name is also an OPERATOR is the collision.
imported_predicate(N, Arity) :-
    functor(Head, N, Arity),
    petta_engine_module(Engine),
    predicate_property(Engine:Head, imported_from(_)).

%Record each callable arity once, even when a function has many equations.
register_arity(N, Arity) :- ( arity(N, Arity) -> true
                            ; assertz(arity(N, Arity), Ref),
                              record_source_assertion(Ref) ).

%The module whose equations are in scope while a term is compiled or run. The
%default is &self's, which is where a program that names no space writes.
%
%The default is a fact read rather than a constant unified, one inference
%instead of none, because the alternative is writing '$petta_exec:&self' out
%here and having two places that decide the name
%[tested: metta_module_context:the_default_context_is_selfs_own_module].
current_metta_module(Module) :-
    ( nb_current('$petta_module', M) -> Module = M ; metta_self_module(Module) ).

%Skipping the switch when Module is already in force was tried and taken back
%out. It saved 4 inferences on every Python evaluation and cost 2 on every
%annotated typed call, which is the wrong side of that trade: the crossing
%happens once and the typed call happens in a loop. Measured 2026-08-16, the
%@m.define annotated tier of python/benchmarks/extension_cost.py went 20.00 to
%22.00 with the test in place, against m.fn 68.00 to 64.00.
%The argument is a MODULE, and refusing anything else is what keeps this
%honest now that a space and its module are different atoms. They used to be
%the same atom for every space but &self, so `with_metta_module('&pool', G)`
%worked by coincidence; today it would switch the context to a module nothing
%compiles into, every lookup would miss, and the goal would answer as if the
%space were empty. One indexed cache probe turns that into a refusal at the
%call [tested: metta_module_context:a_space_name_is_refused_where_a_module_is_asked].
with_metta_module(Module, Goal) :-
    (   metta_exec_module_prefix(Prefix), sub_atom(Module, 0, _, _, Prefix)
    ->  true
    ;   throw(error(type_error(metta_execution_module, Module),
                    context(with_metta_module/2,
                            'space_module/2 maps a space to the module its \c
                             clauses are in; pass that, not the space')))
    ),
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
%
%The engine's own list. It is a SEAM, declared multifile in ext_points.pl, so
%a library that introduces its own cancellation or budget signal adds a
%clause instead of being swallowed by the first recovery catch it meets
%[tested: a_librarys_own_control_signal_is_not_recovered_from].
control_exception(time_limit_exceeded).
control_exception(inference_limit_exceeded).
control_exception(petta_py_interrupted).
control_exception('$aborted').
control_exception(error(petta_py_time_limit(_), _)).
control_exception(error(petta_py_inference_limit(_), _)).
%The reserved seam envelopes for the same two signals: the shim declares
%every petta_py_exception kind control on the Python side, and these two
%are thrown by the ENGINE's own bound forms (inferences, with-pragma!),
%so the CLI must agree or a program could catch its own budget there and
%disarm the counter.
control_exception(error(petta_py_exception(time_limit, _), _)).
control_exception(error(petta_py_exception(inference_limit, _), _)).
control_exception(error(resource_error(_), _)).

%Keep the ISO Formal term because callers and the MeTTa catch form inspect it.
%Only the host context is replaced, so lists:min_list/3, is/2, and nb_setval/2
%cannot leak into a language-level diagnostic. Integer fast paths avoid the
%catch cost on valid arithmetic without letting float overflow escape. Over
%100,000 calls the guarded form used
%300,002 inferences against 300,003 directly, while an unconditional catch used
%400,002 [measured: guarded -1 and caught +99,999 inferences, 2026-08-15].
rethrow_metta_operation_error(_, Error) :- control_exception(Error), !,
                                            throw(Error).
rethrow_metta_operation_error(Operation, error(Formal, _)) :- !,
    throw(error(Formal,
                context(Operation, 'while evaluating MeTTa operation'))).
rethrow_metta_operation_error(_, Error) :- throw(Error).

throw_metta_type_error(Operation, Expected, Culprit) :-
    throw(error(type_error(Expected, Culprit),
                context(Operation, 'invalid MeTTa operation argument'))).

%The culprit in the message is the value the program wrote, so it reads as
%MeTTa: (State 5), not ['State',5]. The Formal term stays ISO, because
%callers and the MeTTa catch form inspect it, and the structured Python
%surface reads it too; only the rendering changes.
%
%prolog:message//1 is consulted before the formal-only
%prolog:error_message//1, and this clause matches the context PeTTa's own
%guards attach, so every other error SWI renders is untouched
%[source: SWI-Prolog 10.1 boot/messages.pl, translate_message/1]
%[tested: metta_operation_error_message].
%The context is matched in the body, not in the head: library(error) throws
%its type errors with an unbound context, which a head pattern would unify
%with and claim, renaming every unrelated type error in the process
%[tested: metta_operation_error_message:an_unrelated_type_error_is_untouched].
%petta_error_context(+Context, -Operation, +Detail) reads a context term
%WITHOUT writing to it. Matching context(Operation, Detail) in the head looks
%equivalent and is not: SWI's own errors carry context(PI, _) with the second
%argument UNBOUND, so unifying a detail atom into it succeeds and the clause
%then renders every ordinary error of that formal. This clause was hijacking
%all of them, which is where I16's "system:(is)/2: evaluable expected, found
%(/ foo 0)" came from: a library predicate's is/2 type error was being
%reported in PeTTa's operation vocabulary, naming an engine internal and a
%culprit the program never wrote [tested: metta_operation_errors,
%an_unrelated_type_error_keeps_swi_s_own_message].
petta_error_context(Context, Operation, Detail) :-
    nonvar(Context),
    Context = context(Operation, Actual),
    nonvar(Actual),
    Actual == Detail.

prolog:message(error(type_error(Expected, Culprit), Context)) -->
    { petta_error_context(Context, Operation, 'invalid MeTTa operation argument'),
      swrite(Culprit, CulpritText) },
    [ '~w: ~w expected, found ~w'-[Operation, Expected, CulpritText] ].
%The ISO formal stays existence_error(procedure, Name), so a program can catch
%it the standard way; only the wording changes, because SWI's default renders
%it as "procedure `f' does not exist", which says nothing about why a
%registration cares. What it costs is the reason worth printing: a name with
%no predicate records no arity, and incomplete_application_kind/3 then reads
%the missing arity as "not applied far enough", so the call compiles to a
%partial application instead of failing.
prolog:message(error(existence_error(procedure, Name), Context)) -->
    { petta_error_context(Context, _, 'no Prolog predicate of that name is loaded') },
    [ 'no predicate named ~w is loaded, so registering it would compile \c
       every call to it into a partial application rather than failing'-[Name] ].

%These builtins validate their own runtime inputs and provide their own error
%context. The translator may therefore bypass reflective input filtering when
%the builtin has not been overridden. Keep this list aligned with those guards.
runtime_type_guarded('+').
runtime_type_guarded('-').
runtime_type_guarded('*').
runtime_type_guarded('/').
runtime_type_guarded('%').
runtime_type_guarded('<').
%== and != carry their own guard, comparable_operands/3, which is exactly
%what their declared type (-> $a $a Bool) states, so the typed dispatch has
%nothing left to check. Classifying them here is what makes
%lib_builtin_types.metta affordable: with the file loaded, a workload calling
%== and != went from 102402 inferences to 181602, +77%, and back to 102402
%with these two lines [measured 2026-08-16]. Their own guard is cheaper than
%either, and free on two numbers: a thousand-iteration == loop is 4487.45
%inferences with and without it [measured 2026-08-19]. A user or named-space
%equation overriding either still gets the full typed dispatch, because
%runtime_guarded_builtin_call/1 requires the unmodified builtin.
%
%The declaration was (-> $a $b Bool), two independent variables, which
%constrained nothing and is why (== 1 "S") answered False. Upstream writes
%(-> $t $t Bool) [source: pinned stdlib.md via the arbiter, and measured from
%hyperon 0.2.10's own !(get-type ==) on 2026-08-19].
runtime_type_guarded('==').
runtime_type_guarded('!=').
runtime_type_guarded('>').
runtime_type_guarded('<=').
runtime_type_guarded('>=').
runtime_type_guarded(min).
runtime_type_guarded(max).
runtime_type_guarded(exp).
runtime_type_guarded('#+').
runtime_type_guarded('#-').
runtime_type_guarded('#*').
runtime_type_guarded('#div').
runtime_type_guarded('#//').
runtime_type_guarded('#mod').
runtime_type_guarded('#min').
runtime_type_guarded('#max').
runtime_type_guarded('#<').
runtime_type_guarded('#>').
runtime_type_guarded('#=').
runtime_type_guarded('#\\=').
runtime_type_guarded('#=<').
runtime_type_guarded('#>=').
runtime_type_guarded('pow-math').
runtime_type_guarded('sqrt-math').
runtime_type_guarded('abs-math').
runtime_type_guarded('log-math').
runtime_type_guarded('exp-math').
runtime_type_guarded('trunc-math').
runtime_type_guarded('ceil-math').
runtime_type_guarded('floor-math').
runtime_type_guarded('round-math').
runtime_type_guarded('sin-math').
runtime_type_guarded('cos-math').
runtime_type_guarded('tan-math').
runtime_type_guarded('asin-math').
runtime_type_guarded('acos-math').
runtime_type_guarded('atan-math').
runtime_type_guarded('isnan-math').
runtime_type_guarded('isinf-math').
runtime_type_guarded('min-atom').
runtime_type_guarded('max-atom').
runtime_type_guarded('random-int').
runtime_type_guarded('random-float').
runtime_type_guarded(and).
runtime_type_guarded(or).
runtime_type_guarded(not).
runtime_type_guarded(xor).
runtime_type_guarded(implies).

%The evaluator's catch-all: real errors take the recovery, control
%signals keep flying.
:- meta_predicate catch_recover(0, 0).
catch_recover(Goal, Recovery) :-
    catch(Goal, E, ( control_exception(E) -> throw(E) ; call(Recovery) )).

%Whether a symbol is callable from where we are: a process-wide function that
%no named equation module claims, a function this module defines, or one &self
%defines, since &self is shared. fun_scoped/1 summarizes non-user fun_in/2
%claims. A builtin or user-only function is therefore unambiguous in every
%space and avoids a current-module read in higher-order loops.
%fun_in/2 is only ever asserted by register_fun_in/2, which registers fun/1
%first, so fun_in implies fun. A name that is not a function therefore cannot
%be one here either, and one indexed lookup settles it: the old second clause
%went on to read current_metta_module/1 and two fun_in/2 facts before failing,
%for every non-function head the translator resolves
%[measured 2026-08-15: alpha-unique 4,050,778 to 3,750,772 inferences].
fun_here(F) :- fun(F),
               ( \+ fun_scoped(F) -> true
               ; current_metta_module(Module), fun_here_in(Module, F) ).

%The builtin fallback is what keeps (+ 1 2) working in &self after some other
%named space defines (= (+ $a $b) ...). fun_scoped(N) stops fun_here/1's first
%clause applying process-wide, and without this the name resolved nowhere: one
%named space turned + into inert data in every other space and in engines
%built afterwards [tested: metta_builtin_scoping].
fun_here_in(Module, F) :- (   fun_in(Module, F) -> true
                          ;   metta_self_module(Self), Module \== Self,
                              fun_in(Self, F) -> true
                          ;   builtin_fun(F) ).

%Register a function and record which module its clauses live in. fun/1 stays
%global because the translator consults it at compile time to decide whether a
%head is a call or data, and that decision has to hold wherever the term is
%compiled; fun_in/2 says where the clauses actually are, so a caller can ask
%whether *this* space defines a symbol rather than whether any space does.
:- dynamic fun_in/2, fun_scoped/1.
%A builtin is visible from every space, and stays visible when a named space
%defines its name. fun_in/2 cannot carry that: it means "an equation or a
%registered operation defines this here", which is exactly the test
%runtime_guarded_builtin_call/1 uses to decide a builtin was overridden. One
%fact for each meaning, so neither reading breaks the other.
:- dynamic builtin_fun/1.
register_builtin_fun(N) :- register_fun(N),
                           register_prolog_arities(N),
                           ( builtin_fun(N) -> true ; assertz(builtin_fun(N)) ).

register_fun_in(Module, N) :- register_fun(N),
                              ( fun_in(Module, N) -> true
                              ; assertz(fun_in(Module, N), FunInRef),
                                record_source_assertion(FunInRef) ),
                              ( metta_self_module(Module) -> true
                              ; fun_scoped(N) -> true
                              ; assertz(fun_scoped(N), ScopedRef),
                                record_source_assertion(ScopedRef) ).

unregister_fun_in(Module, N) :- retractall(fun_in(Module, N)),
                                metta_self_module(Self),
                                ( fun_in(Other, N), Other \== Self
                                  -> true ; retractall(fun_scoped(N)) ).

unregister_fun_everywhere(N) :- retractall(fun_in(_, N)),
                                retractall(fun_scoped(N)).
:- maplist(register_builtin_fun, [superpose, empty, let, 'let*', '+','-','*','/', '%', min, max, 'change-state!', 'get-state', 'bind!',
                          '<','>','==', '!=', '=', '=?', '<=', '>=', and, or, xor, implies, not, exp,
                          'first-from-pair', 'second-from-pair', 'car-atom', 'cdr-atom', 'unique-atom', 'alpha-unique-atom',
                          repr, repra, parse, 'pretty-atom', 'println!', 'readln!', 'read-form!', 'sread-command', test, 'test-no-answer', assert, atom_concat, atom_chars, copy_term, term_hash,
                          foldl, first, last, append, length, 'size-atom', sort, msort, member, 'is-member', 'is-alpha-member', 'exclude-item', list_to_set, maplist, eval, evalc, reduce, 'import!',
                          'git-import!',
                          'add-atom', 'remove-atom', 'add-atoms', 'add-reduct', 'add-reducts', 'get-atoms', match, 'is-var', 'is-ground', 'is-expr', 'is-space',
                          decons, 'decons-atom', noeval, 'new-space',
                          'py-call', 'py-atom', 'py-dot',
                          'py-list', 'py-tuple', 'py-dict', 'py-iter',
                          'get-type', 'get-type-space', 'get-metatype', '=alpha', sread, cons, reverse,
                          'get-doc', 'get-doc-space', 'help!', documented, 'documented-space',
                          'defined-name', undocumented, 'undocumented-space',
                          '#+','#-','#*','#div','#//','#mod','#min','#max','#<','#>','#=','#\\=','#=<','#>=',
                          'union-atom', 'cons-atom', 'intersection-atom', 'subtraction-atom', 'index-atom', id,
                          'pow-math', 'sqrt-math', 'sort-atom','abs-math', 'log-math', 'exp-math', 'trunc-math', 'ceil-math',
                          'floor-math', 'round-math', 'sin-math', 'cos-math', 'tan-math', 'asin-math','random-int','random-float',
                          'acos-math', 'atan-math', 'isnan-math', 'isinf-math', 'min-atom', 'max-atom',
                          'foldl-atom', 'map-atom', 'filter-atom','current-time','format-time', 'context-space', library, exists_file,
                          sleep, 'pragma!', metta,
                          import_prolog_function, check_prolog_function_names, import_prolog_functions,
                          'Predicate', callPredicate, assertaPredicate, assertzPredicate, retractPredicate,
                          'add-translator-rule!', 'remove-translator-rule!', argv,
                          register_metta_library_path,
                          dif, 'residual-goals']).

%A backend's own builtins, registered here because this is where the engine's
%are and the order matters. The NAMES are the backend's: it declares them in
%the file that defines them, so they exist exactly when the predicates behind
%them do. That conditionality used to be an argv test in this file, which meant
%the engine had to know both that MORK had builtins and what they were called.
%
%Registering a name whose predicate is absent records no arity, and
%incomplete_application_kind/3 reads "no arity" as "not applied far enough":
%every call to it then compiled to a partial application, so (mm2-exec &mork 1)
%answered (partial mm2-exec (&mork 1)) instead of running or failing. Declaring
%the names beside the predicates is what makes that unable to happen again.
:- forall(metta_backend_builtin(Name), register_builtin_fun(Name)).


%%%%%%%%%% The engine's own type surface %%%%%%%%%%
%
%Without this, `get-type` misreported the engine to every tool that reads it.
%`!=` IS a builtin, IS registered and IS declared (: != (-> $a $b Bool)) in
%lib/lib_builtin_types.metta, but with nothing loading that file
%`(get-type !=)` answered %Undefined% for an operation that works. Nothing was
%missing; the type surface was simply not connected, and a reader like the
%metta-lsp port has no way to tell "this has no type" from "this has a type
%nobody loaded".
%
%FACTS RATHER THAN ATOMS IN &self, and that is the whole design decision.
%Loading the file into &self was tried first and it changes what every program
%SEES OF ITS OWN SPACE: `(match &self (: $what $type) ...)` then answers 41
%engine declarations alongside the program's own, which broke
%tests/regression/repro3_failed_specialization_self_leak.metta immediately.
%The engine's types belong where the type system reads them and nowhere a
%program enumerating its own atoms can trip over them.
%
%LAST, so a user wins. get_type_candidate/2 tries the intrinsic types, the
%function's arrow, the element-wise reading and &self's own declarations
%before reaching here, so `(: + (-> Foo Bar))` written by a program is
%answered ahead of the engine's and this only ever fills a gap.
%
%ONE SOURCE OF TRUTH: the facts are built by parsing lib_builtin_types.metta
%at boot, so the file a program can still import explicitly and the table the
%engine answers from cannot drift apart.
:- dynamic builtin_type_declaration/2.

load_builtin_type_surface :-
    library('lib_builtin_types.metta', Path),
    exists_file(Path),
    !,
    read_file_to_string(Path, Text, []),
    parse_metta_source(Text, Forms),
    forall(( member(parsed(expression, _, [':', Name, Type]), Forms),
             atom(Name) ),
           ( builtin_type_declaration(Name, Type)
             -> true
             ;  assertz(builtin_type_declaration(Name, Type)) )),
    %Derived from the surface just loaded rather than by a separate
    %initialization, because two initialization/1 goals do not reliably order
    %against each other and an empty index is a silent loss: a constructor like
    %Error would quietly evaluate the argument it exists to carry.
    index_masking_data_heads.
load_builtin_type_surface :- index_masking_data_heads.

%%%%%%%%%% The engine's prelude %%%%%%%%%%
%
%src/prelude.metta holds standard vocabulary promoted from the libraries:
%forms every program may use with no import!, compiled here at startup by
%the same translator that compiles a program's own equations. The clauses
%land in the base tier and each head registers as a builtin, so the names
%are visible from every space and shadowable per named space exactly as
%builtins are; the ATOMS are stored in no space at all, so a program
%enumerating &self sees only its own writes, the same design decision
%load_builtin_type_surface records above for the type surface.
%
%Declarations go to prelude_type_declaration/2, a third register beside
%type_declaration/2 (what the program declared) and
%builtin_type_declaration/2 (the engine's Prolog surface). It is consulted
%on the FUNCTION path, which builtin_type_declaration deliberately is not:
%that register describes arguments a caller writes for predicates
%underneath (the maplist lesson, documented at call_site_type_chains/2),
%while a prelude declaration is an ordinary MeTTa declaration for an
%ordinary compiled equation, so honouring it at call sites is exactly
%right, and it is what makes an Atom parameter like assertEqualToResult's
%arrive unevaluated. A program's own declaration is read first, so a user
%redeclaration wins, the same order the type surface keeps.
%
%Two passes, because the file may use a name before defining it
%(type-cast calls type-cast-holds, defined below it): every equation head
%registers first, then every form compiles, so a forward reference
%compiles as the call it is. The filereader solves the same problem with
%a repair pass; the prelude is small enough to pre-register instead.
:- dynamic prelude_type_declaration/2.
:- dynamic petta_engine_src_dir/1.
:- dynamic prelude_owned/1.
:- dynamic prelude_clause_ref/2.
%Which builtin_type_declaration/2 rows the prelude PUT THERE, as opposed to
%found there. The two registers overlap once a name needs its Atom mask
%honoured at call sites AND belongs to the engine's reported type surface:
%get-type is declared by lib_builtin_types.metta and again by src/prelude.metta,
%for the two different readers. Without this ledger the prelude's eviction
%would retract a row the FILE owns, since the two rows are identical and
%retractall/1 cannot tell them apart.
:- dynamic prelude_wrote_builtin_type/2.

%A user definition WINS over the prelude, entirely. When &self compiles
%an equation for a name the prelude owns, the prelude's clauses and
%declarations for that name are evicted first, so the program's own
%definition answers alone, exactly as it did before the name was
%promoted (examples/types/matchtypes.metta defines its own match-types
%and must keep meaning ITS match-types). Additive answers would be the
%non-exclusive-equations reading, but the prelude is engine vocabulary,
%not part of the program, and the house rule everywhere else on this
%boundary is that the user's word replaces the engine's: get-type reads
%a program's declaration ahead of the surface, prelude_type_declaration
%is consulted last. Eviction is one-way; removing the user's equation
%later does not resurrect the prelude's, the same as redefining any
%function. Named spaces need none of this: their clauses shadow through
%their own module already, the builtin-override rule.
evict_prelude_definition(FAtom) :-
    (   retract(prelude_owned(FAtom))
    ->  forall(retract(prelude_clause_ref(FAtom, Ref)), erase(Ref)),
        retract_prelude_declarations(FAtom),
        retractall(prelude_doc_atom(FAtom, _)),
        %The prelude is the base tier's, so its eviction is &self's change.
        metta_self_module(Self),
        function_changed(Self, FAtom)
    ;   true
    ).

%The ledger rows say exactly which builtin_type_declaration entries are
%the prelude's, so eviction purges both stores and nothing else. A row the
%prelude found already written by lib_builtin_types.metta stays, because it
%was never the prelude's to remove.
retract_prelude_declarations(Name) :-
    forall(retract(prelude_type_declaration(Name, Type)),
           (   retract(prelude_wrote_builtin_type(Name, Type))
           ->  retractall(builtin_type_declaration(Name, Type))
           ;   true
           )).

%The declaration half of the same rule, for the loader's door: a ':'
%atom a file writes into the base tier replaces the prelude's
%declaration for that name, so the compile-time findall over
%type chains sees ONE authority, the user's.
evict_prelude_declaration(Space, [':', Name, _]) :-
    atom(Name),
    Space == '&self',
    !,
    retract_prelude_declarations(Name).
evict_prelude_declaration(_, _).

:- prolog_load_context(directory, Dir),
   (   petta_engine_src_dir(_) -> true
   ;   assertz(petta_engine_src_dir(Dir))
   ).

%The prelude compiles SILENTLY whatever the session's verbosity: these
%are engine internals loading at boot, and a --verbose user asking to see
%their program's compiled clauses is not asking for the engine's own.
%asserta so the silence wins over an already-asserted silent(false), and
%the cleanup erases exactly the clause added here.
load_engine_prelude :-
    setup_call_cleanup(asserta(silent(true), Ref),
                       load_engine_prelude_forms,
                       erase(Ref)).

load_engine_prelude_forms :-
    petta_engine_src_dir(Dir),
    directory_file_path(Dir, 'prelude.metta', Path),
    (   exists_file(Path)
    ->  true
    ;   throw(error(existence_error(source_sink, Path),
                    context(load_engine_prelude/0,
                            'src/prelude.metta is part of the engine')))
    ),
    read_file_to_string(Path, Text, []),
    parse_metta_source(Text, Forms),
    %Re-loading restores only what eviction removed: a name still owned
    %keeps every clause it has, and its forms are skipped WHOLE (a name
    %may carry several equations, so the skip is per name, decided
    %before anything loads). First load: nothing is owned, nothing
    %skips.
    findall(Owned, prelude_owned(Owned), OwnedBefore),
    %Arity registers in pass one WITH the name: a registered name with no
    %recorded arity compiles a later call site as a partial application
    %(the backends note beside metta_backend_builtin/1 records the same
    %trap), and type-cast calls type-cast-check before pass two reaches
    %its equation.
    forall(( member(parsed(function, _, [=, [FAtom|W], _]), Forms),
             atom(FAtom) ),
           ( register_builtin_fun(FAtom),
             length(W, N),
             Arity is N + 1,
             register_arity(FAtom, Arity) )),
    forall(member(parsed(Kind, Src, Term), Forms),
           (   Term = [=, [Skip|_], _],
               memberchk(Skip, OwnedBefore)
           ->  true
           ;   load_prelude_form(Kind, Src, Term)
           )).

%A declaration lands in TWO stores: prelude_type_declaration/2 is the
%masking tier the compiler reads and the eviction ledger, and
%builtin_type_declaration/2 is where get-type already looks, so the
%get-type path gains no new clause to try (measured: an extra candidate
%clause cost ~6 inferences per compiled run() call, 2026-08-18). The
%ledger is what lets eviction purge BOTH stores exactly.
load_prelude_form(expression, _, [':', Name, Type]) :-
    atom(Name), !,
    (   prelude_type_declaration(Name, Type) -> true
    ;   assertz(prelude_type_declaration(Name, Type)),
        %lib_builtin_types.metta loads FIRST and may already carry the same
        %declaration, which is the case for a builtin the prelude declares
        %only so the CALL SITE honours its Atom mask: get-type is in both
        %files for two different readers. A second identical fact would give
        %the engine's type surface a duplicate row, so the prelude writes one
        %only when it is the one putting it there, and records that it did.
        (   builtin_type_declaration(Name, Type) -> true
        ;   assertz(builtin_type_declaration(Name, Type)),
            assertz(prelude_wrote_builtin_type(Name, Type))
        )
    ).
%A (@doc ...) form in the prelude lands in the engine's doc register,
%where get-doc's first tier reads it; the prelude documents its own
%vocabulary the way lib_doc documented its own, because a vocabulary
%that reports undocumented names and has none of its own would be
%telling other people to do what it does not.
load_prelude_form(expression, _, Term) :-
    Term = ['@doc', Name | _], atom(Name), !,
    (   prelude_doc_atom(Name, Term) -> true
    ;   assertz(prelude_doc_atom(Name, Term))
    ).
load_prelude_form(function, _, Term) :-
    Term = [=, [FAtom|W], _], atom(FAtom), !,
    length(W, N),
    Arity is N + 1,
    register_arity(FAtom, Arity),
    %The prelude is the base tier's own vocabulary, so it compiles into &self's
    %module: every other space inherits it from there, and a program that
    %redefines one of its names evicts it exactly as before.
    metta_self_module(Self),
    once(with_metta_module(Self, translate_clause(Term, Clause))),
    assert_function_clause(Self, Clause, Ref),
    assertz(prelude_clause_ref(FAtom, Ref)),
    (   prelude_owned(FAtom) -> true
    ;   assertz(prelude_owned(FAtom))
    ).
%Anything else is refused rather than skipped: a prelude form that is
%neither a declaration nor an equation is a mistake in the engine's own
%source, and silently ignoring it would ship a vocabulary hole.
load_prelude_form(Kind, Src, _) :-
    throw(error(domain_error(prelude_form, Kind),
                context(load_engine_prelude/0, Src))).

%One initialization goal for both, in this order, because initialization/1
%goals do not reliably order against each other (the note above) and the
%prelude's bodies mention constructors like Error whose Atom masking reads
%the surface loaded first.
:- initialization((protect_metta_exec_modules,
                   load_builtin_type_surface, load_engine_prelude)).
