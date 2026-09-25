% Purpose: measure engine execution, report predicate indexes, and reclaim
%   everything the process can free before a caller counts what is left.
% Assumes: loaded through _binding/shim.pl in its host module.
%   SWI-Prolog 10.1.13's profiler primitive `'$profile'/4` (src/pl-prof.c),
%   the one library(prolog_profile) profile/2 runs: it resets the profiler,
%   arms it, runs the goal and stops it, and nothing else.
% Guarantees: compiled profile rows retain their source file through the
%   reader's ownership journal [tested: test_a_profile_exports_as_pstats;
%   commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1].
% Guarantees: profiling returns data without invoking an interactive display
%   [tested: test_profile_does_not_invoke_a_display_callback; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1].
% Guarantees: metta_py_reclaim/1 leaves nothing collectable standing but at
%   most its last tick's clause and the one blob holding it: a dropped space's
%   atoms are gone after it even when another thread held a clause collection
%   as it began, and it settles in a process holding an erase listener
%   [tested 2026-09-25T05:55:18+10:00:
%   test_a_drop_is_reclaimed_while_another_thread_collects,
%   test_dropping_a_space_reclaims_its_atoms,
%   test_a_released_index_is_collected_after_its_query_boundary].
% Decides: 64 rounds before metta_py_reclaim/1 declares that no fixed point
%   comes. A round frees at least one link of each chain of holders (object,
%   blob, clause, atom), so a chain settles in as many rounds as it has
%   links, and only a process still producing garbage elsewhere reaches it.
% Owns resources: '$profile'/4 starts and stops the native sampler around its
%   goal, including exception propagation [source:
%   https://github.com/SWI-Prolog/swipl-devel/blob/fc7ef84b949378b729052c3ade79c90ce5416abb/src/pl-prof.c#L942-L970;
%   commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1].
%   A profile whose sampler took no sample still answers the goal's answers,
%   with zero samples and ticks and rows carrying their call counts
%   [tested: test_a_profile_with_no_samples_still_answers; commit=d9c15a2e39c743ee44f92dc4eedcd82b5f3f8509].
%   metta_py_reclaim/1 stops SWI's collector thread for its loop and restores
%   the gc_thread setting it found on every exit, exceptions included.

%%%%%%%%%% Profiling %%%%%%%%%%
%
% The statistical profiler around one wrapped call, its data projected to
% plain values: the summary counters and one row per predicate,
% self-ticks-descending. Sampling is statistical, so a short program may
% carry few samples, or none.
%
%Workaround: swi-profile-report-divides-by-zero-samples - run the profiler
%primitive profile/2 runs, without profile/2's report.
%
%profile/2 is `call_cleanup('$profile'(Goal, How, Ports, Rate),
%show_profile(Options))`, and the report divides by the total tick count
%(library/prolog_profile.pl time_data/7 and the net time above it), so a
%goal too short for the 5 ms sampling period raises
%evaluation_error(zero_divisor) from the cleanup, AFTER the goal answered,
%and the ball unwinds the goal's bindings on its way to any catcher: the
%answer was gone by the time this door could look at it. Every profile door
%read that as an EngineError on a quiet box, and the report also consults
%prolog:show_profile_hook/1 first, the hook SWI autoloads from xpce whenever
%DISPLAY is set. The primitive does the profiling and nothing else; the rows
%come from profile_data/1 below, whose own division is guarded. An empty
%profile is the honest answer when nothing was sampled
%[measured 2026-09-12: eleven profile tests of the Python suite red on
%c00465ae4 and on the pristine b1d175f13 with `//2: evaluation error:
%zero_divisor` at loadavg 4, where a 3,000,000-inference loop profiles to
%samples=6 ticks=26 and profile(true, [top(0)]) raises;
%command=sh extensions/python/test.sh; commit=d9c15a2e39c743ee44f92dc4eedcd82b5f3f8509].
metta_py_profiled(Pred, Ins, [Out, Samples, Ticks, Seconds, Nodes]) :-
    metta_py_wrapped_goal(Pred, Ins, Out, Goal),
    current_prolog_flag(profile_ports, Ports),
    current_prolog_flag(profile_sample_rate, Rate),
    '$profile'(Goal, cputime, Ports, Rate),
    (   catch(metta_py_profile_rows(Samples, Ticks, Seconds, Nodes),
              error(evaluation_error(zero_divisor), _),
              fail)
    ->  true
    ;   Samples = 0, Ticks = 0, Seconds = 0.0, Nodes = []
    ).

