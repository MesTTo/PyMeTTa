/* Purpose: pin the TypeScript space server's own semantics: the two-sided
 *   unifier, multiset store behavior, and every HTTP refusal the protocol
 *   documents. Build and run per the README:
 *     esbuild space_server.test.ts --bundle --platform=node --format=esm \
 *       --outfile=space_server.test.js && node --test space_server.test.js
 * Open Obligations:
 *   To Do: None
 *   Hacks: None
 *   Future Enhancements: None
 */

import { deepStrictEqual, ok, strictEqual } from "node:assert";
import { test } from "node:test";
import {
  SpaceStore,
  startServer,
  unifiable,
  type WireAtom,
} from "./space_server.ts";

const edge = (a: WireAtom, b: WireAtom): WireAtom => ["e", [["s", "edge"], a, b]];
const sym = (name: string): WireAtom => ["s", name];
const v = (name: string): WireAtom => ["v", name];

test("unification renames the two sides apart", () => {
  // (f $x 1) against (f 2 $x): shared-name reading fails this, the
  // renamed-apart reading unifies it, and the engine's answer is unifiable.
  const pattern: WireAtom = ["e", [sym("f"), v("x"), ["n", 1]]];
  const stored: WireAtom = ["e", [sym("f"), ["n", 2], v("x")]];
  ok(unifiable(pattern, stored));
});

test("unification still links repeated variables within one side", () => {
  const twice: WireAtom = ["e", [sym("f"), v("x"), v("x")]];
  ok(unifiable(twice, ["e", [sym("f"), ["n", 2], ["n", 2]]]));
  ok(!unifiable(twice, ["e", [sym("f"), ["n", 2], ["n", 3]]]));
});

test("unification is structural over expressions and exact over leaves", () => {
  ok(unifiable(edge(v("a"), v("b")), edge(sym("x"), sym("y"))));
  ok(!unifiable(edge(sym("x"), sym("y")), edge(sym("y"), sym("x"))));
  ok(!unifiable(["e", [sym("f")]], ["e", [sym("f"), sym("g")]]));
  ok(unifiable(["g", "text"], ["g", "text"]));
  ok(!unifiable(["g", "text"], ["g", "other"]));
});

test("the store is a multiset and removal subtracts one unifying occurrence", () => {
  const store = new SpaceStore();
  store.add("&self", edge(sym("a"), sym("b")));
  store.add("&self", edge(sym("a"), sym("b")));
  store.add("&self", edge(sym("a"), sym("c")));
  strictEqual(store.atoms("&self").length, 3);
  // Multiset subtraction: three stored, three removals, and the fourth
  // finds nothing. A removal that took them all would empty the store here.
  strictEqual(store.remove("&self", edge(sym("a"), v("any"))), true);
  strictEqual(store.atoms("&self").length, 2);
  strictEqual(store.remove("&self", edge(sym("a"), v("any"))), true);
  strictEqual(store.remove("&self", edge(sym("a"), v("any"))), true);
  strictEqual(store.atoms("&self").length, 0);
  strictEqual(store.remove("&self", edge(sym("a"), v("any"))), false);
});

test("an allowlisted store refuses other spaces by name", () => {
  const store = new SpaceStore(new Set(["&served"]));
  store.add("&served", sym("fine"));
  let refused = "";
  try {
    store.add("&other", sym("nope"));
  } catch (error) {
    refused = error instanceof Error ? error.message : String(error);
  }
  strictEqual(refused, "space '&other' is not served");
});

async function operate(
  port: number,
  operation: string,
  payload: unknown,
  headers: Record<string, string> = {},
): Promise<{ status: number; body: any }> {
  const body = JSON.stringify(payload);
  const response = await fetch(`http://127.0.0.1:${port}/${operation}`, {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body,
  });
  return { status: response.status, body: await response.json() };
}

test("the HTTP boundary mirrors the protocol's refusals", async () => {
  const running = await startServer({ port: 0 });
  try {
    const { port } = running;

    deepStrictEqual(await operate(port, "add", { atom: sym("a") }), {
      status: 200,
      body: { added: true },
    });
    deepStrictEqual(await operate(port, "match", { pattern: v("x") }), {
      status: 200,
      body: { atoms: [sym("a")] },
    });

    const unknown = await operate(port, "nope", {});
    strictEqual(unknown.status, 400);
    strictEqual(unknown.body.error, "unknown operation 'nope'");

    const nonObject = await operate(port, "add", [1, 2]);
    strictEqual(nonObject.status, 400);

    const badAtom = await operate(port, "add", { atom: ["x", 1] });
    strictEqual(badAtom.status, 400);

    const wide = await operate(port, "add", { atom: ["n", null] });
    strictEqual(wide.status, 400);

    const wrongMethod = await fetch(`http://127.0.0.1:${port}/atoms`, { method: "PUT" });
    strictEqual(wrongMethod.status, 405);

    const health = await fetch(`http://127.0.0.1:${port}/health`);
    strictEqual(health.status, 200);
    deepStrictEqual(await health.json(), {
      ok: true,
      atoms: 1,
      protocol: 3,
      capabilities: ["match", "enumerate", "add", "remove", "stream"],
      bound: true,
    });
  } finally {
    await running.close();
  }
});

