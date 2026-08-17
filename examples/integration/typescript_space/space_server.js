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
function parseArguments(argv) {
  const options = {
    token: process.env["PETTA_SPACE_TOKEN"] ?? null
  };
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    const value = () => {
      const next = argv[++i];
      if (next === void 0) throw new Error(`${flag} needs a value`);
      return next;
    };
    switch (flag) {
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
        options.spaces = value().split(",");
        break;
      case "--max-body":
        options.maxBody = Number(value());
        break;
      default:
        throw new Error(`unknown flag ${flag}`);
    }
  }
  return options;
}
function runCli(argv = process.argv.slice(2)) {
  startServer(parseArguments(argv)).then((running) => {
    process.stdout.write(
      JSON.stringify({ listening: { host: running.host, port: running.port } }) + "\n"
    );
    const stop = () => {
      void running.close().then(() => process.exit(0));
    };
    process.on("SIGINT", stop);
    process.on("SIGTERM", stop);
  }).catch((error) => {
    process.stderr.write(`space server failed to start: ${error}
`);
    process.exit(1);
  });
}

// main_store.ts
runCli();
