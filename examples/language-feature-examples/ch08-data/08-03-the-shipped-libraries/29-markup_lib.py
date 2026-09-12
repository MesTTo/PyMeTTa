"""Purpose: XML and HTML as expressions, and the selector language over them.

An element is a built term, so `S.element(name, attributes, children)` is how one
is written and `list()` reads one apart. Documents are `G("...")` text; selectors
are built terms whose parameter is held, so `S.descendant(S.item)` passes through
unevaluated. Every selector answers once per match, which `list()` collects.

Guarantees: the same claims as 29-markup_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/29-markup_lib.metta; commit=ed976b0e70c1176a7ef9feabb0359313105c786e].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, G, S, V, lib, solve
from metta._errors.errors import MettaError

#: The document every query below reads, as ground text rather than a name.
ORDER = G("<order id='7'><item sku='a'>apple</item><item sku='b'>pear</item><note/></order>")


def twin(m):
    """Parse, read, select, write, and refuse what the host would repair."""
    m += lib.markup

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    def tree(value):
        """An element as (name, [attribute rows], [children]) tuples, all the way down.

        A text node is a leaf atom, which is not iterable, so `Expression` is the
        one shape to walk and everything else answers itself.
        """
        if not isinstance(value, Expression):
            return value
        parts = list(value)
        if len(parts) != 4 or parts[0] != S.element:
            return value
        _, name, attributes, children = parts
        return (name,
                [tuple(row) for row in attributes],
                [tree(child) for child in children])

    parse_xml, parse_html = m.fn.markup_parse_xml, m.fn.markup_parse_html
    write, select = m.fn.markup_write, m.fn.markup_select
    attribute, text = m.fn.markup_attribute, m.fn.markup_text

    # An element is (element Name Attributes Children): the name a Symbol, each
    # attribute an (attr Name Value) row and the children an expression of elements
    # and Strings. The attribute row is TAGGED because an untagged (id "7") pair is
    # an expression whose head names the engine's identity function, and it would be
    # evaluated as a call where the document is written.
    doc = parse_xml(ORDER).one()
    assert tree(doc) == (
        S.order,
        [(S.attr, S.id, G("7"))],
        [(S.item, [(S.attr, S.sku, G("a"))], [G("apple")]),
         (S.item, [(S.attr, S.sku, G("b"))], [G("pear")]),
         (S.note, [], [])],
    )
    # The shape is the interface: reading the items out of it needs no library call
    # at all, only the children and a pattern.
    children = list(doc)[3]
    pattern = S.element(S.item, (S.attr(S.sku, V.sku),), (V.text,))
    assert [(row.sku, row.text)
            for child in children
            for row in solve(pattern, child)] == [(G("a"), G("apple")), (G("b"), G("pear"))]

    # The three readers over an element. markup-text joins every text node under
    # it, markup-attribute answers one attribute's value and has NO answer for an
    # attribute the element does not carry.
    assert text(doc) == [G("applepear")]
    assert attribute(doc, S.id) == [G("7")]
    assert list(attribute(doc, S.missing)) == []
    assert text(S.element(S.p, (), ())) == [G("")]

    # The selector language. A step names elements and the three modifiers apply to
    # the step they follow, which is how XPath itself spells them.
    assert list(select(doc, (S.descendant(S.item), S.text()))) == [G("apple"), G("pear")]
    assert list(select(doc, (S.descendant(S.item), S.attribute(S.sku)))) == [G("a"), G("b")]
    assert select(doc, (S.descendant(S.item), S.index(2), S.text())) == [G("pear")]
    assert [tree(found) for found in select(doc, S.child(S.item))] == [
        (S.item, [(S.attr, S.sku, G("a"))], [G("apple")]),
        (S.item, [(S.attr, S.sku, G("b"))], [G("pear")]),
    ]
    assert [tree(found) for found in select(doc, S.self(S.order))] == [tree(doc)]
    assert list(select(doc, S.descendant(S.missing))) == []
    # A path walks down: child of a child, with the text of the last step.
    nested = parse_xml(G("<a><b><c>deep</c></b><c>shallow</c></a>")).one()
    assert list(select(nested, (S.child(S.b), S.child(S.c), S.text()))) == [G("deep")]
    assert list(select(nested, (S.descendant(S.c), S.text()))) == [G("shallow"), G("deep")]

    # Writing inverts parsing: the text is the element's own markup, with no
    # declaration and no layout, so it parses back to the same element.
    assert write(S.element(S.item, (S.attr(S.sku, G("a")),), (G("apple"),))) == [
        G('<item sku="a">apple</item>'),
    ]
    assert tree(parse_xml(S.markup_write(doc)).one()) == tree(doc)
    assert write(S.element(S.empty, (), ())) == [G("<empty/>")]
    # An attribute value written as a Number or a Symbol becomes text, because that
    # is all an XML attribute can hold.
    assert write(S.element(S.a, (S.attr(S.n, 1), S.attr(S.k, S.sym)), ())) == [
        G('<a n="1" k="sym"/>'),
    ]

    # HTML's own rules are the host's: an omitted end tag HTML allows is not an
    # error, so this parses and nests the second paragraph inside the first.
    assert tree(parse_html(G("<p>one<p>two")).one()) == (
        S.p, [], [G("one"), (S.p, [], [G("two")])],
    )
    assert text(S.markup_parse_html(G("<p>a<b>c</b></p>"))) == [G("ac")]

    # Every parse is STRICT, which is the difference between this library and the
    # host's own reader: a missing end tag, a stray close tag and text outside any
    # element are each repaired by the parser with a warning on stderr and a DOM
    # anyway, and each is a refusal here.
    assert refused(S.markup_parse_xml(G("<a><b></a>")))
    assert refused(S.markup_parse_xml(G("<a>")))
    assert refused(S.markup_parse_xml(G("not markup at all")))
    assert refused(S.markup_parse_xml(G("")))
    # An external entity is never fetched: the host refuses a SYSTEM entity and
    # this turns the warning into an error, where it would otherwise answer an
    # element with the entity's content silently missing.
    assert refused(S.markup_parse_xml(
        G("<!DOCTYPE d [<!ENTITY e SYSTEM '/etc/passwd'>]><d>&e;</d>")))

    # A selector the library does not know is refused with the five forms listed,
    # and a modifier with no step before it has nothing to modify.
    assert refused(S.markup_select(doc, S.nosuch(S.item)))
    assert refused(S.markup_select(doc, (S.text(), S.descendant(S.item))))
    assert refused(S.markup_select(doc, S.index(1)))
    # A value that is not an element is refused by every reader. A Number is
    # refused by the DECLARATION rather than by the head, so it answers the
    # engine's own BadArgType; if-error reads both the same way.
    assert list(m.eval(S.markup_text(7))) == [
        S.Error(S.markup_text(7), S.BadArgType(1, S.Expression, S.Number)),
    ]
    assert refused(S.markup_write(S.nosuch()))


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 30 claims cover the six heads, the six selector
#: forms, the tagged attribute row and the nine refusals
#: [measured 2026-09-12: 110431 inferences against the example's 104638, minimum
#: of three serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/29-markup_lib.metta;
#: fixture=lib_markup at its functional commit, artifacts purged before the run;
#: commit=ed976b0e70c1176a7ef9feabb0359313105c786e].
#: RE-PINNED 2026-09-12, 110431 to 110488 (+57), every complaint from the host
#: parser mapped to one refusal, which added the empty-document case [measured
#: 2026-09-12: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ed976b0e70c1176a7ef9feabb0359313105c786e].
BUDGET = 110488