test("a batch lands whole through add_many, and health names the protocol", async () => {
  const running = await startServer({ port: 0 });
  try {
    const { port } = running;
    const batch = await operate(port, "add_many", {
      atoms: [edge(sym("a"), sym("b")), edge(sym("a"), sym("c")), sym("solo")],
    });
    deepStrictEqual(batch, { status: 200, body: { added: 3 } });
    const all = await operate(port, "atoms", {});
    strictEqual(all.body.atoms.length, 3);

    const bad = await operate(port, "add_many", { atoms: [["x", 1]] });
    strictEqual(bad.status, 400);
    strictEqual((await operate(port, "atoms", {})).body.atoms.length, 3);

    const health = await fetch(`http://127.0.0.1:${port}/health`);
    deepStrictEqual(await health.json(), {
      ok: true,
      atoms: 3,
      protocol: 3,
      capabilities: ["match", "enumerate", "add", "remove", "stream"],
      bound: true,
    });
  } finally {
    await running.close();
  }
});

test("a bound crosses on match and is honored exactly", async () => {
  const running = await startServer({ port: 0 });
  try {
    const { port } = running;
    await operate(port, "add_many", {
      atoms: [edge(sym("a"), sym("b")), edge(sym("a"), sym("c")), edge(sym("a"), sym("d"))],
    });
    const bounded = await operate(port, "match", {
      pattern: edge(sym("a"), v("x")),
      bound: 2,
    });
    strictEqual(bounded.status, 200);
    strictEqual(bounded.body.atoms.length, 2);
    const unbounded = await operate(port, "match", {
      pattern: edge(sym("a"), v("x")),
    });
    strictEqual(unbounded.body.atoms.length, 3);
    const zero = await operate(port, "match", {
      pattern: edge(sym("a"), v("x")),
      bound: 0,
    });
    deepStrictEqual(zero.body, { atoms: [] });
    const bad = await operate(port, "match", {
      pattern: edge(sym("a"), v("x")),
      bound: -1,
    });
    strictEqual(bad.status, 400);
    const alsoBad = await operate(port, "match", {
      pattern: edge(sym("a"), v("x")),
      bound: 1.5,
    });
    strictEqual(alsoBad.status, 400);
  } finally {
    await running.close();
  }
});

test("wide integers are refused, not rounded", async () => {
  const running = await startServer({ port: 0 });
  try {
    const response = await fetch(`http://127.0.0.1:${running.port}/add`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: '{"atom": ["n", 123456789012345678901]}',
    });
    strictEqual(response.status, 400);
    const body = await response.json();
    ok(String(body.error).includes("123456789012345678901"));
  } finally {
    await running.close();
  }
});

test("a token gates every operation before the body is read", async () => {
  const running = await startServer({ port: 0, token: "secret" });
  try {
    const { port } = running;
    const refused = await operate(port, "add", { atom: sym("a") });
    strictEqual(refused.status, 401);
    deepStrictEqual(refused.body, { error: "not authorized" });

    const accepted = await operate(
      port,
      "add",
      { atom: sym("a") },
      { authorization: "Bearer secret" },
    );
    strictEqual(accepted.status, 200);

    const wrong = await operate(
      port,
      "add",
      { atom: sym("a") },
      { authorization: "Bearer wrong" },
    );
    strictEqual(wrong.status, 401);
  } finally {
    await running.close();
  }
});

// --------------------------------------------------------------------------
// The ask/next/stop lifecycle.

test("two answers cross without the third being computed", async () => {
  // The store counts what it was asked to unify, so this says in one
  // number how much of a thousand-answer enumeration the server computed
  // for a client that wanted two.
  class CountingStore extends SpaceStore {
    pulled = 0;

    override *stream(name: string, pattern: WireAtom): Generator<WireAtom> {
      for (const atom of this.atoms(name)) {
        this.pulled += 1;
        if (unifiable(pattern, atom)) yield atom;
      }
    }
  }

  const store = new CountingStore();
  store.addMany(
    "&self",
    Array.from({ length: 1000 }, (_, i) => edge(sym("row"), ["n", i])),
  );
  const running = await startServer({ port: 0, store });
  try {
    const { port } = running;
    const pattern = edge(sym("row"), v("n"));
    store.pulled = 0;
    const first = await operate(port, "ask", { pattern, batch: 1 });
    strictEqual(first.status, 200);
    strictEqual(first.body.atoms.length, 1);
    ok(typeof first.body.cursor === "string");
    const second = await operate(port, "next", {
      cursor: first.body.cursor,
      batch: 1,
    });
    strictEqual(second.body.atoms.length, 1);
    strictEqual(second.body.cursor, first.body.cursor);
    deepStrictEqual(await operate(port, "stop", { cursor: first.body.cursor }), {
      status: 200,
      body: { stopped: true },
    });
    strictEqual(store.pulled, 2, "two answers wanted, two atoms unified");

    store.pulled = 0;
    const eager = await operate(port, "match", { pattern });
    strictEqual(eager.body.atoms.length, 1000);
    strictEqual(store.pulled, 1000, "the eager door drains, which is its job");
  } finally {
    await running.close();
  }
});

