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

metta_memoized_dispatch_call(_, _, _, _) :- fail.
metta_on_function_changed(_).
metta_on_function_removed(_).
metta_on_atom_added(_, _).
metta_on_atom_removed(_, _).
