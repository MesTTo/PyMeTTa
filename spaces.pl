% Purpose: store MeTTa atoms, compile equations into per-space modules, and
%   route matching to native and foreign space providers.
% Guarantees:
%   - Every native space stores its atoms in a private data module that does
%     not inherit user predicates [tested: spaces_storage_modules].
%   - Five 2,000-row native joins take 270305 direct and 270307 prepared
%     inferences [measured: 270305 and 270307 inferences on 2026-08-15].
%   - Native spaces preserve scalar atoms and expressions as distinct values
%     [tested 2026-08-14: spaces_arbitrary_atoms].
%   - Removing one scoped get-type rule keeps sibling extension rules visible
%     [tested 2026-08-15: spaces_type_extensions].
%   - Clearing a native space clears its import life without making wildcard
%     atom removal touch that life [tested 2026-08-15:
%     filereader_import_lifecycle].
%   - Dynamic function registration is atomic and failed source loads remove
%     its asserted compiler state [tested 2026-08-14:
%     spaces_registration_atomicity, filereader_source_rollback].
% Guarded by: '$petta_native_storage' serializes private module creation and
%   publication in native_storage_module_cache/2.
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

% Storage modules are separate from execution modules. They inherit nothing,
% so a user predicate cannot appear as a space atom, and unknown arities fail
% without a catch on the indexed read path. The fixed prefix maps every space
% atom injectively to one module name.
native_storage_module(Space, Module) :-
    atom_concat('$petta_atoms:', Space, Module).

:- dynamic native_storage_module_cache/2.
:- dynamic petta_py_add_hooks_idle/1.

%Only a module that actually holds something belongs to somebody else.
%current_module/1 is not that test: SWI creates a module as a side effect of
%merely naming it, including from read-only introspection, so
%predicate_property('$petta_atoms:&kb':anything, dynamic) was enough to make
%&kb throw on every write for the life of the process, with clear/1 reporting
%success and changing nothing. An empty module of that name is ours to claim
%[tested: spaces_registration:naming_the_storage_module_does_not_claim_it].
native_storage_module_occupied(Module) :-
    current_module(Module),
    predicate_property(Module:Head, defined),
    \+ predicate_property(Module:Head, imported_from(_)),
    \+ predicate_property(Module:Head, foreign), !.

native_storage_ready(Module) :-
    current_predicate(Module:'$petta_native_storage'/0),
    predicate_property(Module:'$petta_native_storage', dynamic),
    \+ predicate_property(Module:'$petta_native_storage',
                           imported_from(_)).

native_storage_module_ready(Space, Module) :-
    native_storage_module_cache(Space, Module).

ensure_native_storage_module(Space, Module) :-
    native_storage_module_cache(Space, Module), !.
ensure_native_storage_module(Space, Module) :-
    native_storage_module(Space, Module),
    with_mutex('$petta_native_storage',
               ensure_native_storage_module_locked(Space, Module)).

ensure_native_storage_module_locked(Space, Module) :-
    native_storage_module_cache(Space, Module), !.
ensure_native_storage_module_locked(Space, Module) :-
    native_storage_ready(Module), !,
    assertz(native_storage_module_cache(Space, Module)).
ensure_native_storage_module_locked(Space, Module) :-
    ( native_storage_module_occupied(Module)
      -> throw(error(permission_error(create, native_space_storage, Module),
                     context(ensure_native_storage_module/2,
                             'the reserved storage module name is already in use')))
    ; set_prolog_flag(Module:unknown, fail),
      dynamic(Module:'$petta_native_storage'/0),
      assertz(native_storage_module_cache(Space, Module)) ).

%The dynamic marker and module properties survive transaction rollback even
%when its cache fact does not. A later write can therefore recover the cache
%instead of finding a stranded reserved module name [tested:
%spaces_registration:rolled_back_first_write_keeps_storage_reusable].
:- ensure_native_storage_module('&self', _).
:- dynamic '$petta_atoms:&self':'&self'/3.

