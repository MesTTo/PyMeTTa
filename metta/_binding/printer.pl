% Purpose: print tagged terms and refuse lossy boolean symbols.
% Assumes: loaded through _binding/shim.pl in its host module.

%Print a tagged term the way MeTTa prints it:
%A symbol spelled like a boolean has no faithful text form: the engine's
%term for it IS the boolean (Prolog true/false), so only the wire tag still
%knows the caller meant a symbol, and text written here would read back as
%the boolean. Refuse at this door, where the tag is visible, with the
%writer's own refusal shape; the engine-side writer cannot make this
%distinction because both kinds are one atom there.
metta_py_swrite(Tagged, String) :-
    (   metta_py_wire_boolean_symbol(Tagged, Bad)
    ->  throw(error(metta_unwritable_text(Bad),
                    context(swrite/2,
                            'printed form would read back as a different value')))
    ;   metta_py_decode_shared(Tagged, Term, _),
        swrite(Term, String)
    ).

%Janus hands the wire's leaves over as atoms while Prolog-built wrappers use
%strings, so both spellings of a tag are accepted here.
metta_py_wire_boolean_symbol([Tag, Name], Bad) :-
    metta_py_wire_tag(Tag, s),
    (   atom(Name) -> Bad = Name ; string(Name), atom_string(Bad, Name) ),
    % policy-inventory-exempt: codec-version-identity; reason=these four spellings are how the wire encodes a boolean, so a symbol carrying one would print as text that reads back as a boolean rather than as itself; evidence=extensions/python/metta/_binding/shim.pl:metta_py_wire_boolean_symbol/2
    memberchk(Bad, [true, false, 'True', 'False']).
metta_py_wire_boolean_symbol([Tag, Items], Bad) :-
    metta_py_wire_tag(Tag, e),
    is_list(Items),
    member(Item, Items),
    metta_py_wire_boolean_symbol(Item, Bad),
    !.

metta_py_wire_tag(Tag, Wanted) :-
    (   atom(Tag) -> Tag == Wanted
    ;   string(Tag), atom_string(Wanted, Tag)
    ).
