%Since both normal add-attom call and function additions needs to add the S-expression:
add_sexp(Space, [Rel|Args]) :- Term =.. [Space, Rel | Args],
                               assertz(Term).

%Same but for removal:
remove_sexp(Space, [Rel|Args]) :- Term =.. [Space, Rel | Args],
                                  retractall(Term).

%Which module a space's compiled clauses live in. &self keeps using the default
%module, so every existing program compiles and runs exactly as before; any other
%named space gets its own, which is what makes two spaces able to define the same
%function without answering from each other's equations. A goal unresolved in a
%module falls back to user, so builtins and library functions still reach.
space_module('&self', user) :- !.
space_module(Space, Space).

%Whether any module still holds a clause for a function. `user` is always
%checked, because a function read from a file is compiled by process_form/3
%rather than by add-atom/3 and so has no fun_in/2 record of its own.
function_still_defined(F) :- ( fun_in(Module, F) ; Module = user ),
                             current_predicate(Module:F/Arity),
                             functor(Head, F, Arity),
                             clause(Module:Head, _, _),
                             !.

%Whether this module itself holds a clause for a function. Inherited clauses
%do not count: clause/3 sees user's clauses through module inheritance, and
%counting those would keep a module's claim alive on another space's strength.
module_owns_function(Module, F) :- current_predicate(Module:F/Arity),
                                   functor(Head, F, Arity),
                                   clause(Module:Head, _, Ref),
                                   clause_property(Ref, module(Module)),
                                   !.

%Add a function atom:
'add-atom'(Space, Term, true) :- Term = [=,[FAtom|W],_], !,
                                 add_sexp(Space, Term),
                                 space_module(Space, Module),
                                 register_fun_in(Module, FAtom),
                                 length(W, N),
                                 Arity is N + 1,
                                 assertz(arity(FAtom,Arity)),
                                 once(with_metta_module(Module, translate_clause(Term, Clause))),
                                 assertz(Module:Clause, Ref),
                                 assertz(translated_from(Ref, Term)),
                                 metta_on_function_changed(FAtom),
                                 invalidate_specializations(FAtom),
                                 maybe_print_compiled_clause("added function", Term, Clause).

%Add an atom to the space:
'add-atom'(Space, Term, true) :- add_sexp(Space, Term).

%%Remove a function atom:
'remove-atom'(Space, Term, Removed) :- Term = [=,[F|Args],Body], !,
                                       remove_sexp(Space, Term),
                                       catch(nb_getval(F, Prev), _, Prev = []),
                                       (   select(fun_meta(Args, Body), Prev, Rest)
                                           -> ( Rest == [] -> nb_delete(F)
                                                            ; nb_setval(F, Rest) ) ; true ),
                                       findall(Ref, translated_from(Ref, Term), Refs),
                                       forall(member(Ref, Refs), erase(Ref)),
                                       retractall(translated_from(_, Term)),
                                       metta_on_function_changed(F),
                                       invalidate_specializations(F),
                                       space_module(Space, Module),
                                       ( module_owns_function(Module, F) -> true
                                                                          ; retractall(fun_in(Module, F)) ),
                                       ( \+ function_still_defined(F)
                                         -> retractall(fun(F)), retractall(fun_in(_, F)),
                                            metta_on_function_removed(F)
                                         ; true ),
                                       ( Refs = [] -> Removed = false ; Removed = true ).

%Remove all same atoms:
'remove-atom'(Space, Term, true) :- remove_sexp(Space, Term).

%Match for conjunctive pattern
match(_, LComma, OutPattern, Result) :- LComma == [','], !,
                                        Result = OutPattern.
match(Space, [Comma|[Head|Tail]], OutPattern, Result) :- Comma == ',', !,
                                                         append([Space], Head, List),
                                                         Term =.. List,
                                                         catch(Term, _, fail),
                                                         \+ cyclic_term(OutPattern),
                                                         match(Space, [','|Tail], OutPattern, Result).

% When the pattern list itself is a variable -> enumerate all atoms
match(Space, PatternVar, OutPattern, Result) :- var(PatternVar), !,
                                                'get-atoms'(Space, PatternVar),
                                                \+ cyclic_term(OutPattern),
                                                Result = OutPattern.

%Match for pattern:
match(Space, [Rel|PatArgs], OutPattern, Result) :- Term =.. [Space, Rel | PatArgs],
                                                   catch(Term, _, fail),
                                                   \+ cyclic_term(OutPattern),
                                                   Result = OutPattern.

%Get all atoms in space, irregard of arity:
'get-atoms'(Space, Pattern) :- current_predicate(Space/Arity),
                               functor(Head, Space, Arity),
                               clause(Head, true),
                               Head =.. [Space | Pattern].
