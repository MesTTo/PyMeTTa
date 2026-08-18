% Purpose: read MeTTa source, split it into complete top-level forms, and
% dispatch each parsed form to the evaluator.
% Guarantees:
%   - A parsed form that cannot translate is not reported as a syntax error
%     [tested 2026-08-14: filereader_translation_errors].
%   - top_forms//2 ignores comment text and keeps parentheses inside escaped
%     string quotes inside their form [tested 2026-08-15:
%     filereader_form_splitter].
%   - parse_metta_source/2 consumes comments in its grammars without building a
%     stripped source copy [measured: 7,736,802 versus 8,874,582 inferences for
%     twenty parses of 48,786 codes, 2026-08-15].
%   - Loader diagnostics contain ANSI escapes only on terminal streams
%     [tested 2026-08-14: filereader_terminal_output].
%   - A type declaration that cannot type a function the same source defines
%     is refused before any of that source's forms run [tested 2026-08-16:
%     filereader_untypable_declaration].
%   - A failed source load removes compiler metadata and generated predicates,
%     and does not repair existing callers against definitions that rolled back
%     [tested 2026-08-14: filereader_source_rollback].
%   - Direct source strings compile equations into their target named space
%     [tested 2026-08-14:
%     tracer:function_defined_in_named_trace_stays_in_that_space].
%   - File functions remain a global fallback when a named space defines the
%     same symbol [tested 2026-08-14: filereader_global_function_scope].
%   - prepare_parsed_forms/1 is the ONE definition of what a source does before
%     any of its own forms run, so a reader that parses for itself
%     (python/petta/shim.pl does, to keep one answer group per directive) gets
%     the same signature set registered up front, and the same refusal of a
%     declaration that cannot type what the source defines, rather than a
%     second copy of either [tested 2026-08-18:
%     test_a_source_registers_every_signature_before_any_form_runs,
%     test_load_memoizes_a_function_the_same_file_defines_lower_down,
%     test_a_declaration_that_cannot_type_what_the_source_defines_is_refused].
%   - That pass costs 31 inferences for a one-form source, identical across
%     three different one-form sources, then 4.006 per plain form and 23.073
%     per definition beyond it [measured 2026-08-18: interleaved A/B over
%     eight benchmark lanes, python/benchmarks/baseline.json records each].
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: the pass walks the form list three times, once per
%     concern, and three of the 4.006 a plain form costs are those walks
%     [measured 2026-08-18: 60,024 inferences over 20,001 forms]. One merged
%     walk would collect all three, but acquire_declared_dependencies/1
%     belongs to lib/lib_gitimport.pl and takes the form list itself, so
%     merging changes a library's interface; left alone here for that reason.

:- use_module(library(readutil)). % read_file_to_string/3
:- use_module(library(ansi_term)). % terminal-aware diagnostic colors
:- use_module(library(pcre)). % re_replace/4
:- use_module(library(zlib)). % gzopen/3, .gz program files
:- use_module(library(ordsets)). % ord_memberchk/2
:- use_module(library(pairs)). % group_pairs_by_key/2
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

%One pass over the stored equations answers the whole batch. Repairing each
%function separately walked every equation in the system once per function, so
%a load that repaired several paid that scan several times. The recompiled set
%is the union either way, and recompiling rebuilds clauses from stored source
%without changing translated_from, so a single snapshot answers the same set.
run_source_repairs(LoadId) :-
    findall(F, source_load_repair(LoadId, F), Functions0),
    sort(Functions0, Functions),
    transaction(repair_stale_definitions_batch(Functions)).

repair_stale_definitions_batch([]) :- !.
repair_stale_definitions_batch(Functions) :-
    findall(G,
            ( translated_from(_, [=, [G|_], Body]),
              atom(G),
              member(F, Functions),
              uses_as_data(F, Body) ),
            Stale0),
    sort(Stale0, Stale),
    forall(member(G, Stale), recompile_function_impl(G)).

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
    prepare_parsed_forms(ParsedForms).

%Everything a source does BEFORE any of its own forms run, over forms already
%parsed. It is named apart from prepare_metta_source/2 because the parse is
%not the only door onto it: python/petta/shim.pl reads a source, rewrites the
%parsed forms when run() was given host values, and then processes them one by
%one to keep a group of answers per directive, so it has to prepare the forms
%that will actually RUN rather than the text they were read from. Skipping
%this is what made the library disagree with the engine on seven shipped
%examples, each `!(memoize f)` above the `(= (f ...) ...)` the same file
%defines: fun/1 was not asserted yet and memoize refused the name
%[measured 2026-08-18: 193 of 200 examples agreed, all seven the same root].
prepare_parsed_forms(ParsedForms) :-
    refuse_untypable_source_declarations(ParsedForms),
    register_parsed_signatures(ParsedForms),
    % Pinned git dependencies declared in this file are fetched before any of
    % its forms run (gitimport.pl).
    acquire_declared_dependencies(ParsedForms).

