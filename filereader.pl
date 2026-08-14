% Purpose: read MeTTa source, split it into complete top-level forms, and
% dispatch each parsed form to the evaluator.
% Guarantees:
%   - A parsed form that cannot translate is not reported as a syntax error
%     [tested 2026-08-14: filereader_translation_errors].
%   - top_forms//2 ignores comment text and keeps parentheses inside escaped
%     string quotes inside their form [tested 2026-08-14:
%     filereader_form_splitter].
%   - Loader diagnostics contain ANSI escapes only on terminal streams
%     [tested 2026-08-14: filereader_terminal_output].
%   - A failed source load removes compiler metadata and generated predicates,
%     and does not repair existing callers against definitions that rolled back
%     [tested 2026-08-14: filereader_source_rollback].
%   - Direct source strings compile equations into their target named space
%     [tested 2026-08-14:
%     tracer:function_defined_in_named_trace_stays_in_that_space].
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- use_module(library(readutil)). % read_file_to_string/3
:- use_module(library(ansi_term)). % terminal-aware diagnostic colors
:- use_module(library(pcre)). % re_replace/4
:- use_module(library(zlib)). % gzopen/3, .gz program files
%Every compiled clause's source equation; asserted here and by
%add-atom/3, read by removal and the tracer, so it must exist before
%the first function ever compiles (a virgin-engine remove-atom read it
%undefined and crashed).
:- dynamic translated_from/2.

:- multifile prolog:error_message//1.

prolog:error_message(petta_translation_failed(Form)) -->
    [ 'Could not translate MeTTa form: ~p'-[Form] ].
:- current_prolog_flag(argv, Args), ( (memberchk(silent, Args) ; memberchk('--silent', Args) ; memberchk('-s', Args))
                                      -> assertz(silent(true)) ; assertz(silent(false)) ).
:- dynamic working_dir/1.
:- dynamic compiled_metta_source/1.
:- thread_local active_source_load/1.
:- dynamic source_load_assertion/2.
:- dynamic source_load_repair/2.

push_working_dir(Filename) :- file_directory_name(Filename, Dir0),
                              ( absolute_file_name(Dir0, Dir, [file_type(directory), file_errors(fail)])
                                -> true
                                 ; Dir = Dir0 ),
                              asserta(working_dir(Dir)).

pop_working_dir :- retract(working_dir(_)), !.
pop_working_dir.

%Read Filename into string S and process it (S holds MeTTa code):
load_metta_file(Filename, Results) :- load_metta_file(Filename, Results, '&self').
load_metta_file(Filename, Results, Space) :-
    with_mutex(metta_loader,
               catch(load_entry_metta_file(Filename, Results, Space),
                     Error,
                     rethrow_metta_file_error(Filename, Error))).

load_entry_metta_file(Filename, Results, Space) :-
    absolute_file_name(Filename, CanonPath, [access(read)]),
    import_once(Space, CanonPath,
                load_imported_metta_file(CanonPath, Results, Space)),
    ( var(Results) -> Results = [] ; true ).

load_metta_file_impl(Filename, Results, Space) :-
    load_metta_file_impl(Filename, Results, Space, compile).

load_metta_file_impl(Filename, Results, Space, CompileMode) :-
    setup_call_cleanup(push_working_dir(Filename),
                       ( read_metta_source(Filename, S),
                         process_metta_string(S, Results, Space, CompileMode) ),
                       pop_working_dir).

% A .gz program reads through the engine's own zlib stream. Any other path
% reads plain text, so imports and the CLI share the same source reader.
read_metta_source(Filename, S) :-
    ( file_name_extension(_, gz, Filename)
      -> catch(setup_call_cleanup(gzopen(Filename, read, In),
                                  read_string(In, _, S),
                                  close(In)),
               error(Type, _),
               throw(error(Type, context(Filename,
                                         'while reading gzip-compressed MeTTa source'))))
    ; read_file_to_string(Filename, S, []) ).

