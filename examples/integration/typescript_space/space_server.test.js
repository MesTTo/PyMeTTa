// space_server.test.ts
import { deepStrictEqual, ok, strictEqual } from "node:assert";
import { test } from "node:test";

// space_server.ts
import { createServer } from "node:http";
import { createHash, timingSafeEqual } from "node:crypto";
function isWireAtom(value) {
  if (!Array.isArray(value) || value.length !== 2) return false;
  const [tag, payload] = value;
  switch (tag) {
    case "s":
    case "v":
      return typeof payload === "string";
    case "n":
      return typeof payload === "number" && Number.isFinite(payload);
    case "g":
      return true;
    case "e":
      return Array.isArray(payload) && payload.every(isWireAtom);
    default:
      return false;
  }
}
function walk(side, atom, bindings) {
  let current = { side, atom };
  while (current.atom[0] === "v") {
    const next = bindings.get(`${current.side}:${current.atom[1]}`);
    if (next === void 0) return current;
    current = next;
  }
  return current;
}
function unify(left, right, bindings) {
  const a = walk(left.side, left.atom, bindings);
  const b = walk(right.side, right.atom, bindings);
  if (a.atom[0] === "v") {
    if (b.atom[0] === "v" && a.side === b.side && a.atom[1] === b.atom[1]) {
      return true;
    }
    bindings.set(`${a.side}:${a.atom[1]}`, b);
    return true;
  }
  if (b.atom[0] === "v") {
    bindings.set(`${b.side}:${b.atom[1]}`, a);
    return true;
  }
  const [tagA, payloadA] = a.atom;
  const [tagB, payloadB] = b.atom;
  if (tagA === "e" && tagB === "e") {
    const itemsA = payloadA;
    const itemsB = payloadB;
    if (itemsA.length !== itemsB.length) return false;
    for (let i = 0; i < itemsA.length; i++) {
      const left2 = itemsA[i];
      const right2 = itemsB[i];
      if (left2 === void 0 || right2 === void 0) return false;
      if (!unify({ side: a.side, atom: left2 }, { side: b.side, atom: right2 }, bindings)) {
        return false;
      }
    }
    return true;
  }
  if (tagA !== tagB) {
    return false;
  }
  if (tagA === "n") return payloadA === payloadB;
  if (tagA === "s") return payloadA === payloadB;
  return JSON.stringify(payloadA) === JSON.stringify(payloadB);
}
function unifiable(pattern, atom) {
  return unify({ side: "p", atom: pattern }, { side: "a", atom }, /* @__PURE__ */ new Map());
}
var SpaceStore = class {
  constructor(served = null) {
    this.served = served;
  }
  served;
  spaces = /* @__PURE__ */ new Map();
  space(name) {
    if (this.served !== null && !this.served.has(name)) {
      throw new HttpProblem(400, `space '${name}' is not served`);
    }
    let atoms = this.spaces.get(name);
    if (atoms === void 0) {
      atoms = [];
      this.spaces.set(name, atoms);
    }
    return atoms;
  }
  add(name, atom) {
    this.space(name).push(atom);
  }
  // A batch is a transport optimisation and never a semantic one: the
  // engine's own bulk-door law, kept on the wire. Node runs one handler
  // per event-loop turn, so the batch lands whole between readers.
  addMany(name, atoms) {
    this.space(name).push(...atoms);
    return atoms.length;
  }
  atoms(name) {
    return this.space(name);
  }
  match(name, pattern) {
    return this.space(name).filter((atom) => unifiable(pattern, atom));
  }
  // Honoring is sound HERE because match filters by real unification,
  // so the first `bound` survivors are true answers, never candidates.
  boundedMatch(name, pattern, bound) {
    return this.match(name, pattern).slice(0, bound);
  }
  // Every unifying occurrence goes, the multiset reading remove-atom has
  // everywhere, and the answer says whether any was there.
  remove(name, pattern) {
    const atoms = this.space(name);
    const kept = atoms.filter((atom) => !unifiable(pattern, atom));
    const removed = kept.length !== atoms.length;
    if (removed) this.spaces.set(name, kept);
    return removed;
  }
  count() {
    let total = 0;
    for (const atoms of this.spaces.values()) total += atoms.length;
    return total;
  }
};
var HttpProblem = class extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
  status;
};
var DEFAULT_MAX_BODY = 16 * 1024 * 1024;
function requestLength(request, maxBody) {
  if (request.headers["transfer-encoding"] !== void 0) {
    throw new HttpProblem(400, "transfer-encoding is not supported; send content-length");
  }
  const raw = request.headers["content-length"];
  if (raw === void 0) {
    throw new HttpProblem(411, "content-length is required");
  }
  if (Array.isArray(raw) || raw.includes(",")) {
    throw new HttpProblem(400, "exactly one content-length header is required");
  }
  if (!/^[0-9]+$/.test(raw)) {
    throw new HttpProblem(400, `content-length must be decimal digits, got '${raw}'`);
  }
  const length = Number(raw);
  if (length > maxBody) {
    throw new HttpProblem(413, `request body exceeds the ${maxBody}-byte limit`);
  }
  return length;
}
async function readBody(request, length) {
  const chunks = [];
  let received = 0;
  for await (const chunk of request) {
    chunks.push(chunk);
    received += chunk.length;
    if (received > length) {
      throw new HttpProblem(400, `request body exceeds its declared ${length} bytes`);
    }
  }
  if (received !== length) {
    throw new HttpProblem(400, `request body ended after ${received} of ${length} bytes`);
  }
  return Buffer.concat(chunks);
}
function parseStrictJson(raw) {
  const text = raw.toString("utf-8");
  return JSON.parse(text, (_key, value, context) => {
    if (typeof value === "number" && context?.source !== void 0 && /^-?[0-9]+$/.test(context.source) && !Number.isSafeInteger(value)) {
      throw new HttpProblem(
        400,
        `integer ${context.source} exceeds IEEE-754 exact range; this store cannot hold it faithfully`
      );
    }
    return value;
  });
}
function credentialAccepted(request, token) {
  if (token === null) return true;
  const header = request.headers.authorization;
  if (typeof header !== "string" || !header.startsWith("Bearer ")) return false;
  const presented = header.slice("Bearer ".length);
  const a = createHash("sha256").update(presented).digest();
  const b = createHash("sha256").update(token).digest();
  return timingSafeEqual(a, b);
}
function payloadAtom(payload, field) {
  const value = payload[field];
  if (!isWireAtom(value)) {
    throw new HttpProblem(400, `payload field '${field}' is not a wire atom`);
  }
  return value;
}
function payloadSpace(payload) {
  const value = payload["space"] ?? "&self";
  if (typeof value !== "string") {
    throw new HttpProblem(400, "payload field 'space' must be a string");
  }
  return value;
}
function startServer(options = {}) {
  const host = options.host ?? "127.0.0.1";
  const token = options.token ?? null;
  const maxBody = options.maxBody ?? DEFAULT_MAX_BODY;
  const served = options.spaces == null ? null : new Set(options.spaces);
  const store = options.store ?? new SpaceStore(served);
  const sockets = /* @__PURE__ */ new Set();
  const server = createServer((request, response) => {
    void handle(request, response);
  });
  server.on("connection", (socket) => {
    sockets.add(socket);
    socket.on("close", () => sockets.delete(socket));
  });
  async function handle(request, response) {
    const started = process.hrtime.bigint();
    const path = (request.url ?? "/").replace(/^\/+|\/+$/g, "");
    let status = 200;
    let answer;
    try {
      if (request.method === "GET" && path === "health") {
        answer = {
          ok: true,
          atoms: store.count(),
          protocol: 2,
          capabilities: ["match", "enumerate", "add", "remove"],
          bound: typeof store.boundedMatch === "function"
        };
      } else if (request.method !== "POST") {
        throw new HttpProblem(405, `method ${request.method} is not supported; POST an operation`);
      } else if (!credentialAccepted(request, token)) {
        status = 401;
        answer = { error: "not authorized" };
        request.resume();
      } else {
        const length = requestLength(request, maxBody);
        const raw = await readBody(request, length);
        const parsed = parseStrictJson(raw);
        if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
          throw new HttpProblem(400, `request body must be a JSON object`);
        }
        const payload = parsed;
        answer = operate2(path, payload);
      }
    } catch (error) {
      if (error instanceof HttpProblem) {
        status = error.status;
        answer = { error: error.message };
      } else {
        status = 400;
        answer = { error: error instanceof Error ? error.message : String(error) };
      }
    }
    const body = Buffer.from(JSON.stringify(answer), "utf-8");
    response.writeHead(status, {
      "content-type": "application/json",
      "content-length": String(body.length)
    });
    response.end(body);
    const elapsedMs = Number(process.hrtime.bigint() - started) / 1e6;
    process.stderr.write(
      `${(/* @__PURE__ */ new Date()).toISOString()} ${request.method} /${path} ${status} ${elapsedMs.toFixed(2)}ms
`
    );
  }
  function operate2(operation, payload) {
    switch (operation) {
      case "match": {
        const space = payloadSpace(payload);
        const pattern = payloadAtom(payload, "pattern");
        const bound = payload["bound"];
        if (bound !== void 0) {
          if (typeof bound !== "number" || !Number.isInteger(bound) || bound < 0) {
            throw new HttpProblem(400, `bound must be a non-negative integer, got ${JSON.stringify(bound)}`);
          }
          if (typeof store.boundedMatch === "function") {
            return { atoms: store.boundedMatch(space, pattern, bound) };
          }
        }
        return { atoms: store.match(space, pattern) };
      }
      case "atoms": {
        return { atoms: [...store.atoms(payloadSpace(payload))] };
      }
      case "add": {
        store.add(payloadSpace(payload), payloadAtom(payload, "atom"));
        return { added: true };
      }
      case "add_many": {
        const value = payload["atoms"];
        if (!Array.isArray(value) || !value.every(isWireAtom)) {
          throw new HttpProblem(400, "payload field 'atoms' is not a list of wire atoms");
        }
        return { added: store.addMany(payloadSpace(payload), value) };
      }
      case "remove": {
        const removed = store.remove(payloadSpace(payload), payloadAtom(payload, "atom"));
        return { removed };
      }
      default:
        throw new HttpProblem(400, `unknown operation '${operation}'`);
    }
  }
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(options.port ?? 0, host, () => {
      const address = server.address();
      if (address === null || typeof address === "string") {
        reject(new Error("server bound to a non-TCP address"));
        return;
      }
      resolve({
        server,
        store,
        host,
        port: address.port,
        close: () => new Promise((done, fail) => {
          for (const socket of sockets) socket.destroy();
          server.close((error) => error ? fail(error) : done());
        })
      });
    });
  });
}