test("chunking is a chunk: every batch answers the same set", async () => {
  const running = await startServer({ port: 0 });
  try {
    const { port } = running;
    await operate(port, "add_many", {
      atoms: Array.from({ length: 5 }, (_, i) => edge(sym("k"), ["n", i])),
    });
    const pattern = edge(sym("k"), v("n"));
    const whole = (await operate(port, "match", { pattern })).body.atoms;
    for (const batch of [1, 2, 5, 50]) {
      const answered: unknown[] = [];
      let reply = (await operate(port, "ask", { pattern, batch })).body;
      for (;;) {
        ok(reply.atoms.length <= batch, "a chunk may not exceed the batch");
        answered.push(...reply.atoms);
        if (reply.cursor === null) break;
        ok(reply.atoms.length > 0, "an empty chunk ends the stream");
        reply = (await operate(port, "next", { cursor: reply.cursor, batch })).body;
      }
      deepStrictEqual(answered, whole);
    }
    // A bound is the cut, honored exactly by this store.
    const bounded = (await operate(port, "ask", { pattern, batch: 5, bound: 2 })).body;
    strictEqual(bounded.atoms.length, 2);
    strictEqual(bounded.cursor, null);
    deepStrictEqual((await operate(port, "ask", { pattern, batch: 5, bound: 0 })).body, {
      atoms: [],
      cursor: null,
    });
  } finally {
    await running.close();
  }
});

test("a cursor the server no longer holds is refused, not answered empty", async () => {
  const running = await startServer({ port: 0, cursorLimit: 2 });
  try {
    const { port } = running;
    await operate(port, "add_many", {
      atoms: Array.from({ length: 4 }, (_, i) => edge(sym("g"), ["n", i])),
    });
    const pattern = edge(sym("g"), v("n"));
    const opened = (await operate(port, "ask", { pattern, batch: 1 })).body;
    deepStrictEqual(await operate(port, "stop", { cursor: opened.cursor }), {
      status: 200,
      body: { stopped: true },
    });
    const gone = await operate(port, "next", { cursor: opened.cursor, batch: 1 });
    strictEqual(gone.status, 400);
    ok(String(gone.body.error).includes("no such cursor"));
    deepStrictEqual((await operate(port, "stop", { cursor: opened.cursor })).body, {
      stopped: false,
    });
    strictEqual((await operate(port, "next", { cursor: 7 })).status, 400);
    for (const batch of [0, -1, 1.5, "two"]) {
      strictEqual((await operate(port, "ask", { pattern, batch })).status, 400);
    }
    // The ceiling is refused rather than grown.
    const held = [
      (await operate(port, "ask", { pattern, batch: 1 })).body.cursor,
      (await operate(port, "ask", { pattern, batch: 1 })).body.cursor,
    ];
    const over = await operate(port, "ask", { pattern, batch: 1 });
    strictEqual(over.status, 400);
    ok(String(over.body.error).includes("already holds 2 answer cursors"));
    await operate(port, "stop", { cursor: held[0] });
    ok(typeof (await operate(port, "ask", { pattern, batch: 1 })).body.cursor === "string");
  } finally {
    await running.close();
  }
});

test("a cursor nobody pulls from is released on its idle deadline", async () => {
  const running = await startServer({ port: 0, cursorIdle: 0.05 });
  try {
    const { port } = running;
    await operate(port, "add_many", {
      atoms: Array.from({ length: 4 }, (_, i) => edge(sym("i"), ["n", i])),
    });
    const pattern = edge(sym("i"), v("n"));
    const opened = (await operate(port, "ask", { pattern, batch: 1 })).body;
    await new Promise((done) => setTimeout(done, 200));
    const gone = await operate(port, "next", { cursor: opened.cursor, batch: 1 });
    strictEqual(gone.status, 400);
    ok(String(gone.body.error).includes("untouched for 0.05 seconds"));
  } finally {
    await running.close();
  }
});

test("concurrent clients interleave whole operations", async () => {
  const running = await startServer({ port: 0 });
  try {
    const { port } = running;
    const writers = Array.from({ length: 20 }, (_, i) =>
      operate(port, "add", { atom: edge(sym("row"), ["n", i]) }),
    );
    const readers = Array.from({ length: 20 }, () =>
      operate(port, "match", { pattern: edge(sym("row"), v("n")) }),
    );
    const settled = await Promise.all([...writers, ...readers]);
    for (const { status } of settled) strictEqual(status, 200);
    const final = await operate(port, "match", { pattern: edge(sym("row"), v("n")) });
    strictEqual(final.body.atoms.length, 20);
  } finally {
    await running.close();
  }
});
