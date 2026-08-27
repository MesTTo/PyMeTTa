// mettascript_space_server.ts
import { pathToFileURL } from "node:url";

// space_server.ts
import { createServer } from "node:http";
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
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
  // One filter behind both doors: the generator unifies a stored atom
  // only when a caller pulls for it, so taking two answers of a
  // thousand-atom space unifies against two atoms and the eager door
  // against all thousand [tested: space_server.test.ts, "two answers
  // cross without the third being computed"]. match() is that same walk
  // drained.
  *stream(name, pattern) {
    for (const atom of this.space(name)) {
      if (unifiable(pattern, atom)) yield atom;
    }
  }
  match(name, pattern) {
    return [...this.stream(name, pattern)];
  }
  // Honoring is sound HERE because match filters by real unification,
  // so the first `bound` survivors are true answers, never candidates.
  boundedMatch(name, pattern, bound) {
    return [...take(this.stream(name, pattern), bound)];
  }
  // ONE unifying occurrence goes: a space is a multiset and removal is
  // multiset subtraction, so two stored copies need two removals. The
  // answer says whether one was there.
  remove(name, pattern) {
    const atoms = this.space(name);
    const doomed = atoms.findIndex((atom) => unifiable(pattern, atom));
    if (doomed < 0) return false;
    atoms.splice(doomed, 1);
    return true;
  }
  count() {
    let total = 0;
    for (const atoms of this.spaces.values()) total += atoms.length;
    return total;
  }
};
function* take(source, count) {
  for (let taken = 0; taken < count; taken++) {
    const step = source.next();
    if (step.done === true) return;
    yield step.value;
  }
}
function pull(entry, batch) {
  const want = entry.remaining === null ? batch : Math.min(batch, entry.remaining);
  const atoms = [];
  for (let taken = 0; taken < want; taken++) {
    const step = entry.iterator.next();
    if (step.done === true) break;
    atoms.push(step.value);
  }
  if (entry.remaining !== null) entry.remaining -= atoms.length;
  return { atoms, done: atoms.length < want || entry.remaining === 0 };
}
var CursorTable = class {
  constructor(idleMs, limit) {
    this.idleMs = idleMs;
    this.limit = limit;
  }
  idleMs;
  limit;
  open = /* @__PURE__ */ new Map();
  sweep() {
    const now = Date.now();
    for (const [token, entry] of this.open) {
      if (entry.deadline <= now) {
        this.open.delete(token);
        entry.iterator.return?.(void 0);
      }
    }
  }
  hold(entry) {
    this.sweep();
    if (this.open.size >= this.limit) {
      entry.iterator.return?.(void 0);
      throw new HttpProblem(
        400,
        `this gateway already holds ${this.limit} answer cursors open; stop one before asking for another`
      );
    }
    const token = randomBytes(18).toString("base64url");
    entry.deadline = Date.now() + this.idleMs;
    this.open.set(token, entry);
    return token;
  }
  // A token the table does not hold is an ERROR rather than an empty
  // answer: answering nothing would say the enumeration ended, and
  // under-approximating is the one thing this protocol forbids.
  take(token) {
    this.sweep();
    const entry = this.open.get(this.tokenOf(token));
    if (entry === void 0) {
      throw new HttpProblem(
        400,
        `no such cursor: it was stopped, it ran out of answers, or it went untouched for ${this.idleMs / 1e3} seconds and the server released it. Ask again for a new one`
      );
    }
    entry.deadline = Date.now() + this.idleMs;
    return entry;
  }
  release(token) {
    this.sweep();
    const named = this.tokenOf(token);
    const entry = this.open.get(named);
    if (entry === void 0) return false;
    this.open.delete(named);
    entry.iterator.return?.(void 0);
    return true;
  }
  closeAll() {
    for (const entry of this.open.values()) entry.iterator.return?.(void 0);
    this.open.clear();
  }
  tokenOf(token) {
    if (typeof token !== "string") {
      throw new HttpProblem(400, `cursor must be a string, got ${JSON.stringify(token)}`);
    }
    return token;
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
var DEFAULT_CURSOR_IDLE_SECONDS = 300;
var DEFAULT_CURSOR_LIMIT = 256;
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
function payloadBatch(payload) {
  const value = payload["batch"] ?? 1;
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    throw new HttpProblem(400, `batch must be a positive integer, got ${JSON.stringify(value)}`);
  }
  return value;
}
function payloadBound(payload) {
  const value = payload["bound"];
  if (value === void 0) return null;
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new HttpProblem(400, `bound must be a non-negative integer, got ${JSON.stringify(value)}`);
  }
  return value;
}
function startServer(options = {}) {
  const host = options.host ?? "127.0.0.1";
  const token = options.token ?? null;
  const maxBody = options.maxBody ?? DEFAULT_MAX_BODY;
  const served = options.spaces == null ? null : new Set(options.spaces);
  const store = options.store ?? new SpaceStore(served);
  const cursors = new CursorTable(
    (options.cursorIdle ?? DEFAULT_CURSOR_IDLE_SECONDS) * 1e3,
    options.cursorLimit ?? DEFAULT_CURSOR_LIMIT
  );
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
          protocol: 3,
          capabilities: ["match", "enumerate", "add", "remove", "stream"],
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
        answer = operate(path, payload);
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
  function operate(operation, payload) {
    switch (operation) {
      case "match": {
        const space = payloadSpace(payload);
        const pattern = payloadAtom(payload, "pattern");
        const bound = payloadBound(payload);
        if (bound !== null && typeof store.boundedMatch === "function") {
          return { atoms: store.boundedMatch(space, pattern, bound) };
        }
        return { atoms: store.match(space, pattern) };
      }
      case "ask": {
        const space = payloadSpace(payload);
        const pattern = payloadAtom(payload, "pattern");
        const batch = payloadBatch(payload);
        const asked = payloadBound(payload);
        const bound = typeof store.boundedMatch === "function" ? asked : null;
        if (bound === 0) return { atoms: [], cursor: null };
        const entry = {
          iterator: store.stream(space, pattern),
          space,
          remaining: bound,
          deadline: 0
        };
        const { atoms, done } = pull(entry, batch);
        if (done) {
          entry.iterator.return?.(void 0);
          return { atoms, cursor: null };
        }
        return { atoms, cursor: cursors.hold(entry) };
      }
      case "next": {
        const token2 = payload["cursor"];
        const entry = cursors.take(token2);
        const { atoms, done } = pull(entry, payloadBatch(payload));
        if (done) cursors.release(token2);
        return { atoms, cursor: done ? null : token2 };
      }
      case "stop": {
        return { stopped: cursors.release(payload["cursor"]) };
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
          cursors.closeAll();
          server.close((error) => error ? fail(error) : done());
        })
      });
    });
  });
}