%The rows SWI's own profiler collected, read out of one profile_data/1.
%
%Each row carries seconds beside its ticks, because a tick count alone cannot
%be read without the ratio and nothing published the ratio. The conversion is
%SWI's own, from the report it would have printed: net ticks are the total
%less the profiler's accounting, and a predicate's share of them is its share
%of the sampled time [source: SWI-Prolog 10.1.13
%library/prolog_profile.pl:151,205-210 time_data/7].
%
%Each row carries the consulted clause's location or its MeTTa source-load
%path, so a profile exported to pstats has a source key to navigate by.
%
%And the name and arity APART from the spelling, plus the recursive-call count
%SWI keeps on the '<recursive>' caller node. Both were reachable only by taking
%the printed predicate back apart in Python, which a module atom carrying a
%colon defeats: `'$metta_exec:&pyspace_1':fib/2` is how every compiled MeTTa
%head is written, and the host's regular expression read its name as
%`&pyspace_1':fib`, so profile_extension(names=["fib"]) reported 0 calls in the
%same process where profile() reported 17
%[tested: test_profile_extension_counts_a_compiled_head; commit=3287d4dd4928f09ce7c111d05a1c516808e226d5].
%The profiler knows the parts; sending them is cheaper and total where
%re-parsing Prolog syntax is neither. A predicate the profiler names in some
%other shape keeps its whole spelling as the name and answers arity -1.
metta_py_profile_rows(Samples, Ticks, Seconds, Nodes) :-
    profile_data(Data),
    get_dict(summary, Data, Summary),
    get_dict(samples, Summary, Samples),
    get_dict(ticks, Summary, Ticks),
    get_dict(accounting, Summary, Accounting),
    get_dict(time, Summary, Seconds),
    Net is Ticks - Accounting,
    get_dict(nodes, Data, NodeDicts),
    %sort/4 keys index compounds, not lists, so the self-ticks ride in
    %front as the key of a pair and are stripped after the sort.
    findall(Self-[PredName, Calls, Redos, Self, Siblings, File, Line,
                  SelfSeconds, TotalSeconds, Name, Arity, Recursive],
            ( member(Node, NodeDicts),
              get_dict(predicate, Node, P), term_string(P, PredName),
              get_dict(call, Node, Calls), get_dict(redo, Node, Redos),
              get_dict(ticks_self, Node, Self),
              get_dict(ticks_siblings, Node, Siblings),
              metta_py_predicate_source(P, File, Line),
              metta_py_predicate_parts(P, Name, Arity),
              metta_py_recursive_calls(Node, Recursive),
              metta_py_tick_seconds(Self, Net, Seconds, SelfSeconds),
              Both is Self + Siblings,
              metta_py_tick_seconds(Both, Net, Seconds, TotalSeconds) ),
            Keyed),
    sort(1, @>=, Keyed, SortedKeyed),
    findall(Row, member(_-Row, SortedKeyed), Nodes).

%The predicate's own name and arity, whatever module wrapping it carries.
metta_py_predicate_parts(Module:Name/Arity, Name, Arity) :-
    atom(Module), atom(Name), integer(Arity), !.
metta_py_predicate_parts(Name/Arity, Name, Arity) :-
    atom(Name), integer(Arity), !.
metta_py_predicate_parts(Other, Name, -1) :-
    term_to_atom(Other, Name).