// space_server.test.ts
var edge = (a, b) => ["e", [["s", "edge"], a, b]];
var sym = (name) => ["s", name];
var v = (name) => ["v", name];
test("unification renames the two sides apart", () => {
  const pattern = ["e", [sym("f"), v("x"), ["n", 1]]];
  const stored = ["e", [sym("f"), ["n", 2], v("x")]];
  ok(unifiable(pattern, stored));
});
test("unification still links repeated variables within one side", () => {
  const twice = ["e", [sym("f"), v("x"), v("x")]];
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
test("the store is a multiset and removal takes every unifying occurrence", () => {
  const store = new SpaceStore();
  store.add("&self", edge(sym("a"), sym("b")));
  store.add("&self", edge(sym("a"), sym("b")));
  store.add("&self", edge(sym("a"), sym("c")));
  strictEqual(store.atoms("&self").length, 3);
  strictEqual(store.remove("&self", edge(sym("a"), v("any"))), true);
  strictEqual(store.atoms("&self").length, 0);
  strictEqual(store.remove("&self", edge(sym("a"), v("any"))), false);
});
test("an allowlisted store refuses other spaces by name", () => {
  const store = new SpaceStore(/* @__PURE__ */ new Set(["&served"]));
  store.add("&served", sym("fine"));
  let refused = "";
  try {
    store.add("&other", sym("nope"));
  } catch (error) {
    refused = error instanceof Error ? error.message : String(error);
  }
  strictEqual(refused, "space '&other' is not served");
});
async function operate(port, operation, payload, headers = {}) {
  const body = JSON.stringify(payload);
  const response = await fetch(`http://127.0.0.1:${port}/${operation}`, {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body
  });
  return { status: response.status, body: await response.json() };
}
test("the HTTP boundary mirrors the protocol's refusals", async () => {
  const running = await startServer({ port: 0 });
  try {
    const { port } = running;
    deepStrictEqual(await operate(port, "add", { atom: sym("a") }), {
      status: 200,
      body: { added: true }
    });
    deepStrictEqual(await operate(port, "match", { pattern: v("x") }), {
      status: 200,
      body: { atoms: [sym("a")] }
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
      protocol: 2,
      capabilities: ["match", "enumerate", "add", "remove"],
      bound: true
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
      atoms: [edge(sym("a"), sym("b")), edge(sym("a"), sym("c")), sym("solo")]
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
      protocol: 2,
      capabilities: ["match", "enumerate", "add", "remove"],
      bound: true
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
      atoms: [edge(sym("a"), sym("b")), edge(sym("a"), sym("c")), edge(sym("a"), sym("d"))]
    });
    const bounded = await operate(port, "match", {
      pattern: edge(sym("a"), v("x")),
      bound: 2
    });
    strictEqual(bounded.status, 200);
    strictEqual(bounded.body.atoms.length, 2);
    const unbounded = await operate(port, "match", {
      pattern: edge(sym("a"), v("x"))
    });
    strictEqual(unbounded.body.atoms.length, 3);
    const zero = await operate(port, "match", {
      pattern: edge(sym("a"), v("x")),
      bound: 0
    });
    deepStrictEqual(zero.body, { atoms: [] });
    const bad = await operate(port, "match", {
      pattern: edge(sym("a"), v("x")),
      bound: -1
    });
    strictEqual(bad.status, 400);
    const alsoBad = await operate(port, "match", {
      pattern: edge(sym("a"), v("x")),
      bound: 1.5
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
      body: '{"atom": ["n", 123456789012345678901]}'
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
      { authorization: "Bearer secret" }
    );
    strictEqual(accepted.status, 200);
    const wrong = await operate(
      port,
      "add",
      { atom: sym("a") },
      { authorization: "Bearer wrong" }
    );
    strictEqual(wrong.status, 401);
  } finally {
    await running.close();
  }
});
test("concurrent clients interleave whole operations", async () => {
  const running = await startServer({ port: 0 });
  try {
    const { port } = running;
    const writers = Array.from(
      { length: 20 },
      (_, i) => operate(port, "add", { atom: edge(sym("row"), ["n", i]) })
    );
    const readers = Array.from(
      { length: 20 },
      () => operate(port, "match", { pattern: edge(sym("row"), v("n")) })
    );
    const settled = await Promise.all([...writers, ...readers]);
    for (const { status } of settled) strictEqual(status, 200);
    const final = await operate(port, "match", { pattern: edge(sym("row"), v("n")) });
    strictEqual(final.body.atoms.length, 20);
  } finally {
    await running.close();
  }
});
