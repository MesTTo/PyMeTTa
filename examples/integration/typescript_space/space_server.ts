/* Purpose: a MeTTa space served from TypeScript: the remote-space wire
 *   protocol implemented outside the engine's own languages, so
 *   metta.remote.attach() reaches atoms held by a Node process exactly as
 *   it reaches a served Python engine.
 * Assumes:
 *   - the client is metta.remote.connect(): POST per operation, JSON both
 *     ways, one wire atom grammar (see the README beside this file)
 *   - Node >= 22, for native TypeScript stripping and JSON.parse source
 *     access; no dependencies beyond node's own modules, deliberately,
 *     so the whole trust surface is this one file
 * Guarantees:
 *   - match and remove use real one-sided-namespace unification, so
 *     (f $x 1) against a stored (f 2 $x) unifies here exactly as it does
 *     in the engine; the engine still re-unifies every candidate, so a
 *     defect here can cost time, never soundness [tested:
 *     space_server.test.ts, unification block]
 *   - the HTTP boundary mirrors metta.remote.serve()'s refusals: 401
 *     before the body is read, 411 without content-length, 413 over the
 *     byte limit, 400 for ambiguous lengths, invalid JSON, non-object
 *     payloads and unknown operations, each with a JSON error body
 *   - integers beyond IEEE-754 exact range are refused rather than
 *     silently rounded, because JSON.parse hands back doubles and a
 *     store that rounds an atom returns a different atom
 *   - mutations are atomic per request: the store is only touched
 *     between awaits, and Node runs one request handler at a time per
 *     event-loop turn, so concurrent clients interleave whole
 *     operations, never partial ones
 *   - the ask/next/stop lifecycle hands back at most `batch` answers per
 *     reply and never looks ahead, so a client that takes two answers of
 *     a large space leaves the third uncomputed; the store's match walk
 *     is one generator behind both doors [tested: space_server.test.ts,
 *     lifecycle block]
 * Owns:
 *   - the HTTP server and its open sockets; SIGINT and SIGTERM close the
 *     listener, end open connections, and exit 0
 *   - every answer cursor a client left open, released by close(), by the
 *     stream ending, or by the idle deadline
 * Open Obligations:
 *   To Do: None
 *   Hacks: None
 *   Future Enhancements: None
 */

import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { pathToFileURL } from "node:url";

// ---------------------------------------------------------------------------
// The wire atom grammar, as petta's own to_wire()/atom_from_wire() speak it.

export type WireAtom =
  | ["s", string]      // symbol
  | ["v", string]      // variable
  | ["n", number]      // number
  | ["g", unknown]     // grounded value (strings cross this way)
  | ["e", WireAtom[]]; // expression

export function isWireAtom(value: unknown): value is WireAtom {
  if (!Array.isArray(value) || value.length !== 2) return false;
  const [tag, payload] = value as [unknown, unknown];
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

// ---------------------------------------------------------------------------
// Unification. The two sides carry separate variable namespaces, because a
// name is only an identity within its own atom: (f $x 1) against a stored
// (f 2 $x) must unify (the engine renames apart), and a shared-name reading
// wrongly fails it. Bindings map namespaced names to [side, atom] pairs so a
// variable bound to the other side's variable stays traceable.

type Side = "p" | "a";
type Bound = { side: Side; atom: WireAtom };
type Bindings = Map<string, Bound>;

function walk(side: Side, atom: WireAtom, bindings: Bindings): Bound {
  let current: Bound = { side, atom };
  while (current.atom[0] === "v") {
    const next = bindings.get(`${current.side}:${current.atom[1]}`);
    if (next === undefined) return current;
    current = next;
  }
  return current;
}

function unify(left: Bound, right: Bound, bindings: Bindings): boolean {
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
    const itemsA = payloadA as WireAtom[];
    const itemsB = payloadB as WireAtom[];
    if (itemsA.length !== itemsB.length) return false;
    for (let i = 0; i < itemsA.length; i++) {
      const left = itemsA[i];
      const right = itemsB[i];
      if (left === undefined || right === undefined) return false;
      if (!unify({ side: a.side, atom: left }, { side: b.side, atom: right }, bindings)) {
        return false;
      }
    }
    return true;
  }
  if (tagA !== tagB) {
    // Numbers compare by value whichever tag carried them; nothing else
    // crosses tags.
    return false;
  }
  if (tagA === "n") return payloadA === payloadB;
  if (tagA === "s") return payloadA === payloadB;
  // Grounded values compare structurally: strings are the common case, and
  // JSON-shaped values compare by content the way the wire delivered them.
  return JSON.stringify(payloadA) === JSON.stringify(payloadB);
}