%A source text has ONE parse, so this commits to it. Without the once/1 the
%grammar left a choice point behind every successful parse, and retrying it did
%not offer a second reading, it THREW: the first solution for "(holds foo)" is
%[parsed(expression,"(holds foo)",[holds,foo])] and backtracking into it raised
%`Syntax error: expected '(' or '!('`. So the choice point was not merely
%wasted memory, it was a trap for any caller that backtracked past this point,
%turning a parsed file into a syntax error [reproduced 2026-08-15; it is what
%plunit reported as 18 choicepoint warnings in parser.plt].
parse_metta_source(S, ParsedForms) :-
    string_codes(S, Codes),
    once(phrase(top_forms(Forms, 1), Codes)),
    maplist(parse_form, Forms, ParsedForms).

%Every name this source defines by an equation, against every type this source
%declares for it. refuse_untypable_declaration/3 in metta.pl holds the rule and
%says why it refuses; this is the collector for the case that matters most,
%the declaration and the definition written in one file.
%
%The pass is here rather than at registration because a source's declarations
%do not reach the space until its forms are processed, which is AFTER
%register_parsed_signatures/1; and here rather than after the load because by
%then the file's own !(...) forms have already run and a rollback would be
%undoing effects the author already saw. Declarations for names this source
%does not define are left alone: the space has no equations to contradict them,
%and space.lint() reads the whole space, so the cross-file case is named there.
%
%The pass costs 0.05% to 0.23% of the parse it follows [measured 2026-08-16:
%376 inferences against 770,612 over greedy_chess.metta's 128 forms, 418
%against 180,156 over lib_pln.metta's 82].
refuse_untypable_source_declarations(ParsedForms) :-
    findall(F, source_equation_name(ParsedForms, F), Defined0),
    sort(Defined0, Defined),
    Defined \== [],
    findall(Name-Type, source_declaration(ParsedForms, Defined, Name, Type),
            Declarations0),
    Declarations0 \== [],
    !,
    keysort(Declarations0, Declarations),
    group_pairs_by_key(Declarations, Grouped),
    forall(member(Name-Types, Grouped),
           refuse_untypable_declaration(Name, Types)).
refuse_untypable_source_declarations(_).

source_equation_name(ParsedForms, F) :-
    member(parsed(function, _, [=, [F|_], _]), ParsedForms),
    atom(F).

source_declaration(ParsedForms, Defined, Name, Type) :-
    member(parsed(expression, _, [':', Name, Type]), ParsedForms),
    atom(Name),
    ord_memberchk(Name, Defined).

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

%A source that defines nothing is now the COMMON caller, because the Python
%library's every run() prepares its forms through here, and the clause below
%runs ten list operations over empty lists to conclude that: 43 of the 73
%inferences the whole pre-pass costs `!(+ 1 2)`, more than the other two
%passes together [measured 2026-08-18].
%
%The cut is load-bearing rather than decoration. SWI recognises two clauses
%where one argument is [] and the SAME argument is [_|_] as a special case and
%selects between them deterministically; the clause below takes a VARIABLE
%there, so that case does not apply and indexing leaves a choice point
%[source: SWI-Prolog 10.1 manual, 2.17 Just-in-time clause indexing]. Writing
%it [_|_] to earn the indexing was rejected: a caller passing a non-list would
%then fail silently where sort/2 raises a type error today.
register_function_signatures([]) :- !.
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
             record_translated_from(NewRef, Term, SourceRef),
             record_source_assertion(SourceRef) )),
    invalidate_specializations(G).

%Recompile every stored definition whose body MENTIONS F. Wider than
%uses_as_data/2's "compiled F as data": a caller that already compiled F as a
%CALL is stale too when what changed is how its ARGUMENTS compile, which is
%what a late type declaration changes. (: f (-> Atom Atom)) is the difference
%between the argument arriving evaluated and arriving as written, so a call
%site compiled before it kept evaluating for ever.
%
%This was the Python bridge's, as petta_py_stale_equation/4 and
%petta_py_retranslate/3, which meant the engine could not repair its own
%compiled code without Python in the process. It is engine machinery: the
%rebuild it needs, recompile_function/1, was already here.
%The guard first, because nothing mentions the name in the overwhelmingly
%common case and one indexed lookup that fails is cheaper than a findall, a
%sort and a forall over nothing. This runs on every compiled equation and on
%every registration.
recompile_definitions_mentioning(F) :-
    (   definition_mentions(F, _)
    ->  findall(G, ( definition_mentions(F, G), G \== F ), Callers0),
        sort(Callers0, Callers),
        forall(member(G, Callers), recompile_function(G))
    ;   true
    ).

