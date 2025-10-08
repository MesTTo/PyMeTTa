crun(ARG,OUT) :-
  current_predicate(run/2),
  run(ARG,P),
  convert_term(P,OUT).

convert_term(Var, Str) :-
    var(Var), !,
    term_to_atom(Var, VAtom),
    atom_concat('$', VAtom, Str).

convert_term(Atom, Atom) :-
    atom(Atom), !.

convert_term(Number, Number) :-
    number(Number), !.

convert_term([],'()') :- !.

convert_term(List, Str) :-
    is_list(List), !,
    List = [Head | Tail],
    convert_term(Head, HStr),
    maplist(convert_term, Tail, TStrs),
    atomic_list_concat([HStr | TStrs], ' ', Content),
    atomic_list_concat(['(', Content, ')'], Str).

process_metta_string_silent(S, RunArg) :-
    ( current_prolog_flag(argv, Args) -> true ; Args = [] ),
    append(Args, ['--silent'], Args1),
    set_prolog_flag(argv,Args1),
    process_metta_string(S, RunArg).
