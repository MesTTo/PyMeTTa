/* Purpose: the same remote-space protocol served from a MeTTaScript space:
 *   two MeTTa engines joined through one seam, with MeTTaScript's own
 *   InMemorySpace holding the atoms and its own unifier filtering them.
 * Assumes:
 *   - a MeTTaScript checkout or install is reachable; --mettascript or
 *     METTASCRIPT_CORE names its core module (the built dist of
 *     @mettascript/core, or the package name where node can resolve it)
 *   - the bridge is STORAGE-level on purpose: add, enumerate, unifiable.
 *     MeTTaScript's evaluator never runs, so a semantic quirk in its
 *     evaluation cannot enter; and PeTTa re-unifies every candidate this
 *     server answers, so a quirk in its matcher can cost time, never
 *     soundness. The conformance kit judges the composition anyway.
 * Guarantees:
 *   - removal takes every stored occurrence unifiable with the sent atom,
 *     the multiset reading remove-atom has everywhere, by enumerating and
 *     removing structurally-equal atoms one at a time
 *   - a wire value the mapping cannot carry faithfully is refused with a
 *     400 rather than stored approximately
 * Open Obligations:
 *   To Do: None
 *   Hacks: None
 *   Future Enhancements: None
 */

import { pathToFileURL } from "node:url";
import {
  HttpProblem,
  startServer,
  unifiable,
  type ServerOptions,
  type WireAtom,
  type WireSpaceStore,
} from "./space_server.ts";

// The slice of @mettascript/core this bridge stands on.
interface MettascriptCore {
  sym(name: string): unknown;
  variable(name: string): unknown;
  expr(items: readonly unknown[]): unknown;
  gnd(value: Record<string, unknown>): unknown;
  unifiable(a: unknown, b: unknown): boolean;
  InMemorySpace: new () => {
    add(atom: unknown): void;
    remove(atom: unknown): boolean;
    atoms(): readonly unknown[];
  };
}

interface CoreAtom {
  kind: "sym" | "var" | "expr" | "gnd";
  name?: string;
  items?: readonly CoreAtom[];
  value?: { g: string; n?: number | bigint; s?: string; b?: boolean };
}

export function wireToCore(core: MettascriptCore, atom: WireAtom): unknown {
  const [tag, payload] = atom;
  switch (tag) {
    case "s":
      return core.sym(payload as string);
    case "v":
      return core.variable(payload as string);
    case "e":
      return core.expr((payload as WireAtom[]).map((item) => wireToCore(core, item)));
    case "n": {
      const n = payload as number;
      return Number.isInteger(n) ? core.gnd({ g: "int", n }) : core.gnd({ g: "float", n });
    }
    case "g": {
      if (typeof payload === "string") return core.gnd({ g: "str", s: payload });
      if (typeof payload === "boolean") return core.gnd({ g: "bool", b: payload });
      throw new HttpProblem(
        400,
        `grounded wire value of type ${typeof payload} has no MeTTaScript reading here`,
      );
    }
  }
}

export function coreToWire(atom: CoreAtom): WireAtom {
  switch (atom.kind) {
    case "sym":
      return ["s", atom.name ?? ""];
    case "var":
      return ["v", atom.name ?? ""];
    case "expr":
      return ["e", (atom.items ?? []).map((item) => coreToWire(item))];
    case "gnd": {
      const value = atom.value;
      if (value === undefined) break;
      if (value.g === "int" || value.g === "float") {
        const n = value.n;
        if (typeof n === "bigint") {
          if (n > BigInt(Number.MAX_SAFE_INTEGER) || n < -BigInt(Number.MAX_SAFE_INTEGER)) {
            throw new HttpProblem(
              400,
              `stored integer ${n} exceeds what this wire carries faithfully`,
            );
          }
          return ["n", Number(n)];
        }
        return ["n", n as number];
      }
      if (value.g === "str") return ["g", value.s as string];
      if (value.g === "bool") return ["g", value.b as boolean];
      break;
    }
  }
  throw new HttpProblem(
    400,
    `stored MeTTaScript atom of kind ${atom.kind} has no wire reading here`,
  );
}