% Function clauses are global Prolog predicates, while source atoms belong to a
% particular MeTTa space.  Coordinate compilation by canonical source path so
% the clauses are emitted once, then populate every requested space separately.
load_imported_metta_file(Filename, Results, Space) :-
    catch(load_imported_metta_file_impl(Filename, Results, Space),
          Error,
          rethrow_metta_file_error(Filename, Error)).

load_imported_metta_file_impl(Filename, Results, Space) :-
    ( compiled_metta_source(Filename)
      -> load_metta_file_impl(Filename, Results, Space, populate)
       ; run_with_loading_marker(
             compiled_metta_source(Filename),
             run_new_source_load(Filename, Results, Space)) ).

run_new_source_load(Filename, Results, Space) :-
    gensym(source_load_, LoadId),
    setup_call_catcher_cleanup(
        asserta(active_source_load(LoadId), ContextRef),
        once(( load_metta_file_impl(Filename, Results, Space, compile),
               run_source_repairs(LoadId) )),
        Catcher,
        ( erase(ContextRef),
          retractall(source_load_repair(LoadId, _)),
          ( Catcher == exit
            -> retractall(source_load_assertion(LoadId, _))
             ; rollback_source_load(LoadId) ) )).

run_with_loading_marker(Marker, Goal) :-
    setup_call_catcher_cleanup(
        assertz(Marker, Ref),
        once(Goal),
        Catcher,
        ( Catcher == exit -> true ; erase(Ref) )).

record_source_assertion(Ref) :-
    active_source_load(LoadId), !,
    assertz(source_load_assertion(LoadId, Ref)).
record_source_assertion(_).

run_source_repairs(LoadId) :-
    findall(F, source_load_repair(LoadId, F), Functions0),
    sort(Functions0, Functions),
    transaction(forall(member(F, Functions),
                       repair_stale_definitions_impl(F))).

rollback_source_load(LoadId) :-
    findall(Ref, retract(source_load_assertion(LoadId, Ref)), Refs),
    reverse(Refs, ReverseRefs),
    forall(member(Ref, ReverseRefs), catch(erase(Ref), _, true)).

rethrow_metta_file_error(_, Error) :- control_exception(Error), !,
                                      throw(Error).
rethrow_metta_file_error(_, Error) :- Error = error(_, context(_, _)), !,
                                      throw(Error).
rethrow_metta_file_error(Filename, error(Type, _)) :- !,
                                                      throw(error(Type, context(Filename, 'while loading MeTTa file'))).
rethrow_metta_file_error(_, Error) :- throw(Error).

%Extract function definitions, call invocations, and S-expressions part of &self space:
process_metta_string(S, Results) :- process_metta_string(S, Results, '&self').
process_metta_string(S, Results, Space) :-
    with_mutex(metta_loader,
               process_direct_metta_string(S, Results, Space)).
process_direct_metta_string(S, Results, Space) :-
    prepare_metta_source(S, ParsedForms),
    maplist(process_form(Space), ParsedForms, ResultsList), !,
    append(ResultsList, Results).
process_metta_string(S, Results, Space, CompileMode) :-
    prepare_metta_source(S, ParsedForms),
    maplist(process_form(Space, CompileMode), ParsedForms, ResultsList), !,
    append(ResultsList, Results).

prepare_metta_source(S, ParsedForms) :-
    parse_metta_source(S, ParsedForms),
    register_parsed_signatures(ParsedForms),
    % Pinned git dependencies declared in this file are fetched before any of
    % its forms run (gitimport.pl).
    acquire_declared_dependencies(ParsedForms).

parse_metta_source(S, ParsedForms) :-
    string_codes(S, Cs),
    strip(Cs, outside, Codes),
    phrase(top_forms(Forms, 1), Codes),
    maplist(parse_form, Forms, ParsedForms).

