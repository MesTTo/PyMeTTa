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
%   - print_runnable_form/2 and print_function_form/2's trace output, and
%     library(pcre)-backed regex, both work under autoload=false, not only
%     under the engine's default [measured 2026-08-18: NO_AUTOLOAD=1 sh
%     test.sh, the full examples/ corpus].
%   - source_layout//2 skips exactly the characters sread/2 treats as
%     whitespace between atoms, parser.pl's metta_token_boundary/2 layout
%     rows being the one class both read [tested 2026-08-19:
%     test_every_unicode_whitespace_separates_top_level_forms].
%   - A top-level form is ONE ATOM of any kind, so `! untouched-symbol`,
%     `! 42`, `! "text"` and `! &first` run and a bare symbol on its own
%     line is stored, which is what the arbiter does with each. `!` marks
%     the atom after it only before `(`, layout or end of input, and is an
%     ordinary symbol character everywhere else, so `bind!`, `!=`, `!42`
%     and `!$x` are names [tested 2026-08-19: filereader_form_splitter,
%     filereader_bare_top_level_atoms].
%   - A file that loads again REPLACES what it put in that space rather than
%     adding to it, reaches any other space its change has made stale, and
%     says what it withdrew [tested 2026-08-19:
%     test_a_reloaded_source_replaces_its_definitions_and_says_what_it_replaced,
%     test_a_reload_replaces_the_file_in_every_space_that_holds_it,
%     filereader_source_reload:a_reload_leaves_one_clause_for_a_redefined_function].
%   - The replacement reaches everything derived from the definitions it
%     withdrew, because the atoms leave through metta_remove_atom/3
%     [tested 2026-08-19: test_reloading_invalidates_a_memoized_answer,
%     test_reloading_invalidates_a_tabled_answer,
%     test_reloading_invalidates_a_specialization,
%     test_a_live_view_follows_a_reload].
%   - A reload that raises leaves the previous definitions standing
%     [tested 2026-08-19:
%     test_a_reload_that_fails_leaves_the_previous_definitions_standing].
%   - Replacement is per FILE and reaches nothing another file contributed, so
%     a function two files define still answers twice: that is a name
%     collision and not a reload [tested 2026-08-19:
%     test_a_reload_replaces_that_files_definitions_and_no_others].
%   - "Changed" is answered from the CONTENT, so an edit that keeps a file's
%     length is still an edit where a modification time might not have moved
%     [tested 2026-08-19:
%     filereader_source_reload:an_edit_that_keeps_the_length_is_still_a_change].
%   - Recording what a load contributed costs ONE inference per stored atom,
%     which is one assertz and is what a withdrawal needs to find the atom
%     again, plus about 230 for the load itself. Measured against the same
%     tree without the recording, interleaved, min of three a side, no spread:
%     a 128-equation source 95,396 against 95,165 (+0.24%), and a
%     20,001-atom file 7,381,790 against 7,361,403 through the library's door
%     and 7,322,289 against 7,302,027 through import!'s populate pass, both
%     +0.28%. Asking whether an already-loaded file has changed costs 336, a
%     read and a hash [measured 2026-08-19].
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
%pcre.pl declares four local :- autoload/2 lines (apply, error, dcg/basics,
%lists) but reads its own Options list with option/2 (library(option))
%without declaring THAT one, so it too resolves by global autoload today
%[measured 2026-08-18: examples/libraries/regex_lib.metta under
%NO_AUTOLOAD=1, existence_error(procedure,pcre:option/2)]. Same trap as
%ugraphs.pl and clpb.pl (lib/lib_constraints.pl has both), same fix.
:- pcre:use_module(library(option), [option/2]).
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

%What a reload replaced, said rather than done quietly. It goes out at
%informational, which is where SWI puts what the loader did and is the level a
%caller silences deliberately with -q or verbose(silent) rather than by
%accident.
:- multifile prolog:message//1.
prolog:message(petta_source_replaced(CanonPath, Spaces, Atoms)) -->
    { atomic_list_concat(Spaces, ' ', Named) },
    [ 'replaced ~w: ~w atom(s) withdrawn from ~w'-[CanonPath, Atoms, Named] ].
