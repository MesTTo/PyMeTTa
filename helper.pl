:- dynamic run_result/1.

get_results(OUT) :-
  run_result(P),
  repr(P,OUT).

process_metta_string_silent(S) :-
    ( current_prolog_flag(argv, Args) -> true ; Args = [] ),
    append(Args, ['--silent'], Args1),
    set_prolog_flag(argv,Args1),
    process_metta_string(S).