%How many of a predicate's calls came from itself. SWI keeps them on a
%'<recursive>' pseudo-caller rather than in the node's own call count, so a
%directly recursive head reads `calls` as its ENTRY count and this as the rest
%[source: SWI-Prolog 10.1.13 library/prolog_profile.pl, profile_data/1 callers].
metta_py_recursive_calls(Node, Recursive) :-
    (   get_dict(callers, Node, Callers),
        memberchk(node('<recursive>', _, _, _, Calls, _, _), Callers)
    ->  Recursive = Calls
    ;   Recursive = 0
    ).

metta_py_tick_seconds(_, Net, _, 0.0) :- Net =< 0, !.
metta_py_tick_seconds(Ticks, Net, Seconds, Answer) :-
    Answer is Ticks * Seconds / Net.

%The first profiled clause supplies a consulted location or its load's path.
%Compiled clauses keep line zero; occurrence-level lines belong to origin().
metta_py_predicate_source(Module:Name/Arity, File, Line) :-
    atom(Name),
    integer(Arity),
    functor(Head, Name, Arity),
    catch(nth_clause(Module:Head, 1, Ref), _, fail),
    !,
    (   clause_property(Ref, file(Path)),
        clause_property(Ref, line_count(Line))
    ->  atom_string(Path, File)
    ;   filereader:source_load_assertion(Load, artifact, Ref),
        filereader:metta_source_load(Path, _, Load, _)
    ->  atom_string(Path, File), Line = 0
    ;   File = "", Line = 0
    ).
metta_py_predicate_source(_, "", 0).

%What the profiler cannot say about a registered function: which tier put it
%there, and whether the clause index its callers rely on actually exists.
%
%Index quality is read from predicate_property/2 rather than
%library(prolog_jiti)'s jiti_list/1, which prints its table instead of
%answering it. `speedup` is the ratio SWI itself computes for the index it
%chose, so 1.0 means the argument does not discriminate and every call walks
%the clause list. `realised` matters as much: SWI builds an index on first
%need, so an unrealised index is one no call has asked for yet rather than a
%bad one.
%The tier comes from the two engine facts lib_reflect.pl's 'engine-origin'/2
%reads, not from that predicate, which lives in a library the profiler cannot
%require to be loaded. Its builtin and special-form branches are absent here
%on purpose: a profiled name is one an extension registered, and neither of
%those can be.
metta_py_function_shape(Name0, [Tier, Detail, Arities, Determinism]) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    (   catch(metta_function_determinism(Name, Mode), _, fail)
    ->  atom_string(Mode, Determinism)
    ;   Determinism = ""
    ),
    (   metta_function_origin(Name, Tier0, Detail0)
    ->  atom_string(Tier0, Tier), metta_py_origin_part(Detail0, Detail)
    ;   fun(Name)
    ->  Tier = "equation",
        ( fun_in(Module, Name) -> atom_string(Module, Detail) ; Detail = "" )
    ;   Tier = "absent", Detail = ""
    ),
    ( fun_in(Home, Name) -> true ; metta_py_module('&self', Home) ),
    spaces:metta_ensure_compiled(Name),
    findall([Arity, Speedup, Realised],
            ( arity(Name, Arity),
              metta_py_index_quality(Home, Name, Arity, Speedup, Realised) ),
            Arities).

metta_py_origin_part(Part, String) :-
    ( atom(Part) -> atom_string(Part, String)
    ; string(Part) -> String = Part
    ; term_string(Part, String) ).