% Register the complete signature set before repairing callers.  Translating a
% caller while only the first overload is visible can otherwise leave it stale.
register_parsed_signatures(ParsedForms) :-
    findall(F-Arity,
            ( member(parsed(function, _, [=, [F|Args], _]), ParsedForms),
              length(Args, InputArity),
              Arity is InputArity + 1 ),
            Signatures),
    register_function_signatures(Signatures).

register_function_signature(F, Arity) :-
    register_function_signatures([F-Arity]).

register_function_signatures(Signatures0) :-
    sort(Signatures0, Signatures),
    findall(F,
            ( member(F-Arity, Signatures),
              \+ arity(F, Arity) ),
            NewArityNames0),
    forall(member(F-Arity, Signatures),
           ( arity(F, Arity) -> true
             ; assertz(arity(F, Arity), Ref),
               record_source_assertion(Ref) )),
    findall(F, member(F-_, Signatures), Names0),
    sort(Names0, Names),
    findall(F, (member(F, Names), \+ fun(F)), NewFunNames),
    forall(member(F, Names),
           ( warn_if_executed_as_symbol(F),
             ensure_fun_registered(F) )),
    append(NewArityNames0, NewFunNames, RepairNames0),
    sort(RepairNames0, RepairNames),
    forall(member(F, RepairNames), repair_after_late_registration(F)).

ensure_fun_registered(N) :- fun(N), !.
ensure_fun_registered(N) :-
    assertz(fun(N), FunRef),
    record_source_assertion(FunRef),
    forall(( current_predicate(N/Arity),
             \+ (current_op(_, _, N), Arity =< 2) ),
           ( arity(N, Arity) -> true
             ; assertz(arity(N, Arity), ArityRef),
               record_source_assertion(ArityRef) )).

%An expression that already executed compiled F as plain data; that execution cannot
%be repaired retroactively, so flag it when F now arrives through a parsed definition:
warn_if_executed_as_symbol(F) :- \+ fun(F), symbol_head(F, runnable), !,
                                 format(user_error, "Warning: ~w is defined or imported after already being used; earlier expressions treat it as a plain symbol. Move the import or definition above the first use.~n", [F]).
warn_if_executed_as_symbol(_).

%A function arriving after its name was already compiled as plain data in stored
%definitions: recompile those definitions from their source terms, so import order
%cannot change what a definition means:
repair_after_late_registration(F) :-
    ( symbol_head(F, clause) -> schedule_definition_repair(F) ; true ).

schedule_definition_repair(F) :-
    active_source_load(LoadId), !,
    ( source_load_repair(LoadId, F) -> true
    ; assertz(source_load_repair(LoadId, F)) ).
schedule_definition_repair(F) :-
    repair_stale_definitions(F).

repair_stale_definitions(F) :-
    transaction(repair_stale_definitions_impl(F)).

repair_stale_definitions_impl(F) :-
    findall(G,
            ( translated_from(_, [=, [G|_], Body]),
              atom(G),
              uses_as_data(F, Body) ),
            Functions0),
    sort(Functions0, Functions),
    forall(member(G, Functions), recompile_function_impl(G)).

%Rebuild every clause of G from its stored source terms. Erasing and re-appending each
%tracked clause in assertion order keeps their relative order; clauses asserted through
%Prolog interop are not tracked and would end up before the rebuilt ones:
recompile_function(G) :-
    transaction(recompile_function_impl(G)).

recompile_function_impl(G) :-
    findall(compiled(Ref, Module, Term),
            ( translated_from(Ref, Term),
              Term = [=, [G0|_], _],
              G0 == G,
              clause_property(Ref, module(Module)) ),
            Clauses),
    forall(member(compiled(Ref, _, Term), Clauses),
           ( erase(Ref),
             retract(translated_from(Ref, Term)) )),
    clear_fun_meta(G),
    forall(member(compiled(_, Module, Term), Clauses),
           ( copy_term(Term, Fresh),
             once(with_metta_module(Module,
                                    translate_clause(Fresh, Clause))),
             assertz(Module:Clause, NewRef),
             record_source_assertion(NewRef),
             assertz(translated_from(NewRef, Term), SourceRef),
             record_source_assertion(SourceRef) )),
    invalidate_specializations(G).