:- current_prolog_flag(argv, Args), ( (memberchk(silent, Args) ; memberchk('--silent', Args) ; memberchk('-s', Args))
                                      -> assertz(silent(true)) ; assertz(silent(false)) ).
:- dynamic working_dir/1.
:- dynamic compiled_metta_source/1.
:- thread_local active_source_load/1.
:- dynamic source_load_assertion/2.
:- dynamic source_load_repair/2.
%What a file put where, so that loading it again can REPLACE that rather than
%add to it. SWI states the rule this implements: "clauses are owned by the file
%in which they are defined. This information is used to replace the old
%definition after the file has been modified and is reloaded"
%[source: SWI-Prolog 10.1 Reference Manual, include/1]. Here the owned things
%are whatever the load asserted, which source_load_assertion/2 already lists,
%so the file only needs the key onto that list and the digest of the text it
%was built from.
%
%The list is KEPT as the per-assertion facts the load built it up as, rather
%than collected into one clause holding a list of references. The collected
%form is the smaller of the two, one clause where this pays a clause header
%per atom of every file loaded, and it was tried and rejected on cost: it has
%to walk the accumulator at the end of every load, and that walk cost 80,410
%inferences of the save-load benchmark's 8,502,424 [measured 2026-08-19,
%interleaved A/B, min of three a side]. Keeping the facts costs the load
%NOTHING and takes a walk off it, because the success path used to retract
%them one at a time.
%
%A clause reference is a BLOB of type clause, so holding one keeps its clause
%from being reclaimed and a stale one decodes to nothing rather than to
%whatever later took its place [measured 2026-08-19: erased, then 200,000
%clauses asserted and two clause collections later, the reference still
%decoded to nothing and erase/1 on it failed].
:- dynamic metta_source_load/4. %metta_source_load(CanonPath, Space, LoadId, Digest)
:- dynamic source_load_digest/3. %source_load_digest(LoadId, Filename, Digest)

%The first crypto_data_hash/3 of a process pays a one-off initialisation, and
%without this it lands on whichever program loads first and reads as that
%program's cost [measured 2026-08-19: 3,132 inferences on the first call, 217
%on every later one]. Paid here instead, where it belongs.
:- crypto_data_hash("", _, [algorithm(sha256)]).

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
    import_when(changed, Space, CanonPath,
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
%
%A load's own read is where its digest is taken, because that is where the text
%already is. Computing it again when the load finished read the file a second
%time, and only the digest belongs to the load: metta_source_digest/2 below asks
%the same question of a file that is NOT loading, and going through here would
%have filed its answer under whatever load happened to be running, which for a
%nested import is the importing file's [measured 2026-08-19: the second read
%cost 113 inferences of every load].
read_metta_source(Filename, S) :-
    read_source_text(Filename, S),
    (   active_source_load(LoadId)
    ->  crypto_data_hash(S, Digest, [algorithm(sha256)]),
        assertz(source_load_digest(LoadId, Filename, Digest))
    ;   true
    ).

read_source_text(Filename, S) :-
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
%The re-population closure is load_imported_metta_file_impl/3 with its first
%two arguments filled: the file, and a fresh Results slot per space, since a
%space that is only being brought back up to date has no answers to report.
load_imported_metta_file(Filename, Results, Space) :-
    catch(replacing_previous_load(Filename, Space,
                                  load_imported_metta_file_impl(Filename, _),
                                  load_imported_metta_file_impl(Filename, Results,
                                                                Space)),
          Error,
          rethrow_metta_file_error(Filename, Error)).

%The populate pass gets a load context of its own, the same as the compile
%pass. A file's equations compile once, into the module compile mode targets,
%but its ATOMS are stored once per space, so the second space's copy is a
%contribution the file made and has to be recorded as one; without this a
%reload replaced the first space's copy and left the second's standing.
load_imported_metta_file_impl(Filename, Results, Space) :-
    ( compiled_metta_source(Filename)
      -> with_source_load(Filename, Space,
                          load_metta_file_impl(Filename, Results, Space, populate))
       ; run_with_loading_marker(
             compiled_metta_source(Filename),
             run_new_source_load(Filename, Results, Space)) ).