% Return the asserted clause reference so a source load can roll back every
% atom it added if a later form fails.
add_sexp(Space, Term) :- add_sexp(Space, Term, _).
%&self's storage module is fixed and created when this file loads, so the
%default space skips the cache lookup that every other space needs. Writes are
%the one path that pays per atom: resolving the module per write cost four
%inferences of every seven on this path [measured 2026-08-15: 7.00 to 5.00
%inferences per write over 200,000 writes].
add_sexp('&self', Term, Ref) :- !, add_sexp_in('$petta_atoms:&self', '&self', Term, Ref).
add_sexp(Space, Term, Ref) :- ensure_native_storage_module(Space, Module),
                              add_sexp_in(Module, Space, Term, Ref).

add_sexp_in(Module, Space, [Rel|Args], Ref) :- !,
                                               Term =.. [Space, Rel | Args],
                                               assertz(Module:Term, Ref).
%A scalar or empty expression cannot be a plain Space(Term) fact, because that
%is already the encoding of the singleton expression (Term). It gets its own
%predicate rather than a marked rule inside the space: a marked rule makes
%every clause of the space predicate a rule, so reading one back has to go
%through clause/2, which walks the clause list instead of using SWI's clause
%indexing. Measured on examples/spaces/matespace.metta, that cost 15.3x,
%99.5 billion instructions against 1,520 billion. Keeping scalars in
%the private scalar predicate leaves expressions as facts a direct indexed
%call reaches.
add_sexp_in(Module, _, Atom, Ref) :-
    assertz(Module:'$petta_native_scalar'(Atom), Ref).

%Remove every atom that unifies with the requested value. Expressions and
%scalars live in different predicates, so neither erases the other.
remove_sexp(Space, [Rel|Args]) :- !,
                                  ( native_storage_module_ready(Space, Module)
                                    -> Term =.. [Space, Rel | Args],
                                       retractall(Module:Term)
                                     ; true ).
remove_sexp(Space, Atom) :-
    ( native_storage_module_ready(Space, Module)
      -> retractall(Module:'$petta_native_scalar'(Atom))
    ; true ).

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
module_owns_function(Module, F) :- compiled_function_name(F, Predicate),
                                   current_predicate(Module:Predicate/Arity),
                                   functor(Head, Predicate, Arity),
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
                                     must_be(atom, FAtom),
                                     space_module(Space, Module),
                                     ensure_native_storage_module(Space, Storage),
                                     transaction(add_function_atom(
                                         Storage, Space, Module,
                                         Term, FAtom, W)).

%Add an atom to the space:
metta_add_atom(Space, Term, true) :- add_sexp(Space, Term, Ref),
                                     record_source_assertion(Ref).

%A native batch containing no equations and no observer for this space can
%resolve its storage module once. Equation batches and observed writes keep
%using add-atom/3 so registration and per-atom events retain their ordinary
%behavior.
metta_add_hooks_idle(_) :-
    \+ metta_atom_hook_clause(added, _), !.
metta_add_hooks_idle(Space) :-
    petta_py_add_hooks_idle(Space).

metta_add_atoms(Space, Terms) :-
    \+ metta_foreign_space(Space),
    metta_add_hooks_idle(Space),
    \+ ( member(Term, Terms), Term = [=, [_|_], _] ), !,
    ensure_native_storage_module(Space, Storage),
    forall(member(Term, Terms),
           ( add_sexp_in(Storage, Space, Term, Ref),
             record_source_assertion(Ref) )).
metta_add_atoms(Space, Terms) :-
    forall(member(Term, Terms), 'add-atom'(Space, Term, _)).

