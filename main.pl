:- ensure_loaded(metta).

%Tokens the engine reads for itself, which are therefore not the file to run.
%`backends` asks src/metta.pl to load every native backend that is built; it is
%stripped here for the same reason the silent flags are, so that a bare
%`swipl -s src/main.pl -- backends` still means the demo rather than a file
%called "backends".
is_engine_flag(silent).
is_engine_flag('--silent').
is_engine_flag('-s').
is_engine_flag(backends).

strip_engine_flags([], []).
strip_engine_flags([Arg|Rest], Filtered) :-
        is_engine_flag(Arg),
        !,
        strip_engine_flags(Rest, Filtered).
strip_engine_flags([Arg|Rest], [Arg|Filtered]) :-
        strip_engine_flags(Rest, Filtered).

prologfunc(X,Y) :- Y is X+1.

prolog_interop_example :- import_prolog_function(prologfunc, _),
                          process_metta_string("(= (mettafunc $x) (prologfunc $x))", _),
                          listing(mettafunc),
                          mettafunc(30, R),
                          format("mettafunc(30) = ~w~n", [R]).

%The demo runs every loaded backend's own smoke test. It used to call
%mork_test/0 by name behind an `Args = [mork]` branch, which is why this file
%knew a backend existed at all; with no backend loaded the forall runs nothing
%and the demo is what it always was.
main :- current_prolog_flag(argv, RawArgs),
        strip_engine_flags(RawArgs, Args),
        ( Args = [] -> prolog_interop_example,
                       forall(metta_backend_selftest, true)
        ; Args = [File|_] -> load_metta_file(File,Results),
                             maplist(swrite,Results,ResultsR),
                             maplist(format("~w~n"), ResultsR)
        ),
        halt.

:- initialization(main, main).