run_new_source_load(Filename, Results, Space) :-
    with_source_load(Filename, Space,
                     load_metta_file_impl(Filename, Results, Space, compile)).

%One source load: the context every assertion is filed under while it runs, the
%repair pass at the end, and the two ways it can finish. A failure rolls the
%whole partial load back, which is what this always did. A SUCCESS now keeps
%the list instead of dropping it, because that list is precisely what a later
%load of the same file has to take back out, and metta_source_load/4 is the key
%onto it.
%
%It is a wrapper rather than a fixed body because the Python library's load()
%runs the same file through a reader of its own, to keep one answer group per
%directive (petta_py_load/3 in python/petta/shim.pl), and a load that is not
%recorded here cannot be replaced later. Both doors, one lifecycle
%[tested: test_both_doors_replace_a_files_definitions].
%
%Publishing is part of the GOAL and not of the cleanup, because it only happens
%on success and because it can raise: a cleanup handler is the wrong place for
%either.
:- meta_predicate with_source_load(+, +, 0).
with_source_load(CanonPath, Space, Goal) :-
    gensym(source_load_, LoadId),
    setup_call_catcher_cleanup(
        asserta(active_source_load(LoadId), ContextRef),
        once(( call(Goal),
               run_source_repairs(LoadId),
               publish_source_load(CanonPath, Space, LoadId) )),
        Catcher,
        ( erase(ContextRef),
          retractall(source_load_repair(LoadId, _)),
          retractall(source_load_digest(LoadId, _, _)),
          ( Catcher == exit -> true ; rollback_source_load(LoadId) ) )).