%Which stored definitions mention a symbol, indexed BY the symbol. Answering
%it by scanning translated_from/2 walks every equation in the system once per
%compiled equation, which is quadratic over a source load and was almost the
%whole of one: a thousand equations cost 7,330,334 inferences with the scan
%and 822,578 without it [measured 2026-08-16]. This is the same defect
%run_source_repairs/1 already fixed for the other repair trigger, fixed once
%rather than deferred per caller.
%
%The index may over-approximate, because a rollback erases a clause without
%erasing its entry. That direction is safe: a stale entry costs one rebuild
%from stored source that finds nothing, where a missing entry would leave
%compiled code stale. Nothing removes entries for that reason.
:- dynamic definition_mentions/2.

record_translated_from(Ref, Term, SourceRef) :-
    assertz(translated_from(Ref, Term), SourceRef),
    index_definition_mentions(Term).

index_definition_mentions([=, [G|_], Body]) :- !,
    forall(mentioned_symbol(Body, Symbol),
           ( definition_mentions(Symbol, G) -> true
           ; assertz(definition_mentions(Symbol, G)) )).
index_definition_mentions(_).

mentioned_symbol(Term, _) :- var(Term), !, fail.
mentioned_symbol(Term, Term) :- atom(Term), !.
mentioned_symbol(Term, Symbol) :- is_list(Term),
                                  member(Element, Term),
                                  mentioned_symbol(Element, Symbol).

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
%Only the token substitution here, not the whole parsed-form rewrite: a data
%atom is not a call site, so the py-call alias rewrite has nothing to do in one
%and this path never ran it. The token lookup is one inference per atom and it
%is what makes `(bind! x 1)` reach a stored `(fact x)`.
process_form(Space, parsed(expression, _, Term0), []) :-
    substitute_bound_tokens(Term0, Term),
    %metta_add_atom/3, not the public `add-atom`: the loader has already
    %resolved this space, so the space-argument check the public one owes a
    %PROGRAM is pure cost here. It runs once per atom loaded, and save-load-metta
    %measured it at exactly two inferences on each of its 20,001
    %[measured 2026-08-17].
    metta_add_atom(Space, Term, _),
    print_expression_form(Term).
process_form(Space, parsed(runnable, FormStr, Term), Result) :-
    rewrite_parsed_form(Space, FormStr, Term, BoundTerm),
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
    rewrite_parsed_form(Space, FormStr, Term, BoundTerm),
    %The one compile door (compile_metta_equation/4 in spaces.pl) carries
    %the eviction, registration, translation, provenance, and the complete
    %change notification this clause used to restate.
    compile_metta_equation(Module, BoundTerm, _Clause, Ref),
    print_function_form(FormStr, Ref).
process_form(_, In, _) :-
    throw(error(petta_translation_failed(In),
                context(process_form/3, 'could not translate MeTTa form'))).

% The loader records every asserted clause reference. A later source error can
% then erase the whole partial load and leave the file retryable.
process_form(Space, _, parsed(expression, _, Term), []) :-
    %This pipeline bypasses metta_add_atom/3, so the user-wins rule for
    %prelude declarations applies here directly.
    evict_prelude_declaration(Space, Term),
    add_sexp(Space, Term, SpaceRef),
    record_source_assertion(SpaceRef),
    print_expression_form(Term).
process_form(Space, _, parsed(runnable, FormStr, Term), Result) :-
    rewrite_parsed_form(Space, FormStr, Term, BoundTerm),
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
    rewrite_parsed_form(Space, FormStr, Term, BoundTerm),
    %Compile-mode targets the base tier, so the one door sees user and
    %applies the same user-wins eviction it always applies there.
    compile_metta_equation(user, BoundTerm, _Clause, Ref),
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

%Top-level comments are layout too. Count their terminating newline for source
%diagnostics while consuming their text without constructing another code list.
source_layout(LC0, LC2) --> ";", !, source_comment(LC0, LC2).
source_layout(LC0, LC2) --> "\n", !,
                             { LC1 is LC0 + 1 },
                             source_layout(LC1, LC2).
source_layout(LC0, LC2) --> [C], { code_type(C, space) }, !,
                             source_layout(LC0, LC2).
source_layout(LC, LC) --> [].

source_comment(LC0, LC2) --> "\n", !,
                              { LC1 is LC0 + 1 },
                              source_layout(LC1, LC2).
source_comment(LC, LC) --> eos, !.
source_comment(LC0, LC2) --> [_], source_comment(LC0, LC2).

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

top_forms(Forms, LC0) --> source_layout(LC0, LC1),
                          top_forms_after_layout(Forms, LC1).

top_forms_after_layout([], _) --> eos.
top_forms_after_layout([Term|Fs], LC1) -->
    ( "!" -> {Tag = runnable} ; {Tag = form} ),
    read_form_open(LC1),
    read_balanced_form(LC1, Cs, LC2),
    { string_codes(FormStr, Cs), Term =.. [Tag, FormStr] },
    top_forms(Fs, LC2).