export function unifiable(pattern: WireAtom, atom: WireAtom): boolean {
  return unify({ side: "p", atom: pattern }, { side: "a", atom }, new Map());
}

// ---------------------------------------------------------------------------
// The store: named spaces of wire atoms, multiset semantics throughout. The
// HTTP boundary talks to this interface, so a store backed by another engine
// (mettascript_space_server.ts holds a MeTTaScript space behind it) serves
// the same protocol with nothing above it changing.

export interface WireSpaceStore {
  add(name: string, atom: WireAtom): void;
  addMany(name: string, atoms: readonly WireAtom[]): number;
  atoms(name: string): readonly WireAtom[];
  // The lazy door, required at protocol revision 3: candidates pulled
  // one at a time, so /ask and /next can hand back a chunk without the
  // store computing the answer after it. match() is the eager door and
  // reads as "drain this".
  stream(name: string, pattern: WireAtom): Iterator<WireAtom>;
  match(name: string, pattern: WireAtom): WireAtom[];
  // Present exactly when this store may honor /match's bound field: the
  // trusted-Exact contract. A store whose match over-approximates must
  // NOT implement it, because truncating an over-approximated candidate
  // list can drop truly-unifying atoms past the cut, which is the
  // under-approximation the protocol forbids. Health advertises
  // `bound` from its presence.
  boundedMatch?(name: string, pattern: WireAtom, bound: number): WireAtom[];
  remove(name: string, pattern: WireAtom): boolean;
  count(): number;
}

export class SpaceStore implements WireSpaceStore {
  private readonly spaces = new Map<string, WireAtom[]>();

  constructor(private readonly served: ReadonlySet<string> | null = null) {}

  private space(name: string): WireAtom[] {
    if (this.served !== null && !this.served.has(name)) {
      throw new HttpProblem(400, `space '${name}' is not served`);
    }
    let atoms = this.spaces.get(name);
    if (atoms === undefined) {
      atoms = [];
      this.spaces.set(name, atoms);
    }
    return atoms;
  }

  add(name: string, atom: WireAtom): void {
    this.space(name).push(atom);
  }

  // A batch is a transport optimisation and never a semantic one: the
  // engine's own bulk-door law, kept on the wire. Node runs one handler
  // per event-loop turn, so the batch lands whole between readers.
  addMany(name: string, atoms: readonly WireAtom[]): number {
    this.space(name).push(...atoms);
    return atoms.length;
  }

  atoms(name: string): readonly WireAtom[] {
    return this.space(name);
  }

  // One filter behind both doors: the generator unifies a stored atom
  // only when a caller pulls for it, so taking two answers of a
  // thousand-atom space unifies against two atoms and the eager door
  // against all thousand [tested: space_server.test.ts, "two answers
  // cross without the third being computed"]. match() is that same walk
  // drained.
  *stream(name: string, pattern: WireAtom): Generator<WireAtom> {
    for (const atom of this.space(name)) {
      if (unifiable(pattern, atom)) yield atom;
    }
  }

  match(name: string, pattern: WireAtom): WireAtom[] {
    return [...this.stream(name, pattern)];
  }

  // Honoring is sound HERE because match filters by real unification,
  // so the first `bound` survivors are true answers, never candidates.
  boundedMatch(name: string, pattern: WireAtom, bound: number): WireAtom[] {
    return [...take(this.stream(name, pattern), bound)];
  }

  // ONE unifying occurrence goes: a space is a multiset and removal is
  // multiset subtraction, so two stored copies need two removals. The
  // answer says whether one was there.
  remove(name: string, pattern: WireAtom): boolean {
    const atoms = this.space(name);
    const doomed = atoms.findIndex((atom) => unifiable(pattern, atom));
    if (doomed < 0) return false;
    atoms.splice(doomed, 1);
    return true;
  }

