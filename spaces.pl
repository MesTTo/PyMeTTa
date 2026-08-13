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

%The shared space's storage predicate, asserted by writes; declared so
%a read on a virgin engine fails cleanly instead of erring undefined.
:- dynamic '&self'/3.

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

%A foreign space stores whatever its provider stores, equations included as
%plain atoms; the hook owns the write entirely:
'add-atom'(Space, Term, Result) :- metta_add_atom(Space, Term, Result).

metta_add_atom(Space, Term, true) :- metta_foreign_space(Space), !,
                                     metta_foreign_add(Space, Term).

%Add a function atom:
metta_add_atom(Space, Term, true) :- Term = [=,[FAtom|W],_], !,
                                     add_sexp(Space, Term),
                                     space_module(Space, Module),
                                     register_fun_in(Module, FAtom),
                                     length(W, N),
                                     Arity is N + 1,
                                     assertz(arity(FAtom,Arity)),
                                     once(with_metta_module(Module, translate_clause(Term, Clause))),
                                     assertz(Module:Clause, Ref),
                                     assertz(translated_from(Ref, Term)),
                                     forall(metta_on_function_changed(FAtom), true),
                                     invalidate_specializations(FAtom),
                                     maybe_print_compiled_clause("added function", Term, Clause).

%Add an atom to the space:
metta_add_atom(Space, Term, true) :- add_sexp(Space, Term).

'remove-atom'(Space, Term, Removed) :- metta_remove_atom(Space, Term, Removed).

metta_remove_atom(Space, Term, Removed) :- metta_foreign_space(Space), !,
                                           metta_foreign_remove(Space, Term, Removed).

%%Remove a function atom:
metta_remove_atom(Space, Term, Removed) :- Term = [=,[F|Args],Body], !,
                                           remove_sexp(Space, Term),
                                           ( nb_current(F, Prev) -> true ; Prev = [] ),
                                           (   select(fun_meta(Args, Body), Prev, Rest)
                                               -> ( Rest == [] -> nb_delete(F)
                                                                ; nb_setval(F, Rest) ) ; true ),
                                           space_module(Space, Module),
                                           %Only this space's compiled clauses die: the same equation
                                           %imported into two spaces compiles into two modules, and the
                                           %term-keyed lookup alone would erase the twin space's clause
                                           %and, through the term-wide retractall, its record with it.
                                           findall(Ref, ( translated_from(Ref, Term),
                                                          clause_property(Ref, module(Module)) ), Refs),
                                           forall(member(Ref, Refs), ( erase(Ref),
                                                                       retractall(translated_from(Ref, _)) )),
                                           forall(metta_on_function_changed(F), true),
                                           invalidate_specializations(F),
                                           ( module_owns_function(Module, F) -> true
                                                                              ; unregister_fun_in(Module, F) ),
                                           ( \+ function_still_defined(F)
                                             -> retractall(fun(F)), unregister_fun_everywhere(F),
                                                forall(metta_on_function_removed(F), true)
                                             ; true ),
                                           ( Refs = [] -> Removed = false
                                           ; Removed = true ).

%Remove all same atoms:
metta_remove_atom(Space, Term, true) :- remove_sexp(Space, Term).

%Choose the provider once for the whole match. A conjunction may enumerate
%millions of native candidates, so routing every conjunct back through match/4
%would repeat the foreign-space probe for every candidate.
match(Space, Pattern, OutPattern, Result) :- nonvar(Space),
                                             metta_foreign_space(Space), !,
                                             match_foreign(Space, Pattern, OutPattern, Result).
%A native space is a Prolog predicate named after the space. Its conjunction
%can stay on the direct helper; a space implemented by an earlier multifile
%match/4 clause, such as MORK, must route each conjunct through match/4 so its
%own provider clause sees it.
match(Space, Pattern, OutPattern, Result) :- nonvar(Pattern), Pattern = [Comma|_], Comma == ',',
                                             nonvar(Space),
                                             current_predicate(Space/_), !,
                                             match_native(Space, Pattern, OutPattern, Result).
match(Space, Pattern, OutPattern, Result) :- nonvar(Pattern), Pattern = [Comma|_], Comma == ',', !,
                                             match_routed(Space, Pattern, OutPattern, Result).
match(Space, Pattern, OutPattern, Result) :- match_native(Space, Pattern, OutPattern, Result).

match_routed(_, LComma, OutPattern, Result) :- LComma == [','], !,
                                               Result = OutPattern.
match_routed(Space, [','|[Head|Tail]], OutPattern, Result) :-
    match(Space, Head, conj, conj),
    match_routed(Space, [','|Tail], OutPattern, Result).

%A foreign provider enumerates candidates. Unification against the pattern
%stays here, so an approximate provider cannot change matching soundness.
match_foreign(_, LComma, OutPattern, Result) :- LComma == [','], !,
                                                Result = OutPattern.
match_foreign(Space, [Comma|[Head|Tail]], OutPattern, Result) :- Comma == ',', !,
                                                                 match_foreign(Space, Head, conj, conj),
                                                                 match_foreign(Space, [','|Tail], OutPattern, Result).
match_foreign(Space, PatternVar, OutPattern, Result) :- var(PatternVar), !,
                                                        metta_foreign_atoms(Space, PatternVar),
                                                        \+ cyclic_term(OutPattern),
                                                        Result = OutPattern.
match_foreign(Space, Pattern, OutPattern, Result) :- metta_foreign_match(Space, Pattern),
                                                     \+ cyclic_term(OutPattern),
                                                     Result = OutPattern.

%Native conjunctions call their space predicate directly. The recursive helper
%keeps the provider decision outside the candidate loop.
match_native(_, LComma, OutPattern, Result) :- LComma == [','], !,
                                               Result = OutPattern.
match_native(Space, [Comma|[Head|Tail]], OutPattern, Result) :- Comma == ',',
                                                                var(Head), !,
                                                                get_native_atom(Space, Head),
                                                                \+ cyclic_term(OutPattern),
                                                                match_native(Space, [','|Tail], OutPattern, Result).
match_native(Space, [Comma|[[Rel|PatArgs]|Tail]], OutPattern, Result) :- Comma == ',', !,
                                                                        Term =.. [Space, Rel | PatArgs],
                                                                        catch(Term, E, recover_failure(E)),
                                                                        \+ cyclic_term(OutPattern),
                                                                        match_native(Space, [','|Tail], OutPattern, Result).

%When the native pattern itself is a variable, enumerate all atoms.
match_native(Space, PatternVar, OutPattern, Result) :- var(PatternVar), !,
                                                       get_native_atom(Space, PatternVar),
                                                       \+ cyclic_term(OutPattern),
                                                       Result = OutPattern.

match_native(Space, [Rel|PatArgs], OutPattern, Result) :- Term =.. [Space, Rel | PatArgs],
                                                          catch(Term, E, recover_failure(E)),
                                                          \+ cyclic_term(OutPattern),
                                                          Result = OutPattern.

'get-atoms'(Space, Pattern) :- nonvar(Space),
                               metta_foreign_space(Space), !,
                               metta_foreign_atoms(Space, Pattern).

%Get all atoms in space, irregard of arity:
'get-atoms'(Space, Pattern) :- get_native_atom(Space, Pattern).

get_native_atom(Space, Pattern) :- current_predicate(Space/Arity),
                                   functor(Head, Space, Arity),
                                   clause(Head, true),
                                   Head =.. [Space | Pattern].