%The best index SWI has for this predicate, or 1.0 for none, which is the
%same number a useless index scores and reads the same way: no discrimination.
%The arities come from the engine's name-wide arity/2 register, so this is
%asked about Name/Arity pairs the reported module does not have. indexed/1 is
%one of the properties SWI answers by running its undefined-procedure trap,
%which searches the whole autoload library index before raising the existence
%error: 1,030 inferences to learn "no index". The guard's two arms keep the
%answer exactly: current_predicate/1 admits what the module has, and
%implementation_module/1 admits what it would autoload, for 33 and without
%loading it, so the property behind the guard still resolves what it used to
%[source: /usr/lib/swi-prolog/boot/syspred.pl, property_predicate/2]
%[measured 2026-09-06: 1,030 inferences against 8 for a name the module has,
%and 37 against 9 with the guard;
%tested: extensions/python/tests/ch18_performance/test_function_shape_cost.py;
%commit=693b1bdb6ed06cd0ba01e901a8a6d774bc733d19].
metta_py_index_quality(Module, Name, Arity, Speedup, Realised) :-
    functor(Head, Name, Arity),
    (   (   current_predicate(Module:Name/Arity)
        ->  true
        ;   predicate_property(Module:Head, implementation_module(Home)),
            Home \== Module
        ),
        predicate_property(Module:Head, indexed(Indexes)),
        Indexes \== []
    ->  findall(S-R, ( member(Index, Indexes),
                       get_dict(speedup, Index, S),
                       get_dict(realised, Index, R0),
                       ( R0 == true -> R = @(true) ; R = @(false) ) ), Pairs),
        sort(1, @>=, Pairs, [Speedup-Realised|_])
    ;   Speedup = 1.0, Realised = @(false)
    ).