%True if the term contains a call-shaped (list-head) occurrence of F:
uses_as_data(F, Term) :- nonvar(Term),
                         Term = [H|Args],
                         ( H == F -> true
                         ; uses_as_data(F, H) -> true
                         ; uses_as_data_args(F, Args) ).
uses_as_data_args(F, Args) :- nonvar(Args),
                              Args = [A|Rest],
                              ( uses_as_data(F, A) -> true ; uses_as_data_args(F, Rest) ).

% First pass converts MeTTa to Prolog terms without mutating registration state.
parse_form(form(S), parsed(T, S, Term)) :- sread(S, Term),
                                           ( Term = [=, [F|_], _], atom(F) -> T=function
                                                                           ; T=expression ).
parse_form(runnable(S), parsed(runnable, S, Term)) :- sread(S, Term).

% process_form/3 is the direct-string path used by named Python spaces. File
% loads use process_form/4 so source clauses compile once while their atoms are
% populated into each target space.
process_form(Space, parsed(expression, _, Term), []) :-
    'add-atom'(Space, Term, true),
    print_expression_form(Term).
process_form(Space, parsed(runnable, FormStr, Term), Result) :-
    bind_python_calls(Term, BoundTerm),
    space_module(Space, Module),
    with_metta_module(Module,
                      translate_runnable_expr([collapse, BoundTerm], Goals, Result)),
    print_runnable_form(FormStr, Goals),
    call_goals_in(Module, Goals).
process_form(Space, parsed(function, FormStr, Term), []) :-
    Term = [=, [F|Args], _],
    must_be(atom, F),
    length(Args, InputArity),
    Arity is InputArity + 1,
    register_function_signature(F, Arity),
    add_sexp(Space, Term, SpaceRef),
    record_source_assertion(SpaceRef),
    space_module(Space, Module),
    register_fun_in(Module, F),
    bind_python_calls(Term, BoundTerm),
    once(with_metta_module(Module, translate_clause(BoundTerm, Clause))),
    assertz(Module:Clause, Ref),
    record_source_assertion(Ref),
    assertz(translated_from(Ref, BoundTerm), SourceRef),
    record_source_assertion(SourceRef),
    forall(metta_on_function_changed(F), true),
    print_function_form(FormStr, Ref).
process_form(_, In, _) :-
    throw(error(petta_translation_failed(In),
                context(process_form/3, 'could not translate MeTTa form'))).

% The loader records every asserted clause reference. A later source error can
% then erase the whole partial load and leave the file retryable.
process_form(Space, _, parsed(expression, _, Term), []) :-
    add_sexp(Space, Term, SpaceRef),
    record_source_assertion(SpaceRef),
    print_expression_form(Term).
process_form(Space, _, parsed(runnable, FormStr, Term), Result) :-
    bind_python_calls(Term, BoundTerm),
    space_module(Space, Module),
    with_metta_module(Module,
                      translate_runnable_expr([collapse, BoundTerm], Goals, Result)),
    print_runnable_form(FormStr, Goals),
    call_goals_in(Module, Goals).
process_form(Space, populate, parsed(function, _, Term), []) :-
    add_sexp(Space, Term, SpaceRef),
    record_source_assertion(SpaceRef).
process_form(Space, compile, parsed(function, FormStr, Term), []) :-
    add_sexp(Space, Term, SpaceRef),
    record_source_assertion(SpaceRef),
    bind_python_calls(Term, BoundTerm),
    BoundTerm = [=, [F|_], _],
    once(with_metta_module(user, translate_clause(BoundTerm, Clause))),
    assertz(user:Clause, Ref),
    record_source_assertion(Ref),
    assertz(translated_from(Ref, BoundTerm), SourceRef),
    record_source_assertion(SourceRef),
    forall(metta_on_function_changed(F), true),
    print_function_form(FormStr, Ref).