  count(): number {
    let total = 0;
    for (const atoms of this.spaces.values()) total += atoms.length;
    return total;
  }
}

// ---------------------------------------------------------------------------
// The ask/next/stop lifecycle. A cursor is an iterator held open between
// requests under an unguessable token, so a client takes two answers of a
// large enumeration and stops without the store computing the one after
// them. Two bounds keep a stateful resource on an open port finite, and
// SWI's pengines bounds its own the same two ways: a cursor nobody pulls
// from is released after an idle deadline, and a client that would open
// more than the ceiling at once is refused rather than served.

interface OpenCursor {
  readonly iterator: Iterator<WireAtom>;
  readonly space: string;
  remaining: number | null;
  deadline: number;
}

function* take<T>(source: Iterator<T>, count: number): Generator<T> {
  for (let taken = 0; taken < count; taken++) {
    const step = source.next();
    if (step.done === true) return;
    yield step.value;
  }
}

// A SHORT chunk is the whole of the exhaustion signal, so nothing here
// looks ahead: the answer after the last one a client asked for is never
// computed, which is what makes taking two of a large enumeration cost
// two answers' work.
function pull(entry: OpenCursor, batch: number): { atoms: WireAtom[]; done: boolean } {
  const want = entry.remaining === null ? batch : Math.min(batch, entry.remaining);
  const atoms: WireAtom[] = [];
  for (let taken = 0; taken < want; taken++) {
    const step = entry.iterator.next();
    if (step.done === true) break;
    atoms.push(step.value);
  }
  if (entry.remaining !== null) entry.remaining -= atoms.length;
  return { atoms, done: atoms.length < want || entry.remaining === 0 };
}

export class CursorTable {
  private readonly open = new Map<string, OpenCursor>();

  constructor(
    private readonly idleMs: number,
    private readonly limit: number,
  ) {}

  private sweep(): void {
    const now = Date.now();
    for (const [token, entry] of this.open) {
      if (entry.deadline <= now) {
        this.open.delete(token);
        entry.iterator.return?.(undefined);
      }
    }
  }