%%%%%%%%%% Reclamation %%%%%%%%%%
%
% Everything the process can free now, freed, so a count taken next reads what
% is retained rather than what is merely not collected yet. Python's collector,
% SWI's clause, stack and atom collectors and janus's deferred releases feed
% one another: a Python object holds a blob, a blob or a clause keeps atoms
% alive, and a blob released without the GIL waits for the next
% Prolog-to-Python call before its Python object goes [source
% 2026-09-25T04:25:29+10:00: swipl-devel V10.1.14 packages/swipy/janus/janus.c,
% release_python_object/1 queueing through MyPy_DECREF and py_gil_ensure
% draining through delayed_decref]. So it runs rounds until one is quiet, and
% answers how many that took.
%
% A collection has to be one that RAN, and started after what it should free.
% garbage_collect_clauses/0 and garbage_collect_atoms/0 each return at once,
% having done nothing, while another thread holds that collection, and a clause
% collection keeps every clause erased after it began [source
% 2026-09-25T04:19:30+10:00: swipl-devel V10.1.14 src/pl-proc.c,
% pl_garbage_collect_clauses/0, the COMPARE_AND_SWAP on cgc_active and "clauses
% that were erased before the start generation"; source
% 2026-09-25T04:29:01+10:00: src/pl-atom.c pl_garbage_collect_atoms/0, the
% COMPARE_AND_SWAP on gc_active]. With SWI's collector thread mid-collection a
% single pass therefore reclaimed none of a drop's clauses and none of the atoms
% they named: in plain SWI, with that thread collecting a million erased clauses,
% one pass left all 4000 names of a retracted relation live and one round with
% the thread stopped left none [measured 2026-09-25T04:22:36+10:00: assert and
% retract a million clauses, thread_signal(gc, garbage_collect_clauses), retract
% 4000 facts naming fresh atoms, then count the names]. So the collector thread
% stays stopped for the whole loop, which joins it after the collection it is
% running [source 2026-09-25T04:19:16+10:00: boot/syspred.pl
% set_prolog_gc_thread/1 and boot/gc.pl gc_loop/0], and each collection is
% repeated until SWI's count of collections run (statistics/2's cgc and agc,
% not their _gained counts) moves, which a collection advances as it finishes
% whether or not it freed anything, so one held by any other thread is waited
% out rather than taken for done.
%
% Each clause collection first erases a clause of its own: a clause collection
% starts only when some predicate holds erased clauses, and it reclaims only
% clauses erased before it started, so the erase gives it work to start on and
% puts the generation past everything erased before it, the protocol the
% Prolog suite's collect_materialization_owners/0 uses for the same count.
%
% A round is quiet when Python's collector found nothing, the clause collection
% reclaimed at most the round's own tick, and the live atom and clause counts
% (statistics/2's atoms and clauses) end the round where they began it. What a
% round freed cannot be the test, because what it makes for itself varies with
% the process: SWI hands every clause a collection reclaims, the tick included,
% to each listener on its erase channel as a clause blob [source
% 2026-09-25T05:47:10+10:00: swipl-devel V10.1.14 src/pl-proc.c,
% announceErasedClause/1 called from cleanDefinition/5 for each clause it
% reclaims], and the engine keeps such a listener for the life of any process
% that has published a materialized image (engine/materialize.pl
% ensure_source_owner_listener/0). There every round freed a blob of its own,
% and a rule that no round free an atom never held [measured
% 2026-09-25T05:37:56+10:00: reclamation_unsettled(64, objects(0), clauses(1),
% atoms(1)) after test_materialization's released-index setting; measured
% 2026-09-25T05:44:48+10:00, plain SWI: a tick freed no atom a round without a
% listener and one under a listener, in 499 rounds of 500]. What a round makes
% and frees inside itself leaves the live counts as they were. A blob that
% outlives its round, as one in those 500 did, holds its clause as well and
% moves both counts, so that round is not quiet and the next frees it. The
% reclaimed bound covers the one case both counts could miss: a clause
% reclaimed in the round whose tick blob outlived it, freeing one atom as it
% went, would leave each count where it was.
:- dynamic metta_py_reclaim_tick/0.

metta_py_reclaim(Rounds) :-
    current_prolog_flag(gc_thread, Collector),
    setup_call_cleanup(set_prolog_gc_thread(false),
                       metta_py_reclaim_rounds(1, Rounds),
                       set_prolog_gc_thread(Collector)).

metta_py_reclaim_rounds(Round, Rounds) :-
    statistics(atoms, Atoms0),
    statistics(clauses, Clauses0),
    statistics(cgc_gained, Reclaimed0),
    py_call(gc:collect(), Objects),
    metta_py_collection_ran(cgc, metta_py_collect_clauses),
    garbage_collect,
    metta_py_collection_ran(agc, garbage_collect_atoms),
    statistics(atoms, Atoms),
    statistics(clauses, Clauses),
    statistics(cgc_gained, Reclaimed),
    (   Objects =:= 0, Atoms =:= Atoms0, Clauses =:= Clauses0,
        Reclaimed - Reclaimed0 =< 1
    ->  Rounds = Round
    ;   Round < 64
    ->  Next is Round + 1,
        metta_py_reclaim_rounds(Next, Rounds)
    ;   ReclaimedClauses is Reclaimed - Reclaimed0,
        ClausesMoved is Clauses - Clauses0,
        AtomsMoved is Atoms - Atoms0,
        throw(error(system_error(reclamation_unsettled(Round, objects(Objects),
                                                       reclaimed_clauses(ReclaimedClauses),
                                                       live_clauses_moved(ClausesMoved),
                                                       live_atoms_moved(AtomsMoved))),
                    context(metta_py_reclaim/1,
                            'no round left the process as it found it; another thread keeps changing it')))
    ).

%Retracted rather than erased through a clause reference, which would add a
%blob of the round's own to every round [measured 2026-09-25T05:44:48+10:00,
%plain SWI: a tick erased through a held reference freed one atom a round
%without a listener and two under one].
metta_py_collect_clauses :-
    assertz(metta_py_reclaim_tick),
    retract(metta_py_reclaim_tick),
    garbage_collect_clauses.

metta_py_collection_ran(Count, Collection) :-
    statistics(Count, Before),
    call(Collection),
    statistics(Count, After),
    (   After > Before
    ->  true
    ;   sleep(0.001),
        metta_py_collection_ran(Count, Collection)
    ).
