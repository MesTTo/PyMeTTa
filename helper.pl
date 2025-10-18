crun(ARG,OUT) :-
  current_predicate(run/2),
  run(ARG,P),
  repr(P,OUT).

process_metta_string_silent(S, RunArg) :-
    ( current_prolog_flag(argv, Args) -> true ; Args = [] ),
    append(Args, ['--silent'], Args1),
    set_prolog_flag(argv,Args1),
    process_metta_string(S, RunArg).
