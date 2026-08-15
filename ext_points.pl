%Memoization dispatch: a handler decides whether a call is served from a
%cache. A function name alone does not identify a function, because a named
%space compiles its equations into a module of its own, so a handler that
%keeps state per function reads current_metta_module/1 to learn which module
%the call site is in. It reads it rather than being passed it because this
%hook is consulted on every compiled call site.
:- multifile metta_memoized_dispatch_call/4.
:- multifile metta_on_function_changed/1.
:- multifile metta_on_function_removed/1.

%Space writes: every 'add-atom'/3 and 'remove-atom'/3 runs these hooks with
%the space and the term, after the write. A standing query, a subscription,
%an index or a mirror hangs off them; with no handlers nothing changes.
%A plain-atom removal is retractall, which cannot say whether anything was
%there, so a removal hook may fire for an atom that was never stored;
%handlers re-check the space rather than trust the event.
:- multifile metta_on_atom_added/2.
:- multifile metta_on_atom_removed/2.
:- dynamic metta_on_atom_added/2.
:- dynamic metta_on_atom_removed/2.

%Foreign spaces: a host runtime may declare a space whose atoms live outside
%the Prolog database, in a database, a dataframe, a service. match/4,
%'add-atom'/3, 'remove-atom'/3 and 'get-atoms'/2 consult these hooks first
%for a declared name; with no declarations nothing changes.
:- multifile metta_foreign_space/1.
:- multifile metta_foreign_match/2.
:- multifile metta_foreign_add/2.
:- multifile metta_foreign_remove/3.
:- multifile metta_foreign_atoms/2.

%Extra type candidates for grounded host objects, beyond the object's own
%classes: a protocol the object satisfies may name a type, so a declared
%(-> DLTensor ...) can hold across libraries.
:- multifile py_object_extra_type/2.

%A host bridge may compute an object's type names itself: values can sit in
%envelope objects the boundary must not rewrite, so the names, plain text,
%are what crosses rather than the value. When a bridge answers, its names
%are the object's types; with none, the local class walk applies.
:- multifile py_object_type_names/2.

:- use_module(library(prolog_wrap)).

metta_memoized_dispatch_call(_, _, _, _) :- fail.
metta_on_function_changed(_).
metta_on_function_removed(_).

%Atom hooks wrap the write predicates only while a multifile handler exists.
%prolog_listen/2 sees clauses loaded later, so an engine without handlers keeps
%the original direct write path. Multiple handlers still run through forall/2.

metta_atom_hook_clause(added, Ref) :- clause(metta_on_atom_added(_, _), _, Ref).
metta_atom_hook_clause(removed, Ref) :- clause(metta_on_atom_removed(_, _), _, Ref).

enable_metta_atom_hook(added) :-
    current_predicate_wrapper(user:metta_add_atom(_, _, _), metta_atom_added_hooks, _, _), !.
enable_metta_atom_hook(added) :-
    wrap_predicate(user:metta_add_atom(Space, Term, _Result), metta_atom_added_hooks, Wrapped,
                   user:run_metta_atom_added_hooks(Wrapped, Space, Term)).
enable_metta_atom_hook(removed) :-
    current_predicate_wrapper(user:metta_remove_atom(_, _, _), metta_atom_removed_hooks, _, _), !.
enable_metta_atom_hook(removed) :-
    wrap_predicate(user:metta_remove_atom(Space, Term, Removed), metta_atom_removed_hooks, Wrapped,
                   user:run_metta_atom_removed_hooks(Wrapped, Space, Term, Removed)).

run_metta_atom_added_hooks(Wrapped, Space, Term) :-
    call(Wrapped),
    forall(metta_on_atom_added(Space, Term), true).

run_metta_atom_removed_hooks(Wrapped, Space, Term, Removed) :-
    call(Wrapped),
    ( Removed == true
      -> forall(metta_on_atom_removed(Space, Term), true)
      ; true ).

disable_metta_atom_hook(added) :-
    ( unwrap_predicate(user:metta_add_atom/3, metta_atom_added_hooks) -> true ; true ).
disable_metta_atom_hook(removed) :-
    ( unwrap_predicate(user:metta_remove_atom/3, metta_atom_removed_hooks) -> true ; true ).

sync_metta_atom_hook(Kind) :- ( metta_atom_hook_clause(Kind, _)
                                -> enable_metta_atom_hook(Kind)
                                ; disable_metta_atom_hook(Kind) ).

metta_atom_hook_changed(Kind, Action, Context) :-
    ( ( Action == asserta ; Action == assertz ; Action == rollback(retract) )
      -> enable_metta_atom_hook(Kind)
    ; ( Action == retract ; Action == rollback(asserta) ; Action == rollback(assertz) )
      -> ( metta_atom_hook_clause(Kind, Other), Other \== Context
           -> true ; disable_metta_atom_hook(Kind) )
    ; Action == retractall, Context = end(_)
      -> sync_metta_atom_hook(Kind)
    ; true ).

:- prolog_listen(metta_on_atom_added/2, metta_atom_hook_changed(added)).
:- prolog_listen(metta_on_atom_removed/2, metta_atom_hook_changed(removed)).
:- sync_metta_atom_hook(added).
:- sync_metta_atom_hook(removed).
:- initialization(sync_metta_atom_hook(added), restore_state).
:- initialization(sync_metta_atom_hook(removed), restore_state).