  hold(entry: OpenCursor): string {
    this.sweep();
    if (this.open.size >= this.limit) {
      entry.iterator.return?.(undefined);
      throw new HttpProblem(
        400,
        `this gateway already holds ${this.limit} answer cursors open; ` +
          `stop one before asking for another`,
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
  take(token: unknown): OpenCursor {
    this.sweep();
    const entry = this.open.get(this.tokenOf(token));
    if (entry === undefined) {
      throw new HttpProblem(
        400,
        `no such cursor: it was stopped, it ran out of answers, or it went ` +
          `untouched for ${this.idleMs / 1000} seconds and the server ` +
          `released it. Ask again for a new one`,
      );
    }
    entry.deadline = Date.now() + this.idleMs;
    return entry;
  }

  release(token: unknown): boolean {
    this.sweep();
    const named = this.tokenOf(token);
    const entry = this.open.get(named);
    if (entry === undefined) return false;
    this.open.delete(named);
    entry.iterator.return?.(undefined);
    return true;
  }

  closeAll(): void {
    for (const entry of this.open.values()) entry.iterator.return?.(undefined);
    this.open.clear();
  }

  private tokenOf(token: unknown): string {
    if (typeof token !== "string") {
      throw new HttpProblem(400, `cursor must be a string, got ${JSON.stringify(token)}`);
    }
    return token;
  }
}

// ---------------------------------------------------------------------------
// The HTTP boundary. Refusals mirror metta.remote.serve(), status for status.

export class HttpProblem extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

const DEFAULT_MAX_BODY = 16 * 1024 * 1024;
// pengines' own defaults for the same two bounds: idle_limit is 300
// seconds, and the ceiling is refused rather than grown.
const DEFAULT_CURSOR_IDLE_SECONDS = 300;
const DEFAULT_CURSOR_LIMIT = 256;

function requestLength(request: IncomingMessage, maxBody: number): number {
  if (request.headers["transfer-encoding"] !== undefined) {
    throw new HttpProblem(400, "transfer-encoding is not supported; send content-length");
  }
  const raw = request.headers["content-length"];
  if (raw === undefined) {
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

async function readBody(request: IncomingMessage, length: number): Promise<Buffer> {
  const chunks: Buffer[] = [];
  let received = 0;
  for await (const chunk of request) {
    chunks.push(chunk as Buffer);
    received += (chunk as Buffer).length;
    if (received > length) {
      throw new HttpProblem(400, `request body exceeds its declared ${length} bytes`);
    }
  }
  if (received !== length) {
    throw new HttpProblem(400, `request body ended after ${received} of ${length} bytes`);
  }
  return Buffer.concat(chunks);
}

// JSON.parse rounds integers past 2**53 to doubles silently. The reviver's
// source access (Node >= 21) sees the literal, so a payload this store would
// corrupt is refused instead of stored wrong.
function parseStrictJson(raw: Buffer): unknown {
  const text = raw.toString("utf-8");
  return JSON.parse(text, (_key, value, context?: { source?: string }) => {
    if (
      typeof value === "number" &&
      context?.source !== undefined &&
      /^-?[0-9]+$/.test(context.source) &&
      !Number.isSafeInteger(value)
    ) {
      throw new HttpProblem(
        400,
        `integer ${context.source} exceeds IEEE-754 exact range; this store cannot hold it faithfully`,
      );
    }
    return value;
  });
}

function credentialAccepted(request: IncomingMessage, token: string | null): boolean {
  if (token === null) return true;
  const header = request.headers.authorization;
  if (typeof header !== "string" || !header.startsWith("Bearer ")) return false;
  const presented = header.slice("Bearer ".length);
  // Hash both sides so the comparison is constant-time whatever the lengths.
  const a = createHash("sha256").update(presented).digest();
  const b = createHash("sha256").update(token).digest();
  return timingSafeEqual(a, b);
}

type Payload = Record<string, unknown>;

function payloadAtom(payload: Payload, field: string): WireAtom {
  const value = payload[field];
  if (!isWireAtom(value)) {
    throw new HttpProblem(400, `payload field '${field}' is not a wire atom`);
  }
  return value;
}

function payloadSpace(payload: Payload): string {
  const value = payload["space"] ?? "&self";
  if (typeof value !== "string") {
    throw new HttpProblem(400, "payload field 'space' must be a string");
  }
  return value;
}

// A batch is a CHUNK and a bound is a CUT, which is why only one of them
// needs a matcher's permission: chunking hands back part of an answer set
// with the rest still reachable, so it is sound whatever a store's match
// does, while truncating an over-approximated candidate list can drop true
// answers past the cut.
function payloadBatch(payload: Payload): number {
  const value = payload["batch"] ?? 1;
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    throw new HttpProblem(400, `batch must be a positive integer, got ${JSON.stringify(value)}`);
  }
  return value;
}

function payloadBound(payload: Payload): number | null {
  const value = payload["bound"];
  if (value === undefined) return null;
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new HttpProblem(400, `bound must be a non-negative integer, got ${JSON.stringify(value)}`);
  }
  return value;
}

export interface ServerOptions {
  host?: string;
  port?: number;
  token?: string | null;
  spaces?: readonly string[] | null;
  maxBody?: number;
  store?: WireSpaceStore;
  // Seconds an untouched answer cursor survives, and how many the server
  // holds open at once before /ask is refused.
  cursorIdle?: number;
  cursorLimit?: number;
}

export interface RunningServer {
  server: Server;
  store: WireSpaceStore;
  host: string;
  port: number;
  close(): Promise<void>;
}

export function startServer(options: ServerOptions = {}): Promise<RunningServer> {
  const host = options.host ?? "127.0.0.1";
  const token = options.token ?? null;
  const maxBody = options.maxBody ?? DEFAULT_MAX_BODY;
  const served = options.spaces == null ? null : new Set(options.spaces);
  const store = options.store ?? new SpaceStore(served);
  const cursors = new CursorTable(
    (options.cursorIdle ?? DEFAULT_CURSOR_IDLE_SECONDS) * 1000,
    options.cursorLimit ?? DEFAULT_CURSOR_LIMIT,
  );
  const sockets = new Set<import("node:net").Socket>();

  const server = createServer((request, response) => {
    void handle(request, response);
  });
  server.on("connection", (socket) => {
    sockets.add(socket);
    socket.on("close", () => sockets.delete(socket));
  });

  async function handle(request: IncomingMessage, response: ServerResponse): Promise<void> {
    const started = process.hrtime.bigint();
    const path = (request.url ?? "/").replace(/^\/+|\/+$/g, "");
    let status = 200;
    let answer: unknown;
    try {
      if (request.method === "GET" && path === "health") {
        // protocol names the wire contract's revision, the seam
        // describing itself as data before anyone speaks it. Revision 2
        // adds the reflection: capabilities names what this server
        // admits, so a client can ask before writing, and bound says
        // whether /match honors the bound field exactly. Revision 3 adds
        // `stream`, the ask/next/stop lifecycle every gateway speaks.
        answer = {
          ok: true,
          atoms: store.count(),
          protocol: 3,
          capabilities: ["match", "enumerate", "add", "remove", "stream"],
          bound: typeof store.boundedMatch === "function",
        };
      } else if (request.method !== "POST") {
        throw new HttpProblem(405, `method ${request.method} is not supported; POST an operation`);
      } else if (!credentialAccepted(request, token)) {
        // Before the body is read, so an unauthorized request drives no parser.
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
        const payload = parsed as Payload;
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
      "content-length": String(body.length),
    });
    response.end(body);
    const elapsedMs = Number(process.hrtime.bigint() - started) / 1e6;
    process.stderr.write(
      `${new Date().toISOString()} ${request.method} /${path} ${status} ${elapsedMs.toFixed(2)}ms\n`,
    );
  }

  function operate(operation: string, payload: Payload): unknown {
    switch (operation) {
      case "match": {
        const space = payloadSpace(payload);
        const pattern = payloadAtom(payload, "pattern");
        const bound = payloadBound(payload);
        // Honored exactly when the store can; ignored (a sound
        // over-answer) when it cannot, which health advertises.
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
        const entry: OpenCursor = {
          iterator: store.stream(space, pattern),
          space,
          remaining: bound,
          deadline: 0,
        };
        const { atoms, done } = pull(entry, batch);
        if (done) {
          entry.iterator.return?.(undefined);
          return { atoms, cursor: null };
        }
        return { atoms, cursor: cursors.hold(entry) };
      }
      case "next": {
        const token = payload["cursor"];
        const entry = cursors.take(token);
        const { atoms, done } = pull(entry, payloadBatch(payload));
        if (done) cursors.release(token);
        return { atoms, cursor: done ? null : token };
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
        close: () =>
          new Promise<void>((done, fail) => {
            for (const socket of sockets) socket.destroy();
            // The cursors go with the listener: each is an iterator this
            // server holds on a client's behalf, and a client that walked
            // away leaves one behind.
            cursors.closeAll();
            server.close((error) => (error ? fail(error) : done()));
          }),
      });
    });
  });
}

// ---------------------------------------------------------------------------
// CLI entry: flags in, one readiness line out on stdout, logs on stderr.

function parseArguments(argv: readonly string[]): ServerOptions {
  const options: ServerOptions = {
    token: process.env["METTA_SPACE_TOKEN"] ?? null,
  };
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    const value = () => {
      const next = argv[++i];
      if (next === undefined) throw new Error(`${flag} needs a value`);
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
      case "--cursor-idle":
        options.cursorIdle = Number(value());
        break;
      case "--cursor-limit":
        options.cursorLimit = Number(value());
        break;
      default:
        throw new Error(`unknown flag ${flag}`);
    }
  }
  return options;
}

export function runCli(argv: readonly string[] = process.argv.slice(2)): void {
  startServer(parseArguments(argv))
    .then((running) => {
      process.stdout.write(
        JSON.stringify({ listening: { host: running.host, port: running.port } }) + "\n",
      );
      const stop = () => {
        void running.close().then(() => process.exit(0));
      };
      process.on("SIGINT", stop);
      process.on("SIGTERM", stop);
    })
    .catch((error) => {
      process.stderr.write(`space server failed to start: ${error}\n`);
      process.exit(1);
    });
}
