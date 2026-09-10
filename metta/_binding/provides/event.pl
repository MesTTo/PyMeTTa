% Purpose: supply the Python binding's event seam clauses.
% Assumes: bindinggen projects each row into its declared load audience
% and defining module.
% Guarantees: every supplied head has this file's engine kind
% [tested: test_binding_provisions_keep_audience_and_kind; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].

provides_declaration(host, metta_python_bounds, catalog_row_changed/2).

provides(host, metta_python_bounds, (
seam:catalog_row_changed(_Event, [limit, Name|_]) :-
    ( current_transaction(_) -> metta_py_bound_transaction ; true ),
    py_call('metta._catalog.bounds':bound_row_changed(Name), _)
)).

provides_declaration(host, user, atom_added/2).

provides_declaration(host, user, atom_removed/2).

provides_declaration(host, user, segment_committed/1).

provides_template(host, user, atom_added, (
seam:atom_added(Space, Term) :- metta_py_notify_atom_added(Space, Term)
)).

provides_template(host, user, atom_removed, (
seam:atom_removed(Space, Term) :- metta_py_notify_atom_removed(Space, Term)
)).

provides_template(host, user, segment_committed, (
seam:segment_committed(Spaces) :- metta_py_notify_segment_committed(Spaces)
)).