%Compile and register a dynamic equation as one database transaction. A
%translation or change-hook error therefore leaves no stored atom, function
%marker, arity, meta-clause, or executable clause behind.
add_function_atom(Storage, Space, Module, Term, FAtom, W) :-
    add_sexp_in(Storage, Space, Term, SpaceRef),
    record_source_assertion(SpaceRef),
    register_fun_in(Module, FAtom),
    length(W, N),
    Arity is N + 1,
    register_arity(FAtom, Arity),
    once(with_metta_module(Module, translate_clause(Term, Clause))),
    assert_function_clause(Module, Clause, Ref),
    record_source_assertion(Ref),
    assertz(translated_from(Ref, Term), SourceRef),
    record_source_assertion(SourceRef),
    forall(metta_on_function_changed(FAtom), true),
    invalidate_specializations(FAtom),
    maybe_print_compiled_clause("added function", Term, Clause).

%A builtin is a static predicate compiled into the engine, so an equation for
%its name in &self would have to assert into it. SWI refuses that with a
%permission error naming assertz/2, the Prolog arity, and the absolute path of
%the engine source file, none of which is language the program that wrote the
%equation can act on. Say it in MeTTa's terms, and say where the definition
%can go: a named space compiles its clauses into a module of its own, which
%shadows the builtin there and leaves every other space's alone
%[tested: spaces_builtin_override].
:- multifile prolog:error_message//1.

assert_function_clause(Module, Clause, Ref) :-
    catch(assertz(Module:Clause, Ref),
          error(permission_error(modify, static_procedure, _), _),
          throw_builtin_redefinition(Module, Clause)).

throw_builtin_redefinition(Module, Clause) :-
    ( Clause = (Head :- _) -> true ; Head = Clause ),
    functor(Head, Name, Arity),
    InputArity is Arity - 1,
    ( Module == user -> Space = '&self' ; Space = Module ),
    throw(error(petta_builtin_redefinition(Name, InputArity, Space),
                context('=', 'a builtin cannot be redefined in this space'))).