publish_source_load(CanonPath, Space, LoadId) :-
    (   source_load_digest(LoadId, CanonPath, Digest)
    ->  assertz(metta_source_load(CanonPath, Space, LoadId, Digest))
    ;   throw(error(existence_error(metta_source_digest, CanonPath),
                    context(publish_source_load/3,
                            'a source load finished without reading its own \c
                             source, so nothing records what a reload replaces')))
    ).

%Whether the file on disk still holds the text a load was built from, which is
%SWI's if(changed) condition, "the file ... has been modified since it was
%loaded the last time" [source: SWI-Prolog 10.1 Reference Manual, load_files/2].
%
%SWI answers it from the modification time. This hashes the CONTENT instead,
%because a timestamp cannot answer it soundly here: Linux stamps a file from
%the coarse clock, so two writes inside one tick carry the same time, and an
%edit that keeps the length then reads as unmodified. That is exactly the edit
%this item exists for, `(= (answer) 1)` to `(= (answer) 2)`, and a reload that
%misses it is the silent staleness the second door already had.
%
%The text is read either way when the file does load, so what being sure costs
%is one read of a file that turns out not to need loading: 333 inferences over
%a 128-form 3,236-byte source, where loading it costs 95,165
%[measured 2026-08-19, five runs each, no spread].
metta_source_digest(CanonPath, Digest) :-
    read_source_text(CanonPath, Text),
    crypto_data_hash(Text, Digest, [algorithm(sha256)]).

metta_source_changed(CanonPath) :-
    metta_source_load(CanonPath, _, _, Loaded), !,
    metta_source_digest(CanonPath, Digest),
    Digest \== Loaded.

%Reloading is what makes the trace-edit-verify cycle possible, and the manual
%describes that cycle as the reason it exists: trace a goal, find unexpected
%behaviour, "Fix the sources and reload them using make/0", retry
%[source: SWI-Prolog 10.1 Reference Manual, section 4.3.2]. Two things were
%missing here and they failed in opposite directions. The Python door had no
%file identity at all, so a second load ADDED the file's definitions on top of
%the first and `(answer)` answered 1 and 2; import! had identity but no change
%detection, so a second import was skipped and the edit was ignored. Neither
%said anything [measured 2026-08-19, both doors].
%
%So this is the other half of the lifecycle P11.6 gave a space: clearing a
%space empties its execution module, and loading a file again replaces what
%that file put there. It is not retract-and-assert. The atoms leave through
%metta_remove_atom/3, the funnel that owns every consequence of an atom
%leaving: an equation un-compiles and forgets its name, a declaration
%recompiles the call sites it was shaping, invalidate_specializations/2 drops
%the specializer's clones, metta_on_function_removed/1 drops lib_memo's
%generations and lib_tabling's tables and duals.pl's duals, and
%metta_on_atom_removed/2 tells every LiveView and Python subscription. What no
%atom owns leaves through rollback_source_load/1, the same erase a failed load
%uses, and there is one such thing: a file imported into a NAMED space compiles
%into &self's module while its atoms are stored in that space, so its clauses
%are global where its atoms are not
%[tested: test_a_reloaded_source_replaces_its_definitions_and_says_what_it_replaced,
%test_reloading_invalidates_a_memoized_answer].
%
%Replacement reaches the asking space, and any OTHER space the change has made
%stale. The compiled half is shared for the reason just given, so a file whose
%text has changed cannot be replaced in one space alone: another space still
%holding the old atoms would list definitions the rebuilt module no longer
%answers. A space holding the SAME text is not stale and is left alone, which
%is what keeps loading one file into many spaces linear. The asking space loads
%first, so its pass is the one that compiles; the stale ones are populated
%again after, through LoadInto, called as call(LoadInto, Space).
%
%LoadInto is a parameter because how a file goes into a space is a property of
%the FILE, and the engine is not the only thing that reads one: the Python
%library's trusted fast cache is a serialised space with a format of its own,
%and re-populating one through the MeTTa reader would try to parse its binary
%header. Each door hands in the loader its own format needs.
%
%The withdrawal and the load that follows it are ONE transaction, so a reload
%that raises leaves the previous definitions standing rather than taking them
%with it. This is the difference between a reload being safe to attempt and a
%typo in the source costing the session its program, and the manual makes the
%same point about make/0: "Reloading a previously loaded file is safe, both in
%the debug scenario above and when the code is being executed by another
%thread", where the debug scenario is the fix-and-reload cycle this item is for
%[source: SWI-Prolog 10.1 Reference Manual, section 4.3.2]. transaction/1
%restores an erased clause the same way it discards an asserted one
%[measured 2026-08-19: an erase inside a transaction that then throws left the
%clause answering]. Only the reload path pays it; a first load has nothing to
%protect and does not enter one
%[tested: test_a_reload_that_fails_leaves_the_previous_definitions_standing].
:- meta_predicate replacing_previous_load(+, +, 1, 0).
replacing_previous_load(CanonPath, Space, LoadInto, Goal) :-
    (   metta_source_load(CanonPath, _, _, _)
    ->  replaced_source_spaces(CanonPath, Space, Replaced),
        (   Replaced == []
        ->  call(Goal)
        ;   transaction(replace_source_load(CanonPath, Space, Replaced,
                                            LoadInto, Goal))
        )
    ;   call(Goal)
    ).

%Which spaces this load replaces. Its own, whenever it holds a copy, because
%that is what a consult means. And any OTHER space whose copy this load is
%about to invalidate, which is one holding text this file no longer has: the
%compile that follows rebuilds the shared half from the NEW source, so a space
%still holding the old atoms would list definitions the module no longer
%answers.
%
%A space holding a copy of the SAME text is left alone, and that is what keeps
%the common shape cheap: loading one unchanged file into ten spaces is ten
%loads and not fifty-five, and it says nothing, because nothing was replaced
%[tested test_loading_one_file_into_many_spaces_replaces_none_of_them].
%
%import! asked the same question a moment ago, to decide whether to load at
%all, and this reads the file again rather than being handed that answer.
%Threading it down would save 336 inferences on a path that is about to spend
%tens of thousands loading, and it would be answering from a digest of what
%the file held BEFORE the decision rather than of what is about to be read.
replaced_source_spaces(CanonPath, Space, Replaced) :-
    metta_source_digest(CanonPath, Now),
    findall(S,
            ( metta_source_load(CanonPath, S, _, Loaded),
              ( S == Space -> true ; Loaded \== Now ) ),
            Replaced).

:- meta_predicate replace_source_load(+, +, +, 1, 0).
replace_source_load(CanonPath, Space, Replaced, LoadInto, Goal) :-
    findall(N, ( member(S, Replaced), withdraw_source_load(CanonPath, S, N) ),
            Counts),
    sum_list(Counts, Withdrawn),
    retractall(compiled_metta_source(CanonPath)),
    print_message(informational,
                  petta_source_replaced(CanonPath, Replaced, Withdrawn)),
    call(Goal),
    forall(( member(S, Replaced), S \== Space ), call(LoadInto, S)).

%One space's copy of one file, taken back out. The atoms go first so that the
%funnel sees the state the program was actually running with; the references
%then go the way a rolled-back load's do, and erase/1 on a reference the funnel
%already erased is why rollback_source_load/1 guards it.
withdraw_source_load(CanonPath, Space, Count) :-
    retract(metta_source_load(CanonPath, Space, LoadId, _)),
    findall(Ref, source_load_assertion(LoadId, Ref), Asserted),
    reverse(Asserted, Refs),
    findall(AtomSpace-Atom,
            ( member(Ref, Refs), stored_atom_of_ref(Ref, AtomSpace, Atom) ),
            Atoms),
    forall(member(AtomSpace-Atom, Atoms),
           ( metta_remove_atom(AtomSpace, Atom, _) -> true ; true )),
    rollback_source_load(LoadId),
    length(Atoms, Count).

%A cleared space keeps no record of what a file put in it, because nothing of
%it is left to replace and the name is POOLED: a later life reusing the name
%would otherwise be told it already holds a file's atoms and have them
%withdrawn from under it. This is the storage half of the same lifecycle
%clear_native_atoms/1 owns for the execution module
%[tested: test_a_cleared_space_forgets_what_a_file_put_in_it,
%test_a_recycled_space_name_inherits_no_clauses_from_its_past_life].
forget_space_source_loads(Space) :-
    forall(retract(metta_source_load(_, Space, LoadId, _)),
           ( retractall(source_load_assertion(LoadId, _)),
             retractall(source_load_digest(LoadId, _, _)) )).

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

%Newest first, so an assertion is undone before whatever it was built on.
%
%A reference that is already gone is not an error here, and it arrives two
%ways: erase/1 THROWS on one kind and FAILS on another. The catch alone was
%enough while the only caller was a failed load, whose references are all still
%live. A withdrawal reaches this after metta_remove_atom/3 has already taken
%the equations out, so several references are erased before the sweep starts,
%and a failing erase/1 made forall/2 fail and took the whole withdrawal down
%with it [measured 2026-08-19: it reported one atom and then failed].
rollback_source_load(LoadId) :-
    findall(Ref, retract(source_load_assertion(LoadId, Ref)), Asserted),
    reverse(Asserted, Refs),
    forall(member(Ref, Refs),
           ( catch(erase(Ref), _, true) -> true ; true )).

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

%One MODULE at a time, because the erase and the re-translation are two
%phases and the second one reads the database the first one emptied. The same
%name compiled into two spaces was erased in BOTH before either was
%retranslated, so a clause whose translation consults that name's definition
%elsewhere saw it as undefined: `(super (f $x))` in a space resolved to
%whatever lay above the erased definition instead of to the definition itself
%[tested: translator_super:a_later_definition_retargets_an_earlier_super].
%Within one module the two phases stay, because that is what keeps the
%rebuilt clauses in their original order behind any the Prolog interop
%asserted untracked.
recompile_function_impl(G) :-
    findall(Module,
            ( translated_from(Ref, Term),
              Term = [=, [G0|_], _],
              G0 == G,
              clause_property(Ref, module(Module)) ),
            Modules0),
    sort(Modules0, Modules),
    %EVERY module's retained equations, which is not the same set as the
    %modules that still have clauses: a module whose clauses have all gone
    %keeps its equations otherwise, and the specializer then plans from
    %equations nothing backs. Each module below re-records its own as it
    %retranslates.
    clear_fun_meta(_, G),
    forall(member(Module, Modules), recompile_function_in_module(Module, G)),
    %Per module the recompile touched, because the invalidation is scoped to
    %one space now and this rebuilds a function's clauses wherever they are.
    forall(member(Module, Modules), invalidate_specializations(Module, G)).

recompile_function_in_module(Module, G) :-
    findall(compiled(Ref, Term),
            ( translated_from(Ref, Term),
              Term = [=, [G0|_], _],
              G0 == G,
              clause_property(Ref, module(Module)) ),
            Clauses),
    forall(member(compiled(Ref, Term), Clauses),
           ( erase(Ref),
             retract(translated_from(Ref, Term)) )),
    forall(member(compiled(_, Term), Clauses),
           ( copy_term(Term, Fresh),
             once(with_metta_module(Module,
                                    translate_clause(Fresh, Clause))),
             assertz(Module:Clause, NewRef),
             record_source_assertion(NewRef),
             record_translated_from(NewRef, Term, SourceRef),
             record_source_assertion(SourceRef) )).

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
    %Compile-mode targets the base tier, so the one door sees &self's module
    %and applies the same user-wins eviction it always applies there.
    metta_self_module(Self),
    compile_metta_equation(Self, BoundTerm, _Clause, Ref),
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
    %Module-qualified on purpose: ansi_format/4 (library(ansi_term)) calls a
    %~@ goal argument from ITS OWN module context, not this file's, so an
    %unqualified portray_clause here resolves (or fails to) as
    %ansi_term:portray_clause/N. ansi_term.pl does not declare its own
    %dependency on library(listing), relying on autoload the same way
    %library(prolog_clause) relies on it for nth1/3 (metta.pl's Dependencies
    %section has that finding in full); with autoload=false the unqualified
    %spelling raised existence_error(procedure,ansi_term:portray_clause/1)
    %for EVERY runnable form this prints, i.e. most of the example corpus
    %[measured 2026-08-18: examples/basics/math.metta under NO_AUTOLOAD=1].
    %Naming the predicate's real home module sidesteps the gap in
    %ansi_term.pl entirely, rather than trying to patch a library this repo
    %does not ship.
    forall(member(G, Goals),
           ansi_format([fg(magenta)], "~@", [prolog_listing:portray_clause((:- G))])),
    ansi_format([fg(yellow)], "^^^^^^^^^^^^^^^^^^^^^^^~n", []).

print_function_form(_, _) :- silent(true), !.
print_function_form(FormStr, Ref) :-
    ansi_format([fg(yellow)], "--> metta function -->~n", []),
    ansi_format([fg(cyan)], "~w~n", [FormStr]),
    ansi_format([fg(yellow)], "--> prolog clause -->~n", []),
    clause(Head, Body, Ref),
    ( Body == true -> Show = Head ; Show = (Head :- Body) ),
    %Same ansi_format/module trap as print_runnable_form/2 above.
    ansi_format([fg(green)], "~@", [prolog_listing:portray_clause(current_output, Show)]),
    ansi_format([fg(yellow)], "^^^^^^^^^^^^^^^^^^^^^^~n", []).

%Top-level comments are layout too. Count their terminating newline for source
%diagnostics while consuming their text without constructing another code list.
%
%Whitespace between forms is the reader's own class, parser.pl's
%metta_token_boundary/2, not SWI's code_type/2: reading the two differently is
%what let `(= (a) 1)<IDEOGRAPHIC SPACE>(= (b) 2)` load while the same file
%written with a NO-BREAK SPACE raised `expected '(' or '!('`, SWI calling one
%of them a space and not the other [tested:
%test_every_unicode_whitespace_separates_top_level_forms]. Only "\n" counts a
%line, here and in the Python locator, which counts source.count("\n"), so
%LINE SEPARATOR and NEL are ordinary layout on both sides
%[source: python/petta/_source_forms.py:80].
source_layout(LC0, LC2) --> ";", !, source_comment(LC0, LC2).
source_layout(LC0, LC2) --> "\n", !,
                             { LC1 is LC0 + 1 },
                             source_layout(LC1, LC2).
source_layout(LC0, LC2) --> [C], { metta_token_boundary(C, layout) }, !,
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
read_balanced_form(LC, Cs, LC2) -->
    grab_until_balanced(1, [0'(], Cs, LC, LC2, outside), !.
read_balanced_form(LC, _, _) -->
    string_without("\n", Rest),
    { format(atom(Msg), "missing ')', starting at line ~w:~n~s", [LC, Rest]),
      throw(error(syntax_error(Msg), none)) }.

%One top-level ATOM, which is what a MeTTa source is a sequence of. A
%parenthesised expression is the commonest kind and was for a long time the
%only kind this splitter read, so `! untouched-symbol`, `! 42` and `! &first`
%raised `expected '(' or '!('` and took the whole file down with them
%[source: LeaTTa tests/semantics/eval-core/self-evaluating-atoms.metta,
%grounded/25-state-rendering.metta, modules/09-bind/main.metta, all three
%STATUS conforms].
read_top_atom(LC0, Cs, LC1) --> "(", !, read_balanced_form(LC0, Cs, LC1).
read_top_atom(LC0, Cs, LC1) --> read_bare_atom(outside, LC0, [], Cs, LC1).

%A symbol, a number, a string or a variable, ending at the first token
%boundary reached OUTSIDE a string literal, so `! "a b"` is one atom and not
%two. string_state/3 is the same three-state machine grab_until_balanced//6
%runs, which is why a quote, an escape or a semicolon inside the literal
%behaves here exactly as it does inside a form.
read_bare_atom(State, LC0, Acc, Cs, LC2) --> [C],
    { \+ ( State == outside, metta_token_boundary(C, _) ) }, !,
    { string_state(State, C, State1),
      ( C =:= 0'\n -> LC1 is LC0 + 1 ; LC1 = LC0 ) },
    read_bare_atom(State1, LC1, [C|Acc], Cs, LC2).
read_bare_atom(_, LC, Acc, Cs, LC) --> { Acc \== [], reverse(Acc, Cs) }.

top_forms(Forms, LC0) --> source_layout(LC0, LC1),
                          top_forms_after_layout(Forms, LC1).

top_forms_after_layout([], _) --> eos.
top_forms_after_layout(Forms, LC0) -->
    exec_marker, !,
    source_layout(LC0, LC1),
    top_atom_form(runnable, Forms, LC1).
top_forms_after_layout(Forms, LC0) -->
    top_atom_form(form, Forms, LC0).

%A marker with nothing after it contributes no form rather than raising: the
%arbiter's tokenizer emits the marker and its parser then has no atom to mark
%[measured 2026-08-19: LeaTTa --observed-file on a file ending in a bare `!`
%exits 0 and prints nothing].
top_atom_form(_, [], _) --> eos, !.
top_atom_form(Tag, [Term|Fs], LC0) -->
    read_top_atom(LC0, Cs, LC1),
    { string_codes(FormStr, Cs), Term =.. [Tag, FormStr] },
    top_forms(Fs, LC1).

%`!` marks the atom that follows only when it stands before `(`, layout or
%end of input. Everywhere else it is an ordinary symbol character, which is
%what makes `bind!`, `change-state!`, `println!` and `!=` ordinary names, and
%what makes `!42` and `!$x` symbols rather than runnables [source: LeaTTa
%MettaHyperonFull/Runtime/Parser.lean:85-88; measured 2026-08-19: each of
%those two prints nothing there].
exec_marker --> "!", exec_marker_boundary.

exec_marker_boundary, [C] --> [C], !,
    { C =:= 0'( ; metta_token_boundary(C, layout) }.
exec_marker_boundary --> [].