// mettascript_space_server.ts
function wireToCore(core, atom) {
  const [tag, payload] = atom;
  switch (tag) {
    case "s":
      return core.sym(payload);
    case "v":
      return core.variable(payload);
    case "e":
      return core.expr(payload.map((item) => wireToCore(core, item)));
    case "n": {
      const n = payload;
      return Number.isInteger(n) ? core.gnd({ g: "int", n }) : core.gnd({ g: "float", n });
    }
    case "g": {
      if (typeof payload === "string") return core.gnd({ g: "str", s: payload });
      if (typeof payload === "boolean") return core.gnd({ g: "bool", b: payload });
      throw new HttpProblem(
        400,
        `grounded wire value of type ${typeof payload} has no MeTTaScript reading here`
      );
    }
  }
}
function coreToWire(atom) {
  switch (atom.kind) {
    case "sym":
      return ["s", atom.name ?? ""];
    case "var":
      return ["v", atom.name ?? ""];
    case "expr":
      return ["e", (atom.items ?? []).map((item) => coreToWire(item))];
    case "gnd": {
      const value = atom.value;
      if (value === void 0) break;
      if (value.g === "int" || value.g === "float") {
        const n = value.n;
        if (typeof n === "bigint") {
          if (n > BigInt(Number.MAX_SAFE_INTEGER) || n < -BigInt(Number.MAX_SAFE_INTEGER)) {
            throw new HttpProblem(
              400,
              `stored integer ${n} exceeds what this wire carries faithfully`
            );
          }
          return ["n", Number(n)];
        }
        return ["n", n];
      }
      if (value.g === "str") return ["g", value.s];
      if (value.g === "bool") return ["g", value.b];
      break;
    }
  }
  throw new HttpProblem(
    400,
    `stored MeTTaScript atom of kind ${atom.kind} has no wire reading here`
  );
}
var MettascriptStore = class {
  constructor(core, served = null) {
    this.core = core;
    this.served = served;
  }
  core;
  served;
  spaces = /* @__PURE__ */ new Map();
  space(name) {
    if (this.served !== null && !this.served.has(name)) {
      throw new HttpProblem(400, `space '${name}' is not served`);
    }
    let space = this.spaces.get(name);
    if (space === void 0) {
      space = new this.core.InMemorySpace();
      this.spaces.set(name, space);
    }
    return space;
  }
  add(name, atom) {
    this.space(name).add(wireToCore(this.core, atom));
  }
  addMany(name, atoms) {
    const space = this.space(name);
    for (const atom of atoms) space.add(wireToCore(this.core, atom));
    return atoms.length;
  }
  atoms(name) {
    return this.space(name).atoms().map((atom) => coreToWire(atom));
  }
  // MeTTaScript's own unifier answers first; the wire unifier is the
  // soundness envelope. The protocol's law is that match may never
  // under-approximate unification, and the GatewayComplianceSuite found
  // MeTTaScript refusing rational-tree matches ((f $y $y) against a
  // stored (f (g $x) $x)) that the law answers. Over-approximating is
  // always legal, so the union keeps the law whatever either unifier
  // decides, and PeTTa re-unifies every candidate anyway.
  admits(wanted, pattern, atom) {
    return this.core.unifiable(wanted, atom) || unifiable(pattern, coreToWire(atom));
  }
  // No boundedMatch on purpose, so health advertises bound: false and
  // /match ignores the field: admits() over-approximates (the union
  // envelope above), and truncating an over-approximated list can drop
  // truly-unifying atoms past the cut, the under-approximation the
  // protocol forbids. Ignoring a bound is always sound; honoring one is
  // only sound for an exact matcher.
  // One walk behind both doors: the generator admits a stored atom only
  // when a caller pulls for it, so /ask and /next unify against as many
  // atoms as the client asked for answers rather than the whole space.
  *stream(name, pattern) {
    const wanted = wireToCore(this.core, pattern);
    for (const atom of this.space(name).atoms()) {
      if (this.admits(wanted, pattern, atom)) yield coreToWire(atom);
    }
  }
  match(name, pattern) {
    return [...this.stream(name, pattern)];
  }
  remove(name, pattern) {
    const space = this.space(name);
    const wanted = wireToCore(this.core, pattern);
    const doomed = space.atoms().find((atom) => this.admits(wanted, pattern, atom));
    if (doomed === void 0) return false;
    space.remove(doomed);
    return true;
  }
  count() {
    let total = 0;
    for (const space of this.spaces.values()) total += space.atoms().length;
    return total;
  }
};
function parseArguments(argv) {
  let corePath = process.env["METTASCRIPT_CORE"] ?? "@mettascript/core";
  const options = { token: process.env["METTA_SPACE_TOKEN"] ?? null };
  let spaces = null;
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    const value = () => {
      const next = argv[++i];
      if (next === void 0) throw new Error(`${flag} needs a value`);
      return next;
    };
    switch (flag) {
      case "--mettascript":
        corePath = value();
        break;
      case "--host":
        options.host = value();
        break;
      case "--port":
        options.port = Number(value());
        break;
      case "--token":
        options.token = value();
        break;
      case "--spaces":
        spaces = value().split(",");
        break;
      case "--max-body":
        options.maxBody = Number(value());
        break;
      default:
        throw new Error(`unknown flag ${flag}`);
    }
  }
  return { ...options, spaces, corePath };
}
function runCli(argv = process.argv.slice(2)) {
  const { corePath, ...options } = parseArguments(argv);
  const specifier = corePath.startsWith("/") ? pathToFileURL(corePath).href : corePath;
  import(specifier).then((core) => {
    const served = options.spaces == null ? null : new Set(options.spaces);
    return startServer({ ...options, store: new MettascriptStore(core, served) });
  }).then((running) => {
    process.stdout.write(
      JSON.stringify({
        listening: { host: running.host, port: running.port },
        backend: "mettascript"
      }) + "\n"
    );
    const stop = () => {
      void running.close().then(() => process.exit(0));
    };
    process.on("SIGINT", stop);
    process.on("SIGTERM", stop);
  }).catch((error) => {
    process.stderr.write(`mettascript space server failed to start: ${error}
`);
    process.exit(1);
  });
}

// main_mettascript.ts
runCli();
