% Purpose: measure engine execution and report predicate indexes.
% Assumes: loaded through _binding/shim.pl in its host module.
%   SWI-Prolog 10.1.13's profiler primitive `'$profile'/4` (src/pl-prof.c),
%   the one library(prolog_profile) profile/2 runs: it resets the profiler,
%   arms it, runs the goal and stops it, and nothing else.
% Guarantees: compiled profile rows retain their source file through the
%   reader's ownership journal [tested: test_a_profile_exports_as_pstats;
%   commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
%   A profile whose sampler took no sample still answers the goal's answers,
%   with zero samples and ticks and rows carrying their call counts
%   [tested: test_a_profile_with_no_samples_still_answers; commit=WORKTREE].

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
%command=sh extensions/python/test.sh; commit=WORKTREE].
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