prolog:error_message(petta_builtin_redefinition(Name, Arity, Space)) -->
    [ '~w with ~w arguments is a builtin and cannot be redefined in ~w. A \c
       named space compiles its own clauses, so defining it there shadows \c
       the builtin for that space alone.'-[Name, Arity, Space] ].

'remove-atom'(Space, Term, Removed) :- metta_remove_atom(Space, Term, Removed).

metta_remove_atom(Space, Term, Removed) :- metta_foreign_space(Space), !,
                                           metta_foreign_remove(Space, Term, Removed).

%%Remove a function atom:
metta_remove_atom(Space, Term, Removed) :- Term = [=,[F|Args],Body], !,
                                           remove_sexp(Space, Term),
                                           drop_fun_meta(F, Args, Body),
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
                                             native_storage_module_cache(Space, Module), !,
                                             match_native(Module, Space, Pattern, OutPattern, Result).
match(Space, Pattern, OutPattern, Result) :- nonvar(Pattern), Pattern = [Comma|_], Comma == ',', !,
                                             match_routed(Space, Pattern, OutPattern, Result).
%An unbound space would make this dynamic call enumerate every space that has
%ever been written to, so a program in &self could read &kb without naming it.
%Before storage modules the same path reached Term =.. [Space, Rel|Args] and
%raised, which is the behaviour to keep: matching is against a space you name
%[tested: spaces_storage_modules:matching_requires_a_named_space].
match(Space, Pattern, OutPattern, Result) :-
    ( var(Space) -> instantiation_error(Space) ; true ),
    native_storage_module_cache(Space, Module),
    match_native(Module, Space, Pattern, OutPattern, Result).

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
                                                        acyclic_term(OutPattern),
                                                        Result = OutPattern.
match_foreign(Space, Pattern, OutPattern, Result) :- metta_foreign_match(Space, Pattern),
                                                     acyclic_term(OutPattern),
                                                     Result = OutPattern.

%Native conjunctions call their space predicate directly. The recursive helper
%keeps the provider decision outside the candidate loop.
match_native(_, _, LComma, OutPattern, Result) :- LComma == [','], !,
                                                  Result = OutPattern.
match_native(Module, Space, [Comma|[Head|Tail]], OutPattern, Result) :- Comma == ',',
                                                                        var(Head), !,
                                                                        get_native_atom(Module, Space, Head),
                                                                        acyclic_term(OutPattern),
                                                                        match_native(Module, Space, [','|Tail], OutPattern, Result).
match_native(Module, Space, [Comma|[Head|Tail]], OutPattern, Result) :- Comma == ',',
                                                                        ( Head == [] ; \+ is_list(Head) ), !,
                                                                        get_native_scalar_atom_in(Module, Head),
                                                                        acyclic_term(OutPattern),
                                                                        match_native(Module, Space, [','|Tail], OutPattern, Result).
match_native(Module, Space, [Comma|[[Rel|PatArgs]|Tail]], OutPattern, Result) :- Comma == ',', !,
                                                                                native_expression(Module, Space, Rel, PatArgs),
                                                                                acyclic_term(OutPattern),
                                                                                match_native(Module, Space, [','|Tail], OutPattern, Result).

%When the native pattern itself is a variable, enumerate all atoms.
match_native(Module, Space, PatternVar, OutPattern, Result) :- var(PatternVar), !,
                                                               get_native_atom(Module, Space, PatternVar),
                                                               acyclic_term(OutPattern),
                                                               Result = OutPattern.

match_native(Module, _, Pattern, OutPattern, Result) :-
    ( Pattern == [] ; \+ is_list(Pattern) ), !,
    get_native_scalar_atom_in(Module, Pattern),
    acyclic_term(OutPattern),
    Result = OutPattern.

match_native(Module, Space, [Rel|PatArgs], OutPattern, Result) :- native_expression(Module, Space, Rel, PatArgs),
                                                                  acyclic_term(OutPattern),
                                                                  Result = OutPattern.

%Read one stored expression through its private module. The module's unknown
%flag is fail, so a virgin arity fails directly and this indexed path needs no
%exception handler.
native_expression(Module, Space, Rel, PatArgs) :-
    Term =.. [Space, Rel | PatArgs],
    call(Module:Term).

'get-atoms'(Space, Pattern) :- nonvar(Space),
                               metta_foreign_space(Space), !,
                               metta_foreign_atoms(Space, Pattern).

%Get all atoms in space, irregard of arity:
'get-atoms'(Space, Pattern) :- get_native_atom(Space, Pattern).

%Drop every atom a space holds. Expressions and scalars live in different
%predicates, so a caller that wipes only the space predicate would leave the
%scalars standing and a pooled name's next life would inherit them.
clear_native_atoms(Space) :-
    ( native_storage_module_ready(Space, Module)
      -> forall(( current_predicate(Module:Space/Arity),
                  functor(Head, Space, Arity) ),
                retractall(Module:Head)),
         retractall(Module:'$petta_native_scalar'(_))
    ; true ),
    retractall(import_life(Space, _, _)).

%Enumeration answers the space's expressions and then its scalar atoms.
%The read sibling of match/4's guard, and it needs it for the same reason:
%native_storage_module_ready/2 is a dynamic lookup, so an unbound space
%enumerated every space ever written to and !(collapse (get-atoms $any))
%answered with another space's atoms without ever naming it
%[tested: spaces_storage_modules:reading_atoms_requires_a_named_space].
get_native_atom(Space, Pattern) :-
    ( var(Space) -> instantiation_error(Space) ; true ),
    native_storage_module_ready(Space, Module),
    get_native_atom(Module, Space, Pattern).

get_native_atom(Module, Space, Pattern) :-
    current_predicate(Module:Space/Arity),
    functor(Head, Space, Arity),
    clause(Module:Head, true),
    Head =.. [Space | Pattern].
get_native_atom(Module, _, Pattern) :-
    get_native_scalar_atom_in(Module, Pattern).

get_native_scalar_atom_in(Module, Pattern) :-
    Module:'$petta_native_scalar'(Pattern).