export class MettascriptStore implements WireSpaceStore {
  private readonly spaces = new Map<string, InstanceType<MettascriptCore["InMemorySpace"]>>();

  constructor(
    private readonly core: MettascriptCore,
    private readonly served: ReadonlySet<string> | null = null,
  ) {}

  private space(name: string) {
    if (this.served !== null && !this.served.has(name)) {
      throw new HttpProblem(400, `space '${name}' is not served`);
    }
    let space = this.spaces.get(name);
    if (space === undefined) {
      space = new this.core.InMemorySpace();
      this.spaces.set(name, space);
    }
    return space;
  }

  add(name: string, atom: WireAtom): void {
    this.space(name).add(wireToCore(this.core, atom));
  }

  addMany(name: string, atoms: readonly WireAtom[]): number {
    const space = this.space(name);
    for (const atom of atoms) space.add(wireToCore(this.core, atom));
    return atoms.length;
  }

  atoms(name: string): readonly WireAtom[] {
    return this.space(name).atoms().map((atom) => coreToWire(atom as CoreAtom));
  }

  // MeTTaScript's own unifier answers first; the wire unifier is the
  // soundness envelope. The protocol's law is that match may never
  // under-approximate unification, and the GatewayComplianceSuite found
  // MeTTaScript refusing rational-tree matches ((f $y $y) against a
  // stored (f (g $x) $x)) that the law answers. Over-approximating is
  // always legal, so the union keeps the law whatever either unifier
  // decides, and PeTTa re-unifies every candidate anyway.
  private admits(wanted: unknown, pattern: WireAtom, atom: unknown): boolean {
    return (
      this.core.unifiable(wanted, atom) ||
      unifiable(pattern, coreToWire(atom as CoreAtom))
    );
  }

  match(name: string, pattern: WireAtom): WireAtom[] {
    const wanted = wireToCore(this.core, pattern);
    return this.space(name)
      .atoms()
      .filter((atom) => this.admits(wanted, pattern, atom))
      .map((atom) => coreToWire(atom as CoreAtom));
  }

  remove(name: string, pattern: WireAtom): boolean {
    const space = this.space(name);
    const wanted = wireToCore(this.core, pattern);
    const doomed = space.atoms().filter((atom) => this.admits(wanted, pattern, atom));
    for (const atom of doomed) space.remove(atom);
    return doomed.length > 0;
  }

  count(): number {
    let total = 0;
    for (const space of this.spaces.values()) total += space.atoms().length;
    return total;
  }
}

function parseArguments(argv: readonly string[]): ServerOptions & { corePath: string } {
  let corePath = process.env["METTASCRIPT_CORE"] ?? "@mettascript/core";
  const options: ServerOptions = { token: process.env["PETTA_SPACE_TOKEN"] ?? null };
  let spaces: readonly string[] | null = null;
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    const value = () => {
      const next = argv[++i];
      if (next === undefined) throw new Error(`${flag} needs a value`);
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

export function runCli(argv: readonly string[] = process.argv.slice(2)): void {
  const { corePath, ...options } = parseArguments(argv);
  const specifier = corePath.startsWith("/") ? pathToFileURL(corePath).href : corePath;
  import(specifier)
    .then((core: MettascriptCore) => {
      const served = options.spaces == null ? null : new Set(options.spaces);
      return startServer({ ...options, store: new MettascriptStore(core, served) });
    })
    .then((running) => {
      process.stdout.write(
        JSON.stringify({
          listening: { host: running.host, port: running.port },
          backend: "mettascript",
        }) + "\n",
      );
      const stop = () => {
        void running.close().then(() => process.exit(0));
      };
      process.on("SIGINT", stop);
      process.on("SIGTERM", stop);
    })
    .catch((error) => {
      process.stderr.write(`mettascript space server failed to start: ${error}\n`);
      process.exit(1);
    });
}