process_form(_, _, In, _) :-
    throw(error(petta_translation_failed(In),
                context(process_form/4, 'could not translate MeTTa form'))).

print_expression_form(_) :- silent(true), !.
print_expression_form(Term) :-
    swrite(Term, STerm),
    ansi_format([fg(yellow)], "--> metta sexpr -->~n", []),
    ansi_format([fg(cyan)], "~w~n", [STerm]),
    ansi_format([fg(yellow)], "^^^^^^^^^^^^^^^^^^^~n", []).

print_runnable_form(_, _) :- silent(true), !.
print_runnable_form(FormStr, Goals) :-
    ansi_format([fg(yellow)], "--> metta runnable  -->~n", []),
    ansi_format([fg(cyan)], "!~w~n", [FormStr]),
    ansi_format([fg(yellow)], "-->  prolog goal  -->", []),
    ansi_format([fg(magenta)], " ~n", []),
    forall(member(G, Goals),
           ansi_format([fg(magenta)], "~@", [portray_clause((:- G))])),
    ansi_format([fg(yellow)], "^^^^^^^^^^^^^^^^^^^^^^^~n", []).

print_function_form(_, _) :- silent(true), !.
print_function_form(FormStr, Ref) :-
    ansi_format([fg(yellow)], "--> metta function -->~n", []),
    ansi_format([fg(cyan)], "~w~n", [FormStr]),
    ansi_format([fg(yellow)], "--> prolog clause -->~n", []),
    clause(Head, Body, Ref),
    ( Body == true -> Show = Head ; Show = (Head :- Body) ),
    ansi_format([fg(green)], "~@", [portray_clause(current_output, Show)]),
    ansi_format([fg(yellow)], "^^^^^^^^^^^^^^^^^^^^^^~n", []).

%Like blanks but counts newlines:
newlines(C0, C2) --> blanks_to_nl, !, {C1 is C0+1}, newlines(C1,C2).
newlines(C, C) --> blanks.

%Collect characters until all parentheses are balanced (depth 0), accumulating codes, and also counting newlines:
grab_until_balanced(D, Acc, Cs, LC0, LC2, State) --> [C],
    { string_state(State, C, State1),
      ( State = outside -> ( C=0'( -> D1 is D+1
                                  ; C=0') -> D1 is D-1
                                           ; D1 = D )
                        ; D1 = D ),
      Acc1=[C|Acc],
      ( C=10 -> LC1 is LC0+1 ; LC1 = LC0 ) },
    ( { D1=:=0, State1=outside } -> { reverse(Acc1,Cs), LC2 = LC1 }
                                    ; grab_until_balanced(D1,Acc1,Cs,LC1,LC2,State1) ).

%Read a balanced (...) block if available, turn into string, then continue with rest, ignoring comments:
read_form_open(_) --> "(", !.
read_form_open(LC) -->
    string_without("\n", Rest),
    { format(atom(Msg), "expected '(' or '!(', line ~w:~n~s", [LC, Rest]),
      throw(error(syntax_error(Msg), none)) }.

read_balanced_form(LC, Cs, LC2) -->
    grab_until_balanced(1, [0'(], Cs, LC, LC2, outside), !.
read_balanced_form(LC, _, _) -->
    string_without("\n", Rest),
    { format(atom(Msg), "missing ')', starting at line ~w:~n~s", [LC, Rest]),
      throw(error(syntax_error(Msg), none)) }.

top_forms([],_) --> blanks, eos.
top_forms([Term|Fs], LC0) --> newlines(LC0, LC1),
                              ( "!" -> {Tag = runnable} ; {Tag = form} ),
                              read_form_open(LC1),
                              read_balanced_form(LC1, Cs, LC2),
                              { string_codes(FormStr, Cs), Term =.. [Tag, FormStr] },
                              top_forms(Fs, LC2).
