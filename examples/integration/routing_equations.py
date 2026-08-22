"""Purpose: the subsumption frame on the smallest possible case: an app is a
space, every route is an equation, a request reduces through whichever route
matches, the catch-all equation is the 404, and middleware is composition.
Nothing was built to make this work.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

from petta import MeTTa, S, Expression

app = MeTTa().space()
app.run(
    '(= (route home) (Page 200 "Welcome"))\n'
    '(= (route about) (Page 200 "About us"))\n'
    "(= (route $other) (NotFound 404 $other))\n"
    "(= (handle $req) (once (route $req)))\n"
    "(= (logged $req) (let $res (handle $req) (Logged $req $res)))"
)
check("a route", app.run("!(handle home)"), [[Expression(S.Page, 200, "Welcome")]])
check("the 404", app.run("!(handle nowhere)"), [[Expression(S.NotFound, 404, S.nowhere)]])
check("middleware is composition", app.run("!(logged about)"),
      [[Expression(S.Logged, S.about, Expression(S.Page, 200, "About us"))]])
done("routing_equations")
